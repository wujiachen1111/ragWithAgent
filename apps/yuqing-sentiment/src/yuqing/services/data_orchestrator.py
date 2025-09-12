import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from yuqing.core.logging import app_logger
from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem
from yuqing.services.google_news_service import google_news_service
from yuqing.services.hot_news_discovery import hot_news_discovery
from yuqing.services.cailian_news_service import cailian_news_service
from yuqing.services.entity_analysis_orchestrator import entity_analysis_orchestrator
from sqlalchemy.orm import Session


class DataCollectionOrchestrator:
    """数据采集协调器 - 统一管理Google新闻和热点发现"""
    
    def __init__(self):
        self.services = {
            "google_news": google_news_service,
            "hot_discovery": hot_news_discovery,
            "cailian_news": cailian_news_service
        }
        
        # 采集配置 - 统一5分钟调度
        self.collection_config = {
            "hot_discovery": {
                "enabled": True,
                "max_items": 50,
                "hours_back": 12,  # 扩展到12小时
                "priority": 1,  # 最高优先级
                "description": "智能热点发现"
            },
            "cailian_news": {
                "enabled": True,
                "max_items": 150,
                "priority": 2,  # 第二优先级
                "description": "财联社专业财经新闻"
            },
            "google_news": {
                "enabled": True,
                "max_items": 50,
                "keywords": ["股票", "财经", "投资", "A股", "港股", "美股"],
                "sort_by_date": True,  # 按日期排序，获取最新
                "priority": 3,  # 第三优先级
                "description": "Google新闻搜索"
            }
        }
    
    async def collect_all_sources(self) -> Dict[str, Any]:
        """采集所有数据源"""
        results = {
            "timestamp": datetime.now(timezone.utc),
            "sources": {},
            "total_items": 0,
            "errors": []
        }
        
        app_logger.info("开始全量数据采集...")
        app_logger.info("📋 采集配置:")
        for source_name, config in self.collection_config.items():
            if config.get("enabled", True):
                max_items = config.get("max_items", "未限制")
                keywords = config.get("keywords", [])
                keyword_info = f", 关键词: {len(keywords)}个" if keywords else ""
                app_logger.info(f"  {source_name}: 最大{max_items}条{keyword_info}")
        
        # 并行采集所有数据源
        tasks = []
        for source_name, config in self.collection_config.items():
            if config.get("enabled", True):
                task = asyncio.create_task(
                    self._collect_single_source(source_name, config),
                    name=f"collect_{source_name}"
                )
                tasks.append(task)
        
        # 等待所有任务完成
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(completed_tasks):
            source_name = list(self.collection_config.keys())[i]
            
            if isinstance(result, Exception):
                error_msg = f"{source_name} 采集失败: {result}"
                app_logger.error(error_msg)
                results["errors"].append(error_msg)
                results["sources"][source_name] = {"items": 0, "error": str(result)}
            else:
                results["sources"][source_name] = result
                results["total_items"] += result.get("items", 0)
        
        app_logger.info("📊 数据采集结果统计:")
        app_logger.info(f"  总计采集: {results['total_items']} 条新闻")
        
        for source_name, source_result in results["sources"].items():
            if isinstance(source_result, dict):
                items = source_result.get("items", 0)
                saved = source_result.get("saved_to_db", 0)
                duration = source_result.get("duration_seconds", 0)
                success = "✅" if source_result.get("success") else "❌"
                
                app_logger.info(f"  {success} {source_name}: {items}条采集 -> {saved}条保存 ({duration:.1f}s)")
                
                if not source_result.get("success") and "error" in source_result:
                    app_logger.warning(f"    错误: {source_result['error']}")
        
        if results.get("errors"):
            app_logger.warning(f"  ⚠️ 采集错误: {'; '.join(results['errors'])}")
        
        return results
    
    async def _collect_single_source(self, source_name: str, 
                                   config: Dict[str, Any]) -> Dict[str, Any]:
        """采集单个数据源"""
        start_time = datetime.now()
        
        try:
            if source_name == "hot_discovery":
                # 智能热点发现
                hours_back = config.get("hours_back", 6)
                
                items = await hot_news_discovery.discover_hot_news(hours_back)
                
                # 去重和保存到数据库
                if items:
                    unique_items = hot_news_discovery._enhanced_deduplicate(items)
                    saved_count = await hot_news_discovery.save_to_database(unique_items)
                else:
                    saved_count = 0
                
                return {
                    "items": len(items),
                    "saved_to_db": saved_count,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "success": True
                }
                
            elif source_name == "cailian_news":
                # 财联社新闻采集
                max_items = config.get("max_items", 100)
                
                items = await cailian_news_service.fetch_cailian_news(max_items)
                # 保存到数据库
                if items:
                    saved_count = await cailian_news_service.save_to_database(items)
                else:
                    saved_count = 0
                
                return {
                    "items": len(items),
                    "saved_to_db": saved_count,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "success": True
                }
                
            elif source_name == "google_news":
                # Google新闻搜索 - 优化数量控制
                keywords = config.get("keywords", ["股票", "财经"])
                max_items = config.get("max_items", 50)
                
                app_logger.info(f"Google新闻采集: {len(keywords)}个关键词, 总限制{max_items}条")
                
                all_items = []
                items_per_keyword = max(5, max_items // len(keywords))  # 每个关键词至少5条
                
                for i, keyword in enumerate(keywords):
                    try:
                        # 为了获取最新新闻，限制每个关键词的数量
                        items = await google_news_service.search_news(keyword, items_per_keyword)
                        app_logger.info(f"  关键词 '{keyword}': 采集 {len(items)} 条")
                        all_items.extend(items)
                        
                        # 避免过多采集，达到限制就停止
                        if len(all_items) >= max_items:
                            app_logger.info(f"  已达到最大限制 {max_items} 条，停止采集")
                            break
                            
                    except Exception as e:
                        app_logger.error(f"Google新闻关键词 {keyword} 采集失败: {e}")
                
                # 按时间排序，保留最新的
                if all_items:
                    # 按发布时间降序排序 (最新的在前)
                    all_items.sort(key=lambda x: x.get('published_at', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
                    
                    # 限制总数量
                    all_items = all_items[:max_items]
                    
                    app_logger.info(f"Google新闻排序后保留最新 {len(all_items)} 条")
                    
                    # 去重和保存到数据库
                    unique_items = google_news_service._enhanced_deduplicate(all_items)
                    saved_count = await google_news_service.save_to_database(unique_items)
                else:
                    saved_count = 0
                
                return {
                    "items": len(all_items),
                    "saved_to_db": saved_count,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "success": True
                }
            
            else:
                app_logger.warning(f"未知数据源: {source_name}")
                return {
                    "items": 0,
                    "duration_seconds": 0,
                    "success": False,
                    "error": f"未知数据源: {source_name}"
                }
                
        except Exception as e:
            app_logger.error(f"{source_name} 采集异常: {e}")
            return {
                "items": 0,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
                "success": False,
                "error": str(e)
            }
    
    async def collect_cailian_news(self, limit: int = 100) -> List[Dict[str, Any]]:
        """财联社新闻采集"""
        return await cailian_news_service.fetch_cailian_news(limit)
    
    async def collect_google_news(self, keywords: Optional[List[str]] = None, 
                                max_items: int = 50) -> List[Dict[str, Any]]:
        """Google新闻采集"""
        if not keywords:
            keywords = ["股票", "财经", "投资"]
        
        all_items = []
        for keyword in keywords:
            try:
                items = await google_news_service.search_news(keyword, max_items // len(keywords))
                all_items.extend(items)
            except Exception as e:
                app_logger.error(f"Google新闻关键词 {keyword} 采集失败: {e}")
        
        return all_items
    
    async def collect_hot_discovery(self, hours_back: int = 6, 
                                  max_items: int = 30) -> List[Dict[str, Any]]:
        """智能热点发现"""
        return await hot_news_discovery.discover_hot_news(hours_back=hours_back, max_items=max_items)
    
    async def collect_by_keywords(self, keywords: List[str], 
                                max_items: int = 50) -> Dict[str, Any]:
        """按关键词采集数据"""
        results = {
            "timestamp": datetime.now(timezone.utc),
            "keywords": keywords,
            "sources": {},
            "total_items": 0,
            "errors": []
        }
        
        app_logger.info(f"开始关键词采集: {keywords}")
        
        # 财联社新闻采集
        try:
            cailian_items = await self.collect_cailian_news(max_items)
            results["sources"]["cailian_news"] = {
                "items": len(cailian_items),
                "success": True
            }
            results["total_items"] += len(cailian_items)
        except Exception as e:
            error_msg = f"财联社新闻采集失败: {e}"
            app_logger.error(error_msg)
            results["errors"].append(error_msg)
            results["sources"]["cailian_news"] = {"items": 0, "error": str(e)}
        
        # Google新闻采集
        try:
            google_items = await self.collect_google_news(keywords, max_items)
            results["sources"]["google_news"] = {
                "items": len(google_items),
                "success": True
            }
            results["total_items"] += len(google_items)
        except Exception as e:
            error_msg = f"Google新闻采集失败: {e}"
            app_logger.error(error_msg)
            results["errors"].append(error_msg)
            results["sources"]["google_news"] = {"items": 0, "error": str(e)}
        
        app_logger.info(f"关键词采集完成，总计 {results['total_items']} 条数据")
        return results
    
    async def collect_by_companies(self, companies: List[str], 
                                 max_items: int = 50) -> Dict[str, Any]:
        """按公司名称采集数据"""
        results = {
            "timestamp": datetime.now(timezone.utc),
            "companies": companies,
            "sources": {},
            "total_items": 0,
            "errors": []
        }
        
        app_logger.info(f"开始公司新闻采集: {companies}")
        
        # 财联社新闻采集
        try:
            cailian_items = await self.collect_cailian_news(max_items)
            results["sources"]["cailian_news"] = {
                "items": len(cailian_items),
                "success": True
            }
            results["total_items"] += len(cailian_items)
        except Exception as e:
            error_msg = f"财联社新闻采集失败: {e}"
            app_logger.error(error_msg)
            results["errors"].append(error_msg)
            results["sources"]["cailian_news"] = {"items": 0, "error": str(e)}
        
        # Google新闻采集
        try:
            google_items = await self.collect_google_news(companies, max_items)
            results["sources"]["google_news"] = {
                "items": len(google_items),
                "success": True
            }
            results["total_items"] += len(google_items)
        except Exception as e:
            error_msg = f"Google新闻采集失败: {e}"
            app_logger.error(error_msg)
            results["errors"].append(error_msg)
            results["sources"]["google_news"] = {"items": 0, "error": str(e)}
        
        app_logger.info(f"公司新闻采集完成，总计 {results['total_items']} 条数据")
        return results
    
    async def get_collection_status(self) -> Dict[str, Any]:
        """获取采集状态"""
        status = {
            "timestamp": datetime.now(timezone.utc),
            "services": {},
            "database_status": {}
        }
        
        # 检查服务状态
        for service_name, service in self.services.items():
            try:
                # 简单的健康检查
                status["services"][service_name] = {
                    "status": "active",
                    "enabled": self.collection_config.get(service_name, {}).get("enabled", True)
                }
            except Exception as e:
                status["services"][service_name] = {
                    "status": "error",
                    "error": str(e),
                    "enabled": False
                }
        
        # 检查数据库状态
        try:
            db = next(get_db())
            recent_count = db.query(NewsItem).filter(
                NewsItem.collected_at != None  # noqa: E711
            ).filter(
                NewsItem.collected_at >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).count()
            
            total_count = db.query(NewsItem).count()
            
            status["database_status"] = {
                "status": "connected",
                "total_news": total_count,
                "recent_24h": recent_count
            }
            
        except Exception as e:
            status["database_status"] = {
                "status": "error",
                "error": str(e)
            }
        
        return status
    
    async def analyze_collected_news(self, hours_back: int = 1, limit: int = 20, source: Optional[str] = None) -> Dict[str, Any]:
        """分析最近采集的新闻（包含实体识别）。

        兼容老数据：当 collected_at 为空时，以 published_at 作为回退时间字段。
        """
        try:
            db = next(get_db())
            
            # 获取最近采集的新闻
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            q = db.query(NewsItem).filter(
                (NewsItem.collected_at != None) & (NewsItem.collected_at >= cutoff_time)  # noqa: E711
                |
                ((NewsItem.collected_at == None) & (NewsItem.published_at != None) & (NewsItem.published_at >= cutoff_time))  # noqa: E711
            )
            if source:
                q = q.filter(NewsItem.source == source)
            recent_news = (
                q.order_by(NewsItem.published_at.desc().nullslast())
                 .limit(limit)
                 .all()
            )  # 限制分析数量，避免API调用过多
            
            if not recent_news:
                return {
                    "success": True,
                    "message": "没有找到符合时间窗口的新闻（请先采集或扩大 hours_back）",
                    "analyzed_count": 0
                }
            
            app_logger.info(f"开始分析最近 {len(recent_news)} 条新闻")
            
            # 使用实体分析编排器进行综合分析
            analysis_result = await entity_analysis_orchestrator.batch_analyze_news(
                recent_news, batch_size=5
            )
            
            return {
                "success": True,
                "analyzed_count": analysis_result["successful_count"],
                "failed_count": analysis_result["failed_count"],
                "analysis_details": analysis_result
            }
            
        except Exception as e:
            app_logger.error(f"新闻分析失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def full_pipeline_execution(self, enable_analysis: bool = True) -> Dict[str, Any]:
        """执行完整数据管道：采集 + 分析"""
        pipeline_start = datetime.now()
        
        try:
            # 第一阶段：数据采集
            app_logger.info("开始执行完整数据管道 - 阶段1: 数据采集")
            collection_result = await self.collect_all_sources()
            
            if not collection_result["success"]:
                return {
                    "success": False,
                    "stage": "collection",
                    "error": "数据采集失败",
                    "details": collection_result
                }
            
            # 第二阶段：数据分析（可选）
            analysis_result = None
            if enable_analysis and collection_result["total_items"] > 0:
                app_logger.info("开始执行完整数据管道 - 阶段2: 实体分析")
                analysis_result = await self.analyze_collected_news(hours_back=1)
            
            pipeline_duration = (datetime.now() - pipeline_start).total_seconds()
            
            return {
                "success": True,
                "pipeline_duration": pipeline_duration,
                "collection_result": collection_result,
                "analysis_result": analysis_result,
                "summary": {
                    "collected_items": collection_result["total_items"],
                    "analyzed_items": analysis_result.get("analyzed_count", 0) if analysis_result else 0,
                    "stage_completed": "analysis" if analysis_result else "collection"
                }
            }
            
        except Exception as e:
            app_logger.error(f"完整数据管道执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "pipeline_duration": (datetime.now() - pipeline_start).total_seconds()
            }

    async def analyze_recent_news(self, hours: int = 1, limit: int = 20) -> Dict[str, Any]:
        """分析最近的新闻"""
        try:
            app_logger.info(f"开始分析最近 {hours} 小时内的新闻...")
            
            # 使用实体分析协调器进行分析
            result = await entity_analysis_orchestrator.analyze_recent_news(hours=hours, limit=limit)
            
            analyzed_count = result.get('analyzed_count', 0)
            app_logger.info(f"新闻分析完成: {analyzed_count} 条")
            
            return result
            
        except Exception as e:
            app_logger.error(f"新闻分析失败: {e}")
            return {
                "success": False,
                "analyzed_count": 0,
                "error": str(e)
            }

    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """清理旧数据（基于 collected_at 字段）。"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        try:
            db = next(get_db())

            q = db.query(NewsItem).filter(NewsItem.collected_at != None).filter(  # noqa: E711
                NewsItem.collected_at < cutoff_date
            )
            deleted_news = q.count()
            q.delete(synchronize_session=False)
            db.commit()

            app_logger.info(f"清理完成，删除了 {deleted_news} 条旧新闻")

            return {
                "success": True,
                "deleted_news": deleted_news,
                "cutoff_date": cutoff_date,
            }

        except Exception as e:
            app_logger.error(f"数据清理失败: {e}")
            return {"success": False, "error": str(e)}


# 创建全局实例
data_orchestrator = DataCollectionOrchestrator()
data_collection_orchestrator = data_orchestrator  # 为了兼容性，提供别名
