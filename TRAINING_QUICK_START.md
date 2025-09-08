# 🎯 A股RAG模型训练 - 快速开始

> **一键训练A股特化对比学习RAG模型，提升15-25%检索精度**

## ⚡ 立即开始

### 🚀 一键训练 (推荐)

```bash
# 进入项目根目录 (如果不在根目录)
# cd path/to/ragWithAgent

# 🔥 一键完成：环境配置 + 模型下载 + 训练 + 评估
python tools/development/quick_train_test.py --full-pipeline
```

**预期效果**：
- ⏱️ **训练时间**: GPU约20-30分钟，CPU约2-3小时
- 🎯 **准确率**: > 90%
- 📈 **性能提升**: 相比基线模型提升15-25%

## 📊 实时监控

```bash
# 训练监控 (另开终端)
tensorboard --logdir logs/tensorboard --port 6006
# 访问: http://localhost:6006
```

## ⚙️ 自定义训练

### 基础参数调整

```bash
# GPU内存充足时 (推荐)
python tools/development/quick_train_test.py --full-pipeline \
    --epochs 20 --batch-size 32

# GPU内存不足时
python tools/development/quick_train_test.py --full-pipeline \
    --batch-size 16

# 高精度长训练
python tools/development/quick_train_test.py --full-pipeline \
    --epochs 30 --learning-rate 2e-5
```

### 训练管理

```bash
# 继续中断的训练
python tools/development/quick_train_test.py --train-only \
    --resume checkpoints/latest_checkpoint.pth

# 仅评估已训练模型
python tools/development/quick_train_test.py --eval-only \
    --model checkpoints/best_model.pth

# 仅环境配置 (首次使用)
python tools/development/quick_train_test.py --setup-only
```

## 🔧 故障排查

### GPU内存不足
```bash
# 方案1: 减小批次大小
python tools/development/quick_train_test.py --full-pipeline --batch-size 8

# 方案2: 使用CPU训练
export CUDA_VISIBLE_DEVICES=""
python tools/development/quick_train_test.py --full-pipeline
```

### 网络连接问题
```bash
# 使用国内镜像
export HF_ENDPOINT=https://hf-mirror.com
python tools/development/quick_train_test.py --full-pipeline
```

### 依赖安装失败
```bash
# 手动安装核心依赖
pip install torch sentence-transformers scikit-learn matplotlib seaborn \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## ✅ 训练成功验证

### 1. 查看训练结果
训练成功会显示：
```
🎉 训练完成！
模型准确率: 0.9231 (92.31%)
相比基线提升: 23.45%
最佳模型: checkpoints/best_model.pth
```

### 2. 检查生成文件
```bash
ls checkpoints/best_model.pth      # 最佳模型
ls results/evaluation_*/           # 评估报告
ls logs/tensorboard/               # 训练日志
```

### 3. 测试模型效果
```bash
# API测试增强RAG
curl -X POST http://localhost:8010/v1/analysis/execute \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "浦发银行业绩预警是利好还是利空？",
    "content": "浦发银行业绩预警，市场情绪复杂",
    "symbols": ["600000"],
    "detect_conflicts": true
  }'
```

## 📋 训练参数说明

| 参数 | 默认值 | 推荐范围 | 说明 |
|------|--------|----------|------|
| `--epochs` | 10 | 10-30 | 训练轮数 |
| `--batch-size` | 32 | 8-64 | 批次大小(根据GPU内存) |
| `--learning-rate` | 5e-5 | 1e-5到1e-4 | 学习率 |

## 📈 预期训练效果

| 配置 | 训练时间 | 预期准确率 | GPU显存需求 |
|------|----------|------------|-------------|
| 默认配置 | 20-30分钟 | 85-90% | 4-6GB |
| 高精度配置 | 40-60分钟 | 90-93% | 6-8GB |
| 最佳配置 | 60-90分钟 | 92-95% | 8-12GB |

## 🎯 训练数据说明

- **样本数量**: 30+ 组A股特化难负样本对
- **覆盖类别**: 8大A股业务场景
- **样本质量**: 精心构建的语义相似但影响相反的样本

### 示例样本
```python
{
    "anchor": "公司发布员工持股计划，激励核心骨干",        # 利好
    "hard_negative": "公司控股股东发布减持计划，拟套现离场", # 利空
    "explanation": "都涉及股权变化，但员工持股为利好，股东减持为利空"
}
```

## 📚 详细文档

- 📖 [完整训练指南](docs/user-guide/RAG_TRAINING_GUIDE.md) - 424行详细文档
- 🚀 [快速开始](docs/user-guide/GETTING_STARTED.md) - 系统快速启动
- 📊 [技术概览](docs/TECHNICAL_OVERVIEW.md) - 技术架构说明
- 🏗️ [架构指南](docs/architecture/) - 系统架构设计

## 🆘 获取帮助

```bash
# 查看详细使用指南
python tools/development/quick_train_test.py --usage

# 查看脚本帮助
python tools/development/training/train_contrastive_rag.py --help

# 系统健康检查
python tools/maintenance/health-check/check_all_services.py
```

---

## 🎉 立即开始训练！

**一键启动命令**：
```bash
python tools/development/quick_train_test.py --full-pipeline
```

**20-30分钟后，您将拥有一个专业的A股特化RAG模型！** 🚀

---

*💡 提示：首次训练会自动下载约1.3GB的BGE模型，请确保网络连接稳定。*
