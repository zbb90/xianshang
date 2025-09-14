#!/usr/bin/env python3
"""
增强权限管理系统 - 版本2
"""

def add_batch_permission_api():
    """添加批量权限API到app_clean.py"""
    
    with open('app_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在clear_test_data函数前添加新的API
    api_code = '''
@app.route('/api/admin/batch_update_roles', methods=['POST'])
def batch_update_roles():
    """批量更新用户角色"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '只有管理员可以批量修改权限'}), 403
    
    try:
        data = request.get_json()
        updates = data.get('updates', [])
        
        if not updates:
            return jsonify({'success': False, 'message': '没有要更新的数据'}), 400
        
        with get_db_connection() as db:
            for update in updates:
                user_id = update.get('user_id')
                new_role = update.get('role')
                new_department = update.get('department')
                
                if not user_id or not new_role:
                    continue
                
                if new_role not in ['specialist', 'manager', 'admin']:
                    continue
                
                # 防止修改admin用户
                user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
                if user and user[0] == 'admin':
                    continue
                
                # 更新用户信息
                if new_department:
                    db.execute('UPDATE users SET role = ?, department = ? WHERE id = ?', 
                             (new_role, new_department, user_id))
                else:
                    db.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            
            db.commit()
            return jsonify({'success': True, 'message': f'批量更新{len(updates)}个用户权限成功'})
            
    except Exception as e:
        logger.error(f"批量更新权限失败: {e}")
        return jsonify({'success': False, 'message': f'批量更新失败: {str(e)}'}), 500

@app.route('/api/admin/department_stats')
def get_department_stats():
    """获取部门统计信息用于权限管理"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        with get_db_connection() as db:
            # 获取部门用户统计
            dept_stats = db.execute('''
                SELECT 
                    department,
                    COUNT(*) as total_users,
                    SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_count,
                    SUM(CASE WHEN role = 'manager' THEN 1 ELSE 0 END) as manager_count,
                    SUM(CASE WHEN role = 'specialist' THEN 1 ELSE 0 END) as specialist_count
                FROM users 
                WHERE department IS NOT NULL AND department != ''
                GROUP BY department
                ORDER BY department
            ''').fetchall()
            
            # 获取所有部门列表
            departments = db.execute('''
                SELECT DISTINCT department 
                FROM users 
                WHERE department IS NOT NULL AND department != ''
                ORDER BY department
            ''').fetchall()
            
            return jsonify({
                'success': True,
                'department_stats': [dict(row) for row in dept_stats],
                'departments': [row[0] for row in departments]
            })
            
    except Exception as e:
        logger.error(f"获取部门统计失败: {e}")
        return jsonify({'success': False, 'message': f'获取数据失败: {str(e)}'}), 500

'''
    
    # 在clear_test_data前插入新API
    content = content.replace('# 临时数据清理端点（仅用于测试）', api_code + '# 临时数据清理端点（仅用于测试）')
    
    with open('app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已添加批量权限管理API")

def update_admin_permission_checks():
    """更新所有管理员权限检查，只允许admin角色访问用户管理"""
    
    with open('app_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 将权限检查从 'admin', 'manager' 改为只有 'admin'
    content = content.replace(
        "session.get('role') not in ['admin', 'manager']",
        "session.get('role') != 'admin'"
    )
    
    with open('app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已更新管理员权限检查")

if __name__ == '__main__':
    print("🔧 开始增强权限管理系统...")
    add_batch_permission_api()
    update_admin_permission_checks()
    print("✅ 权限管理系统增强完成!")
    print("\n🎉 新增功能:")
    print("  📊 批量权限设置API")
    print("  🏢 部门权限统计API") 
    print("  🔒 严格的管理员权限控制")
