#!/usr/bin/env python3
"""
A股RAG对比学习模型训练脚本
基于难负样本的对比学习训练，提升RAG检索精度
"""

import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import numpy as np
import yaml
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from datetime import datetime
import pickle
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score

# 添加项目路径（运行时使用），并使用包路径供IDE静态分析
project_root = Path(__file__).parent.parent.parent.parent

from services.decision_engine.contrastive_learning_samples import A_STOCK_CONTRASTIVE_SAMPLES, SentimentLabel
from services.decision_engine.contrastive_rag_enhancer import ContrastiveEmbeddingModel, ContrastiveTrainingConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TrainingMetrics:
    """训练指标记录"""
    epoch: int
    step: int
    loss: float
    accuracy: float
    precision: float
    recall: float
    f1: float
    learning_rate: float
    timestamp: str

class ContrastiveDataset(Dataset):
    """对比学习数据集"""
    
    def __init__(self, samples: List[Dict], tokenizer=None, max_length: int = 512):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        return {
            'anchor': sample['anchor'],
            'positive': sample['positive'], 
            'hard_negative': sample['hard_negative'],
            'category': sample['category'],
            'anchor_label': sample['anchor_label'].value,
            'explanation': sample['explanation']
        }

class ContrastiveLoss(nn.Module):
    """对比学习损失函数"""
    
    def __init__(self, temperature: float = 0.05, margin: float = 0.5):
        super().__init__()
        self.temperature = temperature
        self.margin = margin
        
    def forward(self, anchor_emb, positive_emb, negative_emb):
        """
        计算对比学习损失
        Args:
            anchor_emb: 锚点嵌入 [batch_size, embedding_dim]
            positive_emb: 正样本嵌入 [batch_size, embedding_dim]  
            negative_emb: 负样本嵌入 [batch_size, embedding_dim]
        """
        batch_size = anchor_emb.size(0)
        
        # 计算余弦相似度
        pos_sim = torch.cosine_similarity(anchor_emb, positive_emb, dim=1)
        neg_sim = torch.cosine_similarity(anchor_emb, negative_emb, dim=1)
        
        # InfoNCE损失
        pos_exp = torch.exp(pos_sim / self.temperature)
        neg_exp = torch.exp(neg_sim / self.temperature)
        
        # 对比损失：拉近正样本，推远负样本
        loss_contrastive = -torch.log(pos_exp / (pos_exp + neg_exp + 1e-8))
        
        # 边界损失：确保正负样本差距
        loss_margin = torch.clamp(self.margin - (pos_sim - neg_sim), min=0)
        
        # 总损失
        total_loss = loss_contrastive.mean() + 0.5 * loss_margin.mean()
        
        return {
            'total_loss': total_loss,
            'contrastive_loss': loss_contrastive.mean(),
            'margin_loss': loss_margin.mean(),
            'pos_sim': pos_sim.mean(),
            'neg_sim': neg_sim.mean()
        }

