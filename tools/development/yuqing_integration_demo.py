"""
YuQing-new与RAG+Agent系统集成演示
展示如何使用YuQing-new的舆情数据进行智能投资分析
"""

import asyncio
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os
import sys

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# 设置环境变量
os.environ["YUQING_API_URL"] = "http://localhost:8000"
os.environ["LLM_GATEWAY_URL"] = "http://localhost:8002/v1/chat/completions"


async def test_yuqing_api_connectivity():
    """测试YuQing-new API连通性"""
    print("🔍 测试YuQing-new API连通性...")
    
    yuqing_base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 1. 健康检查
            health_response = await client.get(f"{yuqing_base_url}/health")
            health_data = health_response.json()
            print(f"✅ 系统健康状态: {health_data.get('status')}")
            
            # 2. 获取系统统计
            stats_response = await client.get(f"{yuqing_base_url}/api/news/stats?hours=24")
            stats_data = stats_response.json()
            print(f"📊 系统统计: {stats_data.get('total_news')}条新闻，{stats_data.get('recent_24h')}条最近24小时")
            
            # 3. 测试综合数据API
            comprehensive_response = await client.get(
                f"{yuqing_base_url}/api/news/comprehensive",
                params={"hours": 6, "limit": 5, "include_entities": True}
            )
            comprehensive_data = comprehensive_response.json()
            print(f"🔍 综合数据API: 获取到{comprehensive_data.get('summary', {}).get('total_analyzed', 0)}条已分析新闻")
            
            # 4. 测试实体分析API
            companies_response = await client.get(
                f"{yuqing_base_url}/api/entities/companies",
                params={"limit": 10}
            )
            companies_data = companies_response.json()
            print(f"🏢 公司实体API: 获取到{len(companies_data.get('data', []))}个公司实体")
            
            return True
            
        except Exception as e:
            print(f"❌ YuQing-new连接失败: {e}")
            return False


