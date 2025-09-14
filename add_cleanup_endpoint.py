#!/usr/bin/env python3
"""
添加数据清理端点到app_clean.py
"""

cleanup_endpoint = """
# 临时数据清理端点（仅用于测试）
@app.route('/api/admin/clear_test_data', methods=['POST'])
def clear_test_data():
    '''清理所有工时记录测试数据'''
    if 'user_id' not in session or session.get('role') != 'supervisor':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        with get_db_connection() as db:
            # 删除所有工时记录
            db.execute('DELETE FROM timesheet_records')
            # 删除月度默认设置
            db.execute('DELETE FROM user_monthly_defaults WHERE user_id != 2')  # 保留admin的设置
            db.commit()
            
            return jsonify({
                'success': True, 
                'message': '测试数据清理完成，可以重新创建工时记录进行测试'
            })
            
    except Exception as e:
        logger.error(f"清理测试数据失败: {e}")
        return jsonify({'success': False, 'message': f'清理失败: {str(e)}'}), 500
"""

# 读取现有文件
with open('/Users/zhaobinbin/Desktop/2025年9月/路径线上化/app_clean.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在文件末尾添加清理端点
if 'clear_test_data' not in content:
    content += '\n' + cleanup_endpoint + '\n'
    
    # 写回文件
    with open('/Users/zhaobinbin/Desktop/2025年9月/路径线上化/app_clean.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已添加数据清理端点: /api/admin/clear_test_data")
else:
    print("ℹ️ 清理端点已存在")
