#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI入口文件 - 生产环境部署
"""

import os
import sys
from pathlib import Path

# 添加项目路径到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入Flask应用
from enhanced_final_app import app, init_db

# 初始化数据库
init_db()

# 配置生产环境设置
if __name__ != '__main__':
    # 生产环境配置
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', app.secret_key),
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true',
        SESSION_COOKIE_HTTPONLY=os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true',
        SESSION_COOKIE_SAMESITE=os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax'),
        PERMANENT_SESSION_LIFETIME=int(os.environ.get('PERMANENT_SESSION_LIFETIME', '86400'))
    )

if __name__ == '__main__':
    # 开发环境运行
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=True)
