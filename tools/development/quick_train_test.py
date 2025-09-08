#!/usr/bin/env python3
"""
A股RAG对比学习快速训练和测试脚本
一键完成环境配置、模型训练、性能评估的完整流程
"""

import os
import sys
import subprocess
from pathlib import Path
import logging
import argparse
from datetime import datetime
import json
from typing import Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickTrainer:
    """快速训练管理器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.tools_dir = self.project_root / "tools"
        
        # 脚本路径
        self.setup_script = self.tools_dir / "development" / "setup" / "setup_training_environment.py"
        self.train_script = self.tools_dir / "development" / "training" / "train_contrastive_rag.py"
        self.eval_script = self.tools_dir / "development" / "testing" / "evaluate_rag_performance.py"
        
        # 配置路径
        self.config_dir = self.project_root / "configs" / "training"
        self.config_file = self.config_dir / "contrastive_training.yaml"
        
        # 输出路径
        self.checkpoint_dir = self.project_root / "checkpoints"
        self.results_dir = self.project_root / "results"
        
    def check_prerequisites(self) -> bool:
        """检查前置条件"""
        logger.info("🔍 检查前置条件...")
        
        # 检查脚本文件
        required_scripts = [self.setup_script, self.train_script, self.eval_script]
        missing_scripts = []
        
        for script in required_scripts:
            if not script.exists():
                missing_scripts.append(str(script))
        
        if missing_scripts:
            logger.error(f"缺少必要脚本文件: {missing_scripts}")
            return False
        
        # 检查样本数据
        samples_file = self.project_root / "services" / "decision_engine" / "contrastive_learning_samples.py"
        if not samples_file.exists():
            logger.error(f"缺少训练样本文件: {samples_file}")
            return False
        
        logger.info("✅ 前置条件检查通过")
        return True
    
    def setup_environment(self, force_download: bool = False) -> bool:
        """配置训练环境"""
        logger.info("🔧 配置训练环境...")
        
        try:
            cmd = [sys.executable, str(self.setup_script)]
            if force_download:
                cmd.append("--force-download")
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                logger.info("✅ 环境配置成功")
                logger.info(result.stdout)
                return True
            else:
                logger.error("❌ 环境配置失败")
                logger.error(result.stderr)
                return False
                
        except Exception as e:
            logger.error(f"环境配置异常: {e}")
            return False
    
    def run_training(self, epochs: int = 10, batch_size: int = 32, 
                    learning_rate: float = 5e-5, resume: str = None) -> Tuple[bool, str]:
        """运行训练"""
        logger.info(f"🚀 开始训练模型 (epochs={epochs}, batch_size={batch_size}, lr={learning_rate})...")
        
        try:
            # 确保配置文件存在
            if not self.config_file.exists():
                logger.warning("配置文件不存在，使用默认配置")
                self._create_default_config(epochs, batch_size, learning_rate)
            
            cmd = [sys.executable, str(self.train_script), "--config", str(self.config_file)]
            if resume:
                cmd.extend(["--resume", resume])
            
            # 运行训练
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                # 查找最新的检查点
                best_model = self.checkpoint_dir / "best_model.pth"
                if best_model.exists():
                    logger.info(f"✅ 训练完成，最佳模型: {best_model}")
                    return True, str(best_model)
                else:
                    logger.warning("训练完成但未找到最佳模型")
                    return True, ""
            else:
                logger.error("❌ 训练失败")
                return False, ""
                
        except Exception as e:
            logger.error(f"训练异常: {e}")
            return False, ""
    
    def run_evaluation(self, model_path: str = None) -> bool:
        """运行评估"""
        logger.info("📊 开始评估模型性能...")
        
        try:
            # 创建结果目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            eval_output = self.results_dir / f"evaluation_{timestamp}"
            eval_output.mkdir(parents=True, exist_ok=True)
            
            cmd = [sys.executable, str(self.eval_script), "--output", str(eval_output)]
            
            if model_path and Path(model_path).exists():
                cmd.extend(["--model", model_path])
            
            if self.config_file.exists():
                cmd.extend(["--config", str(self.config_file)])
            
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                logger.info(f"✅ 评估完成，结果保存在: {eval_output}")
                
                # 显示主要结果
                report_file = eval_output / "evaluation_report.json"
                if report_file.exists():
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                    
                    results = report['evaluation_summary']['model_performance']
                    comparison = report['evaluation_summary']['baseline_comparison']
                    
                    logger.info("📊 主要评估结果:")
                    logger.info(f"   准确率: {results['accuracy']:.4f}")
                    logger.info(f"   F1分数: {results['f1_score']:.4f}")
                    logger.info(f"   相似度差距: {results['similarity_gap']:.4f}")
                    logger.info(f"   相比基线提升: {comparison['improvement']['relative_improvement']:.2f}%")
                
                return True
            else:
                logger.error("❌ 评估失败")
                return False
                
        except Exception as e:
            logger.error(f"评估异常: {e}")
            return False
    
    def _create_default_config(self, epochs: int, batch_size: int, learning_rate: float):
        """创建默认配置文件"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        config_content = f"""# A股RAG对比学习训练配置
model:
  base_model: "BAAI/bge-large-zh-v1.5"
  embedding_dim: 1024
  projection_dim: 1024

training:
  batch_size: {batch_size}
  learning_rate: {learning_rate}
  epochs: {epochs}
  warmup_steps: 100
  temperature: 0.05
  margin: 0.5
  hard_negative_weight: 2.0
  gradient_clip_norm: 1.0

