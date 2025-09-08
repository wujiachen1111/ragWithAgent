"""
新闻舆情分析系统 - Streamlit前端界面
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time

# 页面配置
st.set_page_config(
    page_title="新闻舆情分析系统",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API基础URL
API_BASE_URL = "http://localhost:8000/api"

@st.cache_data(ttl=60)  # 缓存1分钟
def fetch_api_data(endpoint: str, params: dict = None):
    """从API获取数据"""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API请求失败: {e}")
        return None

@st.cache_data(ttl=30)
def check_api_status():
    """检查API连接状态"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.json()
    except:
        return {"status": "disconnected"}

def main():
    """主函数"""
    st.title("📰 新闻舆情分析系统")
    
    # 自动刷新设置
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        auto_refresh = st.checkbox("🔄 自动刷新", value=True)
    with col2:
        refresh_interval = st.selectbox(
            "刷新间隔", 
            options=[30, 60, 300, 600],
            index=2,
            format_func=lambda x: f"{x}秒"
        )
    with col3:
        if auto_refresh:
            st.write(f"⏰ 数据将每{refresh_interval}秒自动更新")
            # 使用JavaScript进行页面自动刷新
            st.markdown(f"""
                <script>
                setTimeout(function(){{
                    window.location.reload();
                }}, {refresh_interval * 1000});
                </script>
            """, unsafe_allow_html=True)
        else:
            st.write("🛑 自动刷新已关闭")
    
    st.markdown("---")
    
    # 检查API状态
    api_status = check_api_status()
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # API状态显示
        if api_status.get("status") == "healthy":
            st.success("✅ API服务正常")
            st.success("✅ 数据库连接正常") 
            st.success("✅ Redis缓存正常")
            if api_status.get("chroma") == "connected":
                st.success("✅ Chroma向量库正常")
            else:
                st.warning("⚠️ Chroma向量库离线")
        else:
            st.error("❌ API服务离线")
            st.info("请确保后端服务已启动")
        
        st.markdown("---")
        
        # 时间范围选择
        time_range = st.selectbox(
            "📅 时间范围",
            options=[1, 6, 12, 24, 48, 72],
            index=3,
            format_func=lambda x: f"最近 {x} 小时"
        )
        
        # 数据源过滤
        source_filter = st.selectbox(
            "📡 数据源",
            options=["全部", "google_news", "gdelt", "twitter", "chinese_finance"]
        )
        source_param = None if source_filter == "全部" else source_filter
        
        # 情感过滤
        sentiment_filter = st.selectbox(
            "😊 情感过滤",
            options=["全部", "positive", "negative", "neutral"]
        )
        sentiment_param = None if sentiment_filter == "全部" else sentiment_filter
        
        # 刷新按钮
        if st.button("🔄 刷新数据"):
            st.cache_data.clear()
            st.rerun()
    
    # 主页面布局
    if api_status.get("status") == "healthy":
        tab1, tab2, tab3, tab4 = st.tabs(["📊 概览", "📰 新闻", "🔍 分析", "📈 统计"])
        
        with tab1:
            show_overview(time_range)
        
        with tab2:
            show_news_list(time_range, source_param)
        
        with tab3:
            show_analysis_results(time_range, sentiment_param)
        
        with tab4:
            show_statistics(time_range)
    else:
        st.error("⚠️ API服务不可用，请先启动后端服务")
        st.info("运行命令: `python -m app.main` 启动API服务")

