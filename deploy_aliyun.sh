#!/bin/bash
# 阿里云完整部署脚本
# 使用方法: chmod +x deploy_aliyun.sh && ./deploy_aliyun.sh

set -e  # 遇到错误立即退出

echo "🚀 开始部署古茗工时管理系统到阿里云"
echo "=" * 50

# 颜色输出函数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    error "请不要使用root用户运行此脚本"
    exit 1
fi

# 1. 安装系统依赖
info "安装系统依赖..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx postgresql-client git curl

# 2. 创建Python虚拟环境
info "创建Python虚拟环境..."
cd /home/guming/timesheet
python3 -m venv venv
source venv/bin/activate

# 3. 安装Python依赖
info "安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. 配置环境变量
info "配置环境变量..."
if [ ! -f .env ]; then
    if [ -f .env.aliyun ]; then
        cp .env.aliyun .env
        warn "已从.env.aliyun复制环境配置，请检查并修改数据库连接信息"
    else
        error "未找到环境配置文件，请先创建.env文件"
        exit 1
    fi
fi

# 5. 初始化数据库
info "初始化数据库..."
python aliyun_database_setup.py

# 6. 导入数据（如果存在导入文件）
if ls railway_data_import_*.sql 1> /dev/null 2>&1; then
    info "导入Railway数据..."
    source .env
    psql "$DATABASE_URL" -f railway_data_import_*.sql
    info "数据导入完成"
else
    warn "未找到数据导入文件，跳过数据导入"
fi

# 7. 验证数据迁移
if ls railway_data_export_*.json 1> /dev/null 2>&1; then
    info "验证数据迁移..."
    python verify_migration.py
else
    warn "未找到导出数据文件，跳过迁移验证"
fi

# 8. 配置Nginx
info "配置Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/guming-timesheet
sudo ln -sf /etc/nginx/sites-available/guming-timesheet /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 9. 配置Systemd服务
info "配置Systemd服务..."
sudo cp guming-timesheet.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable guming-timesheet
sudo systemctl start guming-timesheet

# 10. 检查服务状态
info "检查服务状态..."
sleep 3

if sudo systemctl is-active --quiet guming-timesheet; then
    info "✅ 应用服务启动成功"
else
    error "❌ 应用服务启动失败"
    sudo systemctl status guming-timesheet --no-pager
    exit 1
fi

if sudo systemctl is-active --quiet nginx; then
    info "✅ Nginx服务运行正常"
else
    error "❌ Nginx服务异常"
    sudo systemctl status nginx --no-pager
    exit 1
fi

# 11. 测试应用访问
info "测试应用访问..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    info "✅ 应用HTTP访问正常"
else
    warn "⚠️  HTTP访问可能有问题，请检查"
fi

# 12. 显示部署信息
echo ""
info "🎉 部署完成！"
echo "=================================="
echo "应用URL: http://$(curl -s ifconfig.me)/"
echo "本地测试: http://localhost/"
echo ""
echo "管理命令:"
echo "  查看服务状态: sudo systemctl status guming-timesheet"
echo "  重启服务: sudo systemctl restart guming-timesheet"
echo "  查看日志: sudo journalctl -u guming-timesheet -f"
echo "  重载Nginx: sudo systemctl reload nginx"
echo ""
echo "默认登录账号:"
echo "  管理员: admin / admin123"
echo "  (请登录后立即修改密码)"
echo ""
warn "请确保:"
warn "1. 阿里云安全组已开放80和443端口"
warn "2. 数据库连接信息正确"
warn "3. 定期备份数据库"
echo "=================================="