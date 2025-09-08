#!/bin/bash

# 智策 (InsightFolio) 开发环境初始化脚本
# 自动设置本地开发环境

set -e

echo "🚀 正在初始化智策 (InsightFolio) 开发环境..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python版本
echo -e "${YELLOW}📋 检查Python版本...${NC}"
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_version="3.10"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo -e "${RED}❌ Python版本需要 >= 3.10，当前版本: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python版本检查通过: $python_version${NC}"

# 检查Docker
echo -e "${YELLOW}🐳 检查Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装，请先安装Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker检查通过${NC}"

# 安装Python依赖
echo -e "${YELLOW}📦 安装Python依赖...${NC}"
pip install -r requirements.txt

# 安装各服务依赖
echo -e "${YELLOW}🔧 安装各微服务依赖...${NC}"
for service in embedding_service llm_gateway decision_engine; do
    echo "安装 $service 依赖..."
    pip install -r services/$service/requirements.txt
done

# 创建环境变量文件
echo -e "${YELLOW}⚙️ 创建环境变量配置文件...${NC}"

# 创建嵌入服务.env文件
if [ ! -f "services/embedding_service/.env" ]; then
    cat > services/embedding_service/.env << EOF
# 嵌入服务配置
DEFAULT_MODEL_NAME=bge-large-zh-v1.5
CPU_FALLBACK_MODEL_NAME=shibing624/text2vec-base-chinese
PORT=8001
LOG_LEVEL=INFO
EOF
    echo "✅ 创建 embedding_service/.env"
fi

# 创建LLM网关.env文件
if [ ! -f "services/llm_gateway/.env" ]; then
    cat > services/llm_gateway/.env << EOF
# LLM网关配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# DeepSeek API配置（请填入您的API Key）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# 可选的其他LLM配置
# OPENAI_API_KEY=sk-your-openai-key
# ANTHROPIC_API_KEY=sk-your-anthropic-key

PORT=8002
LOG_LEVEL=INFO
CACHE_TTL_HOURS=24
EOF
    echo "✅ 创建 llm_gateway/.env"
    echo -e "${YELLOW}⚠️ 请编辑 services/llm_gateway/.env 文件，填入您的 DeepSeek API Key${NC}"
fi

# 创建决策引擎.env文件
if [ ! -f "services/decision_engine/.env" ]; then
    cat > services/decision_engine/.env << EOF
# 决策引擎配置
EMBEDDING_SERVICE_URL=http://localhost:8001/v1/embeddings
LLM_GATEWAY_URL=http://localhost:8002/v1/chat/completions
VECTOR_DB_PATH=./local_db/chroma
DATABASE_URL=postgresql://insightfolio:insightfolio_dev_password@localhost/insightfolio_dev

PORT=8000
LOG_LEVEL=INFO

# RAG配置
RAG_CONTEXT_LIMIT=5
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200

# LLM配置
DEFAULT_MODEL=deepseek-v3
DEFAULT_TEMPERATURE=0.7
EOF
    echo "✅ 创建 decision_engine/.env"
fi

# 启动基础设施
echo -e "${YELLOW}🗄️ 启动基础设施服务 (PostgreSQL + Redis)...${NC}"
docker-compose up -d postgres redis

# 等待数据库启动
echo -e "${YELLOW}⏳ 等待数据库启动...${NC}"
sleep 10

# 初始化数据库
echo -e "${YELLOW}🗃️ 初始化数据库...${NC}"
cd services/decision_engine
if [ ! -d "alembic/versions" ]; then
    mkdir -p alembic/versions
fi

# 创建初始迁移
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
cd ../..

# 创建向量数据库目录
echo -e "${YELLOW}📂 创建向量数据库目录...${NC}"
mkdir -p services/decision_engine/local_db/chroma

# 安装pre-commit hooks
echo -e "${YELLOW}🪝 设置Git hooks...${NC}"
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "✅ Pre-commit hooks已安装"
fi

# 完成提示
echo -e "${GREEN}🎉 开发环境初始化完成！${NC}"
echo ""
echo -e "${YELLOW}📝 下一步操作：${NC}"
echo "1. 编辑 services/llm_gateway/.env 文件，填入您的 DeepSeek API Key"
echo "2. 运行 'honcho start' 启动所有服务"
echo "3. 运行 'python scripts/system_check.py' 验证系统健康状态"
echo "4. 运行 'python scripts/demo_usage.py' 体验基础RAG功能"
echo "5. 运行 'python scripts/update_stock_demo.py' 体验股票分析功能"
echo ""
echo -e "${GREEN}📚 文档指南：${NC}"
echo "- 快速上手: 查看 TECHNICAL_OVERVIEW.md"
echo "- 详细安装: 查看 GETTING_STARTED.md"
echo "- 股票功能: 查看 STOCK_INTEGRATION.md"
echo ""
echo -e "${GREEN}🚀 准备就绪，开始您的AI驱动股票分析之旅吧！${NC}"
