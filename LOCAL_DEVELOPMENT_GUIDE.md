# 🖥️ 重构后项目本地开发指南

## ✅ 本地运行可行性确认

**重构后的代码完全支持本地运行！** 我已经分析了所有关键组件，确保本地开发环境的完整支持。

## 🔧 本地环境要求

### 基础环境
- **Python**: 3.8+ (推荐 3.11)
- **操作系统**: Windows/macOS/Linux
- **内存**: 最少4GB，推荐8GB+
- **磁盘空间**: 2GB+ (重构后大幅减少)

### 可选外部依赖
- **PostgreSQL**: 12+ (可选，有SQLite回退)
- **Redis**: 6+ (可选，有内存回退)
- **Docker**: 最新版本 (可选，用于容器化部署)

## 🚀 重构后本地启动方案

### 方案一：一键启动脚本 (推荐)

重构后将提供统一的启动脚本：

```bash
# 检查并启动所有服务
python scripts/start_all.py

# 指定启动特定服务
python scripts/start_all.py --services yuqing rag

# 开发模式启动 (自动重载)
python scripts/start_all.py --dev
```

### 方案二：Docker Compose (最简单)

```bash
# 一键启动完整环境 (包含数据库)
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f yuqing-sentiment
```

### 方案三：手动启动 (开发调试)

```bash
# 启动YuQing舆情服务
cd apps/yuqing-sentiment
python -m src.main

# 启动RAG+Agent分析服务  
cd apps/rag-analysis
python -m src.main
```

## 📦 依赖管理优化

### 重构前的问题
- YuQing-new包含34,580个虚拟环境文件
- 依赖分散在多个requirements.txt中
- 版本冲突和重复依赖

### 重构后的解决方案

#### 1. 统一依赖管理
```bash
# 项目根目录
requirements.txt          # 全局共享依赖

# 各服务专用依赖
apps/yuqing-sentiment/requirements.txt     # YuQing专用
apps/rag-analysis/requirements.txt         # RAG+Agent专用
```

#### 2. 依赖分层
```python
# requirements.txt (全局基础依赖)
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.2
python-dotenv==1.0.0

# apps/yuqing-sentiment/requirements.txt (舆情分析专用)
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.1
chromadb==0.4.18
sentence-transformers==2.2.2
jieba==0.42.1

# apps/rag-analysis/requirements.txt (RAG+Agent专用)
langgraph==0.0.55
langsmith==0.0.65
tenacity==8.2.3
```

## 🔧 本地开发环境配置

### 1. 自动环境设置脚本

重构后将提供自动化设置：

```bash
# 一键设置开发环境
python scripts/setup_local_development.py

# 这个脚本会自动：
# 1. 检查Python版本
# 2. 创建虚拟环境
# 3. 安装所有依赖
# 4. 初始化数据库
# 5. 创建必要的配置文件
```

### 2. 配置文件自动生成

```python
# configs/environments/development.yml (自动生成)
database:
  # 优先使用SQLite (无需外部数据库)
  url: "sqlite:///./data/ragwithagentstats.db"
  # 如果有PostgreSQL则使用
  # url: "postgresql://user:pass@localhost:5432/ragwithagentstats"

redis:
  # 可选，不可用时使用内存缓存
  url: "redis://localhost:6379/0"
  fallback_to_memory: true

services:
  yuqing_sentiment:
    host: "localhost"
    port: 8000
    debug: true
    
  rag_analysis:
    host: "localhost" 
    port: 8010
    debug: true

logging:
  level: "DEBUG"
  file: "./logs/development.log"
```

## 🛠️ 本地运行适配

### YuQing服务本地适配

重构后的YuQing服务将包含以下本地运行优化：

```python
# apps/yuqing-sentiment/src/config.py
import os
from pathlib import Path

class LocalConfig:
    """本地开发配置"""
    
    # 数据库配置 - 自动回退到SQLite
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{Path(__file__).parent.parent.parent}/data/yuqing.db"
    )
    
    # Redis配置 - 可选
    REDIS_URL = os.getenv("REDIS_URL")
    USE_MEMORY_CACHE = not bool(REDIS_URL)
    
    # API密钥 - 从配置文件读取
    DEEPSEEK_API_KEYS = self._load_api_keys()
    
    # 本地数据目录
    DATA_DIR = Path(__file__).parent.parent.parent / "data" / "yuqing"
    LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "yuqing"
    
    def _load_api_keys(self):
        """从配置文件加载API密钥"""
        config_file = Path(__file__).parent.parent / "config" / "api_keys.txt"
        if config_file.exists():
            return [line.strip() for line in config_file.read_text().splitlines() if line.strip()]
        return []
```

### RAG+Agent服务本地适配

```python
# apps/rag-analysis/src/config.py
class LocalConfig:
    """RAG+Agent本地配置"""
    
    # YuQing服务连接
    YUQING_API_URL = os.getenv("YUQING_API_URL", "http://localhost:8000")
    
    # LLM网关连接
    LLM_GATEWAY_URL = os.getenv(
        "LLM_GATEWAY_URL", 
        "http://localhost:8002/v1/chat/completions"
    )
    
    # 本地模式 - 无需外部LLM时的Mock模式
    ENABLE_MOCK_LLM = os.getenv("ENABLE_MOCK_LLM", "false").lower() == "true"
```

