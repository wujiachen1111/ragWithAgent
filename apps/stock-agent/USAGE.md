# Stock Agent 使用说明

## 🚀 快速启动

### 1. 安装依赖
```bash
cd apps/stock-agent
pip install -r requirements.txt
```

### 2. 启动服务
```bash
python src/main.py
```

服务将在 http://localhost:8020 启动，API文档可在 http://localhost:8020/docs 查看。

## ⚙️ MongoDB 配置

Stock Agent 需要连接 MongoDB 数据库，支持有认证和无认证两种模式：

### 无认证模式（适合本地开发）
```bash
# 项目根目录 .env 文件
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=stock_db
```

### 有认证模式（推荐用于生产环境）
```bash
# 方式一：分别配置
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=stock_db
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
MONGO_AUTH_SOURCE=admin

# 方式二：使用完整URI（推荐）
MONGO_URI=mongodb://username:password@localhost:27017/stock_db?authSource=admin
```

### API服务配置
- `STOCK_API_PORT=8020` - 服务端口
- `STOCK_API_DEBUG=false` - 调试模式

> 📖 详细的MongoDB配置说明请参考 [MONGODB_CONFIG.md](MONGODB_CONFIG.md)

## 🔧 自定义配置

如果需要自定义配置，可以：

### 方法1：在项目根目录创建 .env 文件
```bash
# 在项目根目录创建 .env 文件
cd ../../  # 回到项目根目录
cat > .env << EOF
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=rag_agent_db
STOCK_API_PORT=8020
EOF
```

### 方法2：设置环境变量
```bash
export MONGO_HOST=your-mongodb-host
export MONGO_DATABASE=your-database
python src/main.py
```

## 📊 API 接口

启动服务后，可以使用以下主要接口：

- `GET /api/v1/stocks/health` - 健康检查
- `GET /api/v1/stocks/` - 查询股票列表
- `GET /api/v1/stocks/{code}` - 获取单只股票详情
- `POST /api/v1/rag/market-context` - 获取市场上下文（RAG集成）

完整的API文档请访问：http://localhost:8020/docs

## 🔗 与 RAG-Analysis 集成

Stock Agent 提供专门的RAG集成接口，RAG-Analysis 系统可以通过以下方式调用：

```python
import httpx

async def get_stock_data():
    async with httpx.AsyncClient() as client:
        # 获取股票数据
        response = await client.get("http://localhost:8020/api/v1/stocks/000001")
        return response.json()
```

## 🐛 故障排除

1. **服务无法启动** - 检查端口8020是否被占用
2. **数据库连接失败** - 确保MongoDB服务正在运行
3. **API调用失败** - 检查服务是否正常启动，访问健康检查接口
