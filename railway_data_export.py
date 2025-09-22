#!/usr/bin/env python3
"""
Railway数据导出脚本
在Railway环境中运行，导出所有数据到SQL文件
"""

import os
import json
from database_config import get_db_connection
from datetime import datetime

def export_railway_data():
    """导出Railway上的所有数据"""
    
    # 检查是否在Railway环境
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    if not DATABASE_URL:
        print("❌ 未检测到Railway数据库连接")
        return False
    
    print("🚀 开始导出Railway数据...")
    
    try:
        with get_db_connection() as db:
            # 导出用户数据
            print("📊 导出用户数据...")
            users = db.execute('SELECT * FROM users ORDER BY id').fetchall()
            users_data = []
            for user in users:
                users_data.append(dict(user))
            
            # 导出工时记录
            print("📊 导出工时记录...")
            records = db.execute('SELECT * FROM timesheet_records ORDER BY id').fetchall()
            records_data = []
            for record in records:
                records_data.append(dict(record))
            
            # 导出月度默认设置（如果表存在）
            defaults_data = []
            try:
                defaults = db.execute('SELECT * FROM user_monthly_defaults ORDER BY user_id, year, month').fetchall()
                for default in defaults:
                    defaults_data.append(dict(default))
                print("📊 导出月度默认设置...")
            except:
                print("⚠️  月度默认设置表不存在，跳过")
            
            # 创建导出数据结构
            export_data = {
                'export_time': datetime.now().isoformat(),
                'database_url': DATABASE_URL[:50] + '...',  # 只显示部分URL
                'users_count': len(users_data),
                'records_count': len(records_data),
                'defaults_count': len(defaults_data),
                'users': users_data,
                'timesheet_records': records_data,
                'user_monthly_defaults': defaults_data
            }
            
            # 保存到JSON文件
            filename = f'railway_data_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            # 生成SQL导入脚本
            sql_filename = f'railway_data_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
            generate_sql_import(export_data, sql_filename)
            
            print(f"✅ 数据导出完成！")
            print(f"📄 JSON文件: {filename}")
            print(f"📄 SQL文件: {sql_filename}")
            print(f"👥 用户数据: {len(users_data)} 条")
            print(f"📊 工时记录: {len(records_data)} 条")
            print(f"⚙️  默认设置: {len(defaults_data)} 条")
            
            return True
            
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return False

def generate_sql_import(data, filename):
    """生成SQL导入脚本"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("-- Railway数据导入脚本\n")
        f.write(f"-- 生成时间: {data['export_time']}\n")
        f.write(f"-- 用户数量: {data['users_count']}\n")
        f.write(f"-- 记录数量: {data['records_count']}\n\n")
        
        # 禁用外键检查
        f.write("SET session_replication_role = replica;\n\n")
        
        # 清空现有数据
        f.write("-- 清空现有数据\n")
        f.write("TRUNCATE TABLE timesheet_records RESTART IDENTITY CASCADE;\n")
        f.write("TRUNCATE TABLE user_monthly_defaults RESTART IDENTITY CASCADE;\n")
        f.write("TRUNCATE TABLE users RESTART IDENTITY CASCADE;\n\n")
        
        # 导入用户数据
        f.write("-- 导入用户数据\n")
        for user in data['users']:
            f.write(f"INSERT INTO users (id, username, password, name, role, department, phone, created_at) VALUES (")
            f.write(f"{user['id']}, ")
            f.write(f"'{user['username']}', ")
            f.write(f"'{user['password']}', ")
            f.write(f"'{user['name']}', ")
            f.write(f"'{user['role']}', ")
            f.write(f"'{user.get('department', '')}', ")
            f.write(f"'{user.get('phone', '')}', ")
            f.write(f"'{user['created_at']}'")
            f.write(");\n")
        
        f.write("\n-- 重置用户ID序列\n")
        f.write(f"SELECT setval('users_id_seq', {max(u['id'] for u in data['users']) if data['users'] else 1});\n\n")
        
        # 导入工时记录
        if data['timesheet_records']:
            f.write("-- 导入工时记录\n")
            for record in data['timesheet_records']:
                f.write("INSERT INTO timesheet_records (")
                f.write("id, user_id, work_date, business_trip_days, actual_visit_days, ")
                f.write("audit_store_count, training_store_count, start_location, end_location, ")
                f.write("round_trip_distance, transport_mode, schedule_number, travel_hours, ")
                f.write("visit_hours, report_hours, total_work_hours, notes, store_code, city, created_at")
                f.write(") VALUES (")
                f.write(f"{record['id']}, ")
                f.write(f"{record['user_id']}, ")
                f.write(f"'{record['work_date']}', ")
                f.write(f"{record.get('business_trip_days', 1)}, ")
                f.write(f"{record.get('actual_visit_days', 1)}, ")
                f.write(f"{record['audit_store_count']}, ")
                f.write(f"{record.get('training_store_count', 0)}, ")
                f.write(f"'{record.get('start_location', '')}', ")
                f.write(f"'{record.get('end_location', '')}', ")
                f.write(f"{record.get('round_trip_distance', 0)}, ")
                f.write(f"'{record.get('transport_mode', 'driving')}', ")
                f.write(f"'{record.get('schedule_number', '')}', ")
                f.write(f"{record.get('travel_hours', 0)}, ")
                f.write(f"{record.get('visit_hours', 0)}, ")
                f.write(f"{record.get('report_hours', 0)}, ")
                f.write(f"{record.get('total_work_hours', 0)}, ")
                f.write(f"'{record.get('notes', '')}', ")
                f.write(f"'{record.get('store_code', '')}', ")
                f.write(f"'{record.get('city', '')}', ")
                f.write(f"'{record['created_at']}'")
                f.write(");\n")
            
            f.write("\n-- 重置工时记录ID序列\n")
            f.write(f"SELECT setval('timesheet_records_id_seq', {max(r['id'] for r in data['timesheet_records'])});\n\n")
        
        # 导入月度默认设置
        if data['user_monthly_defaults']:
            f.write("-- 导入月度默认设置\n")
            for default in data['user_monthly_defaults']:
                f.write("INSERT INTO user_monthly_defaults (")
                f.write("user_id, year, month, business_trip_days, actual_visit_days, updated_at")
                f.write(") VALUES (")
                f.write(f"{default['user_id']}, ")
                f.write(f"{default['year']}, ")
                f.write(f"{default['month']}, ")
                f.write(f"{default['business_trip_days']}, ")
                f.write(f"{default['actual_visit_days']}, ")
                f.write(f"'{default['updated_at']}'")
                f.write(");\n")
        
        # 恢复外键检查
        f.write("\n-- 恢复外键检查\n")
        f.write("SET session_replication_role = DEFAULT;\n")
        
        f.write("\n-- 导入完成\n")

if __name__ == '__main__':
    print("🚀 Railway数据导出工具")
    print("=" * 50)
    
    success = export_railway_data()
    
    if success:
        print("\n✅ 导出成功！")
        print("📝 请下载生成的文件到本地，然后上传到阿里云服务器")
        print("📁 文件包含完整的数据备份和SQL导入脚本")
    else:
        print("\n❌ 导出失败！请检查错误信息")