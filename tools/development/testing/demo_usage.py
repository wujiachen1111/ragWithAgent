#!/usr/bin/env python3
"""
智策 (InsightFolio) 系统演示脚本
展示如何使用系统的核心功能进行股票舆情分析
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict, Any

class InsightFolioDemo:
    """智策系统演示类"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def add_sample_documents(self) -> Dict[str, Any]:
        """添加示例文档到系统"""
        print("📄 正在添加示例股票舆情文档...")
        
        sample_documents = [
            {
                "id": "news-001",
                "title": "苹果公司发布Q4财报：iPhone销售超预期",
                "content": """
                苹果公司今日发布2024年第四季度财报，营收达到946亿美元，同比增长6%，超出分析师预期。
                iPhone销售额为468亿美元，同比增长5%，主要受益于iPhone 15系列的强劲需求。
                CEO蒂姆·库克表示，公司在人工智能领域的投入正在显现成效，Apple Intelligence功能获得用户积极反响。
                分析师普遍认为，苹果在AI领域的布局将为其未来增长提供新动力。
                """,
                "source": "财经新闻",
                "url": "https://example.com/apple-q4-2024",
                "timestamp": "2024-01-15T10:30:00Z"
            },
            {
                "id": "news-002", 
                "title": "特斯拉股价大涨：自动驾驶技术获得重大突破",
                "content": """
                特斯拉股价今日上涨8%，收于$248.50，创下近期新高。
                公司宣布其完全自动驾驶(FSD)技术在最新测试中表现优异，事故率较人类驾驶员降低90%。
                马斯克在社交媒体上表示，FSD技术预计将在2024年底前实现真正的完全自动驾驶。
                华尔街分析师纷纷上调特斯拉目标价，认为自动驾驶技术将彻底改变公司的商业模式。
                投资者对特斯拉的技术领先优势表示乐观，预期未来将有更多积极消息。
                """,
                "source": "科技新闻",
                "url": "https://example.com/tesla-fsd-breakthrough",
                "timestamp": "2024-01-16T14:20:00Z"
            },
            {
                "id": "analysis-001",
                "title": "2024年科技股投资前景分析报告",
                "content": """
                根据最新市场分析，2024年科技股整体表现有望超越大盘。
                人工智能、自动驾驶、云计算等领域预计将迎来爆发式增长。
                
                重点关注股票：
                1. 苹果(AAPL)：AI功能普及带动iPhone升级周期
                2. 特斯拉(TSLA)：自动驾驶技术商业化在即
                3. 微软(MSFT)：OpenAI合作深化，AI服务营收增长
                4. 英伟达(NVDA)：AI芯片需求持续旺盛
                
                风险因素：监管政策变化、地缘政治紧张局势、宏观经济波动
                投资建议：适度配置，关注长期价值，注意风险控制
                """,
                "source": "投资研究",
                "url": "https://example.com/tech-stocks-2024-outlook", 
                "timestamp": "2024-01-10T09:00:00Z"
            }
        ]
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/documents/add",
                json=sample_documents
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ 成功添加 {result['documents_added']} 个文档，生成 {result['chunks_created']} 个文档块")
            return result
            
        except Exception as e:
            print(f"❌ 添加文档失败: {e}")
            return {}
    
    async def query_rag_system(self, query: str, user_id: str = "demo-user") -> Dict[str, Any]:
        """查询RAG系统"""
        print(f"🤖 正在查询: {query}")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/analyse/rag_query",
                json={
                    "query": query,
                    "user_id": user_id,
                    "temperature": 0.7,
                    "context_limit": 5
                }
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"\n💡 AI回答:")
            print(f"{result['answer']}")
            
            print(f"\n📚 参考来源 ({len(result['sources'])}个):")
            for i, source in enumerate(result['sources'], 1):
                print(f"{i}. {source['title']}")
                print(f"   摘要: {source['snippet'][:100]}...")
                if source.get('url'):
                    print(f"   链接: {source['url']}")
                print()
            
            return result
            
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return {}
    
    async def demo_conversation_flow(self):
        """演示完整的对话流程"""
        print("🎯 开始智策系统演示")
        print("=" * 60)
        
        # 1. 添加示例文档
        await self.add_sample_documents()
        print("\n" + "=" * 60)
        
        # 2. 进行多轮RAG查询
        queries = [
            "苹果公司最近的财务表现如何？有什么值得关注的亮点？",
            "特斯拉的自动驾驶技术发展怎么样？对股价有什么影响？", 
            "2024年科技股的投资机会在哪里？应该注意哪些风险？",
            "综合最近的消息，你认为科技股的整体趋势如何？"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n🔍 第{i}轮查询:")
            print("-" * 40)
            await self.query_rag_system(query)
            
            if i < len(queries):
                print("\n⏳ 等待3秒后继续...")
                await asyncio.sleep(3)
        
        print("\n" + "=" * 60)
        print("✨ 演示完成！智策系统成功进行了智能股票舆情分析")
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

async def main():
    """主函数"""
    demo = InsightFolioDemo()
    
    try:
        # 检查服务健康状态
        print("🔍 检查系统健康状态...")
        response = await demo.client.get("http://localhost:8000/")
        if response.status_code != 200:
            print("❌ 智能决策服务未启动，请先运行 'honcho start'")
            return
        
        response = await demo.client.get("http://localhost:8001/")
        if response.status_code != 200:
            print("❌ 嵌入服务未启动，请检查服务状态")
            return
            
        response = await demo.client.get("http://localhost:8002/")
        if response.status_code != 200:
            print("❌ LLM网关未启动，请检查服务状态和DeepSeek API配置")
            return
        
        print("✅ 所有服务运行正常，开始演示...")
        print()
        
        # 运行演示
        await demo.demo_conversation_flow()
        
    except KeyboardInterrupt:
        print("\n👋 演示被用户中断")
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
    finally:
        await demo.close()

if __name__ == "__main__":
    print("🚀 智策 (InsightFolio) 系统演示")
    print("基于RAG+Agent的股票舆情分析平台")
    print("=" * 60)
    asyncio.run(main())