data:
  train_split: 0.8
  val_split: 0.2
  max_seq_length: 512
  num_hard_negatives: 3

optimization:
  optimizer: "AdamW"
  weight_decay: 0.01
  scheduler: "cosine"
  min_lr: 1e-6

logging:
  log_steps: 50
  eval_steps: 200
  save_steps: 500
  tensorboard_dir: "{self.project_root / 'logs' / 'tensorboard'}"
  checkpoint_dir: "{self.checkpoint_dir}"

evaluation:
  metrics: ["accuracy", "precision", "recall", "f1", "auc"]
  top_k: [1, 3, 5, 10]
  similarity_threshold: 0.7
"""
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"创建默认配置文件: {self.config_file}")
    
    def run_full_pipeline(self, epochs: int = 10, batch_size: int = 32,
                         learning_rate: float = 5e-5, force_setup: bool = False,
                         resume: str = None) -> bool:
        """运行完整训练+评估流程"""
        logger.info("🎯 开始完整训练和评估流程...")
        
        start_time = datetime.now()
        
        try:
            # 1. 检查前置条件
            if not self.check_prerequisites():
                return False
            
            # 2. 配置环境 (如果需要)
            if force_setup or not self.config_file.exists():
                if not self.setup_environment():
                    return False
            
            # 3. 训练模型
            success, model_path = self.run_training(epochs, batch_size, learning_rate, resume)
            if not success:
                return False
            
            # 4. 评估模型
            if not self.run_evaluation(model_path):
                return False
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("🎉 完整流程执行成功！")
            logger.info(f"总耗时: {duration}")
            logger.info(f"最佳模型: {model_path}")
            logger.info(f"结果目录: {self.results_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"流程执行异常: {e}")
            return False
    
    def show_usage_guide(self):
        """显示使用指南"""
        guide = """
🎯 A股RAG对比学习训练指南

📋 使用步骤:

1. 快速开始 (推荐新手):
   python tools/development/quick_train_test.py --full-pipeline

2. 仅配置环境:
   python tools/development/quick_train_test.py --setup-only

3. 仅训练模型:
   python tools/development/quick_train_test.py --train-only --epochs 20

4. 仅评估模型:
   python tools/development/quick_train_test.py --eval-only --model checkpoints/best_model.pth

5. 自定义训练参数:
   python tools/development/quick_train_test.py --full-pipeline --epochs 30 --batch-size 16 --learning-rate 1e-5

📊 训练参数说明:
- epochs: 训练轮数 (默认10, 推荐10-30)
- batch-size: 批次大小 (默认32, 根据GPU内存调整)
- learning-rate: 学习率 (默认5e-5, 范围1e-6到1e-4)

💡 训练建议:
- 首次训练推荐使用默认参数
- GPU内存不足可减小batch-size
- 收敛慢可增加epochs
- 过拟合可减小learning-rate

📈 输出文件:
- checkpoints/: 模型检查点
- results/: 评估结果和报告
- logs/: 训练日志和可视化

🔧 故障排查:
- 如果环境配置失败，可手动安装依赖: pip install torch sentence-transformers scikit-learn
- 如果训练中断，可使用 --resume checkpoints/latest_checkpoint.pth 继续训练
- 如果GPU内存不足，减小batch-size或使用CPU训练
"""
        print(guide)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="A股RAG对比学习快速训练和测试")
    
    # 操作模式
    parser.add_argument("--full-pipeline", action="store_true", help="运行完整训练+评估流程")
    parser.add_argument("--setup-only", action="store_true", help="仅配置环境")
    parser.add_argument("--train-only", action="store_true", help="仅训练模型")
    parser.add_argument("--eval-only", action="store_true", help="仅评估模型")
    parser.add_argument("--usage", action="store_true", help="显示使用指南")
    
    # 训练参数
    parser.add_argument("--epochs", type=int, default=10, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=32, help="批次大小")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="学习率")
    
    # 其他选项
    parser.add_argument("--model", type=str, help="评估模型路径")
    parser.add_argument("--resume", type=str, help="恢复训练检查点")
    parser.add_argument("--force-setup", action="store_true", help="强制重新配置环境")
    parser.add_argument("--project-root", type=str, help="项目根目录")
    
    args = parser.parse_args()
    
    if args.usage:
        trainer = QuickTrainer()
        trainer.show_usage_guide()
        return
    
    # 初始化训练器
    trainer = QuickTrainer(args.project_root)
    
    # 执行对应操作
    if args.full_pipeline:
        success = trainer.run_full_pipeline(
            epochs=args.epochs,
            batch_size=args.batch_size, 
            learning_rate=args.learning_rate,
            force_setup=args.force_setup,
            resume=args.resume
        )
        sys.exit(0 if success else 1)
        
    elif args.setup_only:
        success = trainer.setup_environment(args.force_setup)
        sys.exit(0 if success else 1)
        
    elif args.train_only:
        success, _ = trainer.run_training(
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            resume=args.resume
        )
        sys.exit(0 if success else 1)
        
    elif args.eval_only:
        success = trainer.run_evaluation(args.model)
        sys.exit(0 if success else 1)
        
    else:
        # 默认显示帮助
        parser.print_help()
        print("\n💡 使用 --usage 查看详细使用指南")

if __name__ == "__main__":
    main()
