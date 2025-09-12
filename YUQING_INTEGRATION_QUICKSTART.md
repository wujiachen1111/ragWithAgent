# 🚀 舆情服务 × RAG分析 集成快速启动指南

## ⚡ 一键启动（推荐）

```bash
# 在项目根目录执行
python start_all.py            # 默认启动 yuqing、stock_agent、rag
# 或指定
python start_all.py --services yuqing rag stock_agent
```

## 📋 手动启动步骤

### 1. 启动舆情分析服务 (yuqing-sentiment)
```bash
cd apps/yuqing-sentiment
PYTHONPATH=./src python -m src.main
# 服务运行在 http://localhost:8000
```

### 2. 启动RAG分析服务 (rag-analysis)
```bash
cd apps/rag-analysis
# 确保 yuqing-sentiment 服务正在运行
export YUQING_API_URL="http://localhost:8000"
PYTHONPATH=./src python -m src.main
# 服务运行在 http://localhost:8010
```

### 3. 测试集成效果
```bash
python tools/development/yuqing_integration_demo.py
```

## 🎯 核心功能验证

### API调用示例
```bash
# 1. 检查YuQing-new状态
curl http://localhost:8000/health

# 2. 获取舆情数据（综合：新闻+可用的情感与实体）
curl "http://localhost:8000/api/news/comprehensive?hours=6&limit=5&include_entities=true"

# 3. 执行投资分析
curl -X POST "http://localhost:8010/v1/analysis/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "topic": "某科技公司发布新产品",
       "content": "该公司今日发布革命性产品，市场反应积极",
       "symbols": ["000001", "600036"],
       "time_horizon": "medium"
     }'
```

## 🔍 系统架构概览

```
YuQing-sentiment (localhost:8000)      RAG+Agent (localhost:8010)
├── 📰 新闻采集                      ├── 🔍 数据情报专家 
├── 🤖 AI情感分析          ────────>  ├── 🎭 叙事套利者
├── 🏢 实体识别                      ├── 🔢 量化分析师  
├── 🔥 热点发现                      ├── 🎯 逆向怀疑论者
└── 📊 统计分析                      ├── 🌐 二级效应策略师
                                    ├── 🌍 宏观策略师
                                    ├── 🛡️ 风控官
                                    └── 👑 首席整合官
                                           ↓
                                    📋 投资委员会决策
```

## 🎊 集成效果

### 数据能力提升
- **23个专业API** vs 1个通用API
- **实时5分钟更新** vs 按需更新
- **专业实体识别** vs 基础文本分析
- **多源数据融合** vs 单一数据源

### 分析质量提升  
- **叙事套利者**: 基于真实热点数据分析
- **量化分析师**: 精确的实体影响数据
- **数据情报专家**: 从聚合器升级为专业分析师
- **风控官**: 多维度风险数据支撑

## 🛠️ 故障排除

### 常见问题
1. **端口占用**: 确保8000和8010端口可用
2. **依赖缺失**: 检查两个项目的requirements.txt
3. **配置错误**: 验证环境变量YUQING_API_URL
4. **网络问题**: 检查localhost连通性

### 调试命令
```bash
# 检查端口状态
netstat -an | grep -E "8000|8010"

# 查看服务日志
tail -f logs/yuqing/app.log
# (假设rag-analysis服务也将日志输出到logs目录)
# tail -f logs/rag-analysis/app.log 

# 测试API连通性
curl http://localhost:8000/health
curl http://localhost:8000/api/news/stats
curl http://localhost:8010/
```

## 📞 技术支持

- **完整集成指南**: `apps/rag-analysis/YUQING_INTEGRATION_GUIDE.md`
- **舆情服务API文档**: http://localhost:8000/docs
- **集成测试脚本**: `tools/development/yuqing_integration_demo.py`

---

**🎉 恭喜！您现在拥有了一个融合专业舆情分析与AI投研团队的完整系统！**
