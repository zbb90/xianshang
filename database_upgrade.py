#!/usr/bin/env python3
"""
数据库升级脚本：从SQLite迁移到PostgreSQL
使用方法：python database_upgrade.py
"""

import os
import sqlite3
import psycopg2
from datetime import datetime

def migrate_sqlite_to_postgresql():
    """将SQLite数据迁移到PostgreSQL"""
    
    # PostgreSQL连接配置（来自Railway环境变量）
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ 未找到DATABASE_URL环境变量")
        return False
    
    print("🔄 开始数据库迁移...")
    
    try:
        # 连接SQLite
        sqlite_conn = sqlite3.connect('timesheet.db')
        sqlite_conn.row_factory = sqlite3.Row
        
        # 连接PostgreSQL
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_cursor = pg_conn.cursor()
        
        # 创建PostgreSQL表结构
        create_postgres_tables(pg_cursor)
        
        # 迁移用户数据
        migrate_users(sqlite_conn, pg_cursor)
        
        # 迁移工时记录数据
        migrate_timesheet_records(sqlite_conn, pg_cursor)
        
        # 提交事务
        pg_conn.commit()
        
        print("✅ 数据库迁移完成！")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_conn.close()

def create_postgres_tables(cursor):
    """创建PostgreSQL表结构"""
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'specialist',
            department VARCHAR(255),
            phone VARCHAR(20) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建工时记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timesheet_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            work_date DATE NOT NULL,
            business_trip_days INTEGER DEFAULT 1,
            actual_visit_days INTEGER DEFAULT 1,
            audit_store_count INTEGER NOT NULL,
            training_store_count INTEGER DEFAULT 0,
            start_location TEXT,
            end_location TEXT,
            round_trip_distance REAL DEFAULT 0,
            transport_mode VARCHAR(50) DEFAULT 'driving',
            schedule_number VARCHAR(255),
            travel_hours REAL DEFAULT 0,
            visit_hours REAL DEFAULT 0.92,
            report_hours REAL DEFAULT 0.13,
            total_work_hours REAL DEFAULT 0,
            notes TEXT,
            store_code VARCHAR(255),
            city VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    print("📋 PostgreSQL表结构创建完成")

def migrate_users(sqlite_conn, pg_cursor):
    """迁移用户数据"""
    users = sqlite_conn.execute('SELECT * FROM users').fetchall()
    
    for user in users:
        # 获取phone字段，如果不存在则使用空字符串
        phone = user.get('phone', '') if 'phone' in user.keys() else ''
        
        pg_cursor.execute('''
            INSERT INTO users (username, password, name, role, department, phone, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        ''', (user['username'], user['password'], user['name'], 
              user['role'], user['department'], phone, user['created_at']))
    
    print(f"👥 迁移了 {len(users)} 个用户")

def migrate_timesheet_records(sqlite_conn, pg_cursor):
    """迁移工时记录数据"""
    records = sqlite_conn.execute('SELECT * FROM timesheet_records').fetchall()
    
    for record in records:
        pg_cursor.execute('''
            INSERT INTO timesheet_records (
                user_id, work_date, business_trip_days, actual_visit_days,
                audit_store_count, training_store_count, start_location, end_location,
                round_trip_distance, transport_mode, schedule_number,
                travel_hours, visit_hours, report_hours, total_work_hours,
                notes, store_code, city, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            record['user_id'], record['work_date'], record['business_trip_days'],
            record['actual_visit_days'], record['audit_store_count'], 
            record['training_store_count'], record['start_location'], record['end_location'],
            record['round_trip_distance'], record['transport_mode'], record['schedule_number'],
            record['travel_hours'], record['visit_hours'], record['report_hours'],
            record['total_work_hours'], record['notes'], record['store_code'],
            record['city'], record['created_at']
        ))
    
    print(f"📊 迁移了 {len(records)} 条工时记录")

if __name__ == '__main__':
    success = migrate_sqlite_to_postgresql()
    exit(0 if success else 1)


