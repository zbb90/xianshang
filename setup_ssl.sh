#!/bin/bash
# SSL证书配置脚本 - 为jihe.fun域名配置Let's Encrypt免费SSL证书

set -e

echo "🔒 开始为 jihe.fun 配置SSL证书"
echo "=" * 50

# 颜色输出函数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
if [ "$EUID" -ne 0 ]; then
    error "此脚本需要root权限，请使用sudo运行"
    exit 1
fi

# 检查域名解析
info "检查域名解析..."
DOMAIN="jihe.fun"
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short $DOMAIN)

if [ "$DOMAIN_IP" = "$SERVER_IP" ]; then
    info "✅ 域名解析正确: $DOMAIN -> $SERVER_IP"
else
    warn "⚠️  域名解析可能有问题:"
    echo "   域名IP: $DOMAIN_IP"
    echo "   服务器IP: $SERVER_IP"
    echo ""
    read -p "是否继续安装SSL证书? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. 安装certbot
info "安装certbot..."
apt update
apt install -y snapd
snap install core; snap refresh core
snap install --classic certbot
ln -sf /snap/bin/certbot /usr/bin/certbot

# 2. 临时停止nginx
info "临时停止nginx服务..."
systemctl stop nginx

# 3. 获取SSL证书
info "申请SSL证书..."
certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@jihe.fun \
    --domains jihe.fun

# 4. 检查证书是否申请成功
if [ -f "/etc/letsencrypt/live/jihe.fun/fullchain.pem" ]; then
    info "✅ SSL证书申请成功"
else
    error "❌ SSL证书申请失败"
    systemctl start nginx
    exit 1
fi

# 5. 启动nginx
info "启动nginx服务..."
systemctl start nginx

# 6. 测试nginx配置
info "测试nginx配置..."
nginx -t

if [ $? -eq 0 ]; then
    info "✅ nginx配置正确"
    systemctl reload nginx
else
    error "❌ nginx配置有误"
    exit 1
fi

# 7. 设置自动续期
info "设置SSL证书自动续期..."
cat > /etc/cron.d/letsencrypt-renewal << EOF
# Let's Encrypt证书自动续期
0 2 * * * root /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
EOF

# 8. 测试HTTPS访问
info "测试HTTPS访问..."
sleep 3

if curl -s -o /dev/null -w "%{http_code}" https://jihe.fun/ | grep -q "200"; then
    info "✅ HTTPS访问正常"
else
    warn "⚠️  HTTPS访问可能有问题，请检查防火墙设置"
fi

# 9. 显示证书信息
info "SSL证书信息："
certbot certificates

echo ""
echo "🎉 SSL配置完成！"
echo "=================================="
echo "网站地址: https://jihe.fun"
echo "HTTP自动跳转到HTTPS: http://jihe.fun"
echo ""
echo "证书信息:"
echo "  颁发者: Let's Encrypt"
echo "  有效期: 90天（自动续期）"
echo "  证书路径: /etc/letsencrypt/live/jihe.fun/"
echo ""
echo "续期命令: certbot renew"
echo "手动测试续期: certbot renew --dry-run"
echo "=================================="