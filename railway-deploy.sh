#!/bin/bash
# Railway自动部署脚本

set -e

echo "🚀 开始Railway部署流程..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查必要的工具
check_requirements() {
    echo -e "${BLUE}检查部署要求...${NC}"
    
    # 检查git
    if ! command -v git &> /dev/null; then
        echo -e "${RED}错误: 未找到git命令${NC}"
        exit 1
    fi
    
    # 检查railway CLI (如果已安装)
    if command -v railway &> /dev/null; then
        echo -e "${GREEN}✓ Railway CLI已安装${NC}"
    else
        echo -e "${YELLOW}⚠ Railway CLI未安装 (可选)${NC}"
    fi
    
    echo -e "${GREEN}✓ 基本要求检查完成${NC}"
}

# 检查Git状态
check_git_status() {
    echo -e "${BLUE}检查Git状态...${NC}"
    
    # 检查是否在git仓库中
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}错误: 当前目录不是Git仓库${NC}"
        echo -e "${YELLOW}请先运行: git init${NC}"
        exit 1
    fi
    
    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}⚠ 检测到未提交的更改${NC}"
        echo -e "${YELLOW}建议先提交所有更改后再部署${NC}"
        read -p "是否继续部署? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}部署已取消${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Git状态检查完成${NC}"
}

# 推送到GitHub
push_to_github() {
    echo -e "${BLUE}推送代码到GitHub...${NC}"
    
    # 获取当前分支
    current_branch=$(git branch --show-current)
    
    # 添加所有文件
    git add .
    
    # 提交更改（如果有的话）
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}提交最新更改...${NC}"
        git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 推送到远程仓库
    echo -e "${YELLOW}推送到远程仓库...${NC}"
    git push origin $current_branch
    
    echo -e "${GREEN}✓ 代码已推送到GitHub${NC}"
}

# 验证部署
verify_deployment() {
    if [ -n "$RAILWAY_APP_URL" ]; then
        echo -e "${BLUE}验证部署...${NC}"
        echo -e "${YELLOW}等待30秒让应用启动...${NC}"
        sleep 30
        
        # 健康检查
        if curl -f "$RAILWAY_APP_URL/api/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 应用健康检查通过${NC}"
            echo -e "${GREEN}🎉 部署成功! 应用访问地址: $RAILWAY_APP_URL${NC}"
        else
            echo -e "${RED}⚠ 健康检查失败，请检查Railway控制台${NC}"
        fi
    else
        echo -e "${YELLOW}未设置RAILWAY_APP_URL环境变量，跳过自动验证${NC}"
        echo -e "${YELLOW}请手动检查Railway控制台确认部署状态${NC}"
    fi
}

# 显示帮助信息
show_help() {
    echo "Railway部署脚本使用说明:"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -f, --force    强制部署（跳过确认）"
    echo ""
    echo "环境变量:"
    echo "  RAILWAY_APP_URL    Railway应用的URL（用于部署验证）"
    echo ""
    echo "注意:"
    echo "  1. 确保已设置GitHub仓库的Railway集成"
    echo "  2. 确保在GitHub Secrets中配置了必要的环境变量"
    echo "  3. 部署将触发GitHub Actions工作流"
}

# 主流程
main() {
    # 解析命令行参数
    FORCE=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            *)
                echo -e "${RED}未知选项: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo -e "${GREEN}=== Railway自动部署 ===${NC}"
    echo -e "${BLUE}项目: 路径线上化系统${NC}"
    echo -e "${BLUE}时间: $(date)${NC}"
    echo ""
    
    # 执行检查
    check_requirements
    check_git_status
    
    # 确认部署
    if [ "$FORCE" = false ]; then
        echo -e "${YELLOW}即将开始部署到Railway...${NC}"
        read -p "确认继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}部署已取消${NC}"
            exit 1
        fi
    fi
    
    # 执行部署
    push_to_github
    
    echo -e "${GREEN}✓ GitHub推送完成${NC}"
    echo -e "${BLUE}GitHub Actions将自动触发Railway部署...${NC}"
    echo -e "${YELLOW}请查看GitHub Actions页面监控部署进度${NC}"
    
    # 验证部署
    verify_deployment
    
    echo ""
    echo -e "${GREEN}🎉 部署流程完成!${NC}"
    echo -e "${BLUE}监控地址:${NC}"
    echo -e "  - GitHub Actions: https://github.com/YOUR_USERNAME/YOUR_REPO/actions"
    echo -e "  - Railway控制台: https://railway.app/dashboard"
}

# 运行主流程
main "$@"