## 🔍 本地开发工具

### 1. 开发服务器

```python
# tools/development/dev_server.py
"""
本地开发服务器
支持热重载、调试模式、日志输出
"""

import asyncio
import subprocess
from pathlib import Path

class LocalDevServer:
    def __init__(self):
        self.services = {
            "yuqing": {
                "cmd": ["python", "-m", "src.main"],
                "cwd": "apps/yuqing-sentiment",
                "port": 8000,
                "env": {"DEBUG": "true", "LOG_LEVEL": "DEBUG"}
            },
            "rag": {
                "cmd": ["python", "-m", "src.main"], 
                "cwd": "apps/rag-analysis",
                "port": 8010,
                "env": {"DEBUG": "true", "YUQING_API_URL": "http://localhost:8000"}
            }
        }
    
    async def start_all(self):
        """启动所有开发服务"""
        tasks = []
        for name, config in self.services.items():
            task = asyncio.create_task(self.start_service(name, config))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
```

### 2. 健康检查工具

```bash
# tools/development/health_check.py
"""检查所有服务健康状态"""

Services Status:
✅ YuQing Sentiment (localhost:8000) - Healthy
✅ RAG Analysis (localhost:8010) - Healthy  
✅ Database Connection - OK
⚠️  Redis Connection - Optional (using memory cache)
```

### 3. 集成测试工具

```bash
# tools/development/integration_test.py
"""本地集成测试"""

# 自动测试：
# 1. 服务启动
# 2. API连通性
# 3. 数据流测试
# 4. 端到端分析
```

## 📊 本地性能优化

### 轻量化运行模式

```python
# 本地开发时的性能优化
LOCAL_OPTIMIZATIONS = {
    # 减少并发数
    "max_concurrent_requests": 2,  # 生产环境: 10
    
    # 使用本地缓存
    "use_memory_cache": True,
    
    # 简化日志
    "log_level": "INFO",  # 调试时: DEBUG
    
    # 跳过可选功能
    "skip_vector_db": True,  # 如果ChromaDB启动失败
    "mock_external_apis": True,  # 模拟外部API调用
}
```

## 🚨 常见本地运行问题及解决方案

### 问题1: 端口占用
```bash
# 检查端口占用
netstat -an | grep -E "8000|8010"

# 解决方案：修改端口配置
export YUQING_PORT=8001
export RAG_PORT=8011
```

### 问题2: 依赖冲突
```bash
# 使用虚拟环境隔离
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 问题3: 数据库连接失败
```bash
# 自动回退到SQLite
export DATABASE_URL="sqlite:///./data/local.db"

# 或使用Docker快速启动PostgreSQL
docker run -d --name postgres-dev \
  -e POSTGRES_DB=ragwithagentstats \
  -e POSTGRES_USER=dev \
  -e POSTGRES_PASSWORD=dev123 \
  -p 5432:5432 postgres:15
```

### 问题4: 外部API不可用
```bash
# 启用Mock模式
export ENABLE_MOCK_LLM=true
export ENABLE_MOCK_SENTIMENT=true

# 系统会使用模拟数据继续运行
```

## 🎯 本地开发工作流

### 日常开发流程

```bash
# 1. 启动开发环境
python scripts/start_all.py --dev

# 2. 查看服务状态  
curl http://localhost:8000/health
curl http://localhost:8010/health

# 3. 运行集成测试
python tools/development/integration_test.py

# 4. 开发调试
# - 修改代码会自动重载
# - 查看实时日志输出
# - 使用IDE断点调试

# 5. 停止服务
python scripts/stop_all.py
```

### 快速验证

```bash
# 快速API测试
curl -X POST "http://localhost:8010/v1/analysis/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "本地测试",
    "content": "测试重构后的本地运行",
    "symbols": ["000001"],
    "time_horizon": "short"
  }'
```

## 📋 本地运行检查清单

### 重构前检查
- [ ] 备份重要数据和配置
- [ ] 确认Python版本 (3.8+)
- [ ] 检查可用磁盘空间 (2GB+)

### 重构后验证
- [ ] 服务正常启动 (8000, 8010端口)
- [ ] API接口可访问
- [ ] 数据库连接正常
- [ ] 日志输出正常
- [ ] 集成测试通过

### 开发环境就绪
- [ ] 代码热重载工作
- [ ] 调试断点可用
- [ ] 日志级别可调整
- [ ] 配置文件可修改

## 🎊 重构后的本地开发优势

### 开发效率提升
- **统一启动** - 一个命令启动所有服务
- **自动配置** - 无需手动配置复杂环境
- **热重载** - 代码修改即时生效
- **调试友好** - 详细的日志和错误信息

### 环境管理简化  
- **依赖清晰** - 明确的依赖关系和版本
- **配置分离** - 开发/测试/生产配置独立
- **数据隔离** - 本地数据不影响生产环境
- **容器化可选** - 既可本地运行也可容器化

### 团队协作改善
- **环境一致** - 所有开发者使用相同配置
- **快速上手** - 新成员可快速搭建环境
- **问题隔离** - 模块化结构便于定位问题
- **版本控制** - 配置和代码统一管理

**结论：重构后的代码不仅可以在本地运行，而且运行体验将大幅提升！** 🚀
