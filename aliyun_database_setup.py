#!/usr/bin/env python3
"""
阿里云数据库初始化脚本
"""

import os
import psycopg2
from database_config import init_database

def setup_aliyun_database():
    """设置阿里云数据库"""
    
    print("🔧 开始配置阿里云数据库...")
    
    # 设置环境变量（替换为您的实际RDS连接信息）
    os.environ['DATABASE_URL'] = 'postgresql://username:password@rds-host:5432/database_name'
    
    try:
        # 初始化数据库表结构
        print("📋 创建数据库表结构...")
        init_database()
        
        # 创建月度默认设置表（如果不存在）
        print("📋 创建月度默认设置表...")
        create_monthly_defaults_table()
        
        print("✅ 阿里云数据库配置完成！")
        return True
        
    except Exception as e:
        print(f"❌ 数据库配置失败: {e}")
        return False

def create_monthly_defaults_table():
    """创建月度默认设置表"""
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("未找到数据库连接URL")
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_monthly_defaults (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                business_trip_days INTEGER DEFAULT 1,
                actual_visit_days INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year, month),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        print("✅ 月度默认设置表创建成功")
        
    except Exception as e:
        print(f"⚠️  月度默认设置表创建失败: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("🚀 阿里云数据库初始化工具")
    print("=" * 50)
    print("请先修改DATABASE_URL为您的阿里云RDS连接信息")
    print("格式: postgresql://username:password@rds-host:5432/database_name")
    print()
    
    # 检查是否设置了DATABASE_URL
    if input("是否已配置DATABASE_URL? (y/N): ").lower().strip() == 'y':
        setup_aliyun_database()
    else:
        print("请先配置DATABASE_URL环境变量后再运行此脚本")