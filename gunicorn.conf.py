# Gunicorn配置文件
import os
import multiprocessing

# 服务器配置
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 120
keepalive = 5

# 日志配置
accesslog = os.environ.get('ACCESS_LOG', '-')
errorlog = os.environ.get('ERROR_LOG', '-')
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程配置
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL配置（如果需要）
keyfile = os.environ.get('SSL_KEYFILE')
certfile = os.environ.get('SSL_CERTFILE')

# 性能优化
preload_app = True
enable_stdio_inheritance = True
