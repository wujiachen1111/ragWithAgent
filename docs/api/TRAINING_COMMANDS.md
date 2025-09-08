# 🎯 A股RAG训练命令速查表

## 🔍 环境检查

```bash
# 验证训练环境完整性
python tools/development/testing/validate_training_system.py

# 检查系统健康状态  
python tools/maintenance/health-check/check_all_services.py
```

## 🚀 训练命令

### 完整训练流程

```bash
# 🔥 一键训练 (推荐新手)
python tools/development/quick_train_test.py --full-pipeline

# 查看详细使用指南
python tools/development/quick_train_test.py --usage
```

### 分步骤执行

```bash
# 1. 仅配置环境
python tools/development/quick_train_test.py --setup-only

# 2. 仅训练模型 (使用默认参数)
python tools/development/quick_train_test.py --train-only

# 3. 仅评估模型
python tools/development/quick_train_test.py --eval-only --model checkpoints/best_model.pth
```

### 自定义参数训练

```bash
# GPU内存充足时 (推荐)
python tools/development/quick_train_test.py --full-pipeline \
    --epochs 20 --batch-size 32 --learning-rate 5e-5

# GPU内存不足时
python tools/development/quick_train_test.py --full-pipeline \
    --epochs 15 --batch-size 16

# 高精度长训练
python tools/development/quick_train_test.py --full-pipeline \
    --epochs 30 --batch-size 16 --learning-rate 2e-5

# CPU训练 (较慢)
export CUDA_VISIBLE_DEVICES=""
python tools/development/quick_train_test.py --full-pipeline --batch-size 8
```

### 继续训练

```bash
# 从最新检查点继续
python tools/development/quick_train_test.py --train-only \
    --resume checkpoints/latest_checkpoint.pth

# 从指定检查点继续  
python tools/development/quick_train_test.py --train-only \
    --resume checkpoints/checkpoint_epoch_10.pth
```

## 📊 监控和评估

### 训练监控

```bash
# 启动TensorBoard监控
tensorboard --logdir logs/tensorboard --port 6006
# 访问: http://localhost:6006

# 查看训练日志
tail -f logs/training.log
```

### 模型评估

```bash
# 评估最佳模型
python tools/development/testing/evaluate_rag_performance.py \
    --model checkpoints/best_model.pth \
    --output results/evaluation_$(date +%Y%m%d_%H%M%S)

# 评估指定模型
python tools/development/testing/evaluate_rag_performance.py \
    --model checkpoints/checkpoint_epoch_15.pth
```

### 效果演示

```bash
# 训练效果对比演示
python tools/development/testing/demo_trained_model.py

# 指定模型演示
python tools/development/testing/demo_trained_model.py \
    --model checkpoints/best_model.pth
```

## 🔧 高级训练

### 直接调用训练脚本

```bash
# 使用自定义配置文件
python tools/development/training/train_contrastive_rag.py \
    --config configs/training/custom_config.yaml

# 指定GPU
python tools/development/training/train_contrastive_rag.py \
    --config configs/training/contrastive_training.yaml \
    --gpu 0

# 从检查点恢复
python tools/development/training/train_contrastive_rag.py \
    --config configs/training/contrastive_training.yaml \
    --resume checkpoints/checkpoint_epoch_5.pth
```

### 环境配置脚本

```bash
# 完整环境配置
python tools/development/setup/setup_training_environment.py

# 强制重新下载模型
python tools/development/setup/setup_training_environment.py --force-download

# 仅检查环境
python tools/development/setup/setup_training_environment.py --check-only
```

## 🎯 快速开始流程

对于新手，推荐按以下顺序执行：

```bash
# 1. 环境检查
python tools/development/testing/validate_training_system.py

# 2. 一键训练 (如果环境检查通过)
python tools/development/quick_train_test.py --full-pipeline

# 3. 效果演示 (训练完成后)
python tools/development/testing/demo_trained_model.py
```

## 📋 参数说明

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `--epochs` | 10 | 5-50 | 训练轮数 |
| `--batch-size` | 32 | 4-128 | 批次大小 |
| `--learning-rate` | 5e-5 | 1e-6 到 1e-3 | 学习率 |

## 🔧 故障排查

### 常见问题解决

```bash
# GPU内存不足
python tools/development/quick_train_test.py --full-pipeline --batch-size 8

# 网络下载慢
export HF_ENDPOINT=https://hf-mirror.com
python tools/development/quick_train_test.py --full-pipeline

# 依赖安装失败
pip install torch sentence-transformers scikit-learn matplotlib seaborn \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 权限问题
sudo chown -R $USER:$USER checkpoints/ logs/ results/
```

### 清理和重置

```bash
# 清理检查点
rm -rf checkpoints/*

# 清理日志
rm -rf logs/tensorboard/*

# 清理结果
rm -rf results/*

# 完全重置训练环境
rm -rf checkpoints/ logs/ results/ models/ .cache/
```

## 📈 性能基准

| 配置 | GPU | 训练时间 | 预期准确率 | 显存需求 |
|------|-----|----------|------------|----------|
| 默认 | RTX 3080 | 25分钟 | 85-90% | 4-6GB |
| 高精度 | RTX 3080 | 50分钟 | 90-93% | 6-8GB |
| 最佳 | RTX 4090 | 30分钟 | 92-95% | 8-12GB |
| CPU | - | 3小时 | 85-90% | 8GB RAM |

## 🆘 获取帮助

```bash
# 查看脚本帮助
python tools/development/quick_train_test.py --help
python tools/development/training/train_contrastive_rag.py --help
python tools/development/testing/evaluate_rag_performance.py --help

# 查看使用指南
python tools/development/quick_train_test.py --usage
```

---

💡 **提示**: 所有命令都应在项目根目录执行，首次训练建议使用默认参数。
