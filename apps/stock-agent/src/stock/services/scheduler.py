"""
股票数据刷新调度器
"""

import asyncio
import uuid
from datetime import datetime, time
from typing import Optional, Dict, Any
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import pytz

from ..models.base import RefreshTask, SchedulerConfig, BatchProcessResult
from ..core.database import db_manager
from .stock_service import StockService


class StockRefreshScheduler:
    """股票数据刷新调度器"""
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self.scheduler = AsyncIOScheduler(timezone=self.config.timezone)
        self.stock_service = StockService()
        self._running_tasks: Dict[str, RefreshTask] = {}
        
        # 设置调度器事件监听
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
    async def start(self):
        """启动调度器"""
        if not self.config.enabled:
            logger.info("📅 股票刷新调度器已禁用")
            return
            
        try:
            # 添加全局刷新任务
            await self._schedule_global_refresh()
            
            # 启动调度器
            self.scheduler.start()
            logger.info("📅 股票刷新调度器启动成功")
            
        except Exception as e:
            logger.error(f"❌ 调度器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown(wait=False)
            logger.info("📅 股票刷新调度器已停止")
        except Exception as e:
            logger.error(f"❌ 调度器停止失败: {e}")
    
    async def _schedule_global_refresh(self):
        """安排全局刷新任务"""
        # 解析时间
        hour, minute = map(int, self.config.global_refresh_time.split(':'))
        
        # 创建 cron 触发器
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week=','.join(map(str, self.config.global_refresh_weekdays)),
            timezone=pytz.timezone(self.config.timezone)
        )
        
        # 添加任务
        self.scheduler.add_job(
            func=self._execute_global_refresh,
            trigger=trigger,
            id='global_refresh',
            name='全局股票数据刷新',
            replace_existing=True,
            max_instances=1
        )
        
        logger.info(f"📅 已安排全局刷新任务: 每周 {self.config.global_refresh_weekdays} 的 {self.config.global_refresh_time}")
    
    async def _execute_global_refresh(self):
        """执行全局刷新"""
        task_id = f"global_refresh_{uuid.uuid4().hex[:8]}"
        task = RefreshTask(
            task_id=task_id,
            task_type="global_refresh",
            status="running",
            start_time=datetime.now()
        )
        
        try:
            logger.info(f"🔄 开始执行全局股票数据刷新 - 任务ID: {task_id}")
            
            # 保存任务到内存
            self._running_tasks[task_id] = task
            
            # 保存任务到数据库
            await self._save_task(task)
            
            # 获取所有股票代码
            stock_codes = await self.stock_service.get_all_stock_codes()
            
            if not stock_codes:
                raise Exception("未获取到股票代码列表")
            
            logger.info(f"📊 准备刷新 {len(stock_codes)} 只股票的数据")
            
            # 批量刷新股票数据
            result = await self.stock_service.batch_fetch_stocks(stock_codes, batch_size=50)
            
            # 更新任务状态
            task.status = "completed"
            task.end_time = datetime.now()
            task.result = result
            
            # 计算执行时长
            if task.start_time and task.end_time:
                task.duration = (task.end_time - task.start_time).total_seconds()
            
            logger.info(f"✅ 全局股票数据刷新完成 - 成功: {result.success}/{result.total}")
            
        except Exception as e:
            logger.error(f"❌ 全局股票数据刷新失败: {e}")
            task.status = "failed"
            task.end_time = datetime.now()
            task.error_message = str(e)
            
        finally:
            # 更新数据库
            await self._save_task(task)
            
            # 从内存中移除任务
            self._running_tasks.pop(task_id, None)
    
    async def refresh_single_stock(self, stock_code: str) -> RefreshTask:
        """刷新单只股票数据"""
        task_id = f"single_refresh_{stock_code}_{uuid.uuid4().hex[:8]}"
        task = RefreshTask(
            task_id=task_id,
            task_type="single_refresh",
            stock_code=stock_code,
            status="running",
            start_time=datetime.now()
        )
        
        try:
            logger.info(f"🔄 开始刷新股票 {stock_code} 数据 - 任务ID: {task_id}")
            
            # 保存任务到内存
            self._running_tasks[task_id] = task
            
            # 保存任务到数据库
            await self._save_task(task)
            
            # 刷新单只股票数据
            success = await self.stock_service.fetch_and_save_stock(stock_code, refresh_holders=False)
            
            # 根据刷新结果构造 BatchProcessResult
            if success:
                result = BatchProcessResult(
                    total=1, success=1, failed=0, success_rate=1.0,
                    processed_codes=[stock_code], failed_codes=[]
                )
                task.status = "completed"
                task.result = result
                logger.info(f"✅ 股票 {stock_code} 数据刷新成功")
            else:
                result = BatchProcessResult(
                    total=1, success=0, failed=1, success_rate=0.0,
                    processed_codes=[], failed_codes=[stock_code]
                )
                task.status = "failed"
                task.result = result
                task.error_message = f"股票 {stock_code} 数据获取失败"
                logger.error(f"❌ 股票 {stock_code} 数据刷新失败")

        except Exception as e:
            logger.error(f"❌ 刷新股票 {stock_code} 时发生错误: {e}")
            task.status = "failed"
            task.error_message = str(e)
            # 即使发生异常，也创建一个空的result对象，避免序列化错误
            if not task.result:
                task.result = BatchProcessResult(
                    total=1, success=0, failed=1, success_rate=0.0,
                    processed_codes=[], failed_codes=[stock_code]
                )
            
        finally:
            task.end_time = datetime.now()
            
            # 计算执行时长
            if task.start_time and task.end_time:
                task.duration = (task.end_time - task.start_time).total_seconds()
            
            # 更新数据库
            await self._save_task(task)
            
            # 从内存中移除任务
            self._running_tasks.pop(task_id, None)
        
        return task
    
    async def get_task_status(self, task_id: str) -> Optional[RefreshTask]:
        """获取任务状态"""
        # 先查内存中的运行任务
        if task_id in self._running_tasks:
            return self._running_tasks[task_id]
        
        # 再查数据库中的历史任务
        if db_manager.db is not None:
            task_data = db_manager.tasks_collection.find_one({"task_id": task_id})
            if task_data:
                if "_id" in task_data: # 确保 _id 字段在从数据库获取时被处理
                    task_data["_id"] = str(task_data["_id"])
                return RefreshTask(**task_data)
        
        return None
    
    async def get_recent_tasks(self, limit: int = 10) -> list[RefreshTask]:
        """获取最近的任务列表"""
        tasks = []
        
        # 添加运行中的任务
        for task in self._running_tasks.values():
            tasks.append(task)
        
        # 从数据库获取历史任务
        if db_manager.db is not None:
            cursor = db_manager.tasks_collection.find().sort("created_time", -1).limit(limit)
            for task_data in cursor:
                # 避免重复添加运行中的任务
                if task_data["task_id"] not in self._running_tasks:
                    if "_id" in task_data: # 确保 _id 字段在从数据库获取时被处理
                        task_data["_id"] = str(task_data["_id"])
                    tasks.append(RefreshTask(**task_data))
        
        # 按创建时间排序
        tasks.sort(key=lambda x: x.created_time, reverse=True)
        
        return tasks[:limit]
    
    async def _save_task(self, task: RefreshTask):
        """保存任务到数据库"""
        try:
            if db_manager.db is None:
                return
            
            # 转换为字典并处理特殊字段
            task_dict = task.model_dump()
            
            # 使用 upsert 操作
            db_manager.tasks_collection.update_one(
                {"task_id": task.task_id},
                {"$set": task_dict},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"保存任务 {task.task_id} 到数据库失败: {e}")
    
    def _job_executed(self, event):
        """任务执行完成事件"""
        logger.debug(f"调度任务执行完成: {event.job_id}")
    
    def _job_error(self, event):
        """任务执行错误事件"""
        logger.error(f"调度任务执行错误: {event.job_id}, 错误: {event.exception}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self.scheduler.running if self.scheduler else False,
            "config": self.config.model_dump(),
            "running_tasks": len(self._running_tasks),
            "next_global_refresh": self._get_next_run_time("global_refresh"),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in self.scheduler.get_jobs()
            ]
        }
    
    def _get_next_run_time(self, job_id: str) -> Optional[str]:
        """获取指定任务的下次运行时间"""
        try:
            job = self.scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except Exception:
            pass
        return None
