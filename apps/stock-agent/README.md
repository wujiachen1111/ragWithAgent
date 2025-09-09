# Stock Agent - 股票数据获取和分析服务

一个基于 FastAPI 的股票数据获取、存储和查询服务，为 RAG+Agent 系统提供标准化的股票数据接口。

## 🌟 系统特性

- **🔍 多源数据采集**: 整合 akshare、东方财富、腾讯财经等多个数据源
- **📊 完整数据覆盖**: 基本信息、股东信息、K线数据一站式获取
- **🚀 RESTful API**: 标准化的 HTTP API 接口，易于集成
- **🎯 智能查询**: 支持多维度条件查询和过滤
- **📈 实时数据**: 支持实时数据获取和批量处理
- **🔄 MongoDB存储**: 高性能的文档数据库存储
- **📋 完整文档**: 自动生成的 API 文档

## 🚀 快速开始

### 环境要求
- Python 3.9+
- MongoDB 4.4+

### 安装依赖
```bash
cd apps/stock-agent
pip install -r requirements.txt
```

### 配置说明
Stock Agent 使用环境变量进行配置，支持以下配置项：

**数据库配置**（可选，有合理默认值）：
- `MONGO_HOST` - MongoDB主机地址（默认：localhost）
- `MONGO_PORT` - MongoDB端口（默认：27017）
- `MONGO_DATABASE` - 数据库名称（默认：stock_db）

**API配置**（可选）：
- `STOCK_API_PORT` - 服务端口（默认：8020）
- `STOCK_API_DEBUG` - 调试模式（默认：false）

如果需要自定义配置，可以在项目根目录创建 `.env` 文件或设置环境变量。

### 启动服务
```bash
python src/main.py
```

### 访问API文档
浏览器打开: http://localhost:8020/docs

## 📊 核心API接口

### 🔍 股票查询
```bash
# 查询股票列表（支持多维度筛选）
GET /api/v1/stocks/?industries=银行&min_market_cap=100

# 获取单只股票详情
GET /api/v1/stocks/000001

# 获取所有股票代码
GET /api/v1/stocks/codes/all
```

### 🏢 行业和地区
```bash
# 获取所有行业
GET /api/v1/stocks/industries/all

# 获取所有地区
GET /api/v1/stocks/areas/all

# 获取指定行业的股票代码
GET /api/v1/stocks/industry/银行/codes
```

### 📈 数据采集
```bash
# 获取单只股票数据
POST /api/v1/stocks/fetch/single?stock_code=000001

# 批量获取股票数据
POST /api/v1/stocks/fetch/batch
{
  "stock_codes": ["000001", "600000"],
  "batch_size": 50
}
```

### 📊 统计信息
```bash
# 数据库统计
GET /api/v1/stocks/stats/database

# 健康检查
GET /api/v1/stocks/health
```

## 🏗️ 系统架构

### 技术栈
- **Web框架**: FastAPI
- **数据库**: MongoDB
- **数据源**: akshare, 东方财富, 腾讯财经
- **日志**: loguru
- **配置管理**: pydantic-settings

### 目录结构
```
apps/stock-agent/
├── src/
│   ├── stock/
│   │   ├── api/              # API路由
│   │   │   └── stock_api.py
│   │   ├── core/             # 核心配置
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging.py
│   │   ├── models/           # 数据模型
│   │   │   └── base.py
│   │   ├── services/         # 业务服务
│   │   │   ├── data_fetcher.py
│   │   │   └── stock_service.py
│   │   └── utils/            # 工具函数
│   │       └── helpers.py
│   └── main.py               # 服务入口
├── config/                   # 配置文件
├── tests/                    # 测试文件
├── requirements.txt          # Python依赖
├── Dockerfile               # Docker配置
└── README.md               # 文档
```

## 🔗 与 RAG-Analysis 系统集成

