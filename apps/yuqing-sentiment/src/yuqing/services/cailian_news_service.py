import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

try:
    import akshare as ak
except ImportError:
    ak = None

from yuqing.core.logging import app_logger
from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem
from sqlalchemy.orm import Session


class CailianNewsService:
    """财联社新闻服务 - 获取财联社实时电报新闻"""
    
    def __init__(self):
        self.source_name = "cailian"
        self.data_dir = "data/cailian_news"
        self.news_hashes = set()
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载已有的新闻哈希
        self._load_existing_hashes()
    
    def _load_existing_hashes(self):
        """加载已有文件中的新闻哈希值"""
        try:
            # 获取最近3天的文件来加载哈希值
            today = datetime.now()
            for i in range(3):
                date = today - timedelta(days=i)
                filename = self._get_news_filename(date)
                
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        try:
                            news_data = json.load(f)
                            for item in news_data:
                                if 'hash' in item:
                                    self.news_hashes.add(item['hash'])
                                else:
                                    content_hash = self._calculate_hash(item['content'])
                                    self.news_hashes.add(content_hash)
                        except json.JSONDecodeError:
                            app_logger.warning(f"文件 {filename} 格式错误，跳过加载哈希值")
            
            app_logger.info(f"财联社服务已加载 {len(self.news_hashes)} 条新闻哈希值")
        except Exception as e:
            app_logger.error(f"加载财联社新闻哈希值时出错: {e}")
            self.news_hashes = set()
    
    def _calculate_hash(self, content: str) -> str:
        """计算新闻内容的哈希值"""
        return hashlib.md5(str(content).encode('utf-8')).hexdigest()
    
    def _get_news_filename(self, date: datetime = None) -> str:
        """获取指定日期的新闻文件名"""
        if date is None:
            date = datetime.now()
        date_str = date.strftime('%Y%m%d')
        return os.path.join(self.data_dir, f"cailian_news_{date_str}.json")
    
    async def fetch_cailian_news(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取财联社电报新闻"""
        if ak is None:
            app_logger.error("akshare未安装，无法获取财联社新闻")
            return []
        
        try:
            app_logger.info("开始获取财联社电报数据")
            
            # 在线程池中执行akshare调用（因为akshare是同步的）
            loop = asyncio.get_event_loop()
            stock_info_df = await loop.run_in_executor(
                None, 
                lambda: ak.stock_info_global_cls(symbol="全部")
            )
            
            if stock_info_df.empty:
                app_logger.warning("获取的财联社电报数据为空")
                return []
            
            app_logger.info(f"获取财联社数据形状: {stock_info_df.shape}")
            
            # 转换为标准格式
            news_items = []
            new_count = 0
            
            for _, row in stock_info_df.iterrows():
                try:
                    content = str(row.get("内容", ""))
                    title = str(row.get("标题", ""))
                    
                    # 计算内容哈希值
                    content_hash = self._calculate_hash(content)
                    
                    # 检查是否已存在
                    if content_hash in self.news_hashes:
                        continue
                    
                    # 添加新的哈希值
                    self.news_hashes.add(content_hash)
                    new_count += 1
                    
                    # 处理日期时间
                    pub_date = row.get("发布日期", "")
                    pub_time = row.get("发布时间", "")
                    
                    if hasattr(pub_date, 'isoformat'):
                        pub_date = pub_date.isoformat()
                    else:
                        pub_date = str(pub_date)
                    
                    if hasattr(pub_time, 'isoformat'):
                        pub_time = pub_time.isoformat()
                    else:
                        pub_time = str(pub_time)
                    
                    # 构建完整的发布时间
                    try:
                        if pub_date and pub_time:
                            # 处理时间格式
                            if len(pub_time) <= 8:  # HH:MM:SS格式
                                published_at = datetime.fromisoformat(f"{pub_date} {pub_time}")
                            else:
                                published_at = datetime.fromisoformat(pub_time)
                        else:
                            published_at = datetime.now(timezone.utc)
                    except:
                        published_at = datetime.now(timezone.utc)
                    
                    # 生成唯一ID
                    news_id = f"cailian_{content_hash[:16]}"
                    
                    news_item = {
                        "id": news_id,
                        "title": title or content[:50] + "...",
                        "content": content,
                        "source": self.source_name,
                        "source_url": f"https://www.cls.cn/",  # 财联社官网
                        "published_at": published_at.isoformat(),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                        "language": "zh",
                        "region": "china",
                        "raw_data": {
                            "original_title": title,
                            "original_content": content,
                            "publish_date": pub_date,
                            "publish_time": pub_time,
                            "hash": content_hash
                        }
                    }
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    app_logger.error(f"处理财联社新闻项时出错: {e}")
                    continue
                
                # 限制数量
                if len(news_items) >= limit:
                    break
            
            app_logger.info(f"财联社获取完成: 新增 {new_count} 条新闻")
            
            # 保存到本地文件
            if news_items:
                await self._save_to_file(news_items)
            
            return news_items
            
        except Exception as e:
            app_logger.error(f"获取财联社新闻时出错: {e}")
            return []
    
    async def _save_to_file(self, news_items: List[Dict[str, Any]]):
        """保存新闻到本地文件"""
        try:
            filename = self._get_news_filename()
            
            # 如果文件已存在，合并数据
            existing_data = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        app_logger.warning(f"文件 {filename} 格式错误，使用新数据替换")
            
            # 合并并按时间排序
            all_data = existing_data + news_items
            all_data.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            
            # 保存数据
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)
            
            app_logger.info(f"财联社新闻已保存到文件: {filename}")
            
        except Exception as e:
            app_logger.error(f"保存财联社新闻到文件时出错: {e}")
    
    async def save_to_database(self, news_items: List[Dict[str, Any]]) -> int:
        """保存新闻到数据库"""
        if not news_items:
            return 0
        
        try:
            db = next(get_db())
            saved_count = 0
            
            for item in news_items:
                try:
                    # 检查是否已存在
                    existing = db.query(NewsItem).filter(NewsItem.id == item["id"]).first()
                    if existing:
                        continue
                    
                    # 创建新闻项
                    news_item = NewsItem(
                        id=item["id"],
                        title=item["title"],
                        content=item["content"],
                        source=item["source"],
                        source_url=item["source_url"],
                        published_at=datetime.fromisoformat(item["published_at"].replace('Z', '+00:00')),
                        collected_at=datetime.fromisoformat(item["collected_at"].replace('Z', '+00:00')),
                        language=item["language"],
                        region=item["region"],
                        raw_data=item["raw_data"]
                    )
                    
                    db.add(news_item)
                    saved_count += 1
                    
                except Exception as e:
                    app_logger.error(f"保存财联社新闻项到数据库时出错: {e}")
                    continue
            
            db.commit()
            app_logger.info(f"财联社新闻保存到数据库: {saved_count} 条")
            return saved_count
            
        except Exception as e:
            app_logger.error(f"保存财联社新闻到数据库时出错: {e}")
            if 'db' in locals():
                db.rollback()
            return 0
        finally:
            if 'db' in locals():
                db.close()
    
    async def get_latest_news(self, days: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的财联社新闻"""
        try:
            news_data = []
            today = datetime.now()
            
            # 从文件中读取数据
            for i in range(days):
                date = today - timedelta(days=i)
                filename = self._get_news_filename(date)
                
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            news_data.extend(data)
                        except json.JSONDecodeError:
                            app_logger.error(f"读取文件 {filename} 时出错")
            
            # 去重并排序
            unique_news = {}
            for item in news_data:
                item_hash = item.get('raw_data', {}).get('hash', '')
                if item_hash and item_hash not in unique_news:
                    unique_news[item_hash] = item
            
            result = list(unique_news.values())
            result.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            
            return result[:limit]
            
        except Exception as e:
            app_logger.error(f"获取财联社历史新闻时出错: {e}")
            return []
    
    async def search_news(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索财联社新闻"""
        try:
            # 先获取最新新闻
            all_news = await self.get_latest_news(days=3, limit=500)
            
            # 关键词过滤
            filtered_news = []
            for news in all_news:
                content = news.get('content', '')
                title = news.get('title', '')
                
                if keyword.lower() in content.lower() or keyword.lower() in title.lower():
                    filtered_news.append(news)
                
                if len(filtered_news) >= limit:
                    break
            
            return filtered_news
            
        except Exception as e:
            app_logger.error(f"搜索财联社新闻时出错: {e}")
            return []


# 创建全局实例
cailian_news_service = CailianNewsService()
