#!/usr/bin/env python3
"""
统一服务启动脚本
支持开发环境、Docker环境、生产环境
"""

import argparse
import asyncio
import subprocess
import os
import socket
import json
import signal
from pathlib import Path
import sys
import time
import sys
from pathlib import Path
import psutil


class ServiceManager:
    def __init__(self, environment="development", *, strict_ports: bool = True, yuqing_port: int | None = None, rag_port: int | None = None, stock_port: int | None = None):
        self.environment = environment
        self.strict_ports = strict_ports
        self.yuqing_port = yuqing_port
        self.rag_port = rag_port
        self.stock_port = stock_port
        self.project_root = Path(__file__).parent
        self.pid_dir = self.project_root / ".pids"
        self.pid_dir.mkdir(exist_ok=True)
        
        # 绕过系统代理 (如Privoxy)，避免其干扰服务对外的API调用
        for proxy_var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
                print(f"提示：已清除 {proxy_var} 环境变量以绕过系统代理。")
        
    async def start_services(self, services=None):
        """启动指定服务或所有服务"""
        if self.environment == "docker":
            await self._start_docker_services(services)
        else:
            await self._start_local_services(services)
    
    async def _start_docker_services(self, services):
        """使用Docker Compose启动服务"""
        cmd = ["docker-compose", "-f", "docker-compose.yml"]
            
        cmd.append("up")
        
        if services:
            cmd.extend(services)
        else:
            cmd.append("-d")  # 后台运行所有服务
            
        subprocess.run(cmd, cwd=self.project_root)
    
    async def _start_local_services(self, services):
        """本地启动服务（考虑依赖顺序）"""
        available_services = {"yuqing", "rag", "stock_agent"}

        # 默认启动全部
        if not services:
            services = ["yuqing", "stock_agent", "rag"]
        else:
            services = [s for s in services if s in available_services]

        # 先启动 yuqing（独立）
        if "yuqing" in services:
            await self._start_yuqing_service()

        # 若需要 rag 且包含 stock_agent，则先启动 stock_agent，拿到端口再启动 rag
        stock_agent_port = None
        if "stock_agent" in services:
            stock_agent_port = await self._start_stock_agent_service()

        if "rag" in services:
            stock_api_url = None
            if stock_agent_port:
                stock_api_url = f"http://localhost:{stock_agent_port}"
            await self._start_rag_service(stock_api_url=stock_api_url)

        print("\n所有服务已启动。")

    def _is_port_available(self, port: int, host: str = "0.0.0.0") -> bool:
        """检测端口是否可用。"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return True
            except OSError:
                return False

    def _pids_listening_on_port(self, port: int):
        pids = set()
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr and conn.laddr.port == port and conn.pid:
                    pids.add(conn.pid)
        except Exception:
            pass
        return list(pids)

    def _looks_like_our_service(self, proc: psutil.Process, service_dir: Path) -> bool:
        try:
            info = proc.as_dict(attrs=["cmdline", "cwd", "name"])
            cmdline = " ".join(info.get("cmdline") or [])
            cwd = info.get("cwd") or ""
            if str(service_dir) in cmdline or str(service_dir) in cwd:
                return True
            # 兼容常见 uvicorn/python 启动形式
            if "uvicorn" in (info.get("name") or "") and str(service_dir) in cwd:
                return True
        except Exception:
            return False
        return False

    def _try_free_port(self, port: int, service_name: str, service_dir: Path, timeout: float = 5.0) -> bool:
        """尝试优雅释放被我们服务占用的端口。仅当进程看起来属于我们的服务目录时才处理。"""
        pids = self._pids_listening_on_port(port)
        if not pids:
            return True
        killed_any = False
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                if not self._looks_like_our_service(proc, service_dir):
                    continue
                print(f"提示：检测到 {service_name} 端口 {port} 被 PID {pid} 占用，尝试释放...")
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except psutil.TimeoutExpired:
                    proc.kill()
                killed_any = True
            except Exception:
                continue
        # 再次确认
        time.sleep(0.5)
        return self._is_port_available(port)

    def _choose_free_port(self, preferred: int, host: str = "0.0.0.0", max_increment: int = 50) -> int:
        """根据策略选择端口。
        - strict 模式：首选端口可用则用，否则抛错。
        - 非 strict：从首选向上探测，返回首个可用端口（找不到则回退首选）。
        """
        if self.strict_ports:
            if self._is_port_available(preferred, host):
                return preferred
            raise RuntimeError(f"端口 {preferred} 已被占用（严格模式）")
        port = preferred
        for _ in range(max_increment + 1):
            if self._is_port_available(port, host):
                return port
            port += 1
        return preferred

    def _write_pid_file(self, service_name: str, pid: int):
        """将PID写入文件"""
        if not self.pid_dir.exists():
            self.pid_dir.mkdir()
        with open(self.pid_dir / f"{service_name}.pid", "w") as f:
            f.write(str(pid))
    
    def _write_service_info(self, service_name: str, pid: int, port: int):
        """记录服务元信息，便于停止与排障。"""
        try:
            info = {"pid": pid, "port": int(port)}
            with open(self.pid_dir / f"{service_name}.json", "w") as f:
                json.dump(info, f)
        except Exception:
            # 保底：即使写入失败也不影响启动流程
            pass
        
    async def _start_yuqing_service(self):
        """启动舆情分析服务"""
        # yuqing 使用固定端口 8000（应用内固定），仅做占用检测
        yuqing_port = 8000
        service_dir = self.project_root / "apps" / "yuqing-sentiment"
        if not self._is_port_available(yuqing_port):
            # 尝试释放由我们自己先前启动的残留进程
            if not self._try_free_port(yuqing_port, "yuqing", service_dir):
                if self.strict_ports:
                    raise RuntimeError(f"yuqing-sentiment 端口 {yuqing_port} 已被占用（严格模式）")
        print(f"正在启动舆情分析服务 (端口: {yuqing_port})...")
        service_dir = self.project_root / "apps" / "yuqing-sentiment"
        # 计算本地SQLite路径
        sqlite_path = (self.project_root / "data" / "yuqing" / "yuqing.db").resolve()
        env = {
            **os.environ, 
            "HOST": "0.0.0.0", 
            "CHROMA_PERSIST_DIRECTORY": str(self.project_root / "data" / "yuqing" / "chromadb"),
            # 使用本地SQLite，避免未启动Postgres导致失败
            "DATABASE_URL": f"sqlite:///{sqlite_path}",
            # 使用本机Redis（可通过docker-compose启动）
            "REDIS_URL": "redis://localhost:6379/0",
            # 禁用 Transformers 的 TensorFlow/Keras 分支
            "TRANSFORMERS_NO_TF": "1",
            # 确保可导入 src 下的包
            "PYTHONPATH": f"{service_dir / 'src'}:{os.getenv('PYTHONPATH', '')}"
        }
        process = subprocess.Popen([sys.executable, "-m", "src.main"], env=env, cwd=service_dir)
        self._write_pid_file("yuqing", process.pid)
        self._write_service_info("yuqing", process.pid, yuqing_port)
        print(f"舆情分析服务已启动, PID: {process.pid}")
        
    async def _start_rag_service(self, stock_api_url: str | None = None):
        """启动RAG分析服务"""
        rag_port = int(self.rag_port or os.getenv("API__PORT", "8010"))
        service_dir = self.project_root / "apps" / "rag-analysis"
        if not self._is_port_available(rag_port):
            if not self._try_free_port(rag_port, "rag", service_dir):
                if self.strict_ports:
                    raise RuntimeError(f"rag-analysis 端口 {rag_port} 已被占用（严格模式）")
        print(f"正在启动RAG分析服务 (端口: {rag_port})...")
        service_dir = self.project_root / "apps" / "rag-analysis"
        env = {
            **os.environ, 
            "API__HOST": "0.0.0.0", 
            "API__PORT": str(rag_port),
            "YUQING_API_URL": "http://localhost:8000",
            "SENTIMENT_API_URL": "http://localhost:8000",
            "STOCK_API_URL": stock_api_url or os.getenv("STOCK_API_URL", "http://localhost:8020"),
            # 确保可导入 src 下的包
            # 仅包含当前服务 src，避免根级 `services` 包与本服务的 `services` 冲突
            "PYTHONPATH": f"{service_dir / 'src'}:{os.getenv('PYTHONPATH', '')}"
        }
        process = subprocess.Popen([sys.executable, "-m", "src.main"], env=env, cwd=service_dir)
        self._write_pid_file("rag", process.pid)
        self._write_service_info("rag", process.pid, rag_port)
        print(f"RAG分析服务已启动, PID: {process.pid}")

    async def _start_stock_agent_service(self):
        """启动股票代理服务"""
        # 端口以单一变量管理，避免提示与实际端口不一致
        desired_port = int(self.stock_port or os.getenv("STOCK_API__PORT", "8020"))
        service_dir = self.project_root / "apps" / "stock-agent"
        if not self._is_port_available(desired_port):
            if not self._try_free_port(desired_port, "stock_agent", service_dir):
                if self.strict_ports:
                    raise RuntimeError(f"stock-agent 端口 {desired_port} 已被占用（严格模式）")
        print(f"正在启动股票代理服务 (端口: {desired_port})...")
        service_dir = self.project_root / "apps" / "stock-agent"
        env = {
            **os.environ,
            "STOCK_API__HOST": "0.0.0.0",
            "STOCK_API__PORT": str(desired_port),
            # 使用本机MongoDB（可通过docker-compose或手动启动）
            "STOCK_DATABASE__URI": "mongodb://localhost:27017/",
            "STOCK_DATABASE__DATABASE": "stock_data",
            # 确保可导入 src 下的包
            "PYTHONPATH": f"{service_dir / 'src'}:{os.getenv('PYTHONPATH', '')}"
        }
        process = subprocess.Popen([sys.executable, "-m", "src.main"], env=env, cwd=service_dir)
        self._write_pid_file("stock_agent", process.pid)
        self._write_service_info("stock_agent", process.pid, desired_port)
        print(f"股票代理服务已启动, PID: {process.pid}")
        return desired_port


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="服务启动管理器")
    parser.add_argument("--env", choices=["development", "docker", "production"], 
                       default="development", help="运行环境")
    parser.add_argument("--services", nargs="*", help="指定启动的服务")
    # 默认启用严格端口模式，提供禁用开关
    parser.add_argument("--no-strict-ports", dest="strict_ports", action="store_false", help="禁用严格端口模式（不推荐）：端口占用时不提前报错")
    parser.add_argument("--yuqing-port", type=int, help="指定 yuqing-sentiment 服务端口（默认 8000）")
    parser.add_argument("--rag-port", type=int, help="指定 rag-analysis 服务端口（默认 8010）")
    parser.add_argument("--stock-port", type=int, help="指定 stock-agent 服务端口（默认 8020）")
    parser.add_argument("--print-ports", action="store_true", help="仅打印当前记录的服务端口并退出")
    
    args = parser.parse_args()
    if args.print_ports:
        pid_dir = Path(__file__).parent / ".pids"
        if not pid_dir.exists():
            print("无端口信息：未发现 .pids 目录")
            sys.exit(0)
        entries = list(pid_dir.glob("*.json"))
        if not entries:
            print("无端口信息：未发现服务信息文件")
            sys.exit(0)
        for p in entries:
            try:
                data = json.loads(p.read_text())
                print(f"{p.stem}: port={data.get('port')} pid={data.get('pid')}")
            except Exception:
                continue
        sys.exit(0)

    manager = ServiceManager(
        args.env,
        strict_ports=args.strict_ports if hasattr(args, 'strict_ports') else True,
        yuqing_port=args.yuqing_port,
        rag_port=args.rag_port,
        stock_port=args.stock_port,
    )
    asyncio.run(manager.start_services(args.services))
