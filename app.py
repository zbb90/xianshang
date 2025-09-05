#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工时表管理系统 v4.0
简洁版本 - 专注于用户注册、登录和工时管理
"""

import os
import sqlite3
import secrets
import bcrypt
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

# 创建Flask应用
app = Flask(__name__)

# 配置
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# 高德API配置
try:
    from config import AMAP_API_KEY, AMAP_SECRET_KEY
except ImportError:
    AMAP_API_KEY = os.environ.get('AMAP_API_KEY', 'your_amap_api_key_here')
    AMAP_SECRET_KEY = os.environ.get('AMAP_SECRET_KEY', 'your_amap_secret_key_here')

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect('timesheet.db')
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            position TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 门店表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_code TEXT NOT NULL UNIQUE,
            store_name TEXT NOT NULL,
            store_city TEXT NOT NULL,
            address TEXT,
            longitude REAL,
            latitude REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 工时记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timesheet_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            store_name TEXT,
            work_date DATE NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            work_hours REAL NOT NULL,
            work_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

# 装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        conn = sqlite3.connect('timesheet.db')
        cursor = conn.cursor()
        cursor.execute("SELECT position FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or user[0] not in ['管理员', '管理层']:
            return jsonify({'error': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated_function

# 路由定义
@app.route('/')
def index():
    """主页 - 重定向到注册页面"""
    return redirect('/register')

@app.route('/register')
def register_page():
    """注册页面"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户注册 - 智能工时表管理系统</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .register-card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            padding: 50px;
            width: 100%;
            max-width: 520px;
            position: relative;
        }
        .version-badge {
            position: absolute;
            top: -10px;
            right: 20px;
            background: #52c41a;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 600;
        }
        .header {
            text-align: center;
            margin-bottom: 35px;
        }
        .logo {
            font-size: 32px;
            margin-bottom: 15px;
        }
        .title {
            font-size: 28px;
            font-weight: 700;
            color: #333;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #666;
            font-size: 16px;
        }
        .form-row {
            display: flex;
            gap: 20px;
            margin-bottom: 25px;
        }
        .form-group {
            margin-bottom: 25px;
            flex: 1;
        }
        .form-label {
            display: block;
            margin-bottom: 10px;
            color: #333;
            font-weight: 600;
            font-size: 15px;
        }
        .form-control, .form-select {
            width: 100%;
            height: 50px;
            padding: 0 18px;
            border: 2px solid #e8ecef;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s ease;
            background: #fafbfc;
        }
        .form-control:focus, .form-select:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
            transform: translateY(-1px);
        }
        .form-select {
            cursor: pointer;
        }
        .btn-register {
            width: 100%;
            height: 52px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 30px 0 20px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn-register:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        .btn-register:active {
            transform: translateY(-1px);
        }
        .btn-register:disabled {
            opacity: 0.7;
            transform: none;
            cursor: not-allowed;
        }
        .link-text {
            text-align: center;
            color: #666;
            font-size: 15px;
        }
        .link-text a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .link-text a:hover {
            text-decoration: underline;
        }
        .alert {
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 25px;
            font-size: 14px;
            display: none;
            font-weight: 500;
        }
        .alert-success {
            background: #d1f2eb;
            border: 2px solid #a3e4d7;
            color: #0e6b5d;
        }
        .alert-danger {
            background: #fadbd8;
            border: 2px solid #f5b7b1;
            color: #943126;
        }
        .loading {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="register-card">
        <div class="version-badge">V4.0 NEW</div>
        
        <div class="header">
            <div class="logo">🚀 智能工时表管理系统</div>
            <div class="title">用户注册</div>
            <div class="subtitle">创建您的专属账户</div>
        </div>
        
        <div id="message" class="alert"></div>
        
        <form id="registerForm">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">用户名</label>
                    <input type="text" class="form-control" id="username" required placeholder="输入用户名">
                </div>
                <div class="form-group">
                    <label class="form-label">邮箱</label>
                    <input type="email" class="form-control" id="email" required placeholder="输入邮箱地址">
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">密码</label>
                <input type="password" class="form-control" id="password" required minlength="6" placeholder="输入密码（至少6位）">
            </div>
            
            <div class="form-group">
                <label class="form-label">姓名</label>
                <input type="text" class="form-control" id="name" required placeholder="输入真实姓名">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">部门</label>
                    <select class="form-select" id="department" required>
                        <option value="">选择部门</option>
                        <option value="销售部">销售部</option>
                        <option value="市场部">市场部</option>
                        <option value="技术部">技术部</option>
                        <option value="运营部">运营部</option>
                        <option value="财务部">财务部</option>
                        <option value="人事部">人事部</option>
                        <option value="管理层">管理层</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">职位</label>
                    <input type="text" class="form-control" id="position" required placeholder="如：业务员，经理，专员">
                </div>
            </div>
            
            <button type="submit" class="btn-register">立即注册</button>
        </form>
        
        <div class="link-text">
            已有账户？ <a href="/login">立即登录</a>
        </div>
    </div>

    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                username: document.getElementById('username').value.trim(),
                email: document.getElementById('email').value.trim(),
                password: document.getElementById('password').value,
                name: document.getElementById('name').value.trim(),
                department: document.getElementById('department').value,
                position: document.getElementById('position').value.trim()
            };
            
            // 表单验证
            if (!formData.username || !formData.email || !formData.password || 
                !formData.name || !formData.department || !formData.position) {
                showMessage('请填写所有必填字段', 'danger');
                return;
            }
            
            if (formData.password.length < 6) {
                showMessage('密码长度至少6位', 'danger');
                return;
            }
            
            // 邮箱格式验证
            const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
            if (!emailRegex.test(formData.email)) {
                showMessage('请输入正确的邮箱格式', 'danger');
                return;
            }
            
            const messageDiv = document.getElementById('message');
            messageDiv.style.display = 'none';
            
            // 显示加载状态
            const submitBtn = document.querySelector('.btn-register');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = '注册中...';
            submitBtn.disabled = true;
            submitBtn.classList.add('loading');
            
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showMessage('🎉 注册成功！正在跳转到登录页面...', 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else {
                    showMessage(result.error || '注册失败，请重试', 'danger');
                }
            } catch (error) {
                showMessage('网络错误，请检查网络连接后重试', 'danger');
                console.error('Registration error:', error);
            } finally {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                submitBtn.classList.remove('loading');
            }
        });
        
        function showMessage(text, type) {
            const messageDiv = document.getElementById('message');
            messageDiv.className = `alert alert-${type}`;
            messageDiv.textContent = text;
            messageDiv.style.display = 'block';
            messageDiv.scrollIntoView({ behavior: 'smooth' });
        }
    </script>
