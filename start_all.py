#!/usr/bin/env python3
"""
统一服务启动脚本
支持开发环境、Docker环境、生产环境
"""

import argparse
import asyncio
import subprocess
import os
from pathlib import Path
import sys


class ServiceManager:
    def __init__(self, environment="development"):
        self.environment = environment
        self.project_root = Path(__file__).parent
        
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
        """本地启动服务"""
        available_services = {
            "yuqing": self._start_yuqing_service,
            "rag": self._start_rag_service
        }
        
        if not services:
            services = available_services.keys()
            
        tasks = []
        for service in services:
            if service in available_services:
                tasks.append(available_services[service]())
        
        await asyncio.gather(*tasks)
        
    async def _start_yuqing_service(self):
        """启动舆情分析服务"""
        print("正在启动舆情分析服务...")
        service_dir = self.project_root / "apps" / "yuqing-sentiment"
        os.chdir(service_dir)
        # 计算本地SQLite路径
        sqlite_path = (self.project_root / "data" / "yuqing" / "yuqing.db").resolve()
        env = {
            **os.environ, 
            "HOST": "0.0.0.0", 
            "PORT": "8000",
            "CHROMA_PERSIST_DIRECTORY": str(self.project_root / "data" / "yuqing" / "chromadb"),
            # 使用本地SQLite，避免未启动Postgres导致失败
            "DATABASE_URL": f"sqlite:///{sqlite_path}",
            # 使用本机Redis（可通过docker-compose启动）
            "REDIS_URL": "redis://localhost:6379/0",
            # 确保可导入 src 下的包
            "PYTHONPATH": f"{service_dir / 'src'}:{self.project_root}"
        }
        subprocess.Popen([sys.executable, "-m", "src.main"], env=env)
        
    async def _start_rag_service(self):
        """启动RAG分析服务"""
        print("正在启动RAG分析服务...")
        service_dir = self.project_root / "apps" / "rag-analysis"
        os.chdir(service_dir)
        env = {
            **os.environ, 
            "HOST": "0.0.0.0", 
            "PORT": "8010",
            "YUQING_API_URL": "http://localhost:8000",
            "SENTIMENT_API_URL": "http://localhost:8000",
            # 确保可导入 src 下的包
            "PYTHONPATH": f"{service_dir / 'src'}:{self.project_root}"
        }
        subprocess.Popen([sys.executable, "-m", "src.main"], env=env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="服务启动管理器")
    parser.add_argument("--env", choices=["development", "docker", "production"], 
                       default="development", help="运行环境")
    parser.add_argument("--services", nargs="*", help="指定启动的服务")
    
    args = parser.parse_args()
    
    manager = ServiceManager(args.env)
    asyncio.run(manager.start_services(args.services))
