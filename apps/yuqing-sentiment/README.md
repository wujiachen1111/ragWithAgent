# 新闻舆情分析系统

一个基于AI的新闻舆情分析系统，实时采集分析新闻数据，提供情感分析和实体识别。

## 🌟 系统特性

- **🔍 多源数据采集**: Google News、财联社等多个新闻源
- **🤖 智能AI分析**: 基于DeepSeek大模型的情感分析和实体识别
- **⚡ 10倍并发处理**: 10个API密钥并发分析，大幅提升处理速度
- **🔄 实时自动更新**: 每5分钟自动采集最新新闻
- **📊 综合数据API**: 一键获取完整分析数据（新闻+情感+实体）
- **🌐 RESTful API**: 完整的REST API接口服务

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL 12+
- Redis 6+ (可选)

### 一键安装

1. **环境安装**
```bash
# 安装依赖
pip install -r requirements.txt
```

2. **配置API密钥**
编辑 `config/api_keys.txt`，添加DeepSeek API密钥（每行一个，建议10个）

3. **启动系统**
```bash
# 启动舆情分析服务
python src/main.py
```

4. **访问API文档**
浏览器打开: http://localhost:8000/docs

## 📊 核心API接口

### 🏆 综合数据API（推荐）
获取已分析新闻的完整数据（新闻内容+情感分析+实体识别）
```bash
GET /api/news/comprehensive?hours=24&limit=10&include_entities=true
```

### 📰 新闻API
```bash
# 获取新闻列表
GET /api/news/?limit=20

# 获取单条新闻详情
GET /api/news/{news_id}

# 获取系统统计
GET /api/news/stats

# 财联社专用API
GET /api/news/cailian/latest
POST /api/news/cailian/fetch
GET /api/news/cailian/search?q=关键词
```

### 🧠 分析API
```bash
# 情感分析统计
GET /api/analysis/stats/sentiment?hours=24

# 热门关键词
GET /api/analysis/keywords/trending?limit=20

# 智能热点发现
GET /api/analysis/hotspots/discover?limit=10

# 手动触发分析
POST /api/analysis/analyze/recent
```

### 🎯 实体分析API
```bash
# 公司实体分析
GET /api/entities/companies?limit=20&impact_direction=positive

# 人物实体分析
GET /api/entities/persons?limit=20

# 行业影响分析
GET /api/entities/industries?limit=15

# 关键事件分析
GET /api/entities/events?limit=10

# 实时文本实体提取
POST /api/entities/entities/extract
```

## 📋 返回数据示例

### 综合API返回格式
```json
{
  "data": [
    {
      "news": {
        "id": "新闻ID",
        "title": "新闻标题",
        "content": "新闻内容",
        "source": "来源",
        "published_at": "发布时间"
      },
      "sentiment_analysis": {
        "sentiment_label": "positive|negative|neutral",
        "confidence_score": 0.85,
        "market_impact_level": "high|medium|low",
        "analysis_result": {
          "summary": "分析摘要",
          "keywords": ["关键词"],
          "reasoning": "分析推理"
        }
      },
      "entity_analysis": {
        "companies": [/* 公司实体 */],
        "persons": [/* 人物实体 */],
        "industries": [/* 行业影响 */],
        "events": [/* 关键事件 */]
      }
    }
  ],
  "summary": {
    "total_analyzed": 10,
    "time_range_hours": 24,
    "entity_counts": {
      "companies": 15,
      "persons": 8,
      "industries": 12,
      "events": 6
    }
  }
}
```

## 🏗️ 系统架构

### 技术栈
- **Web框架**: FastAPI
- **数据库**: PostgreSQL
- **向量数据库**: ChromaDB  
- **AI模型**: DeepSeek API
- **缓存**: Redis (可选)
- **前端**: 自动生成的API文档

### 目录结构
```
.
├── src/
│   ├── main.py              # 服务入口
│   └── yuqing/
│       ├── api/             # API路由
│       ├── core/            # 核心配置
│       ├── models/          # 数据模型
│       ├── services/        # 业务服务
│       └── tasks/           # 后台任务
├── config/                  # 配置文件
├── data/                    # 数据存储
├── logs/                    # 日志文件
└── requirements.txt         # Python依赖
```

