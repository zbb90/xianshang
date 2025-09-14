#!/usr/bin/env python3
"""
生产环境数据库升级脚本：为已有PostgreSQL数据库添加phone字段
使用方法：python upgrade_production_db.py
"""

import os
import psycopg2
from datetime import datetime

def upgrade_production_database():
    """升级生产环境数据库，添加缺失字段"""
    
    # PostgreSQL连接配置（来自Railway环境变量）
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ 未找到DATABASE_URL环境变量")
        return False
    
    print("🔄 开始升级生产环境数据库...")
    
    try:
        # 连接PostgreSQL
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_cursor = pg_conn.cursor()
        
        # 检查并添加phone字段到users表
        try:
            pg_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='phone'
            """)
            if not pg_cursor.fetchone():
                pg_cursor.execute('ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT \'\'')
                print("✅ 已添加phone字段到users表")
            else:
                print("ℹ️  users表已存在phone字段")
                
        except Exception as e:
            print(f"❌ 添加phone字段失败: {e}")
        
        # 检查并添加store_code字段到timesheet_records表
        try:
            pg_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='timesheet_records' AND column_name='store_code'
            """)
            if not pg_cursor.fetchone():
                pg_cursor.execute('ALTER TABLE timesheet_records ADD COLUMN store_code VARCHAR(255)')
                print("✅ 已添加store_code字段到timesheet_records表")
            else:
                print("ℹ️  timesheet_records表已存在store_code字段")
                
        except Exception as e:
            print(f"❌ 添加store_code字段失败: {e}")
        
        # 检查并添加city字段到timesheet_records表
        try:
            pg_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='timesheet_records' AND column_name='city'
            """)
            if not pg_cursor.fetchone():
                pg_cursor.execute('ALTER TABLE timesheet_records ADD COLUMN city VARCHAR(255)')
                print("✅ 已添加city字段到timesheet_records表")
            else:
                print("ℹ️  timesheet_records表已存在city字段")
                
        except Exception as e:
            print(f"❌ 添加city字段失败: {e}")
        
        # 创建user_monthly_defaults表（如果不存在）
        try:
            pg_cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_monthly_defaults (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    business_trip_days INTEGER DEFAULT 1,
                    actual_visit_days INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, year, month)
                )
            ''')
            print("✅ 已创建user_monthly_defaults表")
        except Exception as e:
            print(f"❌ 创建user_monthly_defaults表失败: {e}")
        
        # 提交所有更改
        pg_conn.commit()
        
        print("✅ 生产环境数据库升级完成！")
        print("📋 现在可以重新部署应用程序")
        return True
        
    except Exception as e:
        print(f"❌ 升级失败: {e}")
        if 'pg_conn' in locals():
            pg_conn.rollback()
        return False
    finally:
        if 'pg_conn' in locals():
            pg_conn.close()

def show_current_schema():
    """显示当前数据库结构"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ 未找到DATABASE_URL环境变量")
        return
    
    try:
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_cursor = pg_conn.cursor()
        
        # 显示users表结构
        print("\n📋 当前users表结构:")
        pg_cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name='users'
            ORDER BY ordinal_position
        """)
        for row in pg_cursor.fetchall():
            print(f"  - {row[0]} ({row[1]}) {'NULL' if row[2]=='YES' else 'NOT NULL'} {f'DEFAULT {row[3]}' if row[3] else ''}")
        
        # 显示timesheet_records表结构
        print("\n📋 当前timesheet_records表结构:")
        pg_cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name='timesheet_records'
            ORDER BY ordinal_position
        """)
        for row in pg_cursor.fetchall():
            print(f"  - {row[0]} ({row[1]}) {'NULL' if row[2]=='YES' else 'NOT NULL'}")
            
        # 显示用户数据
        print("\n👥 当前用户数据:")
        pg_cursor.execute("SELECT id, username, name, role, department, phone FROM users ORDER BY id")
        users = pg_cursor.fetchall()
        for user in users:
            print(f"  - ID:{user[0]} {user[1]}({user[2]}) {user[3]} {user[4] or '无部门'} {user[5] or '无手机'}")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        if 'pg_conn' in locals():
            pg_conn.close()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--show':
        show_current_schema()
    else:
        success = upgrade_production_database()
        if success:
            print("\n🎉 升级成功！接下来请：")
            print("1. 重新部署应用到Railway")
            print("2. 检查新用户注册功能是否正常")
            print("3. 验证管理员页面能否看到所有用户")
        exit(0 if success else 1)
