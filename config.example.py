# 高德地图API配置模板
import os

# 从环境变量获取API密钥，如果没有则使用默认值（仅用于开发）
AMAP_API_KEY = os.environ.get('AMAP_API_KEY', 'your_amap_api_key_here')
AMAP_SECRET_KEY = os.environ.get('AMAP_SECRET_KEY', 'your_amap_secret_key_here')

# Flask应用配置
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-this-in-production')

# 数据库配置
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///enhanced_timesheet.db')

# 服务器配置
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 8080))

# 会话配置
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', 86400))  # 24小时
