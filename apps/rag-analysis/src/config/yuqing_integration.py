"""
YuQing-new系统集成配置
管理两个系统之间的对接参数和映射关系
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class YuQingIntegrationConfig:
    """YuQing-new集成配置"""

    # 基础连接配置
    yuqing_base_url: str = "http://localhost:8000"
    yuqing_timeout: float = 30.0
    yuqing_max_retries: int = 3

    # API端点配置
    api_endpoints: Dict[str, str] = field(default_factory=lambda: {
        "comprehensive": "/api/news/comprehensive",
        "companies": "/api/entities/companies",
        "industries": "/api/entities/industries",
        "events": "/api/entities/events",
        "persons": "/api/entities/persons",
        "hotspots": "/api/analysis/hotspots/discover",
        "trending": "/api/analysis/keywords/trending",
        "sentiment_stats": "/api/analysis/stats/sentiment",
        "entity_extract": "/api/entities/entities/extract",
        "news_stats": "/api/news/stats"
    })

    # 数据获取参数
    default_news_limit: int = 50
    default_entity_limit: int = 30
    default_hotspot_limit: int = 15
    max_content_length: int = 2000

    # 时间映射配置
    time_horizon_mapping: Dict[str, int] = field(default_factory=lambda: {
        "immediate": 1,    # 1小时
        "short": 6,        # 6小时
        "medium": 24,      # 24小时
        "long": 168,       # 1周
        "extended": 720    # 30天
    })

    # 数据源权重配置
    source_weights: Dict[str, float] = field(default_factory=lambda: {
        "cailian": 0.95,        # 财联社 - 最高权威性
        "google_news": 0.75,    # Google News - 中高权重
        "hot_discovery": 0.85,  # 热点发现 - 高权重
        "sina": 0.70,          # 新浪财经 - 中等权重
        "eastmoney": 0.80,     # 东方财富 - 较高权重
        "unknown": 0.50        # 未知来源 - 基础权重
    })

    # 情感分析配置
    sentiment_mapping: Dict[str, float] = field(default_factory=lambda: {
        "positive": 0.7,
        "negative": -0.7,
        "neutral": 0.0
    })

    # 影响级别映射
    impact_level_mapping: Dict[str, float] = field(default_factory=lambda: {
        "high": 0.9,
        "medium": 0.6,
        "low": 0.3,
        "negligible": 0.1
    })

    # 实体过滤配置
    entity_filters: Dict[str, Any] = field(default_factory=lambda: {
        "min_confidence": 0.6,
        "min_impact_magnitude": 0.3,
        "max_entities_per_type": 20,
        "include_indirect_impact": True
    })

    # 股票代码映射表（重要！）
    stock_code_mapping: Dict[str, str] = field(default_factory=lambda: {
        # 主要A股
        "中国平安": "000001.SZ",
        "万科A": "000002.SZ",
        "招商银行": "600036.SH",
        "工商银行": "601398.SH",
        "建设银行": "601939.SH",
        "中国银行": "601988.SH",
        "农业银行": "601288.SH",
        "中国石化": "600028.SH",
        "中国石油": "601857.SH",
        "中国移动": "600941.SH",

        # 科技股
        "腾讯控股": "00700.HK",
        "阿里巴巴": "09988.HK",
        "美团": "03690.HK",
        "小米集团": "01810.HK",
        "比亚迪": "002594.SZ",
        "宁德时代": "300750.SZ",
        "海康威视": "002415.SZ",
        "立讯精密": "002475.SZ",
        "恒瑞医药": "600276.SH",
        "药明康德": "603259.SH",

        # 消费股
        "贵州茅台": "600519.SH",
        "五粮液": "000858.SZ",
        "伊利股份": "600887.SH",
        "海天味业": "603288.SH",
        "格力电器": "000651.SZ",
        "美的集团": "000333.SZ"
    })

    # 行业代码映射
    industry_code_mapping: Dict[str, str] = field(default_factory=lambda: {
        "银行": "BANK",
        "保险": "INSURANCE",
        "证券": "SECURITIES",
        "房地产": "REAL_ESTATE",
        "科技": "TECHNOLOGY",
        "医药": "HEALTHCARE",
        "消费": "CONSUMER",
        "能源": "ENERGY",
        "制造": "MANUFACTURING",
        "电信": "TELECOM"
    })

    # 缓存配置
    cache_config: Dict[str, Any] = field(default_factory=lambda: {
        "enable_caching": True,
        "cache_ttl_seconds": 300,  # 5分钟缓存
        "max_cache_size": 1000,
        "cache_key_prefix": "yuqing_cache:"
    })

    # 错误处理配置
    error_handling: Dict[str, Any] = field(default_factory=lambda: {
        "enable_fallback": True,
        "max_error_rate": 0.1,  # 10%错误率阈值
        "circuit_breaker_threshold": 5,  # 连续5次失败后熔断
        "recovery_timeout_seconds": 60,
        "default_sentiment": {"positive": 0.33, "negative": 0.33, "neutral": 0.34}
    })

    @classmethod
    def from_env(cls) -> "YuQingIntegrationConfig":
        """从环境变量创建配置"""
        return cls(
            yuqing_base_url=os.getenv(
                "YUQING_API_URL",
                "http://localhost:8000"),
            yuqing_timeout=float(
                os.getenv(
                    "YUQING_TIMEOUT",
                    "30.0")),
            yuqing_max_retries=int(
                os.getenv(
                    "YUQING_MAX_RETRIES",
                    "3")),
            default_news_limit=int(
                os.getenv(
                    "YUQING_NEWS_LIMIT",
                    "50")),
            default_entity_limit=int(
                os.getenv(
                    "YUQING_ENTITY_LIMIT",
                    "30")))

    def get_api_url(self, endpoint_key: str) -> str:
        """获取完整的API URL"""
        endpoint = self.api_endpoints.get(endpoint_key, "")
        return f"{self.yuqing_base_url}{endpoint}"

    def map_company_to_stock_code(self, company_name: str) -> Optional[str]:
        """将公司名称映射为股票代码"""
        # 精确匹配
        if company_name in self.stock_code_mapping:
            return self.stock_code_mapping[company_name]

        # 模糊匹配
        for mapped_name, stock_code in self.stock_code_mapping.items():
            if company_name in mapped_name or mapped_name in company_name:
                return stock_code

        return None

    def map_industry_to_code(self, industry_name: str) -> Optional[str]:
        """将行业名称映射为行业代码"""
        return self.industry_code_mapping.get(industry_name)

    def get_source_weight(self, source: str) -> float:
        """获取数据源权重"""
        return self.source_weights.get(source, 0.5)

    def get_sentiment_score(self, sentiment_label: str) -> float:
        """获取情感数值分数"""
        return self.sentiment_mapping.get(sentiment_label, 0.0)

    def get_impact_score(self, impact_level: str) -> float:
        """获取影响力数值分数"""
        return self.impact_level_mapping.get(impact_level, 0.5)

    def should_include_entity(self, entity: Dict[str, Any]) -> bool:
        """判断是否应该包含某个实体"""
        confidence = entity.get("confidence", 0.0)
        impact_magnitude = entity.get("impact_magnitude", 0.0)

        return (confidence >= self.entity_filters["min_confidence"] and
                impact_magnitude >= self.entity_filters["min_impact_magnitude"])


@dataclass
class IntegrationMetrics:
    """集成性能指标"""

    # API调用统计
    total_api_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0

    # 响应时间统计
    total_response_time: float = 0.0
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')

    # 数据质量统计
    total_data_points: int = 0
    valid_data_points: int = 0
    data_quality_scores: List[float] = field(default_factory=list)

    # 错误统计
    error_types: Dict[str, int] = field(default_factory=dict)
    last_error_time: Optional[str] = None

    def record_api_call(
            self,
            success: bool,
            response_time: float,
            error_type: str = None):
        """记录API调用"""
        self.total_api_calls += 1

        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(
                    error_type, 0) + 1
            self.last_error_time = datetime.now().isoformat()

        # 更新响应时间统计
        self.total_response_time += response_time
        self.avg_response_time = self.total_response_time / self.total_api_calls
        self.max_response_time = max(self.max_response_time, response_time)
        self.min_response_time = min(self.min_response_time, response_time)

    def record_data_quality(self, data_points: int, quality_score: float):
        """记录数据质量"""
        self.total_data_points += data_points
        if quality_score > 0:
            self.valid_data_points += data_points
            self.data_quality_scores.append(quality_score)

    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.successful_calls / \
            self.total_api_calls if self.total_api_calls > 0 else 0.0

    @property
    def average_data_quality(self) -> float:
        """平均数据质量"""
        return sum(self.data_quality_scores) / \
            len(self.data_quality_scores) if self.data_quality_scores else 0.0

    def get_health_status(self) -> str:
        """获取健康状态"""
        if self.success_rate > 0.95 and self.average_data_quality > 0.8:
            return "excellent"
        elif self.success_rate > 0.90 and self.average_data_quality > 0.7:
            return "good"
        elif self.success_rate > 0.80:
            return "fair"
        else:
            return "poor"


# 全局配置实例
yuqing_integration_config = YuQingIntegrationConfig.from_env()
integration_metrics = IntegrationMetrics()


def get_yuqing_config() -> YuQingIntegrationConfig:
    """获取YuQing集成配置"""
    return yuqing_integration_config


def get_integration_metrics() -> IntegrationMetrics:
    """获取集成性能指标"""
    return integration_metrics


# 辅助函数
def validate_stock_symbols(symbols: List[str]) -> List[str]:
    """验证和标准化股票代码"""
    validated = []

    for symbol in symbols:
        # 移除空格和特殊字符
        clean_symbol = symbol.strip().upper()

        # 基本格式验证
        if len(clean_symbol) >= 6 and (
            clean_symbol.endswith('.SZ') or
            clean_symbol.endswith('.SH') or
            clean_symbol.endswith('.HK') or
            clean_symbol.isdigit()
        ):
            validated.append(clean_symbol)

    return validated


def extract_stock_codes_from_entities(entities: Dict[str, List]) -> List[str]:
    """从实体数据中提取股票代码"""
    stock_codes = []

    # 从公司实体中提取
    for company in entities.get("companies", []):
        stock_code = company.get("stock_code")
        if stock_code:
            stock_codes.append(stock_code)

    # 去重和验证
    unique_codes = list(set(stock_codes))
    return validate_stock_symbols(unique_codes)


def calculate_entity_relevance_score(
        entity: Dict[str, Any], target_symbols: List[str]) -> float:
    """计算实体与目标股票的相关性分数"""
    relevance_score = 0.0

    # 股票代码直接匹配
    entity_stock_code = entity.get("stock_code", "")
    if entity_stock_code in target_symbols:
        relevance_score += 1.0

    # 公司名称匹配
    entity_name = entity.get("name", "") or entity.get("company_name", "")
    config = get_yuqing_config()

    for symbol in target_symbols:
        mapped_code = config.map_company_to_stock_code(entity_name)
        if mapped_code == symbol:
            relevance_score += 0.8

    # 影响强度加权
    impact_magnitude = entity.get("impact_magnitude", 0.0)
    relevance_score *= (0.5 + impact_magnitude * 0.5)

    # 置信度加权
    confidence = entity.get(
        "confidence",
        0.0) or entity.get(
        "confidence_level",
        0.0)
    relevance_score *= (0.3 + confidence * 0.7)

    return min(1.0, relevance_score)


def prioritize_entities_by_relevance(entities: Dict[str, List],
                                     target_symbols: List[str],
                                     max_per_type: int = 10) -> Dict[str, List]:
    """按相关性对实体进行排序和筛选"""
    prioritized = {}

    for entity_type, entity_list in entities.items():
        # 计算每个实体的相关性分数
        scored_entities = []
        for entity in entity_list:
            relevance_score = calculate_entity_relevance_score(
                entity, target_symbols)
            scored_entities.append((entity, relevance_score))

        # 按相关性排序
        scored_entities.sort(key=lambda x: x[1], reverse=True)

        # 取前N个最相关的实体
        prioritized[entity_type] = [
            entity for entity, score in scored_entities[:max_per_type]
            if score > 0.1  # 过滤掉相关性过低的实体
        ]

    return prioritized


def generate_integration_summary(yuqing_data: Dict[str, Any],
                                 processing_time: float,
                                 error_count: int = 0) -> Dict[str, Any]:
    """生成集成处理摘要"""

    summary = yuqing_data.get("summary", {})

    return {
        "integration_info": {
            "data_source": "YuQing-new",
            "api_version": "v1",
            "processing_time_seconds": round(
                processing_time,
                2),
            "error_count": error_count,
            "integration_timestamp": datetime.now().isoformat()},
        "data_statistics": {
            "total_news_analyzed": summary.get(
                "total_analyzed",
                0),
            "time_range_hours": summary.get(
                "time_range_hours",
                0),
            "entities_included": summary.get(
                "entities_included",
                False),
            "entity_counts": summary.get(
                "entity_counts",
                {}),
            "data_freshness": "real_time" if summary.get(
                "time_range_hours",
                0) <= 6 else "batch"},
        "quality_assessment": {
            "data_completeness": 1.0 if summary.get(
                "total_analyzed",
                0) > 0 else 0.0,
            "entity_coverage": 1.0 if summary.get(
                "entities_included",
                False) else 0.0,
            "temporal_coverage": min(
                1.0,
                summary.get(
                    "time_range_hours",
                    0) / 24.0),
            "source_diversity": len(
                set(
                    dp.get(
                        "news",
                        {}).get("source") for dp in yuqing_data.get(
                        "data",
                        [])))}}


# 环境检查函数
async def check_yuqing_integration_health() -> Dict[str, Any]:
    """检查YuQing集成健康状态"""
    config = get_yuqing_config()
    metrics = get_integration_metrics()

    health_report = {
        "yuqing_service": "unknown",
        "api_connectivity": "unknown",
        "data_quality": "unknown",
        "performance": "unknown",
        "overall_status": "unknown"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 检查YuQing服务状态
            health_response = await client.get(f"{config.yuqing_base_url}/health")
            if health_response.status_code == 200:
                health_report["yuqing_service"] = "healthy"

                # 检查API连通性
                stats_response = await client.get(f"{config.yuqing_base_url}/api/news/stats")
                if stats_response.status_code == 200:
                    health_report["api_connectivity"] = "good"

                    stats_data = stats_response.json()
                    total_news = stats_data.get("total_news", 0)

                    # 评估数据质量
                    if total_news > 100:
                        health_report["data_quality"] = "excellent"
                    elif total_news > 50:
                        health_report["data_quality"] = "good"
                    elif total_news > 10:
                        health_report["data_quality"] = "fair"
                    else:
                        health_report["data_quality"] = "poor"

            # 评估性能
            if metrics.total_api_calls > 0:
                if metrics.success_rate > 0.95 and metrics.avg_response_time < 5.0:
                    health_report["performance"] = "excellent"
                elif metrics.success_rate > 0.90 and metrics.avg_response_time < 10.0:
                    health_report["performance"] = "good"
                else:
                    health_report["performance"] = "needs_improvement"

            # 综合评估
            status_scores = {
                "excellent": 4, "good": 3, "fair": 2, "poor": 1, "unknown": 0,
                "healthy": 4, "needs_improvement": 2
            }

            total_score = sum(status_scores.get(status, 0)
                              for status in health_report.values())
            max_score = len(health_report) * 4

            if total_score >= max_score * 0.8:
                health_report["overall_status"] = "excellent"
            elif total_score >= max_score * 0.6:
                health_report["overall_status"] = "good"
            elif total_score >= max_score * 0.4:
                health_report["overall_status"] = "fair"
            else:
                health_report["overall_status"] = "poor"

    except Exception as e:
        health_report["overall_status"] = f"error: {str(e)}"

    return health_report


# 配置验证
def validate_integration_config(config: YuQingIntegrationConfig) -> List[str]:
    """验证集成配置"""
    errors = []

    # 检查基础URL
    if not config.yuqing_base_url:
        errors.append("YuQing基础URL未配置")

    # 检查超时配置
    if config.yuqing_timeout <= 0:
        errors.append("YuQing超时时间必须大于0")

    # 检查API端点配置
    required_endpoints = ["comprehensive", "companies", "hotspots"]
    for endpoint in required_endpoints:
        if endpoint not in config.api_endpoints:
            errors.append(f"缺少必要的API端点配置: {endpoint}")

    # 检查股票映射表
    if len(config.stock_code_mapping) < 10:
        errors.append("股票代码映射表条目过少，建议至少包含10个主要股票")

    # 检查数据限制配置
    if config.default_news_limit <= 0 or config.default_news_limit > 1000:
        errors.append("新闻获取限制应在1-1000之间")

    return errors
