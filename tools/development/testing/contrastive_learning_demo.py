#!/usr/bin/env python3
"""
A股对比学习RAG增强演示脚本
演示如何使用对比学习技术提升股票舆情分析的准确性
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContrastiveLearningDemo:
    """对比学习演示类"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 训练可能需要较长时间
    
    async def check_system_status(self) -> Dict[str, Any]:
        """检查系统状态"""
        logger.info("🔍 检查系统状态...")
        
        try:
            # 检查决策引擎状态
            response = await self.client.get(f"{self.base_url}/")
            response.raise_for_status()
            system_status = response.json()
            
            # 检查对比学习功能状态
            response = await self.client.get(f"{self.base_url}/v1/contrastive_learning/status")
            response.raise_for_status()
            cl_status = response.json()
            
            logger.info("✅ 系统状态检查完成")
            return {
                "system": system_status,
                "contrastive_learning": cl_status
            }
            
        except Exception as e:
            logger.error(f"❌ 系统状态检查失败: {e}")
            raise
    
    async def show_sample_data(self):
        """展示对比学习样本数据"""
        logger.info("📊 获取对比学习样本数据...")
        
        try:
            response = await self.client.get(f"{self.base_url}/v1/contrastive_learning/samples")
            response.raise_for_status()
            samples_data = response.json()
            
            print("\n" + "="*60)
            print("📈 A股对比学习样本数据概览")
            print("="*60)
            
            # 显示统计信息
            stats = samples_data["statistics"]
            print(f"📊 样本统计:")
            for category, count in stats.items():
                if category != "total":
                    print(f"  • {category}: {count}个样本")
            print(f"  • 总计: {stats['total']}个样本")
            
            # 显示样本示例
            print(f"\n📝 样本示例:")
            for category, examples in samples_data["sample_examples"].items():
                print(f"\n【{category}类】")
                for i, example in enumerate(examples, 1):
                    print(f"  样本{i}:")
                    print(f"    🎯 锚点: {example['anchor']}")
                    print(f"    ❌ 难负样本: {example['hard_negative']}")
                    print(f"    💡 解释: {example['explanation']}")
            
            return samples_data
            
        except Exception as e:
            logger.error(f"❌ 获取样本数据失败: {e}")
            raise
    
    async def train_contrastive_model(self, epochs: int = 5, batch_size: int = 16) -> Dict[str, Any]:
        """训练对比学习模型"""
        logger.info(f"🚀 开始训练对比学习模型 (epochs={epochs}, batch_size={batch_size})...")
        
        try:
            start_time = time.time()
            
            response = await self.client.post(
                f"{self.base_url}/v1/contrastive_learning/train",
                params={
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "learning_rate": 1e-5
                }
            )
            response.raise_for_status()
            training_result = response.json()
            
            end_time = time.time()
            training_time = end_time - start_time
            
            print("\n" + "="*60)
            print("🎓 对比学习模型训练完成")
            print("="*60)
            print(f"⏱️  训练耗时: {training_time:.2f} 秒")
            
            if "training_report" in training_result:
                report = training_result["training_report"]
                if report.get("total_epochs", 0) > 0:
                    print(f"📈 训练轮数: {report['total_epochs']}")
                    print(f"📉 最终损失: {report['final_loss']:.4f}")
                    print(f"🎯 最终准确率: {report['final_accuracy']:.3f}")
                    print(f"🏆 最佳准确率: {report['best_accuracy']:.3f}")
            
            logger.info("✅ 模型训练完成")
            return training_result
            
        except Exception as e:
            logger.error(f"❌ 模型训练失败: {e}")
            raise
    
    async def compare_rag_methods(self):
        """对比标准RAG与增强RAG的效果"""
        logger.info("🔬 对比不同RAG方法的效果...")
        
        test_queries = [
            "浦发银行最近的业绩表现如何？",
            "茅台股票值得投资吗？", 
            "新能源汽车行业前景怎么样？",
            "银行股现在是买入的好时机吗？",
            "科技股的风险有哪些？"
        ]
        
        print("\n" + "="*80)
        print("🆚 标准RAG vs 对比学习增强RAG 效果对比")
        print("="*80)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n【测试查询 {i}】: {query}")
            print("-" * 60)
            
            try:
                # 标准RAG查询
                print("🔹 标准RAG结果:")
                standard_response = await self.client.post(
                    f"{self.base_url}/v1/analyse/rag_query",
                    json={
                        "query": query,
                        "user_id": "demo",
                        "use_contrastive_learning": False
                    }
                )
                
                if standard_response.status_code == 200:
                    standard_result = standard_response.json()
                    print(f"  📝 回答: {standard_result['answer'][:150]}...")
                    print(f"  📚 来源数量: {len(standard_result['sources'])}")
                else:
                    print("  ❌ 查询失败")
                
                # 增强RAG查询  
                print("\n🔸 对比学习增强RAG结果:")
                enhanced_response = await self.client.post(
                    f"{self.base_url}/v1/analyse/enhanced_rag_query",
                    params={
                        "query": query,
                        "user_id": "demo",
                        "context_limit": 5,
                        "detect_conflicts": True
                    }
                )
                
                if enhanced_response.status_code == 200:
                    enhanced_result = enhanced_response.json()
                    print(f"  📝 回答: {enhanced_result['answer'][:150]}...")
                    print(f"  📚 来源数量: {len(enhanced_result['sources'])}")
                    print(f"  🔬 增强模式: {enhanced_result.get('enhanced_by_contrastive_learning', False)}")
                    
                    conflicts = enhanced_result.get('potential_conflicts', {})
                    if conflicts.get('high_similarity_opposite_sentiment'):
                        print(f"  ⚠️  检测到 {len(conflicts['high_similarity_opposite_sentiment'])} 个潜在冲突")
                else:
                    print("  ❌ 增强查询失败")
                
            except Exception as e:
                logger.error(f"查询 '{query}' 失败: {e}")
                continue
            
            await asyncio.sleep(1)  # 避免请求过于频繁
    
    async def demo_conflict_detection(self):
        """演示冲突检测功能"""
        logger.info("⚠️  演示冲突检测功能...")
        
        # 构造一些可能产生冲突的查询
        conflict_test_cases = [
            {
                "query": "公司业绩增长情况",
                "description": "测试业绩相关的冲突信息检测"
            },
            {
                "query": "股价技术走势分析", 
                "description": "测试技术分析相关的冲突检测"
            },
            {
                "query": "政策对行业的影响",
                "description": "测试政策相关的冲突信息检测"
            }
        ]
        
        print("\n" + "="*60)
        print("🔍 冲突检测功能演示")
        print("="*60)
        
        for test_case in conflict_test_cases:
            query = test_case["query"]
            description = test_case["description"]
            
            print(f"\n【{description}】")
            print(f"查询: {query}")
            print("-" * 40)
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/v1/analyse/enhanced_rag_query",
                    params={
                        "query": query,
                        "detect_conflicts": True
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    conflicts = result.get('potential_conflicts', {})
                    
                    if conflicts.get('high_similarity_opposite_sentiment'):
                        print("⚠️  发现潜在冲突信息:")
                        for conflict in conflicts['high_similarity_opposite_sentiment']:
                            print(f"  • {conflict}")
                    else:
                        print("✅ 未发现明显冲突")
                else:
                    print("❌ 冲突检测失败")
                    
            except Exception as e:
                logger.error(f"冲突检测失败: {e}")
            
            await asyncio.sleep(0.5)
    
    async def run_complete_demo(self):
        """运行完整演示"""
        print("🎬 A股对比学习RAG增强系统演示")
        print("="*80)
        
        try:
            # 1. 系统状态检查
            status = await self.check_system_status()
            
            if not status["contrastive_learning"]["available"]:
                logger.error("❌ 对比学习功能不可用，请检查依赖")
                return
            
            # 2. 展示样本数据
            await self.show_sample_data()
            
            # 3. 训练模型
            await self.train_contrastive_model(epochs=3, batch_size=16)
            
            # 4. 效果对比
            await self.compare_rag_methods()
            
            # 5. 冲突检测演示
            await self.demo_conflict_detection()
            
            print("\n" + "="*80)
            print("🎉 演示完成！对比学习RAG增强系统已就绪")
            print("="*80)
            
            # 提供使用建议
            print("\n💡 使用建议:")
            print("1. 在正式使用前，建议使用更多epoch训练模型以获得更好效果")
            print("2. 可以通过API接口 /v1/analyse/enhanced_rag_query 使用增强RAG")
            print("3. 启用 detect_conflicts=True 来获得冲突检测能力") 
            print("4. 定期重新训练模型以适应新的市场情况")
            
        except Exception as e:
            logger.error(f"❌ 演示运行失败: {e}")
            raise
        finally:
            await self.client.aclose()

async def main():
    """主函数"""
    demo = ContrastiveLearningDemo()
    await demo.run_complete_demo()

if __name__ == "__main__":
    print("🚀 启动A股对比学习RAG增强演示...")
    asyncio.run(main())
