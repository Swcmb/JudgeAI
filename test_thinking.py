"""
测试启用思考功能的API调用
"""

import os
import json
import logging
from api_client import BaiLianAPIClient

def test_thinking_api():
    """测试思考功能"""
    logging.basicConfig(level=logging.INFO)
    
    # 检查API密钥
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("请先设置环境变量 DASHSCOPE_API_KEY")
        print("Windows PowerShell: $env:DASHSCOPE_API_KEY=\"your_api_key\"")
        return
    
    # 测试学生数据
    test_student = {
        'id': '001',
        'name': '张三',
        'content': '我对算法竞赛非常感兴趣，从大一开始就自学各种算法知识。参加过ACM竞赛，获得过区域赛银牌。平时喜欢在LeetCode上刷题，已经完成了500+题目。在团队项目中担任技术负责人，能够很好地与队友协作完成复杂的算法实现。'
    }
    
    try:
        print("=" * 50)
        print("测试启用思考功能的AI评分系统")
        print("=" * 50)
        
        # 初始化客户端
        client = BaiLianAPIClient()
        
        print(f"正在为学生 {test_student['name']} 进行AI评分...")
        print("注意：启用思考功能后，AI会先进行深度思考，然后给出评分结果")
        print("-" * 50)
        
        # 调用API评分
        result = client.score_student(test_student)
        
        print("\n" + "=" * 50)
        print("评分结果:")
        print("=" * 50)
        
        # 显示思考过程（如果有）
        if 'AI思考过程' in result:
            print("\n🧠 AI思考过程:")
            print("-" * 30)
            print(result['AI思考过程'][:500] + "..." if len(result['AI思考过程']) > 500 else result['AI思考过程'])
        
        # 显示评分结果
        print(f"\n📊 评分结果:")
        print(f"学生: {result.get('学生信息', {}).get('name', 'Unknown')}")
        print(f"总分: {result.get('总分', 0)}")
        
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        for dim in dimensions:
            dim_data = result.get(dim, {})
            if isinstance(dim_data, dict):
                print(f"{dim}: {dim_data.get('分数', 0)}分 - {dim_data.get('理由', '')}")
        
        print(f"\n💭 综合评价:")
        print(result.get('综合评价', ''))
        
        # 保存详细结果
        with open('test_thinking_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 详细结果已保存到: test_thinking_result.json")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        print("请检查:")
        print("1. API密钥是否正确设置")
        print("2. 网络连接是否正常")
        print("3. API服务是否可用")

if __name__ == "__main__":
    test_thinking_api()