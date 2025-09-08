#!/usr/bin/env python3
"""
训练后模型效果演示脚本
展示A股特化对比学习RAG模型的实际效果
"""

import os
import sys
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import logging
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root / "services" / "decision_engine"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainedModelDemo:
    """训练模型演示器"""
    
    def __init__(self, model_path: str = None):
        self.project_root = project_root
        self.model = None
        self.baseline_model = None
        
        # 查找模型文件
        if model_path and Path(model_path).exists():
            self.model_path = Path(model_path)
        else:
            # 查找最佳模型
            checkpoint_dir = self.project_root / "checkpoints"
            if checkpoint_dir.exists():
                best_model = checkpoint_dir / "best_model.pth"
                if best_model.exists():
                    self.model_path = best_model
                else:
                    self.model_path = None
            else:
                self.model_path = None
        
        # 测试样本对
        self.test_samples = [
            {
                "anchor": "公司发布员工持股计划，激励核心骨干团队",
                "positive": "公司公布股权激励计划，绑定核心团队利益",
                "hard_negative": "公司控股股东发布减持计划，拟大幅套现离场",
                "category": "股权变动",
                "explanation": "员工持股为利好，股东减持为利空"
            },
            {
                "anchor": "产品成功获得海外大额订单，业务拓展顺利",
                "positive": "公司产品出口订单激增，国际化进程加速",  
                "hard_negative": "产品遭遇海外反倾销调查，出口受阻",
                "category": "业务发展", 
                "explanation": "获得订单为利好，反倾销调查为利空"
            },
            {
                "anchor": "公司发布业绩预增公告，净利润大幅提升",
                "positive": "业绩超预期增长，盈利能力显著改善",
                "hard_negative": "公司发布业绩预警，净利润可能大幅下滑",
                "category": "财务状况",
                "explanation": "业绩预增为利好，业绩预警为利空"
            },
            {
                "anchor": "股价突破重要阻力位，技术面转强",
                "positive": "股价放量突破，技术指标显示买入信号",
                "hard_negative": "股价跌破重要支撑位，技术面转弱", 
                "category": "技术分析",
                "explanation": "技术突破为利好，技术破位为利空"
            },
            {
                "anchor": "政策利好频出，行业景气度持续提升",
                "positive": "国家政策大力支持，行业迎来发展机遇",
                "hard_negative": "监管政策趋严，行业面临合规压力",
                "category": "政策环境", 
                "explanation": "政策利好为利好，监管趋严为利空"
            }
        ]
    
    def load_models(self) -> bool:
        """加载训练模型和基线模型"""
        try:
            from contrastive_rag_enhancer import ContrastiveEmbeddingModel
            from sentence_transformers import SentenceTransformer
            
            # 加载训练后的模型
            if self.model_path and self.model_path.exists():
                logger.info(f"📥 加载训练模型: {self.model_path}")
                
                self.model = ContrastiveEmbeddingModel()
                checkpoint = torch.load(self.model_path, map_location='cpu')  # TODO: Consider using weights_only=True for security
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.model.eval()
                
                logger.info("✅ 训练模型加载成功")
            else:
                logger.warning("⚠️  未找到训练模型，将只使用基线模型")
                return False
            
            # 加载基线模型用于对比
            logger.info("📥 加载基线模型: BAAI/bge-large-zh-v1.5")
            self.baseline_model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
            logger.info("✅ 基线模型加载成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            return False
    
    def test_single_sample(self, sample: Dict, model, model_name: str) -> Dict:
        """测试单个样本"""
        try:
            if model_name == "训练模型" and self.model:
                # 使用训练模型
                with torch.no_grad():
                    anchor_emb = model.encode([sample['anchor']])
                    positive_emb = model.encode([sample['positive']])  
                    negative_emb = model.encode([sample['hard_negative']])
                
                pos_sim = torch.cosine_similarity(anchor_emb, positive_emb, dim=1).item()
                neg_sim = torch.cosine_similarity(anchor_emb, negative_emb, dim=1).item()
                
            else:
                # 使用基线模型
                anchor_emb = model.encode([sample['anchor']])
                positive_emb = model.encode([sample['positive']])
                negative_emb = model.encode([sample['hard_negative']])
                
                from sklearn.metrics.pairwise import cosine_similarity
                pos_sim = cosine_similarity(anchor_emb, positive_emb)[0][0]
                neg_sim = cosine_similarity(anchor_emb, negative_emb)[0][0]
            
            # 判断是否正确（正样本相似度应该高于负样本）
            correct = pos_sim > neg_sim
            similarity_gap = pos_sim - neg_sim
            
            return {
                "pos_sim": pos_sim,
                "neg_sim": neg_sim, 
                "similarity_gap": similarity_gap,
                "correct": correct,
                "confidence": abs(similarity_gap)
            }
            
        except Exception as e:
            logger.error(f"样本测试失败: {e}")
            return None
    
    def run_comparison_demo(self):
        """运行对比演示"""
        logger.info("🎯 开始A股RAG模型效果演示")
        logger.info("="*80)
        
        if not self.load_models():
            logger.error("❌ 模型加载失败，无法进行演示")
            return
        
        print(f"\n{'='*80}")
        print("🎯 A股特化对比学习RAG模型效果演示")
        print(f"{'='*80}")
        print(f"📅 演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔢 测试样本数: {len(self.test_samples)}")
        print(f"📊 对比模型: 训练模型 vs 基线模型(BGE-Large-ZH-v1.5)")
        print(f"{'='*80}\n")
        
        total_results = {
            "训练模型": {"correct": 0, "total": 0, "avg_gap": 0, "gaps": []},
            "基线模型": {"correct": 0, "total": 0, "avg_gap": 0, "gaps": []}
        }
        
        for i, sample in enumerate(self.test_samples, 1):
            print(f"📋 测试样本 {i}: {sample['category']}")
            print(f"   锚点(参考): {sample['anchor']}")
            print(f"   正样本(相似): {sample['positive']}")
            print(f"   难负样本(相反): {sample['hard_negative']}")
            print(f"   解释: {sample['explanation']}")
            print()
            
            # 测试训练模型
            trained_result = self.test_single_sample(sample, self.model, "训练模型")
            baseline_result = self.test_single_sample(sample, self.baseline_model, "基线模型")
            
            if trained_result and baseline_result:
                # 更新统计
                for model_name, result in [("训练模型", trained_result), ("基线模型", baseline_result)]:
                    total_results[model_name]["total"] += 1
                    if result["correct"]:
                        total_results[model_name]["correct"] += 1
                    total_results[model_name]["gaps"].append(result["similarity_gap"])
                
                print("   📊 相似度分析:")
                print(f"      模型类型     正样本相似度  负样本相似度  相似度差距   判断结果")
                print(f"      {'─'*60}")
                
                # 训练模型结果
                trained_status = "✅ 正确" if trained_result["correct"] else "❌ 错误"
                print(f"      训练模型     {trained_result['pos_sim']:.4f}       {trained_result['neg_sim']:.4f}       {trained_result['similarity_gap']:.4f}     {trained_status}")
                
                # 基线模型结果  
                baseline_status = "✅ 正确" if baseline_result["correct"] else "❌ 错误"
                print(f"      基线模型     {baseline_result['pos_sim']:.4f}       {baseline_result['neg_sim']:.4f}       {baseline_result['similarity_gap']:.4f}     {baseline_status}")
                
                # 改进分析
                if trained_result["similarity_gap"] > baseline_result["similarity_gap"]:
                    improvement = (trained_result["similarity_gap"] - baseline_result["similarity_gap"])
                    print(f"      🚀 训练模型相似度差距提升: +{improvement:.4f}")
                elif trained_result["similarity_gap"] < baseline_result["similarity_gap"]:
                    decrease = (baseline_result["similarity_gap"] - trained_result["similarity_gap"])
                    print(f"      📉 训练模型相似度差距下降: -{decrease:.4f}")
                else:
                    print(f"      ➡️  相似度差距相同")
                
                print()
            else:
                print("   ❌ 测试失败")
                print()
            
            if i < len(self.test_samples):
                print("─" * 80 + "\n")
        
        # 总结报告
        self.print_summary_report(total_results)
    
    def print_summary_report(self, results: Dict):
        """打印总结报告"""
        print(f"\n{'='*80}")
        print("📊 演示总结报告")
        print(f"{'='*80}")
        
        for model_name, stats in results.items():
            if stats["total"] > 0:
                accuracy = stats["correct"] / stats["total"]
                avg_gap = np.mean(stats["gaps"])
                
                print(f"\n🤖 {model_name}:")
                print(f"   准确率: {accuracy:.1%} ({stats['correct']}/{stats['total']})")
                print(f"   平均相似度差距: {avg_gap:.4f}")
                print(f"   相似度差距标准差: {np.std(stats['gaps']):.4f}")
        
        # 对比分析
        if results["训练模型"]["total"] > 0 and results["基线模型"]["total"] > 0:
            trained_acc = results["训练模型"]["correct"] / results["训练模型"]["total"]
            baseline_acc = results["基线模型"]["correct"] / results["基线模型"]["total"]
            
            trained_gap = np.mean(results["训练模型"]["gaps"])
            baseline_gap = np.mean(results["基线模型"]["gaps"])
            
            acc_improvement = (trained_acc - baseline_acc) / baseline_acc * 100 if baseline_acc > 0 else 0
            gap_improvement = trained_gap - baseline_gap
            
            print(f"\n🎯 性能对比:")
            print(f"   准确率提升: {acc_improvement:+.1f}%")
            print(f"   相似度差距改善: {gap_improvement:+.4f}")
            
            if acc_improvement > 0 and gap_improvement > 0:
                print(f"   🎉 训练模型表现优于基线模型!")
            elif acc_improvement > 0 or gap_improvement > 0:
                print(f"   ⭐ 训练模型在某些方面表现更好")
            else:
                print(f"   🤔 训练模型需要进一步优化")
        
        print(f"\n💡 应用建议:")
        if results["训练模型"]["correct"] / results["训练模型"]["total"] > 0.8:
            print("   ✅ 模型表现良好，可用于生产环境")
            print("   ✅ 能够准确区分A股利好利空信息")
            print("   ✅ 适合集成到RAG系统中使用")
        else:
            print("   ⚠️  建议增加训练轮数或调整参数")
            print("   ⚠️  可以考虑增加更多训练样本")
            print("   ⚠️  检查样本质量和标注准确性")
        
        print(f"\n🔧 使用方式:")
        print("   # 在RAG系统中启用增强模式")
        print("   curl -X POST http://localhost:8000/v1/analyse/enhanced_rag_query \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"query\": \"浦发银行业绩预警是利好还是利空？\", \"detect_conflicts\": true}'")
        
        print(f"\n{'='*80}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="训练模型效果演示")
    parser.add_argument("--model", type=str, help="指定模型文件路径")
    parser.add_argument("--no-baseline", action="store_true", help="不加载基线模型对比")
    
    args = parser.parse_args()
    
    demo = TrainedModelDemo(args.model)
    demo.run_comparison_demo()

if __name__ == "__main__":
    main()
