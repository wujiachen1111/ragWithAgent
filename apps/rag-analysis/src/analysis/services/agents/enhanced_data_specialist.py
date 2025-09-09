"""
增强版数据情报专家 - 集成舆情收集部门API
基于Bloomberg Terminal操作员的工作模式，提供专业级数据情报支撑
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base import BaseAgent
from ..llm_client import LLMClient
from ..sentiment_client import SentimentAPIClient, SentimentQueryParam
from ..yuqing_adapter import YuQingNewsAdapter, YuQingConfig
from ...models.agents import AnalysisRequestVO
from ...models.enhanced_agents import DataIntelligenceReport
# 新增导入 stock_adapter
from ....services.stock_client import stock_adapter


class EnhancedDataIntelligenceSpecialist(BaseAgent):
    """
    增强版数据情报专家 - 集成舆情API和股票数据API的专业数据分析师

    核心能力：
    1. 实时舆情数据采集与分析
    2. 多维度市场数据融合
    3. 异常情况识别与预警
    4. 数据质量评估与校验
    5. 专业级情报报告生成
    """
    name = "enhanced_data_intelligence_specialist"

    def __init__(self):
        super().__init__()
        # 初始化原有舆情API客户端（备用）
        self.sentiment_client = SentimentAPIClient()

        # 初始化YuQing-new适配器（主要数据源）
        yuqing_config = YuQingConfig(
            base_url=os.getenv("YUQING_API_URL", "http://localhost:8000"),
            timeout=30.0,
            max_retries=3
        )
        self.yuqing_adapter = YuQingNewsAdapter(yuqing_config)

        # 新增：初始化 Stock Agent 适配器
        self.stock_adapter = stock_adapter

    async def analyze(self, request: AnalysisRequestVO) -> DataIntelligenceReport:
        """执行增强版数据情报收集和分析"""
        client = LLMClient()

        # 第一阶段：并行收集中来自Stock Agent的核心数据 和 来自Yuqing的舆情数据
        core_data_tasks = [
            self._collect_stock_data_from_agent(request), # <--- 使用真实数据
            self._collect_yuqing_comprehensive_data(request),
            self._get_yuqing_stock_impact_analysis(request),
            self._get_yuqing_market_hotspots(request),
            self._get_yuqing_entity_analysis(request)
        ]

        results = await asyncio.gather(*core_data_tasks, return_exceptions=True)

        # 解析结果
        stock_data = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        yuqing_comprehensive = results[1] if not isinstance(results[1], Exception) else {}
        yuqing_stock_impact = results[2] if not isinstance(results[2], Exception) else {}
        yuqing_hotspots = results[3] if not isinstance(results[3], Exception) else {}
        yuqing_entities = results[4] if not isinstance(results[4], Exception) else {}


        # 第三阶段：数据融合与异常检测 (简化并调整)
        fusion_tasks = [
            self._fuse_multi_source_data(
                stock_data,
                yuqing_comprehensive,
                yuqing_stock_impact,
                yuqing_hotspots,
                yuqing_entities,
                client),
            self._detect_cross_source_anomalies(
                yuqing_comprehensive,
                yuqing_stock_impact,
                yuqing_hotspots,
                client),
            self._assess_data_coherence(
                stock_data.get("data", {}).get("market_context", {}),
                yuqing_comprehensive,
                client)
        ]

        fusion_result, anomalies, coherence_assessment = await asyncio.gather(*fusion_tasks)

        # 第四阶段：生成专业情报报告
        return await self._generate_intelligence_report(
            request, fusion_result, anomalies, coherence_assessment, client
        )

    async def _collect_stock_data_from_agent(self, request: AnalysisRequestVO) -> Dict[str, Any]:
        """
        通过 Stock Agent 客户端获取全面的股票数据
        """
        try:
            self.logger.info(f"向Stock Agent请求 {len(request.symbols)} 只股票的数据...")
            # 使用 comprehensive 模式一次性获取多种数据
            stock_context = await self.stock_adapter.get_investment_context(
                symbols=request.symbols,
                analysis_type="comprehensive"
            )
            if stock_context and not stock_context.get("error"):
                self.logger.info("✅ 成功从Stock Agent获取股票数据")
                return stock_context
            else:
                self.logger.warning(f"⚠️ 从Stock Agent获取股票数据失败: {stock_context.get('error')}")
                return {"error": "Failed to get stock data from agent."}
        except Exception as e:
            self.logger.error(f"❌ 调用Stock Agent时发生异常: {e}")
            return {"error": f"Exception while calling stock agent: {e}"}

    async def _collect_yuqing_comprehensive_data(self, request: AnalysisRequestVO) -> Dict[str, Any]:
        """使用YuQing-new收集综合舆情数据 - 主要数据源"""
        try:
            # 提取关键词
            keywords = [request.topic]
            if request.headline:
                keywords.append(request.headline)

            # 从内容中提取关键词
            extracted_keywords = await self._extract_keywords_from_content(request.content)
            keywords.extend(extracted_keywords[:3])

            # 使用YuQing-new适配器获取数据
            sentiment_report = await self.yuqing_adapter.get_comprehensive_sentiment_data(
                symbols=request.symbols,
                keywords=keywords,
                hours=self._map_time_horizon_to_hours(request.time_horizon),
                limit=50
            )

            # 转换为统一格式
            return {
                "overall_sentiment": sentiment_report.overall_sentiment,
                "sentiment_trend": sentiment_report.sentiment_trend,
                "hot_topics": sentiment_report.hot_topics,
                "influential_sources": sentiment_report.influential_sources,
                "sentiment_anomalies": sentiment_report.sentiment_anomalies,
                "volume_spikes": sentiment_report.volume_spikes,
                "data_quality": sentiment_report.average_credibility,
                "total_mentions": sentiment_report.total_processed,
                "collection_timestamp": sentiment_report.collection_time.isoformat(),
                "processing_duration": sentiment_report.processing_duration,
                "data_source": "YuQing-new"}

        except Exception as e:
            # 回退到原有舆情API
            return await self._fallback_to_original_sentiment_api(request)

    async def _get_yuqing_stock_impact_analysis(self, request: AnalysisRequestVO) -> Dict[str, Any]:
        """获取YuQing-new的股票影响分析"""
        try:
            stock_impact = await self.yuqing_adapter.get_stock_impact_analysis(
                stock_codes=request.symbols,
                hours=self._map_time_horizon_to_hours(request.time_horizon)
            )

            return {
                "stock_specific_analysis": stock_impact.get(
                    "stock_impact_analysis", {}), "market_context": stock_impact.get(
                    "market_context", {}), "analysis_metadata": stock_impact.get(
                    "analysis_metadata", {}), "data_source": "YuQing-new"}

        except Exception as e:
            return {
                "error": f"YuQing股票影响分析失败: {str(e)}",
                "stock_specific_analysis": {},
                "data_source": "YuQing-new"
            }

    async def _get_yuqing_market_hotspots(self, request: AnalysisRequestVO) -> Dict[str, Any]:
        """获取YuQing-new的市场热点数据"""
        try:
            hotspots = await self.yuqing_adapter.get_market_hotspots(
                hours=self._map_time_horizon_to_hours(request.time_horizon),
                limit=15
            )

            return {
                "market_hotspots": hotspots.get("hotspots", []),
                "trending_keywords": hotspots.get("trending_keywords", []),
                "sentiment_overview": hotspots.get("sentiment_overview", {}),
                "hotspot_count": hotspots.get("total_hotspots", 0),
                "data_source": "YuQing-new"
            }

        except Exception as e:
            return {
                "error": f"YuQing热点获取失败: {str(e)}",
                "market_hotspots": [],
                "data_source": "YuQing-new"
            }

    async def _get_yuqing_entity_analysis(self, request: AnalysisRequestVO) -> Dict[str, Any]:
        """获取YuQing-new的实体分析数据"""
        try:
            # 并行获取不同类型的实体分析
            entity_tasks = [
                self.yuqing_adapter.get_entity_based_analysis(
                    "companies", limit=30), self.yuqing_adapter.get_entity_based_analysis(
                    "industries", limit=20), self.yuqing_adapter.get_entity_based_analysis(
                    "events", limit=15), self.yuqing_adapter.get_entity_based_analysis(
                    "persons", limit=10)]

            entity_results = await asyncio.gather(*entity_tasks, return_exceptions=True)

            companies = entity_results[0] if not isinstance(
                entity_results[0], Exception) else {"data": []}
            industries = entity_results[1] if not isinstance(
                entity_results[1], Exception) else {"data": []}
            events = entity_results[2] if not isinstance(
                entity_results[2], Exception) else {"data": []}
            persons = entity_results[3] if not isinstance(
                entity_results[3], Exception) else {"data": []}

            # 过滤与目标股票相关的实体
            relevant_entities = self._filter_relevant_entities(
                request.symbols, companies, industries, events, persons
            )

            return {
                "company_entities": relevant_entities["companies"],
                "industry_entities": relevant_entities["industries"],
                "event_entities": relevant_entities["events"],
                "person_entities": relevant_entities["persons"],
                "entity_summary": {
                    "total_companies": len(relevant_entities["companies"]),
                    "total_industries": len(relevant_entities["industries"]),
                    "total_events": len(relevant_entities["events"]),
                    "total_persons": len(relevant_entities["persons"])
                },
                "data_source": "YuQing-new"
            }

        except Exception as e:
            return {
                "error": f"YuQing实体分析失败: {str(e)}",
                "entity_summary": {
                    "total_companies": 0,
                    "total_industries": 0,
                    "total_events": 0,
                    "total_persons": 0},
                "data_source": "YuQing-new"}

    def _filter_relevant_entities(self,
                                  target_symbols: List[str],
                                  companies: Dict,
                                  industries: Dict,
                                  events: Dict,
                                  persons: Dict) -> Dict[str,
                                                         List]:
        """过滤与目标股票相关的实体"""
        relevant = {
            "companies": [],
            "industries": [],
            "events": [],
            "persons": []
        }

        # 过滤相关公司
        for company in companies.get("data", []):
            if (company.get("stock_code") in target_symbols or any(symbol in str(
                    company.get("stock_code", "")) for symbol in target_symbols)):
                relevant["companies"].append(company)

        # 如果找到相关公司，获取其行业信息
        if relevant["companies"]:
            company_industries = set()
            for company in relevant["companies"]:
                # 从公司信息中提取行业（需要根据实际数据结构调整）
                industry_info = company.get(
                    "industry_name") or company.get("business_segment")
                if industry_info:
                    company_industries.add(industry_info)

            # 过滤相关行业
            for industry in industries.get("data", []):
                if industry.get("industry_name") in company_industries:
                    relevant["industries"].append(industry)

        # 过滤相关事件
        for event in events.get("data", []):
            primary_companies = event.get("primary_companies", [])
            secondary_companies = event.get("secondary_companies", [])

            if (any(symbol in str(primary_companies) for symbol in target_symbols) or any(
                    symbol in str(secondary_companies) for symbol in target_symbols)):
                relevant["events"].append(event)

        # 过滤相关人物
        for person in persons.get("data", []):
            related_companies = person.get("related_companies", [])
            if any(symbol in str(related_companies)
                   for symbol in target_symbols):
                relevant["persons"].append(person)

        return relevant

    async def _fallback_to_original_sentiment_api(self, request: AnalysisRequestVO) -> Dict[str, Any]:
        """回退到原有舆情API的实现"""
        try:
            # 构建查询参数
            keywords = [request.topic]
            if request.headline:
                keywords.append(request.headline)

            extracted_keywords = await self._extract_keywords_from_content(request.content)
            keywords.extend(extracted_keywords[:3])

            # 使用原有舆情API
            sentiment_report = await self.sentiment_client.get_comprehensive_sentiment_report(
                symbols=request.symbols,
                keywords=keywords,
                time_range=self._map_time_horizon_to_range(request.time_horizon)
            )

            return {
                "overall_sentiment": sentiment_report.overall_sentiment,
                "sentiment_trend": sentiment_report.sentiment_trend,
                "hot_topics": sentiment_report.hot_topics,
                "data_quality": sentiment_report.average_credibility,
                "total_mentions": sentiment_report.total_processed,
                "data_source": "fallback_api",
                "fallback_reason": "YuQing-new不可用"
            }

        except Exception as e:
            return {
                "error": f"所有舆情数据源都不可用: {str(e)}",
                "overall_sentiment": {
                    "positive": 0.33,
                    "negative": 0.33,
                    "neutral": 0.34},
                "data_quality": 0.0,
                "total_mentions": 0,
                "data_source": "error"}

    def _map_time_horizon_to_hours(self, time_horizon: str) -> int:
        """将时间视角映射为小时数"""
        mapping = {
            "short": 6,
            "medium": 24,
            "long": 168  # 一周
        }
        return mapping.get(time_horizon, 24)

    async def _fuse_multi_source_data(self, stock_data: Dict,
                                      comprehensive_sentiment: Dict,
                                      news_flow_impact: Dict,
                                      social_media_buzz: Dict,
                                      research_sentiment: Dict, client: LLMClient) -> Dict[str, Any]:
        """多源数据融合分析"""
        system = (
            "你是数据融合专家。整合来自Stock Agent的结构化金融数据和来自舆情系统的数据，"
            "识别数据间的一致性和分歧，形成综合判断。"
            "返回JSON：data_consistency, key_signals, conflicting_indicators, confidence_assessment"
        )

        # 构建简化的数据摘要用于LLM分析
        data_summary = {
            "stock_data": {
                "market_context": str(stock_data.get("data", {}).get("market_context", {}))[:400],
                "comparative_analysis": str(stock_data.get("data", {}).get("comparative_analysis", {}))[:400],
                "sector_analysis": str(stock_data.get("data", {}).get("sector_analysis", {}))[:400]
            },
            "sentiment": {
                "overall": comprehensive_sentiment.get("overall_sentiment", {}),
                "stock_impact": news_flow_impact.get("stock_specific_analysis", {}),
                "hotspots": social_media_buzz.get("market_hotspots", [])[:3],
                "entities": research_sentiment.get("entity_summary", {})
            }
        }

        user = f"多源数据摘要: {json.dumps(data_summary, ensure_ascii=False)[:2000]}"

        try:
            fusion_result = await client.structured_json(system, user, temperature=0.2)

            # 添加原始数据引用
            fusion_result["raw_data_sources"] = {
                "stock_agent_data": stock_data,
                "sentiment_analysis": {
                    "comprehensive": comprehensive_sentiment,
                    "stock_impact": news_flow_impact,
                    "hotspots": social_media_buzz,
                    "entities": research_sentiment
                }
            }

            return fusion_result

        except Exception:
            return {
                "data_consistency": "mixed",
                "key_signals": ["多源数据融合异常，建议人工复核"],
                "conflicting_indicators": ["数据处理错误"],
                "confidence_assessment": 0.3,
                "raw_data_sources": {
                    "error": "数据融合处理失败"
                }
            }

    async def _detect_cross_source_anomalies(self, comprehensive_sentiment: Dict,
                                             news_flow_impact: Dict, social_media_buzz: Dict,
                                             client: LLMClient) -> List[str]:
        """检测跨数据源异常"""
        system = (
            "你是异常检测专家。比较不同舆情数据源，识别异常情况："
            "情感分歧、音量异常、传播异常、可信度问题。"
            "返回异常情况列表的JSON数组"
        )

        sentiment_summary = {
            "comprehensive": comprehensive_sentiment.get(
                "overall_sentiment", {}), "news_sentiment": news_flow_impact.get(
                "impact_score", {}), "social_sentiment": social_media_buzz.get(
                "sentiment_distribution", {}), "volume_metrics": {
                    "news": news_flow_impact.get(
                        "news_volume", {}), "social": social_media_buzz.get(
                            "mention_volume", {})}}

        user = f"舆情数据对比: {json.dumps(sentiment_summary, ensure_ascii=False)[:1500]}"

        try:
            result = await client.structured_json(system, user, temperature=0.1)
            return result.get("anomalies", [])
        except Exception:
            return ["跨源异常检测失败，建议人工验证数据一致性"]

    async def _assess_data_coherence(self, market_fundamentals: Dict,
                                     comprehensive_sentiment: Dict, client: LLMClient) -> Dict[str, Any]:
        """评估数据一致性"""
        system = (
            "你是数据一致性分析师。评估基本面数据与舆情数据的一致性，"
            "识别逻辑冲突和信息不对称。"
            "返回JSON：coherence_score, logical_conflicts, information_gaps, reliability_assessment"
        )

        coherence_data = {
            "fundamentals_summary": {
                k: str(v)[
                    :200] for k, v in market_fundamentals.items()}, "sentiment_summary": {
                "overall": comprehensive_sentiment.get(
                    "overall_sentiment", {}), "hot_topics": comprehensive_sentiment.get(
                        "hot_topics", [])[
                            :3]}}

        user = f"一致性分析数据: {json.dumps(coherence_data, ensure_ascii=False)[:1500]}"

        try:
            return await client.structured_json(system, user, temperature=0.1)
        except Exception:
            return {
                "coherence_score": 0.5,
                "logical_conflicts": ["一致性分析失败"],
                "information_gaps": ["数据处理错误"],
                "reliability_assessment": "低"
            }

    async def _generate_intelligence_report(self, request: AnalysisRequestVO,
                                            fusion_result: Dict, anomalies: List[str],
                                            coherence_assessment: Dict, client: LLMClient) -> DataIntelligenceReport:
        """生成专业情报报告"""

        # 提取关键指标
        sentiment_data = fusion_result.get(
            "raw_data_sources", {}).get(
            "sentiment_analysis", {})
        comprehensive_sentiment = sentiment_data.get("comprehensive", {})

        # 构建市场快照
        market_snapshot = {
            "overall_sentiment": comprehensive_sentiment.get(
                "overall_sentiment", {}), "data_fusion_signals": fusion_result.get(
                "key_signals", []), "consistency_score": coherence_assessment.get(
                "coherence_score", 0.5), "anomaly_count": len(anomalies)}

        # 情感指标
        sentiment_indicators = {
            "sentiment_trend": comprehensive_sentiment.get(
                "sentiment_trend", []), "volume_spikes": comprehensive_sentiment.get(
                "volume_spikes", []), "hot_topics": comprehensive_sentiment.get(
                "hot_topics", []), "influential_sources": comprehensive_sentiment.get(
                    "influential_sources", [])}

        # 关键财务指标
        fundamentals = fusion_result.get(
            "raw_data_sources", {}).get(
            "market_fundamentals", {})
        key_financial_metrics = {
            "valuation_assessment": fundamentals.get("valuation_metrics", {}),
            "earnings_outlook": fundamentals.get("earnings_outlook", {}),
            "growth_prospects": fundamentals.get("growth_prospects", {})
        }

        # 市场异常情况
        market_anomalies = []
        market_anomalies.extend(anomalies)
        market_anomalies.extend(
            comprehensive_sentiment.get(
                "sentiment_anomalies", []))
        market_anomalies.extend(
            fusion_result.get(
                "conflicting_indicators", []))

        # 数据质量评分
        data_quality_score = min(1.0, max(0.0, (
            comprehensive_sentiment.get("data_quality", 0.7) * 0.4 +
            coherence_assessment.get("coherence_score", 0.5) * 0.3 +
            fusion_result.get("confidence_assessment", 0.6) * 0.3
        )))

        # 数据源可靠性
        data_sources_reliability = {
            "sentiment_api": comprehensive_sentiment.get("data_quality", 0.7),
            "market_data": 0.85,  # 基于历史表现的估计
            "technical_analysis": 0.75, # Note: This data is now part of stock_data
            "microstructure": 0.8, # Note: This data is now part of stock_data
            "data_fusion": fusion_result.get("confidence_assessment", 0.6)
        }

        return DataIntelligenceReport(
            market_snapshot=market_snapshot,
            sentiment_indicators=sentiment_indicators,
            key_financial_metrics=self._extract_key_financials_from_stock_data(fusion_result),
            market_anomalies=market_anomalies,
            data_quality_score=data_quality_score,
            data_sources_reliability=data_sources_reliability,
            collection_timestamp=datetime.now().isoformat()
        )

    async def _extract_keywords_from_content(self, content: str) -> List[str]:
        """从内容中提取关键词"""
        # 简化实现，实际项目中可以使用更复杂的NLP技术
        import re

        # 提取中文词汇（简单正则）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', content)

        # 提取英文词汇
        english_words = re.findall(r'[A-Za-z]{3,}', content)

        # 合并并去重
        all_words = list(set(chinese_words + english_words))

        # 过滤常见停用词
        stop_words = {
            '公司',
            '市场',
            '投资',
            '分析',
            '发展',
            '增长',
            '业务',
            'the',
            'and',
            'for',
            'are',
            'with'}
        filtered_words = [
            word for word in all_words if word.lower() not in stop_words]

        return filtered_words[:10]  # 返回前10个关键词

    def _map_time_horizon_to_range(self, time_horizon: str) -> str:
        """将时间视角映射为API时间范围参数"""
        mapping = {
            "short": "24h",
            "medium": "7d",
            "long": "30d"
        }
        return mapping.get(time_horizon, "24h")

    def _extract_key_financials_from_stock_data(self, fusion_result: Dict) -> Dict:
        """从融合结果中提取关键财务指标"""
        try:
            stock_data = fusion_result.get("raw_data_sources", {}).get("stock_agent_data", {})
            market_context = stock_data.get("data", {}).get("market_context", {})

            if not market_context or not market_context.get("data"):
                return {}

            # 以第一只股票为代表
            first_symbol = list(market_context["data"].keys())[0]
            first_stock_data = market_context["data"][first_symbol]

            return {
                "valuation_assessment": first_stock_data.get("valuation", {}),
                "trading_info": first_stock_data.get("trading", {}),
                "ownership_summary": first_stock_data.get("ownership", {})
            }
        except (KeyError, IndexError):
            return {"error": "无法从Stock Agent数据中提取关键财务指标"}


    async def close(self):
        """清理资源"""
        await self.sentiment_client.aclose()
        await self.yuqing_adapter.aclose()
