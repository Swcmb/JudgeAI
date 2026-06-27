"""
算法竞赛团队AI评分系统 - 快速启动脚本
一键体验所有扩展功能
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('quick_start.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print(f"   当前版本: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖包"""
    logger = logging.getLogger(__name__)
    
    required_packages = [
        'flask', 'pandas', 'openai', 'openpyxl', 'requests', 
        'werkzeug', 'matplotlib', 'seaborn', 'plotly', 'numpy',
        'pyjwt', 'cryptography', 'python-dateutil'
    ]
    
    missing_packages = []
    installed_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            installed_packages.append(package)
        except ImportError:
            missing_packages.append(package)
    
    if installed_packages:
        print(f"✅ 已安装依赖: {len(installed_packages)}/{len(required_packages)}")
        for pkg in installed_packages[:5]:  # 只显示前5个
            print(f"   - {pkg}")
        if len(installed_packages) > 5:
            print(f"   - ...还有{len(installed_packages)-5}个")
    
    if missing_packages:
        print(f"❌ 缺少依赖: {len(missing_packages)}个")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        
        print("\n📦 正在安装缺少的依赖...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install"
            ] + missing_packages)
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            return False
    
    return True

def check_api_key():
    """检查API密钥"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print(f"✅ API密钥: 已设置 ({api_key[:8]}...{api_key[-4:]})")
        return True
    else:
        print("⚠️  API密钥: 未设置")
        print("   评分功能将不可用，其他功能正常")
        print("   设置方法: export DASHSCOPE_API_KEY=\"your_api_key\"")
        return False

def create_directories():
    """创建必要目录"""
    directories = [
        'uploads', 'downloads', 'charts', 'reports', 'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print(f"✅ 目录结构已创建")

def display_menu():
    """显示功能菜单"""
    print("\n" + "="*60)
    print("🚀 算法竞赛团队AI评分系统 - 功能选择")
    print("="*60)
    print("1. 🔌 启动API服务器 (推荐)")
    print("2. 📊 运行数据可视化示例")
    print("3. 📥 测试批量导入功能")
    print("4. 📈 测试历史记录管理")
    print("5. 🤖 测试多模型支持")
    print("6. ⚙️ 测试配置管理系统")
    print("7. 👥 测试用户权限系统")
    print("8. 📋 查看系统状态")
    print("9. 📚 查看使用文档")
    print("0. 🚪 退出")
    print("="*60)

def run_api_server():
    """启动API服务器"""
    print("\n🔌 正在启动API服务器...")
    print("   API地址: http://localhost:5000/api")
    print("   按 Ctrl+C 停止服务")
    
    try:
        from api_gateway import app
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 API服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        input("按回车键继续...")

def test_visualization():
    """测试数据可视化"""
    print("\n📊 正在测试数据可视化...")
    
    try:
        # 先创建测试数据
        from result_processor import ResultProcessor
        import json
        
        # 创建模拟数据
        test_results = []
        for i in range(20):
            test_results.append({
                '学生信息': {
                    'id': f'student_{i+1:03d}',
                    'name': f'学生{i+1}',
                    'content': f'这是学生{i+1}的介绍信息...'
                },
                '学习态度': {'分数': 15 + (i % 10), '理由': '学习态度良好'},
                '自学能力': {'分数': 18 + (i % 8), '理由': '自学能力强'},
                '算法基础': {'分数': 12 + (i % 15), '理由': '算法基础一般'},
                '团队合作能力': {'分数': 20 + (i % 6), '理由': '团队合作优秀'},
                '总分': 65 + (i % 30),
                '综合评价': f'学生{i+1}的综合评价'
            })
        
        # 保存测试数据
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump({'results': test_results}, f, ensure_ascii=False, indent=2)
        
        # 测试可视化
        from visualization_enhanced import EnhancedVisualization
        viz = EnhancedVisualization()
        
        viz.create_comprehensive_dashboard(test_results, 'quick_start_dashboard.png')
        print("✅ 生成综合仪表板: quick_start_dashboard.png")
        
        viz.export_detailed_report(test_results, 'quick_start_report.html')
        print("✅ 生成详细报告: quick_start_report.html")
        
        print("🎉 可视化测试完成！")
        
    except Exception as e:
        print(f"❌ 可视化测试失败: {e}")
    
    input("按回车键继续...")

def test_batch_import():
    """测试批量导入"""
    print("\n📥 正在测试批量导入...")
    
    try:
        from batch_import import BatchImporter
        
        # 创建测试数据文件
        import pandas as pd
        
        test_data = pd.DataFrame({
            '学号': [f'{i+1:04d}' for i in range(5)],
            '姓名': [f'测试学生{i+1}' for i in range(5)],
            '个人介绍': [f'这是测试学生{i+1}的个人信息...' for i in range(5)]
        })
        
        test_file = 'test_students.csv'
        test_data.to_csv(test_file, index=False, encoding='utf-8-sig')
        
        # 测试导入
        importer = BatchImporter()
        result = importer.import_file(test_file)
        
        if result['success']:
            print(f"✅ 批量导入成功: 导入{result['student_count']}名学生")
        else:
            print(f"❌ 批量导入失败: {result['error']}")
        
        # 清理测试文件
        os.remove(test_file)
        
    except Exception as e:
        print(f"❌ 批量导入测试失败: {e}")
    
    input("按回车键继续...")

def test_history_manager():
    """测试历史记录管理"""
    print("\n📈 正在测试历史记录管理...")
    
    try:
        from history_manager import HistoryManager
        
        manager = HistoryManager()
        
        # 创建测试结果
        test_result = {
            '学生信息': {'id': 'test_001', 'name': '测试学生'},
            '总分': 85,
            '学习态度': {'分数': 22, '理由': '学习态度积极'},
            '自学能力': {'分数': 20, '理由': '自学能力较强'},
            '算法基础': {'分数': 18, '理由': '算法基础良好'},
            '团队合作能力': {'分数': 25, '理由': '团队合作优秀'},
            '综合评价': '综合表现良好'
        }
        
        # 保存测试数据
        manager.save_scoring_result(test_result, 'test_session')
        
        # 获取进度
        progress = manager.get_student_progress('test_001')
        if progress:
            print(f"✅ 历史记录测试成功:")
            print(f"   学生: {progress.student_name}")
            print(f"   最新分数: {progress.latest_score}")
            print(f"   改进趋势: {progress.improvement_trend:+.1f}")
        
    except Exception as e:
        print(f"❌ 历史记录测试失败: {e}")
    
    input("按回车键继续...")

def test_multi_model():
    """测试多模型支持"""
    print("\n🤖 正在测试多模型支持...")
    
    try:
        from multi_model_support import ModelManager
        
        manager = ModelManager()
        
        # 获取可用模型
        models = manager.get_available_models()
        print(f"✅ 可用模型数量: {len(models)}")
        
        for model in models:
            status = "✅" if model["available"] else "❌"
            print(f"   {status} {model['model_name']}: {model['description']}")
        
        if models and models[0]["available"]:
            # 测试评分
            test_student = {
                'id': 'test_001',
                'name': '测试学生',
                'content': '我对算法竞赛非常感兴趣...'
            }
            
            model_name = models[0]['model_name']
            model = manager.get_model(model_name)
            
            if model:
                print(f"\n🧠 使用模型 {model_name} 进行评分测试...")
                # 注意：这里可能会因为没有API密钥而失败
                result = model.score_student(test_student)
                if not result.get('error'):
                    print(f"✅ 评分测试成功，总分: {result.get('总分', 0)}")
                else:
                    print(f"⚠️  评分测试失败: {result.get('error', '未知错误')}")
        
    except Exception as e:
        print(f"❌ 多模型测试失败: {e}")
    
    input("按回车键继续...")

def test_config_manager():
    """测试配置管理"""
    print("\n⚙️ 正在测试配置管理...")
    
    try:
        from config_manager import ConfigManager
        
        manager = ConfigManager()
        
        # 获取配置摘要
        summary = manager.get_config_summary()
        print(f"✅ 配置系统测试成功:")
        print(f"   系统名称: {summary.get('system_name')}")
        print(f"   维度数量: {summary.get('dimension_count')}")
        print(f"   默认模型: {summary.get('default_model')}")
        
        # 验证配置
        validation = manager.validate_config()
        if validation['valid']:
            print("✅ 配置验证通过")
        else:
            print(f"❌ 配置验证失败:")
            for error in validation['errors']:
                print(f"   - {error}")
        
    except Exception as e:
        print(f"❌ 配置管理测试失败: {e}")
    
    input("按回车键继续...")

def test_user_management():
    """测试用户权限系统"""
    print("\n👥 正在测试用户权限系统...")
    
    try:
        from user_management import UserManagementSystem, UserRole
        
        user_system = UserManagementSystem()
        
        # 获取用户列表
        users = user_system.get_users()
        print(f"✅ 用户系统测试成功:")
        print(f"   用户数量: {len(users)}")
        
        for user in users:
            print(f"   - {user.username} ({user.role.value}): {'活跃' if user.is_active else '未激活'}")
        
        # 测试认证
        user, message = user_system.authenticate("admin", "admin123", "127.0.0.1")
        if user:
            print(f"✅ 管理员认证成功: {user.username}")
        else:
            print(f"❌ 管理员认证失败: {message}")
        
    except Exception as e:
        print(f"❌ 用户管理测试失败: {e}")
    
    input("按回车键继续...")

def show_system_status():
    """显示系统状态"""
    print("\n📋 系统状态检查:")
    print("-" * 40)
    
    # Python版本
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    # 系统路径
    print(f"工作目录: {os.getcwd()}")
    print(f"脚本位置: {os.path.abspath(__file__)}")
    
    # API密钥状态
    api_key = os.getenv("DASHSCOPE_API_KEY")
    print(f"API密钥: {'已设置' if api_key else '未设置'}")
    
    # 文件检查
    important_files = [
        'api_gateway.py',
        'batch_import.py', 
        'history_manager.py',
        'multi_model_support.py',
        'config_manager.py',
        'user_management.py'
    ]
    
    print("核心文件:")
    for file in important_files:
        status = "✅" if os.path.exists(file) else "❌"
        print(f"  {status} {file}")
    
    # 目录检查
    important_dirs = [
        'uploads',
        'downloads'
    ]
    
    print("重要目录:")
    for dir in important_dirs:
        status = "✅" if os.path.exists(dir) else "❌"
        print(f"  {status} {dir}/")
    
    print("-" * 40)

def show_documentation():
    """显示文档"""
    print("\n📚 系统文档:")
    print("-" * 40)
    
    docs = [
        ("README.md", "系统说明文档"),
        ("API_DOCUMENTATION.md", "API接口文档"),
        ("EXTENSION_GUIDE.md", "功能扩展完整指南")
    ]
    
    for doc, desc in docs:
        status = "✅" if os.path.exists(doc) else "❌"
        print(f"{status} {doc:<25} - {desc}")
    
    print("\n📖 推荐阅读顺序:")
    print("1. README.md - 了解基础功能")
    print("2. API_DOCUMENTATION.md - 学习API接口使用")
    print("3. EXTENSION_GUIDE.md - 掌握所有扩展功能")
    
    print("-" * 40)

def main():
    """主函数"""
    logger = setup_logging()
    
    print("🚀 算法竞赛团队AI评分系统 - 快速启动")
    print("=" * 60)
    
    # 环境检查
    print("🔍 正在检查运行环境...")
    
    if not check_python_version():
        input("按回车键退出...")
        return
    
    if not check_dependencies():
        input("按回车键退出...")
        return
    
    check_api_key()
    create_directories()
    
    print("✅ 环境检查完成！")
    
    # 主菜单
    while True:
        display_menu()
        
        try:
            choice = input("\n请选择功能 (0-9): ").strip()
            
            if choice == '0':
                print("👋 感谢使用，再见！")
                break
            elif choice == '1':
                run_api_server()
            elif choice == '2':
                test_visualization()
            elif choice == '3':
                test_batch_import()
            elif choice == '4':
                test_history_manager()
            elif choice == '5':
                test_multi_model()
            elif choice == '6':
                test_config_manager()
            elif choice == '7':
                test_user_management()
            elif choice == '8':
                show_system_status()
                input("按回车键继续...")
            elif choice == '9':
                show_documentation()
                input("按回车键继续...")
            else:
                print("❌ 无效选择，请输入0-9之间的数字")
                input("按回车键继续...")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            logger.error(f"运行出错: {e}")
            print(f"❌ 运行出错: {e}")
            input("按回车键继续...")

if __name__ == "__main__":
    main()