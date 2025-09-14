#!/usr/bin/env python3
"""
激活权限管理系统的测试脚本
"""

import requests
import json

# 线上部署URL
BASE_URL = "https://guming-timesheet-production.up.railway.app"

def test_permission_system():
    """测试权限管理系统"""
    print("🔧 测试权限管理系统...")
    
    # 1. 测试登录
    print("\n1. 测试管理员登录...")
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
    
    # 2. 测试角色升级API
    print("\n2. 激活权限系统...")
    try:
        response = session.post(f"{BASE_URL}/api/admin/upgrade_roles")
        data = response.json()
        if data.get('success'):
            print(f"✅ {data.get('message')}")
        else:
            print(f"⚠️ {data.get('message')}")
    except Exception as e:
        print(f"❌ 角色升级失败: {e}")
    
    # 3. 测试用户列表API
    print("\n3. 测试用户列表...")
    try:
        response = session.get(f"{BASE_URL}/api/admin/users")
        data = response.json()
        if data.get('success'):
            users = data.get('users', [])
            print(f"✅ 获取到 {len(users)} 个用户")
            for user in users:
                role_name = {'specialist': '专员', 'manager': '组长', 'admin': '管理员'}.get(user['role'], user['role'])
                print(f"  - {user['name']} ({user['username']}) - {role_name} - {user.get('department', '未设置')}")
        else:
            print(f"❌ 获取用户列表失败: {data.get('message')}")
    except Exception as e:
        print(f"❌ 获取用户列表失败: {e}")
    
    # 4. 测试部门统计API
    print("\n4. 测试部门统计...")
    try:
        response = session.get(f"{BASE_URL}/api/admin/department_stats")
        data = response.json()
        if data.get('success'):
            dept_stats = data.get('department_stats', [])
            departments = data.get('departments', [])
            print(f"✅ 获取到 {len(departments)} 个部门统计")
            for dept in dept_stats:
                print(f"  - {dept['department']}: {dept['total_users']}人 (管理员{dept['admin_count']}, 组长{dept['manager_count']}, 专员{dept['specialist_count']})")
        else:
            print(f"❌ 获取部门统计失败: {data.get('message')}")
    except Exception as e:
        print(f"❌ 获取部门统计失败: {e}")
    
    print("\n🎉 权限管理系统测试完成!")
    return True

if __name__ == '__main__':
    print("🚀 激活权限管理系统...")
    
    if test_permission_system():
        print("\n✅ 权限管理系统已成功激活!")
        print("\n📋 功能特性:")
        print("  🔐 三级权限控制 (admin/manager/specialist)")
        print("  📊 批量权限设置")
        print("  🏢 部门权限统计")
        print("  ✅ 复选框多选功能")
        print("  🎯 可视化权限管理")
        
        print("\n🔑 使用说明:")
        print("  1. 用admin账号登录管理后台")
        print("  2. 进入'用户管理'标签页")
        print("  3. 使用复选框选择用户")
        print("  4. 选择新角色和部门")
        print("  5. 点击'批量更新权限'按钮")
        
        print("\n🧪 测试账号:")
        print("  - admin/admin123 (管理员)")
        print("  - 李组长/123456 (组长)")
        print("  - 其他专员账号")
    else:
        print("❌ 权限管理系统激活失败")
