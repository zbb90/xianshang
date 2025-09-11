#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import hashlib
import hmac
import json
import requests
import math
import logging
import time
from datetime import datetime, timedelta
from contextlib import contextmanager
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string, send_file
import bcrypt
# 从环境变量或默认值获取配置
AMAP_API_KEY = os.environ.get('AMAP_API_KEY', 'f2ed89b710d6a630881906c440f71691')
AMAP_SECRET_KEY = os.environ.get('AMAP_SECRET_KEY', 'your_amap_secret_key_here')
TENCENT_API_KEY = os.environ.get('TENCENT_API_KEY', 'FLCBZ-CDL6W-52JRT-YBNSH-D4P2H-U7BFJ')
SECRET_KEY = os.environ.get('SECRET_KEY', 'timesheet-secret-key-2024')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# 数据库连接上下文管理器
@contextmanager
def get_db_connection(timeout=30):
    """数据库连接上下文管理器，确保连接正确关闭"""
    conn = None
    try:
        conn = sqlite3.connect('timesheet.db', timeout=timeout)
        conn.row_factory = sqlite3.Row
        # 设置WAL模式提高并发性能
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=10000')
        conn.execute('PRAGMA temp_store=memory')
        yield conn
    except sqlite3.Error as e:
        logger.error(f"数据库错误: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# 带重试机制的HTTP请求
def safe_request(url, params=None, timeout=15, max_retries=3):
    """安全的HTTP请求，带重试机制"""
    for attempt in range(max_retries):
        try:
            logger.info(f"API请求 (尝试 {attempt + 1}/{max_retries}): {url}")
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            logger.warning(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {url}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)  # 等待1秒后重试
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)  # 等待1秒后重试

# 输入验证和清理
def validate_and_clean_input(data, field_name, data_type=str, default=None, min_value=None, max_value=None):
    """验证和清理输入数据"""
    value = data.get(field_name, default)
    
    if value is None or value == '' or value == 'undefined':
        return default
    
    try:
        if data_type == float:
            result = float(value)
            if min_value is not None and result < min_value:
                return min_value
            if max_value is not None and result > max_value:
                return max_value
            return result
        elif data_type == int:
            result = int(value)
            if min_value is not None and result < min_value:
                return min_value
            if max_value is not None and result > max_value:
                return max_value
            return result
        elif data_type == str:
            return str(value).strip()
        else:
            return value
    except (ValueError, TypeError):
        logger.warning(f"数据类型转换失败 {field_name}: {value}, 使用默认值 {default}")
        return default

