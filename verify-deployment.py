#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway部署验证脚本
用于验证部署配置是否正确
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path

def check_file_exists(file_path):
    """检查文件是否存在"""
    return Path(file_path).exists()

def check_git_repo():
    """检查是否为Git仓库"""
    try:
        subprocess.run(['git', 'status'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_requirements():
    """检查requirements.txt中的依赖"""
    if not check_file_exists('requirements.txt'):
        return False, "requirements.txt文件不存在"
    
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
            required_packages = ['Flask', 'gunicorn']
            missing = [pkg for pkg in required_packages if pkg not in content]
            if missing:
                return False, f"缺少必要依赖: {', '.join(missing)}"
        return True, "依赖检查通过"
    except Exception as e:
        return False, f"读取requirements.txt失败: {e}"

def check_railway_config():
    """检查Railway配置"""
    if not check_file_exists('railway.json'):
        return False, "railway.json文件不存在"
    
    try:
        with open('railway.json', 'r') as f:
            config = json.load(f)
            
        # 检查必要配置
        required_keys = ['deploy']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            return False, f"railway.json缺少配置: {', '.join(missing_keys)}"
            
        if 'startCommand' not in config['deploy']:
            return False, "railway.json缺少startCommand配置"
            
        return True, "Railway配置检查通过"
    except json.JSONDecodeError:
        return False, "railway.json格式错误"
    except Exception as e:
        return False, f"检查railway.json失败: {e}"

def check_github_actions():
    """检查GitHub Actions配置"""
    workflow_path = '.github/workflows/railway-deploy.yml'
    if not check_file_exists(workflow_path):
        return False, "GitHub Actions工作流文件不存在"
    
    try:
        with open(workflow_path, 'r') as f:
            content = f.read()
            required_items = ['railway-app/railway-deploy', 'RAILWAY_TOKEN']
            missing = [item for item in required_items if item not in content]
            if missing:
                return False, f"GitHub Actions配置缺少: {', '.join(missing)}"
        return True, "GitHub Actions配置检查通过"
    except Exception as e:
        return False, f"检查GitHub Actions配置失败: {e}"

def check_wsgi():
    """检查WSGI配置"""
    if not check_file_exists('wsgi.py'):
        return False, "wsgi.py文件不存在"
    
    try:
        with open('wsgi.py', 'r') as f:
            content = f.read()
            if 'app' not in content:
                return False, "wsgi.py文件中未找到app变量"
        return True, "WSGI配置检查通过"
    except Exception as e:
        return False, f"检查wsgi.py失败: {e}"

def check_app_health(url=None):
    """检查应用健康状态"""
    if not url:
        return False, "未提供应用URL"
    
    try:
        response = requests.get(f"{url}/api/health", timeout=10)
        if response.status_code == 200:
            return True, "应用健康检查通过"
        else:
            return False, f"健康检查失败，状态码: {response.status_code}"
    except requests.RequestException as e:
        return False, f"健康检查请求失败: {e}"

def main():
    """主验证流程"""
    print("🔍 Railway部署配置验证")
    print("=" * 50)
    
    checks = [
        ("Git仓库检查", check_git_repo),
        ("依赖包检查", check_requirements),
        ("Railway配置检查", check_railway_config),
        ("GitHub Actions检查", check_github_actions),
        ("WSGI配置检查", check_wsgi),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            if callable(check_func):
                result = check_func()
                if isinstance(result, tuple):
                    success, message = result
                else:
                    success, message = result, "检查完成" if result else "检查失败"
            else:
                success, message = check_func, "检查完成"
            
            status = "✅" if success else "❌"
            print(f"{status} {name}: {message}")
            results.append((name, success, message))
            
        except Exception as e:
            print(f"❌ {name}: 检查异常 - {e}")
            results.append((name, False, f"检查异常 - {e}"))
    
    print("\n" + "=" * 50)
    
    # 统计结果
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"验证结果: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("🎉 所有检查都通过！可以开始部署。")
        print("\n下一步操作:")
        print("1. 确保GitHub仓库已创建并配置了Railway集成")
        print("2. 在GitHub Secrets中添加必要的环境变量")
        print("3. 推送代码到主分支触发自动部署")
        print("4. 运行: ./railway-deploy.sh")
        return 0
    else:
        print("⚠️  存在配置问题，请修复后重新验证。")
        print("\n失败的检查项:")
        for name, success, message in results:
            if not success:
                print(f"  - {name}: {message}")
        return 1

    # 可选：检查已部署的应用
    app_url = os.environ.get('RAILWAY_APP_URL')
    if app_url:
        print(f"\n🌐 检查已部署应用: {app_url}")
        success, message = check_app_health(app_url)
        status = "✅" if success else "❌"
        print(f"{status} 应用健康检查: {message}")

if __name__ == '__main__':
    sys.exit(main())
