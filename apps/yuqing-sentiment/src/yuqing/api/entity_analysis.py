"""
实体分析相关API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from yuqing.core.database import get_db
from yuqing.core.logging import app_logger as logger
from yuqing.models.database_models import (
    NewsItem, StockAnalysis, MentionedCompany, 
    MentionedPerson, IndustryImpact, KeyEvent
)
from yuqing.services.deepseek_service import deepseek_service

router = APIRouter(prefix="/analysis", tags=["实体分析"])

@router.get("/companies", summary="获取公司实体分析结果")
async def get_company_analysis(
    limit: int = Query(50, description="返回结果数量限制"),
    offset: int = Query(0, description="结果偏移量"),
    company_name: Optional[str] = Query(None, description="公司名称过滤"),
    impact_direction: Optional[str] = Query(None, description="影响方向: positive/negative/neutral"),
    min_impact: float = Query(0.0, description="最小影响程度"),
    days: int = Query(7, description="时间范围(天)"),
    db: Session = Depends(get_db)
):
    """获取公司实体分析结果"""
    try:
        # 构建查询条件
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(
            MentionedCompany,
            NewsItem.title,
            NewsItem.published_at,
            NewsItem.source
        ).join(
            StockAnalysis, MentionedCompany.analysis_id == StockAnalysis.id
        ).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        ).where(
            NewsItem.collected_at >= cutoff_time
        )
        
        # 添加过滤条件
        if company_name:
            query = query.where(MentionedCompany.company_name.ilike(f"%{company_name}%"))
        
        if impact_direction:
            query = query.where(MentionedCompany.impact_direction == impact_direction)
        
        query = query.where(MentionedCompany.impact_magnitude >= min_impact)
        
        # 排序和分页
        query = query.order_by(desc(NewsItem.published_at)).offset(offset).limit(limit)
        
        result = db.execute(query)
        companies = result.fetchall()
        
        # 格式化结果
        company_analysis = []
        for company, title, published_at, source in companies:
            company_analysis.append({
                "company_name": company.company_name,
                "stock_code": company.stock_code,
                "exchange": company.exchange,
                "impact_type": company.impact_type,
                "impact_direction": company.impact_direction,
                "impact_magnitude": company.impact_magnitude,
                "confidence_level": company.confidence_level,
                "business_segment": company.business_segment,
                "news_title": title,
                "published_at": published_at,
                "source": source
            })
        
        return {
            "success": True,
            "data": company_analysis,
            "total": len(company_analysis),
            "query_params": {
                "limit": limit,
                "offset": offset,
                "company_name": company_name,
                "impact_direction": impact_direction,
                "min_impact": min_impact,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"获取公司分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取公司分析结果失败: {str(e)}")

@router.get("/persons", summary="获取人物实体分析结果")
async def get_person_analysis(
    limit: int = Query(50, description="返回结果数量限制"),
    offset: int = Query(0, description="结果偏移量"),
    person_name: Optional[str] = Query(None, description="人物姓名过滤"),
    influence_level: Optional[str] = Query(None, description="影响力级别: high/medium/low"),
    min_influence: float = Query(0.0, description="最小影响分数"),
    days: int = Query(7, description="时间范围(天)"),
    db: Session = Depends(get_db)
):
    """获取人物实体分析结果"""
    try:
        # 构建查询条件
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(
            MentionedPerson,
            NewsItem.title,
            NewsItem.published_at,
            NewsItem.source
        ).join(
            StockAnalysis, MentionedPerson.analysis_id == StockAnalysis.id
        ).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        ).where(
            NewsItem.collected_at >= cutoff_time
        )
        
        # 添加过滤条件
        if person_name:
            query = query.where(MentionedPerson.person_name.ilike(f"%{person_name}%"))
        
        if influence_level:
            query = query.where(MentionedPerson.influence_level == influence_level)
        
        query = query.where(MentionedPerson.market_influence_score >= min_influence)
        
        # 排序和分页
        query = query.order_by(desc(NewsItem.published_at)).offset(offset).limit(limit)
        
        result = db.execute(query)
        persons = result.fetchall()
        
        # 格式化结果
        person_analysis = []
        for person, title, published_at, source in persons:
            person_analysis.append({
                "person_name": person.person_name,
                "position_title": person.position_title,
                "company_affiliation": person.company_affiliation,
                "influence_level": person.influence_level,
                "person_type": person.person_type,
                "market_influence_score": person.market_influence_score,
                "news_title": title,
                "published_at": published_at,
                "source": source
            })
        
        return {
            "success": True,
            "data": person_analysis,
            "total": len(person_analysis),
            "query_params": {
                "limit": limit,
                "offset": offset,
                "person_name": person_name,
                "influence_level": influence_level,
                "min_influence": min_influence,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"获取人物分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取人物分析结果失败: {str(e)}")

@router.get("/industries", summary="获取行业影响分析结果")
async def get_industry_analysis(
    limit: int = Query(50, description="返回结果数量限制"),
    offset: int = Query(0, description="结果偏移量"),
    industry_name: Optional[str] = Query(None, description="行业名称过滤"),
    impact_direction: Optional[str] = Query(None, description="影响方向: positive/negative/neutral"),
    min_impact: float = Query(0.0, description="最小影响程度"),
    days: int = Query(7, description="时间范围(天)"),
    db: Session = Depends(get_db)
):
    """获取行业影响分析结果"""
    try:
        # 构建查询条件
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(
            IndustryImpact,
            NewsItem.title,
            NewsItem.published_at,
            NewsItem.source
        ).join(
            StockAnalysis, IndustryImpact.analysis_id == StockAnalysis.id
        ).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        ).where(
            NewsItem.collected_at >= cutoff_time
        )
        
        # 添加过滤条件
        if industry_name:
            query = query.where(IndustryImpact.industry_name.ilike(f"%{industry_name}%"))
        
        if impact_direction:
            query = query.where(IndustryImpact.impact_direction == impact_direction)
        
        query = query.where(IndustryImpact.impact_magnitude >= min_impact)
        
        # 排序和分页
        query = query.order_by(desc(NewsItem.published_at)).offset(offset).limit(limit)
        
        result = db.execute(query)
        industries = result.fetchall()
        
        # 格式化结果
        industry_analysis = []
        for industry, title, published_at, source in industries:
            industry_analysis.append({
                "industry_name": industry.industry_name,
                "industry_code": industry.industry_code,
                "sub_industry": industry.sub_industry,
                "impact_type": industry.impact_type,
                "impact_direction": industry.impact_direction,
                "impact_magnitude": industry.impact_magnitude,
                "confidence_level": industry.confidence_level,
                "immediate_impact": industry.immediate_impact,
                "short_term_impact": industry.short_term_impact,
                "long_term_impact": industry.long_term_impact,
                "news_title": title,
                "published_at": published_at,
                "source": source
            })
        
        return {
            "success": True,
            "data": industry_analysis,
            "total": len(industry_analysis),
            "query_params": {
                "limit": limit,
                "offset": offset,
                "industry_name": industry_name,
                "impact_direction": impact_direction,
                "min_impact": min_impact,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"获取行业分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行业分析结果失败: {str(e)}")

@router.get("/events", summary="获取关键事件分析结果")
async def get_event_analysis(
    limit: int = Query(50, description="返回结果数量限制"),
    offset: int = Query(0, description="结果偏移量"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    market_significance: Optional[str] = Query(None, description="市场重要性: major/moderate/minor"),
    days: int = Query(7, description="时间范围(天)"),
    db: Session = Depends(get_db)
):
    """获取关键事件分析结果"""
    try:
        # 构建查询条件
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = select(
            KeyEvent,
            NewsItem.title,
            NewsItem.published_at,
            NewsItem.source
        ).join(
            StockAnalysis, KeyEvent.analysis_id == StockAnalysis.id
        ).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        ).where(
            NewsItem.collected_at >= cutoff_time
        )
        
        # 添加过滤条件
        if event_type:
            query = query.where(KeyEvent.event_type == event_type)
        
        if market_significance:
            query = query.where(KeyEvent.market_significance == market_significance)
        
        # 排序和分页
        query = query.order_by(desc(NewsItem.published_at)).offset(offset).limit(limit)
        
        result = db.execute(query)
        events = result.fetchall()
        
        # 格式化结果
        event_analysis = []
        for event, title, published_at, source in events:
            event_analysis.append({
                "event_type": event.event_type,
                "event_title": event.event_title,
                "event_description": event.event_description,
                "market_significance": event.market_significance,
                "event_category": event.event_category,
                "expected_volatility": event.expected_volatility,
                "primary_companies": event.primary_companies,
                "secondary_companies": event.secondary_companies,
                "affected_industries": event.affected_industries,
                "news_title": title,
                "published_at": published_at,
                "source": source
            })
        
        return {
            "success": True,
            "data": event_analysis,
            "total": len(event_analysis),
            "query_params": {
                "limit": limit,
                "offset": offset,
                "event_type": event_type,
                "market_significance": market_significance,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"获取事件分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取事件分析结果失败: {str(e)}")

@router.post("/entities/extract", summary="提取新闻实体")
async def extract_news_entities(
    news_id: str,
    db: Session = Depends(get_db)
):
    """从指定新闻中提取实体信息"""
    try:
        # 获取新闻
        query = select(NewsItem).where(NewsItem.id == news_id)
        result = db.execute(query)
        news_item = result.scalar_one_or_none()
        
        if not news_item:
            raise HTTPException(status_code=404, detail="新闻不存在")
        
        # 进行实体识别
        entity_result = await deepseek_service.extract_entities(news_item)
        
        if not entity_result:
            return {
                "success": False,
                "message": "实体识别失败",
                "news_id": news_id
            }
        
        # 保存结果到数据库
        saved_count = await deepseek_service.save_entity_analysis_results(news_item, entity_result)
        
        return {
            "success": True,
            "message": f"成功识别并保存 {saved_count} 个实体",
            "news_id": news_id,
            "entities": {
                "companies": [
                    {
                        "name": entity.name,
                        "impact_direction": entity.impact_direction,
                        "impact_magnitude": entity.impact_magnitude,
                        "confidence": entity.confidence
                    } for entity in entity_result.companies
                ],
                "persons": [
                    {
                        "name": entity.name,
                        "impact_direction": entity.impact_direction,
                        "impact_magnitude": entity.impact_magnitude,
                        "confidence": entity.confidence
                    } for entity in entity_result.persons
                ],
                "industries": entity_result.industries,
                "events": entity_result.events
            }
        }
        
    except Exception as e:
        logger.error(f"提取新闻实体失败: {e}")
        raise HTTPException(status_code=500, detail=f"提取新闻实体失败: {str(e)}")

@router.get("/entities/summary", summary="实体分析统计摘要")
async def get_entity_summary(
    days: int = Query(7, description="时间范围(天)"),
    db: Session = Depends(get_db)
):
    """获取实体分析统计摘要"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # 统计公司实体
        company_query = select(MentionedCompany).join(
            StockAnalysis, MentionedCompany.analysis_id == StockAnalysis.id
        ).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        ).where(
            NewsItem.collected_at >= cutoff_time
        )
        company_result = db.execute(company_query)
        companies = company_result.scalars().all()
        
        # 统计人物实体
        person_query = select(MentionedPerson).join(
            StockAnalysis, MentionedPerson.analysis_id == StockAnalysis.id
        ).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        ).where(
            NewsItem.collected_at >= cutoff_time
        )
        person_result = db.execute(person_query)
        persons = person_result.scalars().all()
        
        # 统计行业影响
        industry_query = select(IndustryImpact).join(
            StockAnalysis, IndustryImpact.analysis_id == StockAnalysis.id
        ).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        ).where(
            NewsItem.collected_at >= cutoff_time
        )
        industry_result = db.execute(industry_query)
        industries = industry_result.scalars().all()
        
        # 生成统计信息
        company_stats = {
            "total": len(companies),
            "positive_impact": len([c for c in companies if c.impact_direction == "positive"]),
            "negative_impact": len([c for c in companies if c.impact_direction == "negative"]),
            "neutral_impact": len([c for c in companies if c.impact_direction == "neutral"]),
            "high_impact": len([c for c in companies if c.impact_magnitude >= 0.7]),
            "top_companies": {}
        }
        
        person_stats = {
            "total": len(persons),
            "high_influence": len([p for p in persons if p.influence_level == "high"]),
            "medium_influence": len([p for p in persons if p.influence_level == "medium"]),
            "low_influence": len([p for p in persons if p.influence_level == "low"]),
            "top_persons": {}
        }
        
        industry_stats = {
            "total": len(industries),
            "positive_impact": len([i for i in industries if i.impact_direction == "positive"]),
            "negative_impact": len([i for i in industries if i.impact_direction == "negative"]),
            "neutral_impact": len([i for i in industries if i.impact_direction == "neutral"]),
            "top_industries": {}
        }
        
        # 统计热门公司
        from collections import Counter
        company_counter = Counter([c.company_name for c in companies])
        company_stats["top_companies"] = dict(company_counter.most_common(10))
        
        # 统计热门人物
        person_counter = Counter([p.person_name for p in persons])
        person_stats["top_persons"] = dict(person_counter.most_common(10))
        
        # 统计热门行业
        industry_counter = Counter([i.industry_name for i in industries])
        industry_stats["top_industries"] = dict(industry_counter.most_common(10))
        
        return {
            "success": True,
            "time_range": f"最近 {days} 天",
            "summary": {
                "companies": company_stats,
                "persons": person_stats,
                "industries": industry_stats
            }
        }
        
    except Exception as e:
        logger.error(f"获取实体分析摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实体分析摘要失败: {str(e)}")