# 错误处理装饰器
def handle_errors(f):
    """统一错误处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数 {f.__name__} 发生错误: {e}")
            return jsonify({'success': False, 'message': '服务暂时不可用，请稍后重试'})
    return wrapper

# 数据库初始化
def init_db():
    """初始化数据库"""
    try:
        with get_db_connection() as db:
            # 创建用户表
            db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'specialist',
                    department TEXT,
                    phone TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建工时记录表
            db.execute('''
                CREATE TABLE IF NOT EXISTS timesheet_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    work_date DATE NOT NULL,
                    business_trip_days INTEGER DEFAULT 1,
                    actual_visit_days INTEGER DEFAULT 1,
                    audit_store_count INTEGER NOT NULL,
                    training_store_count INTEGER DEFAULT 0,
                    start_location TEXT,
                    end_location TEXT,
                    round_trip_distance REAL DEFAULT 0,
                    transport_mode TEXT DEFAULT 'driving',
                    schedule_number TEXT,
                    travel_hours REAL DEFAULT 0,
                    visit_hours REAL DEFAULT 0.92,
                    report_hours REAL DEFAULT 0.13,
                    total_work_hours REAL DEFAULT 0,
                    notes TEXT,
                    store_code TEXT,
                    city TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 创建用户月度默认设置表
            db.execute('''
                CREATE TABLE IF NOT EXISTS user_monthly_defaults (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    business_trip_days INTEGER DEFAULT 1,
                    actual_visit_days INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, year, month)
                )
            ''')
            
            # 检查并添加新字段（兼容现有数据库）
            try:
                # 检查用户表字段
                cursor = db.execute("PRAGMA table_info(users)")
                user_columns = [column[1] for column in cursor.fetchall()]
                
                if 'phone' not in user_columns:
                    db.execute('ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ""')
                    logger.info("添加用户表phone字段")
                
                # 检查工时记录表字段
                cursor = db.execute("PRAGMA table_info(timesheet_records)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'store_code' not in columns:
                    db.execute('ALTER TABLE timesheet_records ADD COLUMN store_code TEXT')
                    logger.info("添加store_code字段")
                
                if 'city' not in columns:
                    db.execute('ALTER TABLE timesheet_records ADD COLUMN city TEXT')
                    logger.info("添加city字段")
            
            except Exception as e:
                logger.error(f"添加新字段时出错: {e}")
            
            # 创建默认用户
            try:
                hashed_password = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt())
                db.execute('''
                    INSERT INTO users (username, password, name, role, department)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('zhaohong', hashed_password, '郑皓鸿', 'specialist', '稽核四组'))
                
                # 创建管理员用户
                admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
                db.execute('''
                    INSERT INTO users (username, password, name, role)
                    VALUES (?, ?, ?, ?)
                ''', ('admin', admin_password, '管理员', 'supervisor'))
                
                db.commit()
                logger.info("默认用户创建成功")
            except sqlite3.IntegrityError:
                logger.info("默认用户创建失败（可能已存在）: UNIQUE constraint failed: users.username")
                
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

# 在应用创建后立即初始化数据库（用于生产环境）
def initialize_database():
    """初始化数据库，用于生产环境"""
    try:
        init_db()
        logger.info("生产环境数据库初始化完成")
    except Exception as e:
        logger.error(f"生产环境数据库初始化失败: {e}")

# 如果不是在主模块中运行（如通过gunicorn），则立即初始化数据库
if __name__ != '__main__':
    initialize_database()

# 登录页面模板
# 注册页面模板
register_template = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户注册 - 古茗工时管理系统</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 20px;
        }

        .register-container {
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
            backdrop-filter: blur(10px);
        }

        .logo {
            text-align: center;
            margin-bottom: 30px;
        }

        .logo h1 {
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 24px;
        }

        .logo p {
            color: #666;
            font-size: 14px;
            margin: 0;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 6px;
            color: #333;
            font-weight: 500;
        }

        .required {
            color: #e74c3c;
        }

        input[type="text"], 
        input[type="password"], 
        input[type="tel"],
        select {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s ease;
            box-sizing: border-box;
        }

        input[type="text"]:focus, 
        input[type="password"]:focus, 
        input[type="tel"]:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease;
        }

        .btn:hover {
            transform: translateY(-1px);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .error-message {
            background: #fee;
            border: 1px solid #fcc;
            color: #c33;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .success-message {
            background: #efe;
            border: 1px solid #cfc;
            color: #3c3;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }

        .form-links {
            text-align: center;
            margin-top: 20px;
        }

        .form-links a {
            color: #667eea;
            text-decoration: none;
            font-size: 14px;
        }

        .form-links a:hover {
            text-decoration: underline;
        }

        .department-select {
            position: relative;
        }

        .input-hint {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="register-container">
        <div class="logo">
            <h1>🍃 古茗工时管理</h1>
            <p>新用户注册</p>
        </div>

        <div id="message-container"></div>

        <form id="registerForm">
            <div class="form-group">
                <label for="name">真实姓名 <span class="required">*</span></label>
                <input type="text" id="name" name="name" required>
                <div class="input-hint">请输入您的真实姓名</div>
            </div>

            <div class="form-group">
                <label for="department">所属组别 <span class="required">*</span></label>
                <select id="department" name="department" required>
                    <option value="">请选择组别</option>
                    <option value="稽核一组">稽核一组</option>
                    <option value="稽核二组">稽核二组</option>
                    <option value="稽核三组">稽核三组</option>
                    <option value="稽核四组">稽核四组</option>
                    <option value="稽核五组">稽核五组</option>
                    <option value="稽核六组">稽核六组</option>
                    <option value="稽核七组">稽核七组</option>
                    <option value="稽核八组">稽核八组</option>
                    <option value="稽核九组">稽核九组</option>
                    <option value="稽核十组">稽核十组</option>
                    <option value="管理组">管理组</option>
                    <option value="培训组">培训组</option>
                </select>
            </div>

            <div class="form-group">
                <label for="phone">手机号码 <span class="required">*</span></label>
                <input type="tel" id="phone" name="phone" pattern="[0-9]{11}" required>
                <div class="input-hint">请输入11位手机号码</div>
            </div>


            <div class="form-group">
                <label for="password">登录密码 <span class="required">*</span></label>
                <input type="password" id="password" name="password" required>
                <div class="input-hint">至少6位，建议包含字母和数字</div>
            </div>

            <button type="submit" class="btn" id="registerBtn">
                注册账户
            </button>
        </form>

        <div class="form-links">
            <a href="/login">已有账户？立即登录</a>
        </div>
    </div>

    <script>
        document.getElementById('registerForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            // 使用真实姓名作为用户名
            data.username = data.name;
            
            // 基本验证
            if (!data.name || !data.department || !data.phone || !data.password) {
                showMessage('请填写所有必填字段', 'error');
                return;
            }
            
            // 密码验证
            if (data.password.length < 6) {
                showMessage('密码长度至少6位', 'error');
                return;
            }
            
            // 手机号验证
            if (!/^[0-9]{11}$/.test(data.phone)) {
                showMessage('请输入正确的11位手机号', 'error');
                return;
            }
            
            const registerBtn = document.getElementById('registerBtn');
            registerBtn.disabled = true;
            registerBtn.textContent = '注册中...';
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showMessage(result.message, 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else {
                    showMessage(result.message, 'error');
                }
            } catch (error) {
                showMessage('注册失败，请检查网络连接', 'error');
            } finally {
                registerBtn.disabled = false;
                registerBtn.textContent = '注册账户';
            }
        });
        
        function showMessage(message, type) {
            const container = document.getElementById('message-container');
            container.innerHTML = `<div class="${type}-message">${message}</div>`;
        }
        
        // 手机号格式化
        document.getElementById('phone').addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 11) {
                value = value.substring(0, 11);
            }
            e.target.value = value;
        });
        
    </script>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>古茗工时管理系统</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            color: #2d3748;
            margin-bottom: 10px;
        }
        .logo p {
            color: #718096;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #374151;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #5a67d8;
        }
        .error {
            color: #e53e3e;
            margin-top: 10px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>🍃 古茗工时管理</h1>
            <p>稽核专员工时记录系统</p>
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label for="username">用户名（真实姓名）</label>
                <input type="text" id="username" name="username" required placeholder="请输入您的真实姓名">
            </div>
            <div class="form-group">
                <label for="password">密码</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="btn">登录</button>
            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}
        </form>
        
        <div class="form-links" style="text-align: center; margin-top: 20px;">
            <a href="/register" style="color: #667eea; text-decoration: none; font-size: 14px;">没有账户？立即注册</a>
        </div>
    </div>
</body>
</html>
'''

# 简洁的工时录入页面模板
USER_INPUT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工时录入 - {{ user.name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            line-height: 1.6;
            color: #333;
        }
        .header {
            background: white;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            color: #2d3748;
            font-size: 24px;
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .nav-links {
            display: flex;
            gap: 15px;
        }
        .nav-link {
            color: #667eea;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background 0.3s;
        }
        .nav-link:hover {
            background: #f1f5f9;
        }
        .container {
            max-width: 1000px;
            margin: 20px auto;
            padding: 0 20px;
        }
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 30px;
            margin-bottom: 20px;
        }
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            position: relative;
        }
        .form-group label {
            margin-bottom: 5px;
            font-weight: 500;
            color: #374151;
        }
        .form-group input, .form-group select {
            padding: 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: background 0.3s;
            width: 100%;
            margin-top: 20px;
        }
        .btn:hover {
            background: #5a67d8;
        }
        .btn-secondary {
            background: #6b7280;
            margin-top: 10px;
        }
        .btn-secondary:hover {
            background: #4b5563;
        }
        .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
            margin: 30px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }
        .required {
            color: #ef4444;
        }
        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-height: 320px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        }
        .search-result-item {
            padding: 12px;
            cursor: pointer;
            border-bottom: 1px solid #f3f4f6;
            transition: background-color 0.2s;
        }
        .search-result-item:hover {
            background: #f9fafb;
        }
        .search-result-item:last-child {
            border-bottom: none;
        }
        
        .recommendation-item {
            background-color: #f8f9ff !important;
            border-left: 3px solid #007bff;
        }
        
        .recommendation-label {
            background-color: #007bff;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            margin-left: 5px;
        }
        
        .recommendation-reason {
            font-size: 12px;
            color: #666;
            font-style: italic;
            margin-top: 3px;
        }
        .store-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 6px;
            font-size: 14px;
        }
        .store-address {
            font-size: 13px;
            color: #555;
            line-height: 1.4;
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
            border-left: 3px solid #e9ecef;
        }
        
        .source-info {
            margin-top: 4px;
            text-align: right;
        }
        
        .data-source {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 8px;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .data-source.amap {
            background-color: #52c41a;
            color: white;
        }
        
        .data-source.tencent {
            background-color: #1890ff;
            color: white;
        }
        
        .match-level {
            font-size: 10px;
            padding: 1px 4px;
            border-radius: 6px;
            font-weight: 500;
            margin-left: 6px;
        }
        
        .match-excellent {
            background-color: #52c41a;
            color: white;
        }
        
        .match-high {
            background-color: #1890ff;
            color: white;
        }
        
        .match-medium {
            background-color: #faad14;
            color: white;
        }
        
        .match-low {
            background-color: #d9d9d9;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>古茗工时录入</h1>
        <div class="user-info">
            <div class="nav-links">
                <a href="/user/records" class="nav-link">查看记录</a>
                <a href="/logout" class="nav-link">退出登录</a>
            </div>
            <span>{{ user.name }}</span>
        </div>
    </div>

    <div class="container">
        <div class="card">
            <h2>新增工时记录</h2>
            <form id="timesheetForm">
                <div class="section-title">基础信息</div>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="businessTripDays">出差天数</label>
                        <input type="number" id="businessTripDays" name="businessTripDays" value="1" min="1" required>
                        <small style="color: #666; font-size: 12px;">总出差天数（包含路途天数）</small>
                    </div>
                    <div class="form-group">
                        <label for="actualVisitDays">实际巡店天数 <span class="required">*</span></label>
                        <input type="number" id="actualVisitDays" name="actualVisitDays" value="1" min="1" required>
                        <small style="color: #666; font-size: 12px;">实际用于巡店的天数（排除路途时间），如出差20天，路途2天，则填写18天</small>
                    </div>
                </div>

                <div class="section-title">门店与路线信息</div>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="workDate">工作日期 <span class="required">*</span></label>
                        <input type="date" id="workDate" name="workDate" required>
                    </div>
                    <div class="form-group">
                        <label for="storeCode">门店编码</label>
                        <input type="text" id="storeCode" name="storeCode" placeholder="请输入门店编码">
                    </div>
                    <div class="form-group">
                        <label for="startCity">出发城市</label>
                        <select id="startCity" name="startCity">
                            <option value="">全国搜索</option>
                            <option value="北京">北京</option>
                            <option value="上海">上海</option>
                            <option value="广州">广州</option>
                            <option value="深圳">深圳</option>
                            <option value="杭州">杭州</option>
                            <option value="南京">南京</option>
                            <option value="苏州">苏州</option>
                            <option value="成都">成都</option>
                            <option value="重庆">重庆</option>
                            <option value="武汉">武汉</option>
                            <option value="西安">西安</option>
                            <option value="青岛">青岛</option>
                            <option value="大连">大连</option>
                            <option value="宁波">宁波</option>
                            <option value="厦门">厦门</option>
                            <option value="福州">福州</option>
                            <option value="济南">济南</option>
                            <option value="长沙">长沙</option>
                            <option value="郑州">郑州</option>
                            <option value="石家庄">石家庄</option>
                            <option value="哈尔滨">哈尔滨</option>
                            <option value="长春">长春</option>
                            <option value="沈阳">沈阳</option>
                            <option value="太原">太原</option>
                            <option value="合肥">合肥</option>
                            <option value="南昌">南昌</option>
                            <option value="南宁">南宁</option>
                            <option value="昆明">昆明</option>
                            <option value="贵阳">贵阳</option>
                            <option value="兰州">兰州</option>
                            <option value="银川">银川</option>
                            <option value="西宁">西宁</option>
                            <option value="乌鲁木齐">乌鲁木齐</option>
                            <option value="拉萨">拉萨</option>
                            <option value="海口">海口</option>
                            <option value="三亚">三亚</option>
                            <option value="台州">台州</option>
                            <option value="温州">温州</option>
                            <option value="金华">金华</option>
                            <option value="绍兴">绍兴</option>
                            <option value="嘉兴">嘉兴</option>
                            <option value="湖州">湖州</option>
                            <option value="舟山">舟山</option>
                            <option value="衢州">衢州</option>
                            <option value="丽水">丽水</option>
                            <option value="上饶">上饶</option>
                            <option value="九江">九江</option>
                            <option value="景德镇">景德镇</option>
                            <option value="萍乡">萍乡</option>
                            <option value="新余">新余</option>
                            <option value="鹰潭">鹰潭</option>
                            <option value="赣州">赣州</option>
                            <option value="宜春">宜春</option>
                            <option value="抚州">抚州</option>
                            <option value="吉安">吉安</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="startStore">出发门店 <span class="required">*</span></label>
                        <input type="text" id="startStore" name="startStore" value="古茗" autocomplete="off" required placeholder="请输入门店名称，如：古茗南山花园城店">
                        <div class="search-results" id="startStoreResults"></div>
                    </div>
                    <div class="form-group">
                        <label for="endCity">到达城市</label>
                        <input type="text" id="endCity" name="endCity" placeholder="请输入城市名称，如：北京、上海、广州" autocomplete="off">
                        <small style="color: #666; font-size: 12px; margin-top: 5px; display: block;">
                            💡 输入标准：请输入完整的城市名称，如"北京市"、"上海市"、"广州市"等。支持全国所有城市，留空则全国搜索。
                        </small>
                    </div>
                    <div class="form-group">
                        <label for="endStore">目标门店 <span class="required">*</span></label>
                        <input type="text" id="endStore" name="endStore" value="古茗" autocomplete="off" required placeholder="请输入门店名称，如：古茗南山花园城店">
                        <div class="search-results" id="endStoreResults"></div>
                    </div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label for="transportMode">交通方式</label>
                        <select id="transportMode" name="transportMode">
                            <option value="driving">驾车</option>
                            <option value="taxi">打车</option>
                            <option value="bus">大巴</option>
                            <option value="train">高铁</option>
                            <option value="airplane">飞机</option>
                            <option value="walking">步行</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="roundTripDistance">单程路程 (km)</label>
                        <input type="number" id="roundTripDistance" name="roundTripDistance" step="0.1" readonly>
                    </div>
                    <div class="form-group">
                        <label for="travelHours">路途工时 (H)</label>
                        <div style="position: relative;">
                            <input type="number" id="travelHours" name="travelHours" step="0.01" readonly>
                            <div id="actualHoursDisplay" style="display: none; position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: #e8f5e8; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #2d5016; font-weight: bold;"></div>
                        </div>
                        <small id="travelHoursHint" class="form-hint" style="display: none; color: #666; font-size: 12px; margin-top: 4px;"></small>
                    </div>
                </div>

                <button type="button" class="btn btn-secondary" onclick="calculateRoute()">计算路程</button>

                <div class="section-title">工时详情</div>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="visitHours">巡店工时 (H)</label>
                        <input type="number" id="visitHours" name="visitHours" value="0.92" step="0.01" required>
                    </div>
                    <div class="form-group">
                        <label for="reportHours">报告工时 (H)</label>
                        <input type="number" id="reportHours" name="reportHours" value="0.13" step="0.01" required>
                    </div>
                    <div class="form-group">
                        <label for="totalWorkHours">合计工时 (H)</label>
                        <input type="number" id="totalWorkHours" name="totalWorkHours" step="0.01" readonly>
                    </div>
                </div>

                <button type="submit" class="btn">保存工时记录</button>
            </form>
        </div>
    </div>

    <script>
        // 表单提交
        document.getElementById('timesheetForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            
            // 确保使用门店名称而不是完整地址
            const startStoreInput = document.getElementById('startStore');
            const endStoreInput = document.getElementById('endStore');
            
            data.startStore = startStoreInput.value;  // 门店名称
            data.endStore = endStoreInput.value;      // 门店名称
            
            // 对于高铁和飞机模式，发送用户输入的基础工时，后端会自动添加额外时间
            const transportMode = data.transportMode;
            const travelHoursInput = document.getElementById('travelHours');
            
            if ((transportMode === 'train' || transportMode === 'airplane') && travelHoursInput.dataset.userInput) {
                // 发送用户实际输入的基础工时，而不是加了额外时间的工时
                data.travelHours = travelHoursInput.value;
            }
            
            try {
                const response = await fetch('/api/my_timesheet', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('工时记录保存成功！');
                    e.target.reset();
                    document.getElementById('workDate').value = new Date().toISOString().split('T')[0];
                    document.getElementById('startStore').value = '古茗';
                    document.getElementById('endStore').value = '古茗';
                    document.getElementById('visitHours').value = '0.92';
                    document.getElementById('reportHours').value = '0.13';
                    calculateValues();
                } else {
                    alert('保存失败：' + result.message);
                }
            } catch (error) {
                alert('网络错误，请稍后重试');
                console.error('Error:', error);
            }
        });

        // 计算路程
        async function calculateRoute() {
            const startStoreInput = document.getElementById('startStore');
            const endStoreInput = document.getElementById('endStore');
            const transportMode = document.getElementById('transportMode').value;
            
            // 获取门店名称和坐标
            const startStore = startStoreInput.value; // 使用门店名称
            const endStore = endStoreInput.value; // 使用门店名称
            
            // 获取已保存的坐标
            const startLocation = startStoreInput.getAttribute('data-location');
            const endLocation = endStoreInput.getAttribute('data-location');
            
            if (!startStore || !endStore) {
                alert('请先选择出发门店和目标门店');
                return;
            }
            
            try {
                const response = await fetch('/api/calculate_route', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        start_store: startStore,
                        end_store: endStore,
                        start_location: startLocation,
                        end_location: endLocation,
                        transport_mode: transportMode,
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('roundTripDistance').value = result.distance;
                    document.getElementById('travelHours').value = result.duration.toFixed(2);
                    calculateValues();
                } else {
                    alert('路程计算失败：' + result.message);
                }
            } catch (error) {
                alert('网络错误，请稍后重试');
                console.error('Error:', error);
            }
        }

        // 计算各项数值
        function calculateValues() {
            const travelHoursInput = document.getElementById('travelHours');
            const transportMode = document.getElementById('transportMode').value;
            
            let travelHours = parseFloat(travelHoursInput.value) || 0;
            
            // 如果是高铁或飞机模式，使用最终计算的工时
            if ((transportMode === 'train' || transportMode === 'airplane') && travelHoursInput.dataset.finalHours) {
                travelHours = parseFloat(travelHoursInput.dataset.finalHours);
            }
            
            const visitHours = parseFloat(document.getElementById('visitHours').value) || 0;
            const reportHours = parseFloat(document.getElementById('reportHours').value) || 0;
            
            // 合计工时
            const totalWorkHours = travelHours + visitHours + reportHours;
            document.getElementById('totalWorkHours').value = totalWorkHours.toFixed(2);
        }

        // 设置计算监听器
        function setupCalculations() {
            const fields = ['travelHours', 'visitHours', 'reportHours'];
            fields.forEach(fieldId => {
                document.getElementById(fieldId).addEventListener('input', calculateValues);
            });
        }

        // 门店搜索功能
        function setupStoreSearch() {
            setupSearchForField('startStore', 'startStoreResults');
            setupSearchForField('endStore', 'endStoreResults');
        }

        function setupSearchForField(inputId, resultsId) {
            const input = document.getElementById(inputId);
            const resultsDiv = document.getElementById(resultsId);
            let searchTimeout;

            input.addEventListener('input', function() {
                const query = this.value.trim();
                
                clearTimeout(searchTimeout);
                
                if (query.length < 2) {
                    resultsDiv.style.display = 'none';
                    return;
                }
                
                searchTimeout = setTimeout(async () => {
                    try {
                        // 判断是搜索出发门店还是目标门店，使用对应的城市选择
                        let citySelector = '';
                        if (input.id === 'startStore') {
                            citySelector = document.getElementById('startCity') ? document.getElementById('startCity').value : '';
                        } else if (input.id === 'endStore') {
                            citySelector = document.getElementById('endCity') ? document.getElementById('endCity').value : '';
                        }
                        
                        const response = await fetch('/api/search_location', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ 
                                keyword: query,
                                city: citySelector 
                            })
                        });
                        
                        const data = await response.json();
                        
                        console.log('搜索API返回数据:', data); // 添加调试日志
                        
                        if (data.success && data.locations && data.locations.length > 0) {
                            showSearchResults(data.locations, resultsDiv, input);
                        } else {
                            // 显示"未找到结果"提示
                            console.log('搜索未找到结果:', data.message || '无结果');
                            showNoResults(resultsDiv, query);
                        }
                    } catch (error) {
                        console.error('搜索失败:', error);
                        resultsDiv.style.display = 'none';
                    }
                }, 300);
            });

            // 点击其他地方隐藏搜索结果
            document.addEventListener('click', function(e) {
                if (!input.contains(e.target) && !resultsDiv.contains(e.target)) {
                    resultsDiv.style.display = 'none';
                }
            });
        }

        function showSearchResults(locations, resultsDiv, input) {
            console.log('开始显示搜索结果，数量:', locations.length); // 调试日志
            resultsDiv.innerHTML = '';
            
            if (!locations || locations.length === 0) {
                console.log('没有搜索结果可显示');
                showNoResults(resultsDiv, input.value, input);
                return;
            }
            
            // 按相关性分数排序（从高到低）
            locations.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
            
            // 显示最多12个高匹配度结果
            locations.slice(0, 12).forEach((location, index) => {
                console.log('显示结果 ' + (index + 1) + ':', location); // 调试日志
                
                const item = document.createElement('div');
                
                // 检查是否为推荐结果
                const isRecommendation = location.is_recommendation || false;
                item.className = isRecommendation ? 'search-result-item recommendation-item' : 'search-result-item';
                
                // 安全获取门店名称和地址信息
                const displayText = location.name || '未知店铺';
                const recommendationLabel = isRecommendation ? ' <span class="recommendation-label">推荐</span>' : '';
                let addressText = '';
                
                // 优先显示详细地址，确保用户能看到完整的地址信息
                // 处理address字段可能是数组的情况
                let address = location.address;
                if (Array.isArray(address)) {
                    address = address.length > 0 ? address.join(', ') : '';
                } else if (typeof address !== 'string') {
                    address = '';
                }
                
                if (address && address.trim()) {
                    addressText = address;
                    // 如果有省市区信息，补充完整地址
                    if (location.pname && location.cityname && location.adname) {
                        const fullLocation = location.pname + location.cityname + location.adname;
                        if (!addressText.includes(location.pname)) {
                            addressText = fullLocation + ' ' + addressText;
                        }
                    }
                } else if (location.full_address) {
                    addressText = location.full_address;
                } else if (location.cityname && location.pname && location.adname) {
                    addressText = location.pname + location.cityname + location.adname;
                } else {
                    addressText = '地址信息不完整';
                }
                
                // 推荐原因
                const recommendationReason = location.recommendation_reason ? 
                    '<div class="recommendation-reason">' + location.recommendation_reason + '</div>' : '';
                    
                // 添加数据源标识和匹配度
                const sourceText = location.source === 'tencent' ? 
                    '<span class="data-source tencent">腾讯</span>' : 
                    '<span class="data-source amap">高德</span>';
                
                // 匹配度显示
                const relevanceScore = location.relevance_score || 0;
                let matchLevel = '';
                let matchClass = '';
                if (relevanceScore >= 150) {
                    matchLevel = '精确匹配';
                    matchClass = 'match-excellent';
                } else if (relevanceScore >= 100) {
                    matchLevel = '高度匹配';
                    matchClass = 'match-high';
                } else if (relevanceScore >= 60) {
                    matchLevel = '中度匹配';
                    matchClass = 'match-medium';
                } else {
                    matchLevel = '低度匹配';
                    matchClass = 'match-low';
                }
                
                const matchText = '<span class="match-level ' + matchClass + '">' + matchLevel + '</span>';
                
                item.innerHTML = 
                    '<div class="store-name">' + displayText + recommendationLabel + '</div>' +
                    '<div class="store-address">' + addressText + '</div>' +
                    '<div class="source-info">' + sourceText + ' ' + matchText + '</div>' +
                    recommendationReason;
                
                item.addEventListener('click', function() {
                    console.log('用户选择了:', location); // 调试日志
                    
                    // 选择时只显示门店名称，但保存完整地址信息到隐藏字段
                    input.value = location.name || displayText;
                    
                    // 将完整地址保存到隐藏的data属性中
                    const fullAddress = location.full_address || location.address || addressText;
                    input.setAttribute('data-full-address', fullAddress);
                    input.setAttribute('data-location', location.location || '');
                    
                    resultsDiv.style.display = 'none';
                    
                    console.log('已设置门店信息:', {
                        name: input.value,
                        fullAddress: fullAddress,
                        location: location.location
                    });
                });
                
                resultsDiv.appendChild(item);
            });
            
            // 添加"尝试腾讯地图"按钮
            const tryTencentButton = document.createElement('div');
            tryTencentButton.className = 'search-result-item try-tencent-button';
            tryTencentButton.style.cssText = `
                background: linear-gradient(135deg, #4285f4, #34a853);
                color: white;
                text-align: center;
                font-weight: bold;
                cursor: pointer;
                border-radius: 6px;
                margin-top: 8px;
                padding: 12px;
                transition: all 0.3s ease;
            `;
            tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
            
            tryTencentButton.addEventListener('click', async function() {
                const query = input.value.trim();
                if (!query) return;
                
                try {
                    // 改变按钮状态
                    tryTencentButton.innerHTML = '🔄 搜索中...';
                    tryTencentButton.style.opacity = '0.7';
                    
                    // 强制调用腾讯地图搜索
                    const response = await fetch('/api/search_location', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            keyword: query,
                            force_tencent: true  // 强制使用腾讯地图
                        })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log('腾讯地图搜索结果:', data);
                        
                        if (data.locations && data.locations.length > 0) {
                            // 标记结果来源
                            data.locations.forEach(loc => {
                                if (loc.source === 'tencent') {
                                    loc.tencent_search = true;
                                }
                            });
                            showSearchResults(data.locations, resultsDiv, input);
                        } else {
                            tryTencentButton.innerHTML = '❌ 腾讯地图也未找到结果';
                            setTimeout(() => {
                                tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                                tryTencentButton.style.opacity = '1';
                            }, 2000);
                        }
                    }
                } catch (error) {
                    console.error('腾讯地图搜索失败:', error);
                    tryTencentButton.innerHTML = '❌ 搜索失败，请重试';
                    setTimeout(() => {
                        tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                        tryTencentButton.style.opacity = '1';
                    }, 2000);
                }
            });
            
            // 鼠标悬停效果
            tryTencentButton.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 12px rgba(66, 133, 244, 0.3)';
            });
            
            tryTencentButton.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            });
            
            resultsDiv.appendChild(tryTencentButton);
            
            resultsDiv.style.display = 'block';
            console.log('搜索结果已显示');
        }

        function showNoResults(resultsDiv, query, input) {
            resultsDiv.innerHTML = '';
            
            const noResultItem = document.createElement('div');
            noResultItem.className = 'search-result-item';
            noResultItem.style.color = '#666';
            noResultItem.style.fontStyle = 'italic';
            noResultItem.textContent = '未找到"' + query + '"相关地点，请尝试输入更具体的地址';
            
            resultsDiv.appendChild(noResultItem);
            
            // 添加"尝试腾讯地图"按钮
            if (input) {
                const tryTencentButton = document.createElement('div');
                tryTencentButton.className = 'search-result-item try-tencent-button';
                tryTencentButton.style.cssText = `
                    background: linear-gradient(135deg, #4285f4, #34a853);
                    color: white;
                    text-align: center;
                    font-weight: bold;
                    cursor: pointer;
                    border-radius: 6px;
                    margin-top: 8px;
                    padding: 12px;
                    transition: all 0.3s ease;
                `;
                tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                
                tryTencentButton.addEventListener('click', async function() {
                    const searchQuery = input.value.trim();
                    if (!searchQuery) return;
                    
                    try {
                        // 改变按钮状态
                        tryTencentButton.innerHTML = '🔄 搜索中...';
                        tryTencentButton.style.opacity = '0.7';
                        
                        // 强制调用腾讯地图搜索
                        const response = await fetch('/api/search_location', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                keyword: searchQuery,
                                force_tencent: true  // 强制使用腾讯地图
                            })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            console.log('腾讯地图搜索结果:', data);
                            
                            if (data.locations && data.locations.length > 0) {
                                // 标记结果来源
                                data.locations.forEach(loc => {
                                    if (loc.source === 'tencent') {
                                        loc.tencent_search = true;
                                    }
                                });
                                showSearchResults(data.locations, resultsDiv, input);
                            } else {
                                tryTencentButton.innerHTML = '❌ 腾讯地图也未找到结果';
                                setTimeout(() => {
                                    tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                                    tryTencentButton.style.opacity = '1';
                                }, 2000);
                            }
                        }
                    } catch (error) {
                        console.error('腾讯地图搜索失败:', error);
                        tryTencentButton.innerHTML = '❌ 搜索失败，请重试';
                        setTimeout(() => {
                            tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                            tryTencentButton.style.opacity = '1';
                        }, 2000);
                    }
                });
                
                // 鼠标悬停效果
                tryTencentButton.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = '0 4px 12px rgba(66, 133, 244, 0.3)';
                });
                
                tryTencentButton.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = 'none';
                });
                
                resultsDiv.appendChild(tryTencentButton);
            }
            
            resultsDiv.style.display = 'block';
            
            // 3秒后自动隐藏（但不隐藏按钮）
            setTimeout(() => {
                if (!resultsDiv.querySelector('.try-tencent-button')) {
                    resultsDiv.style.display = 'none';
                }
            }, 5000);  // 延长到5秒，给用户更多时间点击腾讯搜索
        }

        // 验证实际巡店天数
        function validateVisitDays() {
            const businessTripDays = parseInt(document.getElementById('businessTripDays').value) || 0;
            const actualVisitDays = parseInt(document.getElementById('actualVisitDays').value) || 0;
            
            if (actualVisitDays > businessTripDays) {
                document.getElementById('actualVisitDays').setCustomValidity('实际巡店天数不能大于出差天数');
            } else {
                document.getElementById('actualVisitDays').setCustomValidity('');
            }
        }

        // 交通方式改变处理
        function handleTransportModeChange() {
            const transportMode = document.getElementById('transportMode').value;
            const travelHoursInput = document.getElementById('travelHours');
            const travelHoursHint = document.getElementById('travelHoursHint');
            const actualHoursDisplay = document.getElementById('actualHoursDisplay');
            
            if (transportMode === 'train' || transportMode === 'airplane') {
                // 高铁和飞机模式：允许手动输入
                travelHoursInput.removeAttribute('readonly');
                travelHoursInput.style.backgroundColor = '#fff';
                
                if (transportMode === 'train') {
                    travelHoursHint.textContent = '高铁模式：请手动输入实际路途时间，系统将自动在此基础上增加1小时';
                } else if (transportMode === 'airplane') {
                    travelHoursHint.textContent = '飞机模式：请手动输入实际路途时间，系统将自动在此基础上增加2小时';
                }
                travelHoursHint.style.display = 'block';
                
                // 如果当前值为0或者是自动计算的值，设置一个合理的默认值
                if (!travelHoursInput.value || travelHoursInput.value === '0' || travelHoursInput.value === '0.00' || !travelHoursInput.dataset.userInput) {
                    if (transportMode === 'train') {
                        travelHoursInput.value = '3.0'; // 高铁默认3小时
                    } else if (transportMode === 'airplane') {
                        travelHoursInput.value = '2.0'; // 飞机默认2小时
                    }
                    // 触发输入事件来更新显示
                    handleTravelHoursInput();
                }
                
                actualHoursDisplay.style.display = 'block';
            } else {
                // 其他交通方式：只读模式，由系统计算
                travelHoursInput.setAttribute('readonly', 'readonly');
                travelHoursInput.style.backgroundColor = '#f5f5f5';
                travelHoursHint.style.display = 'none';
                actualHoursDisplay.style.display = 'none';
                travelHoursInput.removeAttribute('data-user-input');
                travelHoursInput.removeAttribute('data-final-hours');
            }
        }

        // 处理路途工时手动输入
        function handleTravelHoursInput() {
            const transportMode = document.getElementById('transportMode').value;
            const travelHoursInput = document.getElementById('travelHours');
            const actualHoursDisplay = document.getElementById('actualHoursDisplay');
            
            if (transportMode === 'train' || transportMode === 'airplane') {
                // 标记为用户手动输入
                travelHoursInput.dataset.userInput = 'true';
                
                const baseHours = parseFloat(travelHoursInput.value) || 0;
                let finalHours = baseHours;
                let extraHours = 0;
                
                if (transportMode === 'train') {
                    extraHours = 1;
                    finalHours = baseHours + 1; // 高铁增加1小时
                } else if (transportMode === 'airplane') {
                    extraHours = 2;
                    finalHours = baseHours + 2; // 飞机增加2小时
                }
                
                // 显示最终计算的工时
                travelHoursInput.dataset.finalHours = finalHours.toFixed(2);
                
                // 显示实际计算工时的提示
                if (baseHours > 0) {
                    actualHoursDisplay.textContent = `实际: ${finalHours.toFixed(2)}H`;
                    actualHoursDisplay.style.display = 'block';
                } else {
                    actualHoursDisplay.style.display = 'none';
                }
                
                calculateValues();
            } else {
                actualHoursDisplay.style.display = 'none';
            }
        }

        // 加载月度默认设置
        async function loadMonthlyDefaults() {
            try {
                const response = await fetch('/api/monthly_defaults', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const result = await response.json();
                
                if (result.success && result.defaults) {
                    document.getElementById('businessTripDays').value = result.defaults.business_trip_days;
                    document.getElementById('actualVisitDays').value = result.defaults.actual_visit_days;
                }
            } catch (error) {
                console.error('加载月度默认设置失败:', error);
            }
        }

        // 保存月度默认设置
        async function saveMonthlyDefaults() {
            try {
                const businessTripDays = parseInt(document.getElementById('businessTripDays').value) || 1;
                const actualVisitDays = parseInt(document.getElementById('actualVisitDays').value) || 1;
                
                const response = await fetch('/api/monthly_defaults', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        business_trip_days: businessTripDays,
                        actual_visit_days: actualVisitDays
                    })
                });
                
                const result = await response.json();
                
                if (!result.success) {
                    console.error('保存月度默认设置失败:', result.message);
                }
            } catch (error) {
                console.error('保存月度默认设置失败:', error);
            }
        }

        // 页面初始化
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('workDate').value = new Date().toISOString().split('T')[0];
            setupCalculations();
            setupStoreSearch();
            calculateValues();
            
            // 加载月度默认设置
            loadMonthlyDefaults();
            
            // 添加月度默认设置保存监听器
            document.getElementById('businessTripDays').addEventListener('blur', saveMonthlyDefaults);
            document.getElementById('actualVisitDays').addEventListener('blur', saveMonthlyDefaults);
            
            // 添加交通方式改变监听器
            document.getElementById('transportMode').addEventListener('change', handleTransportModeChange);
            document.getElementById('travelHours').addEventListener('input', handleTravelHoursInput);
            
            // 初始化交通方式状态
            handleTransportModeChange();
            
            // 添加实际巡店天数验证
            document.getElementById('businessTripDays').addEventListener('input', validateVisitDays);
            document.getElementById('actualVisitDays').addEventListener('input', validateVisitDays);
        });
    </script>
</body>
</html>
'''

# 工时记录展示页面模板（仿古茗系统样式）
USER_RECORDS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工时记录 - {{ user.name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo {
            font-size: 24px;
            font-weight: 600;
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .nav-links {
            display: flex;
            gap: 15px;
        }
        .nav-link {
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background 0.3s;
        }
        .nav-link:hover {
            background: rgba(255,255,255,0.1);
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .breadcrumb {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .breadcrumb-text {
            color: #666;
            font-size: 14px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 32px;
            font-weight: 600;
            color: #3498db;
            margin-bottom: 5px;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        .table-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .table-header {
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .table-title {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
        }
        .table-actions {
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-primary:hover {
            background: #2980b9;
        }
        .btn-success {
            background: #27ae60;
            color: white;
        }
        .btn-success:hover {
            background: #229954;
        }
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        .btn-danger:hover {
            background: #c0392b;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .data-table th {
            background: #f8f9fa;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
            white-space: nowrap;
        }
        .data-table td {
            padding: 10px 8px;
            border-bottom: 1px solid #dee2e6;
            white-space: nowrap;
        }
        .data-table tbody tr:hover {
            background: #f8f9fa;
        }
        .number {
            text-align: right;
        }
        .action-buttons {
            display: flex;
            gap: 5px;
        }
        .btn-sm {
            padding: 4px 8px;
            font-size: 12px;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-icon {
            font-size: 48px;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        /* 表单样式 */
        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin: 20px 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #3498db;
        }
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .form-group {
            position: relative;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #2c3e50;
            font-size: 14px;
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s, box-shadow 0.3s;
            background: white;
        }
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }
        .form-group textarea {
            height: 80px;
            resize: vertical;
        }
        .required {
            color: #e74c3c;
        }
        .form-actions {
            display: flex;
            gap: 15px;
            justify-content: flex-end;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }
        .btn-large {
            padding: 12px 24px;
            font-size: 16px;
        }
        .btn-secondary {
            background: #95a5a6;
            color: white;
        }
        .btn-secondary:hover {
            background: #7f8c8d;
        }
        .route-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e9ecef;
            border-top: none;
            max-height: 320px;
            overflow-y: auto;
            z-index: 1000;
            border-radius: 0 0 6px 6px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .search-result-item {
            padding: 12px;
            cursor: pointer;
            border-bottom: 1px solid #f3f4f6;
            transition: background-color 0.2s;
        }
        .search-result-item:hover {
            background: #f9fafb;
        }
        .search-result-item:last-child {
            border-bottom: none;
        }
        
        .recommendation-item {
            background-color: #f8f9ff !important;
            border-left: 3px solid #007bff;
        }
        
        .recommendation-label {
            background-color: #007bff;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            margin-left: 5px;
        }
        
        .recommendation-reason {
            font-size: 12px;
            color: #666;
            font-style: italic;
            margin-top: 3px;
        }
        .store-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 6px;
            font-size: 14px;
        }
        .store-address {
            font-size: 13px;
            color: #555;
            line-height: 1.4;
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
            border-left: 3px solid #e9ecef;
        }
        
        .source-info {
            margin-top: 4px;
            text-align: right;
        }
        
        .data-source {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 8px;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .data-source.amap {
            background-color: #52c41a;
            color: white;
        }
        
        .data-source.tencent {
            background-color: #1890ff;
            color: white;
        }
        
        .match-level {
            font-size: 10px;
            padding: 1px 4px;
            border-radius: 6px;
            font-weight: 500;
            margin-left: 6px;
        }
        
        .match-excellent {
            background-color: #52c41a;
            color: white;
        }
        
        .match-high {
            background-color: #1890ff;
            color: white;
        }
        
        .match-medium {
            background-color: #faad14;
            color: white;
        }
        
        .match-low {
            background-color: #d9d9d9;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">古茗工时管理系统</div>
            <div class="user-info">
                <div class="nav-links">
                    <a href="/user" class="nav-link">录入工时</a>
                    <a href="/user/records" class="nav-link">查看记录</a>
                    <a href="/logout" class="nav-link">退出登录</a>
                </div>
                <span>{{ user.name }}</span>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="breadcrumb">
            <div class="breadcrumb-text">巡店记录 / 基础信息 / 工时记录</div>
        </div>

        <!-- 统计卡片 -->
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-number" id="totalRecords">0</div>
                <div class="stat-label">总记录数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalHours">0.00h</div>
                <div class="stat-label">总工时</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalDistance">0.0km</div>
                <div class="stat-label">总里程</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="actualWorkDays">0</div>
                <div class="stat-label">巡店日期数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avgDailyHours">0.00h</div>
                <div class="stat-label">日均工时</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avgStoreTime">0.00h</div>
                <div class="stat-label">月店均巡店时长</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="extraStores">0</div>
                <div class="stat-label">额外巡店量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="bonusSalary">0元</div>
                <div class="stat-label">自主巡店加班薪资</div>
            </div>
        </div>

        <!-- 数据表格 -->
        <!-- 新增记录表单 -->
        <div class="table-container" style="margin-bottom: 30px;">
            <div class="table-header">
                <div class="table-title">新增工时记录</div>
                <div class="table-actions">
                    <button onclick="toggleForm()" class="btn btn-primary" id="toggleFormBtn">展开表单</button>
                </div>
            </div>
            <div id="newRecordForm" style="display: none; padding: 20px; border-top: 1px solid #e9ecef;">
                <form id="timesheetForm">
                    <div class="section-title">基础信息</div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label for="businessTripDays">出差天数</label>
                            <input type="number" id="businessTripDays" name="businessTripDays" value="1" min="1" required>
                            <small style="color: #666; font-size: 12px;">总出差天数（包含路途天数）</small>
                        </div>
                        <div class="form-group">
                            <label for="actualVisitDays">实际巡店天数 <span class="required">*</span></label>
                            <input type="number" id="actualVisitDays" name="actualVisitDays" value="1" min="1" required>
                            <small style="color: #666; font-size: 12px;">实际用于巡店的天数（排除路途时间），如出差20天，路途2天，则填写18天</small>
                        </div>
                    </div>

                    <div class="section-title">门店与路线信息</div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label for="workDate">工作日期 <span class="required">*</span></label>
                            <input type="date" id="workDate" name="workDate" required>
                        </div>
                        <div class="form-group">
                            <label for="storeCode">门店编码</label>
                            <input type="text" id="storeCode" name="storeCode" placeholder="请输入门店编码">
                        </div>
                        <div class="form-group">
                            <label for="startCity">出发城市</label>
                            <select id="startCity" name="startCity">
                                <option value="">全国搜索</option>
                                <option value="北京">北京</option>
                                <option value="上海">上海</option>
                                <option value="广州">广州</option>
                                <option value="深圳">深圳</option>
                                <option value="杭州">杭州</option>
                                <option value="南京">南京</option>
                                <option value="苏州">苏州</option>
                                <option value="成都">成都</option>
                                <option value="重庆">重庆</option>
                                <option value="武汉">武汉</option>
                                <option value="西安">西安</option>
                                <option value="青岛">青岛</option>
                                <option value="大连">大连</option>
                                <option value="宁波">宁波</option>
                                <option value="厦门">厦门</option>
                                <option value="福州">福州</option>
                                <option value="济南">济南</option>
                                <option value="长沙">长沙</option>
                                <option value="郑州">郑州</option>
                                <option value="石家庄">石家庄</option>
                                <option value="哈尔滨">哈尔滨</option>
                                <option value="长春">长春</option>
                                <option value="沈阳">沈阳</option>
                                <option value="太原">太原</option>
                                <option value="合肥">合肥</option>
                                <option value="南昌">南昌</option>
                                <option value="南宁">南宁</option>
                                <option value="昆明">昆明</option>
                                <option value="贵阳">贵阳</option>
                                <option value="兰州">兰州</option>
                                <option value="银川">银川</option>
                                <option value="西宁">西宁</option>
                                <option value="乌鲁木齐">乌鲁木齐</option>
                                <option value="拉萨">拉萨</option>
                                <option value="海口">海口</option>
                                <option value="三亚">三亚</option>
                                <option value="台州">台州</option>
                                <option value="温州">温州</option>
                                <option value="金华">金华</option>
                                <option value="绍兴">绍兴</option>
                                <option value="嘉兴">嘉兴</option>
                                <option value="湖州">湖州</option>
                                <option value="舟山">舟山</option>
                                <option value="衢州">衢州</option>
                                <option value="丽水">丽水</option>
                                <option value="上饶">上饶</option>
                                <option value="九江">九江</option>
                                <option value="景德镇">景德镇</option>
                                <option value="萍乡">萍乡</option>
                                <option value="新余">新余</option>
                                <option value="鹰潭">鹰潭</option>
                                <option value="赣州">赣州</option>
                                <option value="宜春">宜春</option>
                                <option value="抚州">抚州</option>
                                <option value="吉安">吉安</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="startStore">出发门店 <span class="required">*</span></label>
                            <input type="text" id="startStore" name="startStore" value="古茗" autocomplete="off" required placeholder="请输入门店名称，如：古茗南山花园城店">
                            <div class="search-results" id="startStoreResults"></div>
                        </div>
                        <div class="form-group">
                            <label for="endCity">到达城市</label>
                            <input type="text" id="endCity" name="endCity" placeholder="请输入城市名称，如：北京、上海、广州" autocomplete="off">
                            <small style="color: #666; font-size: 12px; margin-top: 5px; display: block;">
                                💡 输入标准：请输入完整的城市名称，如"北京市"、"上海市"、"广州市"等。支持全国所有城市，留空则全国搜索。
                            </small>
                        </div>
                        <div class="form-group">
                            <label for="endStore">目标门店 <span class="required">*</span></label>
                            <input type="text" id="endStore" name="endStore" value="古茗" autocomplete="off" required placeholder="请输入门店名称，如：古茗南山花园城店">
                            <div class="search-results" id="endStoreResults"></div>
                        </div>
                    </div>

                    <div class="form-grid">
                        <div class="form-group">
                            <label for="transportMode">交通方式</label>
                            <select id="transportMode" name="transportMode">
                                <option value="driving">驾车</option>
                                <option value="taxi">打车</option>
                                <option value="bus">大巴</option>
                                <option value="walking">步行</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>单程距离</label>
                            <div class="route-info">
                                <button type="button" onclick="calculateRoute()" class="btn btn-primary">计算路线</button>
                                <div id="routeResult"></div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="notes">备注信息</label>
                            <textarea id="notes" name="notes" placeholder="请输入备注信息"></textarea>
                        </div>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary btn-large">保存工时记录</button>
                        <button type="button" onclick="resetForm()" class="btn btn-secondary">重置表单</button>
                    </div>
                </form>
            </div>
        </div>

        <div class="table-container">
            <div class="table-header">
                <div class="table-title">工时记录列表</div>
                <div class="table-actions">
                    <button class="btn btn-success" onclick="exportData()">导出数据</button>
                </div>
            </div>
            
            <div style="overflow-x: auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>门店编码</th>
                            <th>城市</th>
                            <th>门店名称</th>
                            <th>交通方式</th>
                            <th>里程</th>
                            <th>里程时间</th>
                            <th>巡店工时 (H)</th>
                            <th>报告工时 (H)</th>
                            <th>因高峰产生的额外沟通工时 (H)</th>
                            <th>合计工时 (H)</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="dataTableBody">
                        <!-- 数据将通过JavaScript动态加载 -->
                    </tbody>
                </table>
            </div>
            
            <div id="emptyState" class="empty-state" style="display: none;">
                <div class="empty-icon">暂无记录</div>
                <h3>暂无工时记录</h3>
                <p>点击"展开表单"开始录入您的工时信息</p>
                <button onclick="toggleForm()" class="btn btn-primary" style="margin-top: 20px;">立即录入</button>
            </div>
        </div>
    </div>

    <script>
        // 加载工时记录
        async function loadRecords() {
            try {
                const response = await fetch('/api/my_timesheet');
                const data = await response.json();
                
                if (data.records && data.records.length > 0) {
                    displayRecords(data.records);
                    updateStatistics(data.records);
                    document.getElementById('emptyState').style.display = 'none';
                } else {
                    document.getElementById('dataTableBody').innerHTML = '';
                    document.getElementById('emptyState').style.display = 'block';
                    resetStatistics();
                }
            } catch (error) {
                console.error('加载记录失败:', error);
                document.getElementById('emptyState').style.display = 'block';
            }
        }

        // 显示记录
        function displayRecords(records) {
            const tbody = document.getElementById('dataTableBody');
            tbody.innerHTML = '';
            
            records.forEach(record => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${record.work_date}</td>
                    <td>${record.store_code || '755' + record.id}</td>
                    <td>${record.city || '台州'}</td>
                    <td>${record.end_location || record.start_location || '门店'}</td>
                    <td>${record.transport_mode === 'driving' ? '驾车' : record.transport_mode === 'taxi' ? '打车' : record.transport_mode}</td>
                    <td class="number">${record.round_trip_distance}km</td>
                    <td class="number">${record.travel_hours.toFixed(2)}h</td>
                    <td class="number">${record.visit_hours.toFixed(2)}</td>
                    <td class="number">${record.report_hours.toFixed(2)}</td>
                    <td class="number">0.00</td>
                    <td class="number">${record.total_work_hours.toFixed(2)}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn btn-primary btn-sm" onclick="editRecord(${record.id})">修改</button>
                            <button class="btn btn-danger btn-sm" onclick="deleteRecord(${record.id})">删除</button>
                        </div>
                    </td>
                `;
            });
        }

        // 薪资梯队计算函数
        function calculateBonusSalary(avgStoreTime, extraStores) {
            // 根据月店均巡店时长确定梯队
            let salaryMatrix;
            if (avgStoreTime <= 1.5) {
                salaryMatrix = [25, 30, 35, 40];
            } else if (avgStoreTime <= 1.7) {
                salaryMatrix = [30, 35, 40, 45];
            } else if (avgStoreTime <= 2) {
                salaryMatrix = [35, 40, 45, 50];
            } else {
                salaryMatrix = [40, 45, 50, 55];
            }
            
            // 根据额外巡店量确定档位
            let tierIndex;
            if (extraStores <= 10) {
                tierIndex = 0;
            } else if (extraStores <= 20) {
                tierIndex = 1;
            } else if (extraStores <= 30) {
                tierIndex = 2;
            } else {
                tierIndex = 3;
            }
            
            return extraStores * salaryMatrix[tierIndex];
        }

        // 更新统计信息
        function updateStatistics(records) {
            const totalRecords = records.length;
            let totalHours = 0;
            let totalStores = 0;
            let totalDistance = 0;
            let totalTravelHours = 0;  // 总里程时长
            let totalVisitHours = 0;   // 总巡店时长
            let totalActualVisitDays = 0; // 累计实际巡店天数
            
            // 统计不同工作日期的数量（实际巡店日期数）
            const uniqueDates = new Set();
            
            records.forEach(record => {
                totalHours += record.total_work_hours || 0;
                totalStores += record.audit_store_count || 0;
                totalDistance += record.round_trip_distance || 0;
                totalTravelHours += record.travel_hours || 0;
                totalVisitHours += record.visit_hours || 0;
                
                // 累加每条记录的实际巡店天数（用于显示）
                totalActualVisitDays += record.actual_visit_days || 0;
                
                // 添加工作日期到集合中（去重）
                if (record.work_date) {
                    uniqueDates.add(record.work_date);
                }
            });
            
            // 实际巡店日期数 = 不同日期的数量
            const actualWorkDays = uniqueDates.size;
            
            // 路途天数计算逻辑：非浙江省需要减去路途时间
            // 填写期间：每个日期-1天，最终核算：总共-2天
            const isZhejiang = false; // 这里可以根据用户地区设置
            let adjustedWorkDays = actualWorkDays;
            
            if (!isZhejiang && actualWorkDays > 0) {
                // 填写期间逻辑：每个工作日期减去1天路途时间
                adjustedWorkDays = Math.max(1, actualWorkDays - 1);
                // 注：最终核算时再减去2天的逻辑可以在月度汇总时应用
            }
            
            // 日均工时 = 总工时 ÷ 实际巡店日期数
            const avgDailyHours = actualWorkDays > 0 ? totalHours / actualWorkDays : 0;
            
            // 月店均巡店时长 = 个人当月店均里程时长 + 个人平均巡店时长（最高60分钟）
            const avgTravelTimePerStore = totalStores > 0 ? totalTravelHours / totalStores : 0;
            const avgVisitTimePerStore = totalStores > 0 ? totalVisitHours / totalStores : 0;
            const cappedVisitTime = Math.min(avgVisitTimePerStore, 1.0); // 最高60分钟(1小时)
            const avgStoreTime = avgTravelTimePerStore + cappedVisitTime;
            
            // 额外巡店量 = (本月实际总工时 - 调整后巡店天数×8H) ÷ 月店均巡店时长
            const standardHours = adjustedWorkDays * 8; // 标准工时 = 调整后巡店天数 × 8小时
            const extraHours = Math.max(0, totalHours - standardHours); // 超出的工时
            const extraStores = avgStoreTime > 0 ? Math.floor(extraHours / avgStoreTime) : 0;
            
            // 自主巡店加班薪资
            const bonusSalary = calculateBonusSalary(avgStoreTime, extraStores);
            
            // 更新页面显示
            document.getElementById('totalRecords').textContent = totalRecords;
            document.getElementById('totalHours').textContent = totalHours.toFixed(2) + 'h';
            document.getElementById('totalDistance').textContent = totalDistance.toFixed(1) + 'km';
            document.getElementById('actualWorkDays').textContent = actualWorkDays + '天';
            document.getElementById('avgDailyHours').textContent = avgDailyHours.toFixed(2) + 'h';
            document.getElementById('avgStoreTime').textContent = avgStoreTime.toFixed(2) + 'h';
            document.getElementById('extraStores').textContent = extraStores + '家';
            document.getElementById('bonusSalary').textContent = bonusSalary + '元';
        }

        // 重置统计信息
        function resetStatistics() {
            document.getElementById('totalRecords').textContent = '0';
            document.getElementById('totalHours').textContent = '0.00h';
            document.getElementById('totalDistance').textContent = '0.0km';
            document.getElementById('actualWorkDays').textContent = '0天';
            document.getElementById('avgDailyHours').textContent = '0.00h';
            document.getElementById('avgStoreTime').textContent = '0.00h';
            document.getElementById('extraStores').textContent = '0家';
            document.getElementById('bonusSalary').textContent = '0元';
        }

        // 修改记录 - 跳转到录入页面
        function editRecord(id) {
            window.location.href = '/user?edit=' + id;
        }

        // 删除记录
        async function deleteRecord(id) {
            if (!confirm('确定要删除这条记录吗？')) {
                return;
            }
            
            try {
                const response = await fetch('/api/my_timesheet/' + id, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('记录删除成功！');
                    loadRecords();
                } else {
                    alert('删除失败：' + result.message);
                }
            } catch (error) {
                alert('网络错误，请稍后重试');
                console.error('Error:', error);
            }
        }

        // 导出数据
        function exportData() {
            window.location.href = '/api/export_timesheet';
        }

        // 切换表单显示/隐藏
        function toggleForm() {
            const form = document.getElementById('newRecordForm');
            const btn = document.getElementById('toggleFormBtn');
            
            if (form.style.display === 'none') {
                form.style.display = 'block';
                btn.textContent = '隐藏表单';
                // 设置默认日期为今天
                document.getElementById('workDate').value = new Date().toISOString().split('T')[0];
            } else {
                form.style.display = 'none';
                btn.textContent = '展开表单';
            }
        }
        
        // 重置表单
        function resetForm() {
            document.getElementById('timesheetForm').reset();
            document.getElementById('workDate').value = new Date().toISOString().split('T')[0];
            document.getElementById('routeResult').innerHTML = '';
            // 清空搜索结果
            document.getElementById('startStoreResults').innerHTML = '';
            document.getElementById('endStoreResults').innerHTML = '';
        }
        
        // 计算路线
        async function calculateRoute() {
            const startStore = document.getElementById('startStore').value;
            const endStore = document.getElementById('endStore').value;
            const transportMode = document.getElementById('transportMode').value;
            
            if (!startStore || !endStore) {
                alert('请先选择出发门店和目标门店');
                return;
            }
            
            // 获取已保存的坐标
            const startLocation = document.getElementById('startStore').getAttribute('data-location');
            const endLocation = document.getElementById('endStore').getAttribute('data-location');
            
            try {
                const response = await fetch('/api/calculate_route', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        start_store: startStore,
                        end_store: endStore,
                        start_location: startLocation,
                        end_location: endLocation,
                        transport_mode: transportMode,
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('routeResult').innerHTML = 
                        `<span style="color: #27ae60;">✓ ${result.distance}km, ${result.duration}小时</span>`;
                } else {
                    document.getElementById('routeResult').innerHTML = 
                        `<span style="color: #e74c3c;">✗ ${result.message}</span>`;
                }
            } catch (error) {
                document.getElementById('routeResult').innerHTML = 
                    `<span style="color: #e74c3c;">✗ 计算失败，请稍后重试</span>`;
            }
        }
        
        // 门店搜索功能
        let searchTimeout;
        function setupStoreSearch(inputId, resultsId) {
            const input = document.getElementById(inputId);
            const results = document.getElementById(resultsId);
            
            input.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                const keyword = this.value.trim();
                
                if (keyword.length < 2) {
                    results.innerHTML = '';
                    return;
                }
                
                searchTimeout = setTimeout(async () => {
                    try {
                        // 判断是搜索出发门店还是目标门店，使用对应的城市选择
                        let citySelector = '';
                        if (input.id === 'startStore') {
                            citySelector = document.getElementById('startCity') ? document.getElementById('startCity').value : '';
                        } else if (input.id === 'endStore') {
                            citySelector = document.getElementById('endCity') ? document.getElementById('endCity').value : '';
                        }
                        
                        const response = await fetch('/api/search_location', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ 
                                keyword: keyword,
                                city: citySelector 
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success && data.locations) {
                            showSearchResults(data.locations, results, input);
                        } else {
                            results.innerHTML = '<div class="search-result-item">未找到相关门店</div>';
                        }
                    } catch (error) {
                        results.innerHTML = '<div class="search-result-item">搜索失败，请稍后重试</div>';
                    }
                }, 300);
            });
            
            // 点击外部隐藏搜索结果
            document.addEventListener('click', function(e) {
                if (!input.contains(e.target) && !results.contains(e.target)) {
                    results.innerHTML = '';
                }
            });
        }
        
        // 显示搜索结果
        function showSearchResults(locations, resultsDiv, input) {
            resultsDiv.innerHTML = '';
            
            if (!locations || locations.length === 0) {
                resultsDiv.innerHTML = '';
                
                // 显示无结果提示
                const noResultItem = document.createElement('div');
                noResultItem.className = 'search-result-item';
                noResultItem.style.color = '#666';
                noResultItem.style.fontStyle = 'italic';
                noResultItem.textContent = '未找到相关门店';
                resultsDiv.appendChild(noResultItem);
                
                // 添加"尝试腾讯地图"按钮
                const tryTencentButton = document.createElement('div');
                tryTencentButton.className = 'search-result-item try-tencent-button';
                tryTencentButton.style.cssText = `
                    background: linear-gradient(135deg, #4285f4, #34a853);
                    color: white;
                    text-align: center;
                    font-weight: bold;
                    cursor: pointer;
                    border-radius: 6px;
                    margin-top: 8px;
                    padding: 12px;
                    transition: all 0.3s ease;
                `;
                tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                
                tryTencentButton.addEventListener('click', async function() {
                    const query = input.value.trim();
                    if (!query) return;
                    
                    try {
                        // 改变按钮状态
                        tryTencentButton.innerHTML = '🔄 搜索中...';
                        tryTencentButton.style.opacity = '0.7';
                        
                        // 强制调用腾讯地图搜索
                        const response = await fetch('/api/search_location', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                keyword: query,
                                force_tencent: true  // 强制使用腾讯地图
                            })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            console.log('腾讯地图搜索结果:', data);
                            
                            if (data.locations && data.locations.length > 0) {
                                showSearchResults(data.locations, resultsDiv, input);
                            } else {
                                tryTencentButton.innerHTML = '❌ 腾讯地图也未找到结果';
                                setTimeout(() => {
                                    tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                                    tryTencentButton.style.opacity = '1';
                                }, 2000);
                            }
                        }
                    } catch (error) {
                        console.error('腾讯地图搜索失败:', error);
                        tryTencentButton.innerHTML = '❌ 搜索失败，请重试';
                        setTimeout(() => {
                            tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                            tryTencentButton.style.opacity = '1';
                        }, 2000);
                    }
                });
                
                // 鼠标悬停效果
                tryTencentButton.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = '0 4px 12px rgba(66, 133, 244, 0.3)';
                });
                
                tryTencentButton.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = 'none';
                });
                
                resultsDiv.appendChild(tryTencentButton);
                return;
            }
            
            // 按相关性分数排序（从高到低）
            locations.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
            
            // 显示最多12个高匹配度结果
            locations.slice(0, 12).forEach((location, index) => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                
                if (location.is_recommendation) {
                    item.classList.add('recommendation-item');
                }
                
                const displayText = location.name || '未知门店';
                const recommendationLabel = location.is_recommendation ? '<span class="recommendation-label">推荐</span>' : '';
                
                // 处理address字段可能是数组的情况
                let address = location.address;
                if (Array.isArray(address)) {
                    address = address.length > 0 ? address.join(', ') : '';
                } else if (typeof address !== 'string') {
                    address = '';
                }
                
                let addressText = '';
                if (address && address.trim()) {
                    addressText = address;
                } else if (location.pname || location.cityname || location.adname) {
                    addressText = [location.pname, location.cityname, location.adname].filter(x => x).join('');
                } else {
                    addressText = '地址信息不完整';
                }
                
                // 添加数据源标识和匹配度
                const sourceText = location.source === 'tencent' ? 
                    '<span class="data-source tencent">腾讯</span>' : 
                    '<span class="data-source amap">高德</span>';
                
                // 匹配度显示
                const relevanceScore = location.relevance_score || 0;
                let matchLevel = '';
                let matchClass = '';
                if (relevanceScore >= 150) {
                    matchLevel = '精确匹配';
                    matchClass = 'match-excellent';
                } else if (relevanceScore >= 100) {
                    matchLevel = '高度匹配';
                    matchClass = 'match-high';
                } else if (relevanceScore >= 60) {
                    matchLevel = '中度匹配';
                    matchClass = 'match-medium';
                } else {
                    matchLevel = '低度匹配';
                    matchClass = 'match-low';
                }
                
                const matchText = '<span class="match-level ' + matchClass + '">' + matchLevel + '</span>';
                
                const recommendationReason = location.recommendation_reason ? 
                    '<div class="recommendation-reason">' + location.recommendation_reason + '</div>' : '';
                
                item.innerHTML = 
                    '<div class="store-name">' + displayText + recommendationLabel + '</div>' +
                    '<div class="store-address">' + addressText + '</div>' +
                    '<div class="source-info">' + sourceText + ' ' + matchText + '</div>' +
                    recommendationReason;
                
                item.addEventListener('click', function() {
                    input.value = displayText;
                    input.setAttribute('data-location', location.location || '');
                    input.setAttribute('data-full-address', addressText);
                    resultsDiv.innerHTML = '';
                });
                
                resultsDiv.appendChild(item);
            });
            
            // 添加"尝试腾讯地图"按钮
            const tryTencentButton = document.createElement('div');
            tryTencentButton.className = 'search-result-item try-tencent-button';
            tryTencentButton.style.cssText = `
                background: linear-gradient(135deg, #4285f4, #34a853);
                color: white;
                text-align: center;
                font-weight: bold;
                cursor: pointer;
                border-radius: 6px;
                margin-top: 8px;
                padding: 12px;
                transition: all 0.3s ease;
            `;
            tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
            
            tryTencentButton.addEventListener('click', async function() {
                const query = input.value.trim();
                if (!query) return;
                
                try {
                    // 改变按钮状态
                    tryTencentButton.innerHTML = '🔄 搜索中...';
                    tryTencentButton.style.opacity = '0.7';
                    
                    // 强制调用腾讯地图搜索
                    const response = await fetch('/api/search_location', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            keyword: query,
                            force_tencent: true  // 强制使用腾讯地图
                        })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log('腾讯地图搜索结果:', data);
                        
                        if (data.locations && data.locations.length > 0) {
                            showSearchResults(data.locations, resultsDiv, input);
                        } else {
                            tryTencentButton.innerHTML = '❌ 腾讯地图也未找到结果';
                            setTimeout(() => {
                                tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                                tryTencentButton.style.opacity = '1';
                            }, 2000);
                        }
                    }
                } catch (error) {
                    console.error('腾讯地图搜索失败:', error);
                    tryTencentButton.innerHTML = '❌ 搜索失败，请重试';
                    setTimeout(() => {
                        tryTencentButton.innerHTML = '🔍 尝试腾讯地图搜索';
                        tryTencentButton.style.opacity = '1';
                    }, 2000);
                }
            });
            
            // 鼠标悬停效果
            tryTencentButton.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 12px rgba(66, 133, 244, 0.3)';
            });
            
            tryTencentButton.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            });
            
            resultsDiv.appendChild(tryTencentButton);
        }
        
        // 表单提交
        document.getElementById('timesheetForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            // 获取坐标信息
            data.start_location = document.getElementById('startStore').getAttribute('data-location') || '';
            data.end_location = document.getElementById('endStore').getAttribute('data-location') || '';
            
            try {
                const response = await fetch('/api/my_timesheet', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('工时记录保存成功！');
                    resetForm();
                    toggleForm(); // 隐藏表单
                    loadRecords(); // 重新加载记录
                } else {
                    alert('保存失败：' + result.message);
                }
            } catch (error) {
                alert('网络错误，请稍后重试');
            }
        });
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadRecords();
            setupStoreSearch('startStore', 'startStoreResults');
            setupStoreSearch('endStore', 'endStoreResults');
            
            // 设置默认日期
            document.getElementById('workDate').value = new Date().toISOString().split('T')[0];
            
            
            // 监听出差天数和实际巡店天数的关系验证
            function validateVisitDays() {
                const businessTripDays = parseInt(document.getElementById('businessTripDays').value) || 0;
                const actualVisitDays = parseInt(document.getElementById('actualVisitDays').value) || 0;
                
                if (actualVisitDays > businessTripDays) {
                    document.getElementById('actualVisitDays').setCustomValidity('实际巡店天数不能大于出差天数');
                } else {
                    document.getElementById('actualVisitDays').setCustomValidity('');
                }
            }
            
            document.getElementById('businessTripDays').addEventListener('input', validateVisitDays);
            document.getElementById('actualVisitDays').addEventListener('input', validateVisitDays);
        });
    </script>
</body>
</html>
'''

# 计算搜索结果相关性分数
def calculate_relevance_score(keyword, location):
    """计算搜索结果与关键词的相关性分数"""
    score = 0.0
    keyword_lower = keyword.lower()
    
    # 安全获取name和address，确保是字符串
    name = location.get('name', '')
    if isinstance(name, list):
        name = ' '.join(str(x) for x in name if x)
    name_lower = str(name).lower()
    
    address = location.get('address', '')
    if isinstance(address, list):
        address = ' '.join(str(x) for x in address if x)
        # 更新location对象中的地址，确保前端获得字符串而不是数组
        location['address'] = address
    address_lower = str(address).lower()
    
    # 1. 名称完全匹配（最高分）
    if keyword_lower == name_lower:
        score += 100.0
        logger.info(f"完全匹配: {location['name']}")
    
    # 2. 名称包含关键词
    elif keyword_lower in name_lower:
        score += 80.0
        logger.info(f"名称包含关键词: {location['name']}")
    
    # 3. 关键词包含在名称中的部分匹配
    else:
        # 拆分关键词，检查部分匹配
        keyword_parts = ['古茗', '铅山', '九狮', '辛弃疾', '广场店']
        for part in keyword_parts:
            if part in keyword_lower and part in name_lower:
                score += 30.0
                logger.info(f"部分匹配 '{part}': {location['name']}")
    
    # 特殊处理：九狮广场应该匹配九狮商业广场
    if '九狮广场' in keyword_lower and '九狮商业广场' in name_lower:
        score += 90.0  # 高分奖励
        logger.info(f"九狮广场匹配九狮商业广场: {location['name']}")
    elif '九狮广场' in keyword_lower and '九狮' in name_lower and '广场' in name_lower:
        score += 70.0  # 中等分奖励
        logger.info(f"九狮广场部分匹配: {location['name']}")
    
    # 4. 地址相关性匹配 - 通用地址匹配逻辑
    # 检查关键词是否包含地名，如果包含则进行地址匹配
    keyword_parts = keyword_lower.split()
    for part in keyword_parts:
        if len(part) >= 2:  # 只考虑长度>=2的关键词部分
            if part in address_lower:
                score += 15.0
                logger.info(f"地址匹配关键词'{part}': {location['name']}")
    
    # 5. 特殊关键词匹配（重要地标或特色词，给予高分）
    # 动态识别关键词中的重要部分
    special_keywords = []
    for part in keyword_parts:
        if len(part) >= 2:
            special_keywords.append(part)
    
    for special_kw in special_keywords:
        if special_kw in (name_lower + address_lower):
            score += 40.0
            logger.info(f"特殊关键词精确匹配'{special_kw}': {location['name']}")
        elif any(related in (name_lower + address_lower) for related in ['广场', '商场', '中心', '大厦', '店']):
            score += 15.0
            logger.info(f"相关词匹配: {location['name']}")
    
    # 6. 品牌匹配优先
    brand_keywords = ['古茗', '星巴克', '麦当劳', '肯德基', '必胜客']  # 可扩展的品牌列表
    for brand in brand_keywords:
        if brand in keyword_lower and brand in name_lower:
            score += 25.0
            logger.info(f"品牌匹配'{brand}': {location['name']}")
    
    # 7. 连锁店惩罚机制（如果搜索特定品牌但结果不是该品牌）
    if any(brand in keyword_lower for brand in brand_keywords):
        search_brand = next((brand for brand in brand_keywords if brand in keyword_lower), None)
        if search_brand and search_brand not in name_lower:
            score -= 20.0  # 轻度惩罚，不要过于严格
            logger.info(f"非目标品牌轻度惩罚: {location['name']}")
    
    logger.info(f"相关性分数计算完成 {location['name']}: {score:.2f}")
    return max(0.0, score)  # 确保分数不为负

# 腾讯地图搜索缓存和使用统计
tencent_search_cache = {}  # 清空缓存以便测试
tencent_daily_usage = {'date': '', 'count': 0}

def get_tencent_usage_today():
    """获取今日腾讯地图API使用次数"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    if tencent_daily_usage['date'] != today:
        # 新的一天，重置计数
        tencent_daily_usage['date'] = today
        tencent_daily_usage['count'] = 0
    return tencent_daily_usage['count']

