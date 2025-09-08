"""
分析相关API端点
"""
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from yuqing.core.database import get_db
from yuqing.models.database_models import NewsItem, StockAnalysis
from yuqing.services.deepseek_service import deepseek_service
from yuqing.services.hot_news_discovery import hot_news_discovery
from yuqing.core.logging import app_logger as logger

router = APIRouter()


@router.get("/", summary="获取分析列表")
async def get_analysis_list(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    sentiment: Optional[str] = Query(None, description="情感过滤"),
    impact: Optional[str] = Query(None, description="影响级别过滤"),
    hours: Optional[int] = Query(24, description="时间范围(小时)"),
    db: Session = Depends(get_db)
):
    """获取分析结果列表"""
    try:
        # 构建查询
        query = select(StockAnalysis, NewsItem).join(
            NewsItem, StockAnalysis.news_id == NewsItem.id
        )

        # 时间过滤
        if hours:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            query = query.where(
                StockAnalysis.analysis_timestamp >= cutoff_time)

        # 情感过滤
        if sentiment:
            query = query.where(StockAnalysis.sentiment_label == sentiment)

        # 影响级别过滤
        if impact:
            query = query.where(StockAnalysis.market_impact_level == impact)

        # 排序和分页
        query = query.order_by(desc(StockAnalysis.analysis_timestamp))
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = db.execute(query)
        analysis_items = result.all()

        # 获取总数
        count_query = select(func.count(StockAnalysis.id))
        if hours:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            count_query = count_query.where(
                StockAnalysis.analysis_timestamp >= cutoff_time)
        if sentiment:
            count_query = count_query.where(
                StockAnalysis.sentiment_label == sentiment)
        if impact:
            count_query = count_query.where(
                StockAnalysis.market_impact_level == impact)

        total_result = db.execute(count_query)
        total = total_result.scalar()

        return {
            "data": [
                {
                    "analysis": {
                        "id": analysis.id,
                        "sentiment_label": analysis.sentiment_label,
                        "confidence_score": analysis.confidence_score,
                        "market_impact_level": analysis.market_impact_level,
                        "analysis_result": analysis.analysis_result,
                        "analysis_timestamp": analysis.analysis_timestamp
                    },
                    "news": {
                        "id": news.id,
                        "title": news.title,
                        "source": news.source,
                        "published_at": news.published_at,
                        "collected_at": news.collected_at
                    }
                }
                for analysis, news in analysis_items
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }

    except Exception as e:
        logger.error(f"获取分析列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取分析列表失败")


@router.get("/stats/sentiment", summary="获取情感分析统计")
async def get_sentiment_stats(
    hours: int = Query(24, description="统计时间范围(小时)"),
    db: Session = Depends(get_db)
):
    """获取情感分析统计数据"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = select(StockAnalysis).where(
            StockAnalysis.analysis_timestamp >= cutoff_time
        )
        result = db.execute(query)
        analyses = result.scalars().all()

        # 统计情感分布
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        impact_counts = {"high": 0, "medium": 0, "low": 0}
        confidence_scores = []

        for analysis in analyses:
            if analysis.sentiment_label:
                sentiment_counts[analysis.sentiment_label] = sentiment_counts.get(
                    analysis.sentiment_label, 0) + 1
            if analysis.market_impact_level:
                impact_counts[analysis.market_impact_level] = impact_counts.get(
                    analysis.market_impact_level, 0) + 1
            if analysis.confidence_score:
                confidence_scores.append(analysis.confidence_score)

        # 计算置信度统计
        avg_confidence = sum(confidence_scores) / \
            len(confidence_scores) if confidence_scores else 0

        return {
            "timeframe_hours": hours,
            "total_analyses": len(analyses),
            "sentiment_distribution": sentiment_counts,
            "impact_distribution": impact_counts,
            "confidence_stats": {
                "average": round(avg_confidence, 3),
                "min": min(confidence_scores) if confidence_scores else 0,
                "max": max(confidence_scores) if confidence_scores else 0,
                "count": len(confidence_scores)
            },
            "generated_at": datetime.now(timezone.utc)
        }

    except Exception as e:
        logger.error(f"获取情感统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取情感统计失败")


@router.get("/stats/timeline", summary="获取时间线统计")
async def get_timeline_stats(
    hours: int = Query(24, description="统计时间范围(小时)"),
    interval: int = Query(1, description="统计间隔(小时)"),
    db: Session = Depends(get_db)
):
    """获取分析结果的时间线统计"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = select(StockAnalysis).where(
            StockAnalysis.analysis_timestamp >= cutoff_time
        ).order_by(StockAnalysis.analysis_timestamp)

        result = db.execute(query)
        analyses = result.scalars().all()

        # 按时间间隔分组
        timeline_data = []
        current_time = cutoff_time
        end_time = datetime.now(timezone.utc)

        while current_time < end_time:
            next_time = current_time + timedelta(hours=interval)

            # 筛选该时间段内的分析
            period_analyses = [
                a for a in analyses
                if current_time <= a.analysis_timestamp < next_time
            ]

            # 统计该时间段的情感分布
            sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
            for analysis in period_analyses:
                if analysis.sentiment_label:
                    sentiment_counts[analysis.sentiment_label] += 1

            timeline_data.append({
                "timestamp": current_time,
                "count": len(period_analyses),
                "sentiment_distribution": sentiment_counts
            })

            current_time = next_time

        return {
            "timeframe_hours": hours,
            "interval_hours": interval,
            "timeline": timeline_data
        }

    except Exception as e:
        logger.error(f"获取时间线统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取时间线统计失败")