class ContrastiveTrainer:
    """对比学习训练器"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        # 自动选择最优设备 (CUDA > MPS > CPU)
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
        elif torch.backends.mps.is_available():
            self.device = torch.device('mps')
        else:
            self.device = torch.device('cpu')
            
        logger.info(f"使用设备: {self.device}")
        
        # 初始化模型
        self.model = ContrastiveEmbeddingModel(
            base_model_name=self.config['model']['base_model']
        ).to(self.device)
        
        # 初始化损失函数
        self.criterion = ContrastiveLoss(
            temperature=self.config['training']['temperature'],
            margin=self.config['training']['margin']
        )
        
        # 初始化优化器
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.config['training']['learning_rate'],
            weight_decay=self.config['optimization']['weight_decay']
        )
        
        # 学习率调度器
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=self.config['training']['epochs'],
            eta_min=self.config['optimization']['min_lr']
        )
        
        # 训练记录
        self.training_history = []
        self.best_accuracy = 0.0
        self.best_model_path = None
        
        # 创建输出目录
        self.checkpoint_dir = Path(self.config['logging']['checkpoint_dir'])
        self.log_dir = Path(self.config['logging']['tensorboard_dir'])
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def prepare_data(self) -> Tuple[DataLoader, DataLoader]:
        """准备训练和验证数据"""
        logger.info("准备训练数据...")
        
        # 转换样本数据
        all_samples = []
        for category, samples in A_STOCK_CONTRASTIVE_SAMPLES.items():
            for sample in samples:
                all_samples.append({
                    'anchor': sample['anchor'],
                    'positive': sample.get('positive', sample['anchor']),  # 如果没有正样本，用锚点替代
                    'hard_negative': sample['hard_negative'],
                    'category': category,
                    'anchor_label': sample['anchor_label'],
                    'explanation': sample['explanation']
                })
        
        logger.info(f"总样本数: {len(all_samples)}")
        
        # 划分训练和验证集
        train_size = int(len(all_samples) * self.config['data']['train_split'])
        train_samples = all_samples[:train_size]
        val_samples = all_samples[train_size:]
        
        logger.info(f"训练集样本数: {len(train_samples)}")
        logger.info(f"验证集样本数: {len(val_samples)}")
        
        # 创建数据集和DataLoader
        train_dataset = ContrastiveDataset(train_samples, max_length=self.config['data']['max_seq_length'])
        val_dataset = ContrastiveDataset(val_samples, max_length=self.config['data']['max_seq_length'])
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config['training']['batch_size'],
            shuffle=True,
            num_workers=self.config['data'].get('num_workers', 4),
            pin_memory=True if self.device.type == 'cuda' else False
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config['training']['batch_size'],
            shuffle=False,
            num_workers=self.config['data'].get('num_workers', 4),
            pin_memory=True if self.device.type == 'cuda' else False
        )
        
        return train_loader, val_loader
    
    def train_epoch(self, train_loader: DataLoader, epoch: int) -> Dict:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0.0
        all_pos_sims = []
        all_neg_sims = []
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}")
        
        for step, batch in enumerate(progress_bar):
            # 数据移动到设备
            anchor_texts = batch['anchor']
            positive_texts = batch['positive']
            negative_texts = batch['hard_negative']
            
            # 获取嵌入
            anchor_emb = self.model.encode(anchor_texts)
            positive_emb = self.model.encode(positive_texts)
            negative_emb = self.model.encode(negative_texts)
            
            # 计算损失
            loss_dict = self.criterion(anchor_emb, positive_emb, negative_emb)
            loss = loss_dict['total_loss']
            
            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            
            # 梯度裁剪
            if self.config['training']['gradient_clip_norm'] > 0:
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), 
                    self.config['training']['gradient_clip_norm']
                )
            
            self.optimizer.step()
            
            # 记录指标
            total_loss += loss.item()
            all_pos_sims.append(loss_dict['pos_sim'].item())
            all_neg_sims.append(loss_dict['neg_sim'].item())
            
            # 更新进度条
            progress_bar.set_postfix({
                'Loss': f"{loss.item():.4f}",
                'Pos_Sim': f"{loss_dict['pos_sim'].item():.3f}",
                'Neg_Sim': f"{loss_dict['neg_sim'].item():.3f}"
            })
            
        epoch_metrics = {
            'avg_loss': total_loss / len(train_loader),
            'avg_pos_sim': np.mean(all_pos_sims),
            'avg_neg_sim': np.mean(all_neg_sims),
            'learning_rate': self.optimizer.param_groups[0]['lr']
        }
        
        return epoch_metrics
    
    def evaluate(self, val_loader: DataLoader) -> Dict:
        """评估模型"""
        self.model.eval()
        total_loss = 0.0
        all_predictions = []
        all_labels = []
        all_pos_sims = []
        all_neg_sims = []
        
        with torch.no_grad():
            for batch in tqdm(val_loader, desc="Evaluating"):
                anchor_texts = batch['anchor']
                positive_texts = batch['positive']
                negative_texts = batch['hard_negative']
                
                # 获取嵌入
                anchor_emb = self.model.encode(anchor_texts)
                positive_emb = self.model.encode(positive_texts)
                negative_emb = self.model.encode(negative_texts)
                
                # 计算损失
                loss_dict = self.criterion(anchor_emb, positive_emb, negative_emb)
                total_loss += loss_dict['total_loss'].item()
                
                # 计算预测准确性（正样本相似度应该高于负样本）
                pos_sims = torch.cosine_similarity(anchor_emb, positive_emb, dim=1)
                neg_sims = torch.cosine_similarity(anchor_emb, negative_emb, dim=1)
                
                predictions = (pos_sims > neg_sims).float()  # 1 表示预测正确
                all_predictions.extend(predictions.cpu().tolist())
                all_labels.extend([1] * len(predictions))  # 全部标签为1（正确）
                
                all_pos_sims.extend(pos_sims.cpu().tolist())
                all_neg_sims.extend(neg_sims.cpu().tolist())
        
        # 计算评估指标
        accuracy = np.mean(all_predictions)
        avg_pos_sim = np.mean(all_pos_sims)
        avg_neg_sim = np.mean(all_neg_sims)
        similarity_gap = avg_pos_sim - avg_neg_sim
        
        eval_metrics = {
            'avg_loss': total_loss / len(val_loader),
            'accuracy': accuracy,
            'avg_pos_sim': avg_pos_sim,
            'avg_neg_sim': avg_neg_sim,
            'similarity_gap': similarity_gap,
            'num_samples': len(all_predictions)
        }
        
        return eval_metrics
    
    def save_checkpoint(self, epoch: int, metrics: Dict, is_best: bool = False):
        """保存模型检查点"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'metrics': metrics,
            'config': self.config,
            'training_history': self.training_history
        }
        
        # 保存最新检查点
        latest_path = self.checkpoint_dir / 'latest_checkpoint.pth'
        torch.save(checkpoint, latest_path)
        logger.info(f"保存检查点: {latest_path}")
        
        # 保存最佳模型
        if is_best:
            best_path = self.checkpoint_dir / 'best_model.pth'
            torch.save(checkpoint, best_path)
            self.best_model_path = best_path
            logger.info(f"保存最佳模型: {best_path}")
            
        # 定期保存
        if (epoch + 1) % 5 == 0:
            epoch_path = self.checkpoint_dir / f'checkpoint_epoch_{epoch+1}.pth'
            torch.save(checkpoint, epoch_path)
    
    def load_checkpoint(self, checkpoint_path: str) -> int:
        """加载检查点"""
        if not os.path.exists(checkpoint_path):
            logger.warning(f"检查点文件不存在: {checkpoint_path}")
            return 0
            
        checkpoint = torch.load(checkpoint_path, map_location=self.device)  # TODO: Consider using weights_only=True for security
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.training_history = checkpoint.get('training_history', [])
        
        epoch = checkpoint['epoch']
        logger.info(f"加载检查点成功，从epoch {epoch+1}继续训练")
        return epoch + 1
    
    def plot_training_history(self):
        """绘制训练历史"""
        if not self.training_history:
            return
            
        # 提取数据
        epochs = [m['epoch'] for m in self.training_history]
        train_losses = [m['train_loss'] for m in self.training_history]
        val_losses = [m['val_loss'] for m in self.training_history]
        accuracies = [m['val_accuracy'] for m in self.training_history]
        similarity_gaps = [m['similarity_gap'] for m in self.training_history]
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('训练历史', fontsize=16)
        
        # 损失曲线
        axes[0,0].plot(epochs, train_losses, label='训练损失', color='blue')
        axes[0,0].plot(epochs, val_losses, label='验证损失', color='red')
        axes[0,0].set_title('损失曲线')
        axes[0,0].set_xlabel('Epoch')
        axes[0,0].set_ylabel('Loss')
        axes[0,0].legend()
        axes[0,0].grid(True)
        
        # 准确率曲线
        axes[0,1].plot(epochs, accuracies, label='验证准确率', color='green')
        axes[0,1].set_title('准确率曲线')
        axes[0,1].set_xlabel('Epoch')
        axes[0,1].set_ylabel('Accuracy')
        axes[0,1].legend()
        axes[0,1].grid(True)
        
        # 相似度差距
        axes[1,0].plot(epochs, similarity_gaps, label='相似度差距', color='purple')
        axes[1,0].set_title('正负样本相似度差距')
        axes[1,0].set_xlabel('Epoch')
        axes[1,0].set_ylabel('Similarity Gap')
        axes[1,0].legend()
        axes[1,0].grid(True)
        
        # 学习率曲线
        learning_rates = [m['learning_rate'] for m in self.training_history]
        axes[1,1].plot(epochs, learning_rates, label='学习率', color='orange')
        axes[1,1].set_title('学习率变化')
        axes[1,1].set_xlabel('Epoch')
        axes[1,1].set_ylabel('Learning Rate')
        axes[1,1].legend()
        axes[1,1].grid(True)
        
        plt.tight_layout()
        
        # 保存图表
        plot_path = self.log_dir / 'training_history.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"训练历史图表保存到: {plot_path}")
        plt.show()
    
    def train(self, resume_from: str = None):
        """开始训练"""
        logger.info("🚀 开始A股RAG对比学习训练...")
        
        # 准备数据
        train_loader, val_loader = self.prepare_data()
        
        # 恢复训练
        start_epoch = 0
        if resume_from:
            start_epoch = self.load_checkpoint(resume_from)
        
        # 训练循环
        for epoch in range(start_epoch, self.config['training']['epochs']):
            logger.info(f"\n========== Epoch {epoch+1}/{self.config['training']['epochs']} ==========")
            
            # 训练
            train_metrics = self.train_epoch(train_loader, epoch)
            
            # 验证
            val_metrics = self.evaluate(val_loader)
            
            # 更新学习率
            self.scheduler.step()
            
            # 记录指标
            epoch_record = {
                'epoch': epoch + 1,
                'train_loss': train_metrics['avg_loss'],
                'val_loss': val_metrics['avg_loss'],
                'val_accuracy': val_metrics['accuracy'],
                'similarity_gap': val_metrics['similarity_gap'],
                'learning_rate': train_metrics['learning_rate'],
                'timestamp': datetime.now().isoformat()
            }
            self.training_history.append(epoch_record)
            
            # 打印指标
            logger.info(f"训练损失: {train_metrics['avg_loss']:.4f}")
            logger.info(f"验证损失: {val_metrics['avg_loss']:.4f}")  
            logger.info(f"验证准确率: {val_metrics['accuracy']:.4f}")
            logger.info(f"相似度差距: {val_metrics['similarity_gap']:.4f}")
            logger.info(f"学习率: {train_metrics['learning_rate']:.2e}")
            
            # 保存检查点
            is_best = val_metrics['accuracy'] > self.best_accuracy
            if is_best:
                self.best_accuracy = val_metrics['accuracy']
                logger.info(f"🎉 新的最佳准确率: {self.best_accuracy:.4f}")
            
            self.save_checkpoint(epoch, val_metrics, is_best)
            
        logger.info("✅ 训练完成!")
        logger.info(f"最佳准确率: {self.best_accuracy:.4f}")
        
        # 绘制训练历史
        self.plot_training_history()
        
        # 保存训练记录
        history_path = self.log_dir/ 'training_history.json'
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(self.training_history, f, ensure_ascii=False, indent=2)
        logger.info(f"训练记录保存到: {history_path}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="训练A股RAG对比学习模型")
    parser.add_argument("--config", type=str, 
                       default="configs/training/contrastive_training.yaml",
                       help="训练配置文件路径")
    parser.add_argument("--resume", type=str, help="恢复训练的检查点路径")
    parser.add_argument("--gpu", type=int, help="使用的GPU ID")
    
    args = parser.parse_args()
    
    # 设置GPU
    if args.gpu is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    
    # 开始训练
    trainer = ContrastiveTrainer(args.config)
    trainer.train(resume_from=args.resume)

if __name__ == "__main__":
    main()
