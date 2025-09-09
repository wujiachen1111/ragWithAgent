"""
股票数据获取服务
"""

import time
import requests
import akshare as ak
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from ..core.config import settings
from ..utils.helpers import safe_convert_value, determine_market, format_secid, classify_holder_type


class StockDataFetcher:
    """股票数据获取器"""
    
    def __init__(self):
        self.session = self._create_session()
        self._holder_cache: Dict[str, pd.DataFrame] = {}
        
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        headers = {
            "User-Agent": settings.data.user_agent,
            "Referer": "https://finance.sina.com.cn/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        session.headers.update(headers)
        
        # 配置连接池
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def get_all_stock_codes(self) -> List[str]:
        """获取所有A股股票代码列表"""
        try:
            stock_info_df = ak.stock_info_a_code_name()
            stock_codes = stock_info_df['code'].tolist()
            logger.info(f"✅ 成功获取 {len(stock_codes)} 个股票代码")
            return stock_codes
        except Exception as e:
            logger.error(f"❌ 获取股票代码失败: {e}")
            return []
    
    def get_stock_basic_info(self, stock_code: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        secid = format_secid(stock_code)
        fields = (
            "f57,f58,f43,f168,f60,f167,f47,"  # 原有字段
            "f116,f117,f86,f84,f85,f169,f170,"  # 新增字段
            "f127,f104,f107,f105,f162,f92,f71"  # 新增字段
        )
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}"
        
        try:
            response = self.session.get(url, timeout=settings.data.request_timeout)
            response.raise_for_status()
            data = response.json().get("data", {})
            
            # 获取总手数据
            volume = safe_convert_value(data.get("f47", 0))
            
            # 备用方案：腾讯财经接口
            if volume == 0:
                volume = self._get_volume_from_tencent(stock_code)
            
            # 处理行业和地区字段
            industry = data.get("f127", "")
            area = data.get("f104", "")
            if isinstance(industry, (int, float)) and industry > 100000000:
                industry = ""
            if isinstance(area, (int, float)) and area > 100000000:
                area = ""
            
            # 返回扩展的基本信息
            return {
                "stock_name": data.get("f58", ""),
                "latest_price": safe_convert_value(data.get("f43", 0), 100),
                "pe_ttm": safe_convert_value(data.get("f167", "N/A")),
                "pb": safe_convert_value(data.get("f60", "N/A")),
                "turnover_rate": safe_convert_value(data.get("f168", 0)),
                "heat": volume,
                "total_market_cap": safe_convert_value(data.get("f116", 0), 100000000),
                "circulating_market_cap": safe_convert_value(data.get("f117", 0), 100000000),
                "week52_high": safe_convert_value(data.get("f84", 0), 100),
                "week52_low": safe_convert_value(data.get("f85", 0), 100),
                "dividend_yield": safe_convert_value(data.get("f170", 0)),
                "roe": safe_convert_value(data.get("f162", "N/A")),
                "eps": safe_convert_value(data.get("f92", "N/A")),
                "bps": safe_convert_value(data.get("f71", "N/A")),
                "industry": industry,
                "area": area,
                "total_shares": safe_convert_value(data.get("f86", 0), 10000),
                "circulating_shares": safe_convert_value(data.get("f169", 0), 10000),
                "beta": safe_convert_value(data.get("f105", "N/A"))
            }
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 基本信息失败: {e}")
            return self._get_empty_basic_info()
    
    def _get_volume_from_tencent(self, stock_code: str) -> float:
        """从腾讯财经获取成交量"""
        try:
            market = determine_market(stock_code)
            symbol = f"{market}{stock_code}"
            url = f"https://qt.gtimg.cn/q=s_{symbol}"
            
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                volume_data = response.text
                parts = volume_data.split('~')
                if len(parts) > 8 and parts[8]:
                    return safe_convert_value(parts[8])
        except Exception as e:
            logger.warning(f"从腾讯财经获取成交量失败: {e}")
        
        return 0
    
    def _get_empty_basic_info(self) -> Dict[str, Any]:
        """获取空的基本信息结构"""
        return {
            "stock_name": "",
            "latest_price": 0,
            "pe_ttm": 0,
            "pb": 0,
            "turnover_rate": 0,
            "heat": 0,
            "total_market_cap": 0,
            "circulating_market_cap": 0,
            "week52_high": 0,
            "week52_low": 0,
            "dividend_yield": 0,
            "roe": 0,
            "eps": 0,
            "bps": 0,
            "industry": "",
            "area": "",
            "total_shares": 0,
            "circulating_shares": 0,
            "beta": 0
        }
    
    def get_top_holders(self, stock_code: str) -> List[Dict[str, Any]]:
        """获取前十大股东信息"""
        try:
            current_year = datetime.now().year
            # 报告期顺序：优先最新数据
            report_dates = [
                f"{current_year}0331",  # 当年一季报
                f"{current_year-1}1231",  # 上年年报
                f"{current_year-1}0930",  # 上年三季报
                f"{current_year-1}0630"   # 上年半年报
            ]
            
            holders = []
            for date in report_dates:
                try:
                    # 检查缓存
                    if date not in self._holder_cache:
                        df = ak.stock_gdfx_free_holding_detail_em(date=date)
                        self._holder_cache[date] = df
                    else:
                        df = self._holder_cache[date]
                    
                    # 筛选当前股票的股东数据
                    df_filtered = df[df["股票代码"] == stock_code]
                    
                    if not df_filtered.empty:
                        # 取前10名股东
                        for _, row in df_filtered.head(10).iterrows():
                            holder_name = row["股东名称"]
                            shares = int(row["期末持股-数量"]) if pd.notna(row["期末持股-数量"]) else 0
                            ratio = round(float(shares) / 1e8, 4) if shares != 0 else 0
                            shares_change = int(row.get("期末持股-数量变化", 0)) if pd.notna(row.get("期末持股-数量变化")) else 0
                            pledged_shares = int(row.get("质押或冻结数量", 0)) if pd.notna(row.get("质押或冻结数量")) else 0
                            
                            holders.append({
                                "holder_name": holder_name,
                                "shares": shares,
                                "ratio": ratio,
                                "report_date": date,
                                "holder_type": classify_holder_type(holder_name),
                                "shares_change": shares_change,
                                "change_ratio": row.get("期末持股-变化比例", "0%"),
                                "pledged_shares": pledged_shares
                            })
                        break
                except Exception as e:
                    logger.warning(f"获取 {stock_code} 报告期 {date} 股东信息失败: {e}")
                    continue
            
            return holders[:10]
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 股东信息失败: {e}")
            return []
    
    def get_kline_data(self, stock_code: str, period: str, count: int) -> List[Dict[str, Any]]:
        """获取K线数据"""
        market = determine_market(stock_code)
        symbol = f"{market}{stock_code}"
        url = (
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            f"?param={symbol},{period},,,1000,qfq"
        )
        
        try:
            response = self.session.get(url, timeout=settings.data.request_timeout)
            response.raise_for_status()
            data = response.json()
            
            klines = []
            raw_list = (
                data.get("data", {})
                .get(symbol, {})
                .get("qfq" + period, []) or data["data"][symbol][period]
            )
            
            # 只取最近count条数据
            for item in raw_list[-count:]:
                if len(item) < 6:
                    continue
                date, open_, close, high, low, volume = item[:6]
                open_, close, high, low, volume = map(
                    lambda x: safe_convert_value(x, 1, 0), 
                    (open_, close, high, low, volume)
                )
                klines.append({
                    "date": date,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume / 1e4,  # 万手
                    "amount": (open_ + close) / 2 * volume / 1e8,  # 亿元
                })
            
            # 计算涨跌幅
            for i in range(1, len(klines)):
                prev = klines[i - 1]["close"]
                curr = klines[i]["close"]
                klines[i]["change"] = round(curr - prev, 2)
                klines[i]["change_pct"] = round((curr - prev) / prev * 100, 2) if prev != 0 else 0
            
            if klines:
                klines[0]["change"] = klines[0]["change_pct"] = 0
            
            return klines
        except Exception as e:
            logger.error(f"获取股票 {stock_code} K线数据失败 ({period}): {e}")
            return []
    
    def get_stock_complete_data(self, stock_code: str) -> Dict[str, Any]:
        """获取单只股票的完整数据"""
        logger.info(f"开始获取股票 {stock_code} 的完整数据")
        
        # 获取基本信息
        basic_info = self.get_stock_basic_info(stock_code)
        stock_name = basic_info["stock_name"]
        
        if stock_name:
            logger.info(f"✅ 基本信息获取完成: {stock_name}")
        else:
            logger.warning(f"⚠️ 股票 {stock_code} 基本信息获取失败")
        
        # 获取股东信息
        holders = self.get_top_holders(stock_code)
        logger.info(f"✅ 股东信息获取完成: {len(holders)} 条")
        
        # 获取日K线数据（最近22个交易日）
        day_kline = self.get_kline_data(stock_code, "day", 22)
        logger.info(f"✅ 日K线获取完成: {len(day_kline)} 条")
        
        # 获取月K线数据（最近24个月）
        month_kline = self.get_kline_data(stock_code, "month", 24)
        logger.info(f"✅ 月K线获取完成: {len(month_kline)} 条")
        
        # 添加延迟避免频率限制
        time.sleep(settings.data.request_delay)
        
        return {
            "stock_code": stock_code,
            "basic_info": basic_info,
            "holders": holders,
            "kline_day": day_kline,
            "kline_month": month_kline
        }

