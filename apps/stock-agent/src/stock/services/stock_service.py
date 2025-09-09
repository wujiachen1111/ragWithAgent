"""
股票数据业务服务
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from ..core.database import db_manager
from ..models.base import StockData, StockQuery, BatchProcessResult
from ..utils.helpers import prepare_mongodb_document
from .data_fetcher import StockDataFetcher


class StockService:
    """股票数据服务"""
    
    def __init__(self):
        self.data_fetcher = StockDataFetcher()
        
    async def get_all_stock_codes(self) -> List[str]:
        """获取所有股票代码"""
        return self.data_fetcher.get_all_stock_codes()
    
    async def fetch_and_save_stock(self, stock_code: str) -> bool:
        """获取并保存单只股票数据"""
        try:
            logger.info(f"开始处理股票 {stock_code}")
            
            # 获取完整数据
            data = self.data_fetcher.get_stock_complete_data(stock_code)
            
            # 保存到数据库
            success = await self._save_stock_data(
                stock_code,
                data["basic_info"],
                data["holders"],
                data["kline_day"],
                data["kline_month"]
            )
            
            if success:
                logger.info(f"✅ 股票 {stock_code} 数据保存成功")
            else:
                logger.error(f"❌ 股票 {stock_code} 数据保存失败")
                
            return success
            
        except Exception as e:
            logger.error(f"处理股票 {stock_code} 时发生错误: {e}")
            return False
    
    async def batch_fetch_stocks(self, stock_codes: List[str], batch_size: int = 50) -> BatchProcessResult:
        """批量获取股票数据"""
        if not stock_codes:
            return BatchProcessResult(
                total=0,
                success=0,
                failed=0,
                success_rate=0.0,
                processed_codes=[],
                failed_codes=[]
            )
        
        total = len(stock_codes)
        success_count = 0
        processed_codes = []
        failed_codes = []
        start_time = time.time()
        
        # 分批处理
        batches = [stock_codes[i:i+batch_size] for i in range(0, len(stock_codes), batch_size)]
        
        for i, batch in enumerate(batches):
            logger.info(f"处理批次 {i+1}/{len(batches)} (共 {len(batch)} 只股票)")
            
            for stock_code in batch:
                try:
                    if await self.fetch_and_save_stock(stock_code):
                        success_count += 1
                        processed_codes.append(stock_code)
                    else:
                        failed_codes.append(stock_code)
                except Exception as e:
                    logger.error(f"处理股票 {stock_code} 异常: {e}")
                    failed_codes.append(stock_code)
        
        success_rate = success_count / total if total > 0 else 0
        total_time = time.time() - start_time
        
        logger.info(f"批量处理完成: 成功 {success_count}/{total} ({success_rate*100:.1f}%), 用时 {total_time:.2f}秒")
        
        return BatchProcessResult(
            total=total,
            success=success_count,
            failed=total - success_count,
            success_rate=success_rate,
            processed_codes=processed_codes,
            failed_codes=failed_codes
        )
    
    async def query_stocks(self, query: StockQuery) -> List[Dict[str, Any]]:
        """查询股票数据"""
        if not db_manager.db:
            raise RuntimeError("数据库未连接")
        
        # 构建MongoDB查询条件
        mongo_query = {}
        
        if query.codes:
            mongo_query["stock_code"] = {"$in": query.codes}
        
        if query.industries:
            mongo_query["basic_info.industry"] = {"$in": query.industries}
        
        if query.areas:
            mongo_query["basic_info.area"] = {"$in": query.areas}
        
        if query.min_market_cap is not None:
            mongo_query["basic_info.total_market_cap"] = {"$gte": query.min_market_cap}
        
        if query.max_market_cap is not None:
            if "basic_info.total_market_cap" in mongo_query:
                mongo_query["basic_info.total_market_cap"]["$lte"] = query.max_market_cap
            else:
                mongo_query["basic_info.total_market_cap"] = {"$lte": query.max_market_cap}
        
        if query.min_pe is not None:
            mongo_query["basic_info.pe_ttm"] = {"$gte": query.min_pe}
        
        if query.max_pe is not None:
            if "basic_info.pe_ttm" in mongo_query:
                mongo_query["basic_info.pe_ttm"]["$lte"] = query.max_pe
            else:
                mongo_query["basic_info.pe_ttm"] = {"$lte": query.max_pe}
        
        # 执行查询
        results = list(db_manager.stocks_collection.find(mongo_query))
        
        # 如果指定了时间范围，过滤K线数据
        if query.start_date or query.end_date:
            start_str = query.start_date.strftime("%Y-%m-%d") if query.start_date else None
            end_str = query.end_date.strftime("%Y-%m-%d") if query.end_date else None
            
            for result in results:
                if "kline_day" in result:
                    result["kline_day"] = self._filter_kline_by_date(
                        result["kline_day"], start_str, end_str
                    )
                
                if "kline_month" in result:
                    result["kline_month"] = self._filter_kline_by_date(
                        result["kline_month"], start_str, end_str
                    )
        
        return results
    
    async def get_stock_by_code(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取单只股票数据"""
        if not db_manager.db:
            raise RuntimeError("数据库未连接")
        
        result = db_manager.stocks_collection.find_one({"stock_code": stock_code})
        return result
    
    async def get_industries(self) -> List[str]:
        """获取所有行业列表"""
        if not db_manager.db:
            raise RuntimeError("数据库未连接")
        
        return db_manager.stocks_collection.distinct("basic_info.industry")
    
    async def get_areas(self) -> List[str]:
        """获取所有地区列表"""
        if not db_manager.db:
            raise RuntimeError("数据库未连接")
        
        return db_manager.stocks_collection.distinct("basic_info.area")
    
    async def get_stocks_by_industry(self, industry: str) -> List[str]:
        """获取指定行业的股票代码"""
        if not db_manager.db:
            raise RuntimeError("数据库未连接")
        
        results = db_manager.stocks_collection.find(
            {"basic_info.industry": industry},
            {"stock_code": 1, "_id": 0}
        )
        
        return [result["stock_code"] for result in results]
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if not db_manager.db:
            raise RuntimeError("数据库未连接")
        
        total_stocks = db_manager.stocks_collection.count_documents({})
        
        # 按行业统计
        pipeline = [
            {"$group": {"_id": "$basic_info.industry", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        industry_stats = list(db_manager.stocks_collection.aggregate(pipeline))
        
        # 按地区统计
        pipeline = [
            {"$group": {"_id": "$basic_info.area", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        area_stats = list(db_manager.stocks_collection.aggregate(pipeline))
        
        # 最近更新时间
        latest_update = db_manager.stocks_collection.find_one(
            {}, {"update_time": 1}, sort=[("update_time", -1)]
        )
        
        return {
            "total_stocks": total_stocks,
            "top_industries": industry_stats,
            "top_areas": area_stats,
            "latest_update": latest_update.get("update_time") if latest_update else None
        }
    
    async def _save_stock_data(self, stock_code: str, basic_info: Dict, holders: List[Dict], 
                              day_kline: List[Dict], month_kline: List[Dict]) -> bool:
        """保存股票数据到MongoDB"""
        try:
            if not db_manager.db:
                raise RuntimeError("数据库未连接")
            
            # 准备文档数据
            document = {
                "stock_code": stock_code,
                "basic_info": prepare_mongodb_document(basic_info),
                "holders": prepare_mongodb_document(holders),
                "kline_day": prepare_mongodb_document(day_kline),
                "kline_month": prepare_mongodb_document(month_kline),
                "update_time": datetime.now()
            }
            
            # 使用upsert操作
            result = db_manager.stocks_collection.update_one(
                {"stock_code": stock_code},
                {"$set": document},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"保存股票 {stock_code} 数据失败: {e}")
            return False
    
    def _filter_kline_by_date(self, kline_data: List[Dict], start_date: Optional[str], 
                             end_date: Optional[str]) -> List[Dict]:
        """根据日期范围过滤K线数据"""
        filtered_data = []
        
        for kline in kline_data:
            if "date" not in kline:
                continue
                
            # 检查日期是否在范围内
            if start_date and kline["date"] < start_date:
                continue
            if end_date and kline["date"] > end_date:
                continue
                
            filtered_data.append(kline)
        
        return filtered_data

