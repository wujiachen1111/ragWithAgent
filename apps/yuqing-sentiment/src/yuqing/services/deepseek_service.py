"""
DeepSeek v3 情感分析服务
"""
import asyncio
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import aiohttp
from dataclasses import dataclass

from yuqing.core.config import settings
from yuqing.core.logging import logger
from yuqing.core.cache import cache_manager
from yuqing.models.database_models import NewsItem, StockAnalysis
from yuqing.core.database import get_db

@dataclass
class SentimentResult:
    """情感分析结果"""
    sentiment: str  # positive, negative, neutral
    confidence: float  # 0.0-1.0
    keywords: List[str]
    summary: str
    market_impact: str  # high, medium, low
    reasoning: str

@dataclass
class EntityInfo:
    """实体信息"""
    name: str
    type: str  # company, person
    confidence: float
    impact_type: str  # direct, indirect, competitive, supply_chain
    impact_direction: str  # positive, negative, neutral
    impact_magnitude: float  # 0.0-1.0
    additional_info: Dict[str, Any]

@dataclass
class EntityAnalysisResult:
    """实体分析结果"""
    companies: List[EntityInfo]
    persons: List[EntityInfo]
    industries: List[str]
    events: List[str]

class DeepSeekService:
    """DeepSeek v3 API 服务"""
    
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model
        
        # 情感分析提示模板
        self.sentiment_prompt = """
你是一个专业的金融新闻情感分析专家。请分析以下新闻内容，并提供详细的情感分析结果。

新闻标题: {title}
新闻内容: {content}
新闻来源: {source}
发布时间: {published_at}

请从以下角度进行分析：
1. 情感倾向：正面(positive)、负面(negative)、中性(neutral)
2. 置信度：0.0-1.0，表示分析结果的可信程度
3. 关键词：提取5-10个最重要的关键词
4. 摘要：用1-2句话总结新闻要点
5. 市场影响：高(high)、中(medium)、低(low)
6. 分析推理：解释为什么得出这个情感判断

请以JSON格式返回结果：
{{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.85,
    "keywords": ["关键词1", "关键词2", ...],
    "summary": "新闻摘要",
    "market_impact": "high/medium/low",
    "reasoning": "分析推理过程"
}}
"""

        # 实体识别提示模板
        self.entity_extraction_prompt = """
你是一个专业的金融新闻实体识别专家。请从以下新闻内容中识别和分析相关实体。

新闻标题: {title}
新闻内容: {content}
新闻来源: {source}
发布时间: {published_at}

请识别以下类型的实体并进行影响分析：

1. **公司实体**:
   - 识别新闻中提到的所有公司
   - 分析每个公司受到的影响类型和程度
   - 确定影响是直接的还是间接的

2. **人物实体**:
   - 识别关键人物(CEO、高管、政府官员、分析师等)
   - 分析人物言论或行为对市场的潜在影响
   - 评估人物的市场影响力

3. **行业分析**:
   - 识别涉及的行业板块
   - 分析行业层面的影响

4. **关键事件**:
   - 识别重要的市场事件
   - 评估事件的市场意义

请以JSON格式返回结果：
{{
    "companies": [
        {{
            "name": "公司名称",
            "type": "company",
            "confidence": 0.95,
            "stock_code": "股票代码(如果提到)",
            "exchange": "交易所(如果提到)",
            "impact_type": "direct/indirect/competitive/supply_chain",
            "impact_direction": "positive/negative/neutral",
            "impact_magnitude": 0.8,
            "additional_info": {{
                "business_segment": "业务板块",
                "market_cap": "市值信息(如果提到)",
                "mentioned_context": "提及的具体上下文"
            }}
        }}
    ],
    "persons": [
        {{
            "name": "人物姓名",
            "type": "person",
            "confidence": 0.9,
            "position": "职位",
            "company": "所属公司",
            "impact_type": "direct/indirect",
            "impact_direction": "positive/negative/neutral", 
            "impact_magnitude": 0.7,
            "additional_info": {{
                "person_type": "ceo/cfo/government_official/analyst/investor",
                "influence_level": "high/medium/low",
                "mentioned_context": "提及的具体上下文"
            }}
        }}
    ],
    "industries": [
        {{
            "name": "行业名称",
            "impact_direction": "positive/negative/neutral",
            "impact_magnitude": 0.6,
            "reasoning": "影响分析说明"
        }}
    ],
    "events": [
        {{
            "type": "merger/ipo/earnings/regulatory/leadership_change",
            "title": "事件标题",
            "description": "事件描述",
            "market_significance": "major/moderate/minor",
            "expected_volatility": "high/medium/low"
        }}
    ]
}}
"""

        # 批量分析提示模板
        self.batch_prompt = """
你是一个专业的金融新闻情感分析专家。请对以下新闻列表进行批量情感分析。

新闻列表:
{news_list}

请为每条新闻提供详细的情感分析结果，返回JSON数组格式：
[
    {{
        "id": "新闻ID",
        "sentiment": "positive/negative/neutral",
        "confidence": 0.85,
        "keywords": ["关键词1", "关键词2", ...],
        "summary": "新闻摘要",
        "market_impact": "high/medium/low",
        "reasoning": "分析推理过程"
    }},
    ...
]
"""

    async def _make_api_request(self, messages: List[Dict[str, str]], 
                              max_retries: int = 3) -> Dict[str, Any]:
        """发送API请求到DeepSeek"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # 较低温度保证一致性
            "max_tokens": 2048,
            "stream": False
        }
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)  # 增加到60秒
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result
                        else:
                            error_text = await response.text()
                            logger.error(f"DeepSeek API错误 {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"DeepSeek API超时，重试 {attempt + 1}/{max_retries}")
            except Exception as e:
                logger.error(f"DeepSeek API请求失败: {e}")
                
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
                
        raise Exception("DeepSeek API请求失败，已达最大重试次数")

    def _generate_cache_key(self, content: str) -> str:
        """生成缓存键"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"sentiment:{content_hash}"

    async def analyze_single_news(self, news_item: NewsItem) -> Optional[SentimentResult]:
        """分析单条新闻的情感"""
        try:
            # 检查缓存
            cache_key = self._generate_cache_key(news_item.content or "")
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"使用缓存的情感分析结果: {news_item.id}")
                return SentimentResult(**json.loads(cached_result))
            
            # 准备提示
            prompt = self.sentiment_prompt.format(
                title=news_item.title or "",
                content=news_item.content or "",
                source=news_item.source or "",
                published_at=news_item.published_at or ""
            )
            
            messages = [
                {"role": "system", "content": "你是一个专业的金融新闻情感分析专家。"},
                {"role": "user", "content": prompt}
            ]
            
            # 调用API
            logger.info(f"开始分析新闻情感: {news_item.id}")
            response = await self._make_api_request(messages)
            
            # 解析响应
            content = response["choices"][0]["message"]["content"]
            
            # 尝试解析JSON
            try:
                # 提取JSON部分（可能包含其他文本）
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx]
                    result_data = json.loads(json_content)
                    
                    result = SentimentResult(**result_data)
                    
                    # 缓存结果（24小时）
                    await cache_manager.set(
                        cache_key, 
                        json.dumps(result_data), 
                        expire=86400
                    )
                    
                    logger.info(f"情感分析完成: {news_item.id} -> {result.sentiment}")
                    return result
                    
            except json.JSONDecodeError as e:
                logger.error(f"解析DeepSeek响应JSON失败: {e}, 响应内容: {content}")
                
        except Exception as e:
            logger.error(f"分析新闻情感失败 {news_item.id}: {e}")
            
        return None

    async def analyze_batch_news(self, news_items: List[NewsItem], 
                               batch_size: int = 10) -> Dict[str, SentimentResult]:
        """批量分析新闻情感 - 优化版本"""
        results = {}
        total_items = len(news_items)
        logger.info(f"开始批量分析 {total_items} 条新闻，批量大小: {batch_size}")
        
        # 分批处理，提高效率
        for i in range(0, len(news_items), batch_size):
            batch = news_items[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_items + batch_size - 1) // batch_size
            
            logger.info(f"处理第 {batch_num}/{total_batches} 批，包含 {len(batch)} 条新闻")
            
            # 检查缓存
            uncached_items = []
            for item in batch:
                cache_key = self._generate_cache_key(item.content or "")
                cached_result = await cache_manager.get(cache_key)
                if cached_result:
                    results[item.id] = SentimentResult(**json.loads(cached_result))
                    logger.debug(f"使用缓存结果: {item.id}")
                else:
                    uncached_items.append(item)
            
            if not uncached_items:
                logger.info(f"第 {batch_num} 批全部命中缓存，跳过")
                continue
                
            logger.info(f"第 {batch_num} 批需要分析 {len(uncached_items)} 条新闻")
            
            # 准备批量提示
            news_list = ""
            for idx, item in enumerate(uncached_items):
                news_list += f"""
{idx + 1}. ID: {item.id}
   标题: {item.title or ""}
   内容: {item.content or ""}
   来源: {item.source or ""}
   时间: {item.published_at or ""}
"""
            
            prompt = self.batch_prompt.format(news_list=news_list)
            
            messages = [
                {"role": "system", "content": "你是一个专业的金融新闻情感分析专家。"},
                {"role": "user", "content": prompt}
            ]
            
            try:
                # 调用API
                logger.info(f"批量分析 {len(uncached_items)} 条新闻")
                response = await self._make_api_request(messages)
                content = response["choices"][0]["message"]["content"]
                
                # 解析JSON数组
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx]
                    batch_results = json.loads(json_content)
                    
                    for result_data in batch_results:
                        news_id = result_data.get("news_id")
                        if news_id and news_id in [item.id for item in uncached_items]:
                            # 移除news_id字段
                            sentiment_data = {k: v for k, v in result_data.items() if k != "news_id"}
                            result = SentimentResult(**sentiment_data)
                            results[news_id] = result
                            
                            # 缓存结果
                            cache_key = self._generate_cache_key(
                                next(item.content for item in uncached_items if item.id == news_id) or ""
                            )
                            await cache_manager.set(
                                cache_key,
                                json.dumps(sentiment_data),
                                expire=86400
                            )
                            
                            logger.info(f"批量分析完成: {news_id} -> {result.sentiment}")
                            
            except Exception as e:
                logger.error(f"批量分析失败: {e}")
                # 降级到单条分析
                for item in uncached_items:
                    single_result = await self.analyze_single_news(item)
                    if single_result:
                        results[item.id] = single_result
            
            # 减少API限流延迟（从1秒改为0.5秒）
            await asyncio.sleep(0.5)
        
        logger.info(f"批量分析完成，共处理 {len(results)} 条新闻")
        return results
        
    async def extract_entities(self, news_item: NewsItem) -> Optional[EntityAnalysisResult]:
        """从新闻中提取实体信息"""
        try:
            # 检查缓存
            cache_key = f"entity:{self._generate_cache_key(news_item.content or '')}"
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"使用缓存的实体分析结果: {news_item.id}")
                data = json.loads(cached_result)
                return self._parse_entity_result(data)
            
            # 准备提示
            prompt = self.entity_extraction_prompt.format(
                title=news_item.title or "",
                content=news_item.content or "",
                source=news_item.source or "",
                published_at=news_item.published_at or ""
            )
            
            messages = [
                {"role": "system", "content": "你是一个专业的金融新闻实体识别和影响分析专家。"},
                {"role": "user", "content": prompt}
            ]
            
            # 调用API
            logger.info(f"开始实体识别: {news_item.id}")
            response = await self._make_api_request(messages)
            
            # 解析响应
            content = response["choices"][0]["message"]["content"]
            
            try:
                # 提取JSON部分
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx]
                    result_data = json.loads(json_content)
                    
                    # 缓存结果（24小时）
                    await cache_manager.set(
                        cache_key, 
                        json.dumps(result_data), 
                        expire=86400
                    )
                    
                    result = self._parse_entity_result(result_data)
                    logger.info(f"实体识别完成: {news_item.id} -> 发现 {len(result.companies)} 个公司，{len(result.persons)} 个人物")
                    return result
                    
            except json.JSONDecodeError as e:
                logger.error(f"解析实体识别响应JSON失败: {e}, 响应内容: {content}")
                
        except Exception as e:
            logger.error(f"实体识别失败 {news_item.id}: {e}")
            
        return None

    def _parse_entity_result(self, data: Dict[str, Any]) -> EntityAnalysisResult:
        """解析实体识别结果"""
        companies = []
        for company_data in data.get("companies", []):
            companies.append(EntityInfo(
                name=company_data.get("name", ""),
                type="company",
                confidence=company_data.get("confidence", 0.0),
                impact_type=company_data.get("impact_type", "direct"),
                impact_direction=company_data.get("impact_direction", "neutral"),
                impact_magnitude=company_data.get("impact_magnitude", 0.0),
                additional_info=company_data.get("additional_info", {})
            ))
        
        persons = []
        for person_data in data.get("persons", []):
            persons.append(EntityInfo(
                name=person_data.get("name", ""),
                type="person",
                confidence=person_data.get("confidence", 0.0),
                impact_type=person_data.get("impact_type", "direct"),
                impact_direction=person_data.get("impact_direction", "neutral"),
                impact_magnitude=person_data.get("impact_magnitude", 0.0),
                additional_info=person_data.get("additional_info", {})
            ))
        
        return EntityAnalysisResult(
            companies=companies,
            persons=persons,
            industries=data.get("industries", []),
            events=data.get("events", [])
        )
        """保存分析结果到数据库"""
        saved_count = 0
        
        db = next(get_db())
        try:
            for news_item in news_items:
                if news_item.id not in results:
                    continue
                    
                result = results[news_item.id]
                
                # 创建或更新股票分析记录
                analysis = StockAnalysis(
                    news_id=news_item.id,
                    sentiment_label=result.sentiment,
                    confidence_score=result.confidence,
                    market_impact_level=result.market_impact,
                    analysis_result={
                        "keywords": result.keywords,
                        "summary": result.summary,
                        "reasoning": result.reasoning,
                        "sentiment": result.sentiment,
                        "confidence": result.confidence,
                        "market_impact": result.market_impact
                    },
                    analysis_timestamp=datetime.now(timezone.utc)
                )
                
                # 检查是否已存在 (通过news_id查找)
                from sqlalchemy import select
                existing_query = select(StockAnalysis).where(StockAnalysis.news_id == news_item.id)
                existing_result = db.execute(existing_query)
                existing = existing_result.scalar_one_or_none()
                
                if existing:
                    # 更新现有记录
                    existing.sentiment_label = result.sentiment
                    existing.confidence_score = result.confidence
                    existing.market_impact_level = result.market_impact
                    existing.analysis_result = analysis.analysis_result
                    existing.analysis_timestamp = datetime.now(timezone.utc)
                    logger.info(f"更新分析结果: {existing.id}")
                else:
                    # 创建新记录
                    db.add(analysis)
                    logger.info(f"创建分析结果: news_id={news_item.id}")
                
                saved_count += 1
            
            db.commit()
            logger.info(f"成功保存 {saved_count} 条分析结果")
            
        except Exception as e:
            db.rollback()
            logger.error(f"保存分析结果失败: {e}")
            raise
        finally:
            db.close()
        return saved_count
    
    async def save_analysis_results(self, news_items: List[NewsItem], 
                                  analysis_results: Dict[str, SentimentResult]) -> int:
        """保存分析结果到数据库"""
        saved_count = 0
        
        db = next(get_db())
        try:
            from sqlalchemy import select
            
            for news_item in news_items:
                if news_item.id not in analysis_results:
                    continue
                    
                sentiment_result = analysis_results[news_item.id]
                
                # 检查是否已存在分析记录
                existing_query = select(StockAnalysis).where(StockAnalysis.news_id == news_item.id)
                existing_result = db.execute(existing_query)
                stock_analysis = existing_result.scalar_one_or_none()
                
                if not stock_analysis:
                    # 创建新的股票分析记录
                    stock_analysis = StockAnalysis(
                        news_id=news_item.id,
                        analysis_timestamp=datetime.now(timezone.utc),
                        sentiment_score=self._convert_sentiment_to_score(sentiment_result.sentiment),
                        sentiment_label=sentiment_result.sentiment,
                        confidence_score=sentiment_result.confidence,
                        market_impact_level=sentiment_result.market_impact,
                        market_impact_score=self._convert_impact_to_score(sentiment_result.market_impact),
                        urgency_level='normal',  # 默认值
                        analysis_result={
                            'summary': sentiment_result.summary,
                            'keywords': sentiment_result.keywords,
                            'reasoning': sentiment_result.reasoning
                        }
                    )
                    db.add(stock_analysis)
                    saved_count += 1
                else:
                    # 更新现有记录
                    stock_analysis.sentiment_score = self._convert_sentiment_to_score(sentiment_result.sentiment)
                    stock_analysis.sentiment_label = sentiment_result.sentiment
                    stock_analysis.confidence_score = sentiment_result.confidence
                    stock_analysis.market_impact_level = sentiment_result.market_impact
                    stock_analysis.market_impact_score = self._convert_impact_to_score(sentiment_result.market_impact)
                    stock_analysis.analysis_result = {
                        'summary': sentiment_result.summary,
                        'keywords': sentiment_result.keywords,
                        'reasoning': sentiment_result.reasoning
                    }
                    saved_count += 1
                
                # 更新新闻项的分析状态
                news_item.analysis_status = 'completed'
            
            db.commit()
            logger.info(f"成功保存 {saved_count} 条分析结果")
            return saved_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"保存分析结果失败: {e}")
            return 0
        finally:
            db.close()
    
    def _convert_sentiment_to_score(self, sentiment: str) -> float:
        """将情感标签转换为数值分数"""
        sentiment_map = {
            'positive': 0.8,
            'negative': -0.8,
            'neutral': 0.0
        }
        return sentiment_map.get(sentiment, 0.0)
    
    def _convert_impact_to_score(self, impact: str) -> float:
        """将影响等级转换为数值分数"""
        impact_map = {
            'high': 0.9,
            'medium': 0.6,
            'low': 0.3
        }
        return impact_map.get(impact, 0.3)

    async def save_entity_analysis_results(self, news_item: NewsItem, 
                                         entity_result: EntityAnalysisResult) -> int:
        """保存实体分析结果到数据库"""
        saved_count = 0
        
        try:
            db = next(get_db())
            from sqlalchemy import select
            
            # 获取或创建股票分析记录
            existing_query = select(StockAnalysis).where(StockAnalysis.news_id == news_item.id)
            existing_result = db.execute(existing_query)
            stock_analysis = existing_result.scalar_one_or_none()
            
            if not stock_analysis:
                # 创建新的股票分析记录
                stock_analysis = StockAnalysis(
                    news_id=news_item.id,
                    analysis_timestamp=datetime.now(timezone.utc),
                    analysis_result={}
                )
                db.add(stock_analysis)
                db.flush()  # 获取ID
            
            # 保存公司实体
            for company in entity_result.companies:
                from yuqing.models.database_models import MentionedCompany
                
                mentioned_company = MentionedCompany(
                    analysis_id=stock_analysis.id,
                    company_name=company.name,
                    stock_code=company.additional_info.get("stock_code"),
                    exchange=company.additional_info.get("exchange"),
                    impact_type=company.impact_type,
                    impact_direction=company.impact_direction,
                    impact_magnitude=company.impact_magnitude,
                    confidence_level=company.confidence,
                    business_segment=company.additional_info.get("business_segment"),
                    geographic_exposure=company.additional_info.get("geographic_exposure")
                )
                db.add(mentioned_company)
                saved_count += 1
            
            # 保存人物实体
            for person in entity_result.persons:
                from yuqing.models.database_models import MentionedPerson
                
                mentioned_person = MentionedPerson(
                    analysis_id=stock_analysis.id,
                    person_name=person.name,
                    position_title=person.additional_info.get("position"),
                    company_affiliation=person.additional_info.get("company"),
                    influence_level=person.additional_info.get("influence_level", "medium"),
                    person_type=person.additional_info.get("person_type"),
                    market_influence_score=person.impact_magnitude,
                    related_companies=json.dumps([person.additional_info.get("company")] if person.additional_info.get("company") else [])
                )
                db.add(mentioned_person)
                saved_count += 1
            
            # 保存行业影响
            for industry in entity_result.industries:
                from yuqing.models.database_models import IndustryImpact
                
                industry_impact = IndustryImpact(
                    analysis_id=stock_analysis.id,
                    industry_name=industry.get("name", ""),
                    impact_direction=industry.get("impact_direction", "neutral"),
                    impact_magnitude=industry.get("impact_magnitude", 0.0),
                    confidence_level=0.8,  # 默认置信度
                    immediate_impact=True,
                    impact_type="market_trend"
                )
                db.add(industry_impact)
                saved_count += 1
            
            # 保存关键事件
            for event in entity_result.events:
                from yuqing.models.database_models import KeyEvent
                
                key_event = KeyEvent(
                    analysis_id=stock_analysis.id,
                    event_type=event.get("type", "other"),
                    event_title=event.get("title", ""),
                    event_description=event.get("description", ""),
                    market_significance=event.get("market_significance", "moderate"),
                    expected_volatility=event.get("expected_volatility", "medium"),
                    event_category="market_event"
                )
                db.add(key_event)
                saved_count += 1
            
            db.commit()
            logger.info(f"成功保存 {saved_count} 条实体分析结果")
            
        except Exception as e:
            if 'db' in locals():
                db.rollback()
            logger.error(f"保存实体分析结果失败: {e}")
            raise
        finally:
            if 'db' in locals():
                db.close()
        
        return saved_count

    def sync_analyze_news(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 将字典数据转换为NewsItem对象进行分析
            from yuqing.models.database_models import NewsItem
            
            # 创建临时NewsItem对象
            news_item = NewsItem(
                id=news_data.get("id", ""),
                title=news_data.get("title", ""),
                content=news_data.get("content", ""),
                source=news_data.get("source", ""),
                published_at=news_data.get("published_at"),
                language=news_data.get("language", "zh"),
                region=news_data.get("region", "global")
            )
            
            # 使用同步方式调用异步分析方法
            import asyncio
            try:
                # 检查当前是否在事件循环中
                loop = asyncio.get_running_loop()
                # 如果在事件循环中，使用线程池执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.analyze_single_news(news_item)
                    )
                    result = future.result(timeout=30)
            except RuntimeError:
                # 如果没有运行的事件循环，直接运行
                result = asyncio.run(self.analyze_single_news(news_item))
            
            if result:
                # 保存分析结果到数据库
                analysis_data = {
                    "sentiment_label": result.sentiment,
                    "confidence_score": result.confidence,
                    "market_impact_level": result.market_impact,
                    "analysis_result": {
                        "keywords": result.keywords,
                        "summary": result.summary,
                        "reasoning": result.reasoning,
                        "sentiment": result.sentiment,
                        "confidence": result.confidence,
                        "market_impact": result.market_impact
                    }
                }
                
                # 保存到数据库
                from yuqing.core.database import get_db
                from sqlalchemy import select
                
                db = next(get_db())
                try:
                    # 检查是否已存在分析记录
                    existing_query = select(StockAnalysis).where(StockAnalysis.news_id == news_data["id"])
                    existing_result = db.execute(existing_query)
                    existing = existing_result.scalar_one_or_none()
                    
                    if existing:
                        # 更新现有记录
                        existing.sentiment_label = result.sentiment
                        existing.confidence_score = result.confidence
                        existing.market_impact_level = result.market_impact
                        existing.analysis_result = analysis_data["analysis_result"]
                        existing.analysis_timestamp = datetime.now(timezone.utc)
                        logger.info(f"更新分析结果: {existing.id}")
                    else:
                        # 创建新记录
                        analysis = StockAnalysis(
                            news_id=news_data["id"],
                            sentiment_label=result.sentiment,
                            confidence_score=result.confidence,
                            market_impact_level=result.market_impact,
                            analysis_result=analysis_data["analysis_result"],
                            analysis_timestamp=datetime.now(timezone.utc)
                        )
                        db.add(analysis)
                        logger.info(f"创建分析结果: news_id={news_data['id']}")
                    
                    db.commit()
                    logger.info(f"分析完成并保存: {news_data['id']} -> {result.sentiment}")
                    
                except Exception as e:
                    db.rollback()
                    logger.error(f"保存分析结果失败: {e}")
                    raise
                finally:
                    db.close()
                
                return analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"分析新闻条目失败: {e}")
            return None

    async def analyze_recent_news(self, hours: int = 24, limit: int = 50) -> Dict[str, Any]:
        """分析最近的新闻"""
        from sqlalchemy import select, desc
        from datetime import timedelta
        
        db = next(get_db())
        try:
            # 获取最近的新闻
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = select(NewsItem).where(
                NewsItem.collected_at >= cutoff_time
            ).order_by(desc(NewsItem.collected_at)).limit(limit)
            
            result = db.execute(query)
            news_items = result.scalars().all()
            
            if not news_items:
                logger.info("没有找到最近的新闻数据")
                return {"analyzed_count": 0, "results": {}}
            
            logger.info(f"开始分析最近 {len(news_items)} 条新闻")
            
            # 批量情感分析
            analysis_results = await self.analyze_batch_news(news_items)
            
            # 保存结果
            saved_count = await self.save_analysis_results(news_items, analysis_results)
            
            # 统计结果
            sentiment_stats = {"positive": 0, "negative": 0, "neutral": 0}
            impact_stats = {"high": 0, "medium": 0, "low": 0}
            
            for result in analysis_results.values():
                sentiment_stats[result.sentiment] = sentiment_stats.get(result.sentiment, 0) + 1
                impact_stats[result.market_impact] = impact_stats.get(result.market_impact, 0) + 1
            
            return {
                "analyzed_count": len(analysis_results),
                "saved_count": saved_count,
                "sentiment_distribution": sentiment_stats,
                "impact_distribution": impact_stats,
                "results": analysis_results
            }
        finally:
            db.close()

# 全局实例
deepseek_service = DeepSeekService()
