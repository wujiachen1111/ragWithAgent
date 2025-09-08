#!/usr/bin/env python3
"""
统一服务启动脚本
"""
import asyncio
import subprocess
import sys
from pathlib import Path

async def start_services():
    """启动所有服务"""
    print("🚀 启动集成系统...")
    
    # 检查Docker环境
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        print("✅ Docker环境检查通过")
        
        # 启动Docker Compose
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print("✅ 所有服务已启动")
        
    except subprocess.CalledProcessError:
        print("❌ Docker环境不可用，尝试本地启动...")
        # 本地启动逻辑
        pass

if __name__ == "__main__":
    asyncio.run(start_services())