def increment_tencent_usage():
    """增加腾讯地图API使用计数"""
    tencent_daily_usage['count'] += 1
    logger.info(f"腾讯地图API今日使用次数: {tencent_daily_usage['count']}/200")

def should_use_tencent_api(keyword, amap_results):
    """智能判断是否需要使用腾讯地图API补充搜索"""
    # 检查今日使用次数
    usage_today = get_tencent_usage_today()
    if usage_today >= 200:
        logger.warning("腾讯地图API今日使用次数已达上限(200次)")
        return False
    
    # 检查缓存
    cache_key = keyword.lower().strip()
    if cache_key in tencent_search_cache:
        logger.info(f"使用腾讯地图搜索缓存: {keyword}")
        return False
    
    # 智能判断：高德结果质量评估
    if not amap_results:
        logger.info("高德地图无结果，使用腾讯地图补充")
        return True
    
    # 检查高德结果的相关性分数
    high_relevance_count = sum(1 for loc in amap_results if loc.get('relevance_score', 0) >= 100)
    if high_relevance_count >= 3:
        logger.info(f"高德地图已找到{high_relevance_count}个高相关性结果，跳过腾讯地图")
        return False
    
    # 检查是否有精确匹配
    exact_matches = sum(1 for loc in amap_results if keyword.lower() in loc.get('name', '').lower())
    if exact_matches >= 2:
        logger.info(f"高德地图已有{exact_matches}个精确匹配，跳过腾讯地图")
        return False
    
    # 节约策略：保留30%的配额用于下午和晚上使用
    from datetime import datetime
    current_hour = datetime.now().hour
    if current_hour < 18:  # 上午到下午6点
        if usage_today >= 140:  # 使用了70%配额
            logger.info("节约模式：保留配额给晚间使用")
            return False
    
    # 检查是否有明显的品牌关键词，如果没有品牌关键词可能是地标搜索，优先使用腾讯
    brand_keywords = ['古茗', '赵一鸣', '蜜雪冰城', '正新鸡排', '华莱士', '肯德基', '麦当劳']
    has_brand = any(brand in keyword for brand in brand_keywords)
    
    if not has_brand:
        logger.info("地标搜索，优先使用腾讯地图补充")
        return True
    
    # 如果高德结果少于5个，使用腾讯补充
    if len(amap_results) < 5:
        logger.info("高德结果较少，使用腾讯地图补充搜索")
        return True
    
    logger.info("高德结果充足，跳过腾讯地图搜索")
    return False

