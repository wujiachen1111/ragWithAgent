# 智策 (InsightFolio) 本地开发环境进程配置文件
# 使用 honcho start 命令启动所有服务

# 核心微服务
decision_engine: uvicorn decision_engine.main:app --host 0.0.0.0 --port 8000 --app-dir services/decision_engine --reload
embedding_service: uvicorn embedding_service.main:app --host 0.0.0.0 --port 8001 --app-dir services/embedding_service --reload
llm_gateway: uvicorn llm_gateway.main:app --host 0.0.0.0 --port 8002 --app-dir services/llm_gateway --reload
stock_data_service: uvicorn stock_data_service.main:app --host 0.0.0.0 --port 8003 --app-dir services/stock_data_service --reload
