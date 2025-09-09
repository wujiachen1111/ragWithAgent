"""
RAG-Analysis 系统集成测试
"""

import asyncio
import httpx
import json
from typing import Dict, Any


class RAGIntegrationTester:
    """RAG 集成测试器"""
    
    def __init__(self):
        self.stock_agent_url = "http://localhost:8020"
        self.rag_analysis_url = "http://localhost:8010"
        
    async def test_stock_agent_health(self) -> Dict[str, Any]:
        """测试 Stock Agent 健康状态"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.stock_agent_url}/api/v1/stocks/health")
                return {
                    "service": "stock-agent",
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response": response.json() if response.status_code == 200 else None,
                    "error": None
                }
        except Exception as e:
            return {
                "service": "stock-agent",
                "status": "error",
                "response": None,
                "error": str(e)
            }
    
    async def test_rag_analysis_health(self) -> Dict[str, Any]:
        """测试 RAG Analysis 健康状态"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.rag_analysis_url}/meta")
                return {
                    "service": "rag-analysis",
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response": response.json() if response.status_code == 200 else None,
                    "error": None
                }
        except Exception as e:
            return {
                "service": "rag-analysis",
                "status": "error",
                "response": None,
                "error": str(e)
            }
    
    async def test_stock_data_retrieval(self) -> Dict[str, Any]:
        """测试股票数据获取"""
        try:
            async with httpx.AsyncClient() as client:
                # 测试获取股票列表
                response = await client.get(
                    f"{self.stock_agent_url}/api/v1/stocks/",
                    params={"industries": ["银行"], "limit": 5}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "test": "stock_data_retrieval",
                        "status": "success",
                        "data_count": len(data.get("data", [])),
                        "sample_data": data.get("data", [])[:2] if data.get("data") else None,
                        "error": None
                    }
                else:
                    return {
                        "test": "stock_data_retrieval",
                        "status": "failed",
                        "error": f"HTTP {response.status_code}"
                    }
        except Exception as e:
            return {
                "test": "stock_data_retrieval",
                "status": "error",
                "error": str(e)
            }
    
    async def test_rag_market_context(self) -> Dict[str, Any]:
        """测试 RAG 市场上下文接口"""
        try:
            async with httpx.AsyncClient() as client:
                # 测试市场上下文接口
                payload = {
                    "symbols": ["000001", "600036"],
                    "time_horizon": "medium"
                }
                
                response = await client.post(
                    f"{self.stock_agent_url}/api/v1/rag/market-context",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "test": "rag_market_context",
                        "status": "success",
                        "symbols_count": len(payload["symbols"]),
                        "data_available": "data" in data and len(data["data"]) > 0,
                        "error": None
                    }
                else:
                    return {
                        "test": "rag_market_context",
                        "status": "failed",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            return {
                "test": "rag_market_context",
                "status": "error",
                "error": str(e)
            }
    
    async def test_sector_analysis(self) -> Dict[str, Any]:
        """测试行业分析接口"""
        try:
            async with httpx.AsyncClient() as client:
                # 测试行业分析接口
                payload = {
                    "industry": "银行",
                    "limit": 10
                }
                
                response = await client.post(
                    f"{self.stock_agent_url}/api/v1/rag/sector-analysis",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "test": "sector_analysis",
                        "status": "success",
                        "industry": payload["industry"],
                        "companies_found": data.get("data", {}).get("total_companies", 0),
                        "error": None
                    }
                else:
                    return {
                        "test": "sector_analysis",
                        "status": "failed",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            return {
                "test": "sector_analysis",
                "status": "error",
                "error": str(e)
            }
    
    async def test_comparative_analysis(self) -> Dict[str, Any]:
        """测试对比分析接口"""
        try:
            async with httpx.AsyncClient() as client:
                # 测试对比分析接口
                payload = {
                    "symbols": ["000001", "600036", "000002"]
                }
                
                response = await client.post(
                    f"{self.stock_agent_url}/api/v1/rag/comparative-analysis",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "test": "comparative_analysis",
                        "status": "success",
                        "symbols_count": len(payload["symbols"]),
                        "comparison_available": "comparison" in data.get("data", {}),
                        "ranking_available": "ranking" in data.get("data", {}),
                        "error": None
                    }
                else:
                    return {
                        "test": "comparative_analysis",
                        "status": "failed",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            return {
                "test": "comparative_analysis",
                "status": "error",
                "error": str(e)
            }
    
    async def test_rag_integration_endpoint(self) -> Dict[str, Any]:
        """测试 RAG 集成测试端点"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.stock_agent_url}/api/v1/rag/integration/test")
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "test": "rag_integration_test",
                        "status": "success",
                        "integration_status": data.get("data", {}).get("integration_status"),
                        "all_tests_passed": data.get("success", False),
                        "error": None
                    }
                else:
                    return {
                        "test": "rag_integration_test",
                        "status": "failed",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
        except Exception as e:
            return {
                "test": "rag_integration_test",
                "status": "error",
                "error": str(e)
            }
    
    async def simulate_rag_workflow(self) -> Dict[str, Any]:
        """模拟 RAG-Analysis 工作流程"""
        try:
            workflow_results = {
                "workflow": "rag_analysis_simulation",
                "steps": [],
                "overall_status": "success"
            }
            
            async with httpx.AsyncClient() as client:
                # 步骤1: 获取市场上下文
                market_context = await client.post(
                    f"{self.stock_agent_url}/api/v1/rag/market-context",
                    json={"symbols": ["000001", "600036"], "time_horizon": "medium"}
                )
                
                step1_result = {
                    "step": 1,
                    "name": "market_context_retrieval",
                    "status": "success" if market_context.status_code == 200 else "failed",
                    "data_available": market_context.status_code == 200
                }
                workflow_results["steps"].append(step1_result)
                
                # 步骤2: 获取行业分析
                sector_analysis = await client.post(
                    f"{self.stock_agent_url}/api/v1/rag/sector-analysis",
                    json={"industry": "银行", "limit": 5}
                )
                
                step2_result = {
                    "step": 2,
                    "name": "sector_analysis",
                    "status": "success" if sector_analysis.status_code == 200 else "failed",
                    "data_available": sector_analysis.status_code == 200
                }
                workflow_results["steps"].append(step2_result)
                
                # 步骤3: 获取对比分析
                comparative = await client.post(
                    f"{self.stock_agent_url}/api/v1/rag/comparative-analysis",
                    json={"symbols": ["000001", "600036"]}
                )
                
                step3_result = {
                    "step": 3,
                    "name": "comparative_analysis",
                    "status": "success" if comparative.status_code == 200 else "failed",
                    "data_available": comparative.status_code == 200
                }
                workflow_results["steps"].append(step3_result)
                
                # 检查整体状态
                failed_steps = [s for s in workflow_results["steps"] if s["status"] != "success"]
                if failed_steps:
                    workflow_results["overall_status"] = "partial_failure"
                    workflow_results["failed_steps"] = len(failed_steps)
                
                return workflow_results
                
        except Exception as e:
            return {
                "workflow": "rag_analysis_simulation",
                "overall_status": "error",
                "error": str(e)
            }
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """运行完整测试套件"""
        print("🚀 开始 RAG-Analysis 与 Stock-Agent 集成测试...")
        
        test_results = {
            "timestamp": asyncio.get_event_loop().time(),
            "tests": []
        }
        
        # 测试列表
        tests = [
            ("Stock Agent 健康检查", self.test_stock_agent_health),
            ("RAG Analysis 健康检查", self.test_rag_analysis_health),
            ("股票数据获取测试", self.test_stock_data_retrieval),
            ("RAG 市场上下文测试", self.test_rag_market_context),
            ("行业分析测试", self.test_sector_analysis),
            ("对比分析测试", self.test_comparative_analysis),
            ("RAG 集成端点测试", self.test_rag_integration_endpoint),
            ("RAG 工作流模拟", self.simulate_rag_workflow)
        ]
        
        # 运行所有测试
        for test_name, test_func in tests:
            print(f"  📋 运行测试: {test_name}")
            result = await test_func()
            result["test_name"] = test_name
            test_results["tests"].append(result)
            
            # 打印结果
            status_emoji = "✅" if result.get("status") == "success" else "❌"
            print(f"    {status_emoji} {test_name}: {result.get('status', 'unknown')}")
            if result.get("error"):
                print(f"      错误: {result['error']}")
        
        # 统计结果
        successful_tests = [t for t in test_results["tests"] if t.get("status") == "success"]
        failed_tests = [t for t in test_results["tests"] if t.get("status") in ["failed", "error"]]
        
        test_results["summary"] = {
            "total_tests": len(tests),
            "successful": len(successful_tests),
            "failed": len(failed_tests),
            "success_rate": len(successful_tests) / len(tests) * 100
        }
        
        print(f"\n📊 测试结果汇总:")
        print(f"  总测试数: {test_results['summary']['total_tests']}")
        print(f"  成功: {test_results['summary']['successful']}")
        print(f"  失败: {test_results['summary']['failed']}")
        print(f"  成功率: {test_results['summary']['success_rate']:.1f}%")
        
        return test_results


async def main():
    """主函数"""
    tester = RAGIntegrationTester()
    results = await tester.run_full_test_suite()
    
    # 保存结果到文件
    with open("rag_integration_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 测试结果已保存到 rag_integration_test_results.json")
    
    # 返回整体状态
    if results["summary"]["success_rate"] >= 80:
        print("🎉 集成测试通过! RAG-Analysis 和 Stock-Agent 可以正常协作")
        return True
    else:
        print("⚠️  集成测试未完全通过，请检查失败的测试项")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())

