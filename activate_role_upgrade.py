#!/usr/bin/env python3
"""
激活角色升级的脚本
"""

import requests

def activate_role_upgrade():
    """激活角色升级"""
    print("🔄 激活角色升级...")
    
    # 线上部署URL
    BASE_URL = "https://guming-timesheet-production.up.railway.app"
    
    # 1. 登录管理员账号
    session = requests.Session()
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        response = session.post(f"{BASE_URL}/login", data=login_data)
        if response.status_code == 200:
            print("✅ 管理员登录成功")
        else:
            print("❌ 管理员登录失败")
            return False
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return False
    
    # 2. 调用角色升级API
    try:
        response = session.post(f"{BASE_URL}/api/admin/upgrade_roles")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success'):
                    print(f"✅ {data.get('message')}")
                    return True
                else:
                    print(f"⚠️ {data.get('message')}")
            except:
                print("✅ 角色升级请求已发送")
                return True
        else:
            print(f"❌ 角色升级失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 角色升级失败: {e}")
    
    return False

if __name__ == '__main__':
    if activate_role_upgrade():
        print("\n🎉 角色升级激活成功!")
        print("\n📋 请等待2-3分钟后重新登录，查看以下功能:")
        print("  ✅ 复选框多选用户")
        print("  📊 批量权限设置")
        print("  🔧 部门下拉选择")
        print("  🎯 三级角色显示")
        print("  📋 批量操作区域")
    else:
        print("❌ 角色升级激活失败")