## 🔧 系统管理

### 启动/停止
```bash
# 启动系统
python src/main.py

# 在终端中按 Ctrl+C 停止服务
```

### 监控状态
```bash
# 查看应用日志
type logs\app.log

# 查看错误日志
type logs\error.log

# 系统状态检查
GET http://localhost:8000/api/news/stats
```

## 🎯 使用场景

### 实时监控
```bash
# 获取最近1小时的重要新闻
GET /api/news/comprehensive?hours=1&limit=10

# 获取情感分析统计
GET /api/analysis/stats/sentiment?hours=1
```

### 市场分析
```bash
# 获取最近24小时的市场新闻分析
GET /api/news/comprehensive?hours=24&limit=50

# 获取正面影响的公司实体
GET /api/entities/companies?impact_direction=positive&limit=20

# 获取行业影响分析
GET /api/entities/industries?limit=15
```

### 热点发现
```bash
# 智能热点发现
GET /api/analysis/hotspots/discover?limit=10&hours=6

# 获取热门关键词
GET /api/analysis/keywords/trending?limit=20&hours=24
```

### 数据研究
```bash
# 获取完整数据（含原始数据）
GET /api/news/comprehensive?include_raw_data=true

# 实时文本实体提取
POST /api/entities/entities/extract
{
  "text": "要分析的新闻文本",
  "enable_sentiment": true
}
```

## ⚡ 性能特性

- **并发处理**: 10个DeepSeek API密钥并发分析
- **智能缓存**: 自动缓存分析结果，避免重复计算
- **增量更新**: 只分析新采集的数据
- **异步处理**: 采集和分析异步进行，不阻塞API查询
- **多源采集**: Google News (RSS) + 财联社 + 智能热点发现
- **实体识别**: 公司、人物、行业、事件四大类实体分析
- **热点发现**: AI驱动的智能热点识别和趋势分析

## 🛠️ 系统功能

### 数据采集
- **Google News RSS**: 实时RSS源采集
- **财联社**: 专业金融新闻采集
- **热点发现**: 多维度热点新闻发现
- **去重机制**: 智能去重，避免重复数据

### AI分析
- **情感分析**: 正面/负面/中性情感判断
- **市场影响**: 高/中/低市场影响评估
- **置信度评分**: AI分析结果置信度
- **关键词提取**: 自动提取新闻关键词

### 实体识别
- **公司实体**: 识别新闻中的公司及其影响
- **人物实体**: 识别重要人物及其作用
- **行业影响**: 分析对不同行业的影响
- **关键事件**: 识别重要事件及其影响

## 📖 详细文档

- **在线API文档**: http://localhost:8000/docs (Swagger UI)
- **系统配置**: `.env` 文件配置说明
- **API测试**: http://localhost:8000/redoc (ReDoc文档)

## 🔍 API端点总览

### 新闻API (8个端点)
- 综合数据API、新闻列表、新闻详情、统计信息
- 财联社专用API：最新、获取、搜索、数据源统计

### 分析API (7个端点)  
- 分析列表、情感统计、时间线、手动分析
- 热门关键词、热点发现、趋势关键词

### 实体API (6个端点)
- 公司、人物、行业、事件实体分析
- 实体提取、统计摘要

### 管理API (2个端点)
- 系统健康检查、配置信息

**总计**: 23个API端点，完整覆盖所有功能模块

## 📞 技术支持

### 🔧 系统监控
- **实时状态**: `GET http://localhost:8000/api/news/stats`
- **应用日志**: `logs/app.log`
- **错误日志**: `logs/error.log`

### 📚 文档资源
- **API文档**: http://localhost:8000/docs (Swagger UI)
- **ReDoc文档**: http://localhost:8000/redoc

### ⚙️ 配置文件
- **环境配置**: `.env` (数据库、API密钥等)
- **API密钥**: `config/api_keys.txt` (DeepSeek密钥)
- **日志配置**: 自动轮转，按日期存储

### 🐛 故障排除
- **数据库连接**: 检查PostgreSQL服务状态
- **API分析**: 验证DeepSeek API密钥有效性  
- **内存使用**: 监控系统资源使用情况
- **端口占用**: 确保8000端口可用

---

*最后更新: 2024年7月*
