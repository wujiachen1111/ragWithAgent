#!/usr/bin/env python3
"""
简化的对比学习RAG测试脚本
用于快速验证对比学习功能是否正常工作
"""

import asyncio
import httpx
import json

async def test_contrastive_learning():
    """测试对比学习功能"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🚀 开始测试A股对比学习RAG增强功能")
        print("="*60)
        
        # 1. 检查状态
        print("1️⃣ 检查系统状态...")
        try:
            response = await client.get(f"{base_url}/v1/contrastive_learning/status")
            status = response.json()
            print(f"   ✅ 功能可用: {status['available']}")
            print(f"   ✅ 增强器已初始化: {status['enhancer_initialized']}")
            print(f"   ✅ 样本数量: {status['sample_count']}")
        except Exception as e:
            print(f"   ❌ 状态检查失败: {e}")
            return
        
        # 2. 快速训练（仅演示）
        print("\n2️⃣ 快速训练模型...")
        try:
            response = await client.post(
                f"{base_url}/v1/contrastive_learning/train",
                params={"epochs": 2, "batch_size": 8}  # 快速训练参数
            )
            if response.status_code == 200:
                result = response.json()
                print("   ✅ 模型训练完成")
                if "training_report" in result:
                    report = result["training_report"]
                    if report.get("final_accuracy"):
                        print(f"   📊 最终准确率: {report['final_accuracy']:.3f}")
            else:
                print(f"   ⚠️ 训练失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ 训练异常: {e}")
        
        # 3. 测试增强查询
        print("\n3️⃣ 测试增强RAG查询...")
        test_query = "公司业绩表现如何？是否值得投资？"
        
        try:
            response = await client.post(
                f"{base_url}/v1/analyse/enhanced_rag_query",
                params={
                    "query": test_query,
                    "detect_conflicts": True
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 查询成功")
                print(f"   📝 问题: {test_query}")
                print(f"   🤖 回答: {result.get('answer', 'N/A')[:100]}...")
                print(f"   🔬 使用增强: {result.get('enhanced_by_contrastive_learning', False)}")
                
                conflicts = result.get('potential_conflicts', {})
                if conflicts.get('high_similarity_opposite_sentiment'):
                    print(f"   ⚠️ 发现 {len(conflicts['high_similarity_opposite_sentiment'])} 个潜在冲突")
                
                print(f"   📚 检索到 {len(result.get('sources', []))} 个相关文档")
            else:
                print(f"   ❌ 查询失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"   ❌ 查询异常: {e}")
        
        # 4. 对比标准RAG
        print("\n4️⃣ 对比标准RAG...")
        try:
            response = await client.post(
                f"{base_url}/v1/analyse/rag_query",
                json={
                    "query": test_query,
                    "user_id": "test",
                    "use_contrastive_learning": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 标准RAG查询成功")
                print(f"   🤖 回答: {result.get('answer', 'N/A')[:100]}...")
                print(f"   📚 检索到 {len(result.get('sources', []))} 个相关文档")
            else:
                print(f"   ❌ 标准RAG查询失败")
        except Exception as e:
            print(f"   ⚠️ 标准RAG查询异常: {e}")
        
        print("\n" + "="*60)
        print("🎉 测试完成！")
        print("\n💡 如需详细演示，请运行:")
        print("   python scripts/contrastive_learning_demo.py")

if __name__ == "__main__":
    asyncio.run(test_contrastive_learning())