# 腾讯地图API搜索函数
def search_tencent_location(keyword, region=None):
    """使用腾讯地图API搜索地点（带缓存和限制）"""
    # 创建缓存key，如果有region则包含region
    cache_key = f"{keyword.lower()}_{region or 'nationwide'}".strip()
    
    # 检查缓存
    if cache_key in tencent_search_cache:
        logger.info(f"返回腾讯地图缓存结果: {keyword}")
        return tencent_search_cache[cache_key]
    
    try:
        # 增加使用计数
        increment_tencent_usage()
        url = 'https://apis.map.qq.com/ws/place/v1/search'
        params = {
            'keyword': keyword,
            'page_size': 20,
            'page_index': 1,
            'key': TENCENT_API_KEY,
            'boundary': f'region({region},0)' if region else 'nearby(39.915,116.404,50000)'  # 腾讯API要求boundary参数，全国搜索改为附近搜索
        }
        
        logger.info(f"腾讯地图API请求: {url} (今日第{tencent_daily_usage['count']}次)")
        response = safe_request(url, params=params)
        
        if response and response.status_code == 200:
            data = response.json()
            logger.info(f"腾讯地图API响应状态: {data.get('status')}")
            
            if data.get('status') == 0:  # 腾讯API成功状态码是0
                results = data.get('data', [])
                logger.info(f"腾讯地图找到 {len(results)} 个结果")
                
                locations = []
                for poi in results:
                    # 转换腾讯地图数据格式为统一格式
                    location = {
                        'name': poi.get('title', ''),
                        'address': poi.get('address', ''),
                        'location': f"{poi.get('location', {}).get('lat', '')},{poi.get('location', {}).get('lng', '')}",
                        'tel': poi.get('tel', ''),
                        'source': 'tencent',  # 标记数据源
                        'pname': poi.get('ad_info', {}).get('province', ''),
                        'cityname': poi.get('ad_info', {}).get('city', ''),
                        'adname': poi.get('ad_info', {}).get('district', ''),
                    }
                    
                    # 计算相关性分数
                    relevance_score = calculate_relevance_score(keyword, location)
                    location['relevance_score'] = relevance_score
                    
                    locations.append(location)
                    logger.info(f"腾讯地图结果: 名称='{location['name']}', 地址='{location['address']}', 相关性={relevance_score:.2f}")
                
                # 缓存结果（限制缓存大小，避免内存占用过多）
                if len(tencent_search_cache) < 100:
                    tencent_search_cache[cache_key] = locations
                
                return locations
            else:
                logger.warning(f"腾讯地图API返回错误: {data.get('message', '未知错误')}")
                return []
        else:
            logger.error(f"腾讯地图API请求失败: {response.status_code if response else '无响应'}")
            return []
        
    except Exception as e:
        logger.error(f"腾讯地图搜索异常: {str(e)}")
        return []

