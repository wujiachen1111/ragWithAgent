from typing import List, Dict, Any, Optional
import numpy as np
from yuqing.core.config import settings
from yuqing.core.logging import app_logger

# 可选依赖：chromadb（懒导入失败不致命）
try:
    import chromadb  # type: ignore
    from chromadb.config import Settings as ChromaSettings  # type: ignore
    _CHROMA_AVAILABLE = True
except Exception:
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore
    _CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    app_logger.warning("sentence_transformers不可用，向量化功能将被禁用")
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class ChromaClient:
    """Chroma向量数据库客户端"""
    
    def __init__(self):
        # 初始化Chroma客户端
        try:
            if not _CHROMA_AVAILABLE:
                raise ImportError("chromadb not installed")

            # 使用配置文件中的路径
            # 禁用 Chroma 遥测，避免本地开发时不必要的网络与警告
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            
            # 初始化embedding模型（完全懒导入，避免在无依赖环境崩溃）
            self.embedding_model = None
            self.use_simple_embedding = True
            try:
                # 在需要时再导入，若失败则保持简化模式
                from sentence_transformers import SentenceTransformer  # type: ignore
                import os

                local_model_path = './models/all-MiniLM-L6-v2'
                if os.path.exists(local_model_path):
                    self.embedding_model = SentenceTransformer(local_model_path)
                    self.use_simple_embedding = False
                    app_logger.info("使用本地Sentence Transformers模型")
                else:
                    app_logger.warning("本地模型不存在，使用简化的文本向量化")
            except Exception as e:
                app_logger.info(f"未启用Sentence Transformers，降级为简化向量化: {e}")
            
            # 创建集合
            if self.client:
                self.news_collection = self._get_or_create_collection(
                    "news_embeddings",
                    "新闻内容向量存储"
                )
                
                self.analysis_collection = self._get_or_create_collection(
                    "analysis_embeddings", 
                    "分析结果向量存储"
                )
            else:
                self.news_collection = None
                self.analysis_collection = None
                
        except Exception as e:
            app_logger.error(f"ChromaClient初始化失败: {e}")
            self.client = None
            self.embedding_model = None
            self.news_collection = None
            self.analysis_collection = None
            # 在向量数据库不可用时，设置降级模式
            self.degraded_mode = True
            app_logger.info("向量数据库将以降级模式运行")
    
    def _get_or_create_collection(self, name: str, description: str):
        """获取或创建集合"""
        try:
            # 尝试获取或创建集合，新版本API推荐使用此方法
            collection = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"} # L2, cosine, ip
            )
            app_logger.info(f"成功获取或创建集合: {name}")
            return collection
        except Exception as e:
            # 捕获所有异常并记录
            app_logger.error(f"获取或创建集合失败 {name}: {e}")
            # 如果是数据库结构问题，可以尝试更复杂的恢复逻辑，但目前先返回None
            if "no such column" in str(e):
                app_logger.error("检测到数据库结构损坏。请考虑手动删除ChromaDB持久化目录并重启。")
            return None
    
    def _simple_embedding(self, text: str) -> List[float]:
        """简化的文本向量化方法（当Sentence Transformers不可用时）"""
        import hashlib
        import struct
        
        # 使用字符频率和位置信息生成简单向量
        vector = [0.0] * 384  # 使用384维向量
        
        # 基于字符频率
        char_freq = {}
        for i, char in enumerate(text[:1000]):  # 限制长度
            char_freq[char] = char_freq.get(char, 0) + 1
            
        # 将字符频率映射到向量维度
        for char, freq in char_freq.items():
            hash_val = int(hashlib.md5(char.encode()).hexdigest()[:8], 16)
            idx = hash_val % 384
            vector[idx] = freq / len(text)
            
        # 归一化
        norm = sum(x*x for x in vector) ** 0.5
        if norm > 0:
            vector = [x/norm for x in vector]
            
        return vector

    def add_news_embedding(self, news_id: str, title: str, content: str, metadata: Dict[str, Any]):
        """添加新闻向量"""
        if not self.news_collection:
            app_logger.warning("新闻集合不可用，跳过向量存储")
            return False
            
        try:
            # 生成文本embedding
            text = f"{title} {content}"
            
            if self.embedding_model and not getattr(self, 'use_simple_embedding', False):
                embedding = self.embedding_model.encode(text).tolist()
            else:
                # 使用简化向量化方法
                embedding = self._simple_embedding(text)
                app_logger.debug("使用简化向量化方法")
            
            # 添加到集合
            self.news_collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "news_id": news_id,
                    "title": title,
                    "source": metadata.get("source", ""),
                    "published_at": metadata.get("published_at", ""),
                    **metadata
                }],
                ids=[news_id]
            )
            
            app_logger.debug(f"添加新闻向量: {news_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"添加新闻向量失败: {e}")
            return False
    
    def search_similar_news(self, query_text: str, n_results: int = 10, 
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似新闻"""
        try:
            # 生成查询向量
            query_embedding = self.embedding_model.encode(query_text).tolist()
            
            # 执行向量搜索
            results = self.news_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filters,
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化返回结果
            similar_news = []
            for i in range(len(results["ids"][0])):
                similar_news.append({
                    "news_id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity_score": 1 - results["distances"][0][i],  # 转换为相似度分数
                })
            
            return similar_news
            
        except Exception as e:
            app_logger.error(f"相似新闻搜索失败: {e}")
            return []
    
    def add_analysis_embedding(self, analysis_id: str, analysis_text: str, metadata: Dict[str, Any]):
        """添加分析结果向量"""
        try:
            embedding = self.embedding_model.encode(analysis_text).tolist()
            
            self.analysis_collection.add(
                embeddings=[embedding],
                documents=[analysis_text],
                metadatas=[{
                    "analysis_id": analysis_id,
                    **metadata
                }],
                ids=[analysis_id]
            )
            
            app_logger.debug(f"添加分析向量: {analysis_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"添加分析向量失败: {e}")
            return False
    
    def search_similar_analysis(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """搜索相似分析结果"""
        try:
            query_embedding = self.embedding_model.encode(query_text).tolist()
            
            results = self.analysis_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            similar_analysis = []
            for i in range(len(results["ids"][0])):
                similar_analysis.append({
                    "analysis_id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity_score": 1 - results["distances"][0][i],
                })
            
            return similar_analysis
            
        except Exception as e:
            app_logger.error(f"相似分析搜索失败: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            news_count = self.news_collection.count()
            analysis_count = self.analysis_collection.count()
            
            return {
                "news_embeddings_count": news_count,
                "analysis_embeddings_count": analysis_count,
                "total_embeddings": news_count + analysis_count,
                "status": "healthy"
            }
        except Exception as e:
            app_logger.error(f"获取统计信息失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_similarity_threshold(self, text1: str, text2: str) -> float:
        """检查两个文本的相似度"""
        try:
            embedding1 = self.embedding_model.encode(text1)
            embedding2 = self.embedding_model.encode(text2)
            
            # 计算余弦相似度
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            return float(similarity)
            
        except Exception as e:
            app_logger.error(f"相似度计算失败: {e}")
            return 0.0
    
    def delete_news_embedding(self, news_id: str) -> bool:
        """删除新闻向量"""
        try:
            self.news_collection.delete(ids=[news_id])
            app_logger.debug(f"删除新闻向量: {news_id}")
            return True
        except Exception as e:
            app_logger.error(f"删除新闻向量失败: {e}")
            return False
    
    def reset_collections(self) -> bool:
        """重置所有集合（慎用）"""
        try:
            self.client.reset()
            app_logger.warning("已重置所有Chroma集合")
            return True
        except Exception as e:
            app_logger.error(f"重置集合失败: {e}")
            return False


# 全局Chroma客户端实例（延迟初始化，避免在导入时触发重依赖）
_chroma_client: Optional[ChromaClient] = None


def get_chroma_client() -> ChromaClient:
    """获取Chroma客户端实例（懒加载）。"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaClient()
    return _chroma_client


def check_chroma_connection() -> bool:
    """检查Chroma连接状态（若不可用则温和失败）。"""
    try:
        client = get_chroma_client()
        if client and getattr(client, "client", None):
            client.client.heartbeat()
            return True
        return False
    except Exception as e:
        app_logger.error(f"Chroma连接检查失败: {e}")
        return False
