"""
新闻相关API端点
"""
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_, or_

from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem, StockAnalysis, MentionedCompany, MentionedPerson, IndustryImpact, KeyEvent
from yuqing.core.logging import logger
from yuqing.services.cailian_news_service import cailian_news_service

router = APIRouter()

@router.get("/", summary="获取新闻列表")
async def get_news_list(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    source: Optional[str] = Query(None, description="新闻源过滤"),
    hours: Optional[int] = Query(24, description="时间范围(小时)"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    db: Session = Depends(get_db)
):
    """获取新闻列表"""
    try:
        # 构建查询
        query = select(NewsItem)
        
        # 时间过滤
        if hours:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            query = query.where(NewsItem.collected_at >= cutoff_time)
        
        # 来源过滤
        if source:
            query = query.where(NewsItem.source.like(f"%{source}%"))
        
        # 关键词搜索
        if keyword:
            query = query.where(
                or_(
                    NewsItem.title.like(f"%{keyword}%"),
                    NewsItem.content.like(f"%{keyword}%")
                )
            )
        
        # 排序和分页
        query = query.order_by(desc(NewsItem.collected_at))
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        result = db.execute(query)
        news_items = result.scalars().all()
        
        # 获取总数
        count_query = select(NewsItem)
        if hours:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            count_query = count_query.where(NewsItem.collected_at >= cutoff_time)
        if source:
            count_query = count_query.where(NewsItem.source.like(f"%{source}%"))
        if keyword:
            count_query = count_query.where(
                or_(
                    NewsItem.title.like(f"%{keyword}%"),
                    NewsItem.content.like(f"%{keyword}%")
                )
            )
        
        total_result = db.execute(count_query)
        total = len(total_result.scalars().all())
        
        return {
            "data": [
                {
                    "id": item.id,
                    "title": item.title,
                    "content": item.content[:200] + "..." if len(item.content or "") > 200 else item.content,
                    "source": item.source,
                    "source_url": item.source_url,
                    "published_at": item.published_at,
                    "collected_at": item.collected_at,
                    "language": item.language,
                    "region": item.region
                }
                for item in news_items
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"获取新闻列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取新闻列表失败")

@router.get("/stats", summary="获取新闻统计信息")
async def get_news_stats(
    hours: Optional[int] = Query(24, description="时间范围(小时)"),
    db: Session = Depends(get_db)
):
    """获取新闻统计信息"""
    try:
        # 时间过滤
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours) if hours else None
        
        # 基础查询
        base_query = select(NewsItem)
        if cutoff_time:
            base_query = base_query.where(NewsItem.collected_at >= cutoff_time)
        
        all_news = db.execute(base_query).scalars().all()
        
        # 统计信息
        total_news = len(all_news)
        
        # 按来源统计
        by_source = {}
        # 按分析状态统计
        by_analysis_status = {}
        
        for news in all_news:
            # 来源统计
            source = news.source or "unknown"
            by_source[source] = by_source.get(source, 0) + 1
            
            # 分析状态统计
            status = news.analysis_status or "unknown"
            by_analysis_status[status] = by_analysis_status.get(status, 0) + 1
        
        # 最近24小时统计
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_query = select(NewsItem).where(NewsItem.collected_at >= recent_cutoff)
        recent_news = db.execute(recent_query).scalars().all()
        recent_24h = len(recent_news)
        
        return {
            "total_news": total_news,
            "by_source": by_source,
            "by_analysis_status": by_analysis_status,
            "recent_24h": recent_24h,
            "time_range_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取新闻统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取新闻统计失败")

@router.get("/comprehensive", summary="获取已分析新闻的完整数据")
async def get_comprehensive_news(
    hours: int = Query(6, description="时间范围(小时)"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量"),
    include_entities: bool = Query(True, description="是否包含实体分析"),
    include_raw_data: bool = Query(False, description="是否包含原始数据"),
    db: Session = Depends(get_db)
):
    """获取特定时间内所有已分析新闻的完整数据（包括情感分析和实体分析）"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # 查询已分析的新闻（有情感分析结果的）
        query = select(
            NewsItem,
            StockAnalysis
        ).join(
            StockAnalysis, NewsItem.id == StockAnalysis.news_id
        ).where(
            and_(
                NewsItem.collected_at >= cutoff_time,
                StockAnalysis.sentiment_label.isnot(None)  # 确保有分析结果
            )
        ).order_by(desc(NewsItem.collected_at)).limit(limit)
        
        result = db.execute(query)
        news_analysis_pairs = result.all()
        
        if not news_analysis_pairs:
            return {
                "data": [],
                "summary": {
                    "total_analyzed": 0,
                    "time_range_hours": hours,
                    "message": f"最近 {hours} 小时内没有已分析的新闻"
                }
            }
        
        comprehensive_data = []
        
        for news_item, analysis in news_analysis_pairs:
            # 构建基础新闻数据
            news_data = {
                "id": news_item.id,
                "title": news_item.title,
                "content": news_item.content,
                "summary": news_item.summary,
                "source": news_item.source,
                "source_url": news_item.source_url,
                "published_at": news_item.published_at,
                "collected_at": news_item.collected_at,
                "language": news_item.language,
                "region": news_item.region
            }
            
            # 添加原始数据（可选）
            if include_raw_data:
                news_data["raw_data"] = news_item.raw_data
            
            # 添加情感分析数据
            sentiment_analysis = {
                "analysis_id": analysis.id,
                "sentiment_label": analysis.sentiment_label,
                "confidence_score": analysis.confidence_score,
                "market_impact_level": analysis.market_impact_level,
                "analysis_result": analysis.analysis_result,
                "analysis_timestamp": analysis.analysis_timestamp
            }
            
            # 构建完整数据对象
            complete_item = {
                "news": news_data,
                "sentiment_analysis": sentiment_analysis
            }
            
            # 获取实体分析数据（可选）
            if include_entities:
                entities = {
                    "companies": [],
                    "persons": [],
                    "industries": [],
                    "events": []
                }
                
                # 查询公司实体
                companies_query = select(MentionedCompany).where(
                    MentionedCompany.analysis_id == analysis.id
                )
                companies_result = db.execute(companies_query)
                for company in companies_result.scalars():
                    entities["companies"].append({
                        "name": company.company_name,
                        "stock_code": company.stock_code,
                        "exchange": company.exchange,
                        "impact_direction": company.impact_direction,
                        "impact_magnitude": company.impact_magnitude,
                        "confidence_level": company.confidence_level,
                        "impact_type": company.impact_type
                    })
                
                # 查询人物实体
                persons_query = select(MentionedPerson).where(
                    MentionedPerson.analysis_id == analysis.id
                )
                persons_result = db.execute(persons_query)
                for person in persons_result.scalars():
                    entities["persons"].append({
                        "name": person.person_name,
                        "position_title": person.position_title,
                        "company_affiliation": person.company_affiliation,
                        "influence_level": person.influence_level,
                        "person_type": person.person_type,
                        "market_influence_score": person.market_influence_score
                    })
                
                # 查询行业影响
                industries_query = select(IndustryImpact).where(
                    IndustryImpact.analysis_id == analysis.id
                )
                industries_result = db.execute(industries_query)
                for industry in industries_result.scalars():
                    entities["industries"].append({
                        "name": industry.industry_name,
                        "industry_code": industry.industry_code,
                        "sub_industry": industry.sub_industry,
                        "impact_direction": industry.impact_direction,
                        "impact_magnitude": industry.impact_magnitude,
                        "confidence_level": industry.confidence_level,
                        "impact_type": industry.impact_type
                    })
                
                # 查询关键事件
                events_query = select(KeyEvent).where(
                    KeyEvent.analysis_id == analysis.id
                )
                events_result = db.execute(events_query)
                for event in events_result.scalars():
                    entities["events"].append({
                        "type": event.event_type,
                        "title": event.event_title,
                        "description": event.event_description,
                        "market_significance": event.market_significance,
                        "event_category": event.event_category
                    })
                
                complete_item["entity_analysis"] = entities
            
            comprehensive_data.append(complete_item)
        
        # 统计信息
        total_companies = 0
        total_persons = 0
        total_industries = 0
        total_events = 0
        
        if include_entities:
            for item in comprehensive_data:
                entities = item.get("entity_analysis", {})
                total_companies += len(entities.get("companies", []))
                total_persons += len(entities.get("persons", []))
                total_industries += len(entities.get("industries", []))
                total_events += len(entities.get("events", []))
        
        return {
            "data": comprehensive_data,
            "summary": {
                "total_analyzed": len(comprehensive_data),
                "time_range_hours": hours,
                "entities_included": include_entities,
                "raw_data_included": include_raw_data,
                "entity_counts": {
                    "companies": total_companies,
                    "persons": total_persons,
                    "industries": total_industries,
                    "events": total_events
                } if include_entities else None,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"获取综合新闻数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取综合新闻数据失败: {str(e)}")

@router.get("/{news_id}", summary="获取新闻详情")
async def get_news_detail(
    news_id: str,
    db: Session = Depends(get_db)
):
    """获取单条新闻详情"""
    try:
        # 获取新闻详情
        news_query = select(NewsItem).where(NewsItem.id == news_id)
        news_result = db.execute(news_query)
        news_item = news_result.scalar_one_or_none()
        
        if not news_item:
            raise HTTPException(status_code=404, detail="新闻不存在")
        
        # 获取分析结果
        analysis_query = select(StockAnalysis).where(StockAnalysis.news_id == news_id)
        analysis_result = db.execute(analysis_query)
        analysis = analysis_result.scalar_one_or_none()
        
        return {
            "news": {
                "id": news_item.id,
                "title": news_item.title,
                "content": news_item.content,
                "summary": news_item.summary,
                "source": news_item.source,
                "source_url": news_item.source_url,
                "published_at": news_item.published_at,
                "collected_at": news_item.collected_at,
                "language": news_item.language,
                "region": news_item.region,
                "raw_data": news_item.raw_data
            },
            "analysis": {
                "id": analysis.id,
                "sentiment_label": analysis.sentiment_label,
                "confidence_score": analysis.confidence_score,
                "market_impact_level": analysis.market_impact_level,
                "analysis_result": analysis.analysis_result,
                "analysis_timestamp": analysis.analysis_timestamp
            } if analysis else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取新闻详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取新闻详情失败")

@router.get("/sources/stats", summary="获取数据源统计")
async def get_source_stats(
    hours: int = Query(24, description="统计时间范围(小时)"),
    db: Session = Depends(get_db)
):
    """获取各数据源的统计信息"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = select(NewsItem).where(NewsItem.collected_at >= cutoff_time)
        result = db.execute(query)
        news_items = result.scalars().all()
        
        # 按来源统计
        source_stats = {}
        for item in news_items:
            source = item.source
            if source not in source_stats:
                source_stats[source] = {
                    "count": 0,
                    "latest": None,
                    "regions": set()
                }
            
            source_stats[source]["count"] += 1
            source_stats[source]["regions"].add(item.region or "unknown")
            
            if (source_stats[source]["latest"] is None or 
                item.collected_at > source_stats[source]["latest"]):
                source_stats[source]["latest"] = item.collected_at
        
        # 转换set为list
        for source in source_stats:
            source_stats[source]["regions"] = list(source_stats[source]["regions"])
        
        return {
            "timeframe_hours": hours,
            "total_news": len(news_items),
            "sources": source_stats,
            "summary": {
                "active_sources": len(source_stats),
                "collected_from": cutoff_time,
                "collected_to": datetime.now(timezone.utc)
            }
        }
        
    except Exception as e:
        logger.error(f"获取数据源统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取数据源统计失败")


@router.get("/cailian/latest", summary="获取财联社最新新闻")
async def get_cailian_latest_news(
    days: int = Query(1, ge=1, le=7, description="获取天数"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    important: bool = Query(False, description="是否只返回重要新闻")
):
    """获取财联社最新电报新闻"""
    try:
        # 获取财联社新闻
        news_items = await cailian_news_service.get_latest_news(days=days, limit=limit*2)
        
        # 如果需要过滤重要新闻
        if important:
            important_keywords = ['重要', '利好', '重磅', '突发', '关注', '警告', '利空', '大涨', '大跌']
            filtered_news = []
            for news in news_items:
                content = news.get('content', '') or ''
                title = news.get('title', '') or ''
                if any(keyword in content or keyword in title for keyword in important_keywords):
                    filtered_news.append(news)
            news_items = filtered_news
        
        # 限制返回数量
        result = news_items[:limit]
        
        return {
            "success": True,
            "total": len(result),
            "days": days,
            "important_only": important,
            "news": result,
            "source": "cailian",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取财联社最新新闻失败: {e}")
        raise HTTPException(status_code=500, detail="获取财联社新闻失败")


@router.post("/cailian/fetch", summary="立即获取财联社新闻")
async def fetch_cailian_news_now(
    limit: int = Query(100, ge=1, le=500, description="获取数量")
):
    """立即从财联社获取最新新闻"""
    try:
        # 获取新闻
        news_items = await cailian_news_service.fetch_cailian_news(limit=limit)
        
        # 保存到数据库
        saved_count = 0
        if news_items:
            saved_count = await cailian_news_service.save_to_database(news_items)
        
        return {
            "success": True,
            "fetched": len(news_items),
            "saved_to_db": saved_count,
            "source": "cailian",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取财联社新闻失败: {e}")
        raise HTTPException(status_code=500, detail="获取财联社新闻失败")


@router.get("/cailian/search", summary="搜索财联社新闻")
async def search_cailian_news(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量")
):
    """搜索财联社新闻"""
    try:
        news_items = await cailian_news_service.search_news(keyword=keyword, limit=limit)
        
        return {
            "success": True,
            "keyword": keyword,
            "total": len(news_items),
            "news": news_items,
            "source": "cailian",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"搜索财联社新闻失败: {e}")
        raise HTTPException(status_code=500, detail="搜索财联社新闻失败")
