from typing import List, Dict, Any, Optional
from yuqing.core.vector_store import get_chroma_client
from yuqing.core.logging import app_logger


class SemanticSearchService:
    """语义检索服务"""
    
    def __init__(self):
        self.chroma_client = get_chroma_client()
    
    async def add_news_to_vector_store(self, news_data: Dict[str, Any]) -> bool:
        """将新闻添加到向量存储"""
        try:
            return self.chroma_client.add_news_embedding(
                news_id=str(news_data["id"]),
                title=news_data["title"],
                content=news_data["content"],
                metadata={
                    "source": news_data.get("source", ""),
                    "published_at": str(news_data.get("published_at", "")),
                    "language": news_data.get("language", "zh"),
                    "region": news_data.get("region", "")
                }
            )
        except Exception as e:
            app_logger.error(f"添加新闻到向量存储失败: {e}")
            return False
    
    async def find_similar_news(self, query: str, limit: int = 10, 
                               source_filter: Optional[str] = None,
                               similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """查找相似新闻"""
        try:
            # 构建过滤条件
            filters = {}
            if source_filter:
                filters["source"] = source_filter
            
            # 执行语义搜索
            results = self.chroma_client.search_similar_news(
                query_text=query,
                n_results=limit,
                filters=filters if filters else None
            )
            
            # 过滤低相似度结果
            filtered_results = [
                result for result in results 
                if result["similarity_score"] >= similarity_threshold
            ]
            
            return filtered_results
            
        except Exception as e:
            app_logger.error(f"相似新闻搜索失败: {e}")
            return []
    
    async def detect_duplicate_news(self, title: str, content: str, 
                                   threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """检测重复新闻"""
        try:
            # 搜索相似新闻
            similar_news = await self.find_similar_news(
                query=f"{title} {content}",
                limit=5,
                similarity_threshold=threshold
            )
            
            # 如果找到高度相似的新闻，返回第一个
            if similar_news:
                return similar_news[0]
            
            return None
            
        except Exception as e:
            app_logger.error(f"重复新闻检测失败: {e}")
            return None
    
    async def get_trending_topics(self, days: int = 7, 
                                 min_news_count: int = 5) -> List[Dict[str, Any]]:
        """获取热门主题（基于聚类分析）"""
        try:
            # TODO: 实现基于向量聚类的热门主题发现
            # 这需要更复杂的算法，如K-means聚类
            app_logger.info("热门主题分析功能开发中...")
            return []
            
        except Exception as e:
            app_logger.error(f"热门主题分析失败: {e}")
            return []
    
    async def recommend_related_news(self, news_id: str, 
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """基于指定新闻推荐相关内容"""
        try:
            # 首先获取指定新闻的内容
            # TODO: 从数据库获取新闻内容
            
            # 暂时使用模拟数据
            app_logger.info(f"为新闻 {news_id} 推荐相关内容...")
            return []
            
        except Exception as e:
            app_logger.error(f"相关新闻推荐失败: {e}")
            return []
    
    async def analyze_content_similarity(self, text1: str, text2: str) -> float:
        """分析两个文本的相似度"""
        try:
            return self.chroma_client.check_similarity_threshold(text1, text2)
        except Exception as e:
            app_logger.error(f"相似度分析失败: {e}")
            return 0.0
    
    async def get_vector_store_stats(self) -> Dict[str, Any]:
        """获取向量存储统计信息"""
        try:
            return self.chroma_client.get_collection_stats()
        except Exception as e:
            app_logger.error(f"获取向量存储统计失败: {e}")
            return {"status": "error", "error": str(e)}


# 全局语义检索服务实例
semantic_search_service = SemanticSearchService()
