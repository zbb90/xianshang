# Railway + GitHub 自动部署指南

## 📋 目录
- [概述](#概述)
- [准备工作](#准备工作)
- [配置步骤](#配置步骤)
- [环境变量设置](#环境变量设置)
- [部署流程](#部署流程)
- [监控和调试](#监控和调试)
- [常见问题](#常见问题)

## 🎯 概述

本项目采用 **Railway + GitHub Actions** 的自动部署方案，实现：

- ✅ **代码推送自动部署**：推送到 main/master 分支自动触发部署
- ✅ **健康检查**：自动验证应用部署状态
- ✅ **回滚支持**：部署失败自动回滚
- ✅ **环境隔离**：生产环境配置独立管理
- ✅ **日志监控**：完整的部署和运行日志

## 🛠 准备工作

### 1. 账号准备
- [x] GitHub 账号（用于代码托管）
- [x] Railway 账号（用于应用部署）

### 2. 本地环境
```bash
# 检查 Git
git --version

# 可选：安装 Railway CLI
npm install -g @railway/cli
railway login
```

### 3. 项目文件检查
确保以下文件存在且配置正确：
- [x] `requirements.txt` - Python依赖
- [x] `wsgi.py` - WSGI入口文件
- [x] `gunicorn.conf.py` - Gunicorn配置
- [x] `railway.json` - Railway配置
- [x] `.github/workflows/railway-deploy.yml` - GitHub Actions工作流

## ⚙️ 配置步骤

### 第一步：创建 GitHub 仓库

1. **创建新仓库**
   ```bash
   # 在 GitHub 上创建新仓库，然后本地初始化
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

### 第二步：连接 Railway

1. **访问 Railway 控制台**
   - 登录 [Railway](https://railway.app)
   - 点击 "New Project"

2. **连接 GitHub 仓库**
   - 选择 "Deploy from GitHub repo"
   - 授权 Railway 访问你的 GitHub 账号
   - 选择刚创建的仓库

3. **配置部署设置**
   - Railway 会自动检测 Python 项目
   - 确认使用 `railway.json` 配置文件

### 第三步：配置 GitHub Secrets

在 GitHub 仓库的 Settings > Secrets and variables > Actions 中添加：

```
RAILWAY_TOKEN=your_railway_token_here
RAILWAY_SERVICE_ID=your_service_id_here
RAILWAY_APP_URL=https://your-app.railway.app
AMAP_API_KEY=your_amap_api_key
AMAP_SECRET_KEY=your_amap_secret_key
SECRET_KEY=your_flask_secret_key
```

#### 获取 Railway Token 和 Service ID：

1. **获取 Railway Token**
   ```bash
   # 使用 Railway CLI
   railway login
   railway whoami --token
   
   # 或在 Railway 控制台
   # Account Settings > Tokens > Create Token
   ```

2. **获取 Service ID**
   ```bash
   # 在项目目录中
   railway status
   
   # 或从 Railway 控制台 URL 获取
   # https://railway.app/project/[PROJECT_ID]/service/[SERVICE_ID]
   ```

## 🔧 环境变量设置

### Railway 环境变量

在 Railway 控制台的 Variables 标签页添加：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `FLASK_ENV` | `production` | Flask 环境 |
| `FLASK_DEBUG` | `False` | 关闭调试模式 |
| `SECRET_KEY` | `your_secret_key` | Flask 密钥 |
| `AMAP_API_KEY` | `your_api_key` | 高德地图 API Key |
| `AMAP_SECRET_KEY` | `your_secret_key` | 高德地图 Secret Key |
| `DATABASE_URL` | `sqlite:///enhanced_timesheet.db` | 数据库 URL |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 安全配置变量
```bash
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=86400
```

## 🚀 部署流程

### 自动部署（推荐）

1. **推送代码触发部署**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   git push origin main
   ```

2. **监控部署进度**
   - GitHub Actions: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`
   - Railway 控制台: `https://railway.app/dashboard`

### 手动部署

使用提供的部署脚本：

```bash
# 基本部署
./railway-deploy.sh

# 强制部署（跳过确认）
./railway-deploy.sh --force

# 查看帮助
./railway-deploy.sh --help
```

## 📊 监控和调试

### 部署状态检查

1. **GitHub Actions 状态**
   - 绿色 ✅：部署成功
   - 红色 ❌：部署失败，查看详细日志

2. **Railway 应用状态**
   - Active：应用正常运行
   - Crashed：应用崩溃，查看日志

3. **健康检查**
   ```bash
   # 手动健康检查
   curl -f https://your-app.railway.app/api/health
   ```

### 日志查看

1. **Railway 日志**
   ```bash
   # 使用 CLI
   railway logs
   
   # 或在控制台查看
   # Railway Project > Deployments > View Logs
   ```

2. **GitHub Actions 日志**
   - 访问 Actions 页面
   - 点击具体的工作流运行
   - 查看每个步骤的详细输出

## 🐛 常见问题

### 1. 部署失败

**问题**：GitHub Actions 构建失败
```
Error: Process completed with exit code 1
```

**解决方案**：
1. 检查 `requirements.txt` 依赖是否正确
2. 检查代码语法错误
3. 验证环境变量配置

### 2. 应用启动失败

**问题**：Railway 部署成功但应用无法访问

**解决方案**：
1. 检查 Railway 日志：
   ```bash
   railway logs --tail
   ```
2. 验证 `wsgi.py` 配置
3. 检查端口配置（Railway 自动分配 PORT 环境变量）

### 3. 数据库问题

**问题**：SQLite 数据库文件丢失

**解决方案**：
1. Railway 使用临时存储，重启会丢失数据
2. 考虑使用 Railway 提供的 PostgreSQL：
   ```bash
   railway add postgresql
   ```
3. 更新 `DATABASE_URL` 环境变量

### 4. API 密钥错误

**问题**：高德地图 API 调用失败

**解决方案**：
1. 检查 API Key 是否正确设置
2. 验证 API Key 权限和配额
3. 检查域名白名单设置

### 5. 健康检查超时

**问题**：应用启动时间过长导致健康检查失败

**解决方案**：
1. 增加健康检查超时时间（`railway.json`）
2. 优化应用启动时间
3. 检查数据库初始化逻辑

## 🔄 更新和维护

### 代码更新
```bash
# 1. 开发新功能
git checkout -b feature/new-feature
# ... 编写代码 ...
git add .
git commit -m "feat: 新功能描述"

# 2. 合并到主分支
git checkout main
git merge feature/new-feature

# 3. 推送触发部署
git push origin main
```

### 依赖更新
```bash
# 更新 requirements.txt
pip list --outdated
pip install --upgrade package_name
pip freeze > requirements.txt

# 提交更新
git add requirements.txt
git commit -m "deps: 更新依赖包"
git push origin main
```

### 配置更新
- 修改 `railway.json` 后推送代码
- Railway 环境变量在控制台直接修改
- GitHub Secrets 在仓库设置中修改

## 📞 支持

如有问题，请：
1. 查看 Railway 和 GitHub Actions 日志
2. 检查本文档的常见问题部分
3. 参考 Railway 和 GitHub 官方文档

---

**🎉 恭喜！你已经成功配置了 Railway + GitHub 自动部署！**

每次推送代码到主分支，都会自动触发部署流程，大大提高了开发效率。
