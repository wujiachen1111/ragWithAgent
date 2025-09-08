"""
智能热点新闻发现服务
通过多策略组合发现实时热点，而非依赖固定关键词
"""

import asyncio
import re
from typing import List, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from collections import Counter
import jieba
import feedparser
from urllib.parse import quote
from yuqing.core.logging import app_logger
from yuqing.services.google_news_service import google_news_service
from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem
from sqlalchemy.orm import Session


class HotNewsDiscoveryService:
    """智能热点新闻发现服务"""
    
    def __init__(self):
        # 扩展的RSS源，覆盖更多维度
        self.rss_sources = {
            # 全球通用热点
            "global_trending": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtVnVHZ0pWVXlnQVAB?hl=zh&gl=CN&ceid=CN:zh",
            
            # 财经商业热点  
            "business_trending": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=zh&gl=CN&ceid=CN:zh",
            
            # 科技热点
            "tech_trending": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=zh&gl=CN&ceid=CN:zh",
            
            # 中国大陆新闻
            "china_news": "https://news.google.com/rss?hl=zh&gl=CN&ceid=CN:zh",
            
            # 香港财经
            "hongkong_finance": "https://news.google.com/rss?hl=zh&gl=HK&ceid=HK:zh",
            
            # 美国商业
            "us_business": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en&gl=US&ceid=US:en"
        }
        
        # 股票相关关键词模式 (更精确的匹配)
        self.stock_patterns = [
            r'\b\d{6}\b',        # A股代码 如 000001 (6位数字)
            r'\b[A-Z]{2,5}\b',   # 美股代码 如 AAPL (2-5位大写字母)
            r'\b\d{5}\.(HK|SH|SZ)\b',  # 港股/A股完整代码
            r'\bSH\d{6}\b',      # 上海A股
            r'\bSZ\d{6}\b',      # 深圳A股
        ]
        
        # 板块/行业关键词
        self.sector_keywords = {
            "科技": ["人工智能", "AI", "芯片", "半导体", "5G", "云计算", "大数据", "物联网", "区块链"],
            "医药": ["药企", "疫苗", "新药", "医疗", "生物科技", "制药"],
            "新能源": ["电动车", "锂电池", "太阳能", "风电", "储能", "充电桩"],
            "消费": ["白酒", "食品", "零售", "电商", "品牌"],
            "地产": ["房地产", "物业", "建筑", "基建"],
            "金融": ["银行", "保险", "证券", "基金", "信托"],
            "汽车": ["汽车", "新能源车", "自动驾驶", "车企"],
            "军工": ["军工", "航空", "航天", "国防"],
            "有色": ["钢铁", "煤炭", "有色金属", "黄金"],
            "石化": ["石油", "化工", "天然气"]
        }
        
        # 热点事件类型
        self.event_patterns = [
            "并购", "重组", "IPO", "上市", "退市", "ST", "*ST",
            "涨停", "跌停", "停牌", "复牌", "减持", "增持",
            "分红", "送股", "配股", "回购", "解禁",
            "业绩", "财报", "预亏", "预盈", "商誉减值"
        ]

    async def discover_hot_news(self, hours_back: int = 6) -> List[Dict[str, Any]]:
        """发现热点新闻"""
        app_logger.info(f"开始智能热点发现，回溯{hours_back}小时...")
        
        all_news = []
        
        # 1. 从多个RSS源并行采集
        tasks = []
        for source_name, rss_url in self.rss_sources.items():
            task = asyncio.create_task(
                self._fetch_rss_news(source_name, rss_url, limit=30)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            source_name = list(self.rss_sources.keys())[i]
            if isinstance(result, Exception):
                app_logger.error(f"{source_name} 采集失败: {result}")
            else:
                all_news.extend(result)
        
        # 2. 分析热点
        hot_news = await self._analyze_hot_trends(all_news, hours_back)
        
        app_logger.info(f"发现 {len(hot_news)} 条热点新闻")
        return hot_news
    
    async def _fetch_rss_news(self, source_name: str, rss_url: str, limit: int = 30) -> List[Dict[str, Any]]:
        """从RSS源获取新闻"""
        try:
            app_logger.info(f"采集 {source_name}: {rss_url}")
            
            # 解析RSS
            feed = feedparser.parse(rss_url)
            
            news_items = []
            for entry in feed.entries[:limit]:
                news_item = self._parse_rss_entry(entry, source_name)
                if news_item:
                    news_items.append(news_item)
            
            app_logger.info(f"{source_name} 采集到 {len(news_items)} 条新闻")
            return news_items
            
        except Exception as e:
            app_logger.error(f"{source_name} 采集失败: {e}")
            return []
    
    def _parse_rss_entry(self, entry, source_name: str) -> Dict[str, Any]:
        """解析RSS条目"""
        try:
            title = entry.get("title", "").strip()
            description = entry.get("summary", "").strip()
            link = entry.get("link", "")
            
            # 解析时间
            published_at = datetime.now(timezone.utc)
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            
            return {
                "title": title,
                "content": description,
                "source_url": link,
                "published_at": published_at,
                "collected_at": datetime.now(timezone.utc),
                "source": f"hot_discovery_{source_name}",
                "raw_entry": entry
            }
        except Exception as e:
            app_logger.error(f"解析RSS条目失败: {e}")
            return None
    
    async def _analyze_hot_trends(self, news_list: List[Dict[str, Any]], hours_back: int) -> List[Dict[str, Any]]:
        """分析热点趋势"""
        if not news_list:
            return []
        
        # 过滤时间范围
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        recent_news = [
            news for news in news_list 
            if news.get("published_at", cutoff_time) >= cutoff_time
        ]
        
        # 热点分析
        hot_news = []
        
        # 1. 基于股票代码的热点
        stock_hot = self._find_stock_mentions(recent_news)
        hot_news.extend(stock_hot)
        
        # 2. 基于板块关键词的热点
        sector_hot = self._find_sector_trends(recent_news)
        hot_news.extend(sector_hot)
        
        # 3. 基于事件类型的热点
        event_hot = self._find_event_driven_news(recent_news)
        hot_news.extend(event_hot)
        
        # 4. 基于词频的新兴热点
        emerging_hot = self._find_emerging_trends(recent_news)
        hot_news.extend(emerging_hot)
        
        # 去重并按热度排序
        unique_hot = self._deduplicate_and_rank(hot_news)
        
        return unique_hot[:50]  # 返回前50条热点
    
    def _find_stock_mentions(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """发现股票相关热点"""
        stock_mentions = Counter()
        stock_news = {}
        
        for news in news_list:
            title = news.get("title", "")
            content = news.get("content", "")
            text = f"{title} {content}"
            
            # 查找股票代码 - 添加更严格的过滤
            for pattern in self.stock_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # 过滤掉常见的非股票代码
                    if self._is_valid_stock_code(match):
                        stock_mentions[match] += 1
                        if match not in stock_news:
                            stock_news[match] = []
                        stock_news[match].append(news)
        
        # 筛选高频股票
        hot_stocks = []
        for stock, count in stock_mentions.most_common(20):
            if count >= 2:  # 至少被提及2次
                for news in stock_news[stock]:
                    news_copy = news.copy()
                    news_copy["hot_reason"] = f"股票代码 {stock} 热度"
                    news_copy["hot_score"] = count * 10
                    news_copy["hot_keywords"] = [stock]
                    hot_stocks.append(news_copy)
        
        return hot_stocks
    
    def _is_valid_stock_code(self, code: str) -> bool:
        """验证是否为有效的股票代码"""
        # 排除常见的非股票代码
        invalid_codes = {
            "U", "V", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", 
            "N", "O", "P", "Q", "R", "S", "T", "W", "X", "Y", "Z",
            "AI", "IT", "US", "CN", "UK", "EU", "API", "CEO", "CFO", "CTO", "IPO"
        }
        
        # 单个字母不是股票代码
        if len(code) == 1:
            return False
            
        # 在排除列表中的不是股票代码
        if code.upper() in invalid_codes:
            return False
            
        # 6位数字但以0开头的可能是A股代码
        if re.match(r'^\d{6}$', code):
            return True
            
        # 2-5位字母且不在排除列表的可能是美股代码
        if re.match(r'^[A-Z]{2,5}$', code) and len(code) >= 3:
            return True
            
        return False
    
    def _find_sector_trends(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """发现板块趋势热点"""
        sector_mentions = Counter()
        sector_news = {}
        
        for news in news_list:
            title = news.get("title", "")
            content = news.get("content", "")
            text = f"{title} {content}"
            
            for sector, keywords in self.sector_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        sector_mentions[sector] += 1
                        if sector not in sector_news:
                            sector_news[sector] = []
                        sector_news[sector].append((news, keyword))
        
        # 筛选热门板块
        hot_sectors = []
        for sector, count in sector_mentions.most_common(10):
            if count >= 3:  # 板块至少被提及3次
                for news, keyword in sector_news[sector]:
                    news_copy = news.copy()
                    news_copy["hot_reason"] = f"{sector}板块热点"
                    news_copy["hot_score"] = count * 15
                    news_copy["hot_keywords"] = [sector, keyword]
                    hot_sectors.append(news_copy)
        
        return hot_sectors
    
    def _find_event_driven_news(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """发现事件驱动热点"""
        event_news = []
        
        for news in news_list:
            title = news.get("title", "")
            content = news.get("content", "")
            text = f"{title} {content}"
            
            for event_type in self.event_patterns:
                if event_type in text:
                    news_copy = news.copy()
                    news_copy["hot_reason"] = f"事件驱动: {event_type}"
                    news_copy["hot_score"] = 20
                    news_copy["hot_keywords"] = [event_type]
                    event_news.append(news_copy)
        
        return event_news
    
    def _find_emerging_trends(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """发现新兴热点（基于词频分析）"""
        # 提取所有标题词汇
        all_words = []
        for news in news_list:
            title = news.get("title", "")
            # 使用jieba分词
            words = jieba.lcut(title)
            # 过滤停用词和短词
            words = [w for w in words if len(w) >= 2 and w not in ["的", "了", "在", "是", "有", "和", "与"]]
            all_words.extend(words)
        
        # 词频统计
        word_freq = Counter(all_words)
        
        # 发现高频新词（可能是新兴热点）
        emerging_news = []
        for word, freq in word_freq.most_common(30):
            if freq >= 3:  # 至少出现3次
                # 找到包含该词的新闻
                for news in news_list:
                    if word in news.get("title", ""):
                        news_copy = news.copy()
                        news_copy["hot_reason"] = f"新兴热词: {word}"
                        news_copy["hot_score"] = freq * 5
                        news_copy["hot_keywords"] = [word]
                        emerging_news.append(news_copy)
        
        return emerging_news
    
    def _deduplicate_and_rank(self, hot_news: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重并按热度排序"""
        seen_urls = set()
        unique_news = []
        
        # 按热度分数排序
        sorted_news = sorted(hot_news, key=lambda x: x.get("hot_score", 0), reverse=True)
        
        for news in sorted_news:
            url = news.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(news)
        
        return unique_news

    async def get_trending_keywords_dynamic(self, limit: int = 20) -> List[Dict[str, Any]]:
        """动态获取趋势关键词"""
        hot_news = await self.discover_hot_news(hours_back=3)
        
        keyword_stats = Counter()
        for news in hot_news:
            keywords = news.get("hot_keywords", [])
            for keyword in keywords:
                keyword_stats[keyword] += news.get("hot_score", 1)
        
        trending = []
        for keyword, score in keyword_stats.most_common(limit):
            trending.append({
                "keyword": keyword,
                "score": score,
                "trend_type": "dynamic_discovery"
            })
        
        return trending

    async def save_to_database(self, news_items: List[Dict[str, Any]]) -> int:
        """保存热点新闻到数据库"""
        if not news_items:
            return 0
            
        try:
            db = next(get_db())
            saved_count = 0
            
            for news_data in news_items:
                try:
                    # 生成唯一ID
                    import hashlib
                    title = news_data.get("title", "")
                    url = news_data.get("source_url", "")
                    content_hash = hashlib.md5((title + url).encode()).hexdigest()
                    news_id = f"hot_news_{content_hash}"
                    
                    # 检查是否已存在
                    existing_news = db.query(NewsItem).filter(
                        NewsItem.id == news_id
                    ).first()
                    
                    if existing_news:
                        continue  # 跳过已存在的新闻
                    
                    # 准备raw_data，包含热点相关信息
                    raw_data = news_data.get("raw_data", {})
                    raw_data.update({
                        "hot_reason": news_data.get("hot_reason", ""),
                        "hot_score": news_data.get("hot_score", 0),
                        "hot_keywords": news_data.get("hot_keywords", []),
                        "source_type": "hot_discovery"
                    })
                    
                    # 创建新的新闻记录
                    news_item = NewsItem(
                        id=news_id,
                        title=news_data.get("title", ""),
                        content=news_data.get("content", ""),
                        summary=news_data.get("summary", news_data.get("title", "")[:200]),
                        source="hot_discovery",
                        source_url=news_data.get("source_url", ""),
                        published_at=news_data.get("published_at", datetime.now(timezone.utc)),
                        collected_at=datetime.now(timezone.utc),
                        language=news_data.get("language", "zh"),
                        region=news_data.get("region", "global"),
                        raw_data=raw_data,
                        analysis_status="pending"
                    )
                    
                    db.add(news_item)
                    saved_count += 1
                    
                except Exception as item_error:
                    app_logger.error(f"保存单条热点新闻失败 {news_data.get('title', 'unknown')}: {item_error}")
                    continue
            
            db.commit()
            app_logger.info(f"热点新闻保存到数据库: {saved_count} 条")
            return saved_count
            
        except Exception as e:
            app_logger.error(f"保存热点新闻到数据库失败: {e}")
            if 'db' in locals():
                db.rollback()
            return 0
        finally:
            if 'db' in locals():
                db.close()

    def _enhanced_deduplicate(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """增强的去重机制"""
        try:
            # 获取数据库中已有的新闻
            db = next(get_db())
            existing_urls = set()
            
            # 获取现有的热点新闻URL
            existing_records = db.query(NewsItem.source_url).filter(
                NewsItem.source.in_(["hot_discovery", "google_news"])
            ).all()
            existing_urls = {record.source_url for record in existing_records if record.source_url}
            
            # 过滤掉已存在的新闻
            unique_news = []
            seen_titles = set()
            
            for news in news_items:
                url = news.get("source_url", "")
                title = news.get("title", "").lower().strip()
                
                if url in existing_urls:
                    continue  # 跳过数据库中已存在的URL
                
                if title in seen_titles:
                    continue  # 跳过标题重复的
                
                seen_titles.add(title)
                unique_news.append(news)
            
            app_logger.info(f"热点新闻去重: 原始{len(news_items)}条 -> 去重后{len(unique_news)}条")
            return unique_news
            
        except Exception as e:
            app_logger.error(f"热点新闻去重失败: {e}")
            return self._deduplicate_and_rank(news_items)  # 降级到简单去重
        finally:
            if 'db' in locals():
                db.close()


# 全局实例
hot_news_discovery = HotNewsDiscoveryService()
