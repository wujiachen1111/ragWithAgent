FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV STOCK_API_HOST=0.0.0.0
ENV STOCK_API_PORT=8020
ENV MONGO_HOST=localhost
ENV MONGO_DATABASE=stock_db

# 暴露端口
EXPOSE 8020

# 启动命令
CMD ["python", "src/main.py"]
