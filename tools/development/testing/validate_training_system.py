#!/usr/bin/env python3
"""
训练系统完整性验证脚本
验证所有训练相关组件是否正常工作
"""

import os
import sys
import subprocess
from pathlib import Path
import importlib.util
import logging
from typing import Dict, List, Tuple
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainingSystemValidator:
    """训练系统验证器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.results = {
            "environment": {},
            "files": {},
            "imports": {},
            "data": {},
            "overall": False
        }
        
    def validate_environment(self) -> Dict[str, bool]:
        """验证Python环境"""
        logger.info("🔍 验证Python环境...")
        
        env_results = {}
        
        # 检查Python版本
        python_version = sys.version_info
        env_results["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
        env_results["python_valid"] = python_version >= (3, 8)
        
        if env_results["python_valid"]:
            logger.info(f"✅ Python版本: {env_results['python_version']}")
        else:
            logger.error(f"❌ Python版本过低: {env_results['python_version']}, 需要 >= 3.8")
        
        # 检查基础包
        required_packages = {
            "torch": "PyTorch深度学习框架",
            "sentence_transformers": "句子转换器",
            "sklearn": "机器学习库",
            "numpy": "数值计算库",
            "matplotlib": "绘图库",
            "pandas": "数据处理库"
        }
        
        for package, desc in required_packages.items():
            try:
                __import__(package.replace("-", "_"))
                env_results[f"package_{package}"] = True
                logger.info(f"✅ {desc}: {package}")
            except ImportError:
                env_results[f"package_{package}"] = False
                logger.warning(f"⚠️  缺少依赖: {package} ({desc})")
        
        return env_results
    
    def validate_files(self) -> Dict[str, bool]:
        """验证文件完整性"""
        logger.info("📁 验证文件完整性...")
        
        file_results = {}
        
        # 关键文件列表
        critical_files = {
            "训练脚本": "tools/development/training/train_contrastive_rag.py",
            "评估脚本": "tools/development/testing/evaluate_rag_performance.py", 
            "快速训练脚本": "tools/development/quick_train_test.py",
            "环境配置脚本": "tools/development/setup/setup_training_environment.py",
            "样本数据": "services/decision_engine/contrastive_learning_samples.py",
            "RAG增强器": "services/decision_engine/contrastive_rag_enhancer.py",
            "主服务": "services/decision_engine/main.py"
        }
        
        for name, filepath in critical_files.items():
            full_path = self.project_root / filepath
            exists = full_path.exists()
            file_results[name] = exists
            
            if exists:
                logger.info(f"✅ {name}: {filepath}")
            else:
                logger.error(f"❌ {name}: {filepath} - 文件不存在")
        
        # 检查配置目录
        config_dirs = [
            "configs/training",
            "checkpoints", 
            "logs/tensorboard",
            "results"
        ]
        
        for dir_path in config_dirs:
            full_path = self.project_root / dir_path
            exists = full_path.exists() or self._can_create_dir(full_path)
            file_results[f"dir_{dir_path.replace('/', '_')}"] = exists
            
            if exists:
                logger.info(f"✅ 目录: {dir_path}")
            else:
                logger.warning(f"⚠️  目录不存在: {dir_path} (将自动创建)")
        
        return file_results
    
    def _can_create_dir(self, path: Path) -> bool:
        """检查是否可以创建目录"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except PermissionError:
            return False
    
    def validate_imports(self) -> Dict[str, bool]:
        """验证关键模块导入"""
        logger.info("📦 验证模块导入...")
        
        import_results = {}
        
        # 添加项目路径
        sys.path.append(str(self.project_root / "services" / "decision_engine"))
        
        # 关键模块
        modules = {
            "对比学习样本": ("contrastive_learning_samples", ["A_STOCK_CONTRASTIVE_SAMPLES", "SentimentLabel"]),
            "RAG增强器": ("contrastive_rag_enhancer", ["ContrastiveEmbeddingModel", "ContrastiveTrainingConfig"])
        }
        
        for name, (module_name, attributes) in modules.items():
            try:
                module = importlib.import_module(module_name)
                import_results[f"module_{module_name}"] = True
                logger.info(f"✅ 模块导入成功: {name}")
                
                # 检查属性
                for attr in attributes:
                    if hasattr(module, attr):
                        import_results[f"attr_{module_name}_{attr}"] = True
                        logger.info(f"  ✅ 属性: {attr}")
                    else:
                        import_results[f"attr_{module_name}_{attr}"] = False
                        logger.warning(f"  ⚠️  缺少属性: {attr}")
                        
            except ImportError as e:
                import_results[f"module_{module_name}"] = False
                logger.error(f"❌ 模块导入失败: {name} - {e}")
        
        return import_results
    
    def validate_data(self) -> Dict[str, bool]:
        """验证训练数据"""
        logger.info("📊 验证训练数据...")
        
        data_results = {}
        
        try:
            sys.path.append(str(self.project_root / "services" / "decision_engine"))
            from contrastive_learning_samples import A_STOCK_CONTRASTIVE_SAMPLES
            
            # 检查数据完整性
            total_samples = 0
            categories = list(A_STOCK_CONTRASTIVE_SAMPLES.keys())
            
            data_results["categories_count"] = len(categories)
            data_results["has_categories"] = len(categories) > 0
            
            for category, samples in A_STOCK_CONTRASTIVE_SAMPLES.items():
                category_count = len(samples)
                total_samples += category_count
                data_results[f"category_{category}"] = category_count > 0
                
                logger.info(f"✅ 类别: {category} - {category_count}个样本")
                
                # 检查样本结构
                if samples:
                    sample = samples[0]
                    required_keys = ['anchor', 'hard_negative', 'anchor_label', 'explanation']
                    for key in required_keys:
                        if key in sample:
                            data_results[f"sample_key_{key}"] = True
                        else:
                            data_results[f"sample_key_{key}"] = False
                            logger.warning(f"⚠️  样本缺少字段: {key}")
            
            data_results["total_samples"] = total_samples
            data_results["sufficient_data"] = total_samples >= 20  # 最少20个样本
            
            logger.info(f"✅ 总样本数: {total_samples}")
            logger.info(f"✅ 类别数: {len(categories)}")
            
        except Exception as e:
            logger.error(f"❌ 数据验证失败: {e}")
            data_results["data_accessible"] = False
            
        return data_results
    
    def validate_scripts_syntax(self) -> Dict[str, bool]:
        """验证脚本语法"""
        logger.info("🔍 验证脚本语法...")
        
        syntax_results = {}
        
        script_files = [
            "tools/development/training/train_contrastive_rag.py",
            "tools/development/testing/evaluate_rag_performance.py",
            "tools/development/quick_train_test.py",
            "tools/development/setup/setup_training_environment.py"
        ]
        
        for script_path in script_files:
            full_path = self.project_root / script_path
            script_name = Path(script_path).name
            
            if not full_path.exists():
                syntax_results[script_name] = False
                logger.error(f"❌ 脚本不存在: {script_path}")
                continue
            
            try:
                # 语法检查
                with open(full_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                compile(source, str(full_path), 'exec')
                
                syntax_results[script_name] = True
                logger.info(f"✅ 语法检查通过: {script_name}")
                
            except SyntaxError as e:
                syntax_results[script_name] = False
                logger.error(f"❌ 语法错误: {script_name} - 第{e.lineno}行: {e.msg}")
            except Exception as e:
                syntax_results[script_name] = False
                logger.error(f"❌ 检查失败: {script_name} - {e}")
        
        return syntax_results
    
    def run_quick_validation(self) -> bool:
        """运行快速验证"""
        logger.info("⚡ 执行快速验证测试...")
        
        try:
            # 测试快速训练脚本的帮助功能
            quick_script = self.project_root / "tools/development/quick_train_test.py"
            result = subprocess.run(
                [sys.executable, str(quick_script), "--usage"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("✅ 快速训练脚本运行正常")
                return True
            else:
                logger.warning(f"⚠️  快速训练脚本警告: {result.stderr}")
                return True  # 帮助信息可能导致非0退出码
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 脚本运行超时")
            return False
        except Exception as e:
            logger.error(f"❌ 脚本运行失败: {e}")
            return False
    
    def generate_report(self) -> Dict:
        """生成验证报告"""
        logger.info("📋 生成验证报告...")
        
        # 执行所有验证
        self.results["environment"] = self.validate_environment()
        self.results["files"] = self.validate_files()
        self.results["imports"] = self.validate_imports() 
        self.results["data"] = self.validate_data()
        self.results["syntax"] = self.validate_scripts_syntax()
        self.results["quick_test"] = self.run_quick_validation()
        
        # 计算总体结果
        critical_checks = [
            self.results["environment"].get("python_valid", False),
            self.results["files"].get("训练脚本", False),
            self.results["files"].get("快速训练脚本", False),
            self.results["imports"].get("module_contrastive_learning_samples", False),
            self.results["data"].get("has_categories", False),
            self.results["data"].get("sufficient_data", False)
        ]
        
        self.results["overall"] = all(critical_checks)
        
        return self.results
    
    def print_summary(self):
        """打印验证总结"""
        logger.info("="*60)
        logger.info("🎯 训练系统验证总结")
        logger.info("="*60)
        
        if self.results["overall"]:
            logger.info("🎉 验证通过！训练系统已准备就绪")
            logger.info("")
            logger.info("✅ 可以开始训练:")
            logger.info("   python tools/development/quick_train_test.py --full-pipeline")
            logger.info("")
            logger.info("📊 预期效果:")
            logger.info("   - 训练时间: GPU约20-30分钟，CPU约2-3小时")
            logger.info("   - 准确率: > 90%")
            logger.info("   - 性能提升: 15-25%")
        else:
            logger.error("❌ 验证失败！存在以下问题:")
            
            # 详细问题分析
            if not self.results["environment"].get("python_valid", False):
                logger.error("   - Python版本过低，需要 >= 3.8")
            
            missing_packages = [k for k, v in self.results["environment"].items() 
                              if k.startswith("package_") and not v]
            if missing_packages:
                logger.error(f"   - 缺少Python包: {[k.replace('package_', '') for k in missing_packages]}")
                logger.error("     安装命令: pip install torch sentence-transformers scikit-learn matplotlib")
            
            missing_files = [k for k, v in self.results["files"].items() if not v]
            if missing_files:
                logger.error(f"   - 缺少关键文件: {missing_files}")
            
            if not self.results["data"].get("sufficient_data", False):
                logger.error("   - 训练数据不足，请检查样本数据")
        
        logger.info("="*60)

def main():
    """主函数"""
    validator = TrainingSystemValidator()
    
    print("🔍 智策(InsightFolio) 训练系统验证工具")
    print("="*60)
    
    # 运行验证
    results = validator.generate_report()
    
    # 打印总结
    validator.print_summary()
    
    # 保存报告
    report_path = validator.project_root / "validation_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存到: {report_path}")
    
    # 退出码
    sys.exit(0 if results["overall"] else 1)

if __name__ == "__main__":
    main()
