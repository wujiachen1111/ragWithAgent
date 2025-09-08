#!/usr/bin/env python3
"""
RAG对比学习训练环境配置脚本
自动下载模型、配置环境、验证依赖
"""

import os
import sys
import subprocess
import torch
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict
import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrainingEnvironmentSetup:
    """训练环境配置管理器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent.parent
        self.models_dir = self.project_root / "models"
        self.cache_dir = self.project_root / ".cache"
        
        # 创建必要目录
        self.models_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 模型配置
        self.models_config = {
            "embedding_model": {
                "name": "BAAI/bge-large-zh-v1.5",
                "type": "sentence-transformers",
                "description": "中文大规模预训练文本嵌入模型",
                "size": "1.3GB"
            },
            "reranker_model": {
                "name": "BAAI/bge-reranker-large",
                "type": "sentence-transformers", 
                "description": "中文文本重排序模型",
                "size": "1.1GB"
            }
        }
        
    def check_dependencies(self) -> Dict[str, bool]:
        """检查训练依赖"""
        dependencies = {
            "torch": False,
            "sentence_transformers": False,
            "sklearn": False,
            "numpy": False,
            "tqdm": False,
            "matplotlib": False,
            "seaborn": False
        }
        
        for dep in dependencies:
            try:
                __import__(dep.replace("-", "_"))
                dependencies[dep] = True
                logger.info(f"✅ {dep} 已安装")
            except ImportError:
                logger.warning(f"❌ {dep} 未安装")
                
        return dependencies
    
    def install_dependencies(self):
        """安装缺失依赖"""
        logger.info("🔧 安装训练依赖...")
        
        requirements = [
            "torch>=1.12.0",
            "sentence-transformers>=2.2.0", 
            "scikit-learn>=1.1.0",
            "numpy>=1.21.0",
            "tqdm>=4.64.0",
            "matplotlib>=3.5.0",
            "seaborn>=0.11.0",
            "tensorboard>=2.10.0",
            "wandb>=0.13.0"  # 可选：实验追踪
        ]
        
        for req in requirements:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", req], 
                             check=True, capture_output=True)
                logger.info(f"✅ 安装成功: {req}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ 安装失败: {req}, 错误: {e}")
    
    def check_gpu_availability(self) -> Dict[str, any]:
        """检查GPU可用性"""
        gpu_info = {
            "cuda_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "gpu_names": [],
            "memory_info": []
        }
        
        if gpu_info["cuda_available"]:
            for i in range(gpu_info["gpu_count"]):
                gpu_names = torch.cuda.get_device_name(i)
                gpu_info["gpu_names"].append(gpu_names)
                
                # GPU内存信息
                memory_info = {
                    "total": torch.cuda.get_device_properties(i).total_memory,
                    "allocated": torch.cuda.memory_allocated(i),
                    "reserved": torch.cuda.memory_reserved(i)
                }
                gpu_info["memory_info"].append(memory_info)
                
                logger.info(f"🚀 GPU {i}: {gpu_names}")
                logger.info(f"   内存: {memory_info['total']/1024**3:.1f}GB 总量")
        else:
            logger.warning("⚠️  未检测到CUDA GPU，将使用CPU训练（较慢）")
            
        return gpu_info
    
    def download_models(self, force_download: bool = False) -> Dict[str, bool]:
        """下载和缓存训练模型"""
        download_results = {}
        
        for model_key, model_config in self.models_config.items():
            model_name = model_config["name"]
            model_path = self.models_dir / model_name.replace("/", "_")
            
            logger.info(f"📥 准备下载模型: {model_name} ({model_config['size']})")
            
            try:
                if model_path.exists() and not force_download:
                    logger.info(f"✅ 模型已存在，跳过下载: {model_name}")
                    download_results[model_key] = True
                    continue
                
                # 使用sentence-transformers自动下载和缓存
                logger.info(f"🔄 正在下载 {model_name}...")
                
                if model_config["type"] == "sentence-transformers":
                    model = SentenceTransformer(model_name, 
                                              cache_folder=str(self.cache_dir))
                    
                    # 保存到本地models目录
                    model.save(str(model_path))
                    logger.info(f"✅ 模型下载完成: {model_name}")
                    download_results[model_key] = True
                else:
                    logger.warning(f"⚠️  不支持的模型类型: {model_config['type']}")
                    download_results[model_key] = False
                    
            except Exception as e:
                logger.error(f"❌ 模型下载失败: {model_name}, 错误: {e}")
                download_results[model_key] = False
                
        return download_results
    
    def create_training_config(self) -> str:
        """创建训练配置文件"""
        config_path = self.project_root / "configs" / "training" / "contrastive_training.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_content = f"""# A股RAG对比学习训练配置
