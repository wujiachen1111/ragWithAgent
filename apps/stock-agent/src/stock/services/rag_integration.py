"""
与 RAG-Analysis 系统的集成适配器
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from ..core.config import settings
from ..models.base import StockQuery


class RAGIntegrationAdapter:
    """RAG-Analysis 系统集成适配器"""
    
    def __init__(self, rag_base_url: str = "http://localhost:8010"):
        self.rag_base_url = rag_base_url
        self.stock_base_url = f"http://{settings.api.host}:{settings.api.port}/api/v1"
        
    async def provide_market_context(self, symbols: List[str], time_horizon: str = "medium") -> Dict[str, Any]:
        """
        为 RAG-Analysis 提供市场上下文数据
        
        Args:
            symbols: 股票代码列表
            time_horizon: 时间范围 (immediate/short/medium/long/extended)
            
        Returns:
            标准化的市场上下文数据
        """
        try:
            async with httpx.AsyncClient() as client:
                market_context = {
                    "timestamp": datetime.now().isoformat(),
                    "symbols": symbols,
                    "time_horizon": time_horizon,
                    "data": {}
                }
                
                # 获取每只股票的详细数据
                for symbol in symbols:
                    try:
                        response = await client.get(f"{self.stock_base_url}/stocks/{symbol}")
                        if response.status_code == 200:
                            stock_data = response.json()["data"]
                            
                            # 转换为 RAG 友好的格式
                            market_context["data"][symbol] = self._format_for_rag(stock_data)
                        else:
                            logger.warning(f"获取股票 {symbol} 数据失败: {response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"获取股票 {symbol} 数据异常: {e}")
                
                # 添加行业和市场概况
                market_context["industry_overview"] = await self._get_industry_overview(symbols)
                market_context["market_summary"] = await self._get_market_summary()
                
                return market_context
                
        except Exception as e:
            logger.error(f"提供市场上下文失败: {e}")
            return {"error": str(e), "symbols": symbols}
    
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
            async with httpx.AsyncClient() as client:
                # 获取行业股票列表
                response = await client.get(
                    f"{self.stock_base_url}/stocks/",
                    params={"industries": [industry]}
                )
                
                if response.status_code != 200:
                    return {"error": "获取行业数据失败", "industry": industry}
                
                stocks_data = response.json()["data"][:limit]
                
                # 分析行业数据
                sector_analysis = {
                    "industry": industry,
                    "timestamp": datetime.now().isoformat(),
                    "total_companies": len(stocks_data),
                    "companies": [],
                    "sector_metrics": self._calculate_sector_metrics(stocks_data)
                }
                
                # 处理每只股票的数据
                for stock in stocks_data:
                    company_info = {
                        "code": stock["stock_code"],
                        "name": stock["basic_info"]["stock_name"],
                        "market_cap": stock["basic_info"]["total_market_cap"],
                        "pe_ratio": stock["basic_info"]["pe_ttm"],
                        "pb_ratio": stock["basic_info"]["pb"],
                        "roe": stock["basic_info"]["roe"],
                        "latest_price": stock["basic_info"]["latest_price"],
                        "area": stock["basic_info"]["area"]
                    }
                    sector_analysis["companies"].append(company_info)
                
                return sector_analysis
                
        except Exception as e:
            logger.error(f"获取行业分析失败: {e}")
            return {"error": str(e), "industry": industry}
    
    async def get_comparative_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """
        获取股票对比分析数据
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            对比分析数据
        """
        try:
            async with httpx.AsyncClient() as client:
                comparative_data = {
                    "timestamp": datetime.now().isoformat(),
                    "symbols": symbols,
                    "comparison": {},
                    "ranking": {}
                }
                
                stocks_data = []
                
                # 获取所有股票数据
                for symbol in symbols:
                    try:
                        response = await client.get(f"{self.stock_base_url}/stocks/{symbol}")
                        if response.status_code == 200:
                            stocks_data.append(response.json()["data"])
                    except Exception as e:
                        logger.warning(f"获取股票 {symbol} 数据失败: {e}")
                
                if not stocks_data:
                    return {"error": "未获取到有效股票数据", "symbols": symbols}
                
                # 生成对比数据
                comparative_data["comparison"] = self._generate_comparison(stocks_data)
                comparative_data["ranking"] = self._generate_ranking(stocks_data)
                
                return comparative_data
                
        except Exception as e:
            logger.error(f"获取对比分析失败: {e}")
            return {"error": str(e), "symbols": symbols}
    
    def _format_for_rag(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """将股票数据格式化为 RAG 友好的格式"""
        basic_info = stock_data["basic_info"]
        
        # 基础信息
        rag_format = {
            "basic": {
                "code": stock_data["stock_code"],
                "name": basic_info["stock_name"],
                "industry": basic_info["industry"],
                "area": basic_info["area"],
                "latest_price": basic_info["latest_price"]
            },
            "valuation": {
                "market_cap": basic_info["total_market_cap"],
                "pe_ttm": basic_info["pe_ttm"],
                "pb": basic_info["pb"],
                "roe": basic_info["roe"],
                "eps": basic_info["eps"],
                "bps": basic_info["bps"]
            },
            "trading": {
                "turnover_rate": basic_info["turnover_rate"],
                "week52_high": basic_info["week52_high"],
                "week52_low": basic_info["week52_low"],
                "beta": basic_info["beta"]
            }
        }
        
        # 添加股东信息摘要
        if stock_data.get("holders"):
            holders = stock_data["holders"][:5]  # 前5大股东
            rag_format["ownership"] = {
                "top_holders": [
                    {
                        "name": h["holder_name"],
                        "ratio": h["ratio"],
                        "type": h["holder_type"]
                    } for h in holders
                ]
            }
        
        # 添加价格趋势
        if stock_data.get("kline_day"):
            recent_klines = stock_data["kline_day"][-5:]  # 最近5天
            if recent_klines:
                rag_format["price_trend"] = {
                    "recent_changes": [k["change_pct"] for k in recent_klines],
                    "avg_volume": sum(k["volume"] for k in recent_klines) / len(recent_klines),
                    "trend_direction": "up" if recent_klines[-1]["change_pct"] > 0 else "down"
                }
        
        return rag_format
    
    async def _get_industry_overview(self, symbols: List[str]) -> Dict[str, Any]:
        """获取相关行业概览"""
        try:
            async with httpx.AsyncClient() as client:
                # 获取所有行业
                response = await client.get(f"{self.stock_base_url}/stocks/industries/all")
                if response.status_code == 200:
                    industries = response.json()["data"]
                    return {
                        "total_industries": len(industries),
                        "industries": industries[:10]  # 返回前10个行业
                    }
        except Exception as e:
            logger.warning(f"获取行业概览失败: {e}")
        
        return {"total_industries": 0, "industries": []}
    
    async def _get_market_summary(self) -> Dict[str, Any]:
        """获取市场摘要"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.stock_base_url}/stocks/stats/database")
                if response.status_code == 200:
                    stats = response.json()["data"]
                    return {
                        "total_stocks": stats.get("total_stocks", 0),
                        "last_update": stats.get("latest_update"),
                        "top_industries": stats.get("top_industries", [])[:5]
                    }
        except Exception as e:
            logger.warning(f"获取市场摘要失败: {e}")
        
        return {"total_stocks": 0, "last_update": None}
    
    def _calculate_sector_metrics(self, stocks_data: List[Dict]) -> Dict[str, Any]:
        """计算行业指标"""
        if not stocks_data:
            return {}
        
        # 提取基本信息
        market_caps = [s["basic_info"]["total_market_cap"] for s in stocks_data if s["basic_info"]["total_market_cap"] > 0]
        pe_ratios = [s["basic_info"]["pe_ttm"] for s in stocks_data if s["basic_info"]["pe_ttm"] > 0]
        roe_values = [s["basic_info"]["roe"] for s in stocks_data if s["basic_info"]["roe"] > 0]
        
        return {
            "avg_market_cap": sum(market_caps) / len(market_caps) if market_caps else 0,
            "avg_pe_ratio": sum(pe_ratios) / len(pe_ratios) if pe_ratios else 0,
            "avg_roe": sum(roe_values) / len(roe_values) if roe_values else 0,
            "total_market_cap": sum(market_caps),
            "company_count": len(stocks_data)
        }
    
    def _generate_comparison(self, stocks_data: List[Dict]) -> Dict[str, Any]:
        """生成股票对比数据"""
        comparison = {}
        
        for stock in stocks_data:
            code = stock["stock_code"]
            basic = stock["basic_info"]
            
            comparison[code] = {
                "name": basic["stock_name"],
                "market_cap": basic["total_market_cap"],
                "pe_ratio": basic["pe_ttm"],
                "pb_ratio": basic["pb"],
                "roe": basic["roe"],
                "price": basic["latest_price"],
                "industry": basic["industry"]
            }
        
        return comparison
    
    def _generate_ranking(self, stocks_data: List[Dict]) -> Dict[str, Any]:
        """生成股票排名"""
        # 按市值排名
        by_market_cap = sorted(
            stocks_data, 
            key=lambda x: x["basic_info"]["total_market_cap"], 
            reverse=True
        )
        
        # 按ROE排名
        by_roe = sorted(
            [s for s in stocks_data if s["basic_info"]["roe"] > 0],
            key=lambda x: x["basic_info"]["roe"],
            reverse=True
        )
        
        return {
            "by_market_cap": [
                {"code": s["stock_code"], "name": s["basic_info"]["stock_name"], "value": s["basic_info"]["total_market_cap"]}
                for s in by_market_cap
            ],
            "by_roe": [
                {"code": s["stock_code"], "name": s["basic_info"]["stock_name"], "value": s["basic_info"]["roe"]}
                for s in by_roe
            ]
        }

