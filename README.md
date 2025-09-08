# 🏛️ 智策 (InsightFolio) - 企业级股票舆情分析平台

> **基于领域驱动设计(DDD)的微服务架构 + RAG+Agent智能分析技术**

## 🎯 项目概述

智策是一个采用**企业级架构标准**构建的股票舆情分析平台，集成了**检索增强生成(RAG)**、**智能代理(Agent)**和**对比学习增强**技术，为投资决策提供专业、准确、实时的智能分析服务。

### 🔥 核心优势
- **🏗️ 企业级架构**: 基于DDD和微服务的标准化架构设计
- **🎯 A股特化**: 专门针对A股市场优化的对比学习RAG技术  
- **📊 15-25%精度提升**: 相比标准RAG的显著性能提升
- **🔍 语义冲突检测**: 自动识别相似语义但相反影响的信息
- **⚡ 高可扩展**: 模块化设计支持快速功能扩展

## 🏗️ 系统架构

### 微服务域架构
```
┌─────────────────────────────────────────────────────────────────────┐
│                           API Gateway                               │
│                     统一入口 • 路由 • 安全                         │
└─────┬─────────────┬─────────────┬─────────────┬─────────────┬───────┘
      │             │             │             │             │
┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│ 🧠 核心域  │ │ 📊 数据域  │ │ 💡 智能域  │ │ 🔌 网关域  │ │ 🔗 共享域  │
├───────────┤ ├───────────┤ ├───────────┤ ├───────────┤ ├───────────┤
│决策引擎   │ │股票数据   │ │LLM网关    │ │API网关    │ │通用组件   │
│分析编排   │ │舆情数据   │ │嵌入服务   │ │认证服务   │ │数据库     │
│           │ │知识库     │ │对比RAG    │ │           │ │消息队列   │
└───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

### 技术栈概览
- **语言框架**: Python 3.10+ + FastAPI + Pydantic
- **AI技术**: LangChain + DeepSeek v3 + BGE-Large-ZH + PyTorch
- **数据存储**: PostgreSQL + ChromaDB + Redis + ClickHouse
- **基础设施**: Docker + Kubernetes + Prometheus + Grafana
- **消息队列**: Celery + RabbitMQ
- **服务网格**: Istio (可选)

## 📁 项目结构

```
InsightFolio/
├── 📖 docs/                          # 文档中心
│   ├── architecture/                 # 架构文档
│   ├── api/                          # API文档  
│   ├── deployment/                   # 部署文档
│   ├── user-guide/                   # 用户指南
│   └── development/                  # 开发文档
│
├── 🔧 apps/                          # 应用服务
│   ├── yuqing-sentiment/             # 舆情分析服务
│   │   ├── src/                     # 源代码
│   │   ├── tests/                   # 测试
│   │   ├── requirements.txt         # 依赖
│   │   └── Dockerfile               # 容器化
│   │
│   └── rag-analysis/                # RAG分析服务
│       ├── src/                     # 源代码
│       ├── tests/                   # 测试
│       ├── requirements.txt         # 依赖
│       └── Dockerfile               # 容器化
│
├── 🔗 libs/                         # 共享库
│   ├── common/                       # 通用组件
│   ├── database/                     # 数据库共享
│   └── messaging/                    # 消息队列
│
├── 🏗️ infrastructure/               # 基础设施
│   ├── docker/                       # Docker配置
│   ├── kubernetes/                   # K8s配置
│   ├── terraform/                    # 基础设施即代码
│   └── monitoring/                   # 监控基础设施
│
├── 🛠️ tools/                        # 工具脚本
│   ├── development/                  # 开发工具
│   ├── deployment/                   # 部署工具
│   └── maintenance/                  # 运维工具
│
├── ⚙️ configs/                      # 配置中心
│   ├── environments/                 # 环境配置
│   └── services/                     # 服务配置
│
└── 🚀 deployments/                  # 部署配置
    ├── local/                        # 本地部署
    ├── development/                  # 开发环境
    ├── staging/                      # 测试环境
    └── production/                   # 生产环境
