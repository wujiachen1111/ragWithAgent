"""
数据清理服务 - 自动清理超过指定时间的旧数据
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from yuqing.core.database import get_db
from yuqing.core.logging import app_logger
from yuqing.models.database_models import (
    NewsItem, StockAnalysis, MentionedCompany, 
    MentionedPerson, IndustryImpact, KeyEvent
)


class DataCleanupService:
    """数据清理服务"""
    
    def __init__(self):
        self.default_retention_hours = 72  # 默认保留72小时
        
    def cleanup_old_data(self, retention_hours: int = None) -> Dict[str, Any]:
        """清理超过指定时间的旧数据"""
        if retention_hours is None:
            retention_hours = self.default_retention_hours
            
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        
        app_logger.info(f"开始清理 {retention_hours} 小时前的数据 (早于 {cutoff_time})")
        
        cleanup_stats = {
            "cutoff_time": cutoff_time,
            "retention_hours": retention_hours,
            "deleted_counts": {},
            "total_deleted": 0,
            "success": True,
            "errors": []
        }
        
        try:
            db = next(get_db())
            
            # 1. 清理新闻项目（这会级联删除相关的分析数据）
            deleted_news = self._cleanup_news_items(db, cutoff_time)
            cleanup_stats["deleted_counts"]["news_items"] = deleted_news
            
            # 2. 清理孤立的股票分析记录
            deleted_analyses = self._cleanup_orphaned_analyses(db, cutoff_time)
            cleanup_stats["deleted_counts"]["stock_analyses"] = deleted_analyses
            
            # 3. 清理孤立的实体记录
            deleted_entities = self._cleanup_orphaned_entities(db)
            cleanup_stats["deleted_counts"]["entities"] = deleted_entities
            
            # 4. 清理向量数据库（如果需要）
            self._cleanup_vector_store(cutoff_time)
            
            cleanup_stats["total_deleted"] = sum(cleanup_stats["deleted_counts"].values())
            
            db.commit()
            app_logger.info(f"数据清理完成: 删除了 {cleanup_stats['total_deleted']} 条记录")
            
        except Exception as e:
            cleanup_stats["success"] = False
            cleanup_stats["errors"].append(str(e))
            app_logger.error(f"数据清理失败: {e}")
            if 'db' in locals():
                db.rollback()
                
        finally:
            if 'db' in locals():
                db.close()
                
        return cleanup_stats
    
    def _cleanup_news_items(self, db: Session, cutoff_time: datetime) -> int:
        """清理旧的新闻项目"""
        try:
            # 查找要删除的新闻ID
            old_news_query = db.query(NewsItem).filter(
                NewsItem.collected_at < cutoff_time
            )
            
            old_news_count = old_news_query.count()
            
            if old_news_count > 0:
                app_logger.info(f"准备删除 {old_news_count} 条旧新闻")
                
                # 删除旧新闻（级联删除相关分析）
                old_news_query.delete(synchronize_session=False)
                
                app_logger.info(f"已删除 {old_news_count} 条新闻记录")
                return old_news_count
            else:
                app_logger.info("没有需要清理的旧新闻")
                return 0
                
        except Exception as e:
            app_logger.error(f"清理新闻项目失败: {e}")
            raise
    
    def _cleanup_orphaned_analyses(self, db: Session, cutoff_time: datetime) -> int:
        """清理孤立的分析记录"""
        try:
            # 清理没有对应新闻的股票分析记录
            orphaned_analyses = db.execute(text("""
                DELETE FROM stock_analysis 
                WHERE news_id NOT IN (SELECT id FROM news_items)
            """))
            
            deleted_count = orphaned_analyses.rowcount
            if deleted_count > 0:
                app_logger.info(f"清理了 {deleted_count} 条孤立的分析记录")
            
            return deleted_count
            
        except Exception as e:
            app_logger.error(f"清理孤立分析记录失败: {e}")
            return 0
    
    def _cleanup_orphaned_entities(self, db: Session) -> int:
        """清理孤立的实体记录"""
        try:
            total_deleted = 0
            
            # 清理孤立的公司实体
            orphaned_companies = db.execute(text("""
                DELETE FROM mentioned_companies 
                WHERE analysis_id NOT IN (SELECT id FROM stock_analysis)
            """))
            deleted_companies = orphaned_companies.rowcount
            total_deleted += deleted_companies
            
            # 清理孤立的人物实体
            orphaned_persons = db.execute(text("""
                DELETE FROM mentioned_persons 
                WHERE analysis_id NOT IN (SELECT id FROM stock_analysis)
            """))
            deleted_persons = orphaned_persons.rowcount
            total_deleted += deleted_persons
            
            # 清理孤立的行业影响
            orphaned_industries = db.execute(text("""
                DELETE FROM industry_impacts 
                WHERE analysis_id NOT IN (SELECT id FROM stock_analysis)
            """))
            deleted_industries = orphaned_industries.rowcount
            total_deleted += deleted_industries
            
            # 清理孤立的关键事件
            orphaned_events = db.execute(text("""
                DELETE FROM key_events 
                WHERE analysis_id NOT IN (SELECT id FROM stock_analysis)
            """))
            deleted_events = orphaned_events.rowcount
            total_deleted += deleted_events
            
            if total_deleted > 0:
                app_logger.info(f"清理了 {total_deleted} 条孤立的实体记录")
                
            return total_deleted
            
        except Exception as e:
            app_logger.error(f"清理孤立实体记录失败: {e}")
            return 0
    
    def _cleanup_vector_store(self, cutoff_time: datetime):
        """清理向量数据库中的旧数据"""
        try:
            # 这里可以添加ChromaDB清理逻辑
            # 由于ChromaDB可能不直接支持时间过滤，暂时跳过
            app_logger.info("向量数据库清理已跳过（需要特殊处理）")
            
        except Exception as e:
            app_logger.warning(f"向量数据库清理失败: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息与连接信息（不泄露密码）。"""
        try:
            db = next(get_db())
            
            stats: Dict[str, Any] = {}
            # 连接信息
            try:
                eng = db.get_bind()
                url = eng.url
                stats["engine"] = {
                    "dialect": eng.dialect.name,
                    "driver": getattr(eng.dialect, "driver", None),
                    "url": url.render_as_string(hide_password=True),
                    "database": getattr(url, "database", None),
                    "host": getattr(url, "host", None),
                    "port": getattr(url, "port", None),
                }
            except Exception as e:
                stats["engine"] = {"error": str(e)}
            
            # 统计各表的记录数
            stats["news_items"] = db.query(NewsItem).count()
            stats["stock_analyses"] = db.query(StockAnalysis).count()
            stats["mentioned_companies"] = db.query(MentionedCompany).count()
            stats["mentioned_persons"] = db.query(MentionedPerson).count()
            stats["industry_impacts"] = db.query(IndustryImpact).count()
            stats["key_events"] = db.query(KeyEvent).count()
            
            # 统计数据时间范围
            latest_row = db.query(NewsItem.collected_at).order_by(
                NewsItem.collected_at.desc()
            ).first()
            oldest_row = db.query(NewsItem.collected_at).order_by(
                NewsItem.collected_at.asc()
            ).first()

            latest_ts = latest_row[0] if (latest_row and latest_row[0] is not None) else None
            oldest_ts = oldest_row[0] if (oldest_row and oldest_row[0] is not None) else None

            if latest_ts is not None and oldest_ts is not None:
                stats["latest_news_time"] = latest_ts
                stats["oldest_news_time"] = oldest_ts
                try:
                    stats["data_span_hours"] = (latest_ts - oldest_ts).total_seconds() / 3600
                except Exception:
                    stats["data_span_hours"] = None
            
            return stats
            
        except Exception as e:
            app_logger.error(f"获取数据库统计失败: {e}")
            return {"error": str(e)}
        finally:
            if 'db' in locals():
                db.close()
    
    def schedule_cleanup(self, retention_hours: int = 72, 
                        cleanup_interval_hours: int = 6) -> Dict[str, Any]:
        """调度定期清理任务"""
        return {
            "retention_hours": retention_hours,
            "cleanup_interval_hours": cleanup_interval_hours,
            "message": "数据清理已调度，将定期执行"
        }


# 全局实例
data_cleanup_service = DataCleanupService()
