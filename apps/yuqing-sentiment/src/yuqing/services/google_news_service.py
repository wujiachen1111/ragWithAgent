import feedparser
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
from urllib.parse import quote
from yuqing.core.logging import app_logger
from yuqing.core.config import settings
from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem
from sqlalchemy.orm import Session


class GoogleNewsService:
    """Google News RSS数据采集服务"""
    
    def __init__(self):
        self.base_url = "https://news.google.com/rss"
        self.search_url = "https://news.google.com/rss/search"
        
    async def fetch_latest_news(self, language: str = "zh", region: str = "CN", 
                               limit: int = 100) -> List[Dict[str, Any]]:
        """获取最新新闻"""
        try:
            # 构建RSS URL
            if language == "zh":
                url = f"{self.base_url}?hl={language}&gl={region}&ceid={region}:{language}"
            else:
                url = f"{self.base_url}?hl={language}&gl={region}"
            
            app_logger.info(f"获取Google News最新新闻: {url}")
            
            # 解析RSS feed
            feed = feedparser.parse(url)
            
            if feed.bozo:
                app_logger.warning(f"RSS feed解析有警告: {feed.bozo_exception}")
            
            news_items = []
            for entry in feed.entries[:limit]:
                news_item = self._parse_entry(entry, "google_news_latest")
                if news_item:
                    news_items.append(news_item)
            
            app_logger.info(f"成功获取 {len(news_items)} 条最新新闻")
            return news_items
            
        except Exception as e:
            app_logger.error(f"获取Google News最新新闻失败: {e}")
            return []
    
    async def search_news(self, query: str, language: str = "zh", 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """搜索特定关键词新闻"""
        try:
            # URL编码查询词
            encoded_query = quote(query)
            url = f"{self.search_url}?q={encoded_query}&hl={language}"
            
            app_logger.info(f"搜索Google News: {query}")
            
            # 解析RSS feed
            feed = feedparser.parse(url)
            
            news_items = []
            for entry in feed.entries[:limit]:
                news_item = self._parse_entry(entry, "google_news_search", query)
                if news_item:
                    news_items.append(news_item)
            
            app_logger.info(f"搜索到 {len(news_items)} 条相关新闻")
            return news_items
            
        except Exception as e:
            app_logger.error(f"搜索Google News失败: {e}")
            return []
    
    async def fetch_finance_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取财经新闻"""
        finance_keywords = [
            "股票", "股市", "A股", "港股", "美股", "股价", "涨停", "跌停",
            "IPO", "并购", "财报", "业绩", "利润", "营收", "市值",
            "基金", "投资", "银行", "保险", "证券", "期货",
            "央行", "货币政策", "利率", "通胀", "GDP", "经济"
        ]
        
        all_news = []
        for keyword in finance_keywords[:5]:  # 限制查询数量
            news = await self.search_news(keyword, limit=10)
            all_news.extend(news)
            await asyncio.sleep(1)  # 避免请求过于频繁
        
        # 去重
        unique_news = self._deduplicate_news(all_news)
        return unique_news[:limit]
    
    def _parse_entry(self, entry, source_type: str, query: str = "") -> Optional[Dict[str, Any]]:
        """解析RSS条目"""
        try:
            # 提取基本信息
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            description = entry.get("summary", "").strip()
            
            # 解析发布时间
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "published"):
                try:
                    from dateutil import parser
                    published_at = parser.parse(entry.published)
                except:
                    pass
            
            if not published_at:
                published_at = datetime.now(timezone.utc)
            
            # 生成唯一ID
            content_hash = hashlib.md5((title + link).encode()).hexdigest()
            
            return {
                "id": f"google_news_{content_hash}",
                "title": title,
                "content": description,
                "summary": description[:200] if description else title[:200],
                "source": "google_news",
                "source_url": link,
                "published_at": published_at,
                "collected_at": datetime.now(timezone.utc),
                "language": "zh",
                "region": "global",
                "raw_data": {
                    "source_type": source_type,
                    "query": query,
                    "entry": {
                        "title": entry.get("title"),
                        "link": entry.get("link"),
                        "summary": entry.get("summary"),
                        "published": entry.get("published"),
                        "tags": [tag.get("term") for tag in entry.get("tags", [])],
                        "source": entry.get("source", {})
                    }
                }
            }
            
        except Exception as e:
            app_logger.error(f"解析RSS条目失败: {e}")
            return None
    
    def _deduplicate_news(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重新闻"""
        seen_titles = set()
        seen_urls = set()
        unique_news = []
        
        for news in news_list:
            title = news.get("title", "")
            url = news.get("source_url", "")
            
            # 简单的去重逻辑
            title_key = title.lower().strip()
            if title_key not in seen_titles and url not in seen_urls:
                seen_titles.add(title_key)
                seen_urls.add(url)
                unique_news.append(news)
        
        return unique_news
    
    async def get_trending_topics(self) -> List[str]:
        """获取热门话题"""
        try:
            # 获取最新新闻并提取关键词
            latest_news = await self.fetch_latest_news(limit=30)
            
            # 简单的关键词提取（后续可以用更复杂的NLP）
            topics = []
            for news in latest_news:
                title = news.get("title", "")
                # 提取可能的公司名、概念等
                if "股份" in title or "公司" in title or "集团" in title:
                    topics.append(title)
            
            return topics[:10]
            
        except Exception as e:
            app_logger.error(f"获取热门话题失败: {e}")
            return []

    async def save_to_database(self, news_items: List[Dict[str, Any]]) -> int:
        """保存新闻到数据库"""
        if not news_items:
            return 0
            
        try:
            db = next(get_db())
            saved_count = 0
            
            for news_data in news_items:
                try:
                    # 检查是否已存在
                    existing_news = db.query(NewsItem).filter(
                        NewsItem.id == news_data["id"]
                    ).first()
                    
                    if existing_news:
                        continue  # 跳过已存在的新闻
                    
                    # 创建新的新闻记录
                    news_item = NewsItem(
                        id=news_data["id"],
                        title=news_data["title"],
                        content=news_data.get("content", ""),
                        summary=news_data.get("summary"),
                        source=news_data["source"],
                        source_url=news_data["source_url"],
                        published_at=news_data["published_at"],
                        collected_at=news_data["collected_at"],
                        language=news_data.get("language", "zh"),
                        region=news_data.get("region", "global"),
                        raw_data=news_data.get("raw_data", {}),
                        analysis_status="pending"
                    )
                    
                    db.add(news_item)
                    saved_count += 1
                    
                except Exception as item_error:
                    app_logger.error(f"保存单条Google新闻失败 {news_data.get('id', 'unknown')}: {item_error}")
                    continue
            
            db.commit()
            app_logger.info(f"Google新闻保存到数据库: {saved_count} 条")
            return saved_count
            
        except Exception as e:
            app_logger.error(f"保存Google新闻到数据库失败: {e}")
            if 'db' in locals():
                db.rollback()
            return 0
        finally:
            if 'db' in locals():
                db.close()

    def _enhanced_deduplicate(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """增强的去重机制"""
        try:
            # 获取数据库中已有的新闻ID
            db = next(get_db())
            existing_ids = set()
            
            # 批量查询现有ID
            news_ids = [item["id"] for item in news_items]
            existing_records = db.query(NewsItem.id).filter(NewsItem.id.in_(news_ids)).all()
            existing_ids = {record.id for record in existing_records}
            
            # 过滤掉已存在的新闻
            unique_news = []
            seen_urls = set()
            
            for news in news_items:
                if news["id"] in existing_ids:
                    continue  # 跳过数据库中已存在的
                
                url = news.get("source_url", "")
                if url in seen_urls:
                    continue  # 跳过URL重复的
                
                seen_urls.add(url)
                unique_news.append(news)
            
            app_logger.info(f"Google新闻去重: 原始{len(news_items)}条 -> 去重后{len(unique_news)}条")
            return unique_news
            
        except Exception as e:
            app_logger.error(f"Google新闻去重失败: {e}")
            return self._deduplicate_news(news_items)  # 降级到简单去重
        finally:
            if 'db' in locals():
                db.close()


# 全局实例
google_news_service = GoogleNewsService()
