"""
多API密钥管理器 - 实现负载均衡和并发处理
"""
import asyncio
import random
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from dataclasses import dataclass

from yuqing.core.logging import app_logger
from yuqing.services.deepseek_service import DeepSeekService


@dataclass
class APIKeyConfig:
    """API密钥配置"""
    key: str
    name: str
    rate_limit: int = 10  # 每分钟请求限制
    last_request_time: float = 0
    error_count: int = 0
    is_active: bool = True


class MultiKeyDeepSeekService:
    """多密钥DeepSeek服务管理器"""
    
    def __init__(self, api_keys: List[str]):
        self.api_configs = [
            APIKeyConfig(key=key, name=f"API-{i+1}")
            for i, key in enumerate(api_keys)
        ]
        self.services = {}
        self._init_services()
        
        app_logger.info(f"初始化多密钥服务，共 {len(api_keys)} 个API密钥")
    
    def _init_services(self):
        """初始化每个API密钥对应的服务实例"""
        for config in self.api_configs:
            service = DeepSeekService()
            service.api_key = config.key  # 覆盖默认密钥
            self.services[config.name] = service
    
    def get_available_key(self) -> Optional[APIKeyConfig]:
        """获取可用的API密钥"""
        current_time = time.time()
        available_keys = [
            config for config in self.api_configs
            if config.is_active and 
            (current_time - config.last_request_time) > 6  # 6秒间隔
        ]
        
        if not available_keys:
            # 如果没有完全可用的，选择错误最少的
            available_keys = [
                config for config in self.api_configs
                if config.is_active
            ]
            available_keys.sort(key=lambda x: x.error_count)
        
        if available_keys:
            # 随机选择以平衡负载
            return random.choice(available_keys[:3])  # 从错误最少的3个中随机选
        
        return None
    
    def mark_key_used(self, config: APIKeyConfig, success: bool = True):
        """标记密钥使用情况"""
        config.last_request_time = time.time()
        if not success:
            config.error_count += 1
            if config.error_count > 5:  # 连续5次失败就暂停使用
                config.is_active = False
                app_logger.warning(f"API密钥 {config.name} 因连续失败被暂停")
        else:
            config.error_count = max(0, config.error_count - 1)  # 成功时减少错误计数
    
    def analyze_single_news_with_key(self, news_data: Dict[str, Any], key_config: APIKeyConfig) -> Optional[Dict[str, Any]]:
        """使用指定密钥分析单条新闻（同步包装器）"""
        try:
            service = self.services[key_config.name]
            
            # 创建临时的NewsItem对象
            from yuqing.models.database_models import NewsItem
            news_item = NewsItem(
                id=news_data.get("id", "temp"),
                title=news_data.get("title", ""),
                content=news_data.get("content", ""),
                summary=news_data.get("summary", ""),
                source=news_data.get("source", "unknown"),
                published_at=news_data.get("published_at"),
                analysis_status="pending"
            )
            
            # 使用asyncio.run来运行异步方法
            import asyncio
            try:
                # 在线程中使用新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(service.analyze_single_news(news_item))
                
                if result:
                    self.mark_key_used(key_config, success=True)
                    app_logger.debug(f"✅ {key_config.name} 成功分析新闻: {news_data['title'][:30]}...")
                    return {
                        "success": True,
                        "news_id": news_data.get("id"),
                        "sentiment_result": result,
                        "api_key": key_config.name
                    }
                else:
                    self.mark_key_used(key_config, success=False)
                    return None
                    
            finally:
                loop.close()
                
        except Exception as e:
            self.mark_key_used(key_config, success=False)
            app_logger.error(f"❌ {key_config.name} 分析失败: {e}")
            return None
    
    async def analyze_news_parallel(self, news_list: List[Dict[str, Any]], max_workers: int = None) -> List[Dict[str, Any]]:
        """并行分析新闻列表"""
        if not news_list:
            return []
        
        if max_workers is None:
            max_workers = min(len(self.api_configs), len(news_list), 8)  # 最多8个并发
        
        app_logger.info(f"🚀 开始并行分析 {len(news_list)} 条新闻，使用 {max_workers} 个并发")
        
        results = []
        failed_news = []
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建任务映射
            future_to_news = {}
            
            for news_data in news_list:
                key_config = self.get_available_key()
                if key_config:
                    future = executor.submit(
                        self.analyze_single_news_with_key,
                        news_data,
                        key_config
                    )
                    future_to_news[future] = news_data
                else:
                    failed_news.append(news_data)
                    app_logger.warning("⚠️ 没有可用的API密钥")
                
                # 控制提交速度，避免瞬间压力过大
                if len(future_to_news) % 5 == 0:
                    await asyncio.sleep(0.1)
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_news.keys()):
                news_data = future_to_news[future]
                result = future.result()
                
                if result:
                    results.append(result)
                    completed += 1
                    if completed % 5 == 0:  # 每5个显示一次进度
                        app_logger.info(f"📊 已完成 {completed}/{len(news_list)} 条新闻分析")
                else:
                    failed_news.append(news_data)
        
        # 处理失败的新闻（降级为串行处理）
        if failed_news:
            app_logger.info(f"🔄 串行重试 {len(failed_news)} 条失败的新闻")
            for news_data in failed_news:
                key_config = self.get_available_key()
                if key_config:
                    result = self.analyze_single_news_with_key(news_data, key_config)
                    if result:
                        results.append(result)
                    time.sleep(1)  # 串行处理时增加间隔
        
        app_logger.info(f"🎉 并行分析完成！成功: {len(results)}, 失败: {len(news_list) - len(results)}")
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有API密钥状态"""
        return {
            "total_keys": len(self.api_configs),
            "active_keys": len([c for c in self.api_configs if c.is_active]),
            "key_status": [
                {
                    "name": config.name,
                    "active": config.is_active,
                    "error_count": config.error_count,
                    "last_used": config.last_request_time
                }
                for config in self.api_configs
            ]
        }


# 全局多密钥服务实例
multi_key_service = None

def init_multi_key_service(api_keys: List[str]):
    """初始化多密钥服务"""
    global multi_key_service
    multi_key_service = MultiKeyDeepSeekService(api_keys)
    return multi_key_service

def get_multi_key_service() -> Optional[MultiKeyDeepSeekService]:
    """获取多密钥服务实例"""
    return multi_key_service