```

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd InsightFolio

# 安装基础依赖
pip install -r requirements.txt

# 安装服务依赖
pip install -r apps/yuqing-sentiment/requirements.txt
pip install -r apps/rag-analysis/requirements.txt
```

### 2. 基础设施启动
```bash
# 启动数据库和缓存
docker-compose up -d postgres redis

# 初始化数据库
python tools/deployment/migration/init_databases.py
```

### 3. 服务启动
```bash
# 方式1: 使用Docker Compose启动所有服务
docker-compose up -d

# 方式2: 分别启动各个服务
# 舆情分析服务
cd apps/yuqing-sentiment
python -m src.main

# RAG分析服务
cd apps/rag-analysis
python -m src.main
```

### 4. 验证系统
```bash
# 检查舆情分析服务状态
curl http://localhost:8000/health

# 检查RAG分析服务状态
curl http://localhost:8010/meta
```

## 📊 API使用指南

### 舆情分析服务

```python
import httpx

# 基础URL
BASE_URL = "http://localhost:8000/api"

async with httpx.AsyncClient() as client:
    # 获取新闻数据
    response = await client.get(f"{BASE_URL}/news/recent")
    news = response.json()
    print(f"最近新闻: {news}")
    
    # 获取情感分析
    response = await client.get(f"{BASE_URL}/sentiment/stock/600000")
    sentiment = response.json()
    print(f"舆情分析: {sentiment}")
```

### RAG分析服务

```python
import httpx

# 基础URL
BASE_URL = "http://localhost:8010/api"

async with httpx.AsyncClient() as client:
    # RAG分析
    response = await client.post(f"{BASE_URL}/analysis/rag", 
                               json={
                                   "query": "浦发银行业绩预警是利好还是利空？",
                                   "detect_conflicts": True
                               })
    result = response.json()
    print(f"RAG分析: {result}")
```

## 🔧 开发指南

### 服务开发规范
- **目录结构**: 严格按照DDD分层架构组织代码
- **API设计**: 遵循RESTful设计原则和OpenAPI规范
- **数据模型**: 使用Pydantic进行数据验证
- **测试覆盖**: 单元测试覆盖率 > 80%

### 代码质量
```bash
# 代码格式化
black apps/ libs/ tools/

# 代码检查  
ruff check apps/ libs/ tools/

# 类型检查
mypy apps/ libs/
```

## 📊 监控和运维

### 系统监控
- **指标监控**: Prometheus + Grafana
- **日志聚合**: ELK Stack (Elasticsearch + Logstash + Kibana)
- **链路追踪**: Jaeger分布式追踪
- **告警通知**: AlertManager + 微信/邮件通知

### 健康检查
```bash
# 检查所有服务状态
python tools/maintenance/health-check/check_all_services.py

# 检查特定服务
curl http://localhost:8000/health
curl http://localhost:8010/meta
```

## 🛠️ 部署方案

### 本地开发
- **数据库**: Docker Compose
- **服务启动**: 直接运行Python脚本
- **配置管理**: 本地.env文件

### 生产环境
- **容器编排**: Kubernetes
- **服务网格**: Istio (可选)
- **数据库**: 托管数据库服务
- **监控**: 完整的监控栈

## 📚 文档体系

| 文档类型 | 位置 | 用途 |
|---------|------|------|
| **架构文档** | `docs/architecture/` | 系统架构设计和技术决策 |
| **API文档** | `docs/api/` | 接口文档和使用指南 |
| **用户指南** | `docs/user-guide/` | 功能使用说明 |
| **开发文档** | `docs/development/` | 开发规范和最佳实践 |
| **部署文档** | `docs/deployment/` | 部署和运维指南 |

---

**🏛️ 智策(InsightFolio) - 企业级架构 + AI智能分析 = 专业投资决策平台！** 🚀