def show_overview(time_range: int):
    """显示系统概览"""
    st.header("🎯 系统概览")
    
    # 获取统计数据
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("� 数据源状态")
        source_stats = fetch_api_data("/news/sources/stats", {"hours": time_range})
        
        if source_stats:
            total_news = source_stats.get("total_news", 0)
            active_sources = source_stats.get("summary", {}).get("active_sources", 0)
            
            # 显示总体指标
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("📰 总新闻数", total_news)
            with col_b:
                st.metric("� 活跃数据源", active_sources)
            
            # 数据源详情
            if "sources" in source_stats:
                source_data = []
                for source, stats in source_stats["sources"].items():
                    source_data.append({
                        "数据源": source,
                        "新闻数量": stats["count"],
                        "最新更新": stats["latest"]
                    })
                
                if source_data:
                    df_sources = pd.DataFrame(source_data)
                    st.dataframe(df_sources, use_container_width=True)
        else:
            st.info("暂无数据源统计")
    
    with col2:
        st.subheader("🔍 情感分析概况")
        sentiment_stats = fetch_api_data("/analysis/stats/sentiment", {"hours": time_range})
        
        if sentiment_stats:
            total_analyses = sentiment_stats.get("total_analyses", 0)
            avg_confidence = sentiment_stats.get("confidence_stats", {}).get("average", 0)
            
            # 显示分析指标
            col_c, col_d = st.columns(2)
            with col_c:
                st.metric("🔍 分析总数", total_analyses)
            with col_d:
                st.metric("🎯 平均置信度", f"{avg_confidence:.2f}")
            
            # 情感分布饼图
            sentiment_dist = sentiment_stats.get("sentiment_distribution", {})
            if any(sentiment_dist.values()):
                fig_pie = px.pie(
                    values=list(sentiment_dist.values()),
                    names=list(sentiment_dist.keys()),
                    title="情感分布",
                    color_discrete_map={
                        'positive': '#00C851',
                        'negative': '#FF4444',
                        'neutral': '#FFBB33'
                    }
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("暂无分析统计")

def show_news_list(time_range: int, source_filter: str):
    """显示新闻列表"""
    st.header("📰 新闻列表")
    
    # 搜索框
    keyword = st.text_input("🔍 关键词搜索", placeholder="输入关键词搜索新闻...")
    
    # 获取新闻数据
    params = {
        "hours": time_range,
        "limit": 50
    }
    if source_filter:
        params["source"] = source_filter
    if keyword:
        params["keyword"] = keyword
    
    news_data = fetch_api_data("/news/", params)
    
    if news_data and news_data.get("data"):
        news_list = news_data["data"]
        
        # 显示分页信息
        pagination = news_data.get("pagination", {})
        st.info(f"共找到 {pagination.get('total', 0)} 条新闻，显示前 {len(news_list)} 条")
        
        # 显示新闻卡片
        for news in news_list:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"### {news['title']}")
                    st.markdown(f"**来源**: {news['source']} | **发布时间**: {news['published_at']}")
                    
                    if news['content'] and len(news['content']) > 100:
                        st.markdown(f"{news['content'][:100]}...")
                        with st.expander("查看完整内容"):
                            st.markdown(news['content'])
                    elif news['content']:
                        st.markdown(news['content'])
                
                with col2:
                    if st.button("🔍 详情", key=f"detail_{news['id']}"):
                        show_news_detail(news['id'])
                
                st.markdown("---")
    else:
        st.info("暂无新闻数据")

def show_news_detail(news_id: str):
    """显示新闻详情"""
    detail_data = fetch_api_data(f"/news/{news_id}")
    
    if detail_data:
        news = detail_data["news"]
        analysis = detail_data.get("analysis")
        
        with st.expander(f"新闻详情: {news['title']}", expanded=True):
            st.markdown(f"**来源**: {news['source']} | **发布时间**: {news['published_at']}")
            
            if news['content']:
                st.markdown("### 内容")
                st.markdown(news['content'])
            
            if analysis:
                st.markdown("### 分析结果")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    sentiment_color = {
                        'positive': '🟢',
                        'negative': '🔴',
                        'neutral': '🟡'
                    }.get(analysis['sentiment_label'], '⚪')
                    st.metric(
                        "情感倾向",
                        f"{sentiment_color} {analysis['sentiment_label']}"
                    )
                
                with col2:
                    st.metric("置信度", f"{analysis['confidence_score']:.2f}")
                
                with col3:
                    st.metric("市场影响", analysis.get('market_impact_level', 'N/A'))
                
                # 显示详细分析结果
                if analysis.get('analysis_result'):
                    result = analysis['analysis_result']
                    if isinstance(result, str):
                        try:
                            result = json.loads(result)
                        except:
                            pass
                    
                    if isinstance(result, dict):
                        if 'keywords' in result:
                            st.markdown("**关键词**: " + ", ".join(result['keywords']))
                        if 'summary' in result:
                            st.markdown("**摘要**: " + result['summary'])
                        if 'reasoning' in result:
                            st.markdown("**分析推理**: " + result['reasoning'])