async def demo_yuqing_comprehensive_analysis():
    """演示YuQing-new综合分析功能"""
    print("\n🎯 演示YuQing-new综合分析功能...")
    
    yuqing_base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 获取最近24小时的综合数据
            response = await client.get(
                f"{yuqing_base_url}/api/news/comprehensive",
                params={
                    "hours": 24,
                    "limit": 10,
                    "include_entities": True,
                    "include_raw_data": False
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            print(f"📈 数据概览:")
            summary = data.get("summary", {})
            print(f"  - 已分析新闻: {summary.get('total_analyzed', 0)}条")
            print(f"  - 时间范围: {summary.get('time_range_hours', 0)}小时")
            print(f"  - 实体统计: {summary.get('entity_counts', {})}")
            
            # 分析情感分布
            sentiment_distribution = {"positive": 0, "negative": 0, "neutral": 0}
            impact_levels = {"high": 0, "medium": 0, "low": 0}
            
            print(f"\n📰 新闻分析详情:")
            for i, item in enumerate(data.get("data", [])[:5], 1):
                news = item.get("news", {})
                sentiment = item.get("sentiment_analysis", {})
                entities = item.get("entity_analysis", {})
                
                print(f"\n  {i}. {news.get('title', 'N/A')[:80]}...")
                print(f"     📊 情感: {sentiment.get('sentiment_label', 'N/A')} (置信度: {sentiment.get('confidence_score', 0):.2f})")
                print(f"     🎯 市场影响: {sentiment.get('market_impact_level', 'N/A')}")
                print(f"     🏢 相关公司: {len(entities.get('companies', []))}个")
                print(f"     🏭 相关行业: {len(entities.get('industries', []))}个")
                
                # 统计
                sentiment_label = sentiment.get('sentiment_label', 'neutral')
                sentiment_distribution[sentiment_label] += 1
                
                impact_level = sentiment.get('market_impact_level', 'medium')
                if impact_level in impact_levels:
                    impact_levels[impact_level] += 1
            
            print(f"\n📊 情感分布统计:")
            total = sum(sentiment_distribution.values())
            if total > 0:
                for sentiment, count in sentiment_distribution.items():
                    percentage = (count / total) * 100
                    print(f"  - {sentiment}: {count}条 ({percentage:.1f}%)")
            
            print(f"\n🎯 影响级别统计:")
            total_impact = sum(impact_levels.values())
            if total_impact > 0:
                for level, count in impact_levels.items():
                    percentage = (count / total_impact) * 100
                    print(f"  - {level}: {count}条 ({percentage:.1f}%)")
            
            return data
            
        except Exception as e:
            print(f"❌ 综合分析演示失败: {e}")
            return None


async def demo_stock_specific_analysis(stock_codes: List[str] = ["000001", "600036"]):
    """演示特定股票的舆情分析"""
    print(f"\n🎯 演示股票 {stock_codes} 的舆情分析...")
    
    yuqing_base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. 获取公司实体数据
            companies_response = await client.get(
                f"{yuqing_base_url}/api/entities/companies",
                params={"limit": 100}
            )
            companies_data = companies_response.json()
            
            # 查找目标股票相关的公司
            target_companies = []
            for company in companies_data.get("data", []):
                stock_code = company.get("stock_code", "")
                if any(code in str(stock_code) for code in stock_codes):
                    target_companies.append(company)
            
            print(f"🏢 找到相关公司: {len(target_companies)}个")
            for company in target_companies[:3]:
                print(f"  - {company.get('company_name', 'N/A')} ({company.get('stock_code', 'N/A')})")
                print(f"    影响: {company.get('impact_direction', 'N/A')} | 强度: {company.get('impact_magnitude', 0):.2f}")
            
            # 2. 获取相关新闻
            news_response = await client.get(
                f"{yuqing_base_url}/api/news/comprehensive",
                params={"hours": 24, "limit": 50, "include_entities": True}
            )
            news_data = news_response.json()
            
            # 过滤相关新闻
            relevant_news = []
            for news_item in news_data.get("data", []):
                entity_analysis = news_item.get("entity_analysis", {})
                companies_in_news = entity_analysis.get("companies", [])
                
                for company in companies_in_news:
                    if any(code in str(company.get("stock_code", "")) for code in stock_codes):
                        relevant_news.append(news_item)
                        break
            
            print(f"\n📰 相关新闻: {len(relevant_news)}条")
            
            # 分析相关新闻的情感趋势
            sentiment_scores = []
            for news in relevant_news[:5]:
                sentiment = news.get("sentiment_analysis", {})
                news_title = news.get("news", {}).get("title", "N/A")
                sentiment_label = sentiment.get("sentiment_label", "neutral")
                confidence = sentiment.get("confidence_score", 0)
                
                print(f"  📄 {news_title[:60]}...")
                print(f"     情感: {sentiment_label} (置信度: {confidence:.2f})")
                
                # 转换情感为数值
                sentiment_score = {"positive": 1, "negative": -1, "neutral": 0}.get(sentiment_label, 0)
                sentiment_scores.append(sentiment_score)
            
            # 计算整体情感
            if sentiment_scores:
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                sentiment_trend = "看涨" if avg_sentiment > 0.2 else "看跌" if avg_sentiment < -0.2 else "中性"
                print(f"\n📊 整体情感趋势: {sentiment_trend} (平均分: {avg_sentiment:.2f})")
            
            return {
                "target_companies": target_companies,
                "relevant_news": relevant_news,
                "sentiment_analysis": {
                    "average_sentiment": avg_sentiment if sentiment_scores else 0,
                    "sentiment_trend": sentiment_trend if sentiment_scores else "无数据",
                    "total_relevant_news": len(relevant_news)
                }
            }
            
        except Exception as e:
            print(f"❌ 股票分析演示失败: {e}")
            return None


async def demo_integrated_rag_agent_analysis():
    """演示完整的RAG+Agent投资分析流程"""
    print(f"\n🚀 演示完整的RAG+Agent投资分析流程...")
    
    # 模拟市场事件
    market_event = {
        "topic": "某科技公司发布AI新产品",
        "headline": "革命性AI产品引发市场热议，相关概念股或受益",
        "content": """
        今日，某知名科技公司正式发布了其最新一代人工智能产品，该产品在多个技术指标上实现突破，
        预计将显著提升公司在AI领域的竞争力。市场分析师认为，这一产品发布将对整个科技行业产生
        深远影响，相关上下游公司也可能从中受益。投资者对此消息反应积极，相关概念股在盘前交易
        中出现上涨。分析师建议关注产品商业化进展和市场接受度。
        """,
        "symbols": ["000001", "600036", "002415"],
        "time_horizon": "medium",
        "risk_appetite": "balanced",
        "region": "CN",
        "max_iterations": 2
    }
    
    # 调用增强版多智能体分析系统
    analysis_orchestrator_url = "http://localhost:8010"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print("🎭 启动多智能体投研分析...")
            
            response = await client.post(
                f"{analysis_orchestrator_url}/v1/analysis/execute",
                json=market_event
            )
            response.raise_for_status()
            
            analysis_result = response.json()
            
            print("✅ 分析完成！")
            print(f"\n📋 投资委员会纪要:")
            
            committee_minutes = analysis_result.get("committee_minutes", {})
            if committee_minutes:
                print(f"  会议ID: {committee_minutes.get('meeting_id')}")
                print(f"  参与者: {', '.join(committee_minutes.get('participants', []))}")
                print(f"  讨论轮次: {committee_minutes.get('discussion_rounds')}轮")
                print(f"  最终决议: {committee_minutes.get('final_resolution')}")
                
                key_debates = committee_minutes.get('key_debates', [])
                if key_debates:
                    print(f"\n🔥 关键争议点:")
                    for debate in key_debates:
                        print(f"  - {debate.get('topic')}: {debate.get('positions')}")
            
            # 显示增强版决策
            enhanced_decision = analysis_result.get("enhanced_decision", {})
            if enhanced_decision:
                base_decision = enhanced_decision.get("base_decision", {})
                print(f"\n💡 投资决策:")
                print(f"  行动建议: {base_decision.get('action')}")
                print(f"  基础信心度: {base_decision.get('confidence', 0):.2f}")
                print(f"  风险调整后信心度: {enhanced_decision.get('risk_adjusted_confidence', 0):.2f}")
                print(f"  宏观匹配度: {enhanced_decision.get('macro_alignment', 0):.2f}")
                print(f"  数据质量因子: {enhanced_decision.get('data_quality_factor', 0):.2f}")
            
            # 显示数据情报专家的分析
            enhanced_findings = analysis_result.get("enhanced_findings", {})
            if enhanced_findings:
                data_intelligence = enhanced_findings.get("data_intelligence", {})
                if data_intelligence:
                    market_snapshot = data_intelligence.get("market_snapshot", {})
                    sentiment_indicators = data_intelligence.get("sentiment_indicators", {})
                    
                    print(f"\n📊 数据情报摘要:")
                    print(f"  整体情感: {market_snapshot.get('overall_sentiment', {})}")
                    print(f"  数据一致性评分: {market_snapshot.get('consistency_score', 0):.2f}")
                    print(f"  异常情况: {market_snapshot.get('anomaly_count', 0)}个")
                    
                    hot_topics = sentiment_indicators.get("hot_topics", [])
                    if hot_topics:
                        print(f"  热门话题: {', '.join([topic.get('keyword', '') for topic in hot_topics[:5]])}")
            
            return analysis_result
            
        except httpx.ConnectError:
            print("❌ 无法连接到分析编排器，请确保服务已启动 (http://localhost:8010)")
            return None
        except Exception as e:
            print(f"❌ 分析流程失败: {e}")
            return None


async def demo_yuqing_entity_extraction():
    """演示YuQing-new的实体提取功能"""
    print(f"\n🔍 演示YuQing-new实体提取功能...")
    
    test_text = """
    腾讯控股今日发布2024年第三季度财报，营收同比增长8%至1546亿元，净利润增长47%至537亿元。
    CEO马化腾表示，公司在人工智能和云计算领域的投资开始显现回报。分析师认为，腾讯的游戏业务
    和广告业务表现强劲，预计未来几个季度将继续保持增长势头。投资银行摩根大通将腾讯目标价
    上调至450港元，维持"增持"评级。
    """
    
    yuqing_base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{yuqing_base_url}/api/entities/entities/extract",
                json={
                    "text": test_text,
                    "enable_sentiment": True
                }
            )
            response.raise_for_status()
            
            extraction_result = response.json()
            
            print("✅ 实体提取完成！")
            
            entities = extraction_result.get("entities", {})
            
            companies = entities.get("companies", [])
            if companies:
                print(f"\n🏢 识别到的公司 ({len(companies)}个):")
                for company in companies:
                    print(f"  - {company.get('name', 'N/A')}")
                    print(f"    股票代码: {company.get('stock_code', 'N/A')}")
                    print(f"    影响方向: {company.get('impact_direction', 'N/A')}")
                    print(f"    影响强度: {company.get('impact_magnitude', 0):.2f}")
            
            persons = entities.get("persons", [])
            if persons:
                print(f"\n👤 识别到的人物 ({len(persons)}个):")
                for person in persons:
                    print(f"  - {person.get('name', 'N/A')} ({person.get('position_title', 'N/A')})")
                    print(f"    所属公司: {person.get('company_affiliation', 'N/A')}")
                    print(f"    影响力: {person.get('influence_level', 'N/A')}")
            
            industries = entities.get("industries", [])
            if industries:
                print(f"\n🏭 识别到的行业 ({len(industries)}个):")
                for industry in industries:
                    print(f"  - {industry.get('name', 'N/A')}")
                    print(f"    影响方向: {industry.get('impact_direction', 'N/A')}")
                    print(f"    影响强度: {industry.get('impact_magnitude', 0):.2f}")
            
            events = entities.get("events", [])
            if events:
                print(f"\n📅 识别到的事件 ({len(events)}个):")
                for event in events:
                    print(f"  - {event.get('type', 'N/A')}: {event.get('description', 'N/A')}")
                    print(f"    市场重要性: {event.get('market_significance', 'N/A')}")
            
            return extraction_result
            
        except Exception as e:
            print(f"❌ 实体提取演示失败: {e}")
            return None


async def demo_market_hotspots_discovery():
    """演示市场热点发现功能"""
    print(f"\n🔥 演示市场热点发现功能...")
    
    yuqing_base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 并行获取热点数据
            tasks = [
                client.get(f"{yuqing_base_url}/api/analysis/hotspots/discover", 
                          params={"hours": 6, "limit": 10}),
                client.get(f"{yuqing_base_url}/api/analysis/keywords/trending",
                          params={"hours": 24, "limit": 15}),
                client.get(f"{yuqing_base_url}/api/analysis/stats/sentiment",
                          params={"hours": 24})
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 解析热点发现结果
            if not isinstance(responses[0], Exception):
                hotspots_data = responses[0].json()
                hotspots = hotspots_data.get("data", [])
                
                print(f"🔥 发现热点: {len(hotspots)}个")
                for i, hotspot in enumerate(hotspots[:5], 1):
                    print(f"  {i}. {hotspot.get('title', 'N/A')}")
                    print(f"     热度分数: {hotspot.get('hotness_score', 0):.2f}")
                    print(f"     相关度: {hotspot.get('relevance_score', 0):.2f}")
            
            # 解析趋势关键词
            if not isinstance(responses[1], Exception):
                keywords_data = responses[1].json()
                keywords = keywords_data.get("data", [])
                
                print(f"\n🎯 趋势关键词: {len(keywords)}个")
                trending_words = [kw.get('keyword', '') for kw in keywords[:10]]
                print(f"  {', '.join(trending_words)}")
            
            # 解析情感统计
            if not isinstance(responses[2], Exception):
                sentiment_data = responses[2].json()
                sentiment_stats = sentiment_data.get("data", {})
                
                print(f"\n📊 24小时情感统计:")
                print(f"  正面情感比例: {sentiment_stats.get('positive_ratio', 0):.2%}")
                print(f"  负面情感比例: {sentiment_stats.get('negative_ratio', 0):.2%}")
                print(f"  中性情感比例: {sentiment_stats.get('neutral_ratio', 0):.2%}")
            
            return {
                "hotspots": hotspots if not isinstance(responses[0], Exception) else [],
                "trending_keywords": keywords if not isinstance(responses[1], Exception) else [],
                "sentiment_stats": sentiment_stats if not isinstance(responses[2], Exception) else {}
            }
            
        except Exception as e:
            print(f"❌ 热点发现演示失败: {e}")
            return None


async def create_integration_test_report():
    """生成集成测试报告"""
    print("📝 生成YuQing-new集成测试报告...")
    
    report = {
        "test_timestamp": datetime.now().isoformat(),
        "yuqing_connectivity": False,
        "comprehensive_analysis": None,
        "stock_analysis": None,
        "entity_extraction": None,
        "hotspot_discovery": None,
        "integration_status": "未知"
    }
    
    try:
        # 1. 连通性测试
        report["yuqing_connectivity"] = await test_yuqing_api_connectivity()
        
        if report["yuqing_connectivity"]:
            # 2. 综合分析测试
            report["comprehensive_analysis"] = await demo_yuqing_comprehensive_analysis()
            
            # 3. 股票分析测试
            report["stock_analysis"] = await demo_stock_specific_analysis(["000001", "600036"])
            
            # 4. 实体提取测试
            report["entity_extraction"] = await demo_yuqing_entity_extraction()
            
            # 5. 热点发现测试
            report["hotspot_discovery"] = await demo_market_hotspots_discovery()
            
            # 6. 完整RAG+Agent分析测试
            print("\n" + "="*60)
            print("🎯 开始完整的RAG+Agent分析测试...")
            print("="*60)
            
            rag_result = await demo_integrated_rag_agent_analysis()
            report["rag_agent_analysis"] = rag_result is not None
            
            # 评估集成状态
            success_count = sum([
                report["yuqing_connectivity"],
                report["comprehensive_analysis"] is not None,
                report["stock_analysis"] is not None,
                report["entity_extraction"] is not None,
                report["hotspot_discovery"] is not None,
                report["rag_agent_analysis"]
            ])
            
            if success_count >= 5:
                report["integration_status"] = "优秀"
            elif success_count >= 3:
                report["integration_status"] = "良好"
            elif success_count >= 1:
                report["integration_status"] = "部分可用"
            else:
                report["integration_status"] = "失败"
        
        else:
            report["integration_status"] = "YuQing-new服务不可用"
    
    except Exception as e:
        report["integration_status"] = f"测试异常: {str(e)}"
    
    # 输出报告摘要
    print(f"\n" + "="*60)
    print(f"📊 YuQing-new集成测试报告")
    print("="*60)
    print(f"🔗 连通性: {'✅' if report['yuqing_connectivity'] else '❌'}")
    print(f"📈 综合分析: {'✅' if report['comprehensive_analysis'] else '❌'}")
    print(f"🎯 股票分析: {'✅' if report['stock_analysis'] else '❌'}")
    print(f"🏢 实体提取: {'✅' if report['entity_extraction'] else '❌'}")
    print(f"🔥 热点发现: {'✅' if report['hotspot_discovery'] else '❌'}")
    print(f"🤖 RAG+Agent: {'✅' if report.get('rag_agent_analysis') else '❌'}")
    print(f"🏆 集成状态: {report['integration_status']}")
    
    # 保存详细报告
    report_path = "yuqing_integration_test_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📄 详细报告已保存: {report_path}")
    
    return report


async def main():
    """主函数 - 运行完整的集成演示"""
    print("🎉 欢迎使用YuQing-new与RAG+Agent系统集成演示！")
    print("="*60)
    
    # 检查必要的环境配置
    yuqing_url = os.getenv("YUQING_API_URL", "http://localhost:8000")
    llm_url = os.getenv("LLM_GATEWAY_URL", "http://localhost:8002/v1/chat/completions")
    
    print(f"🔧 环境配置:")
    print(f"  YuQing-new API: {yuqing_url}")
    print(f"  LLM Gateway: {llm_url}")
    print()
    
    # 运行集成测试
    report = await create_integration_test_report()
    
    print(f"\n🎊 集成演示完成！")
    
    if report["integration_status"] in ["优秀", "良好"]:
        print("🚀 系统集成成功！您可以开始使用YuQing-new驱动的投研分析系统了！")
        
        print(f"\n🔧 使用建议:")
        print(f"  1. 确保YuQing-new服务运行在 {yuqing_url}")
        print(f"  2. 确保RAG+Agent服务运行在 http://localhost:8010")
        print(f"  3. 配置环境变量 YUQING_API_URL 指向YuQing-new服务")
        print(f"  4. 调用 /v1/analysis/execute 接口开始分析")
    
    else:
        print("⚠️  系统集成存在问题，请检查服务状态和配置。")
        
        print(f"\n🔧 故障排除:")
        print(f"  1. 检查YuQing-new是否正常运行: {yuqing_url}/health")
        print(f"  2. 检查RAG+Agent服务是否启动: http://localhost:8010/health")
        print(f"  3. 验证网络连接和端口配置")
        print(f"  4. 查看日志文件排查具体错误")


if __name__ == "__main__":
    asyncio.run(main())
