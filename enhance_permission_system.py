#!/usr/bin/env python3
"""
增强权限管理系统
"""

import re

def enhance_user_management():
    """增强用户管理界面"""
    
    with open('app_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 添加批量权限管理API
    batch_permission_api = '''
# 批量权限管理API
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
                    db.execute('''
                    UPDATE users 
                    SET role = ?, department = ? 
                    WHERE id = ?
                    ''', (new_role, new_department, user_id))
                else:
                    db.execute('''
                    UPDATE users 
                    SET role = ? 
                    WHERE id = ?
                    ''', (new_role, user_id))
            
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
    
    # 在其他API前添加新的API
    content = content.replace(
        '# 用户角色升级端点',
        batch_permission_api + '\n# 用户角色升级端点'
    )
    
    # 2. 增强用户管理界面HTML
    enhanced_user_management = '''            <!-- 用户管理 -->
            <div id="users" class="tab-content">
                <div class="permission-management-container">
                    <!-- 权限管理工具栏 -->
                    <div class="permission-toolbar">
                        <h3>🔐 权限管理中心</h3>
                        <div class="toolbar-actions">
                            <button class="btn btn-primary" onclick="showBatchPermissionModal()">
                                📊 批量权限设置
                            </button>
                            <button class="btn btn-secondary" onclick="showDepartmentOverview()">
                                🏢 部门权限概览
                            </button>
                            <button class="btn btn-success" onclick="loadUsers()">
                                🔄 刷新用户列表
                            </button>
                        </div>
                    </div>
                    
                    <!-- 权限统计卡片 -->
                    <div class="permission-stats">
                        <div class="stat-card admin-card">
                            <div class="stat-icon">👑</div>
                            <div class="stat-info">
                                <div class="stat-number" id="adminCount">0</div>
                                <div class="stat-label">管理员</div>
                            </div>
                        </div>
                        <div class="stat-card manager-card">
                            <div class="stat-icon">👨‍💼</div>
                            <div class="stat-info">
                                <div class="stat-number" id="managerCount">0</div>
                                <div class="stat-label">组长</div>
                            </div>
                        </div>
                        <div class="stat-card specialist-card">
                            <div class="stat-icon">👨‍💻</div>
                            <div class="stat-info">
                                <div class="stat-number" id="specialistCount">0</div>
                                <div class="stat-label">专员</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 用户筛选器 -->
                    <div class="user-filters">
                        <div class="filter-group">
                            <label>角色筛选:</label>
                            <select id="roleFilter" onchange="filterUsers()">
                                <option value="">全部角色</option>
                                <option value="admin">管理员</option>
                                <option value="manager">组长</option>
                                <option value="specialist">专员</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label>部门筛选:</label>
                            <select id="departmentFilterUser" onchange="filterUsers()">
                                <option value="">全部部门</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <label>搜索用户:</label>
                            <input type="text" id="userSearch" placeholder="输入用户名或姓名" onkeyup="filterUsers()">
                        </div>
                    </div>
                    
                    <!-- 用户列表 -->
                    <div class="table-container">
                        <table class="table user-table">
                            <thead>
                                <tr>
                                    <th>
                                        <input type="checkbox" id="selectAll" onchange="toggleSelectAll()">
                                    </th>
                                    <th>ID</th>
                                    <th>用户名</th>
                                    <th>姓名</th>
                                    <th>当前角色</th>
                                    <th>部门</th>
                                    <th>手机号</th>
                                    <th>创建时间</th>
                                    <th>权限操作</th>
                                </tr>
                            </thead>
                            <tbody id="usersList">
                                <tr>
                                    <td colspan="9" style="text-align: center; padding: 20px;">
                                        正在加载用户数据...
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- 批量操作区域 -->
                    <div class="batch-actions" id="batchActions" style="display: none;">
                        <div class="batch-info">
                            已选择 <span id="selectedCount">0</span> 个用户
                        </div>
                        <div class="batch-buttons">
                            <select id="batchRole">
                                <option value="">选择角色</option>
                                <option value="specialist">设为专员</option>
                                <option value="manager">设为组长</option>
                                <option value="admin">设为管理员</option>
                            </select>
                            <select id="batchDepartment">
                                <option value="">选择部门</option>
                            </select>
                            <button class="btn btn-primary" onclick="batchUpdatePermissions()">
                                批量更新权限
                            </button>
                            <button class="btn btn-secondary" onclick="clearSelection()">
                                取消选择
                            </button>
                        </div>
                    </div>
                </div>
            </div>'''
    
    # 替换原有的用户管理部分
    content = re.sub(
        r'<!-- 用户管理 -->\s*<div id="users" class="tab-content">.*?</div>\s*</div>',
        enhanced_user_management,
        content,
        flags=re.DOTALL
    )
    
    with open('app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已增强用户管理界面")

def add_permission_styles():
    """添加权限管理样式"""
    
    with open('app_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    permission_styles = '''        
        /* 权限管理样式 */
        .permission-management-container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .permission-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .permission-toolbar h3 {
            margin: 0;
            color: #2c3e50;
            font-size: 24px;
        }
        
        .toolbar-actions {
            display: flex;
            gap: 10px;
        }
        
        .permission-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .stat-card.admin-card {
            background: linear-gradient(135deg, #c2185b 0%, #ad1457 100%);
        }
        
        .stat-card.manager-card {
            background: linear-gradient(135deg, #f57c00 0%, #ef6c00 100%);
        }
        
        .stat-card.specialist-card {
            background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
        }
        
        .stat-icon {
            font-size: 32px;
        }
        
        .stat-number {
            font-size: 28px;
            font-weight: bold;
        }
        
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .user-filters {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .filter-group label {
            font-weight: 600;
            color: #2c3e50;
            font-size: 14px;
        }
        
        .filter-group select,
        .filter-group input {
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        .filter-group select:focus,
        .filter-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .batch-actions {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .batch-info {
            font-weight: 600;
            color: #1976d2;
        }
        
        .batch-buttons {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .user-table tbody tr.selected {
            background-color: #e3f2fd !important;
        }
        
        .permission-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            text-align: center;
            min-width: 60px;
        }
        
        .permission-badge.admin {
            background: #fce4ec;
            color: #c2185b;
            border: 1px solid #f8bbd9;
        }
        
        .permission-badge.manager {
            background: #fff3e0;
            color: #f57c00;
            border: 1px solid #ffcc02;
        }
        
        .permission-badge.specialist {
            background: #e3f2fd;
            color: #1976d2;
            border: 1px solid #90caf9;
        }'''
    
    # 在现有样式后添加新样式
    content = content.replace(
        '        .efficiency-none {',
        permission_styles + '\n        .efficiency-none {'
    )
    
    with open('app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已添加权限管理样式")

def add_permission_javascript():
    """添加权限管理JavaScript功能"""
    
    with open('app_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    permission_js = '''        
        // 权限管理变量
        let allUsers = [];
        let selectedUsers = [];
        
        // 加载用户数据 (增强版)
        function loadUsers() {
            Promise.all([
                fetch('/api/admin/users'),
                fetch('/api/admin/department_stats')
            ])
            .then(([usersResponse, statsResponse]) => 
                Promise.all([usersResponse.json(), statsResponse.json()])
            )
            .then(([usersData, statsData]) => {
                if (usersData.success) {
                    allUsers = usersData.users;
                    renderUsersList(allUsers);
                    updatePermissionStats(allUsers);
                    
                    if (statsData.success) {
                        updateDepartmentFilters(statsData.departments);
                        updateBatchDepartmentOptions(statsData.departments);
                    }
                }
            })
            .catch(error => {
                console.error('加载用户数据失败:', error);
                showNotification('加载用户数据失败', 'error');
            });
        }
        
        // 渲染用户列表
        function renderUsersList(users) {
            const tbody = document.getElementById('usersList');
            
            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 20px;">没有找到用户</td></tr>';
                return;
            }
            
            tbody.innerHTML = users.map(user => `
                <tr data-user-id="${user.id}" ${selectedUsers.includes(user.id) ? 'class="selected"' : ''}>
                    <td>
                        <input type="checkbox" 
                               ${user.username === 'admin' ? 'disabled' : ''} 
                               ${selectedUsers.includes(user.id) ? 'checked' : ''}
                               onchange="toggleUserSelection(${user.id})">
                    </td>
                    <td>${user.id}</td>
                    <td>${user.username}</td>
                    <td>${user.name}</td>
                    <td>
                        <span class="permission-badge ${user.role}">${getRoleDisplayName(user.role)}</span>
                    </td>
                    <td>${user.department || '未设置'}</td>
                    <td>${user.phone || '未设置'}</td>
                    <td>${formatDateTime(user.created_at)}</td>
                    <td>
                        <select onchange="updateUserRole(${user.id}, this.value)" 
                                ${user.username === 'admin' ? 'disabled' : ''} 
                                class="role-selector">
                            <option value="specialist" ${user.role === 'specialist' ? 'selected' : ''}>专员</option>
                            <option value="manager" ${user.role === 'manager' ? 'selected' : ''}>组长</option>
                            <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>管理员</option>
                        </select>
                        ${user.username !== 'admin' ? `
                            <button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id})" style="margin-left: 8px;">
                                删除
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
        }
        
        // 更新权限统计
        function updatePermissionStats(users) {
            const stats = users.reduce((acc, user) => {
                acc[user.role] = (acc[user.role] || 0) + 1;
                return acc;
            }, {});
            
            document.getElementById('adminCount').textContent = stats.admin || 0;
            document.getElementById('managerCount').textContent = stats.manager || 0;
            document.getElementById('specialistCount').textContent = stats.specialist || 0;
        }
        
        // 更新部门筛选器
        function updateDepartmentFilters(departments) {
            const filter = document.getElementById('departmentFilterUser');
            filter.innerHTML = '<option value="">全部部门</option>' + 
                departments.map(dept => `<option value="${dept}">${dept}</option>`).join('');
        }
        
        // 更新批量操作部门选项
        function updateBatchDepartmentOptions(departments) {
            const select = document.getElementById('batchDepartment');
            select.innerHTML = '<option value="">选择部门</option>' + 
                departments.map(dept => `<option value="${dept}">${dept}</option>`).join('');
        }
        
        // 筛选用户
        function filterUsers() {
            const roleFilter = document.getElementById('roleFilter').value;
            const deptFilter = document.getElementById('departmentFilterUser').value;
            const searchText = document.getElementById('userSearch').value.toLowerCase();
            
            const filteredUsers = allUsers.filter(user => {
                const matchRole = !roleFilter || user.role === roleFilter;
                const matchDept = !deptFilter || user.department === deptFilter;
                const matchSearch = !searchText || 
                    user.username.toLowerCase().includes(searchText) ||
                    user.name.toLowerCase().includes(searchText);
                
                return matchRole && matchDept && matchSearch;
            });
            
            renderUsersList(filteredUsers);
        }
        
        // 切换用户选择
        function toggleUserSelection(userId) {
            const index = selectedUsers.indexOf(userId);
            if (index > -1) {
                selectedUsers.splice(index, 1);
            } else {
                selectedUsers.push(userId);
            }
            
            updateSelectionUI();
        }
        
        // 全选/取消全选
        function toggleSelectAll() {
            const checkAll = document.getElementById('selectAll').checked;
            const visibleUsers = Array.from(document.querySelectorAll('[data-user-id]'))
                .map(row => parseInt(row.dataset.userId))
                .filter(id => !allUsers.find(u => u.id === id)?.username === 'admin');
            
            if (checkAll) {
                selectedUsers = [...new Set([...selectedUsers, ...visibleUsers])];
            } else {
                selectedUsers = selectedUsers.filter(id => !visibleUsers.includes(id));
            }
            
            updateSelectionUI();
            renderUsersList(allUsers.filter(user => {
                const roleFilter = document.getElementById('roleFilter').value;
                const deptFilter = document.getElementById('departmentFilterUser').value;
                const searchText = document.getElementById('userSearch').value.toLowerCase();
                
                const matchRole = !roleFilter || user.role === roleFilter;
                const matchDept = !deptFilter || user.department === deptFilter;
                const matchSearch = !searchText || 
                    user.username.toLowerCase().includes(searchText) ||
                    user.name.toLowerCase().includes(searchText);
                
                return matchRole && matchDept && matchSearch;
            }));
        }
        
        // 更新选择UI
        function updateSelectionUI() {
            const count = selectedUsers.length;
            document.getElementById('selectedCount').textContent = count;
            document.getElementById('batchActions').style.display = count > 0 ? 'flex' : 'none';
        }
        
        // 清除选择
        function clearSelection() {
            selectedUsers = [];
            document.getElementById('selectAll').checked = false;
            updateSelectionUI();
            renderUsersList(allUsers);
        }
        
        // 批量更新权限
        function batchUpdatePermissions() {
            const newRole = document.getElementById('batchRole').value;
            const newDepartment = document.getElementById('batchDepartment').value;
            
            if (!newRole && !newDepartment) {
                showNotification('请选择要更新的角色或部门', 'warning');
                return;
            }
            
            if (selectedUsers.length === 0) {
                showNotification('请选择要更新的用户', 'warning');
                return;
            }
            
            const updates = selectedUsers.map(userId => ({
                user_id: userId,
                role: newRole || allUsers.find(u => u.id === userId)?.role,
                department: newDepartment || allUsers.find(u => u.id === userId)?.department
            }));
            
            if (!confirm(`确定要批量更新 ${selectedUsers.length} 个用户的权限吗？`)) {
                return;
            }
            
            fetch('/api/admin/batch_update_roles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message, 'success');
                    clearSelection();
                    loadUsers();
                } else {
                    showNotification(data.message, 'error');
                }
            })
            .catch(error => {
                console.error('批量更新失败:', error);
                showNotification('批量更新失败', 'error');
            });
        }
        
        // 显示通知
        function showNotification(message, type = 'info') {
            // 创建通知元素
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.innerHTML = `
                <span>${message}</span>
                <button onclick="this.parentElement.remove()">×</button>
            `;
            
            // 添加样式
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 6px;
                color: white;
                z-index: 1000;
                display: flex;
                justify-content: space-between;
                align-items: center;
                min-width: 300px;
                background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : type === 'warning' ? '#ff9800' : '#2196f3'};
            `;
            
            document.body.appendChild(notification);
            
            // 3秒后自动移除
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 3000);
        }
        
        // 显示批量权限模态框
        function showBatchPermissionModal() {
            if (selectedUsers.length === 0) {
                showNotification('请先选择要管理的用户', 'warning');
                return;
            }
            
            const modal = `
                <div class="modal-overlay" onclick="closeBatchModal()">
                    <div class="modal-content" onclick="event.stopPropagation()">
                        <h3>批量权限设置</h3>
                        <p>已选择 ${selectedUsers.length} 个用户</p>
                        <div class="form-group">
                            <label>新角色:</label>
                            <select id="modalBatchRole">
                                <option value="">保持不变</option>
                                <option value="specialist">专员</option>
                                <option value="manager">组长</option>
                                <option value="admin">管理员</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>新部门:</label>
                            <select id="modalBatchDepartment">
                                <option value="">保持不变</option>
                            </select>
                        </div>
                        <div class="modal-actions">
                            <button class="btn btn-primary" onclick="confirmBatchUpdate()">确认更新</button>
                            <button class="btn btn-secondary" onclick="closeBatchModal()">取消</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modal);
            
            // 填充部门选项
            fetch('/api/admin/department_stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const select = document.getElementById('modalBatchDepartment');
                        select.innerHTML = '<option value="">保持不变</option>' + 
                            data.departments.map(dept => `<option value="${dept}">${dept}</option>`).join('');
                    }
                });
        }
        
        // 关闭批量模态框
        function closeBatchModal() {
            document.querySelector('.modal-overlay')?.remove();
        }
        
        // 确认批量更新
        function confirmBatchUpdate() {
            const newRole = document.getElementById('modalBatchRole').value;
            const newDepartment = document.getElementById('modalBatchDepartment').value;
            
            if (!newRole && !newDepartment) {
                showNotification('请至少选择一个要更新的项目', 'warning');
                return;
            }
            
            document.getElementById('batchRole').value = newRole;
            document.getElementById('batchDepartment').value = newDepartment;
            
            closeBatchModal();
            batchUpdatePermissions();
        }
        
        // 显示部门概览
        function showDepartmentOverview() {
            fetch('/api/admin/department_stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const modal = `
                            <div class="modal-overlay" onclick="this.remove()">
                                <div class="modal-content department-overview" onclick="event.stopPropagation()">
                                    <h3>🏢 部门权限概览</h3>
                                    <div class="department-stats-grid">
                                        ${data.department_stats.map(dept => `
                                            <div class="dept-card">
                                                <h4>${dept.department}</h4>
                                                <div class="dept-stats">
                                                    <div class="stat-item">
                                                        <span class="stat-label">总人数:</span>
                                                        <span class="stat-value">${dept.total_users}</span>
                                                    </div>
                                                    <div class="stat-item">
                                                        <span class="stat-label">管理员:</span>
                                                        <span class="stat-value admin">${dept.admin_count}</span>
                                                    </div>
                                                    <div class="stat-item">
                                                        <span class="stat-label">组长:</span>
                                                        <span class="stat-value manager">${dept.manager_count}</span>
                                                    </div>
                                                    <div class="stat-item">
                                                        <span class="stat-label">专员:</span>
                                                        <span class="stat-value specialist">${dept.specialist_count}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        `).join('')}
                                    </div>
                                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">关闭</button>
                                </div>
                            </div>
                        `;
                        
                        document.body.insertAdjacentHTML('beforeend', modal);
                    }
                });
        }'''
    
    # 在现有JavaScript函数前添加新功能
    content = content.replace(
        '        // 加载用户列表',
        permission_js + '\n        // 加载用户列表'
    )
    
    with open('app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已添加权限管理JavaScript功能")

if __name__ == '__main__':
    print("🔧 开始增强权限管理系统...")
    enhance_user_management()
    add_permission_styles()
    add_permission_javascript()
    print("✅ 权限管理系统增强完成!")
    print("\n🎉 新增功能:")
    print("  📊 批量权限设置")
    print("  🏢 部门权限概览") 
    print("  🔍 高级用户筛选")
    print("  📈 权限统计面板")
    print("  🎯 可视化权限管理")