</body>
</html>
    ''')

@app.route('/login')
def login_page():
    """登录页面"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户登录 - 智能工时表管理系统</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            padding: 50px;
            width: 100%;
            max-width: 420px;
        }
        .header {
            text-align: center;
            margin-bottom: 35px;
        }
        .logo {
            font-size: 32px;
            margin-bottom: 15px;
        }
        .title {
            font-size: 28px;
            font-weight: 700;
            color: #333;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #666;
            font-size: 16px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        .form-label {
            display: block;
            margin-bottom: 10px;
            color: #333;
            font-weight: 600;
            font-size: 15px;
        }
        .form-control {
            width: 100%;
            height: 50px;
            padding: 0 18px;
            border: 2px solid #e8ecef;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s ease;
            background: #fafbfc;
        }
        .form-control:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
            transform: translateY(-1px);
        }
        .btn-login {
            width: 100%;
            height: 52px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 30px 0 20px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn-login:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        .link-text {
            text-align: center;
            color: #666;
            font-size: 15px;
        }
        .link-text a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .alert {
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 25px;
            font-size: 14px;
            display: none;
            font-weight: 500;
        }
        .alert-success { background: #d1f2eb; color: #0e6b5d; }
        .alert-danger { background: #fadbd8; color: #943126; }
        .alert-warning { background: #fcf3cf; color: #7d6608; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="header">
            <div class="logo">🚀 智能工时表管理系统</div>
            <div class="title">用户登录</div>
            <div class="subtitle">欢迎回来</div>
        </div>
        
        <div id="message" class="alert"></div>
        
        <form id="loginForm">
            <div class="form-group">
                <label class="form-label">用户名/邮箱</label>
                <input type="text" class="form-control" id="account" required placeholder="请输入用户名或邮箱">
            </div>
            <div class="form-group">
                <label class="form-label">密码</label>
                <input type="password" class="form-control" id="password" required placeholder="请输入密码">
            </div>
            <button type="submit" class="btn-login">立即登录</button>
        </form>
        
        <div class="link-text">
            还没有账户？ <a href="/register">立即注册</a>
        </div>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const account = document.getElementById('account').value.trim();
            const password = document.getElementById('password').value;
            
            if (!account || !password) {
                showMessage('请填写完整信息', 'warning');
                return;
            }
            
            const submitBtn = document.querySelector('.btn-login');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = '登录中...';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account, password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showMessage('✅ 登录成功，正在跳转...', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    showMessage(result.error || '登录失败', 'danger');
                }
            } catch (error) {
                showMessage('网络错误，请重试', 'danger');
            } finally {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
        
        function showMessage(text, type) {
            const messageDiv = document.getElementById('message');
            messageDiv.className = `alert alert-${type}`;
            messageDiv.textContent = text;
            messageDiv.style.display = 'block';
        }
    </script>
</body>
</html>
    ''')

