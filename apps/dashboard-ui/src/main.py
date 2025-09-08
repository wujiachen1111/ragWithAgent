import streamlit as st
import httpx
import asyncio
from pydantic import BaseModel, ValidationError
from typing import List, Optional

# --- 配置 ---
RAG_ANALYSIS_API_URL = "http://localhost:8010/v1/analysis/execute"

# --- Pydantic 模型 (用于前端验证) ---
class AnalysisRequest(BaseModel):
    topic: str
    headline: Optional[str] = ""
    content: str
    symbols: List[str]
    time_horizon: str = "medium"
    risk_appetite: str = "balanced"
    region: str = "CN"
    max_iterations: int = 2

# --- API 调用函数 ---
async def execute_analysis(request_data: dict):
    """异步调用RAG分析API"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(RAG_ANALYSIS_API_URL, json=request_data)
            response.raise_for_status()  # 如果状态码是 4xx 或 5xx，则抛出异常
            return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"API 请求失败: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            st.error(f"无法连接到分析服务: {e}. 请确保服务正在 http://localhost:8010 运行。")
        except Exception as e:
            st.error(f"发生未知错误: {e}")
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="智策 InsightFolio - 投研分析系统", layout="wide")

st.title("🏛️ 智策 InsightFolio - RAG+Agent 投研分析系统")
st.caption("一个用于测试后端多智能体分析流程的前端界面")

with st.sidebar:
    st.header("API配置")
    RAG_ANALYSIS_API_URL = st.text_input("RAG分析服务API URL", RAG_ANALYSIS_API_URL)
    st.info("确保 `rag-analysis` 和 `yuqing-sentiment` 服务正在运行。")

st.header("创建新的分析任务")

# 使用表单来组织输入
with st.form("analysis_form"):
    topic = st.text_input("🎯 分析主题", placeholder="例如：最近科技股的投资机会如何？")
    headline = st.text_input("📰 相关新闻标题 (可选)", placeholder="例如：革命性AI产品引发市场热议")
    content = st.text_area("📄 详细内容/问题", height=150, placeholder="输入您关心的具体问题、市场事件或需要分析的新闻内容...")
    
    # 使用列布局
    col1, col2 = st.columns(2)
    with col1:
        symbols_str = st.text_input("股票代码 (用逗号分隔)", "000001,600036", help="例如: 600036,000001,AAPL")
    with col2:
        time_horizon = st.selectbox("投资周期", ["short", "medium", "long"], index=1)

    submitted = st.form_submit_button("🚀 开始分析", use_container_width=True)


if submitted:
    # --- 输入验证 ---
    error = False
    if not topic:
        st.error("请输入分析主题。")
        error = True
    if not content:
        st.error("请输入详细内容。")
        error = True
    
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
    if not symbols:
        st.error("请输入至少一个股票代码。")
        error = True

    if not error:
        try:
            # 使用Pydantic模型进行前端验证
            request = AnalysisRequest(
                topic=topic,
                headline=headline,
                content=content,
                symbols=symbols,
                time_horizon=time_horizon
            )
            request_data = request.model_dump()

            st.info(f"分析任务已提交，正在处理中... (主题: {topic}, 股票: {symbols_str})")
            
            # 执行异步API调用
            with st.spinner("🤖 正在调用多智能体进行分析，请稍候..."):
                result = asyncio.run(execute_analysis(request_data))

            if result:
                st.success("✅ 分析完成!")
                st.header("📊 分析结果")
                st.json(result)

        except ValidationError as e:
            st.error("输入数据格式有误，请检查：")
            st.json(e.errors())
