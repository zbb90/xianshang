#!/usr/bin/env python3
"""
数据迁移验证脚本
检查阿里云数据库中的数据是否完整
"""

import os
import json
from database_config import get_db_connection

def verify_migration(export_file_path):
    """验证数据迁移是否成功"""
    
    print("🔍 开始验证数据迁移...")
    
    # 读取原始导出数据
    try:
        with open(export_file_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取原始数据文件: {e}")
        return False
    
    print(f"📊 原始数据统计:")
    print(f"   用户数量: {original_data['users_count']}")
    print(f"   工时记录: {original_data['records_count']}")
    print(f"   默认设置: {original_data['defaults_count']}")
    
    try:
        with get_db_connection() as db:
            # 验证用户数据
            users_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            records_count = db.execute('SELECT COUNT(*) FROM timesheet_records').fetchone()[0]
            
            try:
                defaults_count = db.execute('SELECT COUNT(*) FROM user_monthly_defaults').fetchone()[0]
            except:
                defaults_count = 0
            
            print(f"\n🎯 阿里云数据统计:")
            print(f"   用户数量: {users_count}")
            print(f"   工时记录: {records_count}")
            print(f"   默认设置: {defaults_count}")
            
            # 数据对比
            users_match = users_count == original_data['users_count']
            records_match = records_count == original_data['records_count']
            defaults_match = defaults_count == original_data['defaults_count']
            
            print(f"\n✅ 验证结果:")
            print(f"   用户数据: {'✓ 匹配' if users_match else '✗ 不匹配'}")
            print(f"   工时记录: {'✓ 匹配' if records_match else '✗ 不匹配'}")
            print(f"   默认设置: {'✓ 匹配' if defaults_match else '✗ 不匹配'}")
            
            if users_match and records_match and defaults_match:
                print(f"\n🎉 数据迁移验证成功！所有数据完整迁移")
                
                # 额外检查：验证关键用户是否存在
                print(f"\n🔍 关键数据检查:")
                admin_exists = db.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'").fetchone()[0]
                print(f"   管理员账号: {'✓ 存在' if admin_exists > 0 else '✗ 缺失'}")
                
                # 检查最新的工时记录
                latest_record = db.execute('''
                    SELECT u.name, t.work_date, t.total_work_hours 
                    FROM timesheet_records t 
                    JOIN users u ON t.user_id = u.id 
                    ORDER BY t.created_at DESC 
                    LIMIT 1
                ''').fetchone()
                
                if latest_record:
                    print(f"   最新记录: {latest_record[0]} - {latest_record[1]} ({latest_record[2]}小时)")
                
                return True
            else:
                print(f"\n❌ 数据迁移验证失败！请检查数据导入过程")
                return False
                
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return False

def test_application():
    """测试应用程序基本功能"""
    
    print(f"\n🧪 测试应用程序功能...")
    
    try:
        # 测试数据库连接
        with get_db_connection() as db:
            # 测试用户查询
            users = db.execute('SELECT id, username, name, role FROM users LIMIT 5').fetchall()
            print(f"✓ 数据库连接正常，用户查询成功")
            
            for user in users:
                print(f"   {user[0]}: {user[1]} ({user[2]}) - {user[3]}")
            
            # 测试工时记录查询
            records = db.execute('''
                SELECT COUNT(*) as total,
                       MIN(work_date) as earliest,
                       MAX(work_date) as latest
                FROM timesheet_records
            ''').fetchone()
            
            if records[0] > 0:
                print(f"✓ 工时记录查询正常")
                print(f"   总记录数: {records[0]}")
                print(f"   时间范围: {records[1]} 到 {records[2]}")
            else:
                print(f"⚠️  暂无工时记录")
            
            return True
            
    except Exception as e:
        print(f"❌ 应用程序测试失败: {e}")
        return False

if __name__ == '__main__':
    print("🚀 数据迁移验证工具")
    print("=" * 50)
    
    # 查找导出文件
    import glob
    export_files = glob.glob('railway_data_export_*.json')
    
    if not export_files:
        print("❌ 未找到导出数据文件，请确保已上传 railway_data_export_*.json 文件")
        exit(1)
    
    # 使用最新的导出文件
    export_file = sorted(export_files)[-1]
    print(f"📄 使用导出文件: {export_file}")
    
    # 验证迁移
    if verify_migration(export_file):
        # 测试应用功能
        if test_application():
            print(f"\n🎉 迁移验证完成！系统已准备就绪")
        else:
            print(f"\n⚠️  数据迁移成功，但应用测试有问题")
    else:
        print(f"\n❌ 迁移验证失败！请检查数据导入过程")