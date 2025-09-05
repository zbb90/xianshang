#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI入口文件 - 生产环境部署 v4.0
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入新的Flask应用
from app import app, init_db

# 初始化数据库
init_db()

# 生产环境配置
if __name__ != '__main__':
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', app.secret_key),
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)