def show_analysis_results(time_range: int, sentiment_filter: str):
    """显示分析结果"""
    st.header("� 分析结果")
    
    # 获取分析数据
    params = {
        "hours": time_range,
        "limit": 50
    }
    if sentiment_filter:
        params["sentiment"] = sentiment_filter
    
    analysis_data = fetch_api_data("/analysis/", params)
    
    if analysis_data and analysis_data.get("data"):
        analyses = analysis_data["data"]
        
        # 显示分页信息
        pagination = analysis_data.get("pagination", {})
        st.info(f"共找到 {pagination.get('total', 0)} 条分析结果，显示前 {len(analyses)} 条")
        
        # 创建DataFrame显示
        analysis_list = []
        for item in analyses:
            analysis = item["analysis"]
            news = item["news"]
            
            analysis_list.append({
                "新闻标题": news["title"][:50] + "..." if len(news["title"]) > 50 else news["title"],
                "情感": analysis["sentiment_label"],
                "置信度": f"{analysis['confidence_score']:.2f}",
                "市场影响": analysis.get("market_impact_level", "N/A"),
                "来源": news["source"],
                "分析时间": analysis["analysis_timestamp"]
            })
        
        if analysis_list:
            df_analysis = pd.DataFrame(analysis_list)
            st.dataframe(df_analysis, use_container_width=True)
    else:
        st.info("暂无分析数据")

def show_statistics(time_range: int):
    """显示统计图表"""
    st.header("📈 统计分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 情感趋势")
        timeline_data = fetch_api_data("/analysis/stats/timeline", {
            "hours": time_range,
            "interval": max(1, time_range // 12)
        })
        
        if timeline_data and timeline_data.get("timeline"):
            timeline = timeline_data["timeline"]
            
            # 准备时间线数据
            timestamps = [item["timestamp"] for item in timeline]
            positive_counts = [item["sentiment_distribution"]["positive"] for item in timeline]
            negative_counts = [item["sentiment_distribution"]["negative"] for item in timeline]
            neutral_counts = [item["sentiment_distribution"]["neutral"] for item in timeline]
            
            # 创建时间线图
            fig_timeline = go.Figure()
            fig_timeline.add_trace(go.Scatter(
                x=timestamps, y=positive_counts,
                mode='lines+markers', name='正面', line=dict(color='green')
            ))
            fig_timeline.add_trace(go.Scatter(
                x=timestamps, y=negative_counts,
                mode='lines+markers', name='负面', line=dict(color='red')
            ))
            fig_timeline.add_trace(go.Scatter(
                x=timestamps, y=neutral_counts,
                mode='lines+markers', name='中性', line=dict(color='orange')
            ))
            
            fig_timeline.update_layout(
                title="情感分析时间趋势",
                xaxis_title="时间",
                yaxis_title="数量",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("暂无时间线数据")
    
    with col2:
        st.subheader("🔥 热门关键词")
        keywords_data = fetch_api_data("/analysis/keywords/trending", {
            "hours": time_range,
            "limit": 15
        })
        
        if keywords_data and keywords_data.get("trending_keywords"):
            keywords = keywords_data["trending_keywords"]
            
            if keywords:
                # 创建关键词条形图
                df_keywords = pd.DataFrame(keywords)
                fig_keywords = px.bar(
                    df_keywords.head(10),
                    x="count",
                    y="keyword",
                    orientation='h',
                    title="热门关键词 TOP 10",
                    labels={"count": "出现次数", "keyword": "关键词"}
                )
                fig_keywords.update_layout(yaxis={'categoryorder':'total ascending'})
                
                st.plotly_chart(fig_keywords, use_container_width=True)
                
                # 显示完整关键词列表
                with st.expander("查看完整关键词列表"):
                    for i, kw in enumerate(keywords, 1):
                        st.markdown(f"{i}. **{kw['keyword']}** ({kw['count']}次)")
            else:
                st.info("暂无关键词数据")
        else:
            st.info("暂无关键词统计")

if __name__ == "__main__":
    main()
