#!/usr/bin/env python3
"""
系统健康检查脚本
快速验证所有服务是否正常运行
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any
from datetime import datetime

class SystemHealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self.services = {
            "决策引擎": "http://localhost:8000",
            "嵌入服务": "http://localhost:8001", 
            "LLM网关": "http://localhost:8002",
            "股票数据服务": "http://localhost:8003"
        }
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def check_service(self, name: str, url: str) -> Dict[str, Any]:
        """检查单个服务状态"""
        try:
            response = await self.client.get(url)
            status = "✅ 正常" if response.status_code == 200 else f"⚠️ 异常 ({response.status_code})"
            
            # 尝试解析响应详情
            try:
                details = response.json()
                service_info = details.get('service', 'unknown')
                extra_info = ""
                
                if name == "LLM网关":
                    providers = details.get('providers', [])
                    cache_enabled = details.get('cache_enabled', False)
                    extra_info = f"供应商: {len(providers)}, 缓存: {'开启' if cache_enabled else '关闭'}"
                
                elif name == "决策引擎":
                    db_connected = details.get('database_connected', False)
                    vector_store = details.get('vector_store_initialized', False)
                    extra_info = f"数据库: {'连接' if db_connected else '断开'}, 向量库: {'就绪' if vector_store else '未就绪'}"
                
                elif name == "嵌入服务":
                    model_loaded = details.get('model_loaded', False)
                    device = details.get('device', 'unknown')
                    extra_info = f"模型: {'已加载' if model_loaded else '未加载'}, 设备: {device}"
                
                return {
                    "name": name,
                    "status": status,
                    "url": url,
                    "service": service_info,
                    "extra_info": extra_info,
                    "response_time": response.elapsed.total_seconds()
                }
                
            except json.JSONDecodeError:
                return {
                    "name": name,
                    "status": status,
                    "url": url,
                    "service": "unknown",
                    "extra_info": "响应格式异常",
                    "response_time": response.elapsed.total_seconds()
                }
                
        except httpx.ConnectError:
            return {
                "name": name,
                "status": "❌ 无法连接",
                "url": url,
                "service": "offline",
                "extra_info": "服务未启动或端口不可达",
                "response_time": 0
            }
        except httpx.TimeoutException:
            return {
                "name": name,
                "status": "⏱️ 超时",
                "url": url,
                "service": "timeout",
                "extra_info": "请求超时(>10s)",
                "response_time": 10
            }
        except Exception as e:
            return {
                "name": name,
                "status": f"❌ 错误",
                "url": url,
                "service": "error",
                "extra_info": str(e)[:50],
                "response_time": 0
            }
    
    async def check_api_functionality(self) -> Dict[str, Any]:
        """检查API功能性"""
        functionality_results = {}
        
        # 测试RAG查询
        try:
            response = await self.client.post(
                "http://localhost:8000/v1/analyse/rag_query",
                json={
                    "query": "系统测试查询",
                    "user_id": "health-check", 
                    "temperature": 0.5
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                functionality_results["RAG查询"] = "✅ 正常"
            else:
                functionality_results["RAG查询"] = f"⚠️ 异常 ({response.status_code})"
                
        except Exception as e:
            functionality_results["RAG查询"] = f"❌ 失败: {str(e)[:30]}"
        
        # 测试股票数据服务
        try:
            response = await self.client.get(
                "http://localhost:8003/v1/stocks/search",
                params={"query": "银行", "per_page": 1}
            )
            
            if response.status_code == 200:
                functionality_results["股票数据"] = "✅ 正常"
            else:
                functionality_results["股票数据"] = f"⚠️ 异常 ({response.status_code})"
                
        except Exception as e:
            functionality_results["股票数据"] = f"❌ 失败: {str(e)[:30]}"
        
        return functionality_results
    
    async def run_health_check(self) -> Dict[str, Any]:
        """运行完整的健康检查"""
        print("🔍 开始系统健康检查...")
        print("=" * 60)
        
        # 检查所有服务状态
        service_results = []
        for name, url in self.services.items():
            result = await self.check_service(name, url)
            service_results.append(result)
            
            print(f"{result['status']} {name} ({url})")
            if result['extra_info']:
                print(f"   {result['extra_info']}")
            print(f"   响应时间: {result['response_time']:.2f}s")
            print()
        
        # 统计健康状态
        healthy_services = len([r for r in service_results if "✅" in r['status']])
        total_services = len(service_results)
        
        print("=" * 60)
        print(f"📊 服务状态汇总: {healthy_services}/{total_services} 服务正常运行")
        
        # 如果所有服务都正常，测试API功能
        if healthy_services == total_services:
            print("\n🚀 所有服务正常，测试API功能...")
            print("-" * 40)
            
            functionality_results = await self.check_api_functionality()
            for func_name, status in functionality_results.items():
                print(f"{status} {func_name}")
            
            working_apis = len([r for r in functionality_results.values() if "✅" in r])
            total_apis = len(functionality_results)
            print(f"\n📈 API功能: {working_apis}/{total_apis} 接口正常工作")
            
        else:
            print("\n⚠️ 部分服务异常，请检查服务启动状态")
            
        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy" if healthy_services == total_services else "partial",
            "services": service_results,
            "summary": {
                "healthy_services": healthy_services,
                "total_services": total_services,
                "health_rate": f"{(healthy_services/total_services)*100:.1f}%"
            }
        }
        
        if healthy_services == total_services:
            functionality_results = await self.check_api_functionality()
            working_apis = len([r for r in functionality_results.values() if "✅" in r])
            total_apis = len(functionality_results)
            
            report["functionality"] = functionality_results
            report["summary"]["api_health_rate"] = f"{(working_apis/total_apis)*100:.1f}%"
        
        print("\n" + "=" * 60)
        if healthy_services == total_services:
            print("✨ 系统健康检查完成 - 所有服务运行正常！")
        else:
            print("⚠️ 系统健康检查完成 - 发现异常服务，请检查")
            
        return report
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

async def main():
    """主函数"""
    checker = SystemHealthChecker()
    
    try:
        report = await checker.run_health_check()
        
        # 保存检查报告
        with open("health_check_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: health_check_report.json")
        
        # 返回退出码
        if report["overall_status"] == "healthy":
            exit(0)  # 成功
        else:
            exit(1)  # 异常
            
    except KeyboardInterrupt:
        print("\n👋 健康检查被用户中断")
    except Exception as e:
        print(f"❌ 健康检查过程中发生错误: {e}")
    finally:
        await checker.close()

if __name__ == "__main__":
    print("🎯 智策系统健康检查工具")
    asyncio.run(main())
