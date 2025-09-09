# MongoDB 配置指南

## 📋 概述

Stock Agent 支持多种 MongoDB 配置方式，包括无认证和有认证模式，支持本地部署、Docker 和云服务。

## ⚙️ 配置方式

### 方式一：使用环境变量（推荐用于简单场景）

在项目根目录创建 `.env` 文件：

```bash
# 基本连接信息
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=stock_db

# 如果需要认证，添加以下配置
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
MONGO_AUTH_SOURCE=admin
```

### 方式二：使用完整 URI（推荐用于复杂场景）

```bash
# 无认证模式
MONGO_URI=mongodb://localhost:27017/stock_db

# 有认证模式
MONGO_URI=mongodb://username:password@localhost:27017/stock_db?authSource=admin

# MongoDB Atlas 云服务
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/stock_db?retryWrites=true&w=majority
```

## 🔧 具体配置示例

### 本地开发（无认证）

```bash
# .env 文件内容
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=stock_dev
STOCK_API_PORT=8020
```

### 本地开发（有认证）

```bash
# .env 文件内容
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=stock_db
MONGO_USERNAME=stock_user
MONGO_PASSWORD=your_password
MONGO_AUTH_SOURCE=admin
STOCK_API_PORT=8020
```

### Docker 部署

```bash
# .env 文件内容
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DATABASE=stock_db
MONGO_USERNAME=stock_user
MONGO_PASSWORD=stock_pass
STOCK_API_PORT=8020
```

### 生产环境

```bash
# .env 文件内容
MONGO_URI=mongodb://prod_user:secure_password@prod-mongodb:27017/stock_production?authSource=admin
STOCK_API_PORT=8020
STOCK_API_DEBUG=false
```

### MongoDB Atlas 云服务

```bash
# .env 文件内容
MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/stock_db?retryWrites=true&w=majority
STOCK_API_PORT=8020
```

## 🛠️ MongoDB 用户创建

如果您的 MongoDB 需要认证，可以使用以下命令创建用户：

### 1. 连接到 MongoDB

```bash
mongo
# 或者如果有认证
mongo -u admin -p --authenticationDatabase admin
```

### 2. 创建数据库和用户

```javascript
// 切换到 admin 数据库
use admin

// 创建用户
db.createUser({
  user: "stock_user",
  pwd: "your_secure_password",
  roles: [
    { role: "readWrite", db: "stock_db" },
    { role: "dbAdmin", db: "stock_db" }
  ]
})

// 验证用户创建成功
db.auth("stock_user", "your_secure_password")
```

### 3. 测试连接

```bash
# 使用新用户连接
mongo -u stock_user -p your_secure_password --authenticationDatabase admin stock_db
```

## 🔒 安全最佳实践

### 1. 密码安全

- 使用强密码（至少12位，包含大小写字母、数字和特殊字符）
- 不要在代码中硬编码密码
- 定期更换密码

### 2. 网络安全

```bash
# 限制 MongoDB 监听地址
# 在 mongod.conf 中设置
net:
  bindIp: 127.0.0.1,10.0.0.100  # 只允许特定IP访问
  port: 27017
```

### 3. 权限控制

```javascript
// 创建只读用户
db.createUser({
  user: "readonly_user",
  pwd: "readonly_password",
  roles: [{ role: "read", db: "stock_db" }]
})

// 创建管理员用户
db.createUser({
  user: "admin_user", 
  pwd: "admin_password",
  roles: [{ role: "dbOwner", db: "stock_db" }]
})
```

### 4. .env 文件安全

```bash
# 设置文件权限（仅所有者可读）
chmod 600 .env

# 确保 .env 在 .gitignore 中
echo ".env" >> .gitignore
```

## 🐛 故障排除

### 连接失败

1. **检查 MongoDB 服务状态**
   ```bash
   # Linux/Mac
   sudo systemctl status mongod
   # 或
   brew services list | grep mongodb
   
   # Windows
   net start MongoDB
   ```

2. **检查端口是否开放**
   ```bash
   telnet localhost 27017
   # 或
   nc -zv localhost 27017
   ```

3. **检查认证信息**
   ```bash
   # 使用 mongo shell 测试连接
   mongo mongodb://username:password@localhost:27017/database?authSource=admin
   ```

### 常见错误

1. **认证失败**
   ```
   MongoAuthenticationError: Authentication failed
   ```
   - 检查用户名、密码是否正确
   - 确认 authSource 设置正确
   - 验证用户是否有访问目标数据库的权限

2. **连接超时**
   ```
   ServerSelectionTimeoutError: localhost:27017
   ```
   - 检查 MongoDB 服务是否运行
   - 确认主机地址和端口是否正确
   - 检查防火墙设置

3. **数据库不存在**
   ```
   Database 'stock_db' does not exist
   ```
   - MongoDB 会自动创建数据库，这个错误通常是权限问题
   - 确认用户有创建数据库的权限

## 📊 配置验证

启动 Stock Agent 后，检查日志输出：

```
✅ 已加载配置文件: /path/to/project/.env
✅ 成功连接到MongoDB
   主机: localhost:27017
   数据库: stock_db
   认证: 认证模式
```

如果看到以上信息，说明配置正确。如果出现错误，请根据错误信息调整配置。

## 📞 获取帮助

如果遇到配置问题：

1. 检查 MongoDB 服务状态
2. 验证 .env 文件配置
3. 查看 Stock Agent 启动日志
4. 使用 mongo shell 测试连接

