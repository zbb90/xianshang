#!/usr/bin/env python3
"""
修复角色系统显示问题
"""

import re

def fix_role_system():
    """修复角色系统中的显示问题"""
    
    with open('app_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 强制修复角色升级函数，确保supervisor角色被替换为admin
    new_upgrade_function = '''
    try:
        with get_db_connection() as db:
            # 升级所有supervisor为admin
            result = db.execute("UPDATE users SET role = 'admin' WHERE role = 'supervisor' OR role = '主管'")
            updated_count = result.rowcount if hasattr(result, 'rowcount') else 0
            
            # 创建测试组长账号
            existing_manager = db.execute("SELECT id FROM users WHERE role = 'manager'").fetchone()
            if not existing_manager:
                import bcrypt
                password_hash = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt())
                db.execute('''
                    INSERT OR IGNORE INTO users (username, password, name, role, department, phone)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', ('李组长', password_hash.decode('utf-8'), '李组长', 'manager', '稽核一组', '13900139001'))
            
            # 添加预设部门选项
            departments = [
                '稽核一组', '稽核二组', '稽核三组', '稽核四组', '稽核五组',
                '稽核六组', '稽核七组', '稽核八组', '稽核九组', '稽核十组',
                '管理组', '培训组', '业务组', '技术组'
            ]
            
            db.commit()
            
            return jsonify({
                'success': True, 
                'message': f'角色系统升级完成！已更新{updated_count}个用户角色，已创建测试组长账号：李组长/123456',
                'departments': departments
            })
            
    except Exception as e:
        logger.error(f"升级用户角色失败: {e}")
        return jsonify({'success': False, 'message': f'升级失败: {str(e)}'}), 500'''
    
    # 替换升级函数的内容
    content = re.sub(
        r'try:\s*with get_db_connection\(\) as db:.*?return jsonify\({[^}]*}\), 500',
        new_upgrade_function,
        content,
        flags=re.DOTALL
    )
    
    # 2. 添加部门管理API
    department_api = '''
@app.route('/api/admin/departments')
def get_departments():
    """获取所有部门列表"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    departments = [
        '稽核一组', '稽核二组', '稽核三组', '稽核四组', '稽核五组',
        '稽核六组', '稽核七组', '稽核八组', '稽核九组', '稽核十组',
        '管理组', '培训组', '业务组', '技术组'
    ]
    
    return jsonify({
        'success': True,
        'departments': departments
    })

@app.route('/api/admin/update_user_department', methods=['POST'])
def update_user_department():
    """更新用户部门"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '只有管理员可以修改用户部门'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_department = data.get('department')
        
        if not user_id:
            return jsonify({'success': False, 'message': '用户ID不能为空'}), 400
        
        with get_db_connection() as db:
            # 检查用户是否存在
            user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            # 更新用户部门
            db.execute('UPDATE users SET department = ? WHERE id = ?', (new_department, user_id))
            db.commit()
            
            return jsonify({'success': True, 'message': '用户部门更新成功'})
            
    except Exception as e:
        logger.error(f"更新用户部门失败: {e}")
        return jsonify({'success': False, 'message': '服务器错误'}), 500

'''
    
    # 在批量权限管理API前添加部门管理API
    content = content.replace('# 批量权限管理API', department_api + '# 批量权限管理API')
    
    # 3. 添加部门编辑功能到用户列表
    enhanced_user_row = '''                        tbody.innerHTML = data.users.map(user => `
                            <tr data-user-id="${user.id}">
                                <td>
                                    <input type="checkbox" 
                                           ${user.username === 'admin' ? 'disabled' : ''} 
                                           onchange="toggleUserSelection(${user.id}, this.checked)">
                                </td>
                                <td>${user.id}</td>
                                <td>${user.username}</td>
                                <td>${user.name}</td>
                                <td>
                                    <span class="permission-badge ${user.role}">${getRoleDisplayName(user.role)}</span>
                                </td>
                                <td>
                                    <select onchange="updateUserDepartment(${user.id}, this.value)" 
                                            ${user.username === 'admin' ? 'disabled' : ''}>
                                        <option value="">未设置</option>
                                        <option value="稽核一组" ${user.department === '稽核一组' ? 'selected' : ''}>稽核一组</option>
                                        <option value="稽核二组" ${user.department === '稽核二组' ? 'selected' : ''}>稽核二组</option>
                                        <option value="稽核三组" ${user.department === '稽核三组' ? 'selected' : ''}>稽核三组</option>
                                        <option value="稽核四组" ${user.department === '稽核四组' ? 'selected' : ''}>稽核四组</option>
                                        <option value="稽核五组" ${user.department === '稽核五组' ? 'selected' : ''}>稽核五组</option>
                                        <option value="稽核六组" ${user.department === '稽核六组' ? 'selected' : ''}>稽核六组</option>
                                        <option value="稽核七组" ${user.department === '稽核七组' ? 'selected' : ''}>稽核七组</option>
                                        <option value="稽核八组" ${user.department === '稽核八组' ? 'selected' : ''}>稽核八组</option>
                                        <option value="稽核九组" ${user.department === '稽核九组' ? 'selected' : ''}>稽核九组</option>
                                        <option value="稽核十组" ${user.department === '稽核十组' ? 'selected' : ''}>稽核十组</option>
                                        <option value="管理组" ${user.department === '管理组' ? 'selected' : ''}>管理组</option>
                                        <option value="培训组" ${user.department === '培训组' ? 'selected' : ''}>培训组</option>
                                        <option value="业务组" ${user.department === '业务组' ? 'selected' : ''}>业务组</option>
                                        <option value="技术组" ${user.department === '技术组' ? 'selected' : ''}>技术组</option>
                                    </select>
                                </td>
                                <td>${user.phone || '未设置'}</td>
                                <td>${formatDateTime(user.created_at)}</td>
                                <td>
                                    <select onchange="updateUserRole(${user.id}, this.value)" ${user.username === 'admin' ? 'disabled' : ''}>
                                        <option value="specialist" ${user.role === 'specialist' ? 'selected' : ''}>专员</option>
                                        <option value="manager" ${user.role === 'manager' ? 'selected' : ''}>组长</option>
                                        <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>管理员</option>
                                    </select>
                                    ${user.username !== 'admin' ? `<button class="btn btn-danger" onclick="deleteUser(${user.id})" style="margin-left: 10px;">删除</button>` : ''}
                                </td>
                            </tr>
                        `).join('');'''
    
    # 替换用户列表渲染
    content = re.sub(
        r'tbody\.innerHTML = data\.users\.map\(user => `.*?`\)\.join\(\'\'\);',
        enhanced_user_row,
        content,
        flags=re.DOTALL
    )
    
    # 4. 添加部门更新函数
    department_js = '''        
        // 更新用户部门
        function updateUserDepartment(userId, newDepartment) {
            if (!confirm('确定要修改此用户的部门吗？')) {
                loadUsers(); // 重新加载以恢复原始值
                return;
            }

            fetch('/api/admin/update_user_department', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    department: newDepartment
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('部门更新成功！');
                    loadUsers();
                    loadOverviewData();
                } else {
                    alert('更新失败：' + data.message);
                    loadUsers();
                }
            })
            .catch(error => {
                console.error('更新用户部门失败:', error);
                alert('更新失败，请重试');
                loadUsers();
            });
        }
        '''
    
    # 在批量权限管理功能前添加部门更新函数
    content = content.replace('// 批量权限管理功能', department_js + '// 批量权限管理功能')
    
    with open('app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已修复角色系统显示问题")

if __name__ == '__main__':
    print("🔧 开始修复角色系统...")
    fix_role_system()
    print("✅ 角色系统修复完成!")
    print("\n📋 修复内容:")
    print("  🔄 强化角色升级逻辑")
    print("  📝 添加部门编辑功能") 
    print("  🎯 确保三个角色选项正确显示")
    print("  ✅ 添加部门管理API")
