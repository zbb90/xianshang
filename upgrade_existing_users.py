#!/usr/bin/env python3
"""
升级现有用户角色的脚本
将现有的supervisor角色更新为admin角色
"""

import os
import sys
sys.path.append('.')

from database_config import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upgrade_user_roles():
    """升级现有用户角色"""
    try:
        with get_db_connection() as db:
            # 查看当前用户角色
            users = db.execute('SELECT id, username, name, role FROM users').fetchall()
            
            print("📋 升级前用户角色:")
            for user in users:
                print(f"  ID:{user[0]} - {user[1]}({user[2]}) - {user[3]}")
            
            # 将supervisor角色升级为admin
            updated = db.execute('''
                UPDATE users 
                SET role = 'admin' 
                WHERE role = 'supervisor'
            ''')
            
            db.commit()
            
            # 查看升级后的用户角色
            users_after = db.execute('SELECT id, username, name, role FROM users').fetchall()
            
            print("\n📋 升级后用户角色:")
            for user in users_after:
                role_name = {'specialist': '专员', 'manager': '组长', 'admin': '管理员'}.get(user[3], user[3])
                print(f"  ID:{user[0]} - {user[1]}({user[2]}) - {user[3]} ({role_name})")
                
            print(f"\n✅ 角色升级完成！")
            return True
            
    except Exception as e:
        logger.error(f"❌ 角色升级失败: {e}")
        return False

def create_test_manager():
    """创建一个测试组长账号"""
    try:
        import bcrypt
        
        with get_db_connection() as db:
            # 检查是否已有组长
            manager = db.execute("SELECT id FROM users WHERE role = 'manager'").fetchone()
            if manager:
                print("ℹ️ 已存在组长账号")
                return True
            
            # 创建测试组长
            password_hash = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt())
            db.execute('''
                INSERT INTO users (username, password, name, role, department, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('李组长', password_hash.decode('utf-8'), '李组长', 'manager', '稽核一组', '13900139001'))
            
            db.commit()
            print("✅ 已创建测试组长账号: 李组长/123456 (稽核一组)")
            return True
            
    except Exception as e:
        logger.error(f"❌ 创建组长账号失败: {e}")
        return False

if __name__ == '__main__':
    print("🔧 开始升级用户角色...")
    
    if upgrade_user_roles():
        create_test_manager()
        print("\n🎉 权限系统升级完成!")
        print("\n📋 当前权限等级:")
        print("  🔴 admin - 管理员：可查看全部内容")
        print("  🟡 manager - 组长：只能查看自己组内情况")  
        print("  🟢 specialist - 专员：只能查看自己的数据")
        print("\n🧪 测试账号:")
        print("  - admin/admin123 (管理员)")
        print("  - 李组长/123456 (组长)")
        print("  - 赵彬彬/123456 (专员)")
    else:
        print("❌ 升级失败")
        exit(1)
