#!/usr/bin/env python3
"""
数据库配置模块 - 支持SQLite和PostgreSQL
根据环境变量自动选择数据库类型
"""

import os
import sqlite3
from contextlib import contextmanager
import logging

try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None

logger = logging.getLogger(__name__)

# 数据库类型检测
DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_POSTGRESQL = (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://')) and PSYCOPG2_AVAILABLE

@contextmanager
def get_db_connection(timeout=30):
    """
    数据库连接上下文管理器
    自动检测并使用SQLite或PostgreSQL
    """
    conn = None
    try:
        if USE_POSTGRESQL and PSYCOPG2_AVAILABLE:
            # PostgreSQL连接
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            yield conn
        else:
            # SQLite连接（默认）
            conn = sqlite3.connect('timesheet.db', timeout=timeout)
            conn.row_factory = sqlite3.Row
            # 设置WAL模式提高并发性能
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            conn.execute('PRAGMA temp_store=memory')
            yield conn
            
    except Exception as e:
        logger.error(f"数据库错误: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def init_database():
    """初始化数据库表结构"""
    
    if USE_POSTGRESQL and PSYCOPG2_AVAILABLE:
        init_postgresql()
    else:
        init_sqlite()

def init_postgresql():
    """初始化PostgreSQL数据库"""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
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
        
        # 检查并添加新字段（兼容现有数据库）
        try:
            # 检查users表是否有phone字段
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='phone'
            """)
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT \'\'')
                logger.info("PostgreSQL: 添加用户表phone字段")
            
            # 检查timesheet_records表是否有store_code和city字段
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='timesheet_records' AND column_name='store_code'
            """)
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE timesheet_records ADD COLUMN store_code VARCHAR(255)')
                logger.info("PostgreSQL: 添加store_code字段")
                
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='timesheet_records' AND column_name='city'
            """)
            if not cursor.fetchone():
                cursor.execute('ALTER TABLE timesheet_records ADD COLUMN city VARCHAR(255)')
                logger.info("PostgreSQL: 添加city字段")
                
        except Exception as e:
            logger.error(f"PostgreSQL添加新字段时出错: {e}")
        
        conn.commit()
        logger.info("PostgreSQL数据库初始化完成")

def init_sqlite():
    """初始化SQLite数据库"""
    
    with get_db_connection() as db:
        # 创建用户表
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'specialist',
                department TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建工时记录表
        db.execute('''
            CREATE TABLE IF NOT EXISTS timesheet_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                work_date DATE NOT NULL,
                business_trip_days INTEGER DEFAULT 1,
                actual_visit_days INTEGER DEFAULT 1,
                audit_store_count INTEGER NOT NULL,
                training_store_count INTEGER DEFAULT 0,
                start_location TEXT,
                end_location TEXT,
                round_trip_distance REAL DEFAULT 0,
                transport_mode TEXT DEFAULT 'driving',
                schedule_number TEXT,
                travel_hours REAL DEFAULT 0,
                visit_hours REAL DEFAULT 0.92,
                report_hours REAL DEFAULT 0.13,
                total_work_hours REAL DEFAULT 0,
                notes TEXT,
                store_code TEXT,
                city TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        db.commit()
        logger.info("SQLite数据库初始化完成")

def get_database_info():
    """获取当前数据库信息"""
    if USE_POSTGRESQL and PSYCOPG2_AVAILABLE:
        return {
            'type': 'PostgreSQL',
            'url': DATABASE_URL[:50] + '...' if len(DATABASE_URL) > 50 else DATABASE_URL,
            'features': ['高并发', '自动备份', '高可用性']
        }
    else:
        return {
            'type': 'SQLite',
            'file': 'timesheet.db',
            'features': ['轻量级', '无服务器', '简单部署']
        }


