"""
Stock Agent 基础数据模型
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StockData(BaseModel):
    """股票数据模型"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    basic_info: Dict[str, Any] = Field(default_factory=dict, description="基本信息")
    holders: List[Dict[str, Any]] = Field(default_factory=list, description="股东信息")
    kline_day: List[Dict[str, Any]] = Field(default_factory=list, description="日K线数据")
    kline_month: List[Dict[str, Any]] = Field(default_factory=list, description="月K线数据")
    update_time: datetime = Field(default_factory=datetime.now, description="更新时间")


class StockQuery(BaseModel):
    """股票查询条件模型"""
    codes: Optional[List[str]] = Field(None, description="股票代码列表")
    industries: Optional[List[str]] = Field(None, description="行业列表")
    min_market_cap: Optional[float] = Field(None, description="最小市值(亿元)")
    max_market_cap: Optional[float] = Field(None, description="最大市值(亿元)")
    min_pe: Optional[float] = Field(None, description="最小市盈率")
    max_pe: Optional[float] = Field(None, description="最大市盈率")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


class BatchProcessResult(BaseModel):
    """批处理结果模型"""
    total: int = Field(..., description="总数量")
    success: int = Field(..., description="成功数量")
    failed: int = Field(..., description="失败数量")
    success_rate: float = Field(..., description="成功率")
    processed_codes: List[str] = Field(default_factory=list, description="成功处理的股票代码")
    failed_codes: List[str] = Field(default_factory=list, description="失败的股票代码")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行时长(秒)")


class RefreshTask(BaseModel):
    """刷新任务模型"""
    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型: global_refresh 或 single_refresh")
    stock_code: Optional[str] = Field(None, description="股票代码(单只股票刷新时使用)")
    status: str = Field(default="pending", description="任务状态: pending, running, completed, failed")
    created_time: datetime = Field(default_factory=datetime.now, description="创建时间")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行时长(秒)")
    result: Optional[BatchProcessResult] = Field(None, description="执行结果")
    error_message: Optional[str] = Field(None, description="错误信息")


class SchedulerConfig(BaseModel):
    """调度器配置模型"""
    enabled: bool = Field(default=True, description="是否启用调度器")
    global_refresh_time: str = Field(default="15:00", description="全局刷新时间 (HH:MM)")
    global_refresh_weekdays: List[int] = Field(default=[1, 2, 3, 4, 5], description="全局刷新工作日 (1-7, 1=周一)")
    timezone: str = Field(default="Asia/Shanghai", description="时区")
    max_concurrent_tasks: int = Field(default=1, description="最大并发任务数")
    
    @classmethod
    def from_env(cls) -> 'SchedulerConfig':
        """从环境变量创建配置"""
        import os
        
        # 从环境变量读取配置
        enabled = os.getenv('SCHEDULER_ENABLED', 'true').lower() in ['true', '1', 'yes', 'on']
        
        return cls(
            enabled=enabled,
            global_refresh_time=os.getenv('SCHEDULER_REFRESH_TIME', "15:00"),
            timezone=os.getenv('SCHEDULER_TIMEZONE', "Asia/Shanghai"),
            max_concurrent_tasks=int(os.getenv('SCHEDULER_MAX_TASKS', '1'))
        )