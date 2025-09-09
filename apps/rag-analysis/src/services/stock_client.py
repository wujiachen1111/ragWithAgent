"""
Stock Agent 客户端适配器
为 RAG-Analysis 系统提供股票数据接入能力
"""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class StockDataClient:
    """Stock Agent 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8020"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = "/api/v1"
        self._client = httpx.AsyncClient(timeout=30.0)
        
    async def aclose(self):
        """关闭客户端"""
        await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_market_context(self, symbols: List[str], time_horizon: str = "medium") -> Dict[str, Any]:
        """
        获取市场上下文数据
        
        Args:
            symbols: 股票代码列表
            time_horizon: 时间范围 (immediate/short/medium/long/extended)
            
        Returns:
            市场上下文数据
        """
        try:
            response = await self._client.post(
                f"{self.base_url}{self.api_prefix}/rag/market-context",
                json={
                    "symbols": symbols,
                    "time_horizon": time_horizon
                }
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                logger.info(f"✅ 获取 {len(symbols)} 只股票的市场上下文成功")
                return data["data"]
            else:
                logger.warning(f"⚠️ 获取市场上下文失败: {data.get('message', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 获取市场上下文异常: {e}")
            return {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_sector_analysis(self, industry: str, limit: int = 20) -> Dict[str, Any]:
        """
        获取行业分析数据
        
        Args:
            industry: 行业名称
            limit: 返回股票数量限制
            
        Returns:
            行业分析数据
        """
        try:
            response = await self._client.post(
                f"{self.base_url}{self.api_prefix}/rag/sector-analysis",
                json={
                    "industry": industry,
                    "limit": limit
                }
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                logger.info(f"✅ 获取 {industry} 行业分析成功，包含 {data['data'].get('total_companies', 0)} 家公司")
                return data["data"]
            else:
                logger.warning(f"⚠️ 获取行业分析失败: {data.get('message', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 获取行业分析异常: {e}")
            return {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_comparative_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """
        获取对比分析数据
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            对比分析数据
        """
        try:
            response = await self._client.post(
                f"{self.base_url}{self.api_prefix}/rag/comparative-analysis",
                json={
                    "symbols": symbols
                }
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                logger.info(f"✅ 获取 {len(symbols)} 只股票的对比分析成功")
                return data["data"]
            else:
                logger.warning(f"⚠️ 获取对比分析失败: {data.get('message', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 获取对比分析异常: {e}")
            return {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_stock_detail(self, stock_code: str) -> Dict[str, Any]:
        """
        获取单只股票详细信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票详细信息
        """
        try:
            response = await self._client.get(
                f"{self.base_url}{self.api_prefix}/stocks/{stock_code}"
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                logger.info(f"✅ 获取股票 {stock_code} 详细信息成功")
                return data["data"]
            else:
                logger.warning(f"⚠️ 获取股票详细信息失败: {data.get('message', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 获取股票详细信息异常: {e}")
            return {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def query_stocks(self, **filters) -> List[Dict[str, Any]]:
        """
        查询股票列表
        
        Args:
            **filters: 查询过滤条件
                - industries: 行业列表
                - areas: 地区列表
                - min_market_cap: 最小市值
                - max_market_cap: 最大市值
                - min_pe: 最小市盈率
                - max_pe: 最大市盈率
                
        Returns:
            股票列表
        """
        try:
            response = await self._client.get(
                f"{self.base_url}{self.api_prefix}/stocks/",
                params=filters
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                logger.info(f"✅ 查询股票成功，返回 {len(data['data'])} 只股票")
                return data["data"]
            else:
                logger.warning(f"⚠️ 查询股票失败: {data.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"❌ 查询股票异常: {e}")
            return []
    
    async def get_industry_stocks(self, industry: str) -> List[str]:
        """
        获取指定行业的股票代码列表
        
        Args:
            industry: 行业名称
            
        Returns:
            股票代码列表
        """
        try:
            response = await self._client.get(
                f"{self.base_url}{self.api_prefix}/stocks/industry/{industry}/codes"
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                logger.info(f"✅ 获取 {industry} 行业股票代码成功，共 {len(data['data'])} 只")
                return data["data"]
            else:
                logger.warning(f"⚠️ 获取行业股票代码失败: {data.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"❌ 获取行业股票代码异常: {e}")
            return []
    
    async def get_all_industries(self) -> List[str]:
        """
        获取所有行业列表
        
        Returns:
            行业名称列表
        """
        try:
            response = await self._client.get(
                f"{self.base_url}{self.api_prefix}/stocks/industries/all"
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                logger.info(f"✅ 获取所有行业成功，共 {len(data['data'])} 个行业")
                return data["data"]
            else:
                logger.warning(f"⚠️ 获取所有行业失败: {data.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"❌ 获取所有行业异常: {e}")
            return []
    
    async def check_health(self) -> bool:
        """
        检查 Stock Agent 服务健康状态
        
        Returns:
            服务是否健康
        """
        try:
            response = await self._client.get(
                f"{self.base_url}{self.api_prefix}/stocks/health"
            )
            
            if response.status_code == 200:
                data = response.json()
                is_healthy = data.get("success", False) and data.get("status") == "healthy"
                logger.info(f"✅ Stock Agent 健康检查: {'健康' if is_healthy else '异常'}")
                return is_healthy
            else:
                logger.warning(f"⚠️ Stock Agent 健康检查失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Stock Agent 健康检查异常: {e}")
            return False
    
    async def test_integration(self) -> Dict[str, Any]:
        """
        测试与 Stock Agent 的集成
        
        Returns:
            集成测试结果
        """
        try:
            response = await self._client.get(
                f"{self.base_url}{self.api_prefix}/rag/integration/test"
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Stock Agent 集成测试完成: {data.get('message', 'Success')}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Stock Agent 集成测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()


class StockDataAdapter:
    """
    Stock Agent 数据适配器
    为 RAG-Analysis 系统提供统一的股票数据接口
    """
    
    def __init__(self, stock_client: StockDataClient):
        self.client = stock_client
        
    async def get_investment_context(self, symbols: List[str], analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        获取投资分析上下文
        
        Args:
            symbols: 股票代码列表
            analysis_type: 分析类型 (comprehensive/basic/comparative)
            
        Returns:
            投资分析上下文数据
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "symbols": symbols,
            "analysis_type": analysis_type,
            "data": {}
        }
        
        try:
            if analysis_type == "comprehensive":
                # 获取市场上下文
                market_data = await self.client.get_market_context(symbols, "medium")
                context["data"]["market_context"] = market_data
                
                # 获取对比分析
                if len(symbols) > 1:
                    comparative_data = await self.client.get_comparative_analysis(symbols)
                    context["data"]["comparative_analysis"] = comparative_data
                
                # 获取行业分析（基于第一只股票的行业）
                if symbols and market_data and "data" in market_data:
                    first_stock_data = market_data["data"].get(symbols[0])
                    if first_stock_data and "basic" in first_stock_data:
                        industry = first_stock_data["basic"].get("industry")
                        if industry:
                            sector_data = await self.client.get_sector_analysis(industry, 10)
                            context["data"]["sector_analysis"] = sector_data
            
            elif analysis_type == "basic":
                # 基础分析：只获取市场上下文
                market_data = await self.client.get_market_context(symbols, "short")
                context["data"]["market_context"] = market_data
            
            elif analysis_type == "comparative":
                # 对比分析：重点关注股票对比
                comparative_data = await self.client.get_comparative_analysis(symbols)
                context["data"]["comparative_analysis"] = comparative_data
            
            logger.info(f"✅ 获取投资分析上下文成功: {analysis_type} 模式，{len(symbols)} 只股票")
            return context
            
        except Exception as e:
            logger.error(f"❌ 获取投资分析上下文失败: {e}")
            context["error"] = str(e)
            return context
    
    async def get_sector_intelligence(self, industry: str, limit: int = 15) -> Dict[str, Any]:
        """
        获取行业情报
        
        Args:
            industry: 行业名称
            limit: 返回公司数量限制
            
        Returns:
            行业情报数据
        """
        try:
            sector_data = await self.client.get_sector_analysis(industry, limit)
            
            if sector_data:
                # 增强行业情报
                intelligence = {
                    "industry": industry,
                    "timestamp": datetime.now().isoformat(),
                    "overview": {
                        "total_companies": sector_data.get("total_companies", 0),
                        "sector_metrics": sector_data.get("sector_metrics", {}),
                    },
                    "top_companies": sector_data.get("companies", [])[:10],
                    "investment_highlights": self._extract_investment_highlights(sector_data),
                    "risk_factors": self._extract_risk_factors(sector_data)
                }
                
                logger.info(f"✅ 获取 {industry} 行业情报成功")
                return intelligence
            else:
                return {"error": f"无法获取 {industry} 行业数据"}
                
        except Exception as e:
            logger.error(f"❌ 获取行业情报失败: {e}")
            return {"error": str(e)}
    
    def _extract_investment_highlights(self, sector_data: Dict[str, Any]) -> List[str]:
        """提取投资亮点"""
        highlights = []
        
        try:
            metrics = sector_data.get("sector_metrics", {})
            companies = sector_data.get("companies", [])
            
            # 基于行业指标的亮点
            if metrics.get("avg_roe", 0) > 15:
                highlights.append(f"行业平均ROE达到{metrics['avg_roe']:.1f}%，盈利能力较强")
            
            if metrics.get("avg_pe_ratio", 0) < 15:
                highlights.append(f"行业平均PE为{metrics['avg_pe_ratio']:.1f}倍，估值相对合理")
            
            # 基于公司数据的亮点
            if companies:
                high_roe_companies = [c for c in companies if c.get("roe", 0) > 20]
                if len(high_roe_companies) > 0:
                    highlights.append(f"有{len(high_roe_companies)}家公司ROE超过20%")
                
                large_cap_companies = [c for c in companies if c.get("market_cap", 0) > 1000]
                if len(large_cap_companies) > 0:
                    highlights.append(f"包含{len(large_cap_companies)}家千亿市值以上公司")
            
        except Exception as e:
            logger.warning(f"提取投资亮点失败: {e}")
        
        return highlights or ["暂无特别投资亮点"]
    
    def _extract_risk_factors(self, sector_data: Dict[str, Any]) -> List[str]:
        """提取风险因素"""
        risks = []
        
        try:
            metrics = sector_data.get("sector_metrics", {})
            companies = sector_data.get("companies", [])
            
            # 基于行业指标的风险
            if metrics.get("avg_pe_ratio", 0) > 30:
                risks.append(f"行业平均PE达到{metrics['avg_pe_ratio']:.1f}倍，估值偏高")
            
            if metrics.get("avg_roe", 0) < 5:
                risks.append(f"行业平均ROE仅{metrics['avg_roe']:.1f}%，盈利能力较弱")
            
            # 基于公司分布的风险
            if companies:
                low_roe_companies = [c for c in companies if c.get("roe", 0) < 5]
                if len(low_roe_companies) / len(companies) > 0.5:
                    risks.append("超过一半公司ROE低于5%，整体盈利能力不佳")
            
        except Exception as e:
            logger.warning(f"提取风险因素失败: {e}")
        
        return risks or ["暂无特别风险提示"]


# 全局实例
stock_client = StockDataClient()
stock_adapter = StockDataAdapter(stock_client)

