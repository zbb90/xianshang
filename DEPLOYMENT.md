# 🚀 生产环境部署指南

## GitHub + Railway 部署步骤

### 📋 前置准备

1. **GitHub仓库设置**
   ```bash
   git add .
   git commit -m "Ready for production deployment"
   git push origin main
   ```

2. **API密钥准备**
   - 高德地图API密钥
   - 腾讯地图API密钥（可选）
   - 生成强密钥：`python -c "import secrets; print(secrets.token_urlsafe(32))"`

### 🎯 Railway部署方案

#### 方案A：SQLite数据库（推荐小型应用）

**适用场景：**
- 用户数 < 50人
- 并发数 < 10人
- 快速部署，零配置

**部署步骤：**

1. **连接Railway**
   ```bash
   # 安装Railway CLI
   npm install -g @railway/cli
   
   # 登录
   railway login
   
   # 连接项目
   railway link
   ```

2. **设置环境变量**
   ```bash
   railway variables set FLASK_ENV=production
   railway variables set FLASK_DEBUG=False
   railway variables set SECRET_KEY=your-secret-key
   railway variables set AMAP_API_KEY=your-amap-key
   railway variables set AMAP_SECRET_KEY=your-amap-secret
   railway variables set TENCENT_API_KEY=your-tencent-key
   ```

3. **部署应用**
   ```bash
   railway up
   ```

#### 方案B：PostgreSQL数据库（推荐大型应用）

**适用场景：**
- 用户数 > 50人
- 高并发访问
- 需要数据备份和高可用

**部署步骤：**

1. **添加PostgreSQL服务**
   ```bash
   # 在Railway控制台添加PostgreSQL插件
   # Railway会自动设置DATABASE_URL环境变量
   ```

2. **运行数据迁移**
   ```bash
   # 本地迁移（如果有现有数据）
   python database_upgrade.py
   ```

3. **更新requirements.txt**
   ```bash
   echo "psycopg2-binary==2.9.7" >> requirements.txt
   ```

4. **部署**
   ```bash
   railway up
   ```

### 🔧 必要的环境变量

在Railway控制台设置以下环境变量：

```bash
# 必需的
FLASK_ENV=production
SECRET_KEY=your-super-secret-key
AMAP_API_KEY=your-amap-api-key

# 可选的
AMAP_SECRET_KEY=your-amap-secret-key
TENCENT_API_KEY=your-tencent-api-key
DATABASE_URL=auto-generated-by-railway
```

### 📊 数据库存储对比

| 方案 | 适用用户数 | 并发支持 | 维护成本 | 月费用 |
|------|-----------|----------|----------|--------|
| SQLite | < 50 | < 10 | 极低 | $0 |
| PostgreSQL | > 50 | > 50 | 低 | $5+ |

### 🛡️ 安全配置

1. **环境变量安全**
   - 在Railway控制台设置，不要硬编码
   - 使用强密钥：`python -c "import secrets; print(secrets.token_urlsafe(32))"`

2. **HTTPS配置**
   - Railway自动提供HTTPS
   - 确保 `SESSION_COOKIE_SECURE=True`

3. **数据备份**
   ```bash
   # SQLite备份（定期下载）
   railway run --detach python -c "
   import shutil
   from datetime import datetime
   backup_name = f'backup_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.db'
   shutil.copy2('timesheet.db', backup_name)
   print(f'备份完成: {backup_name}')
   "
   ```

### 🚀 部署检查清单

- [ ] ✅ GitHub代码已推送
- [ ] ✅ Railway项目已创建并连接
- [ ] ✅ 环境变量已设置
- [ ] ✅ API密钥已配置
- [ ] ✅ 数据库选择已确定
- [ ] ✅ 域名已配置（可选）
- [ ] ✅ 健康检查通过

### 📈 监控和维护

1. **应用监控**
   - Railway提供自动监控
   - 查看日志：`railway logs`

2. **性能优化**
   - 监控响应时间
   - 数据库查询优化

3. **定期备份**
   - SQLite：定期下载数据库文件
   - PostgreSQL：Railway自动备份

### 🆘 故障排除

**常见问题：**

1. **应用启动失败**
   ```bash
   railway logs --tail
   ```

2. **数据库连接失败**
   ```bash
   railway variables
   # 检查DATABASE_URL是否正确
   ```

3. **API密钥错误**
   ```bash
   railway variables set AMAP_API_KEY=new-key
   ```

### 🎯 推荐配置

**对于您的工时管理系统，建议：**

✅ **使用SQLite方案**，因为：
- 用户数量预计较少（< 50人）
- 系统复杂度适中
- 维护成本极低
- 部署简单快速

🔄 **未来升级路径**：
- 当用户数超过50人时，再迁移到PostgreSQL
- 使用提供的 `database_upgrade.py` 进行无缝迁移

---

**🎉 部署完成后，您将拥有：**
- 全自动HTTPS的Web应用
- 自动扩容和高可用性
- 零停机部署
- 实时监控和日志

