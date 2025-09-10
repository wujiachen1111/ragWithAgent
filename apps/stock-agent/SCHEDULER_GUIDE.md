# Stock Agent 股票数据刷新触发器使用指南

## 🎯 功能概述

Stock Agent 现在支持股票数据的自动刷新功能，包括：

1. **定时全局刷新**: 每周一到周五下午3点自动刷新所有股票数据
2. **单只股票刷新**: 按需刷新指定股票的数据
3. **任务状态跟踪**: 监控刷新任务的执行状态和结果

## ⚙️ 配置说明

### 调度器配置

调度器支持以下配置选项：

```python
class SchedulerConfig:
    enabled: bool = True                              # 是否启用调度器
    global_refresh_time: str = "15:00"               # 全局刷新时间 (HH:MM)
    global_refresh_weekdays: List[int] = [1,2,3,4,5] # 刷新工作日 (1=周一)
    timezone: str = "Asia/Shanghai"                   # 时区
    max_concurrent_tasks: int = 1                     # 最大并发任务数
```

### 环境变量配置

可以通过环境变量自定义调度器行为：

```bash
# 启用/禁用调度器
SCHEDULER_ENABLED=true

# 全局刷新时间 (24小时制)
SCHEDULER_GLOBAL_REFRESH_TIME=15:00

# 时区设置
SCHEDULER_TIMEZONE=Asia/Shanghai
```

## 🚀 启动服务

### 1. 安装依赖

确保安装了调度器相关依赖：

```bash
cd apps/stock-agent
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python src/main.py
```

服务启动时会自动：
- 连接数据库
- 启动股票刷新调度器
- 安排定时全局刷新任务

## 📡 API 接口

### 1. 刷新单只股票数据

```bash
# 刷新指定股票数据
POST /api/v1/stocks/refresh/single/{stock_code}

# 示例：刷新平安银行数据
curl -X POST "http://localhost:8020/api/v1/stocks/refresh/single/000001"
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "task_id": "single_refresh_000001_abc123",
    "stock_code": "000001",
    "status": "completed",
    "start_time": "2024-01-15T10:30:00",
    "result": {
      "total": 1,
      "success": 1,
      "failed": 0,
      "success_rate": 1.0
    }
  },
  "message": "股票 000001 刷新任务已完成"
}
```

### 2. 触发全局刷新

```bash
# 手动触发全局刷新
POST /api/v1/stocks/refresh/global

curl -X POST "http://localhost:8020/api/v1/stocks/refresh/global"
```

### 3. 查看刷新任务

```bash
# 获取最近的刷新任务列表
GET /api/v1/stocks/refresh/tasks?limit=10

# 获取指定任务状态
GET /api/v1/stocks/refresh/tasks/{task_id}
```

### 4. 调度器状态

```bash
# 获取调度器运行状态
GET /api/v1/stocks/scheduler/status

curl "http://localhost:8020/api/v1/stocks/scheduler/status"
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "running": true,
    "config": {
      "enabled": true,
      "global_refresh_time": "15:00",
      "global_refresh_weekdays": [1, 2, 3, 4, 5],
      "timezone": "Asia/Shanghai"
    },
    "running_tasks": 0,
    "next_global_refresh": "2024-01-16T15:00:00+08:00",
    "jobs": [
      {
        "id": "global_refresh",
        "name": "全局股票数据刷新",
        "next_run_time": "2024-01-16T15:00:00+08:00"
      }
    ]
  },
  "message": "调度器状态获取成功"
}
```

## 🧪 测试功能

### 运行测试脚本

```bash
cd apps/stock-agent
python test_scheduler.py
```

测试脚本会验证：
- 调度器基本功能
- 调度器生命周期管理
- 单只股票刷新功能

### 手动测试步骤

1. **启动服务**
   ```bash
   python src/main.py
   ```

2. **检查调度器状态**
   ```bash
   curl "http://localhost:8020/api/v1/stocks/scheduler/status"
   ```

3. **测试单只股票刷新**
   ```bash
   curl -X POST "http://localhost:8020/api/v1/stocks/refresh/single/000001"
   ```

4. **查看任务列表**
   ```bash
   curl "http://localhost:8020/api/v1/stocks/refresh/tasks"
   ```

## 📊 监控和日志

### 日志信息

调度器会输出详细的日志信息：

```
📅 股票刷新调度器启动成功
📅 已安排全局刷新任务: 每周 [1, 2, 3, 4, 5] 的 15:00
🔄 开始执行全局股票数据刷新 - 任务ID: global_refresh_abc123
📊 准备刷新 4000 只股票的数据
✅ 全局股票数据刷新完成 - 成功: 3950/4000
```

### 数据库存储

刷新任务信息会存储在 MongoDB 的 `tasks` 集合中：

```javascript
{
  "task_id": "single_refresh_000001_abc123",
  "task_type": "single_refresh",
  "stock_code": "000001",
  "status": "completed",
  "created_time": "2024-01-15T10:30:00Z",
  "start_time": "2024-01-15T10:30:01Z",
  "end_time": "2024-01-15T10:30:05Z",
  "duration": 4.2,
  "result": {
    "total": 1,
    "success": 1,
    "failed": 0,
    "success_rate": 1.0,
    "processed_codes": ["000001"],
    "failed_codes": []
  }
}
```

## 🔧 故障排除

### 常见问题

1. **调度器启动失败**
   - 检查数据库连接是否正常
   - 确认时区设置是否正确
   - 查看日志中的错误信息

2. **定时任务不执行**
   - 确认调度器配置中 `enabled=true`
   - 检查时间和工作日设置
   - 查看调度器状态接口

3. **单只股票刷新失败**
   - 检查股票代码是否正确
   - 确认网络连接和数据源可用
   - 查看任务详细错误信息

### 调试模式

启动服务时可以启用调试模式：

```bash
STOCK_API_DEBUG=true python src/main.py
```

## 🎯 最佳实践

1. **监控调度器状态**
   - 定期检查调度器运行状态
   - 监控任务执行成功率
   - 关注任务执行时间

2. **数据库维护**
   - 定期清理旧的任务记录
   - 监控数据库存储空间
   - 备份重要的股票数据

3. **性能优化**
   - 根据系统负载调整批处理大小
   - 合理设置并发任务数量
   - 监控内存和CPU使用情况

## 📋 API 文档

完整的 API 文档可通过以下方式访问：

- Swagger UI: http://localhost:8020/docs
- ReDoc: http://localhost:8020/redoc

## 🎉 总结

通过以上配置，Stock Agent 现在具备了完整的股票数据刷新触发器功能：

✅ **自动定时刷新**: 每工作日下午3点自动刷新所有股票数据  
✅ **按需刷新**: 支持单只股票的即时数据刷新  
✅ **任务跟踪**: 完整的任务状态监控和历史记录  
✅ **灵活配置**: 支持自定义刷新时间和工作日  
✅ **RESTful API**: 标准化的HTTP接口，易于集成  

这套触发器系统可以确保股票数据的及时性和准确性，为RAG+Agent系统提供可靠的数据支撑。