@router.post("/analyze/recent", summary="分析最近新闻")
async def analyze_recent_news(
    background_tasks: BackgroundTasks,
    hours: int = Query(24, description="分析时间范围(小时)"),
    limit: int = Query(50, description="分析数量限制")
):
    """触发最近新闻的批量分析"""
    try:
        # 添加后台任务
        background_tasks.add_task(
            _background_analyze_recent_news,
            hours=hours,
            limit=limit
        )

        return {
            "message": "分析任务已启动",
            "hours": hours,
            "limit": limit,
            "started_at": datetime.now(timezone.utc)
        }

    except Exception as e:
        logger.error(f"启动分析任务失败: {e}")
        raise HTTPException(status_code=500, detail="启动分析任务失败")


async def _background_analyze_recent_news(hours: int, limit: int):
    """后台执行的分析任务"""
    try:
        logger.info(f"开始后台分析任务: {hours}小时内的{limit}条新闻")
        result = await deepseek_service.analyze_recent_news(hours=hours, limit=limit)
        logger.info(f"后台分析完成: 分析了{result['analyzed_count']}条新闻")
    except Exception as e:
        logger.error(f"后台分析任务失败: {e}")


@router.get("/keywords/trending", summary="获取热门关键词")
async def get_trending_keywords(
    hours: int = Query(24, description="统计时间范围(小时)"),
    limit: int = Query(20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取热门关键词统计"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = select(StockAnalysis).where(
            StockAnalysis.analysis_timestamp >= cutoff_time
        )
        result = db.execute(query)
        analyses = result.scalars().all()

        # 提取和统计关键词
        keyword_counts = {}
        for analysis in analyses:
            if analysis.analysis_result and 'keywords' in analysis.analysis_result:
                keywords = analysis.analysis_result.get('keywords', [])
                for keyword in keywords:
                    keyword_counts[keyword] = keyword_counts.get(
                        keyword, 0) + 1

        # 按频次排序
        trending_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return {
            "timeframe_hours": hours,
            "trending_keywords": [
                {"keyword": keyword, "count": count}
                for keyword, count in trending_keywords
            ],
            "total_unique_keywords": len(keyword_counts),
            "generated_at": datetime.now(timezone.utc)
        }

    except Exception as e:
        logger.error(f"获取热门关键词失败: {e}")
        raise HTTPException(status_code=500, detail="获取热门关键词失败")


@router.get("/hotspots/discover", summary="智能热点发现")
async def discover_hot_news(
    hours: int = Query(6, description="回溯时间(小时)"),
    limit: int = Query(30, description="返回数量限制")
):
    """智能发现实时热点新闻"""
    try:
        hot_news = await hot_news_discovery.discover_hot_news(hours_back=hours)

        # 限制返回数量
        hot_news = hot_news[:limit]

        return {
            "timeframe_hours": hours,
            "total_hotspots": len(hot_news),
            "hotspots": [
                {
                    "title": news.get("title"),
                    "hot_reason": news.get("hot_reason"),
                    "hot_score": news.get("hot_score"),
                    "hot_keywords": news.get("hot_keywords", []),
                    "source": news.get("source"),
                    "published_at": news.get("published_at"),
                    "source_url": news.get("source_url")
                }
                for news in hot_news
            ],
            "generated_at": datetime.now(timezone.utc)
        }

    except Exception as e:
        logger.error(f"智能热点发现失败: {e}")
        raise HTTPException(status_code=500, detail="智能热点发现失败")


@router.get("/hotspots/trending-keywords", summary="动态趋势关键词")
async def get_dynamic_trending_keywords(
    limit: int = Query(20, description="返回数量")
):
    """获取基于热点发现的动态趋势关键词"""
    try:
        trending = await hot_news_discovery.get_trending_keywords_dynamic(limit=limit)

        return {
            "trending_keywords": trending,
            "algorithm": "dynamic_discovery",
            "total_keywords": len(trending),
            "generated_at": datetime.now(timezone.utc)
        }

    except Exception as e:
        logger.error(f"获取动态趋势关键词失败: {e}")
        raise HTTPException(status_code=500, detail="获取动态趋势关键词失败")