model:
  base_model: "BAAI/bge-large-zh-v1.5"
  model_path: "{self.models_dir / 'BAAI_bge-large-zh-v1_5'}"
  embedding_dim: 1024
  projection_dim: 1024
  
training:
  batch_size: 32
  learning_rate: 5e-5
  epochs: 20
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
  checkpoint_dir: "{self.project_root / 'checkpoints'}"
  
evaluation:
  metrics: ["accuracy", "precision", "recall", "f1", "auc"]
  top_k: [1, 3, 5, 10]
  similarity_threshold: 0.7
"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
            
        logger.info(f"✅ 训练配置文件创建: {config_path}")
        return str(config_path)
    
    def validate_environment(self) -> bool:
        """验证训练环境完整性"""
        logger.info("🔍 验证训练环境...")
        
        # 检查依赖
        deps = self.check_dependencies()
        missing_deps = [k for k, v in deps.items() if not v]
        
        if missing_deps:
            logger.error(f"❌ 缺少依赖: {missing_deps}")
            return False
        
        # 检查GPU
        gpu_info = self.check_gpu_availability()
        
        # 检查模型
        model_path = self.models_dir / "BAAI_bge-large-zh-v1_5"
        if not model_path.exists():
            logger.error("❌ 基础模型未下载")
            return False
            
        # 检查样本数据
        samples_path = self.project_root / "services" / "decision_engine" / "contrastive_learning_samples.py"
        if not samples_path.exists():
            logger.error("❌ 训练样本文件不存在")
            return False
            
        logger.info("✅ 训练环境验证通过")
        return True
    
    def setup_full_environment(self):
        """完整环境配置流程"""
        logger.info("🚀 开始配置RAG训练环境...")
        
        # 1. 检查并安装依赖
        logger.info("步骤 1/5: 检查依赖...")
        deps = self.check_dependencies()
        missing_deps = [k for k, v in deps.items() if not v]
        
        if missing_deps:
            logger.info(f"需要安装依赖: {missing_deps}")
            self.install_dependencies()
        
        # 2. 检查GPU
        logger.info("步骤 2/5: 检查GPU环境...")
        self.check_gpu_availability()
        
        # 3. 下载模型
        logger.info("步骤 3/5: 下载训练模型...")
        download_results = self.download_models()
        
        failed_downloads = [k for k, v in download_results.items() if not v]
        if failed_downloads:
            logger.warning(f"⚠️  部分模型下载失败: {failed_downloads}")
        
        # 4. 创建配置
        logger.info("步骤 4/5: 创建训练配置...")
        config_path = self.create_training_config()
        
        # 5. 验证环境
        logger.info("步骤 5/5: 验证环境完整性...")
        is_valid = self.validate_environment()
        
        if is_valid:
            logger.info("🎉 训练环境配置完成！")
            logger.info(f"📄 配置文件: {config_path}")
            logger.info(f"📁 模型目录: {self.models_dir}")
            logger.info(f"💾 缓存目录: {self.cache_dir}")
            
            # 输出下一步指导
            logger.info("\n📋 下一步操作:")
            logger.info("1. 运行训练脚本: python tools/development/training/train_contrastive_rag.py")
            logger.info("2. 监控训练过程: tensorboard --logdir logs/tensorboard")
            logger.info("3. 评估模型效果: python tools/development/testing/evaluate_rag_performance.py")
        else:
            logger.error("❌ 环境配置失败，请检查错误信息")
            
        return is_valid

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="配置RAG训练环境")
    parser.add_argument("--project-root", type=str, help="项目根目录")
    parser.add_argument("--force-download", action="store_true", help="强制重新下载模型")
    parser.add_argument("--check-only", action="store_true", help="仅检查环境，不进行配置")
    
    args = parser.parse_args()
    
    setup = TrainingEnvironmentSetup(args.project_root)
    
    if args.check_only:
        setup.validate_environment()
    else:
        setup.setup_full_environment()

if __name__ == "__main__":
    main()
