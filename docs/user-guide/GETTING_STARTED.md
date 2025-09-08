# 🚀 快速开始指南

欢迎使用智策 (InsightFolio)！这份指南将帮助您快速启动系统。

## 📋 系统要求

### 基础要求
- **Python**: 3.10+
- **内存**: 至少 8GB RAM
- **磁盘**: 至少 5GB 可用空间
- **Docker**: 最新版本
- **DeepSeek API Key**: 用于`rag-analysis`服务

### GPU加速训练 (可选)
- **NVIDIA GPU**: 8GB+ 显存推荐
- **CUDA**: 11.8+ 或 12.0+

## 🚀 完整系统启动 (推荐)

这是启动完整微服务系统（`yuqing-sentiment` 和 `rag-analysis`）的最快方式。

```bash
# 1. (首次运行) 安装全局依赖
pip install -r requirements.txt

# 2. 启动Docker基础设施 (数据库, 缓存等)
docker-compose up -d

# 3. 配置API密钥
#    - 编辑 apps/yuqing-sentiment/config/api_keys.txt 添加DeepSeek密钥
#    - 为 rag-analysis 服务设置环境变量或配置文件 (参见该服务的README)

# 4. 启动所有应用服务
python scripts/start_all.py
```

**验证系统运行:**
```bash
# 检查 yuqing-sentiment 服务
curl http://localhost:8000/health

# 检查 rag-analysis 服务
curl http://localhost:8010/
```

## 🔬 RAG模型训练 (可选)

如果您想训练针对A股优化的RAG模型：

```bash
# 🔥 一键训练: 环境配置 + 模型下载 + 训练 + 评估
python tools/development/quick_train_test.py --full-pipeline

# 实时监控训练过程 (在另一个终端中运行)
tensorboard --logdir logs/tensorboard --port 6006
```
> 详细的训练指南请参考 `TRAINING_QUICK_START.md`。

## 🔧 手动启动 (用于开发调试)

如果您想单独启动某个服务进行开发：

### 1. 启动基础设施
```bash
docker-compose up -d
```

### 2. 启动 `yuqing-sentiment` 服务
```bash
cd apps/yuqing-sentiment
pip install -r requirements.txt # (首次)
python src/main.py
```

### 3. 启动 `rag-analysis` 服务
```bash
cd apps/rag-analysis
pip install -r requirements.txt # (首次)
# 设置必要的环境变量, 例如 YUQING_API_URL
export YUQING_API_URL="http://localhost:8000"
python src/main.py
```

## 🧪 验证系统运行

### 1. 检查服务健康状态
- **yuqing-sentiment**: `http://localhost:8000/health`
- **rag-analysis**: `http://localhost:8010/`

### 2. 运行集成演示
```bash
# 运行演示脚本
python tools/development/yuqing_integration_demo.py
```

### 3. 手动API测试
```bash
# 测试 rag-analysis 服务
curl -X POST "http://localhost:8010/v1/analysis/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "最近科技股的投资机会如何？",
    "content": "多家公司发布财报",
    "symbols": ["000001"]
  }'
```

## 🔍 故障排除

**Q: 服务启动失败?**
- **检查端口占用**: 确保 `8000` 和 `8010` 端口未被占用。
- **检查Docker**: 确认Docker正在运行 (`docker ps`)。
- **检查依赖**: 确保每个服务的 `requirements.txt` 已被安装。

**Q: API调用失败?**
- **检查服务日志**: 查看 `logs/` 目录下对应服务的日志文件。
- **检查API密钥**: 确认DeepSeek API密钥已正确配置。

## 📖 下一步

- **舆情服务**: 查看 `apps/yuqing-sentiment/README.md` 了解其API和功能。
- **RAG分析服务**: 查看 `apps/rag-analysis/README.md` 了解其Agent架构和API。
- **模型训练**: 参考 `TRAINING_QUICK_START.md` 进行模型训练和优化。

---

**🎉 恭喜！您已成功启动专业的A股RAG分析系统！**