@app.route('/dashboard')
@login_required
def dashboard():
    """管理后台"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理后台 - 智能工时表管理系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f7fa; }
        .sidebar {
            width: 260px;
            background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
            height: 100vh;
            position: fixed;
            color: white;
        }
        .sidebar-header {
            padding: 30px 20px;
            text-align: center;
            border-bottom: 1px solid #34495e;
        }
        .sidebar-header h3 {
            color: white;
            font-size: 18px;
        }
        .nav-menu { padding: 20px 0; }
        .nav-item { margin: 8px 0; }
        .nav-link {
            color: #bdc3c7;
            padding: 15px 25px;
            display: flex;
            align-items: center;
            text-decoration: none;
            transition: all 0.3s;
            border: none;
            background: none;
            width: 100%;
            cursor: pointer;
        }
        .nav-link:hover, .nav-link.active {
            background: #3498db;
            color: white;
        }
        .nav-link i {
            width: 20px;
            margin-right: 12px;
        }
        .main-content {
            margin-left: 260px;
            padding: 30px;
        }
        .card {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
            margin-bottom: 20px;
        }
        .card h4 {
            margin-bottom: 20px;
            color: #2c3e50;
        }
        .form-row {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .form-group {
            flex: 1;
            margin-bottom: 20px;
        }
        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        .form-control, .form-select {
            width: 100%;
            height: 40px;
            padding: 0 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .btn-primary {
            background: #3498db;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }
        .btn-success {
            background: #27ae60;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }
        .hidden { display: none; }
        .user-info {
            text-align: right;
            margin-bottom: 20px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h3>🚀 工时管理系统</h3>
        </div>
        <nav class="nav-menu">
            <div class="nav-item">
                <button class="nav-link active" onclick="showPage('timesheet')">
                    ⏰ 工时录入
                </button>
            </div>
            <div class="nav-item admin-only">
                <button class="nav-link" onclick="showPage('stores')">
                    🏪 门店管理
                </button>
            </div>
            <div class="nav-item">
                <button class="nav-link" onclick="showPage('reports')">
                    📊 报表统计
                </button>
            </div>
            <div class="nav-item">
                <button class="nav-link" onclick="logout()">
                    🚪 退出登录
                </button>
            </div>
        </nav>
    </div>

    <div class="main-content">
        <div class="user-info">
            当前用户：<span id="userName">加载中...</span> | 
            部门：<span id="userDept">加载中...</span>
        </div>

        <!-- 工时录入页面 -->
        <div id="timesheet-page" class="page-content">
            <div class="card">
                <h4>📝 工时录入</h4>
                <form id="timesheetForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">门店编码</label>
                            <input type="text" class="form-control" id="storeCode" required placeholder="输入门店编码">
                        </div>
                        <div class="form-group">
                            <label class="form-label">工作日期</label>
                            <input type="date" class="form-control" id="workDate" required>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">开始时间</label>
                            <input type="time" class="form-control" id="startTime" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">结束时间</label>
                            <input type="time" class="form-control" id="endTime" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">工作内容</label>
                        <textarea class="form-control" id="workContent" rows="3" placeholder="描述工作内容..."></textarea>
                    </div>
                    <button type="submit" class="btn-primary">💾 保存工时记录</button>
                </form>
            </div>
        </div>

        <!-- 门店管理页面 -->
        <div id="stores-page" class="page-content hidden">
            <div class="card">
                <h4>🏪 门店管理</h4>
                <button class="btn-success" onclick="document.getElementById('storeFile').click()">
                    📤 导入门店信息
                </button>
                <input type="file" id="storeFile" accept=".xlsx,.xls,.csv" style="display: none;" onchange="importStores()">
                <div id="storesTable" style="margin-top: 20px;">
                    <!-- 门店列表将在这里显示 -->
                </div>
            </div>
        </div>

        <!-- 报表页面 -->
        <div id="reports-page" class="page-content hidden">
            <div class="card">
                <h4>📊 报表统计</h4>
                <p>报表功能开发中...</p>
            </div>
        </div>
    </div>

    <script>
        let currentUser = null;

        document.addEventListener('DOMContentLoaded', async () => {
            await loadUserInfo();
            setDefaultDate();
        });

        async function loadUserInfo() {
            try {
                const response = await fetch('/api/user/info');
                const user = await response.json();
                currentUser = user;
                
                document.getElementById('userName').textContent = user.name;
                document.getElementById('userDept').textContent = user.department;

                // 根据权限显示/隐藏管理功能
                if (user.position !== '管理员' && user.position !== '管理层') {
                    document.querySelectorAll('.admin-only').forEach(el => {
                        el.style.display = 'none';
                    });
                }
            } catch (error) {
                console.error('获取用户信息失败:', error);
                window.location.href = '/login';
            }
        }

        function setDefaultDate() {
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('workDate').value = today;
        }

        function showPage(pageId) {
            document.querySelectorAll('.page-content').forEach(page => {
                page.classList.add('hidden');
            });
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            
            document.getElementById(pageId + '-page').classList.remove('hidden');
            event.target.classList.add('active');
        }

        async function logout() {
            await fetch('/api/logout', { method: 'POST' });
            window.location.href = '/login';
        }

        // 工时表单提交
        document.getElementById('timesheetForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                store_code: document.getElementById('storeCode').value,
                work_date: document.getElementById('workDate').value,
                start_time: document.getElementById('startTime').value,
                end_time: document.getElementById('endTime').value,
                work_content: document.getElementById('workContent').value
            };
            
            try {
                const response = await fetch('/api/timesheet', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ 工时记录保存成功！');
                    document.getElementById('timesheetForm').reset();
                    setDefaultDate();
                } else {
                    alert('❌ ' + result.error);
                }
            } catch (error) {
                alert('网络错误: ' + error.message);
            }
        });

        async function importStores() {
            const fileInput = document.getElementById('storeFile');
            const file = fileInput.files[0];
            
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/api/stores/import', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                if (result.success) {
                    alert('✅ 门店信息导入成功！');
                } else {
                    alert('❌ ' + result.error);
                }
            } catch (error) {
                alert('导入失败: ' + error.message);
            }
        }
    </script>
</body>
</html>
    ''')

# API路由
@app.route('/api/health')
def health_check():
    """健康检查"""
    try:
        conn = sqlite3.connect('timesheet.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '4.0.0',
            'build': 'force-redeploy-2025-09-05'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    
    required_fields = ['username', 'email', 'password', 'name', 'department', 'position']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'缺少必要字段: {field}'}), 400
    
    # 验证
    if len(data['password']) < 6:
        return jsonify({'error': '密码长度至少6位'}), 400
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, data['email']):
        return jsonify({'error': '邮箱格式不正确'}), 400
    
    # 密码加密
    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    
    conn = sqlite3.connect('timesheet.db')
    cursor = conn.cursor()
    
    try:
        # 检查重复
        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', 
                      (data['username'], data['email']))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': '用户名或邮箱已存在'}), 400
        
        # 插入用户
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, name, department, position)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['username'], data['email'], password_hash.decode('utf-8'),
            data['name'], data['department'], data['position']
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'user_id': user_id
        })
        
    except sqlite3.Error as e:
        conn.close()
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    required_fields = ['account', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'缺少必要字段: {field}'}), 400
    
    conn = sqlite3.connect('timesheet.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, username, name, department, position, email, password_hash
            FROM users WHERE (username = ? OR email = ?) AND is_active = 1
        ''', (data['account'], data['account']))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user[6].encode('utf-8')):
            return jsonify({'error': '用户名或密码错误'}), 401
        
        # 设置session
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['name'] = user[2]
        session['department'] = user[3]
        session['position'] = user[4]
        session['email'] = user[5]
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': {
                'id': user[0], 'username': user[1], 'name': user[2],
                'department': user[3], 'position': user[4], 'email': user[5]
            }
        })
        
    except sqlite3.Error as e:
        conn.close()
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/user/info')
@login_required
def get_user_info():
    """获取用户信息"""
    conn = sqlite3.connect('timesheet.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, username, name, department, position, email
            FROM users WHERE id = ?
        ''', (session['user_id'],))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        return jsonify({
            'id': user[0], 'username': user[1], 'name': user[2],
            'department': user[3], 'position': user[4], 'email': user[5]
        })
        
    except sqlite3.Error as e:
        conn.close()
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500

@app.route('/api/timesheet', methods=['POST'])
@login_required
def add_timesheet():
    """添加工时记录"""
    data = request.get_json()
    
    required_fields = ['store_code', 'work_date', 'start_time', 'end_time']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'缺少必要字段: {field}'}), 400
    
    try:
        # 计算工作时长
        from datetime import datetime
        work_date = datetime.strptime(data['work_date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        start_datetime = datetime.combine(work_date, start_time)
        end_datetime = datetime.combine(work_date, end_time)
        
        if end_datetime <= start_datetime:
            return jsonify({'error': '结束时间必须晚于开始时间'}), 400
        
        work_hours = (end_datetime - start_datetime).total_seconds() / 3600
        
        conn = sqlite3.connect('timesheet.db')
        cursor = conn.cursor()
        
        # 插入记录
        cursor.execute('''
            INSERT INTO timesheet_records 
            (user_id, store_code, work_date, start_time, end_time, work_hours, work_content)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'], data['store_code'], data['work_date'],
            data['start_time'], data['end_time'], round(work_hours, 2),
            data.get('work_content', '')
        ))
        
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '工时记录添加成功',
            'record_id': record_id,
            'work_hours': round(work_hours, 2)
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

@app.route('/api/stores/import', methods=['POST'])
@admin_required
def import_stores():
    """导入门店信息"""
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400
    
    file = request.files['file']
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        return jsonify({'error': '不支持的文件格式'}), 400
    
    try:
        import pandas as pd
        df = pd.read_excel(file)
        
        required_columns = ['门店编码', '门店名称', '城市']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            return jsonify({'error': f'缺少必要列: {", ".join(missing)}'}), 400
        
        conn = sqlite3.connect('timesheet.db')
        cursor = conn.cursor()
        
        success_count = 0
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO stores (store_code, store_name, store_city, address)
                    VALUES (?, ?, ?, ?)
                ''', (
                    str(row['门店编码']).strip(),
                    str(row['门店名称']).strip(),
                    str(row['城市']).strip(),
                    str(row.get('地址', '')).strip()
                ))
                success_count += 1
            except:
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'导入完成，成功{success_count}条'
        })
        
    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