Stock Agent 专为与 RAG-Analysis 系统集成而设计，提供标准化的股票数据接口。

### 集成方式

1. **服务发现**: RAG-Analysis 通过配置的服务地址调用 Stock Agent
2. **数据标准**: 统一的 JSON 数据格式，便于 LLM 处理
3. **错误处理**: 完善的错误处理和重试机制
4. **性能优化**: 支持批量查询和缓存机制

### 在 RAG-Analysis 中使用

```python
import httpx

# 查询银行行业股票
async def get_bank_stocks():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8020/api/v1/stocks/",
            params={"industries": ["银行"], "min_market_cap": 100}
        )
        return response.json()

# 获取特定股票数据
async def get_stock_data(stock_code: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8020/api/v1/stocks/{stock_code}"
        )
        return response.json()
```

## 📋 数据模型

### 股票基本信息
```json
{
  "stock_name": "平安银行",
  "latest_price": 12.50,
  "pe_ttm": 5.2,
  "pb": 0.8,
  "total_market_cap": 2420.5,
  "industry": "银行",
  "area": "广东",
  "roe": 12.5,
  "eps": 2.4
}
```

### 股东信息
```json
[
  {
    "holder_name": "中国平安保险集团股份有限公司",
    "shares": 11500000000,
    "ratio": 59.2,
    "holder_type": "机构",
    "report_date": "20240331"
  }
]
```

### K线数据
```json
[
  {
    "date": "2024-01-15",
    "open": 12.30,
    "high": 12.65,
    "low": 12.20,
    "close": 12.50,
    "volume": 15420.5,
    "change": 0.20,
    "change_pct": 1.63
  }
]
```

## 📖 详细使用说明

请查看 [USAGE.md](USAGE.md) 获取详细的使用说明和配置选项。

## 🚀 部署

### Docker 部署
```bash
# 构建镜像
docker build -t stock-agent .

# 运行容器
docker run -p 8020:8020 -e MONGO_HOST=host.docker.internal stock-agent
```

### 生产环境
```bash
# 使用 gunicorn 部署
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app --bind 0.0.0.0:8020
```

## 📊 监控和日志

### 日志配置
- 控制台日志: INFO 级别，彩色输出
- 文件日志: `logs/stock_agent.log` (轮转存储)
- 错误日志: `logs/stock_agent_error.log` (仅错误)

### 健康检查
```bash
# 检查服务状态
curl http://localhost:8020/api/v1/stocks/health

# 检查数据库统计
curl http://localhost:8020/api/v1/stocks/stats/database
```

## 🤝 集成示例

### 与 RAG-Analysis 集成示例
```python
# 在 RAG-Analysis 的数据获取服务中
class StockDataClient:
    def __init__(self):
        self.base_url = "http://localhost:8020/api/v1"
    
    async def get_industry_analysis(self, industry: str):
        """获取行业分析数据"""
        async with httpx.AsyncClient() as client:
            # 获取行业股票列表
            stocks = await client.get(
                f"{self.base_url}/stocks/",
                params={"industries": [industry], "limit": 50}
            )
            
            return stocks.json()
    
    async def get_stock_fundamentals(self, stock_code: str):
        """获取股票基本面数据"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/stocks/{stock_code}"
            )
            return response.json()
```

## 🔍 故障排除

### 常见问题
1. **数据库连接失败**: 检查 MongoDB 服务状态和连接配置
2. **数据获取超时**: 调整 `request_timeout` 配置
3. **API 限频**: 增加 `request_delay` 间隔时间
4. **内存不足**: 减小 `batch_size` 批处理大小

### 性能优化
- 使用数据库索引加速查询
- 合理设置批处理大小
- 启用请求缓存
- 使用连接池

## 📞 技术支持

- **API 文档**: http://localhost:8020/docs
- **服务状态**: http://localhost:8020/api/v1/stocks/health
- **日志文件**: `logs/stock_agent.log`
