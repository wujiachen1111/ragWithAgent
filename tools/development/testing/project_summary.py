#!/usr/bin/env python3
"""
项目统计脚本
生成项目的代码统计、技术栈分析等信息
"""

import os
import subprocess
from pathlib import Path
from collections import defaultdict
import json

def count_lines_of_code():
    """统计代码行数"""
    extensions = {'.py', '.md', '.yml', '.yaml', '.toml', '.txt', '.sh', '.json'}
    stats = defaultdict(int)
    total_lines = 0
    
    for root, dirs, files in os.walk('.'):
        # 跳过不需要的目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                        ext = Path(file).suffix or 'no_ext'
                        stats[ext] += lines
                        total_lines += lines
                except:
                    continue
    
    return stats, total_lines

def analyze_project_structure():
    """分析项目结构"""
    structure = {
        'services': [],
        'scripts': [],
        'docs': [],
        'config_files': []
    }
    
    # 统计微服务
    services_dir = Path('services')
    if services_dir.exists():
        for service_dir in services_dir.iterdir():
            if service_dir.is_dir():
                py_files = len(list(service_dir.glob('*.py')))
                structure['services'].append({
                    'name': service_dir.name,
                    'python_files': py_files
                })
    
    # 统计脚本
    scripts_dir = Path('scripts')
    if scripts_dir.exists():
        for script in scripts_dir.iterdir():
            if script.is_file():
                structure['scripts'].append(script.name)
    
    # 统计文档
    for file in Path('.').glob('*.md'):
        structure['docs'].append(file.name)
    
    # 统计配置文件
    config_patterns = ['*.yml', '*.yaml', '*.toml', '*.ini', 'Procfile', 'docker-compose*']
    for pattern in config_patterns:
        for file in Path('.').glob(pattern):
            structure['config_files'].append(file.name)
    
    return structure

def get_git_stats():
    """获取Git统计信息"""
    try:
        # 获取提交数量
        commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], 
                                             stderr=subprocess.DEVNULL).decode().strip()
        
        # 获取文件数量
        tracked_files = subprocess.check_output(['git', 'ls-files'], 
                                              stderr=subprocess.DEVNULL).decode().strip().split('\n')
        
        return {
            'commits': int(commit_count) if commit_count.isdigit() else 0,
            'tracked_files': len([f for f in tracked_files if f])
        }
    except:
        return {'commits': 'N/A', 'tracked_files': 'N/A'}

def generate_tech_stack_summary():
    """生成技术栈摘要"""
    tech_stack = {
        'backend_frameworks': ['FastAPI 0.104.1', 'LangChain 0.0.335'],
        'ai_models': ['DeepSeek v3', 'BGE-Large-ZH-v1.5', 'Sentence-Transformers'],
        'databases': ['PostgreSQL 15', 'ChromaDB 0.4.18', 'Redis 7'],
        'development_tools': ['Docker Compose', 'Honcho', 'Alembic', 'Black + Ruff'],
        'languages': ['Python 3.10+'],
        'deployment': ['AWS Lambda', 'AWS EC2', 'AWS RDS', 'Pinecone (生产)']
    }
    return tech_stack

def main():
    """主函数"""
    print("📊 智策 (InsightFolio) 项目统计报告")
    print("=" * 60)
    
    # 代码统计
    print("\n📝 代码统计:")
    code_stats, total_lines = count_lines_of_code()
    print(f"总代码行数: {total_lines:,}")
    for ext, lines in sorted(code_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ext}: {lines:,} 行")
    
    # 项目结构
    print("\n🏗️ 项目结构:")
    structure = analyze_project_structure()
    
    print(f"微服务数量: {len(structure['services'])}")
    for service in structure['services']:
        print(f"  - {service['name']}: {service['python_files']} 个Python文件")
    
    print(f"\n脚本数量: {len(structure['scripts'])}")
    for script in structure['scripts'][:5]:  # 显示前5个
        print(f"  - {script}")
    
    print(f"\n文档数量: {len(structure['docs'])}")
    for doc in structure['docs']:
        print(f"  - {doc}")
    
    print(f"\n配置文件: {len(structure['config_files'])}")
    for config in structure['config_files']:
        print(f"  - {config}")
    
    # Git统计
    print("\n📈 版本控制:")
    git_stats = get_git_stats()
    print(f"Git提交数: {git_stats['commits']}")
    print(f"跟踪文件数: {git_stats['tracked_files']}")
    
    # 技术栈
    print("\n🛠️ 技术栈:")
    tech_stack = generate_tech_stack_summary()
    for category, technologies in tech_stack.items():
        print(f"{category.replace('_', ' ').title()}:")
        for tech in technologies:
            print(f"  - {tech}")
        print()
    
    # 功能特性
    print("🎯 核心功能特性:")
    features = [
        "✅ 微服务架构 (4个核心服务)",
        "✅ RAG检索增强生成",  
        "✅ 股票分析Agent",
        "✅ 实时股票数据集成",
        "✅ DeepSeek v3大模型",
        "✅ 中文语义理解",
        "✅ 向量数据库检索",
        "✅ 智能缓存优化",
        "✅ 异步高性能架构",
        "✅ 完整API文档",
        "✅ 开箱即用演示"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    # 项目规模评估
    print(f"\n📏 项目规模评估:")
    complexity_score = 0
    complexity_score += len(structure['services']) * 10  # 微服务数量
    complexity_score += total_lines // 100  # 代码行数
    complexity_score += len(structure['docs']) * 2  # 文档数量
    
    if complexity_score < 50:
        scale = "小型项目"
    elif complexity_score < 150:
        scale = "中型项目"
    else:
        scale = "大型项目"
    
    print(f"项目规模: {scale} (复杂度分数: {complexity_score})")
    print(f"开发周期估算: 约 {max(1, complexity_score // 20)} 人月")
    print(f"团队规模建议: {max(1, len(structure['services']))} - {len(structure['services']) * 2} 人")
    
    # 生成JSON报告
    report = {
        'timestamp': str(subprocess.check_output(['date'], stderr=subprocess.DEVNULL).decode().strip()),
        'code_stats': dict(code_stats),
        'total_lines': total_lines,
        'structure': structure,
        'git_stats': git_stats,
        'tech_stack': tech_stack,
        'complexity_score': complexity_score,
        'project_scale': scale
    }
    
    with open('project_summary.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存到: project_summary.json")
    print("\n" + "=" * 60)
    print("✨ 项目统计完成！")

if __name__ == "__main__":
    main()
