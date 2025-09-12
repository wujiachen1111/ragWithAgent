"""
实体分析综合服务
整合情感分析和实体识别功能
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from yuqing.core.logging import app_logger as logger
from yuqing.models.database_models import NewsItem
from yuqing.services.deepseek_service import deepseek_service, SentimentResult, EntityAnalysisResult
from yuqing.core.database import get_db


class EntityAnalysisOrchestrator:
    """实体分析编排器"""
    
    def __init__(self):
        self.deepseek_service = deepseek_service
        self._multi_key_service = None
        self._init_multi_key_service()
    
    def _init_multi_key_service(self):
        """初始化多密钥服务"""
        try:
            from yuqing.services.multi_key_service import MultiKeyDeepSeekService
            from yuqing.core.config import settings
            
            # 获取所有API密钥
            api_keys = []
            if hasattr(settings, 'deepseek_api_keys') and settings.deepseek_api_keys:
                api_keys = settings.deepseek_api_keys
            elif hasattr(settings, 'deepseek_api_key') and settings.deepseek_api_key:
                api_keys = [settings.deepseek_api_key]
            
            if len(api_keys) > 1:
                self._multi_key_service = MultiKeyDeepSeekService(api_keys)
                logger.info(f"启用多密钥并发服务，共 {len(api_keys)} 个API密钥")
            else:
                logger.info("使用单密钥服务")
                self._multi_key_service = None
                
        except Exception as e:
            logger.warning(f"多密钥服务初始化失败: {e}，将使用单密钥服务")
            self._multi_key_service = None
    
    async def analyze_news_comprehensive(self, news_item: NewsItem) -> Dict[str, Any]:
        """对新闻进行综合分析（情感分析 + 实体识别）"""
        try:
            results = {}
            
            # 并行执行情感分析和实体识别
            sentiment_task = self.deepseek_service.analyze_single_news(news_item)
            entity_task = self.deepseek_service.extract_entities(news_item)
            
            sentiment_result, entity_result = await asyncio.gather(
                sentiment_task, 
                entity_task,
                return_exceptions=True
            )
            
            # 处理情感分析结果
            if isinstance(sentiment_result, SentimentResult):
                results["sentiment"] = {
                    "sentiment": sentiment_result.sentiment,
                    "confidence": sentiment_result.confidence,
                    "keywords": sentiment_result.keywords,
                    "summary": sentiment_result.summary,
                    "market_impact": sentiment_result.market_impact,
                    "reasoning": sentiment_result.reasoning
                }
                
                # 保存情感分析结果
                await self.deepseek_service.save_analysis_results([news_item], {news_item.id: sentiment_result})
                
            elif isinstance(sentiment_result, Exception):
                logger.error(f"情感分析失败: {sentiment_result}")
                results["sentiment"] = {"error": str(sentiment_result)}
            else:
                results["sentiment"] = {"error": "情感分析返回空结果"}
            
            # 处理实体识别结果
            if isinstance(entity_result, EntityAnalysisResult):
                results["entities"] = {
                    "companies": [
                        {
                            "name": entity.name,
                            "impact_direction": entity.impact_direction,
                            "impact_magnitude": entity.impact_magnitude,
                            "confidence": entity.confidence,
                            "additional_info": entity.additional_info
                        } for entity in entity_result.companies
                    ],
                    "persons": [
                        {
                            "name": entity.name,
                            "impact_direction": entity.impact_direction,
                            "impact_magnitude": entity.impact_magnitude,
                            "confidence": entity.confidence,
                            "additional_info": entity.additional_info
                        } for entity in entity_result.persons
                    ],
                    "industries": entity_result.industries,
                    "events": entity_result.events
                }
                
                # 保存实体分析结果
                await self.deepseek_service.save_entity_analysis_results(news_item, entity_result)
                
            elif isinstance(entity_result, Exception):
                logger.error(f"实体识别失败: {entity_result}")
                results["entities"] = {"error": str(entity_result)}
            else:
                results["entities"] = {"error": "实体识别返回空结果"}
            
            # 生成综合分析报告
            results["comprehensive_analysis"] = self._generate_comprehensive_report(
                results.get("sentiment"),
                results.get("entities")
            )
            
            return {
                "success": True,
                "news_id": news_item.id,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"综合分析失败 {news_item.id}: {e}")
            return {
                "success": False,
                "news_id": news_item.id,
                "error": str(e)
            }
    
    def _generate_comprehensive_report(self, sentiment_data: Dict, entity_data: Dict) -> Dict[str, Any]:
        """生成综合分析报告"""
        report = {
            "overall_impact": "neutral",
            "key_insights": [],
            "risk_alerts": [],
            "investment_implications": []
        }
        
        try:
            # 基于情感分析确定整体影响
            if sentiment_data and not sentiment_data.get("error"):
                sentiment = sentiment_data.get("sentiment", "neutral")
                confidence = sentiment_data.get("confidence", 0.0)
                market_impact = sentiment_data.get("market_impact", "low")
                
                if confidence >= 0.8:
                    report["overall_impact"] = sentiment
                
                # 添加关键洞察
                if market_impact == "high":
                    report["key_insights"].append(f"高市场影响事件：{sentiment_data.get('summary', '')}")
                
                if sentiment == "negative" and confidence >= 0.8:
                    report["risk_alerts"].append("检测到高置信度负面情绪，需要关注潜在风险")
            
            # 基于实体分析添加具体洞察
            if entity_data and not entity_data.get("error"):
                companies = entity_data.get("companies", [])
                persons = entity_data.get("persons", [])
                industries = entity_data.get("industries", [])
                events = entity_data.get("events", [])
                
                # 分析高影响公司
                high_impact_companies = [
                    c for c in companies 
                    if c.get("impact_magnitude", 0) >= 0.7
                ]
                
                if high_impact_companies:
                    company_names = [c["name"] for c in high_impact_companies]
                    report["key_insights"].append(f"高影响公司: {', '.join(company_names)}")
                
                # 分析高影响人物
                high_influence_persons = [
                    p for p in persons 
                    if p.get("additional_info", {}).get("influence_level") == "high"
                ]
                
                if high_influence_persons:
                    person_names = [p["name"] for p in high_influence_persons]
                    report["key_insights"].append(f"高影响力人物: {', '.join(person_names)}")
                
                # 分析行业影响
                if industries:
                    positive_industries = [
                        i["name"] for i in industries 
                        if i.get("impact_direction") == "positive"
                    ]
                    negative_industries = [
                        i["name"] for i in industries 
                        if i.get("impact_direction") == "negative"
                    ]
                    
                    if positive_industries:
                        report["investment_implications"].append(f"利好行业: {', '.join(positive_industries)}")
                    
                    if negative_industries:
                        report["risk_alerts"].append(f"风险行业: {', '.join(negative_industries)}")
                
                # 分析重大事件
                major_events = [
                    e for e in events 
                    if e.get("market_significance") == "major"
                ]
                
                if major_events:
                    for event in major_events:
                        report["key_insights"].append(f"重大事件: {event.get('title', '')}")
                        if event.get("expected_volatility") == "high":
                            report["risk_alerts"].append(f"高波动性事件预警: {event.get('title', '')}")
            
            # 生成投资建议
            if report["overall_impact"] == "positive" and len(report["risk_alerts"]) == 0:
                report["investment_implications"].append("整体偏向积极，可考虑适度配置相关资产")
            elif report["overall_impact"] == "negative" or len(report["risk_alerts"]) > 0:
                report["investment_implications"].append("存在下行风险，建议谨慎操作并关注风险控制")
            else:
                report["investment_implications"].append("市场情绪中性，建议密切关注后续发展")
            
        except Exception as e:
            logger.error(f"生成综合报告失败: {e}")
            report["error"] = str(e)
        
        return report
    
    async def analyze_recent_news(self, hours: int = 1, limit: int = 20) -> Dict[str, Any]:
        """分析最近几小时内的新闻"""
        try:
            from datetime import timedelta
            from sqlalchemy.orm import Session
            
            # 计算时间范围
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # 获取数据库会话
            db = next(get_db())
            
            # 查询最近的新闻（优先分析未分析的）
            news_items = db.query(NewsItem).filter(
                NewsItem.collected_at >= cutoff_time,
                NewsItem.analysis_status == 'pending'
            ).order_by(NewsItem.published_at.desc()).limit(limit).all()
            
            if not news_items:
                logger.info(f"最近 {hours} 小时内没有需要分析的新闻")
                return {
                    "success": True,
                    "analyzed_count": 0,
                    "message": f"最近 {hours} 小时内没有需要分析的新闻"
                }
            
            logger.info(f"找到 {len(news_items)} 条需要分析的新闻")
            
            # 执行批量分析
            result = await self.batch_analyze_news(news_items)
            
            return {
                "success": True,
                "analyzed_count": result.get("successful_count", 0),
                "total_items": len(news_items),
                "time_range_hours": hours,
                "details": result
            }
            
        except Exception as e:
            logger.error(f"分析最近新闻失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analyzed_count": 0
            }

    async def batch_analyze_news(self, news_items: List[NewsItem], 
                               batch_size: int = None) -> Dict[str, Any]:
        """批量分析新闻 - 使用多密钥并发"""
        total_items = len(news_items)
        
        # 如果有多密钥服务，使用并发分析
        if self._multi_key_service and total_items > 1:
            return await self._concurrent_analyze_news(news_items)
        
        # 否则使用原有的串行分析
        return await self._sequential_analyze_news(news_items, batch_size or 5)
    
    async def _concurrent_analyze_news(self, news_items: List[NewsItem]) -> Dict[str, Any]:
        """并发分析新闻（使用多密钥）"""
        total_items = len(news_items)
        logger.info(f"开始并发分析 {total_items} 条新闻")
        
        try:
            # 准备新闻数据
            news_data_list = []
            for news_item in news_items:
                news_data = {
                    "id": news_item.id,
                    "title": news_item.title,
                    "content": news_item.content or "",
                    "summary": news_item.summary or "",
                    "published_at": news_item.published_at,
                    "source": news_item.source
                }
                news_data_list.append(news_data)
            
            # 使用多密钥并发分析
            analysis_results = await self._multi_key_service.analyze_news_parallel(
                news_data_list, 
                max_workers=min(8, len(news_items))  # 最多8个并发
            )
            
            # 处理结果并保存
            successful_count = 0
            failed_count = 0
            
            for i, (news_item, result) in enumerate(zip(news_items, analysis_results)):
                try:
                    if result and result.get("success"):
                        # 保存情感分析结果
                        sentiment_result = result.get("sentiment_result")
                        if sentiment_result:
                            await self.deepseek_service.save_analysis_results(
                                [news_item], 
                                {news_item.id: sentiment_result}
                            )
                        
                        # 执行实体分析
                        try:
                            entity_result = await self.deepseek_service.extract_entities(news_item)
                            if entity_result:
                                await self.deepseek_service.save_entity_analysis_results(news_item, entity_result)
                                logger.debug(f"✅ 实体分析完成: {news_item.title[:30]}...")
                        except Exception as entity_error:
                            logger.warning(f"实体分析失败 {news_item.id}: {entity_error}")
                        
                        successful_count += 1
                        logger.debug(f"✅ 综合分析成功: {news_item.title[:30]}...")
                    else:
                        failed_count += 1
                        logger.warning(f"❌ 并发分析失败: {news_item.title[:30]}...")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"保存分析结果失败 {news_item.id}: {e}")
            
            logger.info(f"综合分析完成: 成功 {successful_count} 条 (包含情感分析和实体识别), 失败 {failed_count} 条")
            
            return {
                "success": True,
                "total_analyzed": total_items,
                "successful_count": successful_count,
                "failed_count": failed_count,
                "method": "concurrent"
            }
            
        except Exception as e:
            logger.error(f"并发分析失败: {e}")
            # 降级到串行分析
            return await self._sequential_analyze_news(news_items, 5)
    
    async def _sequential_analyze_news(self, news_items: List[NewsItem], 
                                     batch_size: int = 5) -> Dict[str, Any]:
        """串行分析新闻（原有方法）"""
        results = []
        total_items = len(news_items)
        
        logger.info(f"开始串行批量分析 {total_items} 条新闻 (批大小: {batch_size})")
        
        for i in range(0, total_items, batch_size):
            batch = news_items[i:i + batch_size]
            batch_tasks = [
                self.analyze_news_comprehensive(news_item) 
                for news_item in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批量分析中出现异常: {result}")
                    results.append({"success": False, "error": str(result)})
                else:
                    results.append(result)
            
            # 避免API限流，添加延迟
            if i + batch_size < total_items:
                await asyncio.sleep(1)
        
        successful_count = len([r for r in results if r.get("success")])
        
        return {
            "success": True,
            "total_analyzed": total_items,
            "successful_count": successful_count,
            "failed_count": total_items - successful_count,
            "results": results,
            "method": "sequential"
        }


# 全局实例
entity_analysis_orchestrator = EntityAnalysisOrchestrator()


def analyze_latest_news(limit: int = 10) -> Dict[str, Any]:
    """
    分析最新的新闻数据（同步版本，用于脚本调用）
    
    Args:
        limit: 限制分析的新闻数量
        
    Returns:
        分析结果字典
    """
    try:
        # 使用同步方式运行异步函数
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 获取最新新闻
            db = next(get_db())
            news_items = db.query(NewsItem).filter(
                NewsItem.analysis_status == 'pending'
            ).order_by(NewsItem.published_at.desc()).limit(limit).all()
            
            if not news_items:
                return {
                    "success": True,
                    "analyzed_count": 0,
                    "message": "没有需要分析的新闻"
                }
            
            # 执行分析
            result = loop.run_until_complete(
                entity_analysis_orchestrator.batch_analyze_news(news_items)
            )
            
            return {
                "success": True,
                "analyzed_count": result.get("successful_count", 0),
                "total_items": len(news_items),
                "details": result
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"分析最新新闻失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "analyzed_count": 0
        }
