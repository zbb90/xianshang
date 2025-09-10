#!/usr/bin/env python3
import sqlite3
import bcrypt

# 测试密码验证
def test_password(username, test_password):
    db = sqlite3.connect('timesheet.db')
    user = db.execute('SELECT username, password FROM users WHERE username = ?', (username,)).fetchone()
    db.close()
    
    if user:
        stored_password = user[1]
        print(f"用户: {user[0]}")
        print(f"存储的密码长度: {len(stored_password)}")
        print(f"存储的密码前缀: {stored_password[:20]}...")
        
        # 测试密码验证
        try:
            if isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')
            
            result = bcrypt.checkpw(test_password.encode('utf-8'), stored_password)
            print(f"密码验证结果: {result}")
            return result
        except Exception as e:
            print(f"密码验证出错: {e}")
            return False
    else:
        print(f"用户 {username} 不存在")
        return False

# 测试专员账号
print("=== 测试专员账号 ===")
test_password('zhaohong', '123456')

print("\n=== 测试管理员账号 ===")
test_password('admin', 'admin123')

# 重新创建测试用户
print("\n=== 重新创建测试密码 ===")
new_password = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt())
print(f"新密码哈希: {new_password}")

# 测试新密码
result = bcrypt.checkpw('123456'.encode('utf-8'), new_password)
print(f"新密码验证: {result}")
