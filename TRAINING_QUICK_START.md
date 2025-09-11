# 🎯 A股RAG模型训练 - 快速开始

> **一键训练A股特化对比学习RAG模型，可将特定场景检索精度提升15-25%**

## 📚 环境准备 (重要)

在开始之前，请确保您的开发环境满足以下要求：

1.  **Python 版本**:
    -   请确保已安装 Python `3.8` 或更高版本。

2.  **创建虚拟环境 (强烈推荐)**:
    -   为了隔离项目依赖，避免与系统或其他项目产生冲突，建议创建一个虚拟环境。
    ```bash
    # 1. 创建虚拟环境
    python -m venv venv

    # 2. 激活虚拟环境
    # Windows
    # venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **网络环境**:
    -   首次训练会自动下载约 **1.3GB** 的预训练模型 (`BAAI/bge-large-zh-v1.5`)，请确保网络连接稳定。
    -   如果下载速度慢，可使用国内镜像源：`export HF_ENDPOINT=https://hf-mirror.com`

## ⚡ 快速训练

### 🚀 一键启动 (推荐)

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

# CPU训练 (较慢)
export CUDA_VISIBLE_DEVICES=""
python tools/development/quick_train_test.py --full-pipeline --batch-size 8
```

### Apple Silicon (M系列芯片) Mac 用户
对于使用M1/M2/M3等芯片的Mac用户，代码已进行适配以支持GPU加速。
- **设备**: 训练将自动尝试使用 `mps` (Metal Performance Shaders)。
- **性能**: 相比CPU有显著提升，但可能仍慢于同级别NVIDIA GPU。
- **建议**:
  - 使用较小的批次大小 (`--batch-size 8` 或 `16`) 开始。
  - 如果遇到 `RuntimeError: MPS backend out of memory`，请进一步减小批次大小。

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

- 🚀 [快速开始指南](docs/user-guide/GETTING_STARTED.md) - 系统快速启动
- 🏗️ [架构设计规划](docs/architecture/plan.md) - 系统架构设计

## 🆘 获取帮助

```
```