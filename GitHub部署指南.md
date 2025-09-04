# 🚀 GitHub部署指南 - 智能工时表管理系统

本指南将帮您将智能工时表管理系统部署到GitHub，并实现公网访问。

## 📋 部署准备

### 1. 高德地图API密钥
1. 访问 [高德开放平台](https://lbs.amap.com/)
2. 注册开发者账号
3. 创建应用获取API Key和Secret Key
4. 记录下这两个密钥，稍后需要配置

### 2. GitHub账号准备
- 确保您有GitHub账号
- 准备创建新的Repository

## 🏗️ 步骤一：创建GitHub Repository

### 1. 创建新仓库
```bash
# 在GitHub网站上创建新仓库，或使用GitHub CLI
gh repo create timesheet-management-system --public --description "智能工时表管理系统"
```

### 2. 初始化本地Git仓库
```bash
# 在项目目录下
cd /Users/zhaobinbin/Desktop/2025年9月/路径线上化
git init
git add .
git commit -m "🎉 Initial commit: 智能工时表管理系统"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/timesheet-management-system.git
git push -u origin main
```

## 🌐 步骤二：选择部署平台

### 选项1: Railway部署 (推荐)

Railway是现代化的云平台，非常适合Python应用。

#### 1. 准备Railway账号
- 访问 [Railway.app](https://railway.app/)
- 使用GitHub账号登录

#### 2. 从GitHub部署
1. 在Railway控制台点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 选择您的仓库 `timesheet-management-system`
4. Railway会自动检测Python应用并开始构建

#### 3. 配置环境变量
在Railway项目设置中添加以下环境变量：
```
SECRET_KEY=your-super-secret-key-here
AMAP_API_KEY=your_amap_api_key
AMAP_SECRET_KEY=your_amap_secret_key
FLASK_ENV=production
DATABASE_URL=sqlite:///enhanced_timesheet.db
```

#### 4. 自定义域名（可选）
- 在Railway项目设置中配置自定义域名
- 或使用Railway提供的免费子域名

### 选项2: Vercel部署

Vercel非常适合前端应用，也支持Python后端。

#### 1. 准备Vercel账号
- 访问 [Vercel.com](https://vercel.com/)
- 使用GitHub账号登录

#### 2. 从GitHub导入项目
1. 在Vercel控制台点击 "New Project"
2. 从GitHub导入您的仓库
3. Vercel会自动检测配置

#### 3. 配置环境变量
在Vercel项目设置中添加环境变量（同Railway）

### 选项3: Heroku部署

Heroku是老牌的云平台，稳定可靠。

#### 1. 一键部署
点击下面的按钮一键部署到Heroku：

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/YOUR_USERNAME/timesheet-management-system)

#### 2. 手动部署
```bash
# 安装Heroku CLI
# macOS
brew install heroku/brew/heroku

# 登录Heroku
heroku login

# 创建应用
heroku create your-timesheet-app

# 设置环境变量
heroku config:set SECRET_KEY=your-secret-key
heroku config:set AMAP_API_KEY=your_amap_api_key
heroku config:set AMAP_SECRET_KEY=your_amap_secret_key

# 部署
git push heroku main
```

## 🔧 步骤三：配置GitHub Actions自动部署

### 1. 设置GitHub Secrets
在GitHub仓库设置中添加以下Secrets：

#### 基础Secrets
```
SECRET_KEY=your-super-secret-key
AMAP_API_KEY=your_amap_api_key
AMAP_SECRET_KEY=your_amap_secret_key
```

#### Railway部署（如果使用）
```
RAILWAY_TOKEN=your_railway_token
```

#### Vercel部署（如果使用）
```
VERCEL_TOKEN=your_vercel_token
ORG_ID=your_vercel_org_id
PROJECT_ID=your_vercel_project_id
```

#### Docker Hub部署（可选）
```
DOCKERHUB_USERNAME=your_dockerhub_username
DOCKERHUB_TOKEN=your_dockerhub_token
```

### 2. 触发自动部署
每当您push代码到main分支时，GitHub Actions会自动：
1. 运行测试
2. 构建应用
3. 部署到配置的平台

## 📱 步骤四：访问和测试

### 1. 获取应用URL
- **Railway**: `https://your-app-name.railway.app`
- **Vercel**: `https://your-app-name.vercel.app`
- **Heroku**: `https://your-app-name.herokuapp.com`

### 2. 功能测试
1. 访问应用首页
2. 测试用户注册/登录
3. 导入门店数据
4. 测试路线计算功能
5. 导出工时表数据

## 🔐 安全配置

### 1. 环境变量安全
- ✅ 已配置从环境变量读取敏感信息
- ✅ 已添加.gitignore防止密钥泄露
- ✅ 已创建配置模板文件

### 2. 数据库安全
- 生产环境建议使用PostgreSQL或MySQL
- 定期备份数据
- 配置数据库访问权限

### 3. HTTPS配置
- 所有推荐的平台都自动提供HTTPS
- 确保SESSION_COOKIE_SECURE=True

## 🔧 高级配置

### 1. 自定义域名
大多数平台都支持自定义域名：
1. 在平台控制台配置域名
2. 在DNS提供商添加CNAME记录
3. 配置SSL证书（通常自动）

### 2. 数据库升级
对于生产环境，建议升级到专业数据库：

#### PostgreSQL (推荐)
```python
# 在环境变量中设置
DATABASE_URL=postgresql://user:password@host:port/database
```

#### MySQL
```python
# 在环境变量中设置
DATABASE_URL=mysql://user:password@host:port/database
```

### 3. 性能优化
1. **CDN配置**: 使用Cloudflare等CDN服务
2. **缓存配置**: 启用Redis缓存
3. **监控配置**: 配置应用性能监控

## 🆘 常见问题

### Q1: 部署失败怎么办？
1. 检查环境变量是否正确设置
2. 查看构建日志找出错误原因
3. 确认所有依赖都在requirements.txt中

### Q2: 高德API不工作？
1. 确认API密钥正确
2. 检查API调用量是否超限
3. 验证IP白名单设置

### Q3: 数据丢失怎么办？
1. 定期备份数据库文件
2. 使用云数据库服务
3. 配置自动备份策略

### Q4: 性能问题？
1. 检查数据库查询优化
2. 启用缓存机制
3. 考虑升级服务器配置

## 🎉 部署完成

恭喜！您的智能工时表管理系统现在已经部署到公网了！

### 接下来可以：
1. 🎨 自定义界面样式
2. 📈 配置数据分析功能
3. 📱 开发移动端应用
4. 🔧 添加更多业务功能
5. 👥 邀请团队成员使用

### 获取支持
- 📧 技术支持: your-email@example.com
- 💬 在线文档: https://your-docs-site.com
- 🐛 问题反馈: https://github.com/YOUR_USERNAME/timesheet-management-system/issues

---

🌟 **记得给项目点个Star支持一下！**
