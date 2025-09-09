"""
测试配置文件
提供测试用的fixtures和配置
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from analysis.models.agents import AnalysisRequestVO, TimeHorizon, RiskAppetite
from analysis.services.llm_client import LLMClient
from analysis.services.sentiment_client import SentimentAPIClient


@pytest.fixture
def sample_analysis_request():
    """示例分析请求"""
    return AnalysisRequestVO(
        topic="AI技术突破",
        headline="某公司发布革命性AI产品",
        content="该公司宣布推出新一代人工智能产品，预计将改变行业格局...",
        symbols=["000001", "600036"],
        time_horizon=TimeHorizon.medium,
        risk_appetite=RiskAppetite.balanced,
        region="CN",
        max_iterations=1
    )


@pytest.fixture
def mock_llm_client():
    """模拟LLM客户端"""
    client = AsyncMock(spec=LLMClient)
    client.structured_json = AsyncMock(return_value={
        "one_liner": "AI技术突破",
        "meme_potential": 0.8,
        "influencers_take": ["技术突破", "市场影响"],
        "lifecycle_days": 7,
        "priced_in": False
    })
    return client


@pytest.fixture
def mock_sentiment_client():
    """模拟舆情客户端"""
    client = AsyncMock(spec=SentimentAPIClient)
    client.get_comprehensive_sentiment_report = AsyncMock(return_value={
        "overall_sentiment": {"positive": 0.6, "negative": 0.2, "neutral": 0.2},
        "sentiment_trend": [],
        "hot_topics": ["AI", "技术"],
        "data_quality": 0.8,
        "total_processed": 100
    })
    return client


@pytest.fixture
def event_loop():
    """事件循环fixture"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_stock_data():
    """模拟股票数据"""
    return {
        "000001": {
            "basic": {
                "code": "000001",
                "name": "平安银行",
                "industry": "银行",
                "latest_price": 12.5
            },
            "valuation": {
                "market_cap": 1000.0,
                "pe_ttm": 8.5,
                "pb": 0.8
            }
        }
    }

