#!/bin/bash
# 部署脚本

set -e

echo "🚀 开始部署智能工时表管理系统..."

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 未安装，请先安装pip3"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip3 install -r requirements.txt

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env文件不存在，从env.example复制..."
    cp env.example .env
    echo "📝 请编辑.env文件，设置正确的配置值"
fi

# 初始化数据库
echo "🗄️  初始化数据库..."
python3 -c "from enhanced_final_app import init_db; init_db()"

# 设置权限
chmod +x wsgi.py
chmod +x deploy.sh

echo "✅ 部署完成！"
echo ""
echo "🌐 启动方式："
echo "开发环境: python3 enhanced_final_app.py"
echo "生产环境: gunicorn -c gunicorn.conf.py wsgi:app"
echo ""
echo "📋 端口配置："
echo "默认端口: 8080"
echo "可通过环境变量PORT修改"
echo ""
echo "🔐 安全提醒："
echo "1. 修改.env中的SECRET_KEY"
echo "2. 设置正确的AMAP_API_KEY和AMAP_SECRET_KEY"
echo "3. 生产环境建议使用HTTPS"
