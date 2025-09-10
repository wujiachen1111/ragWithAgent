#!/usr/bin/env python3
"""
股票刷新触发器功能测试脚本
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock.models.base import SchedulerConfig
from stock.services.scheduler import StockRefreshScheduler
from stock.core.database import db_manager
from stock.core.logging import logger


async def test_scheduler_basic():
    """测试调度器基本功能"""
    logger.info("🧪 开始测试调度器基本功能...")
    
    try:
        # 创建调度器配置
        config = SchedulerConfig(
            enabled=True,
            global_refresh_time="15:00",  # 下午3点
            global_refresh_weekdays=[1, 2, 3, 4, 5],  # 周一到周五
            timezone="Asia/Shanghai"
        )
        
        # 创建调度器实例
        scheduler = StockRefreshScheduler(config)
        
        # 获取调度器状态
        status = scheduler.get_scheduler_status()
        logger.info(f"📊 调度器状态: {status}")
        
        logger.info("✅ 调度器基本功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 调度器基本功能测试失败: {e}")
        return False


async def test_single_stock_refresh():
    """测试单只股票刷新"""
    logger.info("🧪 开始测试单只股票刷新功能...")
    
    try:
        # 连接数据库
        if not db_manager.connect():
            logger.error("❌ 数据库连接失败，跳过单只股票刷新测试")
            return False
        
        # 创建调度器
        config = SchedulerConfig(enabled=False)  # 禁用定时任务，只测试手动刷新
        scheduler = StockRefreshScheduler(config)
        
        # 测试刷新单只股票（使用平安银行作为测试）
        test_stock = "000001"
        logger.info(f"🔄 测试刷新股票 {test_stock}...")
        
        task = await scheduler.refresh_single_stock(test_stock)
        
        logger.info(f"📋 刷新任务结果:")
        logger.info(f"   任务ID: {task.task_id}")
        logger.info(f"   股票代码: {task.stock_code}")
        logger.info(f"   状态: {task.status}")
        logger.info(f"   执行时长: {task.duration:.2f}秒" if task.duration else "   执行时长: 未知")
        
        if task.result:
            logger.info(f"   成功率: {task.result.success_rate*100:.1f}%")
        
        if task.status == "completed":
            logger.info("✅ 单只股票刷新测试通过")
            return True
        else:
            logger.error(f"❌ 单只股票刷新测试失败: {task.error_message}")
            return False
        
    except Exception as e:
        logger.error(f"❌ 单只股票刷新测试异常: {e}")
        return False
    finally:
        db_manager.disconnect()


async def test_scheduler_lifecycle():
    """测试调度器生命周期"""
    logger.info("🧪 开始测试调度器生命周期...")
    
    try:
        # 创建调度器
        config = SchedulerConfig(
            enabled=True,
            global_refresh_time="23:59",  # 设置一个不会立即触发的时间
            global_refresh_weekdays=[1, 2, 3, 4, 5]
        )
        scheduler = StockRefreshScheduler(config)
        
        # 启动调度器
        logger.info("🚀 启动调度器...")
        await scheduler.start()
        
        # 等待一秒
        await asyncio.sleep(1)
        
        # 检查状态
        status = scheduler.get_scheduler_status()
        logger.info(f"📊 运行状态: {status['running']}")
        logger.info(f"📊 下次全局刷新时间: {status.get('next_global_refresh', '未设置')}")
        
        # 停止调度器
        logger.info("🛑 停止调度器...")
        await scheduler.stop()
        
        logger.info("✅ 调度器生命周期测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 调度器生命周期测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("🎯 开始股票刷新触发器功能测试")
    logger.info(f"⏰ 测试时间: {datetime.now()}")
    logger.info("=" * 60)
    
    tests = [
        ("调度器基本功能", test_scheduler_basic),
        ("调度器生命周期", test_scheduler_lifecycle),
        ("单只股票刷新", test_single_stock_refresh),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 执行测试: {test_name}")
        logger.info("-" * 40)
        
        result = await test_func()
        results.append((test_name, result))
        
        logger.info("-" * 40)
        logger.info(f"📊 {test_name} 结果: {'✅ 通过' if result else '❌ 失败'}")
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试结果汇总:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    total = len(results)
    logger.info(f"\n🎯 总计: {passed}/{total} 个测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 所有测试通过！触发器功能实现成功！")
        return True
    else:
        logger.error("⚠️ 部分测试失败，请检查相关功能")
        return False


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
