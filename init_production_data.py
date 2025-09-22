#!/usr/bin/env python3
"""
生产环境初始数据创建脚本
用于在Railway部署时自动创建基础用户和数据
"""

import os
import hashlib
from database_config import get_db_connection, init_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_default_users():
    """创建默认用户"""
    try:
        with get_db_connection() as db:
            # 检查是否已有用户
            existing_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            if existing_users > 0:
                logger.info(f"数据库已有 {existing_users} 个用户，跳过初始化")
                return True
            
            # 创建默认管理员
            admin_password = hashlib.sha256("admin123".encode()).hexdigest()
            db.execute('''
                INSERT OR IGNORE INTO users (username, password, name, role, department, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', ('admin', admin_password, '管理员', 'admin', '管理部', '', ))
            
            # 创建测试用户
            user_password = hashlib.sha256("123456".encode()).hexdigest()
            users_to_create = [
                ('zhaohong', '郑皓鸿', 'specialist', '稽核组'),
                ('赵彬彬', '赵彬彬', 'specialist', '稽核组'),
                ('冯志强', '冯志强', 'specialist', '稽核组')
            ]
            
            for username, name, role, department in users_to_create:
                db.execute('''
                    INSERT OR IGNORE INTO users (username, password, name, role, department, phone, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (username, user_password, name, role, department, ''))
            
            db.commit()
            
            # 验证创建结果
            total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            logger.info(f"✅ 初始用户创建完成，共 {total_users} 个用户")
            
            # 显示创建的用户
            users = db.execute('SELECT username, name, role FROM users').fetchall()
            for user in users:
                logger.info(f"  - {user[1]} ({user[0]}) - {user[2]}")
            
            return True
            
    except Exception as e:
        logger.error(f"创建默认用户失败: {e}")
        return False

def create_sample_timesheet_records():
    """创建示例工时记录（仅在完全空数据库时）"""
    try:
        with get_db_connection() as db:
            # 检查是否已有记录
            existing_records = db.execute('SELECT COUNT(*) FROM timesheet_records').fetchone()[0]
            if existing_records > 0:
                logger.info(f"数据库已有 {existing_records} 条工时记录，跳过示例数据创建")
                return True
            
            # 获取用户ID
            user = db.execute("SELECT id FROM users WHERE username = 'zhaohong'").fetchone()
            if not user:
                logger.info("没有找到zhaohong用户，跳过示例数据创建")
                return True
            
            user_id = user[0]
            
            # 创建示例工时记录
            sample_records = [
                ('2025-09-20', 1, 1, 3, '古茗奶茶店A', '古茗奶茶店C', 15.5, 'driving', 1.2, 2.76, 0.39, '门店巡查'),
                ('2025-09-21', 1, 1, 4, '古茗奶茶店B', '古茗奶茶店D', 18.2, 'driving', 1.4, 3.68, 0.52, '门店审核'),
                ('2025-09-22', 1, 1, 2, '古茗奶茶店E', '古茗奶茶店F', 12.3, 'driving', 0.9, 1.84, 0.26, '质量检查')
            ]
            
            for record in sample_records:
                work_date, trip_days, visit_days, store_count, start_loc, end_loc, distance, transport, travel_h, visit_h, report_h, notes = record
                total_hours = travel_h + visit_h + report_h
                
                db.execute('''
                    INSERT INTO timesheet_records (
                        user_id, work_date, business_trip_days, actual_visit_days,
                        audit_store_count, start_location, end_location, round_trip_distance,
                        transport_mode, travel_hours, visit_hours, report_hours,
                        total_work_hours, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (user_id, work_date, trip_days, visit_days, store_count, start_loc, 
                     end_loc, distance, transport, travel_h, visit_h, report_h, total_hours, notes))
            
            db.commit()
            
            total_records = db.execute('SELECT COUNT(*) FROM timesheet_records').fetchone()[0]
            logger.info(f"✅ 示例工时记录创建完成，共 {total_records} 条记录")
            
            return True
            
    except Exception as e:
        logger.error(f"创建示例工时记录失败: {e}")
        return False

def main():
    """主初始化函数"""
    logger.info("开始生产环境数据初始化...")
    
    try:
        # 初始化数据库表结构
        init_database()
        logger.info("✅ 数据库表结构初始化完成")
        
        # 创建默认用户
        if create_default_users():
            logger.info("✅ 默认用户创建完成")
        else:
            logger.error("❌ 默认用户创建失败")
            return False
        
        # 创建示例数据（仅在空数据库时）
        if create_sample_timesheet_records():
            logger.info("✅ 示例数据处理完成")
        else:
            logger.warning("⚠️  示例数据创建失败，但不影响基本功能")
        
        logger.info("🎉 生产环境数据初始化完成！")
        return True
        
    except Exception as e:
        logger.error(f"生产环境数据初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("🎉 生产环境初始化成功！")
    else:
        print("❌ 生产环境初始化失败！")
        exit(1)
