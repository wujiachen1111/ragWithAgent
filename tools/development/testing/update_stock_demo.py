#!/usr/bin/env python3
"""
股票数据集成演示脚本
展示如何使用集成的股票数据API进行智能分析
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict, Any

class StockIntegrationDemo:
    """股票数据集成演示类"""
    
    def __init__(self, 
                 decision_engine_url: str = "http://localhost:8000",
                 stock_service_url: str = "http://localhost:8003"):
        self.decision_engine_url = decision_engine_url
        self.stock_service_url = stock_service_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def demo_stock_data_sync(self):
        """演示股票数据同步到向量数据库"""
        print("📊 演示股票数据同步功能")
        print("-" * 50)
        
        # 1. 同步几只热门股票到向量数据库
        popular_stocks = ["600000", "000001", "600036", "000002", "600519"]  # 银行+地产+白酒
        
        print(f"正在同步 {len(popular_stocks)} 只热门股票到向量数据库...")
        
        try:
            response = await self.client.post(
                f"{self.decision_engine_url}/v1/stock/sync",
                json=popular_stocks
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ 同步完成:")
            print(f"   - 同步股票数量: {result.get('stocks_synced', 0)}")
            print(f"   - 生成文档数量: {result.get('documents_created', 0)}")
            print(f"   - 同步时间: {result.get('timestamp', 'N/A')}")
            return True
            
        except Exception as e:
            print(f"❌ 同步失败: {e}")
            return False
    
    async def demo_stock_specific_query(self):
        """演示股票专项查询"""
        print("\n🤖 演示股票专项智能分析")
        print("-" * 50)
        
        stock_queries = [
            "浦发银行最近的表现怎么样？投资价值如何？",
            "请分析一下银行板块的投资机会",
            "贵州茅台的估值水平合理吗？相比其他白酒股如何？",
            "比较一下招商银行和平安银行，哪个更有投资价值？"
        ]
        
        for i, query in enumerate(stock_queries, 1):
            print(f"\n📈 查询 {i}: {query}")
            print("🔍 分析中...")
            
            try:
                response = await self.client.post(
                    f"{self.decision_engine_url}/v1/analyse/stock_query",
                    params={"query": query, "context": "作为专业投资顾问进行分析"}
                )
                response.raise_for_status()
                result = response.json()
                
                print(f"💡 AI分析结果:")
                print(f"{result.get('answer', '分析结果获取失败')}")
                print(f"🕒 分析类型: {result.get('analysis_type', 'N/A')}")
                
            except Exception as e:
                print(f"❌ 查询失败: {e}")
            
            # 等待一下再进行下一个查询
            if i < len(stock_queries):
                print("\n⏳ 等待3秒后继续...")
                await asyncio.sleep(3)
    
    async def demo_traditional_vs_ai_query(self):
        """演示传统RAG vs 股票专项分析的对比"""
        print("\n🔬 演示传统RAG vs 股票专项分析对比")
        print("-" * 50)
        
        test_query = "分析一下浦发银行的投资价值，包括基本面和技术面"
        
        print(f"测试问题: {test_query}")
        print("\n🔹 传统RAG分析:")
        try:
            response = await self.client.post(
                f"{self.decision_engine_url}/v1/analyse/rag_query",
                json={
                    "query": test_query,
                    "user_id": "demo-user",
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"回答: {result.get('answer', '分析失败')}")
            print(f"参考来源: {len(result.get('sources', []))} 个文档")
            
        except Exception as e:
            print(f"❌ 传统RAG查询失败: {e}")
        
        print("\n🔹 股票专项分析:")
        try:
            response = await self.client.post(
                f"{self.decision_engine_url}/v1/analyse/stock_query",
                params={"query": test_query}
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"回答: {result.get('answer', '分析失败')}")
            print(f"分析类型: {result.get('analysis_type', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 股票专项查询失败: {e}")
    
    async def demo_direct_stock_api(self):
        """演示直接调用股票数据API"""
        print("\n📡 演示股票数据API调用")
        print("-" * 50)
        
        # 1. 搜索股票
        print("1. 搜索股票 '银行':")
        try:
            response = await self.client.get(
                f"{self.stock_service_url}/v1/stocks/search",
                params={"query": "银行", "per_page": 3}
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"找到 {result.get('total', 0)} 只相关股票:")
            for stock in result.get('data', [])[:3]:
                print(f"  - {stock['stock_name']} ({stock['stock_code']}): {stock['latest_price']} 元")
                
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
        
        # 2. 获取股票详细信息
        print("\n2. 获取浦发银行详细信息:")
        try:
            response = await self.client.get(f"{self.stock_service_url}/v1/stocks/600000/summary")
            response.raise_for_status()
            result = response.json()
            
            basic_info = result['basic_info']
            latest_kline = result['latest_kline']
            
            print(f"  股票名称: {basic_info['stock_name']}")
            print(f"  当前价格: {basic_info['latest_price']} 元") 
            print(f"  市盈率: {basic_info.get('pe_ttm', 'N/A')}")
            print(f"  市净率: {basic_info.get('pb', 'N/A')}")
            print(f"  总市值: {basic_info.get('total_market_cap', 'N/A')} 亿元")
            print(f"  最新涨跌幅: {latest_kline.get('change_pct', 'N/A')}%")
            
        except Exception as e:
            print(f"❌ 获取详情失败: {e}")
        
        # 3. 股票分析
        print("\n3. 多股票综合分析:")
        try:
            response = await self.client.post(
                f"{self.stock_service_url}/v1/stocks/analyze",
                json={
                    "stock_codes": ["600000", "000001", "600036"],
                    "analysis_type": "comprehensive",
                    "time_range": "1m"
                }
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"分析结果:")
            for analysis in result.get('results', []):
                if 'error' not in analysis:
                    print(f"  - {analysis['stock_name']}: {analysis['technical_trend']}")
                    print(f"    当前价格: {analysis['current_price']} 元")
                else:
                    print(f"  - {analysis['stock_code']}: 分析失败 - {analysis['error']}")
                    
        except Exception as e:
            print(f"❌ 分析失败: {e}")
    
    async def run_complete_demo(self):
        """运行完整演示"""
        print("🚀 智策股票数据集成功能演示")
        print("=" * 60)
        
        # 检查服务状态
        print("🔍 检查服务状态...")
        services = [
            ("决策引擎", self.decision_engine_url),
            ("股票数据服务", self.stock_service_url)
        ]
        
        for service_name, url in services:
            try:
                response = await self.client.get(url)
                if response.status_code == 200:
                    print(f"✅ {service_name} 运行正常")
                else:
                    print(f"⚠️ {service_name} 状态异常: {response.status_code}")
                    return
            except Exception as e:
                print(f"❌ {service_name} 连接失败: {e}")
                return
        
        print("\n" + "=" * 60)
        
        # 运行各个演示模块
        await self.demo_stock_data_sync()
        await self.demo_direct_stock_api() 
        await self.demo_stock_specific_query()
        await self.demo_traditional_vs_ai_query()
        
        print("\n" + "=" * 60)
        print("✨ 演示完成！股票数据已成功集成到RAG+Agent系统")
        print("\n📋 功能总结:")
        print("1. ✅ 股票数据API集成 - 支持搜索、详情、K线等功能")
        print("2. ✅ 智能数据同步 - 自动将股票数据转换为RAG文档")
        print("3. ✅ 专项分析Agent - 基于股票数据的专业分析")
        print("4. ✅ 混合RAG系统 - 结合舆情和股票数据的综合分析")
        
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

async def main():
    """主函数"""
    demo = StockIntegrationDemo()
    
    try:
        await demo.run_complete_demo()
    except KeyboardInterrupt:
        print("\n👋 演示被用户中断")
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
    finally:
        await demo.close()

if __name__ == "__main__":
    print("🎯 启动股票数据集成演示...")
    asyncio.run(main())
