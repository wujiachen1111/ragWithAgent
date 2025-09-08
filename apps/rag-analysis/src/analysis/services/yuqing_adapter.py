"""
YuQing-new系统适配器
将YuQing-new的舆情分析能力无缝集成到RAG+Agent投研系统
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .sentiment_client import SentimentAnalysisReport, SentimentDataPoint
from ..models.enhanced_agents import DataIntelligenceReport


@dataclass
class YuQingConfig:
    """YuQing-new系统配置"""
    base_url: str = "http://localhost:8000"
    timeout: float = 30.0
    max_retries: int = 3
    default_hours: int = 24
    default_limit: int = 50


class YuQingNewsAdapter:
    """
    YuQing-new新闻舆情适配器

    职责：
    1. 将YuQing-new的API接口适配为标准格式
    2. 提供统一的数据访问接口
    3. 处理数据格式转换和标准化
    4. 集成实体识别和情感分析结果
    """

    def __init__(self, config: YuQingConfig = None):
        # 允许通过环境变量覆盖默认配置
        if config is None:
            try:
                self.config = YuQingConfig(
                    base_url=os.getenv(
                        "YUQING_API_URL", YuQingConfig.base_url), timeout=float(
                        os.getenv(
                            "YUQING_TIMEOUT", str(
                                YuQingConfig.timeout))), max_retries=int(
                        os.getenv(
                            "YUQING_MAX_RETRIES", str(
                                YuQingConfig.max_retries))), default_hours=int(
                                    os.getenv(
                                        "YUQING_DEFAULT_HOURS", str(
                                            YuQingConfig.default_hours))), default_limit=int(
                                                os.getenv(
                                                    "YUQING_DEFAULT_LIMIT", str(
                                                        YuQingConfig.default_limit))), )
            except Exception:
                # 回退到类默认值，避免环境变量格式错误导致崩溃
                self.config = YuQingConfig()
        else:
            self.config = config
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout, limits=httpx.Limits(
                max_connections=10, max_keepalive_connections=5))

    async def aclose(self):
        """关闭HTTP客户端"""
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_comprehensive_sentiment_data(self,
                                               symbols: List[str] = None,
                                               keywords: List[str] = None,
                                               hours: int = 24,
                                               limit: int = 50) -> SentimentAnalysisReport:
        """
        获取综合舆情数据 - 核心对接方法

        Args:
            symbols: 股票代码列表
            keywords: 关键词列表
            hours: 时间范围(小时)
            limit: 返回数量限制

        Returns:
            SentimentAnalysisReport: 标准化的舆情分析报告
        """
        start_time = datetime.now()

        try:
            # 调用YuQing-new的综合数据API
            response = await self._client.get(
                f"{self.config.base_url}/api/news/comprehensive",
                params={
                    "hours": hours,
                    "limit": limit,
                    "include_entities": True,
                    "include_raw_data": False
                }
            )
            response.raise_for_status()

            yuqing_data = response.json()

            # 转换为标准格式
            return await self._convert_yuqing_to_standard_format(
                yuqing_data, symbols, keywords, start_time
            )

        except Exception as e:
            return self._create_error_report(str(e), start_time)

    async def get_entity_based_analysis(self,
                                        entity_type: str,
                                        impact_direction: str = None,
                                        time_horizon: str = None,
                                        limit: int = 20) -> Dict[str, Any]:
        """
        获取基于实体的分析数据

        Args:
            entity_type: 实体类型 (companies/persons/industries/events)
            impact_direction: 影响方向 (positive/negative/neutral)
            time_horizon: 时间范围 (short/medium/long)
            limit: 返回数量

        Returns:
            Dict: 实体分析数据
        """
        try:
            # 构建请求参数
            params = {"limit": limit}
            if impact_direction:
                params["impact_direction"] = impact_direction
            if time_horizon:
                params["time_horizon"] = time_horizon

            # 调用对应的实体API
            response = await self._client.get(
                f"{self.config.base_url}/api/entities/{entity_type}",
                params=params
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {"error": str(e), "data": []}

    async def get_stock_related_news(self, stock_codes: List[str], hours: int = 24) -> Dict[str, Any]:
        """
        获取特定股票相关的新闻数据

        Args:
            stock_codes: 股票代码列表
            hours: 时间范围

        Returns:
            Dict: 股票相关新闻数据
        """
        try:
            # 并行查询每个股票代码相关的公司实体
            tasks = []
            for stock_code in stock_codes:
                # 通过公司实体API查找相关新闻
                tasks.append(self._get_company_related_news(stock_code, hours))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 整合结果
            all_news = []
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    all_news.extend(result.get("news_data", []))

            # 去重处理（基于新闻ID）
            unique_news = {}
            for news in all_news:
                news_id = news.get("news", {}).get("id")
                if news_id and news_id not in unique_news:
                    unique_news[news_id] = news

            return {
                "stock_codes": stock_codes,
                "news_data": list(unique_news.values()),
                "total_found": len(unique_news),
                "time_range_hours": hours,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "stock_codes": stock_codes,
                "error": str(e),
                "news_data": [],
                "total_found": 0
            }

    async def get_market_hotspots(self, hours: int = 6, limit: int = 10) -> Dict[str, Any]:
        """
        获取市场热点发现

        Args:
            hours: 时间范围
            limit: 返回数量

        Returns:
            Dict: 市场热点数据
        """
        try:
            # 并行获取热点相关数据
            tasks = [
                self._client.get(f"{self.config.base_url}/api/analysis/hotspots/discover",
                                 params={"hours": hours, "limit": limit}),
                self._client.get(f"{self.config.base_url}/api/analysis/keywords/trending",
                                 params={"hours": hours, "limit": limit * 2}),
                self._client.get(f"{self.config.base_url}/api/analysis/stats/sentiment",
                                 params={"hours": hours})
            ]

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 解析结果
            hotspots = responses[0].json() if not isinstance(
                responses[0], Exception) else {"data": []}
            trending_keywords = responses[1].json() if not isinstance(
                responses[1], Exception) else {"data": []}
            sentiment_stats = responses[2].json() if not isinstance(
                responses[2], Exception) else {"data": {}}

            return {
                "hotspots": hotspots.get("data", []),
                "trending_keywords": trending_keywords.get("data", []),
                "sentiment_overview": sentiment_stats.get("data", {}),
                "time_range_hours": hours,
                "total_hotspots": len(hotspots.get("data", [])),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "error": str(e),
                "hotspots": [],
                "trending_keywords": [],
                "sentiment_overview": {}
            }

    async def extract_entities_from_text(self, text: str, enable_sentiment: bool = True) -> Dict[str, Any]:
        """
        从文本中提取实体信息

        Args:
            text: 要分析的文本
            enable_sentiment: 是否启用情感分析

        Returns:
            Dict: 实体提取结果
        """
        try:
            response = await self._client.post(
                f"{self.config.base_url}/api/entities/entities/extract",
                json={
                    "text": text,
                    "enable_sentiment": enable_sentiment
                }
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {
                "error": str(e),
                "entities": {
                    "companies": [],
                    "persons": [],
                    "industries": [],
                    "events": []
                }
            }

    async def _get_company_related_news(self, stock_code: str, hours: int) -> Dict[str, Any]:
        """获取特定股票代码相关的新闻"""
        try:
            # 首先通过公司实体API查找相关公司
            companies_response = await self._client.get(
                f"{self.config.base_url}/api/entities/companies",
                params={"limit": 100}  # 获取更多公司数据进行匹配
            )
            companies_response.raise_for_status()
            companies_data = companies_response.json()

            # 查找匹配的公司
            target_companies = []
            for company in companies_data.get("data", []):
                if (company.get("stock_code") == stock_code or
                        stock_code in str(company.get("stock_code", ""))):
                    target_companies.append(company)

            if not target_companies:
                return {"news_data": [], "company_matches": []}

            # 获取相关新闻
            news_response = await self._client.get(
                f"{self.config.base_url}/api/news/comprehensive",
                params={"hours": hours, "limit": 50, "include_entities": True}
            )
            news_response.raise_for_status()
            news_data = news_response.json()

            # 过滤相关新闻
            related_news = []
            for news_item in news_data.get("data", []):
                # 检查新闻中是否包含目标公司
                entity_analysis = news_item.get("entity_analysis", {})
                companies_in_news = entity_analysis.get("companies", [])

                for company in companies_in_news:
                    if (company.get("stock_code") == stock_code or any(
                            tc.get("company_name") == company.get("name") for tc in target_companies)):
                        related_news.append(news_item)
                        break

            return {
                "news_data": related_news,
                "company_matches": target_companies,
                "total_related": len(related_news)
            }

        except Exception as e:
            return {"error": str(e), "news_data": [], "company_matches": []}

    async def _convert_yuqing_to_standard_format(self,
                                                 yuqing_data: Dict[str, Any],
                                                 symbols: List[str],
                                                 keywords: List[str],
                                                 start_time: datetime) -> SentimentAnalysisReport:
        """将YuQing-new的数据格式转换为标准格式"""

        data_points = []

        # 转换数据点
        for item in yuqing_data.get("data", []):
            try:
                news = item.get("news", {})
                sentiment = item.get("sentiment_analysis", {})
                entities = item.get("entity_analysis", {})

                # 构建标准数据点
                data_point = SentimentDataPoint(
                    content_id=news.get("id", ""),
                    title=news.get("title", ""),
                    content=news.get("content", ""),
                    source=news.get("source", ""),
                    source_type=self._map_source_type(news.get("source", "")),
                    author=None,  # YuQing-new暂不提供作者信息
                    publish_time=datetime.fromisoformat(
                        news.get(
                            "published_at",
                            datetime.now().isoformat()).replace(
                            'Z',
                            '+00:00')),
                    url=news.get("source_url"),

                    # 情感分析数据
                    sentiment_score=self._convert_sentiment_to_score(
                        sentiment.get("sentiment_label", "neutral")),
                    sentiment_label=sentiment.get(
                        "sentiment_label", "neutral"),
                    confidence=sentiment.get("confidence_score", 0.0),

                    # 影响力指标（基于YuQing的market_impact_level推算）
                    view_count=None,
                    share_count=None,
                    comment_count=None,
                    influence_score=self._convert_impact_to_influence(
                        sentiment.get("market_impact_level", "medium")),

                    # 实体信息
                    mentioned_entities=self._extract_entities_list(entities),
                    mentioned_stocks=self._extract_stock_codes(
                        entities.get("companies", [])),
                    key_topics=self._extract_key_topics(
                        sentiment.get("analysis_result", {})),

                    # 质量指标
                    data_quality=0.9,  # YuQing-new的数据质量较高
                    relevance_score=self._calculate_relevance(
                        news, symbols, keywords),
                    credibility_score=0.8  # 基于来源的可信度评估
                )

                data_points.append(data_point)

            except Exception as e:
                continue  # 跳过格式异常的数据点

        # 构建聚合分析
        overall_sentiment = self._calculate_overall_sentiment(data_points)
        sentiment_trend = await self._get_sentiment_trend(hours=24)
        hot_topics = await self._get_hot_topics(limit=10)

        return SentimentAnalysisReport(
            query_summary={
                "symbols": symbols or [],
                "keywords": keywords or [],
                "time_range_hours": yuqing_data.get("summary", {}).get("time_range_hours", 24),
                "data_source": "YuQing-new"
            },
            data_points=data_points,
            overall_sentiment=overall_sentiment,
            sentiment_trend=sentiment_trend,
            hot_topics=hot_topics,
            influential_sources=self._identify_influential_sources(data_points),
            sentiment_anomalies=await self._detect_sentiment_anomalies(hours=24),
            volume_spikes=await self._detect_volume_spikes(hours=24),
            data_coverage=self._assess_data_coverage(yuqing_data),
            source_distribution=self._calculate_source_distribution(data_points),
            average_credibility=sum(dp.credibility_score for dp in data_points) / len(data_points) if data_points else 0.0,
            collection_time=datetime.now(),
            processing_duration=(datetime.now() - start_time).total_seconds(),
            total_processed=len(data_points)
        )

    async def get_stock_impact_analysis(self, stock_codes: List[str], hours: int = 24) -> Dict[str, Any]:
        """
        获取股票影响分析 - 专门为投研团队设计

        Args:
            stock_codes: 股票代码列表
            hours: 分析时间范围

        Returns:
            Dict: 股票影响分析结果
        """
        try:
            # 并行获取多个维度的数据
            tasks = [
                self.get_stock_related_news(stock_codes, hours),
                self.get_entity_based_analysis("companies", limit=100),
                self.get_entity_based_analysis("industries", limit=50),
                self.get_entity_based_analysis("events", limit=30),
                self.get_market_hotspots(hours, 20)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            stock_news = results[0] if not isinstance(
                results[0], Exception) else {}
            company_entities = results[1] if not isinstance(
                results[1], Exception) else {}
            industry_entities = results[2] if not isinstance(
                results[2], Exception) else {}
            event_entities = results[3] if not isinstance(
                results[3], Exception) else {}
            market_hotspots = results[4] if not isinstance(
                results[4], Exception) else {}

            # 为每个股票代码构建影响分析
            stock_impact_analysis = {}

            for stock_code in stock_codes:
                impact_analysis = await self._analyze_stock_specific_impact(
                    stock_code, stock_news, company_entities,
                    industry_entities, event_entities, market_hotspots
                )
                stock_impact_analysis[stock_code] = impact_analysis

            return {
                "stock_impact_analysis": stock_impact_analysis,
                "market_context": {
                    "hotspots": market_hotspots.get(
                        "hotspots",
                        []),
                    "trending_keywords": market_hotspots.get(
                        "trending_keywords",
                        []),
                    "sentiment_overview": market_hotspots.get(
                        "sentiment_overview",
                        {})},
                "analysis_metadata": {
                    "time_range_hours": hours,
                    "total_stocks_analyzed": len(stock_codes),
                    "data_freshness": "real_time",
                    "analysis_timestamp": datetime.now().isoformat()}}

        except Exception as e:
            return {
                "error": str(e),
                "stock_impact_analysis": {},
                "market_context": {}
            }

    async def _analyze_stock_specific_impact(self, stock_code: str, stock_news: Dict,
                                             company_entities: Dict, industry_entities: Dict,
                                             event_entities: Dict, market_hotspots: Dict) -> Dict[str, Any]:
        """分析特定股票的影响"""

        # 查找相关公司信息
        related_companies = []
        for company in company_entities.get("data", []):
            if company.get("stock_code") == stock_code:
                related_companies.append(company)

        # 查找相关新闻
        related_news = []
        for news_item in stock_news.get("news_data", []):
            entity_analysis = news_item.get("entity_analysis", {})
            companies_in_news = entity_analysis.get("companies", [])

            for company in companies_in_news:
                if company.get("stock_code") == stock_code:
                    related_news.append(news_item)
                    break

        # 计算影响指标
        sentiment_scores = []
        impact_magnitudes = []

        for news in related_news:
            sentiment = news.get("sentiment_analysis", {})
            if sentiment.get("sentiment_label"):
                sentiment_scores.append(
                    self._convert_sentiment_to_score(
                        sentiment["sentiment_label"]))

            # 从实体分析中提取影响强度
            entity_analysis = news.get("entity_analysis", {})
            for company in entity_analysis.get("companies", []):
                if company.get("stock_code") == stock_code:
                    impact_magnitudes.append(
                        company.get("impact_magnitude", 0.5))

        # 计算综合影响
        avg_sentiment = sum(sentiment_scores) / \
            len(sentiment_scores) if sentiment_scores else 0.0
        avg_impact = sum(impact_magnitudes) / \
            len(impact_magnitudes) if impact_magnitudes else 0.0

        return {
            "stock_code": stock_code,
            "related_companies": related_companies,
            "related_news_count": len(related_news),
            "sentiment_analysis": {
                "average_sentiment_score": avg_sentiment,
                "sentiment_distribution": self._calculate_sentiment_distribution(sentiment_scores),
                "sentiment_trend": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral"
            },
            "impact_assessment": {
                "average_impact_magnitude": avg_impact,
                "impact_direction": "positive" if avg_sentiment > 0 else "negative" if avg_sentiment < 0 else "neutral",
                "confidence_level": min(0.9, max(0.1, abs(avg_sentiment) + avg_impact) / 2)
            },
            "recent_news_headlines": [news.get("news", {}).get("title", "") for news in related_news[:5]],
            "key_events": self._extract_key_events_for_stock(stock_code, event_entities),
            "industry_context": self._get_industry_context_for_stock(stock_code, industry_entities)
        }

    def _map_source_type(self, source: str) -> str:
        """映射数据源类型"""
        source_mapping = {
            "cailian": "financial_news",
            "google_news": "news",
            "hot_discovery": "trending_news",
            "sina": "news",
            "eastmoney": "financial_news"
        }
        return source_mapping.get(source, "unknown")

    def _convert_sentiment_to_score(self, sentiment_label: str) -> float:
        """将情感标签转换为数值分数"""
        mapping = {
            "positive": 0.7,
            "negative": -0.7,
            "neutral": 0.0
        }
        return mapping.get(sentiment_label, 0.0)

    def _convert_impact_to_influence(self, impact_level: str) -> float:
        """将影响级别转换为影响力分数"""
        mapping = {
            "high": 0.9,
            "medium": 0.6,
            "low": 0.3,
            "negligible": 0.1
        }
        return mapping.get(impact_level, 0.5)

    def _extract_entities_list(
            self, entities: Dict[str, Any]) -> List[Dict[str, str]]:
        """提取实体列表"""
        entity_list = []

        for company in entities.get("companies", []):
            entity_list.append({
                "type": "company",
                "name": company.get("name", ""),
                "code": company.get("stock_code", "")
            })

        for person in entities.get("persons", []):
            entity_list.append({
                "type": "person",
                "name": person.get("name", ""),
                "role": person.get("position_title", "")
            })

        for industry in entities.get("industries", []):
            entity_list.append({
                "type": "industry",
                "name": industry.get("name", ""),
                "code": industry.get("industry_code", "")
            })

        return entity_list

    def _extract_stock_codes(self, companies: List[Dict]) -> List[str]:
        """提取股票代码列表"""
        stock_codes = []
        for company in companies:
            code = company.get("stock_code")
            if code:
                stock_codes.append(code)
        return list(set(stock_codes))  # 去重

    def _extract_key_topics(self, analysis_result: Dict) -> List[str]:
        """提取关键主题"""
        topics = []

        # 从分析结果中提取关键词
        keywords = analysis_result.get("keywords", [])
        if keywords:
            topics.extend(keywords[:5])  # 取前5个关键词

        # 从摘要中提取主题
        summary = analysis_result.get("summary", "")
        if summary:
            # 简单的主题提取逻辑
            import re
            topics_from_summary = re.findall(r'[\u4e00-\u9fff]{2,}', summary)
            topics.extend(topics_from_summary[:3])

        return list(set(topics))[:8]  # 去重并限制数量

    def _calculate_relevance(
            self,
            news: Dict,
            symbols: List[str],
            keywords: List[str]) -> float:
        """计算新闻相关性"""
        relevance_score = 0.5  # 基础分数

        title = news.get("title", "").lower()
        content = news.get("content", "").lower()

        # 关键词匹配
        if keywords:
            for keyword in keywords:
                if keyword.lower() in title:
                    relevance_score += 0.2
                elif keyword.lower() in content:
                    relevance_score += 0.1

        # 股票代码匹配（通过实体分析结果）
        if symbols:
            # 这里需要更复杂的逻辑来匹配股票代码
            # 暂时使用简单的文本匹配
            for symbol in symbols:
                if symbol in title or symbol in content:
                    relevance_score += 0.3

        return min(1.0, relevance_score)

    def _calculate_overall_sentiment(
            self, data_points: List[SentimentDataPoint]) -> Dict[str, float]:
        """计算整体情感分布"""
        if not data_points:
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34}

        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

        for dp in data_points:
            sentiment_counts[dp.sentiment_label] += 1

        total = len(data_points)
        return {
            "positive": sentiment_counts["positive"] / total,
            "negative": sentiment_counts["negative"] / total,
            "neutral": sentiment_counts["neutral"] / total
        }

    async def _get_sentiment_trend(self, hours: int) -> List[Dict[str, Any]]:
        """获取情感趋势数据"""
        try:
            response = await self._client.get(
                f"{self.config.base_url}/api/analysis/stats/timeline",
                params={"hours": hours, "interval": "hour"}
            )
            response.raise_for_status()

            timeline_data = response.json()
            return timeline_data.get("data", [])

        except Exception:
            return []

    async def _get_hot_topics(self, limit: int) -> List[Dict[str, Any]]:
        """获取热门话题"""
        try:
            response = await self._client.get(
                f"{self.config.base_url}/api/analysis/keywords/trending",
                params={"limit": limit, "hours": 24}
            )
            response.raise_for_status()

            keywords_data = response.json()
            return keywords_data.get("data", [])

        except Exception:
            return []

    def _identify_influential_sources(
            self, data_points: List[SentimentDataPoint]) -> List[Dict[str, Any]]:
        """识别有影响力的信息源"""
        source_influence = {}

        for dp in data_points:
            source = dp.source
            if source not in source_influence:
                source_influence[source] = {
                    "source": source,
                    "count": 0,
                    "avg_influence": 0.0,
                    "total_influence": 0.0
                }

            source_influence[source]["count"] += 1
            source_influence[source]["total_influence"] += dp.influence_score

        # 计算平均影响力
        for source_data in source_influence.values():
            if source_data["count"] > 0:
                source_data["avg_influence"] = source_data["total_influence"] / \
                    source_data["count"]

        # 按影响力排序
        sorted_sources = sorted(
            source_influence.values(),
            key=lambda x: x["avg_influence"],
            reverse=True
        )

        return sorted_sources[:10]

    async def _detect_sentiment_anomalies(self, hours: int) -> List[Dict[str, Any]]:
        """检测情感异常"""
        try:
            # 获取情感统计数据
            response = await self._client.get(
                f"{self.config.base_url}/api/analysis/stats/sentiment",
                params={"hours": hours}
            )
            response.raise_for_status()

            sentiment_stats = response.json()

            # 简单的异常检测逻辑
            anomalies = []
            data = sentiment_stats.get("data", {})

            # 检测极端情感偏向
            positive_ratio = data.get("positive_ratio", 0.33)
            negative_ratio = data.get("negative_ratio", 0.33)

            if positive_ratio > 0.7:
                anomalies.append({
                    "type": "extreme_positive",
                    "description": f"异常高的正面情感比例: {positive_ratio:.2%}",
                    "severity": "medium"
                })

            if negative_ratio > 0.7:
                anomalies.append({
                    "type": "extreme_negative",
                    "description": f"异常高的负面情感比例: {negative_ratio:.2%}",
                    "severity": "high"
                })

            return anomalies

        except Exception:
            return []

    async def _detect_volume_spikes(self, hours: int) -> List[Dict[str, Any]]:
        """检测音量激增"""
        try:
            # 获取新闻统计数据
            response = await self._client.get(
                f"{self.config.base_url}/api/news/stats",
                params={"hours": hours}
            )
            response.raise_for_status()

            stats_data = response.json()

            # 简单的音量激增检测
            spikes = []
            recent_24h = stats_data.get("recent_24h", 0)
            total_news = stats_data.get("total_news", 0)

            # 如果最近24小时的新闻量占总量的比例过高，认为是音量激增
            if total_news > 0:
                recent_ratio = recent_24h / total_news
                if recent_ratio > 0.6:  # 60%的新闻都是最近24小时的
                    spikes.append({
                        "type": "news_volume_spike",
                        "description": f"新闻量激增: 最近24小时占比{recent_ratio:.2%}",
                        "magnitude": recent_ratio,
                        "timeframe": "24h"
                    })

            return spikes

        except Exception:
            return []

    def _assess_data_coverage(self, yuqing_data: Dict) -> Dict[str, float]:
        """评估数据覆盖度"""
        summary = yuqing_data.get("summary", {})

        return {
            "news_coverage": 1.0 if summary.get("total_analyzed", 0) > 0 else 0.0,
            "entity_coverage": 1.0 if summary.get("entities_included", False) else 0.0,
            "sentiment_coverage": 1.0,  # YuQing-new始终提供情感分析
            "temporal_coverage": min(1.0, summary.get("time_range_hours", 0) / 24.0)
        }

    def _calculate_source_distribution(
            self, data_points: List[SentimentDataPoint]) -> Dict[str, int]:
        """计算数据源分布"""
        distribution = {}

        for dp in data_points:
            source = dp.source
            distribution[source] = distribution.get(source, 0) + 1

        return distribution

    def _calculate_sentiment_distribution(
            self, sentiment_scores: List[float]) -> Dict[str, float]:
        """计算情感分布"""
        if not sentiment_scores:
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34}

        positive_count = sum(1 for score in sentiment_scores if score > 0.1)
        negative_count = sum(1 for score in sentiment_scores if score < -0.1)
        neutral_count = len(sentiment_scores) - positive_count - negative_count

        total = len(sentiment_scores)
        return {
            "positive": positive_count / total,
            "negative": negative_count / total,
            "neutral": neutral_count / total
        }

    def _extract_key_events_for_stock(
            self, stock_code: str, event_entities: Dict) -> List[Dict[str, Any]]:
        """提取特定股票的关键事件"""
        relevant_events = []

        for event in event_entities.get("data", []):
            # 检查事件是否与目标股票相关
            primary_companies = event.get("primary_companies", [])
            secondary_companies = event.get("secondary_companies", [])

            if (any(stock_code in str(company) for company in primary_companies) or any(
                    stock_code in str(company) for company in secondary_companies)):
                relevant_events.append({
                    "event_type": event.get("event_type", ""),
                    "description": event.get("event_description", ""),
                    "market_significance": event.get("market_significance", ""),
                    "expected_volatility": event.get("expected_volatility", "")
                })

        return relevant_events[:5]  # 返回前5个相关事件

    def _get_industry_context_for_stock(
            self, stock_code: str, industry_entities: Dict) -> Dict[str, Any]:
        """获取股票的行业背景"""
        # 这里需要通过股票代码查找对应的行业
        # 简化实现，实际项目中需要维护股票-行业映射表

        return {
            "primary_industry": "待映射",
            "industry_sentiment": "neutral",
            "industry_trends": [],
            "competitive_landscape": "需要行业数据支撑"
        }

    def _create_error_report(
            self,
            error_msg: str,
            start_time: datetime) -> SentimentAnalysisReport:
        """创建错误报告"""
        return SentimentAnalysisReport(
            query_summary={
                "error": error_msg,
                "data_source": "YuQing-new"},
            data_points=[],
            overall_sentiment={
                "positive": 0.0,
                "negative": 0.0,
                "neutral": 1.0},
            sentiment_trend=[],
            hot_topics=[],
            influential_sources=[],
            sentiment_anomalies=[],
            volume_spikes=[],
            data_coverage={},
            source_distribution={},
            average_credibility=0.0,
            collection_time=datetime.now(),
            processing_duration=(
                datetime.now() -
                start_time).total_seconds(),
            total_processed=0)
