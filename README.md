# 🚀 智能工时表管理系统

一个功能完整的工时管理系统，支持门店管理、路线规划、数据导出等功能，集成高德地图API进行智能路线计算。

## ✨ 功能特性

- ✅ **工时管理** - 完整的工时录入、编辑、查询功能
- ✅ **门店管理** - 门店信息导入导出，支持批量操作
- ✅ **路线规划** - 集成高德地图API，支持多种路线策略
- ✅ **智能输入** - 门店编码自动补全，实时显示门店信息
- ✅ **数据导出** - Excel格式导出，支持自定义时间范围
- ✅ **用户认证** - 完整的用户注册登录系统
- ✅ **性能优化** - 分页加载，搜索功能，防止页面卡顿
- ✅ **移动端适配** - 响应式设计，支持手机和平板访问

## 🛠️ 技术栈

- **后端**: Python Flask, SQLite
- **前端**: HTML5, CSS3, JavaScript (ES6+)
- **API集成**: 高德地图路线规划API
- **部署**: Docker, Gunicorn, Nginx
- **数据处理**: Pandas, OpenPyXL

## 🚀 快速开始

### 本地部署

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/timesheet-management-system.git
   cd timesheet-management-system
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   cp env.example .env
   # 编辑 .env 文件，设置高德API密钥等配置
   ```

4. **启动应用**
   ```bash
   # 开发环境
   python enhanced_final_app.py
   
   # 生产环境
   gunicorn -c gunicorn.conf.py wsgi:app
   ```

5. **访问应用**
   ```
   http://localhost:8080
   ```

### Docker部署

1. **构建镜像**
   ```bash
   docker build -t timesheet-system .
   ```

2. **运行容器**
   ```bash
   docker-compose up -d
   ```

## 🌐 云平台部署

### Vercel部署
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/timesheet-management-system)

### Railway部署
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/your-template)

### Heroku部署
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/your-username/timesheet-management-system)

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|---------|
| `SECRET_KEY` | Flask应用密钥 | 需要设置 |
| `AMAP_API_KEY` | 高德地图API密钥 | 需要设置 |
| `AMAP_SECRET_KEY` | 高德地图API密钥签名 | 需要设置 |
| `DATABASE_URL` | 数据库连接URL | `sqlite:///enhanced_timesheet.db` |
| `PORT` | 应用端口 | `8080` |
| `FLASK_ENV` | 运行环境 | `production` |

### 高德地图API配置

1. 访问 [高德开放平台](https://lbs.amap.com/)
2. 注册开发者账号
3. 创建应用获取API Key和Secret Key
4. 在`.env`文件中配置相关密钥

## 📁 项目结构

```
timesheet-management-system/
├── enhanced_final_app.py      # 主应用文件
├── wsgi.py                    # WSGI入口文件
├── config.py                  # 配置文件模板
├── requirements.txt           # Python依赖
├── gunicorn.conf.py          # Gunicorn配置
├── Dockerfile                # Docker配置
├── docker-compose.yml        # Docker Compose配置
├── nginx.conf                # Nginx配置
├── deploy.sh                 # 部署脚本
├── .github/
│   └── workflows/
│       └── deploy.yml        # GitHub Actions配置
└── docs/
    ├── 部署指南.md            # 详细部署指南
    ├── 使用说明.md            # 用户使用说明
    └── API文档.md             # API接口文档
```

## 🔧 开发指南

### API接口

- `GET /api/health` - 健康检查
- `GET /api/users` - 获取用户列表
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/stores` - 获取门店列表
- `POST /api/stores/import` - 导入门店数据
- `POST /api/calculate-route` - 计算路线
- `GET /api/timesheet` - 获取工时记录
- `POST /api/timesheet` - 提交工时记录

### 数据库结构

系统使用SQLite数据库，包含以下主要表：
- `users` - 用户信息表
- `locations` - 地点信息表
- `stores` - 门店信息表
- `timesheets` - 工时记录表

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 问题反馈

如果您在使用过程中遇到问题，请通过以下方式反馈：

- [GitHub Issues](https://github.com/your-username/timesheet-management-system/issues)
- Email: your-email@example.com

## 🙏 致谢

- [高德地图开放平台](https://lbs.amap.com/) - 提供地图和路线规划服务
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Bootstrap](https://getbootstrap.com/) - 前端样式框架

---

⭐ 如果这个项目对您有帮助，请给个Star支持一下！