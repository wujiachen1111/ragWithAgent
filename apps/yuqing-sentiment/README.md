# 新闻舆情分析系统（yuqing-sentiment)

基于 FastAPI 的新闻舆情子系统：采集多源新闻，进行情感与实体分析，并提供可查询的 REST API。

## 环境与安装
- Python 3.10+
- 数据库：PostgreSQL（推荐）；不可用时自动回退至本地 SQLite（data/yuqing_local.db）
- 缓存：Redis 6+（推荐）；不可用时自动回退至进程内内存缓存

安装依赖：
```bash
pip install -r requirements.txt
pip install -r apps/yuqing-sentiment/requirements.txt
```

常用环境变量（.env）
- `DATABASE_URL`（缺省回退 SQLite）
- `REDIS_URL`（默认 redis://localhost:6379/0）
- `ENABLE_VECTOR_FEATURES=1`（启用 ChromaDB 检查与向量能力）
- `DEEPSEEK_API_KEY` 或在 `configs/api_keys.txt` 提供多密钥（每行一个）

## 启动与健康检查
推荐使用统一脚本：
```bash
python start_all.py --services yuqing  # 监听 8000
```
或仅启动本服务：
```bash
cd apps/yuqing-sentiment
PYTHONPATH=./src python -m src.main
# 健康检查
curl http://localhost:8000/health
```

日志：`logs/yuqing/app.log`、`logs/yuqing/error.log`

## 快速体验
```bash
# 1) 写入示例新闻（离线可用）
curl -X POST 'http://localhost:8000/api/news/seed/sample?count=5'

# 2) 最近新闻（纯数组）
curl 'http://localhost:8000/api/news/recent?limit=5'

# 3) 综合数据（新闻 + 可用的情感与实体）
curl 'http://localhost:8000/api/news/comprehensive?hours=24&limit=10&include_entities=true'

# 4) 触发最近新闻分析（后台任务）
curl -X POST 'http://localhost:8000/api/analysis/analyze/recent?hours=24&limit=50'
```

更多接口见：`docs/api/yuqing-sentiment.md`（News / Analysis / Data 分类整理，附 curl 示例）

## 测试
```bash
pytest apps/yuqing-sentiment/tests -q
```

## 说明
- API 同时挂载在 `/api/*` 与 `/api/v1/*` 前缀。
- Chroma/Embedding 为可选依赖，缺失时自动降级，不影响核心采集/分析能力。
- 可通过 `.env` 控制严格模式（例如 `require_external_services=true` 时禁用 SQLite/内存回退）。

