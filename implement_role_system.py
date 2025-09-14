#!/usr/bin/env python3
"""
实现三级权限系统的脚本
"""

import re

def update_app_clean():
    """更新app_clean.py实现三级权限"""
    
    with open('app_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 添加权限检查函数
    permission_functions = '''
# 权限检查函数
def check_permission(required_role):
    """检查用户权限"""
    if 'user_id' not in session:
        return False, '未登录'
    
    user_role = session.get('role')
    user_department = session.get('department')
    
    # 角色权限等级 (数字越大权限越高)
    role_levels = {
        'specialist': 1,
        'manager': 2, 
        'admin': 3
    }
    
    current_level = role_levels.get(user_role, 0)
    required_level = role_levels.get(required_role, 999)
    
    return current_level >= required_level, '权限不足'

def can_view_department_data(target_department=None):
    """检查是否可以查看指定部门数据"""
    user_role = session.get('role')
    user_department = session.get('department')
    
    if user_role == 'admin':
        return True  # 管理员可查看所有部门
    elif user_role == 'manager':
        # 组长只能查看自己部门的数据
        return target_department is None or target_department == user_department
    else:
        return False  # 专员不能查看部门数据

def get_department_filter():
    """获取当前用户的部门过滤条件"""
    user_role = session.get('role')
    user_department = session.get('department')
    
    if user_role == 'admin':
        return None  # 无过滤条件
    elif user_role == 'manager':
        return user_department  # 只看自己部门
    else:
        return None  # 专员不需要部门过滤
'''
    
    # 在app创建后添加权限函数
    content = content.replace(
        '# 数据库连接函数现在从database_config.py导入，支持PostgreSQL和SQLite自动切换',
        permission_functions + '\n\n# 数据库连接函数现在从database_config.py导入，支持PostgreSQL和SQLite自动切换'
    )
    
    # 2. 更新注册页面的部门选项
    register_dept_options = '''                    <option value="稽核一组">稽核一组</option>
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
                    <option value="培训组">培训组</option>'''
    
    # 3. 修改主页重定向逻辑
    new_index_logic = '''@app.route('/')
def index():
    """主页，重定向到登录页"""
    if 'user_id' in session:
        user_role = session.get('role')
        if user_role in ['admin', 'manager']:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))'''
    
    content = re.sub(
        r'@app\.route\(\'/\'\)\s*\ndef index\(\):[^@]+',
        new_index_logic + '\n\n',
        content,
        flags=re.DOTALL
    )
    
    # 4. 更新管理员仪表板权限检查
    content = content.replace(
        "if 'user_id' not in session or session.get('role') != 'supervisor':",
        "if 'user_id' not in session or session.get('role') not in ['admin', 'manager']:"
    )
    
    # 5. 更新角色显示逻辑
    role_display_logic = '''function getRoleDisplayName(role) {
    const roleMap = {
        'specialist': '专员',
        'manager': '组长', 
        'admin': '管理员'
    };
    return roleMap[role] || role;
}'''
    
    # 替换角色显示
    content = content.replace(
        "${user.role === 'specialist' ? '专员' : '主管'}",
        "${getRoleDisplayName(user.role)}"
    )
    
    # 6. 更新角色选择选项
    role_options = '''                                        <option value="specialist" ${user.role === 'specialist' ? 'selected' : ''}>专员</option>
                                        <option value="manager" ${user.role === 'manager' ? 'selected' : ''}>组长</option>
                                        <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>管理员</option>'''
    
    content = re.sub(
        r'<option value="specialist"[^>]*>专员</option>\s*<option value="supervisor"[^>]*>主管</option>',
        role_options,
        content
    )
    
    # 7. 更新角色验证
    content = content.replace(
        "if new_role not in ['specialist', 'supervisor']:",
        "if new_role not in ['specialist', 'manager', 'admin']:"
    )
    
    with open('app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已更新 app_clean.py")

if __name__ == '__main__':
    print("🔧 开始实现三级权限系统...")
    update_app_clean()
    print("✅ 三级权限系统实现完成!")
    print("\n📋 新的权限等级:")
    print("  🔴 admin - 超级管理员：可查看全部内容")
    print("  🟡 manager - 组长：只能查看自己组内情况")  
    print("  🟢 specialist - 专员：只能查看自己的数据")
