#!/usr/bin/env python3
"""
统一服务停止脚本
"""

import argparse
import subprocess
import os
import signal
import sys
import psutil
from pathlib import Path


def find_service_processes():
    """查找服务进程"""
    service_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and len(cmdline) > 1:
                # 查找舆情分析服务
                if 'python' in cmdline[0] and 'src.main' in ' '.join(cmdline) and 'yuqing-sentiment' in ' '.join(cmdline):
                    service_processes.append(('yuqing', proc.info['pid']))
                
                # 查找RAG分析服务
                elif 'python' in cmdline[0] and 'src.main' in ' '.join(cmdline) and 'rag-analysis' in ' '.join(cmdline):
                    service_processes.append(('rag', proc.info['pid']))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return service_processes


def stop_docker_services():
    """停止Docker服务"""
    project_root = Path(__file__).parent
    subprocess.run(["docker-compose", "down"], cwd=project_root)
    print("已停止所有Docker服务")


def stop_local_services(services=None):
    """停止本地服务"""
    service_processes = find_service_processes()
    
    if not service_processes:
        print("未找到正在运行的服务进程")
        return
    
    for service_name, pid in service_processes:
        if services is None or service_name in services:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"已停止{service_name}服务 (PID: {pid})")
            except OSError as e:
                print(f"停止{service_name}服务失败: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="服务停止管理器")
    parser.add_argument("--env", choices=["development", "docker", "production"], 
                       default="development", help="运行环境")
    parser.add_argument("--services", nargs="*", help="指定停止的服务")
    
    args = parser.parse_args()
    
    if args.env == "docker":
        stop_docker_services()
    else:
        stop_local_services(args.services)

