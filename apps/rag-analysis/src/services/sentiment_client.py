"""
舆情收集API客户端
与团队舆情收集部门的专业API集成，提供实时舆情数据支撑
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


@dataclass
class SentimentQueryParam:
    """舆情查询参数 - 遵循Param命名约定"""
    keywords: List[str]
    symbols: List[str] = None
    time_range: str = "24h"  # 1h, 6h, 24h, 7d, 30d
    data_sources: List[str] = None  # news, social, research, regulatory
    sentiment_threshold: float = 0.0
    language: str = "zh"
    region: str = "CN"
    max_results: int = 100
    include_analysis: bool = True


@dataclass
class SentimentDataPoint:
    """单条舆情数据点 - BO"""
    content_id: str
    title: str
    content: str
    source: str
    source_type: str  # news, weibo, wechat, research_report, regulatory
    author: Optional[str]
    publish_time: datetime
    url: Optional[str]

    # 情感分析结果
    sentiment_score: float  # -1 to 1
    sentiment_label: str   # positive, negative, neutral
    confidence: float      # 0 to 1

    # 影响力指标
    view_count: Optional[int]
    share_count: Optional[int]
    comment_count: Optional[int]
    influence_score: float  # 0 to 1

    # 实体识别
    mentioned_entities: List[Dict[str, str]]
    mentioned_stocks: List[str]
    key_topics: List[str]

    # 元数据
    data_quality: float
    relevance_score: float
    credibility_score: float


@dataclass
class SentimentAnalysisReport:
    """舆情分析报告 - BO"""
    query_summary: Dict[str, Any]
    data_points: List[SentimentDataPoint]

    # 聚合分析
    # positive, negative, neutral percentages
    overall_sentiment: Dict[str, float]
    sentiment_trend: List[Dict[str, Any]]  # time series sentiment
    hot_topics: List[Dict[str, Any]]
    influential_sources: List[Dict[str, Any]]

    # 异常检测
    sentiment_anomalies: List[Dict[str, Any]]
    volume_spikes: List[Dict[str, Any]]

    # 质量指标
    data_coverage: Dict[str, float]
    source_distribution: Dict[str, int]
    average_credibility: float

    # 元信息
    collection_time: datetime
    processing_duration: float
    total_processed: int


class SentimentAPIClient:
    """舆情API客户端 - 专业级数据接入"""

    def __init__(self,
                 base_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 timeout: float = 30.0,
                 max_retries: int = 3):
        """
        初始化舆情API客户端

        Args:
            base_url: 舆情API基础URL
            api_key: API密钥
            timeout: 请求超时时间
            max_retries: 最大重试次数
        """
        self.base_url = base_url or os.getenv(
            "SENTIMENT_API_URL", "http://localhost:9001")
        self.api_key = api_key or os.getenv("SENTIMENT_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries

        # 创建HTTP客户端
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "InvestmentResearch-Agent/1.0"
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._client = httpx.AsyncClient(
            timeout=timeout, headers=headers, limits=httpx.Limits(
                max_connections=10, max_keepalive_connections=5))

    async def aclose(self):
        """关闭客户端连接"""
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def query_sentiment_data(self, query_param: SentimentQueryParam) -> SentimentAnalysisReport:
        """
        查询舆情数据 - 主要接口

        Args:
            query_param: 查询参数

        Returns:
            SentimentAnalysisReport: 舆情分析报告
        """
        start_time = datetime.now()

        try:
            # 构建请求载荷
            payload = self._build_query_payload(query_param)

            # 发送请求
            response = await self._client.post(
                f"{self.base_url}/api/v1/sentiment/query",
                json=payload
            )
            response.raise_for_status()

            # 解析响应
            data = response.json()

            # 转换为标准格式
            report = self._parse_sentiment_response(data, start_time)

            return report

        except Exception as e:
            # 记录错误并返回空报告
            return self._create_empty_report(query_param, str(e), start_time)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_real_time_sentiment(self, symbols: List[str],
                                      time_window: str = "1h") -> Dict[str, Any]:
        """
        获取实时舆情摘要

        Args:
            symbols: 股票代码列表
            time_window: 时间窗口

        Returns:
            Dict: 实时舆情摘要
        """
        try:
            payload = {
                "symbols": symbols,
                "time_window": time_window,
                "metrics": ["sentiment_score", "volume", "trend", "alerts"]
            }

            response = await self._client.post(
                f"{self.base_url}/api/v1/sentiment/realtime",
                json=payload
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {
                "symbols": symbols,
                "sentiment_summary": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_news_flow_analysis(self, keywords: List[str],
                                     time_range: str = "24h") -> Dict[str, Any]:
        """
        获取新闻流分析

        Args:
            keywords: 关键词列表
            time_range: 时间范围

        Returns:
            Dict: 新闻流分析结果
        """
        try:
            payload = {
                "keywords": keywords,
                "time_range": time_range,
                "analysis_types": [
                    "sentiment",
                    "impact",
                    "credibility",
                    "propagation"]}

            response = await self._client.post(
                f"{self.base_url}/api/v1/news/flow-analysis",
                json=payload
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {
                "keywords": keywords,
                "news_flow": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_social_media_buzz(self, symbols: List[str],
                                    platforms: List[str] = None) -> Dict[str, Any]:
        """
        获取社交媒体热度分析

        Args:
            symbols: 股票代码
            platforms: 社交平台列表 [weibo, wechat, zhihu, xueqiu]

        Returns:
            Dict: 社交媒体分析结果
        """
        if platforms is None:
            platforms = ["weibo", "wechat", "zhihu", "xueqiu"]

        try:
            payload = {
                "symbols": symbols,
                "platforms": platforms,
                "metrics": [
                    "mention_volume",
                    "sentiment",
                    "influencer_activity",
                    "viral_content"]}

            response = await self._client.post(
                f"{self.base_url}/api/v1/social/buzz-analysis",
                json=payload
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {
                "symbols": symbols,
                "social_buzz": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_research_sentiment(self, symbols: List[str]) -> Dict[str, Any]:
        """
        获取研报情感分析

        Args:
            symbols: 股票代码列表

        Returns:
            Dict: 研报情感分析结果
        """
        try:
            payload = {
                "symbols": symbols,
                "report_types": [
                    "analyst_report",
                    "institution_research",
                    "rating_change"],
                "time_range": "30d"}

            response = await self._client.post(
                f"{self.base_url}/api/v1/research/sentiment",
                json=payload
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            return {
                "symbols": symbols,
                "research_sentiment": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }

    async def get_comprehensive_sentiment_report(self,
                                                 symbols: List[str],
                                                 keywords: List[str] = None,
                                                 time_range: str = "24h") -> SentimentAnalysisReport:
        """
        获取综合舆情报告 - 整合多个数据源

        Args:
            symbols: 股票代码列表
            keywords: 关键词列表
            time_range: 时间范围

        Returns:
            SentimentAnalysisReport: 综合舆情报告
        """
        start_time = datetime.now()

        # 并行获取多个数据源
        tasks = [
            self.get_real_time_sentiment(symbols, time_range),
            self.get_social_media_buzz(symbols),
            self.get_research_sentiment(symbols)
        ]

        if keywords:
            tasks.append(self.get_news_flow_analysis(keywords, time_range))

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 整合结果
            realtime_sentiment = results[0] if not isinstance(
                results[0], Exception) else {}
            social_buzz = results[1] if not isinstance(
                results[1], Exception) else {}
            research_sentiment = results[2] if not isinstance(
                results[2], Exception) else {}
            news_flow = results[3] if len(results) > 3 and not isinstance(
                results[3], Exception) else {}

            # 构建综合报告
            return self._build_comprehensive_report(
                symbols, keywords, time_range,
                realtime_sentiment, social_buzz, research_sentiment, news_flow,
                start_time
            )

        except Exception as e:
            return self._create_empty_report(
                SentimentQueryParam(
                    keywords=keywords or [],
                    symbols=symbols,
                    time_range=time_range),
                str(e),
                start_time)

    def _build_query_payload(
            self, query_param: SentimentQueryParam) -> Dict[str, Any]:
        """构建查询载荷"""
        return {
            "keywords": query_param.keywords,
            "symbols": query_param.symbols or [],
            "time_range": query_param.time_range,
            "data_sources": query_param.data_sources or [
                "news",
                "social",
                "research"],
            "sentiment_threshold": query_param.sentiment_threshold,
            "language": query_param.language,
            "region": query_param.region,
            "max_results": query_param.max_results,
            "include_analysis": query_param.include_analysis}

    def _parse_sentiment_response(self, data: Dict[str, Any],
                                  start_time: datetime) -> SentimentAnalysisReport:
        """解析舆情API响应"""
        data_points = []

        # 解析数据点
        for item in data.get("data_points", []):
            try:
                data_point = SentimentDataPoint(
                    content_id=item.get(
                        "id",
                        ""),
                    title=item.get(
                        "title",
                        ""),
                    content=item.get(
                        "content",
                        ""),
                    source=item.get(
                        "source",
                        ""),
                    source_type=item.get(
                        "source_type",
                        "unknown"),
                    author=item.get("author"),
                    publish_time=datetime.fromisoformat(
                        item.get(
                            "publish_time",
                            datetime.now().isoformat())),
                    url=item.get("url"),
                    sentiment_score=item.get(
                        "sentiment_score",
                        0.0),
                    sentiment_label=item.get(
                        "sentiment_label",
                        "neutral"),
                    confidence=item.get(
                        "confidence",
                        0.0),
                    view_count=item.get("view_count"),
                    share_count=item.get("share_count"),
                    comment_count=item.get("comment_count"),
                    influence_score=item.get(
                        "influence_score",
                        0.0),
                    mentioned_entities=item.get(
                        "mentioned_entities",
                        []),
                    mentioned_stocks=item.get(
                        "mentioned_stocks",
                        []),
                    key_topics=item.get(
                        "key_topics",
                        []),
                    data_quality=item.get(
                        "data_quality",
                        0.7),
                    relevance_score=item.get(
                        "relevance_score",
                        0.5),
                    credibility_score=item.get(
                        "credibility_score",
                        0.5))
                data_points.append(data_point)
            except Exception:
                continue  # 跳过解析失败的数据点

        # 构建报告
        return SentimentAnalysisReport(
            query_summary=data.get("query_summary", {}),
            data_points=data_points,
            overall_sentiment=data.get("overall_sentiment", {}),
            sentiment_trend=data.get("sentiment_trend", []),
            hot_topics=data.get("hot_topics", []),
            influential_sources=data.get("influential_sources", []),
            sentiment_anomalies=data.get("sentiment_anomalies", []),
            volume_spikes=data.get("volume_spikes", []),
            data_coverage=data.get("data_coverage", {}),
            source_distribution=data.get("source_distribution", {}),
            average_credibility=data.get("average_credibility", 0.7),
            collection_time=datetime.now(),
            processing_duration=(datetime.now() - start_time).total_seconds(),
            total_processed=len(data_points)
        )

    def _build_comprehensive_report(
            self,
            symbols: List[str],
            keywords: List[str],
            time_range: str,
            realtime_sentiment: Dict,
            social_buzz: Dict,
            research_sentiment: Dict,
            news_flow: Dict,
            start_time: datetime) -> SentimentAnalysisReport:
        """构建综合舆情报告"""
        # 简化实现，实际项目中需要更复杂的数据整合逻辑
        data_points = []

        # 整合各数据源的数据点
        for source_name, source_data in [
            ("realtime", realtime_sentiment),
            ("social", social_buzz),
            ("research", research_sentiment),
            ("news", news_flow)
        ]:
            if "data_points" in source_data:
                data_points.extend(source_data["data_points"])

        return SentimentAnalysisReport(
            query_summary={
                "symbols": symbols,
                "keywords": keywords or [],
                "time_range": time_range,
                "data_sources": ["realtime", "social", "research", "news"]
            },
            data_points=data_points,
            overall_sentiment=self._aggregate_sentiment(
                [realtime_sentiment, social_buzz, research_sentiment]),
            sentiment_trend=realtime_sentiment.get("sentiment_trend", []),
            hot_topics=news_flow.get("hot_topics", []),
            influential_sources=social_buzz.get("influential_sources", []),
            sentiment_anomalies=realtime_sentiment.get("anomalies", []),
            volume_spikes=social_buzz.get("volume_spikes", []),
            data_coverage={
                "realtime": 1.0 if realtime_sentiment else 0.0,
                "social": 1.0 if social_buzz else 0.0,
                "research": 1.0 if research_sentiment else 0.0,
                "news": 1.0 if news_flow else 0.0
            },
            source_distribution={
                "total_sources": len([s for s in [realtime_sentiment, social_buzz, research_sentiment, news_flow] if s])
            },
            average_credibility=0.8,  # 基于数据源质量的估计
            collection_time=datetime.now(),
            processing_duration=(datetime.now() - start_time).total_seconds(),
            total_processed=len(data_points)
        )

    def _aggregate_sentiment(
            self, source_data_list: List[Dict]) -> Dict[str, float]:
        """聚合多源情感数据"""
        sentiments = []
        for data in source_data_list:
            if "overall_sentiment" in data:
                sentiments.append(data["overall_sentiment"])

        if not sentiments:
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34}

        # 简单平均，实际项目中可能需要加权平均
        avg_sentiment = {
            "positive": sum(
                s.get(
                    "positive",
                    0) for s in sentiments) /
            len(sentiments),
            "negative": sum(
                s.get(
                    "negative",
                    0) for s in sentiments) /
            len(sentiments),
            "neutral": sum(
                s.get(
                    "neutral",
                    0) for s in sentiments) /
            len(sentiments)}

        return avg_sentiment

    def _create_empty_report(
            self,
            query_param: SentimentQueryParam,
            error_msg: str,
            start_time: datetime) -> SentimentAnalysisReport:
        """创建空的错误报告"""
        return SentimentAnalysisReport(
            query_summary={
                "error": error_msg,
                "keywords": query_param.keywords,
                "symbols": query_param.symbols or [],
                "time_range": query_param.time_range},
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
