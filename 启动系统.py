#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工时表管理系统 - 启动脚本
一键启动完整功能的工时表管理系统
"""

import os
import sys
import subprocess
import platform

def check_requirements():
    """检查系统要求"""
    print("🔍 检查系统环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ Python版本需要3.7或以上")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查必需的库
    required_packages = ['flask', 'requests', 'openpyxl']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 缺失")
    
    if missing_packages:
        print(f"\n⚠️ 缺少必需的库: {', '.join(missing_packages)}")
        print("请运行: pip3 install " + " ".join(missing_packages))
        return False
    
    return True

def start_system():
    """启动系统"""
    print("\n🚀 启动智能工时表管理系统...")
    
    # 检查系统文件
    required_files = ['enhanced_final_app.py', 'config.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ 缺少必需文件: {file}")
            return False
    
    print("✅ 系统文件检查完成")
    
    # 启动Flask应用
    try:
        print("\n" + "="*50)
        print("🎯 智能工时表管理系统")
        print("📊 功能: 工时管理 + 门店管理 + 数据导出")
        print("🌐 访问地址: http://localhost:8080")
        print("=" * 50)
        
        # 启动应用
        subprocess.run([sys.executable, 'enhanced_final_app.py'], check=True)
        
    except KeyboardInterrupt:
        print("\n👋 系统已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True

def show_help():
    """显示帮助信息"""
    print("""
🎯 智能工时表管理系统 - 使用指南

📋 主要功能：
  ⏰ 工时管理 - 智能工时录入和路程计算
  🏪 门店管理 - 门店信息导入和管理  
  📊 数据导出 - Excel和JSON格式导出

🚀 快速开始：
  1. 运行启动脚本: python3 启动系统.py
  2. 打开浏览器访问: http://localhost:8080
  3. 在"门店管理"标签导入门店信息
  4. 在"工时管理"标签开始记录工时
  5. 在"数据导出"标签导出报表

📁 门店信息格式：
  CSV格式: 门店编码,门店名称,门店城市,经度,纬度,地址
  支持文件: CSV, Excel(.xlsx), JSON

🛠️ 系统要求：
  - Python 3.7+
  - Flask 3.0+
  - openpyxl (Excel支持)
  - requests (API调用)

📞 问题排查：
  - 如果端口被占用，请关闭其他应用
  - 如果导入失败，请检查文件格式
  - 如果API不可用，系统会自动降级

🎉 现在就开始使用您的智能工时表系统吧！
    """)

def main():
    """主函数"""
    print("🎯 智能工时表管理系统 - 启动脚本")
    print("版本: 增强最终版 | 作者: AI助手")
    print("-" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_help()
        return
    
    # 检查环境
    if not check_requirements():
        print("\n❌ 环境检查失败，请安装必需的依赖")
        sys.exit(1)
    
    # 启动系统
    if start_system():
        print("✅ 系统运行完成")
    else:
        print("❌ 系统启动失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
