# YuQing Sentiment API 参考

基地址：`http://localhost:8000`（同时提供 `/api/*` 与 `/api/v1/*` 路径别名）

## 健康检查
- GET `/health` → `{status, database, redis, chroma, version}`

## News（新闻）
- GET `/api/news/recent?limit=5`
  - 返回最近新闻“数组”，用于快速校验/展示。
- GET `/api/news/?page=1&limit=20&source=&hours=24&keyword=`
  - 返回 `{data, pagination}`；按 `published_at` 降序。
- GET `/api/news/stats?hours=24`
- GET `/api/news/sources/stats?hours=24`
- GET `/api/news/{news_id}`
- POST `/api/news/seed/sample?count=5`
  - 无外网/离线时快速写入示例新闻。
- POST `/api/news/seed/cailian?limit=50`
- GET `/api/news/cailian/latest?days=1&limit=50&important=false`
- POST `/api/news/cailian/fetch?limit=100`
- GET `/api/news/cailian/search?keyword=芯片&limit=20`

示例：
```bash
curl 'http://localhost:8000/api/news/recent?limit=3'
curl -X POST 'http://localhost:8000/api/news/seed/sample?count=5'
```

## Analysis（分析/情感与实体）
- GET `/api/analysis/?page=1&limit=20&sentiment=&impact=&hours=24`
- GET `/api/analysis/stats/sentiment?hours=24`
- GET `/api/analysis/stats/timeline?hours=24&interval=1`
- POST `/api/analysis/analyze/recent?hours=24&limit=50`
- GET `/api/analysis/keywords/trending?hours=24&limit=20`
- GET `/api/analysis/hotspots/discover?hours=6&limit=30`
- GET `/api/analysis/hotspots/trending-keywords?limit=20`

实体分析（挂载在 `/api/analysis/*`）
- GET `/api/analysis/companies?limit=50&offset=0&company_name=&impact_direction=&min_impact=0.0&days=7`
- GET `/api/analysis/persons?limit=50&offset=0&person_name=&influence_level=&min_influence=0.0&days=7`
- GET `/api/analysis/industries?limit=50&offset=0&industry_name=&impact_direction=&min_impact=0.0&days=7`
- GET `/api/analysis/events?limit=50&offset=0&event_type=&market_significance=&days=7`
- POST `/api/analysis/entities/extract?news_id={id}`
- GET `/api/analysis/entities/summary?days=7`

示例：
```bash
# 触发最近新闻分析（后台执行）
curl -X POST 'http://localhost:8000/api/analysis/analyze/recent?hours=24&limit=50'
# 获取实体统计摘要
curl 'http://localhost:8000/api/analysis/entities/summary?days=7'
```

## Data（采集与运维）
- POST `/api/data/collect/all?analyze=false`  
  仅采集或采集+分析（后台任务）
- POST `/api/data/collect/analyze`  
  触发采集并自动实体分析（后台任务）
- POST `/api/data/analyze/recent?hours_back=1&source=&limit=20`
- POST `/api/data/collect/keywords`（JSON: `{keywords:[], sources?:[]}`）
- POST `/api/data/collect/companies`（JSON: `{companies:[], sources?:[]}`）
- GET `/api/data/status`
- POST `/api/data/cleanup?days_to_keep=30`
- POST `/api/data/cleanup/legacy?days_to_keep=3`
- GET `/api/data/stats/database`

示例：
```bash
curl -X POST 'http://localhost:8000/api/data/collect/all?analyze=false'
curl 'http://localhost:8000/api/data/status'
```

## 备注
- 模型字段以 `apps/yuqing-sentiment/src/yuqing/models/database_models.py` 为准。
- 非关键外部依赖（Chroma/Transformers/akshare）缺失时会自动降级，不影响核心接口可用性。

