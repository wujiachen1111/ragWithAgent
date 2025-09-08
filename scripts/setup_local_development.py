#!/usr/bin/env python3
"""
本地开发环境自动化设置脚本
基于兼容性检查结果，自动配置开发环境
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import json
import venv
import platform


class LocalDevelopmentSetup:
    """本地开发环境设置器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.platform = platform.system()
        self.venv_path = self.project_root / "venv"
        self.python_executable = sys.executable
        # conda 环境检测
        self.using_conda = bool(os.environ.get("CONDA_PREFIX"))
        self.conda_prefix = os.environ.get("CONDA_PREFIX", "")
        self.conda_env_name = os.environ.get("CONDA_DEFAULT_ENV", "ragWithAgent")
        
        # 检查兼容性报告
        self.compatibility_report = self.load_compatibility_report()
        
        print(f"🏠 项目根目录: {self.project_root}")
        print(f"🐍 Python版本: {sys.version}")
        print(f"💻 操作系统: {self.platform}")
        if self.using_conda:
            print(f"🧪 已检测到conda环境: {self.conda_env_name} @ {self.conda_prefix}")
    
    def load_compatibility_report(self) -> Optional[Dict]:
        """加载兼容性检查报告"""
        report_path = self.project_root / "compatibility_report.json"
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def setup_virtual_environment(self) -> bool:
        """设置虚拟环境"""
        print("\n🔧 设置虚拟环境...")
        # 已在conda下运行时跳过创建venv
        if self.using_conda:
            print(f"  ✅ 已在conda环境中运行: {self.conda_env_name}，跳过venv创建")
            return True
        
        if self.venv_path.exists():
            print(f"  ✅ 虚拟环境已存在: {self.venv_path}")
            return True
        
        try:
            print(f"  📦 创建虚拟环境: {self.venv_path}")
            venv.create(self.venv_path, with_pip=True)
            print("  ✅ 虚拟环境创建成功")
            return True
        except Exception as e:
            print(f"  ❌ 虚拟环境创建失败: {e}")
            return False
    
    def get_venv_python(self) -> str:
        """获取虚拟环境中的Python可执行文件路径"""
        if self.using_conda:
            # 直接使用当前解释器
            return self.python_executable
        if self.platform == "Windows":
            return str(self.venv_path / "Scripts" / "python.exe")
        else:
            return str(self.venv_path / "bin" / "python")
    
    def get_venv_pip(self) -> str:
        """获取虚拟环境中的pip可执行文件路径"""
        if self.using_conda and self.conda_prefix:
            if self.platform == "Windows":
                candidate = Path(self.conda_prefix) / "Scripts" / "pip.exe"
            else:
                candidate = Path(self.conda_prefix) / "bin" / "pip"
            return str(candidate)
        if self.platform == "Windows":
            return str(self.venv_path / "Scripts" / "pip.exe")
        else:
            return str(self.venv_path / "bin" / "pip")
    
    def install_dependencies(self) -> bool:
        """安装项目依赖"""
        print("\n📦 安装项目依赖...")
        
        pip_executable = self.get_venv_pip()
        
        # 定义依赖安装顺序（重要依赖优先）
        dependency_groups = [
            {
                "name": "核心依赖",
                "packages": [
                    "fastapi==0.104.1",
                    "uvicorn[standard]==0.24.0",
                    "pydantic==2.5.0",
                    "pydantic-settings==2.1.0",
                    "python-dotenv==1.0.0"
                ]
            },
            {
                "name": "网络通信",
                "packages": [
                    "httpx==0.25.2",
                    "aiohttp==3.9.1",
                    "requests==2.31.0",
                    "tenacity==8.2.3"
                ]
            },
            {
                "name": "数据库和存储",
                "packages": [
                    "sqlalchemy==2.0.23",
                    "alembic==1.12.1",
                    "redis==5.0.1"
                ]
            },
            {
                "name": "数据处理",
                "packages": [
                    "pandas==2.1.3",
                    "numpy==1.25.2",
                    "python-dateutil==2.8.2",
                    "pytz==2023.3"
                ]
            },
            {
                "name": "AI和NLP",
                "packages": [
                    "sentence-transformers==2.2.2",
                    "jieba==0.42.1",
                    "chromadb==0.4.18"
                ]
            },
            {
                "name": "工具和实用库",
                "packages": [
                    "loguru==0.7.2",
                    "schedule==1.2.0",
                    "python-multipart==0.0.6",
                    "beautifulsoup4==4.12.2",
                    "lxml==4.9.3",
                    "feedparser==6.0.10"
                ]
            }
        ]
        
        # 升级pip（conda环境内同样适用）
        try:
            print("  🔄 升级pip...")
            subprocess.run([pip_executable, "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            print("  ✅ pip升级完成")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  pip升级失败，继续安装: {e}")
        
        # 逐组安装依赖
        for group in dependency_groups:
            print(f"\n  📦 安装{group['name']}...")
            
            for package in group['packages']:
                try:
                    print(f"    ⏳ 安装 {package}")
                    result = subprocess.run([
                        pip_executable, "install", package
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        print(f"    ✅ {package} 安装成功")
                    else:
                        print(f"    ⚠️  {package} 安装失败: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    print(f"    ⏰ {package} 安装超时，跳过")
                except Exception as e:
                    print(f"    ❌ {package} 安装异常: {e}")
        
        # 验证关键依赖
        critical_packages = ["fastapi", "uvicorn", "pydantic", "httpx", "sqlalchemy"]
        print(f"\n  🔍 验证关键依赖...")
        
        python_executable = self.get_venv_python()
        all_critical_installed = True
        
        for package in critical_packages:
            try:
                result = subprocess.run([
                    python_executable, "-c", f"import {package}; print('{package} OK')"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"    ✅ {package} 验证通过")
                else:
                    print(f"    ❌ {package} 验证失败")
                    all_critical_installed = False
                    
            except Exception as e:
                print(f"    ❌ {package} 验证异常: {e}")
                all_critical_installed = False
        
        return all_critical_installed
    
    def create_configuration_files(self) -> bool:
        """创建配置文件"""
        print("\n⚙️  创建配置文件...")
        
        # 创建环境配置文件
        env_content = """# 本地开发环境配置
# 数据库配置
DATABASE_URL=sqlite:///./data/ragwithagentstats.db
# DATABASE_URL=postgresql://user:password@localhost:5432/ragwithagentstats

# Redis配置 (可选)
# REDIS_URL=redis://localhost:6379/0

# 服务端口配置
YUQING_PORT=8000
RAG_ANALYSIS_PORT=8010

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=./logs

# API配置
YUQING_API_URL=http://localhost:8000
LLM_GATEWAY_URL=http://localhost:8002/v1/chat/completions

# 开发模式
DEBUG=true
ENABLE_MOCK_LLM=false
ENABLE_HOT_RELOAD=true

# 数据目录
DATA_DIR=./data
"""
        
        env_file = self.project_root / ".env.local"
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"  ✅ 环境配置文件: {env_file}")
        
        # 创建数据目录
        data_dirs = [
            self.project_root / "data",
            self.project_root / "data" / "yuqing",
            self.project_root / "logs",
            self.project_root / "logs" / "yuqing",
            self.project_root / "logs" / "rag"
        ]
        
        for data_dir in data_dirs:
            data_dir.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ 数据目录: {data_dir}")
        
        # 创建启动脚本配置（更新为 apps/* 结构）
        startup_config = {
            "services": {
                "yuqing-sentiment": {
                    "path": "apps/yuqing-sentiment/src",
                    "main": "yuqing.main:app",
                    "port": 8000,
                    "env_file": ".env.local"
                },
                "rag-analysis": {
                    "path": "apps/rag-analysis/src",
                    "main": "main:app",
                    "port": 8010,
                    "env_file": ".env.local"
                }
            },
            "development": {
                "hot_reload": True,
                "log_level": "info",
                "workers": 1
            }
        }
        
        config_file = self.project_root / "local_services.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(startup_config, f, indent=2, ensure_ascii=False)
        print(f"  ✅ 服务配置文件: {config_file}")
        
        return True
    
    def create_database_schema(self) -> bool:
        """创建数据库表结构"""
        print("\n🗄️  初始化数据库...")
        
        python_executable = self.get_venv_python()
        
        # 检查SQLite数据库
        db_path = self.project_root / "data" / "ragwithagentstats.db"
        
        if not db_path.exists():
            print(f"  📄 创建SQLite数据库: {db_path}")
            
            # 创建基础表结构的SQL
            init_sql = """
CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    source TEXT,
    source_url TEXT,
    published_at DATETIME,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    language TEXT DEFAULT 'zh',
    region TEXT DEFAULT 'CN'
);

CREATE TABLE IF NOT EXISTS sentiment_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER,
    sentiment_label TEXT,
    confidence_score REAL,
    market_impact_level TEXT,
    analysis_result TEXT,
    analysis_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (news_id) REFERENCES news_items (id)
);

CREATE TABLE IF NOT EXISTS analysis_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    content TEXT,
    symbols TEXT,
    time_horizon TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_items(published_at);
CREATE INDEX IF NOT EXISTS idx_sentiment_news_id ON sentiment_analysis(news_id);
CREATE INDEX IF NOT EXISTS idx_requests_created_at ON analysis_requests(created_at);
"""
            
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.executescript(init_sql)
                conn.commit()
                conn.close()
                print("  ✅ 数据库表结构创建成功")
                return True
            except Exception as e:
                print(f"  ❌ 数据库初始化失败: {e}")
                return False
        else:
            print(f"  ✅ 数据库已存在: {db_path}")
            return True
    
    def create_startup_scripts(self) -> bool:
        """创建启动脚本"""
        print("\n🚀 创建启动脚本...")
        
        # Windows批处理脚本
        if self.platform == "Windows":
            bat_content = f"""@echo off
echo 🚀 启动本地开发环境...

REM 激活虚拟环境
call "{self.venv_path}\\Scripts\\activate.bat"

REM 加载环境变量
set PYTHONPATH={self.project_root}
set ENV_FILE=.env.local

REM 启动YuQing服务
echo 📡 启动YuQing舆情服务 (端口8000)...
start "YuQing-Sentiment" cmd /k "cd /d {self.project_root}\\YuQing-new && python -m app.main"

REM 等待YuQing服务启动
timeout /t 5 /nobreak

REM 启动RAG分析服务
echo 🤖 启动RAG+Agent分析服务 (端口8010)...
start "RAG-Analysis" cmd /k "cd /d {self.project_root}\\services_new\\core\\analysis-orchestrator\\src && python main.py"

echo ✅ 所有服务已启动！
echo 🌐 YuQing服务: http://localhost:8000
echo 🌐 RAG分析服务: http://localhost:8010
echo 📚 API文档: http://localhost:8000/docs 和 http://localhost:8010/docs

pause
"""
            bat_file = self.project_root / "start_local_dev.bat"
            with open(bat_file, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            print(f"  ✅ Windows启动脚本: {bat_file}")
        
        # Unix/Linux/macOS shell脚本（在conda下优先激活conda环境，否则使用venv）
        if self.using_conda:
            activate_lines = (
                'eval "$(conda shell.bash hook)"\n'
                f'conda activate {self.conda_env_name}\n'
            )
            python_cmd = "python"
        else:
            activate_lines = f'source "{self.venv_path}/bin/activate"\n'
            python_cmd = "python"

        shell_content = f"""#!/bin/bash

echo "🚀 启动本地开发环境..."

# 激活环境
{activate_lines}

# 设置环境变量
export PYTHONPATH="{self.project_root}"
export ENV_FILE=".env.local"

# 创建日志目录
mkdir -p logs/yuqing logs/rag

# 启动YuQing服务
echo "📡 启动YuQing舆情服务 (端口8000)..."
cd "{self.project_root}/apps/yuqing-sentiment"
{python_cmd} -m src.main > "{self.project_root}/logs/yuqing/service.log" 2>&1 &
YUQING_PID=$!
echo "YuQing PID: $YUQING_PID"

# 等待YuQing服务启动
echo "⏳ 等待YuQing服务启动..."
sleep 5

# 启动RAG分析服务
echo "🤖 启动RAG+Agent分析服务 (端口8010)..."
cd "{self.project_root}/apps/rag-analysis"
{python_cmd} -m src.main > "{self.project_root}/logs/rag/service.log" 2>&1 &
RAG_PID=$!
echo "RAG Analysis PID: $RAG_PID"

# 保存PID到文件
echo $YUQING_PID > "{self.project_root}/logs/yuqing.pid"
echo $RAG_PID > "{self.project_root}/logs/rag.pid"

echo ""
echo "✅ 所有服务已启动！"
echo "🌐 YuQing服务: http://localhost:8000"
echo "🌐 RAG分析服务: http://localhost:8010"
echo "📚 API文档: http://localhost:8000/docs 和 http://localhost:8010/docs"
echo ""
echo "📄 日志文件:"
echo "  - YuQing: logs/yuqing/service.log"
echo "  - RAG: logs/rag/service.log"
echo ""
echo "🛑 停止服务: ./stop_local_dev.sh"

# 等待用户输入
echo "按 Ctrl+C 停止所有服务..."
wait
"""
        
        shell_file = self.project_root / "start_local_dev.sh"
        with open(shell_file, 'w', encoding='utf-8') as f:
            f.write(shell_content)
        
        # 设置执行权限
        if self.platform != "Windows":
            os.chmod(shell_file, 0o755)
        
        print(f"  ✅ Shell启动脚本: {shell_file}")
        
        # 创建停止脚本
        stop_content = f"""#!/bin/bash

echo "🛑 停止本地开发服务..."

# 读取PID并停止服务
if [ -f "{self.project_root}/logs/yuqing.pid" ]; then
    YUQING_PID=$(cat "{self.project_root}/logs/yuqing.pid")
    if kill -0 $YUQING_PID 2>/dev/null; then
        echo "🔄 停止YuQing服务 (PID: $YUQING_PID)..."
        kill $YUQING_PID
    fi
    rm -f "{self.project_root}/logs/yuqing.pid"
fi

if [ -f "{self.project_root}/logs/rag.pid" ]; then
    RAG_PID=$(cat "{self.project_root}/logs/rag.pid")
    if kill -0 $RAG_PID 2>/dev/null; then
        echo "🔄 停止RAG分析服务 (PID: $RAG_PID)..."
        kill $RAG_PID
    fi
    rm -f "{self.project_root}/logs/rag.pid"
fi

# 强制停止占用端口的进程
echo "🔍 检查端口占用..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8010 | xargs kill -9 2>/dev/null || true

echo "✅ 所有服务已停止"
"""
        
        stop_file = self.project_root / "stop_local_dev.sh"
        with open(stop_file, 'w', encoding='utf-8') as f:
            f.write(stop_content)
        
        if self.platform != "Windows":
            os.chmod(stop_file, 0o755)
        
        print(f"  ✅ 停止脚本: {stop_file}")
        
        return True
    
    def create_health_check_script(self) -> bool:
        """创建健康检查脚本"""
        print("\n🏥 创建健康检查脚本...")
        
        health_check_content = f"""#!/usr/bin/env python3
\"\"\"
本地服务健康检查脚本
\"\"\"

import asyncio
import aiohttp
import json
from datetime import datetime


async def check_service_health(name: str, url: str, timeout: int = 5) -> dict:
    \"\"\"检查单个服务健康状态\"\"\"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {{
                        "service": name,
                        "status": "✅ 健康",
                        "url": url,
                        "response_time": f"{{response.headers.get('X-Response-Time', 'N/A')}}",
                        "data": data
                    }}
                else:
                    return {{
                        "service": name,
                        "status": f"⚠️  HTTP {{response.status}}",
                        "url": url,
                        "error": f"HTTP状态码: {{response.status}}"
                    }}
    except asyncio.TimeoutError:
        return {{
            "service": name,
            "status": "⏰ 超时",
            "url": url,
            "error": f"请求超时 ({{timeout}}s)"
        }}
    except Exception as e:
        return {{
            "service": name,
            "status": "❌ 不可用",
            "url": url,
            "error": str(e)
        }}


async def main():
    \"\"\"主函数\"\"\"
    print("🏥 本地服务健康检查")
    print("=" * 50)
    print(f"🕐 检查时间: {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}")
    print()
    
    # 定义要检查的服务
    services = [
        ("YuQing舆情服务", "http://localhost:8000/health"),
        ("RAG分析服务", "http://localhost:8010/"),
        ("YuQing API文档", "http://localhost:8000/docs"),
        ("RAG API文档", "http://localhost:8010/docs")
    ]
    
    # 并行检查所有服务
    tasks = [check_service_health(name, url) for name, url in services]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 显示结果
    healthy_count = 0
    for result in results:
        if isinstance(result, Exception):
            print(f"❌ 检查异常: {{result}}")
            continue
            
        print(f"{{result['status']}} {{result['service']}}")
        print(f"   🌐 URL: {{result['url']}}")
        
        if "error" in result:
            print(f"   ❌ 错误: {{result['error']}}")
        else:
            healthy_count += 1
            if "data" in result and result["data"]:
                # 显示关键信息
                data = result["data"]
                if "version" in data:
                    print(f"   📦 版本: {{data['version']}}")
                if "status" in data:
                    print(f"   📊 状态: {{data['status']}}")
        print()
    
    # 总结
    total_services = len([s for s in services if not s[1].endswith('/docs')])  # 排除文档服务
    core_healthy = sum(1 for r in results[:2] if not isinstance(r, Exception) and "✅" in r.get('status', ''))
    
    print("=" * 50)
    print(f"📊 健康检查总结:")
    print(f"   核心服务: {{core_healthy}}/{{total_services}} 健康")
    print(f"   总体状态: {{'🎉 优秀' if core_healthy == total_services else '⚠️  需要注意' if core_healthy > 0 else '❌ 异常'}}")
    
    if core_healthy == total_services:
        print("\\n🎊 恭喜！所有核心服务运行正常！")
        print("🌐 您可以开始使用系统了:")
        print("   - YuQing舆情分析: http://localhost:8000")
        print("   - RAG+Agent分析: http://localhost:8010")
    elif core_healthy > 0:
        print("\\n⚠️  部分服务可能需要检查，请查看上述错误信息")
    else:
        print("\\n❌ 服务未启动或存在问题，请检查:")
        print("   1. 是否已运行 ./start_local_dev.sh")
        print("   2. 检查端口是否被占用")
        print("   3. 查看日志文件: logs/yuqing/service.log, logs/rag/service.log")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n👋 健康检查已取消")
"""
        
        health_file = self.project_root / "check_health.py"
        with open(health_file, 'w', encoding='utf-8') as f:
            f.write(health_check_content)
        
        if self.platform != "Windows":
            os.chmod(health_file, 0o755)
        
        print(f"  ✅ 健康检查脚本: {health_file}")
        
        return True
    
    def run_setup(self) -> bool:
        """运行完整的开发环境设置"""
        print("🔧 开始设置本地开发环境...")
        print("=" * 60)
        
        setup_steps = [
            ("设置虚拟环境", self.setup_virtual_environment),
            ("安装项目依赖", self.install_dependencies),
            ("创建配置文件", self.create_configuration_files),
            ("初始化数据库", self.create_database_schema),
            ("创建启动脚本", self.create_startup_scripts),
            ("创建健康检查", self.create_health_check_script)
        ]
        
        success_count = 0
        for step_name, step_func in setup_steps:
            try:
                print(f"\\n{'='*20} {{step_name}} {'='*20}")
                if step_func():
                    success_count += 1
                    print(f"✅ {{step_name}} 完成")
                else:
                    print(f"❌ {{step_name}} 失败")
            except Exception as e:
                print(f"❌ {{step_name}} 异常: {{e}}")
        
        # 总结
        print("\\n" + "=" * 60)
        print("📊 本地开发环境设置总结")
        print("=" * 60)
        
        if success_count == len(setup_steps):
            print("🎉 恭喜！本地开发环境设置完成！")
            print("\\n🚀 下一步操作:")
            print("   1. 启动开发服务: ./start_local_dev.sh")
            print("   2. 检查服务状态: python check_health.py")
            print("   3. 访问API文档: http://localhost:8000/docs")
            print("   4. 开始开发调试！")
            print("\\n📁 重要文件:")
            print(f"   - 环境配置: .env.local")
            print(f"   - 启动脚本: start_local_dev.sh")
            print(f"   - 停止脚本: stop_local_dev.sh")
            print(f"   - 健康检查: check_health.py")
            print(f"   - 数据目录: data/")
            print(f"   - 日志目录: logs/")
            
            return True
        else:
            print(f"⚠️  设置完成度: {{success_count}}/{{len(setup_steps)}}")
            print("\\n🔧 需要手动检查和修复的步骤:")
            for i, (step_name, _) in enumerate(setup_steps):
                if i >= success_count:
                    print(f"   - {{step_name}}")
            
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="本地开发环境自动化设置")
    parser.add_argument("--project-root", help="项目根目录路径")
    parser.add_argument("--skip-deps", action="store_true", help="跳过依赖安装")
    
    args = parser.parse_args()
    
    # 运行设置
    setup = LocalDevelopmentSetup(args.project_root)
    
    if args.skip_deps:
        print("⚠️  已跳过依赖安装步骤")
        # 可以添加跳过逻辑
    
    success = setup.run_setup()
    
    if success:
        print("\\n🎊 本地开发环境就绪！重构后的代码完全可以在本地运行！")
        sys.exit(0)
    else:
        print("\\n⚠️  设置过程中遇到一些问题，请查看上述信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
