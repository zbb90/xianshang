#!/usr/bin/env python3
"""
清理测试数据脚本
删除所有现有工时记录，重新测试专员姓名显示
"""

import os
import sys
sys.path.append('.')

from database_config import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_timesheet_records():
    """清空所有工时记录"""
    try:
        with get_db_connection() as db:
            # 删除所有工时记录
            db.execute('DELETE FROM timesheet_records')
            
            # 删除月度默认设置
            db.execute('DELETE FROM user_monthly_defaults')
            
            db.commit()
            
            logger.info("✅ 所有工时记录和月度默认设置已清空")
            
    except Exception as e:
        logger.error(f"❌ 清空数据失败: {e}")
        return False
        
    return True

def show_current_users():
    """显示当前用户列表"""
    try:
        with get_db_connection() as db:
            users = db.execute('SELECT id, username, name, role, department FROM users ORDER BY id').fetchall()
            
            print("\n📋 当前用户列表:")
            for user in users:
                print(f"  ID:{user[0]} - {user[1]}({user[2]}) - {user[3]} - {user[4] or '无部门'}")
                
    except Exception as e:
        logger.error(f"❌ 获取用户列表失败: {e}")

if __name__ == '__main__':
    print("🧹 开始清理测试数据...")
    show_current_users()
    
    if clear_timesheet_records():
        print("✅ 测试数据清理完成!")
        print("💡 现在可以用专员账号登录创建新的工时记录进行测试")
    else:
        print("❌ 数据清理失败")
        exit(1)
