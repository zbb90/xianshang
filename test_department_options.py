#!/usr/bin/env python3
"""
测试部门选项调整效果
"""

import requests

def test_department_options():
    """测试部门选项"""
    print("🔧 测试部门选项调整效果...")
    
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
    
    # 2. 测试部门列表API
    try:
        response = session.get(f"{BASE_URL}/api/admin/departments")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                departments = data.get('departments', [])
                print(f"✅ 获取到 {len(departments)} 个部门:")
                for i, dept in enumerate(departments, 1):
                    print(f"  {i}. {dept}")
                
                # 验证部门列表是否正确
                expected_departments = [
                    '稽核一组', '稽核二组', '稽核三组', 
                    '稽核四组', '稽核五组', '稽核六组', 
                    '管理组'
                ]
                
                if departments == expected_departments:
                    print("✅ 部门列表完全正确")
                    return True
                else:
                    print("⚠️ 部门列表与预期不符")
                    print(f"  预期: {expected_departments}")
                    print(f"  实际: {departments}")
            else:
                print(f"❌ 获取部门列表失败: {data.get('message')}")
        else:
            print(f"❌ 获取部门列表失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取部门列表失败: {e}")
    
    return False

if __name__ == '__main__':
    if test_department_options():
        print("\n🎉 部门选项调整成功!")
        print("\n📋 现在的部门选项:")
        print("  1. 稽核一组")
        print("  2. 稽核二组") 
        print("  3. 稽核三组")
        print("  4. 稽核四组")
        print("  5. 稽核五组")
        print("  6. 稽核六组")
        print("  7. 管理组")
        
        print("\n✅ 调整位置:")
        print("  📝 注册页面下拉选择器")
        print("  👥 用户管理界面部门编辑")
        print("  📊 批量操作部门选择")
        print("  🔗 API接口返回数据")
    else:
        print("❌ 部门选项测试失败")