# 高德地图API函数
def search_location(keyword, city=None):
    """搜索地点"""
    if not keyword or len(keyword.strip()) < 2:
        return {'success': False, 'message': '搜索关键词太短'}
    
    try:
        url = 'https://restapi.amap.com/v3/place/text'
        
        # 智能搜索策略 - 优先使用高德地图，腾讯地图作为备选
        search_strategies = []
        
        # 策略1：优先使用高德地图API（主要搜索方式）
        search_strategies.append({
            'keywords': keyword.strip(),
            'types': '',
            'city': city if city else '',  # 使用传递的城市参数
            'children': 1,
            'offset': 15,  # 减少结果数量，提高效率
            'page': 1,
            'extensions': 'all',
            'citylimit': 'true' if city else 'false',  # 如果指定城市则限制在该城市
            'datatype': 'all'
        })
        
        # 策略2：如果关键词包含品牌名，进行品牌搜索
        brand_keywords = ['古茗', '星巴克', '麦当劳', '肯德基', '必胜客', '喜茶', '奈雪的茶']
        found_brand = None
        for brand in brand_keywords:
            if brand in keyword:
                found_brand = brand
                break
        
        if found_brand:
            # 只有在包含品牌时才添加品牌特定搜索
            search_strategies.append({
                'keywords': found_brand,
                'types': '050700',  # 餐饮服务类型
                'city': city if city else '',
                'children': 1,
                'offset': 10,
                'page': 1,
                'extensions': 'all',
                'citylimit': 'true' if city else 'false'
            })
        
        # 策略3：如果关键词较长，尝试拆分关键词搜索（限制条件：避免过度拆分）
        if len(keyword.strip()) > 4 and ' ' not in keyword:
            # 只在关键词较长且没有空格的情况下才进行拆分搜索
            keyword_parts = []
            if found_brand:
                # 移除品牌名，搜索剩余部分
                remaining = keyword.replace(found_brand, '').strip()
                if len(remaining) >= 2:
                    keyword_parts.append(remaining)
            
            # 添加拆分搜索（限制数量）
            for part in keyword_parts[:1]:  # 只取第一个拆分结果，避免搜索过多
                search_strategies.append({
                    'keywords': part,
                    'types': '',
                    'city': city if city else '',
                    'children': 1,
                    'offset': 10,
                    'page': 1,
                    'extensions': 'all',
                    'citylimit': 'true' if city else 'false'
                })
        
        logger.info(f"搜索关键词: {keyword}")
        
        all_locations = []  # 收集所有策略的结果
        
        for i, params in enumerate(search_strategies):
            params['key'] = AMAP_API_KEY
            logger.info(f"尝试搜索策略 {i+1}: {params}")
            
            try:
                response = safe_request(url, params=params, timeout=10)
                data = response.json()
                
                logger.info(f"策略 {i+1} API响应状态: {data.get('status')}")
                logger.info(f"策略 {i+1} API完整响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                
                if data['status'] == '1' and data.get('pois'):
                    strategy_locations = []
                    for poi in data['pois'][:20]:  # 先获取更多结果用于过滤
                        # 获取城市信息
                        cityname = poi.get('cityname', '')
                        adname = poi.get('adname', '')  # 区县名
                        pname = poi.get('pname', '')    # 省份名
                        
                        # 构建完整地址显示
                        full_address = f"{pname}{cityname}{adname} {poi['address']}" if pname else poi['address']
                        
                        location_obj = {
                            'name': poi['name'],
                            'address': poi['address'],
                            'full_address': full_address,
                            'location': poi['location'],
                            'cityname': cityname,
                            'adname': adname,
                            'pname': pname
                        }
                        
                        # 计算相关性分数
                        relevance_score = calculate_relevance_score(keyword, location_obj)
                        location_obj['relevance_score'] = relevance_score
                        
                        strategy_locations.append(location_obj)
                        
                        # 详细日志记录每个搜索结果
                        logger.info(f"策略{i+1} 结果 {len(strategy_locations)}: 名称='{poi['name']}', 地址='{poi['address']}', 相关性={relevance_score:.2f}")
                    
                    # 将这个策略的结果添加到总结果中
                    all_locations.extend(strategy_locations)
                    logger.info(f"策略 {i+1} 成功找到 {len(strategy_locations)} 个结果")
                    
                    # 如果找到了高分结果（相关性>100），优先返回
                    high_score_results = [loc for loc in strategy_locations if loc['relevance_score'] > 100]
                    if high_score_results:
                        logger.info(f"策略 {i+1} 找到高相关性结果，提前返回")
                        high_score_results.sort(key=lambda x: x['relevance_score'], reverse=True)
                        return {'success': True, 'locations': high_score_results[:8]}
                else:
                    logger.info(f"策略 {i+1} 未找到结果")
            except Exception as e:
                logger.error(f"策略 {i+1} 执行失败: {e}")
                continue
        
        # 智能决策是否使用腾讯地图搜索
        if should_use_tencent_api(keyword, all_locations):
            logger.info("开始腾讯地图搜索...")
            try:
                tencent_results = search_tencent_location(keyword)
                if tencent_results:
                    all_locations.extend(tencent_results)
                    logger.info(f"腾讯地图搜索成功找到 {len(tencent_results)} 个结果")
                else:
                    logger.info("腾讯地图搜索未找到结果")
            except Exception as e:
                logger.error(f"腾讯地图搜索失败: {e}")
        else:
            logger.info("智能策略：跳过腾讯地图搜索，节约API调用")
        
        # 合并所有策略的结果（包括高德和腾讯），去重并排序
        if all_locations:
            # 去重（基于名称和位置）
            unique_locations = {}
            for loc in all_locations:
                key = f"{loc['name']}_{loc['location']}"
                if key not in unique_locations or loc['relevance_score'] > unique_locations[key]['relevance_score']:
                    unique_locations[key] = loc
            
            # 按相关性分数排序
            final_locations = list(unique_locations.values())
            final_locations.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # 检查搜索结果质量，如果不佳则尝试智能推荐
            if not final_locations or (final_locations and final_locations[0]['relevance_score'] < 60):
                logger.info(f"搜索结果质量不高（最高分: {final_locations[0]['relevance_score'] if final_locations else 0}），尝试智能推荐...")
                recommendations = get_smart_recommendations(keyword)
                if recommendations:
                    # 在结果前面加入推荐，并标记
                    final_locations = recommendations + final_locations
                    logger.info(f"添加了 {len(recommendations)} 个智能推荐结果")
            
            filtered_locations = final_locations[:8]  # 只取前8个最相关的结果
            
            # 统计数据源分布
            amap_count = sum(1 for loc in filtered_locations if loc.get('source') != 'tencent')
            tencent_count = sum(1 for loc in filtered_locations if loc.get('source') == 'tencent')
            
            logger.info(f"合并多数据源结果: 总共{len(all_locations)}个，去重后{len(final_locations)}个，最终返回{len(filtered_locations)}个")
            logger.info(f"数据源分布: 高德{amap_count}个，腾讯{tencent_count}个")
            return {'success': True, 'locations': filtered_locations}
        
        # 所有策略都失败，尝试智能推荐作为最后手段
        logger.warning("所有搜索策略都未找到结果，尝试最后的智能推荐...")
        recommendations = get_smart_recommendations(keyword)
        if recommendations:
            logger.info(f"最后推荐找到 {len(recommendations)} 个结果")
            return {'success': True, 'locations': recommendations[:8]}
        
        return {'success': False, 'message': f'未找到"{keyword}"相关地点，请尝试其他关键词'}
        
    except Exception as e:
        logger.error(f"搜索地点失败: {e}")
        return {'success': False, 'message': '搜索服务暂时不可用'}

def get_smart_recommendations(original_keyword):
    """获取智能推荐结果"""
    try:
        logger.info(f"为关键词 '{original_keyword}' 获取智能推荐...")
        
        # 智能推荐策略1：基于品牌的全国推荐
        brand_keywords = ['古茗', '星巴克', '麦当劳', '肯德基', '必胜客', '喜茶', '奈雪的茶']
        found_brand = None
        for brand in brand_keywords:
            if brand in original_keyword.lower():
                found_brand = brand
                break
        
        if found_brand:
            try:
                url = 'https://restapi.amap.com/v3/place/text'
                params = {
                    'key': AMAP_API_KEY,
                    'keywords': found_brand,
                    'types': '050700',  # 餐饮相关
                    'children': 1,
                    'offset': 8,  # 减少推荐数量，提高质量
                    'page': 1,
                    'extensions': 'all',
                    'citylimit': 'false'  # 全国范围搜索
                }
                
                response = safe_request(url, params=params, timeout=10)
                data = response.json()
                
                if data['status'] == '1' and data.get('pois'):
                    recommendations = []
                    for poi in data['pois'][:5]:  # 推荐前5个
                        location = {
                            'name': poi['name'],
                            'address': poi['address'],
                            'location': poi['location'],
                            'cityname': poi.get('cityname', ''),
                            'adname': poi.get('adname', ''),
                            'pname': poi.get('pname', ''),
                            'relevance_score': 75.0,  # 给推荐结果中等分数
                            'is_recommendation': True,
                            'recommendation_reason': f'未找到"{original_keyword}"，为您推荐{found_brand}门店'
                        }
                        recommendations.append(location)
                        logger.info(f"品牌推荐: {poi['name']} - {poi['address']}")
                    
                    if recommendations:
                        return recommendations
                        
            except Exception as e:
                logger.error(f"推荐{found_brand}门店失败: {e}")
        
        # 智能推荐策略2：基于关键词的模糊搜索推荐
        if len(original_keyword.strip()) >= 2:
            try:
                # 提取关键词中的有意义部分进行推荐
                keywords_to_try = []
                
                # 如果包含常见地标词汇，尝试推荐相关地点
                landmark_words = ['广场', '商场', '中心', '大厦', '公园', '医院', '学校', '车站']
                for word in landmark_words:
                    if word in original_keyword:
                        keywords_to_try.append(word)
                        break
                
                # 如果没有地标词汇，尝试用整个关键词的模糊搜索
                if not keywords_to_try:
                    # 简化关键词，移除可能的修饰词
                    simplified = original_keyword.replace('店', '').replace('门店', '').strip()
                    if len(simplified) >= 2:
                        keywords_to_try.append(simplified)
                
                for keyword_to_search in keywords_to_try[:1]:  # 只尝试第一个，避免过多请求
                    url = 'https://restapi.amap.com/v3/place/text'
                    params = {
                        'key': AMAP_API_KEY,
                        'keywords': keyword_to_search,
                        'children': 1,
                        'offset': 6,
                        'page': 1,
                        'extensions': 'all',
                        'citylimit': 'false'
                    }
                    
                    response = safe_request(url, params=params, timeout=10)
                    data = response.json()
                    
                    if data['status'] == '1' and data.get('pois'):
                        recommendations = []
                        for poi in data['pois'][:3]:  # 推荐前3个
                            location = {
                                'name': poi['name'],
                                'address': poi['address'],
                                'location': poi['location'],
                                'cityname': poi.get('cityname', ''),
                                'adname': poi.get('adname', ''),
                                'pname': poi.get('pname', ''),
                                'relevance_score': 60.0,
                                'is_recommendation': True,
                                'recommendation_reason': f'为您推荐与"{keyword_to_search}"相关的地点'
                            }
                            recommendations.append(location)
                            logger.info(f"关键词推荐: {poi['name']} - {poi['address']}")
                        
                        if recommendations:
                            return recommendations
                            
            except Exception as e:
                logger.error(f"关键词推荐失败: {e}")
        
        logger.info("未能生成智能推荐")
        return []
        
    except Exception as e:
        logger.error(f"获取智能推荐失败: {e}")
        return []

def calculate_route(start_store, end_store, transport_mode='driving', route_strategy='10', start_location=None, end_location=None):
    """计算路线"""
    try:
        # 输入验证
        if not start_store or not end_store:
            return {'success': False, 'message': '起点和终点不能为空'}
        
        if not start_store.strip() or not end_store.strip():
            return {'success': False, 'message': '起点和终点不能为空'}
        
        # 坐标格式标准化函数
        def normalize_coordinate(coord_str):
            """将坐标标准化为 经度,纬度 格式"""
            if not coord_str or ',' not in coord_str:
                return coord_str
            
            coords = coord_str.strip().split(',')
            if len(coords) != 2:
                return coord_str
            
            try:
                val1, val2 = float(coords[0]), float(coords[1])
                
                # 判断哪个是经度哪个是纬度
                # 中国境内：经度范围大约73-135，纬度范围大约18-54
                # 如果第一个值在纬度范围内且第二个值在经度范围内，则交换
                if 18 <= val1 <= 54 and 73 <= val2 <= 135:
                    # 第一个是纬度，第二个是经度，需要交换
                    logger.info(f"坐标格式修正: {coord_str} -> {val2},{val1}")
                    return f"{val2},{val1}"
                else:
                    # 已经是正确格式
                    return coord_str
            except ValueError:
                return coord_str
        
        # 优先使用传递的坐标，如果没有则搜索门店坐标
        if start_location and end_location:
            logger.info("使用前端传递的坐标")
            # 标准化坐标格式
            start_location = normalize_coordinate(start_location)
            end_location = normalize_coordinate(end_location)
        else:
            logger.info("搜索门店坐标")
            # 先搜索起点和终点的坐标
            start_result = search_location(start_store.strip())
            end_result = search_location(end_store.strip())
            
            if not start_result['success'] or not end_result['success']:
                return {'success': False, 'message': '无法找到门店位置'}
            
            if not start_result.get('locations') or not end_result.get('locations'):
                return {'success': False, 'message': '无法找到门店位置'}
            
            start_location = normalize_coordinate(start_result['locations'][0]['location'])
            end_location = normalize_coordinate(end_result['locations'][0]['location'])
        
        if transport_mode in ['driving', 'taxi']:
            # 使用高德路径规划API - 驾车路线（打车也使用驾车路线）
            url = 'https://restapi.amap.com/v3/direction/driving'
            params = {
                'key': AMAP_API_KEY,
                'origin': start_location,
                'destination': end_location,
                'strategy': route_strategy,  # 使用用户选择的路线策略
                'extensions': 'all',  # 返回详细信息
                'waypoints': '',  # 途经点
                'avoidpolygons': '',  # 避让区域
                'avoidroad': '',  # 避让道路
                'number': '3',  # 返回多条路径供选择
                'multiexport': '1'  # 启用多路径导出
            }
            
            response = safe_request(url, params=params, timeout=15)
            data = response.json()
            
            logger.info(f"起点: {start_store} -> {start_location}")
            logger.info(f"终点: {end_store} -> {end_location}")
            logger.info(f"路线策略: {route_strategy}")
            logger.info(f"交通方式: {transport_mode}")
            
            if data['status'] == '1' and data.get('route', {}).get('paths'):
                paths = data['route']['paths']
                
                # 打印所有路线选项
                logger.info(f"找到 {len(paths)} 条路线:")
                for i, p in enumerate(paths):
                    dist = float(p['distance']) / 1000
                    dur = float(p['duration']) / 3600
                    logger.info(f"  路线{i+1}: {dist:.3f}km, {dur*60:.1f}分钟")
                
                # 根据策略选择最佳路径
                if route_strategy == '2':  # 最短路线（时间及里程最短）- 优先考虑时间
                    best_path = min(paths, key=lambda p: float(p['duration']))
                    logger.info("选择最短时间路线（时间及里程最短）")
                elif route_strategy == '1':  # 最快路线
                    best_path = min(paths, key=lambda p: float(p['duration']))
                    logger.info("选择最快时间路线")
                else:  # 默认选择第一条（推荐路线）
                    best_path = paths[0]
                    logger.info("选择推荐路线")
                
                distance = float(best_path['distance']) / 1000  # 转换为公里
                duration = float(best_path['duration']) / 3600   # 转换为小时
                
                # 根据交通方式添加额外时间
                if transport_mode == 'driving':
                    # 驾车：添加0.16小时停车时长
                    duration += 0.16
                    logger.info(f"驾车模式：添加0.16小时停车时长")
                elif transport_mode == 'taxi':
                    # 打车：使用驾车算法（包括0.16小时停车）+ 0.083小时等待时长
                    duration += 0.16  # 先添加驾车的停车时长
                    duration += 0.083  # 再添加打车的等待时长
                    logger.info(f"打车模式：添加0.16小时停车时长 + 0.083小时等待时长 = 0.243小时")
                
                # 获取路线详细信息
                traffic_lights = best_path.get('traffic_lights', 0)  # 红绿灯数量
                tolls = float(best_path.get('tolls', 0))  # 过路费
                toll_distance = float(best_path.get('toll_distance', 0)) / 1000  # 收费路段距离
                
                logger.info(f"最终选择: {distance:.3f}km, {duration*60:.1f}分钟")
                logger.info(f"红绿灯数量: {traffic_lights}, 过路费: {tolls}元, 收费路段: {toll_distance}km")
                
                return {
                    'success': True,
                    'distance': distance,  # 返回单程距离
                    'duration': duration,  # 返回单程时间（已包含额外时间）
                    'traffic_lights': traffic_lights,
                    'tolls': tolls,  # 单程过路费
                    'toll_distance': toll_distance
                }
            else:
                logger.error(f"高德API错误: {data}")
                return {'success': False, 'message': f"路线规划失败: {data.get('info', '未知错误')}"}
        else:
            # 公共交通使用直线距离估算
            start_coords = start_location.split(',')
            end_coords = end_location.split(',')
            
            distance = haversine_distance(
                float(start_coords[1]), float(start_coords[0]),
                float(end_coords[1]), float(end_coords[0])
            )
            
            # 根据交通方式估算时间（单程）
            if transport_mode == 'walking':
                # 步行：使用高德步行路径规划API
                duration = calculate_walking_time(start_location, end_location)
                if duration <= 0:
                    # 如果API失败，使用默认步行速度估算
                    duration = distance / 5  # 平均步行速度5km/h
                logger.info(f"步行模式：{distance:.3f}km, {duration*60:.1f}分钟")
            elif transport_mode == 'bus':
                duration = distance / 60  # 大巴平均60km/h
            elif transport_mode == 'train':
                duration = distance / 200  # 高铁平均200km/h
            elif transport_mode == 'airplane':
                duration = distance / 600  # 飞机平均600km/h
            else:
                duration = distance / 60
            
            return {
                'success': True,
                'distance': distance,  # 单程距离
                'duration': duration   # 单程时间
            }
            
    except Exception as e:
        logger.error(f"路线计算失败: {e}")
        return {'success': False, 'message': '路线计算服务暂时不可用'}

def haversine_distance(lat1, lon1, lat2, lon2):
    """计算两点间的直线距离（公里）"""
    R = 6371  # 地球半径（公里）
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def calculate_walking_time(start_location, end_location):
    """计算步行时长（小时）"""
    try:
        # 使用高德步行路径规划API
        url = 'https://restapi.amap.com/v3/direction/walking'
        params = {
            'key': AMAP_API_KEY,
            'origin': start_location,
            'destination': end_location,
        }
        
        response = safe_request(url, params=params, timeout=10)
        data = response.json()
        
        logger.info(f"步行路线API响应状态: {data.get('status')}")
        
        if data['status'] == '1' and data.get('route', {}).get('paths'):
            # 获取步行时长（秒转小时）
            walking_duration = float(data['route']['paths'][0]['duration']) / 3600
            walking_distance = float(data['route']['paths'][0]['distance']) / 1000
            
            logger.info(f"步行路线: {walking_distance:.3f}km, {walking_duration*60:.1f}分钟")
            return walking_duration
        else:
            logger.warning(f"步行路线API错误: {data}")
            # 如果API失败，使用默认步行速度估算（5km/h）
            start_coords = start_location.split(',')
            end_coords = end_location.split(',')
            
            distance = haversine_distance(
                float(start_coords[1]), float(start_coords[0]),
                float(end_coords[1]), float(end_coords[0])
            )
            
            walking_duration = distance / 5  # 平均步行速度5km/h
            logger.info(f"使用默认步行速度估算: {distance:.3f}km, {walking_duration*60:.1f}分钟")
            return walking_duration
            
    except Exception as e:
        logger.error(f"步行路线计算失败: {e}")
        # 发生错误时返回默认估算值
        try:
            start_coords = start_location.split(',')
            end_coords = end_location.split(',')
            
            distance = haversine_distance(
                float(start_coords[1]), float(start_coords[0]),
                float(end_coords[1]), float(end_coords[0])
            )
            
            walking_duration = distance / 5  # 平均步行速度5km/h
            logger.info(f"异常情况下使用步行默认速度: {distance:.3f}km, {walking_duration*60:.1f}分钟")
            return walking_duration
        except:
            logger.error("无法计算步行时长，返回0")
            return 0

# 路由
@app.route('/')
def index():
    """主页，重定向到登录页"""
    if 'user_id' in session:
        user_role = session.get('role')
        if user_role == 'supervisor':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/health')
def health():
    """健康检查端点"""
    return {'status': 'ok', 'message': 'GuMing Timesheet System is running'}

# 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'GET':
        return render_template_string(register_template)
    
    logger.info("收到注册请求")
    
    try:
        data = request.get_json() if request.is_json else request.form
        password = data.get('password', '').strip()
        name = data.get('name', '').strip()
        department = data.get('department', '').strip()
        phone = data.get('phone', '').strip()
        
        # 使用真实姓名作为用户名
        username = name
        
        logger.info(f"注册尝试: 用户名={username}, 姓名={name}, 组别={department}, 手机={phone}")
        
        # 验证必填字段
        if not all([username, password, name, department, phone]):
            return jsonify({'success': False, 'message': '所有字段都必须填写'}), 400
        
        # 验证真实姓名长度（用作用户名）
        if not (2 <= len(name) <= 20):
            return jsonify({'success': False, 'message': '姓名长度应在2-20个字符之间'}), 400
        
        # 验证密码强度
        if len(password) < 6:
            return jsonify({'success': False, 'message': '密码长度至少6位'}), 400
        
        # 验证手机号格式
        if not (phone.isdigit() and len(phone) == 11):
            return jsonify({'success': False, 'message': '请输入有效的11位手机号'}), 400
        
        with get_db_connection() as db:
            # 检查姓名是否已被注册
            existing_user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            if existing_user:
                return jsonify({'success': False, 'message': '该姓名已被注册，请联系管理员'}), 400
            
            # 检查手机号是否已存在
            existing_phone = db.execute('SELECT id FROM users WHERE phone = ?', (phone,)).fetchone()
            if existing_phone:
                return jsonify({'success': False, 'message': '手机号已被注册'}), 400
            
            # 加密密码
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # 插入新用户
            db.execute('''
                INSERT INTO users (username, password, name, role, department, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password_hash.decode('utf-8'), name, 'specialist', department, phone))
            
            db.commit()
            logger.info(f"用户 {username}({name}) 注册成功")
            
            return jsonify({
                'success': True, 
                'message': '注册成功！请使用新账号登录',
                'redirect': '/login'
            })
            
    except Exception as e:
        logger.error(f"注册错误: {e}")
        return jsonify({'success': False, 'message': '注册失败，请重试'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        logger.info("收到登录请求")
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        logger.info(f"登录尝试: 用户名={username}, 密码长度={len(password)}")
        
        if not username or not password:
            logger.warning("用户名或密码为空")
            return render_template_string(LOGIN_TEMPLATE, error='用户名和密码不能为空')
        
        try:
            db = sqlite3.connect('timesheet.db')
            user = db.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
            db.close()
            
            if user:
                logger.info(f"找到用户: {user[1]}, 角色: {user[4]}")
                # 检查密码
                stored_password = user[2]
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')
                
                if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                    logger.info(f"用户 {username} 登录成功")
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    session['name'] = user[3]
                    session['role'] = user[4]
                    session['department'] = user[5]
                    
                    if user[4] == 'supervisor':
                        logger.info("重定向到管理员仪表板")
                        return redirect(url_for('admin_dashboard'))
                    else:
                        logger.info("重定向到用户仪表板")
                        return redirect(url_for('user_dashboard'))
                else:
                    logger.warning(f"用户 {username} 密码错误")
                    return render_template_string(LOGIN_TEMPLATE, error='用户名或密码错误')
            else:
                logger.warning(f"用户 {username} 不存在")
                return render_template_string(LOGIN_TEMPLATE, error='用户名或密码错误')
                
        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            return render_template_string(LOGIN_TEMPLATE, error='登录失败，请重试')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('login'))

# 管理页面模板
ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理者仪表板 - 工时管理系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .nav-bar {
            background: #f8f9fa;
            padding: 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .nav-tabs {
            list-style: none;
            display: flex;
            margin: 0;
            padding: 0;
        }
        
        .nav-tabs li {
            flex: 1;
        }
        
        .nav-tabs a {
            display: block;
            padding: 15px 20px;
            text-decoration: none;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
            text-align: center;
            font-weight: 500;
        }
        
        .nav-tabs a:hover,
        .nav-tabs a.active {
            color: #4facfe;
            border-bottom-color: #4facfe;
            background: white;
        }
        
        .content {
            padding: 30px;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #4facfe;
            margin-bottom: 10px;
        }
        
        .stat-label {
            color: #666;
            font-size: 1.1em;
        }
        
        .table-container {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .table-header {
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
        }
        
        .table-header h3 {
            margin: 0;
            color: #333;
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .table th,
        .table td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        
        .table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        
        .table tr:hover {
            background: #f8f9fa;
        }
        
        .filters {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .filter-group {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .filter-group label {
            font-weight: 500;
            color: #333;
        }
        
        .filter-group input,
        .filter-group select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .btn {
            background: #4facfe;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s ease;
        }
        
        .btn:hover {
            background: #3d8bfe;
        }
        
        .btn-danger {
            background: #dc3545;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .btn-success {
            background: #28a745;
        }
        
        .btn-success:hover {
            background: #218838;
        }
        
        .user-table {
            margin-top: 20px;
        }
        
        .role-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .role-specialist {
            background: #e3f2fd;
            color: #1976d2;
        }
        
        .role-supervisor {
            background: #fff3e0;
            color: #f57c00;
        }
        
        .efficiency-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }
        
        .efficiency-excellent {
            background: #e8f5e8;
            color: #2d5016;
        }
        
        .efficiency-good {
            background: #e3f2fd;
            color: #1976d2;
        }
        
        .efficiency-normal {
            background: #fff3e0;
            color: #f57c00;
        }
        
        .efficiency-low {
            background: #ffebee;
            color: #c62828;
        }
        
        .efficiency-none {
            background: #f5f5f5;
            color: #757575;
        }
        
        .logout-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        
        .logout-btn:hover {
            background: rgba(255,255,255,0.3);
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/logout" class="logout-btn">退出登录</a>
            <h1>管理者仪表板</h1>
            <p>欢迎您，{{ user.name }}！系统管理员控制面板</p>
        </div>
        
        <nav class="nav-bar">
            <ul class="nav-tabs">
                <li><a href="#overview" class="nav-link active" data-tab="overview">概览统计</a></li>
                <li><a href="#records" class="nav-link" data-tab="records">工时记录</a></li>
                <li><a href="#users" class="nav-link" data-tab="users">用户管理</a></li>
            </ul>
        </nav>
        
        <div class="content">
            <!-- 概览统计 -->
            <div id="overview" class="tab-content active">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number" id="totalUsers">0</div>
                        <div class="stat-label">注册用户</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="todayRecords">0</div>
                        <div class="stat-label">今日工时记录</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="monthRecords">0</div>
                        <div class="stat-label">本月工时记录</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="totalHours">0</div>
                        <div class="stat-label">本月总工时</div>
                    </div>
                </div>
                
                <div class="table-container">
                    <div class="table-header">
                        <h3>组别平均日工时统计</h3>
                        <div style="margin-top: 10px;">
                            <label>选择月份:</label>
                            <select id="monthSelector" onchange="handleMonthSelection()" style="margin-left: 10px; padding: 5px;">
                                <option value="">当前月份</option>
                            </select>
                        </div>
                    </div>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>组别/部门</th>
                                <th>工作天数</th>
                                <th>实际巡店日数</th>
                                <th>总工时</th>
                                <th>平均日工时</th>
                                <th>效率等级</th>
                            </tr>
                        </thead>
                        <tbody id="departmentStats">
                            <tr>
                                <td colspan="6" style="text-align: center; color: #666;">加载中...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="table-container">
                    <div class="table-header">
                        <h3>最新工时记录</h3>
                    </div>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>专员</th>
                                <th>工作日期</th>
                                <th>出发地点</th>
                                <th>目标地点</th>
                                <th>总工时</th>
                                <th>录入时间</th>
                            </tr>
                        </thead>
                        <tbody id="recentRecords">
                            <tr>
                                <td colspan="6" style="text-align: center; color: #666;">加载中...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- 工时记录 -->
            <div id="records" class="tab-content">
                <div class="filters">
                    <div class="filter-group">
                        <label>快速选择:</label>
                        <select id="monthFilter" onchange="handleMonthChange()">
                            <option value="">自定义日期范围</option>
                            <option value="current">本月</option>
                            <option value="last">上月</option>
                            <option value="last2">前2月</option>
                            <option value="last3">前3月</option>
                        </select>
                        
                        <label>开始日期:</label>
                        <input type="date" id="startDate" value="">
                        
                        <label>结束日期:</label>
                        <input type="date" id="endDate" value="">
                        
                        <label>组别/部门:</label>
                        <select id="departmentFilter">
                            <option value="">全部组别</option>
                        </select>
                        
                        <label>专员:</label>
                        <select id="userFilter">
                            <option value="">全部专员</option>
                        </select>
                        
                        <button class="btn" onclick="loadRecords()">查询</button>
                        <button class="btn btn-success" onclick="exportRecords()">导出Excel</button>
                    </div>
                </div>
                
                <div class="table-container">
                    <div class="table-header">
                        <h3>工时记录列表</h3>
                    </div>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>专员</th>
                                <th>工作日期</th>
                                <th>出发地点</th>
                                <th>目标地点</th>
                                <th>路程(km)</th>
                                <th>总工时</th>
                                <th>录入时间</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="recordsList">
                            <tr>
                                <td colspan="9" style="text-align: center; color: #666;">请选择查询条件</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- 用户管理 -->
            <div id="users" class="tab-content">
                <div class="table-container">
                    <div class="table-header">
                        <h3>用户管理</h3>
                    </div>
                    <table class="table user-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>用户名</th>
                                <th>姓名</th>
                                <th>角色</th>
                                <th>部门</th>
                                <th>注册时间</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="usersList">
                            <tr>
                                <td colspan="7" style="text-align: center; color: #666;">加载中...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            setupTabs();
            initMonthSelector();
            loadOverviewData();
            loadUsers();
            
            // 设置默认日期
            const today = new Date();
            const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
            document.getElementById('startDate').value = formatDate(firstDay);
            document.getElementById('endDate').value = formatDate(today);
        });
        
        // 标签页切换
        function setupTabs() {
            const navLinks = document.querySelectorAll('.nav-link');
            const tabContents = document.querySelectorAll('.tab-content');
            
            navLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    // 移除所有活动状态
                    navLinks.forEach(l => l.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    // 添加活动状态
                    this.classList.add('active');
                    const tabId = this.getAttribute('data-tab');
                    document.getElementById(tabId).classList.add('active');
                });
            });
        }
        
        // 加载概览数据
        function loadOverviewData(selectedMonth = '') {
            const url = selectedMonth ? `/api/admin/overview?month=${selectedMonth}` : '/api/admin/overview';
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('totalUsers').textContent = data.totalUsers;
                        document.getElementById('todayRecords').textContent = data.todayRecords;
                        document.getElementById('monthRecords').textContent = data.monthRecords;
                        document.getElementById('totalHours').textContent = data.totalHours + 'h';
                        
                        // 加载部门统计数据
                        loadDepartmentStats(data.departmentStats);
                        
                        // 加载最新记录
                        loadRecentRecords(data.recentRecords);
                    }
                })
                .catch(error => {
                    console.error('加载概览数据失败:', error);
                });
        }
        
        // 处理月份选择
        function handleMonthSelection() {
            const monthSelector = document.getElementById('monthSelector');
            const selectedMonth = monthSelector.value;
            loadOverviewData(selectedMonth);
        }
        
        // 初始化月份选择器
        function initMonthSelector() {
            const monthSelector = document.getElementById('monthSelector');
            const currentDate = new Date();
            
            // 生成最近12个月的选项
            for (let i = 0; i < 12; i++) {
                const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
                const monthValue = date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0');
                const monthText = date.getFullYear() + '年' + (date.getMonth() + 1) + '月';
                
                const option = document.createElement('option');
                option.value = monthValue;
                option.textContent = monthText;
                monthSelector.appendChild(option);
            }
        }
        
        // 加载部门统计数据
        function loadDepartmentStats(departmentStats) {
            const tbody = document.getElementById('departmentStats');
            if (departmentStats && departmentStats.length > 0) {
                tbody.innerHTML = departmentStats.map(dept => {
                    // 根据平均日工时判断效率等级
                    let efficiencyLevel = '';
                    let levelClass = '';
                    const avgHours = dept.avg_daily_hours;
                    
                    if (avgHours >= 8) {
                        efficiencyLevel = '优秀';
                        levelClass = 'efficiency-excellent';
                    } else if (avgHours >= 6) {
                        efficiencyLevel = '良好';
                        levelClass = 'efficiency-good';
                    } else if (avgHours >= 4) {
                        efficiencyLevel = '一般';
                        levelClass = 'efficiency-normal';
                    } else if (avgHours > 0) {
                        efficiencyLevel = '待提升';
                        levelClass = 'efficiency-low';
                    } else {
                        efficiencyLevel = '无数据';
                        levelClass = 'efficiency-none';
                    }
                    
                    return `
                        <tr>
                            <td>${dept.department}</td>
                            <td>${dept.work_days}天</td>
                            <td>${dept.actual_visit_days}天</td>
                            <td>${dept.total_hours.toFixed(1)}h</td>
                            <td>${dept.avg_daily_hours}h</td>
                            <td><span class="efficiency-badge ${levelClass}">${efficiencyLevel}</span></td>
                        </tr>
                    `;
                }).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #666;">暂无部门数据</td></tr>';
            }
        }
        
        // 加载最新记录
        function loadRecentRecords(records) {
            const tbody = document.getElementById('recentRecords');
            if (records && records.length > 0) {
                tbody.innerHTML = records.map(record => `
                    <tr>
                        <td>${record.user_name}</td>
                        <td>${record.work_date}</td>
                        <td>${record.start_location || '未设置'}</td>
                        <td>${record.end_location || '未设置'}</td>
                        <td>${record.total_work_hours}h</td>
                        <td>${formatDateTime(record.created_at)}</td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #666;">暂无记录</td></tr>';
            }
        }
        
        // 加载用户列表
        function loadUsers() {
            fetch('/api/admin/users')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const tbody = document.getElementById('usersList');
                        const select = document.getElementById('userFilter');
                        
                        // 更新用户列表
                        tbody.innerHTML = data.users.map(user => `
                            <tr>
                                <td>${user.id}</td>
                                <td>${user.username}</td>
                                <td>${user.name}</td>
                                <td><span class="role-badge role-${user.role}">${user.role === 'specialist' ? '专员' : '主管'}</span></td>
                                <td>${user.department || '未设置'}</td>
                                <td>${formatDateTime(user.created_at)}</td>
                                <td>
                                    <select onchange="updateUserRole(${user.id}, this.value)" ${user.username === 'admin' ? 'disabled' : ''}>
                                        <option value="specialist" ${user.role === 'specialist' ? 'selected' : ''}>专员</option>
                                        <option value="supervisor" ${user.role === 'supervisor' ? 'selected' : ''}>主管</option>
                                    </select>
                                    ${user.username !== 'admin' ? `<button class="btn btn-danger" onclick="deleteUser(${user.id})" style="margin-left: 10px;">删除</button>` : ''}
                                </td>
                            </tr>
                        `).join('');
                        
                        // 更新用户筛选下拉框
                        select.innerHTML = '<option value="">全部专员</option>' + 
                            data.users.filter(user => user.role === 'specialist').map(user => `
                                <option value="${user.id}">${user.name}</option>
                            `).join('');
                        
                        // 更新部门筛选下拉框
                        const departmentSelect = document.getElementById('departmentFilter');
                        const departments = [...new Set(data.users.map(user => user.department).filter(dept => dept))];
                        departmentSelect.innerHTML = '<option value="">全部组别</option>' + 
                            departments.map(dept => `
                                <option value="${dept}">${dept}</option>
                            `).join('');
                    }
                })
                .catch(error => {
                    console.error('加载用户列表失败:', error);
                });
        }
        
        // 更新用户角色
        function updateUserRole(userId, newRole) {
            if (!confirm('确定要修改此用户的角色吗？')) {
                loadUsers(); // 重新加载以恢复原始值
                return;
            }
            
            fetch('/api/admin/update_user_role', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    role: newRole
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('用户角色更新成功！');
                    loadUsers();
                } else {
                    alert('更新失败：' + data.message);
                    loadUsers();
                }
            })
            .catch(error => {
                console.error('更新用户角色失败:', error);
                alert('更新失败，请重试');
                loadUsers();
            });
        }
        
        // 删除用户
        function deleteUser(userId) {
            if (!confirm('确定要删除此用户吗？此操作不可恢复！')) {
                return;
            }
            
            fetch('/api/admin/delete_user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('用户删除成功！');
                    loadUsers();
                    loadOverviewData(); // 重新加载概览数据
                } else {
                    alert('删除失败：' + data.message);
                }
            })
            .catch(error => {
                console.error('删除用户失败:', error);
                alert('删除失败，请重试');
            });
        }
        
        // 处理月份选择
        function handleMonthChange() {
            const monthFilter = document.getElementById('monthFilter').value;
            const startDateInput = document.getElementById('startDate');
            const endDateInput = document.getElementById('endDate');
            
            if (monthFilter) {
                const now = new Date();
                let startDate, endDate;
                
                switch(monthFilter) {
                    case 'current':
                        // 本月
                        startDate = new Date(now.getFullYear(), now.getMonth(), 1);
                        endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                        break;
                    case 'last':
                        // 上月
                        startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                        endDate = new Date(now.getFullYear(), now.getMonth(), 0);
                        break;
                    case 'last2':
                        // 前2月
                        startDate = new Date(now.getFullYear(), now.getMonth() - 2, 1);
                        endDate = new Date(now.getFullYear(), now.getMonth() - 1, 0);
                        break;
                    case 'last3':
                        // 前3月
                        startDate = new Date(now.getFullYear(), now.getMonth() - 3, 1);
                        endDate = new Date(now.getFullYear(), now.getMonth() - 2, 0);
                        break;
                }
                
                startDateInput.value = startDate.toISOString().split('T')[0];
                endDateInput.value = endDate.toISOString().split('T')[0];
                
                // 自动查询
                loadRecords();
            }
        }

        // 加载工时记录
        function loadRecords() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const userId = document.getElementById('userFilter').value;
            const department = document.getElementById('departmentFilter').value;
            
            const params = new URLSearchParams({
                start_date: startDate,
                end_date: endDate,
                user_id: userId,
                department: department
            });
            
            fetch('/api/admin/records?' + params)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const tbody = document.getElementById('recordsList');
                        if (data.records && data.records.length > 0) {
                            tbody.innerHTML = data.records.map(record => `
                                <tr>
                                    <td>${record.id}</td>
                                    <td>${record.user_name}</td>
                                    <td>${record.work_date}</td>
                                    <td>${record.start_location || '未设置'}</td>
                                    <td>${record.end_location || '未设置'}</td>
                                    <td>${record.round_trip_distance || 0}</td>
                                    <td>${record.total_work_hours}</td>
                                    <td>${formatDateTime(record.created_at)}</td>
                                    <td>
                                        <button class="btn btn-danger" onclick="deleteRecord(${record.id})">删除</button>
                                    </td>
                                </tr>
                            `).join('');
                        } else {
                            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #666;">没有找到符合条件的记录</td></tr>';
                        }
                    }
                })
                .catch(error => {
                    console.error('加载记录失败:', error);
                });
        }
        
        // 删除工时记录
        function deleteRecord(recordId) {
            if (!confirm('确定要删除此工时记录吗？')) {
                return;
            }
            
            fetch('/api/admin/delete_record', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    record_id: recordId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('记录删除成功！');
                    loadRecords();
                    loadOverviewData(); // 重新加载概览数据
                } else {
                    alert('删除失败：' + data.message);
                }
            })
            .catch(error => {
                console.error('删除记录失败:', error);
                alert('删除失败，请重试');
            });
        }
        
        // 导出记录
        function exportRecords() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const userId = document.getElementById('userFilter').value;
            const department = document.getElementById('departmentFilter').value;
            
            const params = new URLSearchParams({
                start_date: startDate,
                end_date: endDate,
                user_id: userId,
                department: department
            });
            
            window.open('/api/admin/export_records?' + params, '_blank');
        }
        
        // 格式化日期时间
        function formatDateTime(dateTimeStr) {
            const date = new Date(dateTimeStr);
            return date.toLocaleString('zh-CN');
        }
        
        // 格式化日期
        function formatDate(date) {
            return date.toISOString().split('T')[0];
        }
    </script>
</body>
</html>
'''

@app.route('/admin')
def admin_dashboard():
    """管理者仪表板"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return redirect(url_for('login'))
    
    user = {
        'name': session.get('name'),
        'department': session.get('department')
    }
    
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, user=user)

# 管理者API端点
@app.route('/api/admin/overview')
def admin_overview():
    """管理者概览统计API"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        # 获取月份参数，默认为当前月份
        selected_month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        month_start = f"{selected_month}-01"
        # 计算月末日期
        if selected_month:
            year, month = map(int, selected_month.split('-'))
            if month == 12:
                next_month = f"{year + 1}-01-01"
            else:
                next_month = f"{year}-{month + 1:02d}-01"
            from datetime import datetime as dt
            month_end = (dt.strptime(next_month, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            month_end = datetime.now().strftime('%Y-%m-%d')
        
        with get_db_connection() as db:
            # 统计总用户数
            total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            
            # 统计今日工时记录
            today = datetime.now().strftime('%Y-%m-%d')
            today_records = db.execute(
                'SELECT COUNT(*) FROM timesheet_records WHERE work_date = ?', 
                (today,)
            ).fetchone()[0]
            
            # 统计选定月份工时记录
            current_month_start = datetime.now().strftime('%Y-%m-01')
            month_records = db.execute(
                'SELECT COUNT(*) FROM timesheet_records WHERE work_date >= ? AND work_date <= ?', 
                (month_start, month_end)
            ).fetchone()[0]
            
            # 统计选定月份总工时
            total_hours = db.execute(
                'SELECT COALESCE(SUM(total_work_hours), 0) FROM timesheet_records WHERE work_date >= ? AND work_date <= ?', 
                (month_start, month_end)
            ).fetchone()[0]
            
            # 统计各部门平均日工时（使用与专员端相同的算法：总工时 ÷ 实际巡店日期数）
            department_avg_hours = db.execute('''
                SELECT 
                    u.department,
                    COUNT(DISTINCT t.work_date) as work_days,
                    COALESCE(SUM(t.total_work_hours), 0) as total_hours,
                    COALESCE(SUM(t.actual_visit_days), 0) as total_actual_visit_days,
                    ROUND(COALESCE(SUM(t.total_work_hours), 0) / NULLIF(COALESCE(SUM(t.actual_visit_days), 0), 0), 2) as avg_daily_hours
                FROM users u
                LEFT JOIN timesheet_records t ON u.id = t.user_id AND t.work_date >= ? AND t.work_date <= ?
                WHERE u.department IS NOT NULL AND u.department != ''
                GROUP BY u.department
                ORDER BY avg_daily_hours DESC
            ''', (month_start, month_end)).fetchall()
            
            dept_stats = []
            for dept in department_avg_hours:
                dept_stats.append({
                    'department': dept['department'],
                    'work_days': dept['work_days'],
                    'actual_visit_days': dept['total_actual_visit_days'],
                    'total_hours': dept['total_hours'],
                    'avg_daily_hours': dept['avg_daily_hours'] or 0
                })
            
            # 获取最新5条工时记录
            recent_records = db.execute('''
                SELECT t.*, u.name as user_name 
                FROM timesheet_records t 
                JOIN users u ON t.user_id = u.id 
                ORDER BY t.created_at DESC 
                LIMIT 5
            ''').fetchall()
            
            records_list = []
            for record in recent_records:
                records_list.append({
                    'user_name': record['user_name'],
                    'work_date': record['work_date'],
                    'start_location': record['start_location'],
                    'end_location': record['end_location'],
                    'total_work_hours': record['total_work_hours'],
                    'created_at': record['created_at']
                })
            
            return jsonify({
                'success': True,
                'totalUsers': total_users,
                'todayRecords': today_records,
                'monthRecords': month_records,
                'totalHours': round(total_hours, 1),
                'departmentStats': dept_stats,
                'recentRecords': records_list
            })
            
    except Exception as e:
        logger.error(f"加载管理者概览数据失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/api/admin/users')
def admin_users():
    """管理者用户列表API"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        with get_db_connection() as db:
            users = db.execute('''
                SELECT id, username, name, role, department, created_at 
                FROM users 
                ORDER BY created_at DESC
            ''').fetchall()
            
            users_list = []
            for user in users:
                users_list.append({
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'department': user['department'],
                    'created_at': user['created_at']
                })
            
            return jsonify({
                'success': True,
                'users': users_list
            })
            
    except Exception as e:
        logger.error(f"加载用户列表失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/api/admin/update_user_role', methods=['POST'])
def admin_update_user_role():
    """更新用户角色API"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_role = data.get('role')
        
        if not user_id or not new_role:
            return jsonify({'success': False, 'message': '参数不完整'}), 400
        
        if new_role not in ['specialist', 'supervisor']:
            return jsonify({'success': False, 'message': '无效的角色类型'}), 400
        
        with get_db_connection() as db:
            # 检查用户是否存在
            user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            # 不允许修改admin用户的角色
            if user['username'] == 'admin':
                return jsonify({'success': False, 'message': '不能修改管理员账号的角色'}), 403
            
            # 更新用户角色
            db.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            db.commit()
            
            return jsonify({'success': True, 'message': '用户角色更新成功'})
            
    except Exception as e:
        logger.error(f"更新用户角色失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/api/admin/delete_user', methods=['POST'])
def admin_delete_user():
    """删除用户API"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': '参数不完整'}), 400
        
        with get_db_connection() as db:
            # 检查用户是否存在
            user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            # 不允许删除admin用户
            if user['username'] == 'admin':
                return jsonify({'success': False, 'message': '不能删除管理员账号'}), 403
            
            # 先删除用户的工时记录
            db.execute('DELETE FROM timesheet_records WHERE user_id = ?', (user_id,))
            
            # 删除用户
            db.execute('DELETE FROM users WHERE id = ?', (user_id,))
            db.commit()
            
            return jsonify({'success': True, 'message': '用户删除成功'})
            
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/api/admin/records')
def admin_records():
    """管理者工时记录查询API"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        user_id = request.args.get('user_id', '')
        department = request.args.get('department', '')
        
        with get_db_connection() as db:
            query = '''
                SELECT t.*, u.name as user_name, u.department as user_department 
                FROM timesheet_records t 
                JOIN users u ON t.user_id = u.id 
                WHERE 1=1
            '''
            params = []
            
            if start_date:
                query += ' AND t.work_date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND t.work_date <= ?'
                params.append(end_date)
                
            if user_id:
                query += ' AND t.user_id = ?'
                params.append(user_id)
                
            if department:
                query += ' AND u.department = ?'
                params.append(department)
            
            query += ' ORDER BY t.work_date DESC, t.created_at DESC'
            
            records = db.execute(query, params).fetchall()
            
            records_list = []
            for record in records:
                records_list.append({
                    'id': record['id'],
                    'user_name': record['user_name'],
                    'user_department': record['user_department'],
                    'work_date': record['work_date'],
                    'start_location': record['start_location'],
                    'end_location': record['end_location'],
                    'round_trip_distance': record['round_trip_distance'],
                    'total_work_hours': record['total_work_hours'],
                    'created_at': record['created_at']
                })
            
            return jsonify({
                'success': True,
                'records': records_list
            })
            
    except Exception as e:
        logger.error(f"查询工时记录失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/api/admin/delete_record', methods=['POST'])
def admin_delete_record():
    """删除工时记录API"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        record_id = data.get('record_id')
        
        if not record_id:
            return jsonify({'success': False, 'message': '参数不完整'}), 400
        
        with get_db_connection() as db:
            # 检查记录是否存在
            record = db.execute('SELECT id FROM timesheet_records WHERE id = ?', (record_id,)).fetchone()
            if not record:
                return jsonify({'success': False, 'message': '记录不存在'}), 404
            
            # 删除记录
            db.execute('DELETE FROM timesheet_records WHERE id = ?', (record_id,))
            db.commit()
            
            return jsonify({'success': True, 'message': '记录删除成功'})
            
    except Exception as e:
        logger.error(f"删除工时记录失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/api/admin/export_records')
def admin_export_records():
    """导出工时记录为Excel"""
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        user_id = request.args.get('user_id', '')
        department = request.args.get('department', '')
        
        with get_db_connection() as db:
            query = '''
                SELECT t.*, u.name as user_name, u.department as user_department 
                FROM timesheet_records t 
                JOIN users u ON t.user_id = u.id 
                WHERE 1=1
            '''
            params = []
            
            if start_date:
                query += ' AND t.work_date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND t.work_date <= ?'
                params.append(end_date)
                
            if user_id:
                query += ' AND t.user_id = ?'
                params.append(user_id)
                
            if department:
                query += ' AND u.department = ?'
                params.append(department)
            
            query += ' ORDER BY t.work_date DESC, t.created_at DESC'
            
            records = db.execute(query, params).fetchall()
            
            # 简单的CSV导出（可以后续升级为Excel）
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow([
                'ID', '专员姓名', '工作日期', '出发地点', '目标地点', 
                '路程(km)', '总工时(h)', '录入时间'
            ])
            
            # 写入数据
            for record in records:
                writer.writerow([
                    record['id'],
                    record['user_name'],
                    record['work_date'],
                    record['start_location'] or '',
                    record['end_location'] or '',
                    record['round_trip_distance'] or 0,
                    record['total_work_hours'],
                    record['created_at']
                ])
            
            # 创建响应
            from flask import Response
            
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=工时记录_{datetime.now().strftime("%Y%m%d")}.csv'
                }
            )
            
    except Exception as e:
        logger.error(f"导出工时记录失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

@app.route('/user')
def user_dashboard():
    """用户工时录入界面"""
    if 'user_id' not in session or session.get('role') != 'specialist':
        return redirect(url_for('login'))
    
    user = {
        'name': session.get('name'),
        'department': session.get('department')
    }
    
    return render_template_string(USER_INPUT_TEMPLATE, user=user)

@app.route('/user/records')
def user_records():
    """用户工时记录查看界面"""
    if 'user_id' not in session or session.get('role') != 'specialist':
        return redirect(url_for('login'))
    
    user = {
        'name': session.get('name'),
        'department': session.get('department')
    }
    
    return render_template_string(USER_RECORDS_TEMPLATE, user=user)

@app.route('/test_amap')
def test_amap_page():
    """高德API测试页面"""
    try:
        with open('/Users/zhaobinbin/Desktop/2025年9月/路径线上化/test_amap.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "测试页面文件未找到", 404

@app.route('/debug')
def debug_page():
    """调试页面 - 简化版界面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>调试页面</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            input, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #007bff; color: white; cursor: pointer; }
            #result { margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>搜索调试页面</h1>
            <div>
                <input type="text" id="keyword" placeholder="输入搜索关键词" value="古茗铅山九狮广场店">
                <button onclick="testSearch()">测试搜索</button>
            </div>
            <div id="result">准备测试...</div>
        </div>
        
        <script>
            async function testSearch() {
                const keyword = document.getElementById('keyword').value;
                const resultDiv = document.getElementById('result');
                
                if (!keyword) {
                    resultDiv.innerHTML = '请输入搜索关键词';
                    return;
                }
                
                resultDiv.innerHTML = '搜索中...';
                
                try {
                    const response = await fetch('/api/search_location', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ keyword: keyword })
                    });
                    
                    const data = await response.json();
                    console.log('搜索结果:', data);
                    
                    if (data.success && data.locations) {
                        let html = '<h3>搜索结果:</h3>';
                        data.locations.forEach((loc, index) => {
                            const isRec = loc.is_recommendation ? ' [推荐]' : '';
                            html += `<div style="border:1px solid #ddd; margin:5px 0; padding:10px;">
                                <strong>${index + 1}. ${loc.name}${isRec}</strong><br>
                                地址: ${loc.address}<br>
                                坐标: ${loc.location}<br>
                                ${loc.recommendation_reason ? '<em>' + loc.recommendation_reason + '</em><br>' : ''}
                            </div>`;
                        });
                        resultDiv.innerHTML = html;
                    } else {
                        resultDiv.innerHTML = '<span style="color:red;">搜索失败: ' + (data.message || '未知错误') + '</span>';
                    }
                } catch (error) {
                    console.error('搜索错误:', error);
                    resultDiv.innerHTML = '<span style="color:red;">搜索出错: ' + error.message + '</span>';
                }
            }
            
            // 页面加载完成后自动测试
            window.onload = function() {
                testSearch();
            };
        </script>
    </body>
    </html>
    """

# 高德API测试路由
@app.route('/api/test_amap', methods=['POST'])
def api_test_amap():
    """测试高德API的各种搜索方式"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求数据格式错误'})
    
    keyword = validate_and_clean_input(data, 'keyword', str, '')
    
    if not keyword:
        return jsonify({'success': False, 'message': '关键词不能为空'})
    
    # 测试多种搜索方式
    test_results = []
    
    # 测试1：完整关键词搜索
    test_results.append(test_amap_search("完整搜索", keyword, {}))
    
    # 测试2：铅山+古茗
    test_results.append(test_amap_search("铅山古茗", "古茗", {"city": "铅山"}))
    
    # 测试3：九狮广场
    test_results.append(test_amap_search("九狮广场", "九狮广场", {"city": "铅山"}))
    
    # 测试4：辛弃疾广场
    test_results.append(test_amap_search("辛弃疾广场", "辛弃疾广场", {"city": "铅山"}))
    
    # 测试5：广场+古茗
    test_results.append(test_amap_search("广场古茗", "广场 古茗", {"city": "铅山"}))
    
    return jsonify({'success': True, 'test_results': test_results})

def test_amap_search(test_name, keywords, extra_params=None):
    """测试单个高德搜索"""
    try:
        url = 'https://restapi.amap.com/v3/place/text'
        params = {
            'key': AMAP_API_KEY,
            'keywords': keywords,
            'types': '',
            'city': '',
            'children': 1,
            'offset': 20,
            'page': 1,
            'extensions': 'all',
            'citylimit': 'false',
            'datatype': 'all'
        }
        
        if extra_params:
            params.update(extra_params)
        
        response = safe_request(url, params=params, timeout=10)
        data = response.json()
        
        result = {
            'test_name': test_name,
            'params': params,
            'status': data.get('status'),
            'count': len(data.get('pois', [])),
            'results': []
        }
        
        if data['status'] == '1' and data.get('pois'):
            for poi in data['pois'][:5]:  # 只显示前5个结果
                result['results'].append({
                    'name': poi['name'],
                    'address': poi['address'],
                    'location': poi['location'],
                    'cityname': poi.get('cityname', ''),
                    'adname': poi.get('adname', '')
                })
        
        return result
        
    except Exception as e:
        return {
            'test_name': test_name,
            'error': str(e)
        }

# API路由
@app.route('/api/search_location', methods=['POST'])
def api_search_location():
    """搜索地点API"""
    # 移除登录检查，允许搜索功能正常使用
    # if 'user_id' not in session:
    #     return jsonify({'success': False, 'message': '未登录'})
    
    data = request.get_json()
    keyword = data.get('keyword', '')
    city = data.get('city', '')  # 恢复：城市参数
    force_tencent = data.get('force_tencent', False)  # 强制使用腾讯地图
    
    if not keyword:
        return jsonify({'success': False, 'message': '关键词不能为空'})
    
    if force_tencent:
        # 强制使用腾讯地图搜索
        logger.info(f"手动激活腾讯地图搜索: {keyword}, 城市: {city}")
        tencent_results = search_tencent_location(keyword, region=city if city else None)
        
        if tencent_results:
            result = {
                'success': True,
                'locations': tencent_results,
                'message': f'腾讯地图找到 {len(tencent_results)} 个结果',
                'source': 'tencent_manual'
            }
        else:
            result = {
                'success': False,
                'locations': [],
                'message': '腾讯地图未找到相关结果',
                'source': 'tencent_manual'
            }
    else:
        # 正常搜索流程（传递城市参数）
        result = search_location(keyword, city=city)
    
    return jsonify(result)

@app.route('/api/calculate_route', methods=['POST'])
def api_calculate_route():
    """计算路线API"""
    # 移除登录检查，允许路线计算功能正常使用
    # if 'user_id' not in session:
    #     return jsonify({'success': False, 'message': '未登录'})
    
    data = request.get_json()
    start_store = data.get('start_store', '')
    end_store = data.get('end_store', '')
    start_location = data.get('start_location', '')
    end_location = data.get('end_location', '')
    transport_mode = data.get('transport_mode', 'driving')
    # 强制使用高德推荐路线（移除前端路线策略选择）
    route_strategy = '10'
    
    if not start_store or not end_store:
        return jsonify({'success': False, 'message': '起点和终点不能为空'})
    
    result = calculate_route(start_store, end_store, transport_mode, route_strategy, start_location, end_location)
    return jsonify(result)

@app.route('/api/my_timesheet', methods=['GET'])
def api_get_my_timesheet():
    """获取当前用户的工时记录"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})
    
    try:
        db = sqlite3.connect('timesheet.db')
        db.row_factory = sqlite3.Row
        
        records = db.execute('''
            SELECT * FROM timesheet_records 
            WHERE user_id = ? 
            ORDER BY work_date ASC, created_at ASC
        ''', (session['user_id'],)).fetchall()
        
        db.close()
        
        records_list = []
        for record in records:
            record_dict = dict(record)
            records_list.append(record_dict)
        
        return jsonify({
            'success': True,
            'records': records_list
        })
    except Exception as e:
        print(f"获取工时记录失败: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/my_timesheet', methods=['POST'])
def api_create_timesheet():
    """创建工时记录"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})
    
    try:
        data = request.get_json()
        
        # 安全转换数值，处理空字符串
        def safe_float(value, default=0):
            if value is None or value == '' or value == 'undefined':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        def safe_int(value, default=0):
            if value is None or value == '' or value == 'undefined':
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        # 计算总工时
        travel_hours = safe_float(data.get('travelHours', 0))
        transport_mode = data.get('transportMode', 'driving')
        
        # 根据交通方式调整路途工时
        if transport_mode == 'train':
            # 高铁：在用户输入基础上增加1小时
            travel_hours = travel_hours + 1
        elif transport_mode == 'airplane':
            # 飞机：在用户输入基础上增加2小时
            travel_hours = travel_hours + 2
        
        visit_hours = safe_float(data.get('visitHours', 0))
        report_hours = safe_float(data.get('reportHours', 0))
        total_work_hours = travel_hours + visit_hours + report_hours
        
        db = sqlite3.connect('timesheet.db')
        db.execute('''
            INSERT INTO timesheet_records (
                user_id, work_date, business_trip_days, actual_visit_days,
                audit_store_count, training_store_count, start_location, end_location,
                round_trip_distance, transport_mode, schedule_number,
                travel_hours, visit_hours, report_hours, total_work_hours,
                notes, store_code, city
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            data.get('workDate'),
            safe_int(data.get('businessTripDays', 1), 1),
            safe_int(data.get('actualVisitDays', 1), 1),
            1,  # audit_store_count 默认设为1
            0,  # training_store_count 设为0
            data.get('startStore', ''),
            data.get('endStore', ''),
            safe_float(data.get('roundTripDistance', 0)),
            data.get('transportMode', 'driving'),
            data.get('scheduleNumber', ''),
            travel_hours,
            visit_hours,
            report_hours,
            total_work_hours,
            data.get('notes', ''),
            data.get('storeCode', ''),
            data.get('city', '')
        ))
        
        db.commit()
        db.close()
        
        return jsonify({'success': True, 'message': '工时记录保存成功'})
    except Exception as e:
        print(f"创建工时记录失败: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/export_timesheet')
def api_export_timesheet():
    """导出工时记录为CSV（日期升序排列）"""
    if 'user_id' not in session:
        return redirect('/login')
    
    try:
        import io
        import csv
        from datetime import datetime
        
        # 创建内存中的CSV文件
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 设置列头
        headers = [
            '工作日期', '出差天数', '实际巡店天数', '审核门店数', 
            '起始门店', '终点门店', '单程距离(km)', '交通方式',
            '巡途工时(H)', '巡店工时(H)', '汇报工时(H)', '合计工时(H)',
            '备注', '门店编码', '城市'
        ]
        
        # 写入列头
        writer.writerow(headers)
        
        # 获取用户记录（按日期升序排序，5号在最上方）
        db = sqlite3.connect('timesheet.db')
        db.row_factory = sqlite3.Row
        records = db.execute('''
            SELECT * FROM timesheet_records 
            WHERE user_id = ? 
            ORDER BY work_date ASC, created_at ASC
        ''', (session['user_id'],)).fetchall()
        db.close()
        
        # 写入数据
        for record in records:
            writer.writerow([
                record['work_date'],
                record['business_trip_days'],
                record['actual_visit_days'],
                record['audit_store_count'],
                record['start_location'] or '',
                record['end_location'] or '',
                record['round_trip_distance'] or 0,
                record['transport_mode'] or 'driving',
                record['travel_hours'] or 0,
                record['visit_hours'] or 0,
                record['report_hours'] or 0,
                record['total_work_hours'] or 0,
                record['notes'] or '',
                record['store_code'] or '',
                record['city'] or ''
            ])
        
        # 转换为字节
        output.seek(0)
        csv_data = output.getvalue()
        output.close()
        
        # 生成文件名
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'工时记录_{current_time}.csv'
        
        # 创建字节流
        csv_bytes = io.BytesIO()
        csv_bytes.write(csv_data.encode('utf-8-sig'))  # 使用BOM确保Excel正确显示中文
        csv_bytes.seek(0)
        
        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"导出工时记录失败: {e}")
        return f"导出失败: {str(e)}", 500

@app.route('/api/my_timesheet/<int:record_id>', methods=['DELETE'])
def api_delete_timesheet(record_id):
    """删除工时记录"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})
    
    try:
        db = sqlite3.connect('timesheet.db')
        
        # 检查记录是否属于当前用户
        record = db.execute(
            'SELECT user_id FROM timesheet_records WHERE id = ?',
            (record_id,)
        ).fetchone()
        
        if not record:
            return jsonify({'success': False, 'message': '记录不存在'})
        
        if record[0] != session['user_id']:
            return jsonify({'success': False, 'message': '无权限删除此记录'})
        
        db.execute('DELETE FROM timesheet_records WHERE id = ?', (record_id,))
        db.commit()
        db.close()
        
        return jsonify({'success': True, 'message': '记录删除成功'})
    except Exception as e:
        print(f"删除工时记录失败: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/monthly_defaults', methods=['GET'])
def api_get_monthly_defaults():
    """获取当前用户本月的默认设置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})
    
    try:
        from datetime import datetime
        now = datetime.now()
        year = now.year
        month = now.month
        
        with get_db_connection() as db:
            # 查询当前月份的默认设置
            defaults = db.execute('''
                SELECT business_trip_days, actual_visit_days
                FROM user_monthly_defaults
                WHERE user_id = ? AND year = ? AND month = ?
            ''', (session['user_id'], year, month)).fetchone()
            
            if defaults:
                return jsonify({
                    'success': True,
                    'defaults': {
                        'business_trip_days': defaults[0],
                        'actual_visit_days': defaults[1]
                    }
                })
            else:
                # 没有默认设置，返回系统默认值
                return jsonify({
                    'success': True,
                    'defaults': {
                        'business_trip_days': 1,
                        'actual_visit_days': 1
                    }
                })
    except Exception as e:
        logger.error(f"获取月度默认设置失败: {e}")
        return jsonify({'success': False, 'message': '获取默认设置失败'})

@app.route('/api/monthly_defaults', methods=['POST'])
def api_save_monthly_defaults():
    """保存当前用户本月的默认设置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'})
    
    try:
        data = request.get_json()
        business_trip_days = int(data.get('business_trip_days', 1))
        actual_visit_days = int(data.get('actual_visit_days', 1))
        
        from datetime import datetime
        now = datetime.now()
        year = now.year
        month = now.month
        
        with get_db_connection() as db:
            # 使用 INSERT OR REPLACE 来更新或插入记录
            db.execute('''
                INSERT OR REPLACE INTO user_monthly_defaults 
                (user_id, year, month, business_trip_days, actual_visit_days, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (session['user_id'], year, month, business_trip_days, actual_visit_days))
            
            db.commit()
            
        return jsonify({'success': True, 'message': '月度默认设置保存成功'})
    except Exception as e:
        logger.error(f"保存月度默认设置失败: {e}")
        return jsonify({'success': False, 'message': '保存默认设置失败'})

@app.route('/api/tencent_usage_stats')
def api_tencent_usage_stats():
    """获取腾讯地图API使用统计"""
    usage_today = get_tencent_usage_today()
    cache_size = len(tencent_search_cache)
    
    return jsonify({
        'success': True,
        'today_usage': usage_today,
        'daily_limit': 200,
        'remaining': max(0, 200 - usage_today),
        'cache_size': cache_size,
        'cache_limit': 100,
        'usage_percentage': round((usage_today / 200) * 100, 1),
        'date': tencent_daily_usage['date']
    })

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8081))
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
