#!/usr/bin/env python3
"""
生产环境数据恢复脚本
将本地数据安全地迁移到生产环境，不会覆盖已有数据
"""
import json
import sys
import os
from database_config import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_backup_data():
    """加载备份数据"""
    try:
        with open('data_backup.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("备份文件 data_backup.json 不存在")
        return None
    except Exception as e:
        logger.error(f"加载备份数据失败: {e}")
        return None

def restore_users(db, users_data):
    """恢复用户数据（不覆盖已存在的用户）"""
    restored_count = 0
    for user in users_data:
        try:
            # 检查用户是否已存在
            existing = db.execute(
                'SELECT id FROM users WHERE username = ?', 
                (user['username'],)
            ).fetchone()
            
            if existing:
                logger.info(f"用户 {user['username']} 已存在，跳过")
                continue
            
            # 插入新用户
            db.execute('''
                INSERT INTO users (username, password, name, role, department, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['username'], user['password'], user['name'], 
                user['role'], user.get('department', ''), 
                user.get('phone', ''), user['created_at']
            ))
            restored_count += 1
            logger.info(f"恢复用户: {user['username']} ({user['name']})")
            
        except Exception as e:
            logger.error(f"恢复用户 {user['username']} 失败: {e}")
    
    return restored_count

def restore_timesheet_records(db, records_data):
    """恢复工时记录"""
    restored_count = 0
    for record in records_data:
        try:
            # 检查用户是否存在
            user = db.execute(
                'SELECT id FROM users WHERE id = ?', 
                (record['user_id'],)
            ).fetchone()
            
            if not user:
                logger.warning(f"工时记录的用户ID {record['user_id']} 不存在，跳过此记录")
                continue
            
            # 检查是否已有相同的记录（基于用户、日期和创建时间）
            existing = db.execute('''
                SELECT id FROM timesheet_records 
                WHERE user_id = ? AND work_date = ? AND created_at = ?
            ''', (record['user_id'], record['work_date'], record['created_at'])).fetchone()
            
            if existing:
                logger.info(f"工时记录已存在 (用户ID: {record['user_id']}, 日期: {record['work_date']})，跳过")
                continue
            
            # 插入工时记录
            db.execute('''
                INSERT INTO timesheet_records (
                    user_id, work_date, business_trip_days, actual_visit_days,
                    audit_store_count, training_store_count, start_location, end_location,
                    round_trip_distance, transport_mode, schedule_number,
                    travel_hours, visit_hours, report_hours, total_work_hours,
                    notes, store_code, city, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record['user_id'], record['work_date'], record['business_trip_days'],
                record['actual_visit_days'], record['audit_store_count'], 
                record.get('training_store_count', 0), record.get('start_location', ''),
                record.get('end_location', ''), record.get('round_trip_distance', 0),
                record.get('transport_mode', 'driving'), record.get('schedule_number', ''),
                record.get('travel_hours', 0), record.get('visit_hours', 0),
                record.get('report_hours', 0), record.get('total_work_hours', 0),
                record.get('notes', ''), record.get('store_code', ''),
                record.get('city', ''), record['created_at']
            ))
            restored_count += 1
            logger.info(f"恢复工时记录: 用户ID {record['user_id']}, 日期 {record['work_date']}")
            
        except Exception as e:
            logger.error(f"恢复工时记录失败: {e}")
    
    return restored_count

def main():
    """主恢复函数"""
    logger.info("开始数据恢复过程...")
    
    # 加载备份数据
    backup_data = load_backup_data()
    if not backup_data:
        logger.error("无法加载备份数据，退出")
        return False
    
    logger.info(f"备份数据包含: {len(backup_data['users'])} 个用户, {len(backup_data['timesheet_records'])} 条工时记录")
    
    try:
        with get_db_connection() as db:
            # 开始事务
            db.execute('BEGIN TRANSACTION')
            
            # 恢复用户
            users_restored = restore_users(db, backup_data['users'])
            logger.info(f"恢复了 {users_restored} 个用户")
            
            # 恢复工时记录
            records_restored = restore_timesheet_records(db, backup_data['timesheet_records'])
            logger.info(f"恢复了 {records_restored} 条工时记录")
            
            # 提交事务
            db.commit()
            
            logger.info("✅ 数据恢复完成！")
            logger.info(f"总共恢复: {users_restored} 个用户, {records_restored} 条工时记录")
            
            # 验证恢复结果
            total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            total_records = db.execute('SELECT COUNT(*) FROM timesheet_records').fetchone()[0]
            logger.info(f"数据库当前状态: {total_users} 个用户, {total_records} 条工时记录")
            
            return True
            
    except Exception as e:
        logger.error(f"数据恢复失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("🎉 数据恢复成功！")
        exit(0)
    else:
        print("❌ 数据恢复失败！")
        exit(1)
