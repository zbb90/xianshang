#!/bin/bash
# GitHub部署自动化脚本

set -e

echo "🚀 开始GitHub部署流程..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Git是否安装
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git未安装，请先安装Git${NC}"
    exit 1
fi

# 检查是否在Git仓库中
if [ ! -d ".git" ]; then
    echo -e "${BLUE}📦 初始化Git仓库...${NC}"
    git init
    echo -e "${GREEN}✅ Git仓库初始化完成${NC}"
fi

# 获取用户GitHub信息
echo -e "${BLUE}🔧 配置GitHub信息...${NC}"
read -p "请输入您的GitHub用户名: " GITHUB_USERNAME
read -p "请输入仓库名称 (建议: timesheet-management-system): " REPO_NAME

# 设置默认仓库名
if [ -z "$REPO_NAME" ]; then
    REPO_NAME="timesheet-management-system"
fi

# 检查是否已有远程仓库
if git remote | grep -q "origin"; then
    echo -e "${YELLOW}⚠️  已存在origin远程仓库，是否要重新设置？ (y/n)${NC}"
    read -p "" reset_remote
    if [ "$reset_remote" = "y" ] || [ "$reset_remote" = "Y" ]; then
        git remote remove origin
        git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
    fi
else
    git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
fi

# 创建.env模板（如果不存在）
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📝 创建环境变量模板...${NC}"
    cat > .env << EOF
# 生产环境配置
SECRET_KEY=your-super-secret-key-change-in-production
FLASK_ENV=production
FLASK_DEBUG=False

# 高德地图API配置
AMAP_API_KEY=your_amap_api_key_here
AMAP_SECRET_KEY=your_amap_secret_key_here

# 数据库配置
DATABASE_URL=sqlite:///enhanced_timesheet.db

# 服务器配置
HOST=0.0.0.0
PORT=8080

# 安全配置
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=86400
EOF
    echo -e "${GREEN}✅ .env模板创建完成${NC}"
    echo -e "${YELLOW}⚠️  请编辑.env文件，设置正确的API密钥！${NC}"
fi

# 更新README.md中的用户名
if [ -f "README.md" ]; then
    echo -e "${BLUE}📝 更新README.md...${NC}"
    sed -i.bak "s/your-username/${GITHUB_USERNAME}/g" README.md
    sed -i.bak "s/timesheet-management-system/${REPO_NAME}/g" README.md
    rm README.md.bak 2>/dev/null || true
    echo -e "${GREEN}✅ README.md更新完成${NC}"
fi

# 更新部署指南中的用户名
if [ -f "GitHub部署指南.md" ]; then
    echo -e "${BLUE}📝 更新部署指南...${NC}"
    sed -i.bak "s/YOUR_USERNAME/${GITHUB_USERNAME}/g" "GitHub部署指南.md"
    sed -i.bak "s/timesheet-management-system/${REPO_NAME}/g" "GitHub部署指南.md"
    rm "GitHub部署指南.md.bak" 2>/dev/null || true
    echo -e "${GREEN}✅ 部署指南更新完成${NC}"
fi

# 检查并添加所有文件
echo -e "${BLUE}📦 准备提交文件...${NC}"
git add .

# 检查是否有文件要提交
if git diff --staged --quiet; then
    echo -e "${YELLOW}⚠️  没有新的文件需要提交${NC}"
else
    # 提交文件
    echo -e "${BLUE}💾 提交文件到Git...${NC}"
    git commit -m "🎉 Initial commit: 智能工时表管理系统

✨ 功能特性:
- 完整的工时管理系统
- 门店管理和路线规划
- 高德地图API集成
- 用户认证和数据导出
- 支持多种部署方式

🚀 部署支持:
- Railway
- Vercel  
- Heroku
- Docker
- GitHub Actions CI/CD

📝 文档完整:
- 部署指南
- 使用说明
- API文档"

    echo -e "${GREEN}✅ 文件提交完成${NC}"
fi

# 设置主分支
echo -e "${BLUE}🌿 设置主分支...${NC}"
git branch -M main

# 推送到GitHub
echo -e "${BLUE}🚀 推送到GitHub...${NC}"
echo -e "${YELLOW}注意: 如果这是第一次推送，可能需要您的GitHub认证${NC}"

if git push -u origin main; then
    echo -e "${GREEN}✅ 成功推送到GitHub!${NC}"
else
    echo -e "${RED}❌ 推送失败，可能需要先在GitHub创建仓库${NC}"
    echo -e "${BLUE}💡 请访问: https://github.com/new${NC}"
    echo -e "${BLUE}   仓库名称: ${REPO_NAME}${NC}"
    echo -e "${BLUE}   然后重新运行此脚本${NC}"
    exit 1
fi

# 显示部署信息
echo ""
echo -e "${GREEN}🎉 GitHub部署配置完成！${NC}"
echo ""
echo -e "${BLUE}📋 接下来的步骤:${NC}"
echo "1. 🌐 仓库地址: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
echo "2. 📖 查看部署指南: GitHub部署指南.md"
echo "3. 🔧 配置环境变量 (.env文件)"
echo "4. 🚀 选择部署平台:"
echo "   - Railway: https://railway.app/"
echo "   - Vercel: https://vercel.com/"
echo "   - Heroku: https://heroku.com/"
echo ""
echo -e "${YELLOW}⚠️  重要提醒:${NC}"
echo "- 🔑 记得设置高德地图API密钥"
echo "- 🔐 在部署平台配置环境变量"
echo "- 📱 测试所有功能是否正常"
echo ""
echo -e "${GREEN}🌟 部署成功后，别忘了给项目点个Star！${NC}"
