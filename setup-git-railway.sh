#!/bin/bash
# Git + Railway 快速设置脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Git + Railway 快速设置${NC}"
echo "================================"

# 1. 初始化Git仓库（如果未初始化）
if [ ! -d ".git" ]; then
    echo -e "${BLUE}初始化Git仓库...${NC}"
    git init
    echo -e "${GREEN}✓ Git仓库初始化完成${NC}"
else
    echo -e "${GREEN}✓ Git仓库已存在${NC}"
fi

# 2. 添加gitignore
if [ ! -f ".gitignore" ]; then
    echo -e "${BLUE}创建.gitignore文件...${NC}"
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Railway
.railway/

# Temporary files
tmp/
temp/
EOF
    echo -e "${GREEN}✓ .gitignore创建完成${NC}"
else
    echo -e "${GREEN}✓ .gitignore已存在${NC}"
fi

# 3. 检查是否有远程仓库
if ! git remote | grep -q origin; then
    echo -e "${YELLOW}⚠ 未检测到GitHub远程仓库${NC}"
    echo -e "${BLUE}请手动添加GitHub仓库:${NC}"
    echo "git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    echo ""
    echo -e "${YELLOW}或者现在添加? (需要先在GitHub创建仓库)${NC}"
    read -p "输入GitHub仓库URL (留空跳过): " repo_url
    
    if [ -n "$repo_url" ]; then
        git remote add origin "$repo_url"
        echo -e "${GREEN}✓ 远程仓库添加成功${NC}"
    fi
else
    echo -e "${GREEN}✓ GitHub远程仓库已配置${NC}"
    git remote -v
fi

# 4. 提交所有文件
echo -e "${BLUE}提交所有文件...${NC}"
git add .

# 检查是否有更改需要提交
if git diff --staged --quiet; then
    echo -e "${YELLOW}没有新的更改需要提交${NC}"
else
    git commit -m "feat: 配置Railway + GitHub自动部署

- 添加GitHub Actions工作流
- 配置Railway部署文件
- 添加部署脚本和验证工具
- 更新环境变量配置"
    echo -e "${GREEN}✓ 文件提交完成${NC}"
fi

# 5. 验证部署配置
echo -e "${BLUE}验证部署配置...${NC}"
python3 verify-deployment.py

echo ""
echo -e "${GREEN}🎉 设置完成！${NC}"
echo ""
echo -e "${BLUE}下一步操作：${NC}"
echo "1. 确保在GitHub上创建了仓库并推送代码:"
echo "   git push -u origin main"
echo ""
echo "2. 在Railway控制台连接GitHub仓库:"
echo "   - 访问 https://railway.app"
echo "   - 创建新项目 > Deploy from GitHub repo"
echo "   - 选择你的仓库"
echo ""
echo "3. 配置GitHub Secrets (仓库设置 > Secrets and variables > Actions):"
echo "   - RAILWAY_TOKEN"
echo "   - RAILWAY_SERVICE_ID"
echo "   - RAILWAY_APP_URL"
echo "   - AMAP_API_KEY"
echo "   - AMAP_SECRET_KEY"
echo "   - SECRET_KEY"
echo ""
echo "4. 推送代码触发自动部署:"
echo "   ./railway-deploy.sh"
echo ""
echo -e "${YELLOW}详细说明请查看: Railway+GitHub自动部署指南.md${NC}"
