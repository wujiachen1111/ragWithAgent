#!/usr/bin/env python3
"""
统一服务停止脚本
"""

import argparse
import subprocess
import os
import signal
import sys
import json
import psutil
import time
from pathlib import Path


def stop_docker_services():
    """停止Docker服务"""
    project_root = Path(__file__).parent
    subprocess.run(["docker-compose", "down"], cwd=project_root, check=True)
    print("已停止所有Docker服务")


def _read_service_info(pid_dir: Path, service_name: str):
    info_path = pid_dir / f"{service_name}.json"
    if not info_path.exists():
        return None
    try:
        return json.loads(info_path.read_text())
    except Exception:
        return None


def _cleanup_service_info(pid_dir: Path, service_name: str):
    info_path = pid_dir / f"{service_name}.json"
    if info_path.exists():
        try:
            info_path.unlink()
        except Exception:
            pass


def _pids_listening_on_port(port: int):
    pids = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port and conn.pid:
                pids.add(conn.pid)
    except Exception:
        pass
    return list(pids)


DEFAULT_PORTS = {
    "yuqing": 8000,
    "rag": 8010,
    "stock_agent": 8020,
}


def _pids_listening_on_port(port: int):
    pids = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port and conn.pid:
                pids.add(conn.pid)
    except Exception:
        pass
    return list(pids)


def _try_free_port(port: int, service_name: str, timeout: float = 5.0) -> bool:
    pids = _pids_listening_on_port(port)
    if not pids:
        return True
    print(f"检测到 {service_name} 端口 {port} 被占用，尝试释放...")
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                proc.kill()
        except Exception:
            continue
    time.sleep(0.5)
    return not _pids_listening_on_port(port)


def stop_local_services(services=None, force_free_ports: bool = False):
    """通过PID文件停止本地服务"""
    project_root = Path(__file__).parent
    pid_dir = project_root / ".pids"

    if not pid_dir.exists():
        print("PID目录不存在，似乎没有正在运行的服务。")
        return

    service_pids = {}
    all_pid_files = list(pid_dir.glob("*.pid"))

    if not all_pid_files:
        print("未找到任何PID文件，似乎没有正在运行的服务。")
        return

    # 读取所有PID
    for pid_file in all_pid_files:
        service_name = pid_file.stem
        if services is None or service_name in services:
            with open(pid_file, "r") as f:
                try:
                    service_pids[service_name] = int(f.read().strip())
                except ValueError:
                    print(f"警告：无法从 {pid_file.name} 读取有效的PID。")
                    continue

    if not service_pids:
        print("未找到匹配的服务进程。")
        return

    # 优雅地终止进程 (SIGTERM)
    for service_name, pid in service_pids.items():
        try:
            if psutil.pid_exists(pid):
                print(f"正在停止 {service_name} 服务 (PID: {pid})... (SIGTERM)")
                os.kill(pid, signal.SIGTERM)
            else:
                print(f"{service_name} 服务 (PID: {pid}) 已不存在。")
        except OSError as e:
            print(f"停止 {service_name} 服务失败 (PID: {pid}): {e}")

    # 等待进程关闭
    time.sleep(3)

    # 强制终止仍在运行的进程 (SIGKILL)
    for service_name, pid in service_pids.items():
        try:
            if psutil.pid_exists(pid):
                print(f"{service_name} 服务 (PID: {pid}) 未能优雅关闭，强制停止... (SIGKILL)")
                os.kill(pid, signal.SIGKILL)
        except OSError as e:
            print(f"强制停止 {service_name} 服务失败 (PID: {pid}): {e}")

    # 清理PID文件
    for service_name, pid in service_pids.items():
        pid_file = pid_dir / f"{service_name}.pid"
        if pid_file.exists():
            pid_file.unlink()
        _cleanup_service_info(pid_dir, service_name)

    # 可选：尝试释放端口（优先使用记录的端口；如无记录，使用默认端口）
    if force_free_ports:
        target_services = services or [p.stem for p in pid_dir.glob("*.pid")]
        for service_name in target_services:
            info = _read_service_info(pid_dir, service_name)
            port = None
            if info and "port" in info:
                try:
                    port = int(info["port"])
                except Exception:
                    port = None
            if not port:
                port = DEFAULT_PORTS.get(service_name)
            if not port:
                continue
            _try_free_port(port, service_name)
            
    print("\n所有选定服务已停止。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="服务停止管理器")
    parser.add_argument("--env", choices=["development", "docker"], 
                       default="development", help="运行环境")
    parser.add_argument("--services", nargs="*", help="指定停止的服务 (例如: yuqing rag)")
    parser.add_argument("--force-free-ports", action="store_true", help="尝试强制释放被记录的服务端口（谨慎使用）")
    
    args = parser.parse_args()
    
    if args.env == "docker":
        stop_docker_services()
    else:
        stop_local_services(args.services, force_free_ports=args.force_free_ports)
