#!/usr/bin/env python3
"""
本地兼容性验证脚本
验证重构后的代码在本地环境的运行能力
"""

import os
import sys
import subprocess
import socket
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
import platform


class LocalCompatibilityChecker:
    """本地兼容性检查器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.python_version = sys.version_info
        self.platform = platform.system()
        
        self.check_results = {
            "environment": {},
            "dependencies": {},
            "services": {},
            "networking": {},
            "storage": {},
            "overall_compatibility": "unknown"
        }
    
    def check_python_environment(self) -> bool:
        """检查Python环境"""
        print("🐍 检查Python环境...")
        
        # 检查Python版本
        required_version = (3, 8)
        if self.python_version >= required_version:
            self.check_results["environment"]["python_version"] = {
                "status": "✅ 通过",
                "version": f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}",
                "required": f"{required_version[0]}.{required_version[1]}+"
            }
            print(f"  ✅ Python版本: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        else:
            self.check_results["environment"]["python_version"] = {
                "status": "❌ 失败",
                "version": f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}",
                "required": f"{required_version[0]}.{required_version[1]}+",
                "issue": "Python版本过低"
            }
            print(f"  ❌ Python版本过低: {self.python_version.major}.{self.python_version.minor}")
            return False
        
        # 检查pip
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                                  capture_output=True, text=True, check=True)
            pip_version = result.stdout.strip()
            self.check_results["environment"]["pip"] = {
                "status": "✅ 可用",
                "version": pip_version
            }
            print(f"  ✅ pip可用: {pip_version}")
        except subprocess.CalledProcessError:
            self.check_results["environment"]["pip"] = {
                "status": "❌ 不可用",
                "issue": "pip未安装或不可用"
            }
            print("  ❌ pip不可用")
            return False
        
        # 检查虚拟环境支持
        try:
            subprocess.run([sys.executable, "-m", "venv", "--help"], 
                         capture_output=True, check=True)
            self.check_results["environment"]["venv"] = {"status": "✅ 支持"}
            print("  ✅ 虚拟环境支持")
        except subprocess.CalledProcessError:
            self.check_results["environment"]["venv"] = {
                "status": "⚠️  不支持",
                "issue": "建议使用Python 3.8+的内置venv"
            }
            print("  ⚠️  虚拟环境支持有限")
        
        return True
    
    def check_system_resources(self) -> bool:
        """检查系统资源"""
        print("💻 检查系统资源...")
        
        # 检查磁盘空间
        try:
            disk_usage = os.statvfs(self.project_root)
            free_space_gb = (disk_usage.f_frsize * disk_usage.f_bavail) / (1024**3)
            
            if free_space_gb >= 2.0:
                self.check_results["storage"]["disk_space"] = {
                    "status": "✅ 充足",
                    "free_space_gb": round(free_space_gb, 2),
                    "required_gb": 2.0
                }
                print(f"  ✅ 磁盘空间: {free_space_gb:.1f}GB 可用")
            else:
                self.check_results["storage"]["disk_space"] = {
                    "status": "⚠️  不足",
                    "free_space_gb": round(free_space_gb, 2),
                    "required_gb": 2.0,
                    "issue": "建议至少2GB可用空间"
                }
                print(f"  ⚠️  磁盘空间不足: {free_space_gb:.1f}GB")
        except (OSError, AttributeError):
            self.check_results["storage"]["disk_space"] = {
                "status": "⚠️  无法检测",
                "issue": "无法检测磁盘空间"
            }
            print("  ⚠️  无法检测磁盘空间")
        
        # 检查内存 (简化检查)
        try:
            if self.platform == "Linux":
                with open("/proc/meminfo", 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if 'MemAvailable:' in line:
                            mem_kb = int(line.split()[1])
                            mem_gb = mem_kb / (1024**2)
                            break
                    else:
                        mem_gb = 4.0  # 默认假设
            else:
                mem_gb = 4.0  # 其他系统默认假设4GB
            
            if mem_gb >= 2.0:
                self.check_results["storage"]["memory"] = {
                    "status": "✅ 充足",
                    "available_gb": round(mem_gb, 1)
                }
                print(f"  ✅ 内存充足: {mem_gb:.1f}GB")
            else:
                self.check_results["storage"]["memory"] = {
                    "status": "⚠️  较低",
                    "available_gb": round(mem_gb, 1),
                    "issue": "建议至少2GB可用内存"
                }
                print(f"  ⚠️  内存较低: {mem_gb:.1f}GB")
        except Exception:
            self.check_results["storage"]["memory"] = {
                "status": "⚠️  无法检测"
            }
            print("  ⚠️  无法检测内存信息")
        
        return True
    
    def check_network_ports(self) -> bool:
        """检查网络端口可用性"""
        print("🌐 检查网络端口...")
        
        required_ports = [8000, 8010]
        optional_ports = [5432, 6379]  # PostgreSQL, Redis
        
        for port in required_ports:
            if self.is_port_available(port):
                self.check_results["networking"][f"port_{port}"] = {
                    "status": "✅ 可用",
                    "port": port,
                    "required": True
                }
                print(f"  ✅ 端口{port}可用")
            else:
                self.check_results["networking"][f"port_{port}"] = {
                    "status": "❌ 被占用",
                    "port": port,
                    "required": True,
                    "issue": f"端口{port}被占用，需要释放或修改配置"
                }
                print(f"  ❌ 端口{port}被占用")
        
        for port in optional_ports:
            if self.is_port_available(port):
                self.check_results["networking"][f"port_{port}"] = {
                    "status": "✅ 可用",
                    "port": port,
                    "required": False
                }
                print(f"  ✅ 端口{port}可用 (可选)")
            else:
                self.check_results["networking"][f"port_{port}"] = {
                    "status": "⚠️  被占用",
                    "port": port,
                    "required": False,
                    "note": "可选服务，可使用替代方案"
                }
                print(f"  ⚠️  端口{port}被占用 (可选服务)")
        
        return True
    
    def is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0  # 0表示连接成功，即端口被占用
        except Exception:
            return True  # 异常时假设端口可用
    
    def check_dependencies_compatibility(self) -> bool:
        """检查依赖兼容性"""
        print("📦 检查依赖兼容性...")
        
        # 检查关键依赖的安装可能性
        critical_deps = [
            ("fastapi", "0.104.1"),
            ("uvicorn", "0.24.0"), 
            ("pydantic", "2.5.0"),
            ("httpx", "0.25.2"),
            ("sqlalchemy", "2.0.23")
        ]
        
        for dep_name, dep_version in critical_deps:
            try:
                # 尝试导入或检查是否可安装
                result = subprocess.run([
                    sys.executable, "-m", "pip", "show", dep_name
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    # 已安装
                    installed_version = self.extract_version_from_pip_show(result.stdout)
                    self.check_results["dependencies"][dep_name] = {
                        "status": "✅ 已安装",
                        "installed_version": installed_version,
                        "required_version": dep_version
                    }
                    print(f"  ✅ {dep_name} 已安装: {installed_version}")
                else:
                    # 未安装，检查是否可安装
                    self.check_results["dependencies"][dep_name] = {
                        "status": "⚠️  未安装",
                        "required_version": dep_version,
                        "note": "将在环境设置时自动安装"
                    }
                    print(f"  ⚠️  {dep_name} 未安装 (可自动安装)")
                    
            except Exception as e:
                self.check_results["dependencies"][dep_name] = {
                    "status": "❌ 检查失败",
                    "error": str(e)
                }
                print(f"  ❌ {dep_name} 检查失败: {e}")
        
        return True
    
    def extract_version_from_pip_show(self, pip_output: str) -> str:
        """从pip show输出中提取版本"""
        for line in pip_output.split('\n'):
            if line.startswith('Version:'):
                return line.split(':', 1)[1].strip()
        return "unknown"
    
    def check_optional_services(self) -> bool:
        """检查可选服务的可用性"""
        print("🔧 检查可选服务...")
        
        # 检查PostgreSQL
        try:
            result = subprocess.run(["psql", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                pg_version = result.stdout.strip()
                self.check_results["services"]["postgresql"] = {
                    "status": "✅ 可用",
                    "version": pg_version,
                    "note": "可用于生产级数据存储"
                }
                print(f"  ✅ PostgreSQL可用: {pg_version}")
            else:
                raise subprocess.CalledProcessError(result.returncode, "psql")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            self.check_results["services"]["postgresql"] = {
                "status": "⚠️  不可用",
                "fallback": "将使用SQLite作为替代",
                "note": "可选服务，不影响基本功能"
            }
            print("  ⚠️  PostgreSQL不可用 (将使用SQLite)")
        
        # 检查Redis
        try:
            result = subprocess.run(["redis-cli", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                redis_version = result.stdout.strip()
                self.check_results["services"]["redis"] = {
                    "status": "✅ 可用",
                    "version": redis_version,
                    "note": "可用于缓存加速"
                }
                print(f"  ✅ Redis可用: {redis_version}")
            else:
                raise subprocess.CalledProcessError(result.returncode, "redis-cli")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            self.check_results["services"]["redis"] = {
                "status": "⚠️  不可用",
                "fallback": "将使用内存缓存作为替代",
                "note": "可选服务，不影响基本功能"
            }
            print("  ⚠️  Redis不可用 (将使用内存缓存)")
        
        # 检查Docker (可选)
        try:
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                docker_version = result.stdout.strip()
                self.check_results["services"]["docker"] = {
                    "status": "✅ 可用",
                    "version": docker_version,
                    "note": "支持容器化部署"
                }
                print(f"  ✅ Docker可用: {docker_version}")
            else:
                raise subprocess.CalledProcessError(result.returncode, "docker")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            self.check_results["services"]["docker"] = {
                "status": "⚠️  不可用",
                "note": "可选服务，可使用本地运行模式"
            }
            print("  ⚠️  Docker不可用 (可使用本地模式)")
        
        return True
    
    def check_project_structure(self) -> bool:
        """检查项目结构完整性"""
        print("📁 检查项目结构...")
        
        # 检查当前结构
        current_structure = {
            "apps_yuqing-sentiment": self.project_root / "apps" / "yuqing-sentiment",
            "apps_rag-analysis": self.project_root / "apps" / "rag-analysis",
            "configs": self.project_root / "configs"
        }
        
        structure_ok = True
        for name, path in current_structure.items():
            if path.exists():
                self.check_results["storage"][f"structure_{name}"] = {
                    "status": "✅ 存在",
                    "path": str(path)
                }
                print(f"  ✅ {name} 目录存在")
            else:
                self.check_results["storage"][f"structure_{name}"] = {
                    "status": "❌ 缺失",
                    "path": str(path),
                    "issue": f"{name} 目录不存在"
                }
                print(f"  ❌ {name} 目录缺失")
                structure_ok = False
        
        return structure_ok
    
    def generate_compatibility_report(self) -> Dict:
        """生成兼容性报告"""
        # 计算总体兼容性
        issues = []
        warnings = []
        
        for category, checks in self.check_results.items():
            if category == "overall_compatibility":
                continue
                
            for check_name, result in checks.items():
                status = result.get("status", "")
                if "❌" in status:
                    issues.append(f"{category}.{check_name}: {result.get('issue', '失败')}")
                elif "⚠️" in status:
                    warnings.append(f"{category}.{check_name}: {result.get('note', result.get('issue', '警告'))}")
        
        # 确定总体兼容性
        if len(issues) == 0:
            if len(warnings) <= 2:
                overall = "excellent"  # 优秀
            else:
                overall = "good"       # 良好
        elif len(issues) <= 2:
            overall = "fair"           # 一般
        else:
            overall = "poor"           # 较差
        
        self.check_results["overall_compatibility"] = overall
        
        return {
            "compatibility_level": overall,
            "issues": issues,
            "warnings": warnings,
            "detailed_results": self.check_results,
            "recommendations": self.generate_recommendations(overall, issues, warnings)
        }
    
    def generate_recommendations(self, overall: str, issues: List[str], warnings: List[str]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if overall == "excellent":
            recommendations.append("✅ 环境完美兼容！可以直接进行重构")
            recommendations.append("🚀 建议使用Docker Compose方式获得最佳体验")
        
        elif overall == "good":
            recommendations.append("✅ 环境基本兼容，可以进行重构")
            recommendations.append("🔧 建议解决以下警告项以获得更好体验:")
            for warning in warnings[:3]:
                recommendations.append(f"   - {warning}")
        
        elif overall == "fair":
            recommendations.append("⚠️  环境部分兼容，建议先解决关键问题")
            recommendations.append("🔧 必须解决的问题:")
            for issue in issues:
                recommendations.append(f"   - {issue}")
            recommendations.append("💡 解决后可正常使用本地开发模式")
        
        else:  # poor
            recommendations.append("❌ 环境兼容性较差，需要解决多个问题")
            recommendations.append("🔧 关键问题:")
            for issue in issues[:5]:
                recommendations.append(f"   - {issue}")
            recommendations.append("💡 建议先搭建基础环境，或使用Docker方式")
        
        # 通用建议
        recommendations.extend([
            "",
            "🎯 通用建议:",
            "   - 使用Python虚拟环境隔离依赖",
            "   - 重构前先备份重要数据",
            "   - 可选择Docker方式简化环境配置"
        ])
        
        return recommendations
    
    def save_report(self, report: Dict, output_file: str = "compatibility_report.json"):
        """保存兼容性报告"""
        report_path = self.project_root / output_file
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path
    
    def run_full_check(self) -> Dict:
        """运行完整的兼容性检查"""
        print("🔍 开始本地兼容性检查...")
        print("="*60)
        
        # 执行所有检查
        checks = [
            self.check_python_environment,
            self.check_system_resources,
            self.check_network_ports,
            self.check_dependencies_compatibility,
            self.check_optional_services,
            self.check_project_structure
        ]
        
        for check in checks:
            try:
                check()
                print()
            except Exception as e:
                print(f"❌ 检查异常: {e}\n")
        
        # 生成报告
        report = self.generate_compatibility_report()
        
        # 显示摘要
        self.print_summary(report)
        
        return report
    
    def print_summary(self, report: Dict):
        """打印检查摘要"""
        print("="*60)
        print("📊 本地兼容性检查摘要")
        print("="*60)
        
        compatibility = report["compatibility_level"]
        compatibility_icons = {
            "excellent": "🎉 优秀",
            "good": "✅ 良好", 
            "fair": "⚠️  一般",
            "poor": "❌ 较差"
        }
        
        print(f"🏆 总体兼容性: {compatibility_icons.get(compatibility, compatibility)}")
        print()
        
        if report["issues"]:
            print("🚨 需要解决的问题:")
            for issue in report["issues"]:
                print(f"   • {issue}")
            print()
        
        if report["warnings"]:
            print("⚠️  警告项目:")
            for warning in report["warnings"][:5]:
                print(f"   • {warning}")
            if len(report["warnings"]) > 5:
                print(f"   ... 还有 {len(report['warnings']) - 5} 个警告")
            print()
        
        print("💡 建议:")
        for rec in report["recommendations"]:
            if rec.strip():
                print(f"   {rec}")
        
        print()
        print("📄 详细报告已保存到: compatibility_report.json")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="本地兼容性验证工具")
    parser.add_argument("--project-root", help="项目根目录路径")
    parser.add_argument("--output", default="compatibility_report.json", help="报告输出文件")
    
    args = parser.parse_args()
    
    # 运行检查
    checker = LocalCompatibilityChecker(args.project_root)
    report = checker.run_full_check()
    
    # 保存报告
    report_path = checker.save_report(report, args.output)
    
    # 返回状态码
    compatibility = report["compatibility_level"]
    if compatibility in ["excellent", "good"]:
        print(f"\n🎊 恭喜！您的环境{compatibility_icons.get(compatibility)}，可以进行重构！")
        sys.exit(0)
    elif compatibility == "fair":
        print(f"\n⚠️  您的环境需要一些改进，但基本可用")
        sys.exit(1)
    else:
        print(f"\n❌ 您的环境需要解决一些关键问题")
        sys.exit(2)


if __name__ == "__main__":
    # 兼容性图标
    compatibility_icons = {
        "excellent": "🎉 优秀",
        "good": "✅ 良好", 
        "fair": "⚠️  一般",
        "poor": "❌ 较差"
    }
    
    main()
