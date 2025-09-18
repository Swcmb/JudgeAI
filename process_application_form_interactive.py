"""
处理ApplicationForm.xlsx真实数据的交互式脚本
将申请表数据转换为适合AI评分的格式，并提供用户选择功能
"""

import pandas as pd
import logging
from typing import List, Dict, Any
from file_reader import FileReader
from api_client import BaiLianAPIClient
from result_processor import ResultProcessor

class ApplicationFormProcessor:
    """申请表数据处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_application_form(self, excel_path: str = "ApplicationForm.xlsx") -> List[Dict[str, Any]]:
        """
        处理申请表Excel文件
        
        Args:
            excel_path: Excel文件路径
            
        Returns:
            处理后的学生信息列表
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(excel_path, sheet_name='Sheet1')
            self.logger.info(f"成功读取申请表数据，共 {len(df)} 条记录")
            
            students = []
            
            for index, row in df.iterrows():
                # 构建学生信息
                student_info = {
                    'id': str(row['序号']),
                    'name': f'学生{row["序号"]}',  # 由于没有姓名，使用序号
                    'content': self._build_content_from_row(row)
                }
                
                # 过滤掉内容为空的记录
                if student_info['content'].strip():
                    students.append(student_info)
                else:
                    self.logger.warning(f"学生{row['序号']}的信息为空，跳过")
            
            self.logger.info(f"处理完成，有效学生信息 {len(students)} 条")
            return students
            
        except Exception as e:
            self.logger.error(f"处理申请表失败: {e}")
            raise
    
    def _build_content_from_row(self, row) -> str:
        """
        从行数据构建学生内容描述
        
        Args:
            row: 数据行
            
        Returns:
            格式化的学生信息
        """
        content_parts = []
        
        # 个人优势
        advantages = str(row['9、个人优势']).strip()
        if advantages and advantages not in ['无', '(空)', 'nan', 'I']:
            content_parts.append(f"个人优势: {advantages}")
        
        # 未来规划
        future_plan = str(row['10、未来规划']).strip()
        if future_plan and future_plan not in ['无', '(空)', 'nan', 'I']:
            content_parts.append(f"未来规划: {future_plan}")
        
        # 其他信息
        other_info = str(row['11、其他']).strip()
        if other_info and other_info not in ['无', '(空)', 'nan', 'wu']:
            content_parts.append(f"其他信息: {other_info}")
        
        return "; ".join(content_parts)
    
    def create_enhanced_prompt(self, student_info: str) -> str:
        """
        为申请表数据创建增强的评分提示词
        
        Args:
            student_info: 学生信息
            
        Returns:
            格式化的提示词
        """
        prompt = f"""你是一位专业的算法竞赛团队选拔专家。请根据以下学生申请表信息，从四个维度对该学生进行评分：

学生申请信息：
{student_info}

评分维度及标准：
1. 学习态度（25分）：
   - 积极主动、有强烈的学习意愿和上进心，如提到主动学习新知识、参加培训课程等：20-25分
   - 学习态度一般，需要督促，但有一定学习意愿：10-19分
   - 态度消极、缺乏学习动力，表现出被动学习特征：0-9分

2. 自学能力（25分）：
   - 具备独立解决问题的能力、能够自主学习新的算法和技术，如描述了自学经历、解决难题的过程等：20-25分
   - 有一定自学能力但需要指导，能够在帮助下学习新知识：10-19分
   - 依赖他人指导较多，缺乏独立学习能力：0-9分

3. 算法基础（25分）：
   - 有一定的算法知识储备，熟悉常见的算法和数据结构，如提及相关课程学习、算法竞赛经历等：20-25分
   - 有一定编程基础但算法经验不足，了解基本概念：10-19分
   - 算法基础薄弱或零基础，但如果有强烈学习意愿可适当给分：0-9分

4. 团队合作能力（25分）：
   - 能够与他人有效合作、沟通顺畅，如分享了团队项目经验、协作成果等：20-25分
   - 有一定合作意识，能够参与团队活动：10-19分
   - 团队合作能力欠佳，更倾向于独立工作：0-9分

特别注意以下几点：
- 如果学生明确表示"编程0基础"但有强烈学习意愿，算法基础可给5-10分，学习态度可给较高分
- 如果学生有竞赛经验（如信息竞赛、编程猫等），算法基础应给较高分
- 考虑学生的未来规划是否与算法竞赛相关（如考研、进大厂等），相关规划可提高评分
- 从个人优势中判断学生的学习能力和态度，如"爱学习"、"动手能力强"等
- 重点关注学生的学习意愿和潜力，而不仅仅是当前的技术水平

请按照以下JSON格式返回评分结果：
{{
    "思考过程": "详细分析该学生在四个维度的表现，说明评分理由",
    "学习态度": {{
        "分数": 分数(0-25),
        "理由": "具体评分理由"
    }},
    "自学能力": {{
        "分数": 分数(0-25),
        "理由": "具体评分理由"
    }},
    "算法基础": {{
        "分数": 分数(0-25),
        "理由": "具体评分理由"
    }},
    "团队合作能力": {{
        "分数": 分数(0-25),
        "理由": "具体评分理由"
    }},
    "总分": 总分(0-100),
    "综合评价": "对该学生的综合评价和建议",
    "推荐等级": "强烈推荐/推荐/一般/不推荐"
}}

注意：请严格按照JSON格式返回，分数必须是整数，总分为四个维度分数之和。"""

        return prompt

    def get_user_choice(self, total_students: int) -> tuple:
        """
        获取用户选择
        
        Args:
            total_students: 总学生数
            
        Returns:
            (choice, sample_students_count) 元组
        """
        print(f"\n🤖 是否开始AI评分？")
        print("注意：需要设置DASHSCOPE_API_KEY环境变量")
        print("\n请选择:")
        print("1. 开始AI评分（处理前5个学生作为示例）")
        print(f"2. 开始AI评分（处理所有{total_students}个学生）")
        print("3. 仅查看数据，不进行评分")
        print("0. 退出程序")
        
        # 获取用户选择
        while True:
            try:
                choice = input("\n请输入选择 (0-3): ").strip()
                if choice in ['0', '1', '2', '3']:
                    break
                else:
                    print("❌ 无效选择，请输入 0-3")
            except KeyboardInterrupt:
                print("\n\n👋 用户取消操作")
                return ('0', 0)
        
        if choice == '0':
            print("👋 程序退出")
            return ('0', 0)
        elif choice == '3':
            print("📊 数据查看完成，程序退出")
            return ('3', 0)
        elif choice == '1':
            return ('1', 5)
        else:  # choice == '2'
            print(f"\n⚠️  这将处理{total_students}个学生，可能需要较长时间和API费用")
            confirm = input("确认继续？(y/N): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                return ('2', total_students)
            else:
                print("👋 用户取消操作")
                return ('0', 0)


def main():
    """主函数 - 处理真实申请表数据"""
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("=" * 60)
        print("算法竞赛团队申请表AI评分系统")
        print("=" * 60)
        
        # 初始化处理器
        processor = ApplicationFormProcessor()
        
        # 处理申请表数据
        print("正在处理申请表数据...")
        students = processor.process_application_form()
        
        if not students:
            print("❌ 没有找到有效的学生数据")
            return
        
        print(f"✅ 成功处理 {len(students)} 条学生申请信息")
        
        # 显示前几个学生的信息示例
        print("\n📋 学生信息示例:")
        for i, student in enumerate(students[:3]):
            print(f"\n学生{student['id']}:")
            print(f"  {student['content']}")
        
        # 获取用户选择
        choice, sample_count = processor.get_user_choice(len(students))
        
        if choice in ['0', '3']:
            return
        
        # 检查API密钥
        import os
        if not os.getenv("DASHSCOPE_API_KEY"):
            print("\n⚠️  未检测到API密钥，请先设置：")
            print("Windows PowerShell: $env:DASHSCOPE_API_KEY=\"your_api_key\"")
            print("Linux/Mac: export DASHSCOPE_API_KEY=your_api_key")
            return
        
        # 根据用户选择确定处理范围
        sample_students = students[:sample_count]
        print(f"\n🚀 开始AI评分（处理{len(sample_students)}个学生）...")
        
        api_client = BaiLianAPIClient()
        result_processor = ResultProcessor()
        
        # 临时修改API客户端的提示词创建方法
        original_method = api_client.create_scoring_prompt
        api_client.create_scoring_prompt = processor.create_enhanced_prompt
        
        results = []
        
        for i, student in enumerate(sample_students, 1):
            try:
                print(f"正在评分 ({i}/{len(sample_students)}): 学生{student['id']}")
                result = api_client.score_student(student)
                results.append(result)
                print(f"✅ 学生{student['id']} 评分完成")
            except Exception as e:
                print(f"❌ 学生{student['id']} 评分失败: {e}")
        
        # 保存结果
        if results:
            saved_files = result_processor.save_all_formats(results, "application_form_results")
            
            print(f"\n🎉 评分完成！生成的文件:")
            for format_type, file_path in saved_files.items():
                print(f"  {format_type.upper()}: {file_path}")
            
            print(f"\n📊 评分统计:")
            successful_count = len([r for r in results if not r.get('error', False)])
            print(f"  成功评分: {successful_count}/{len(sample_students)}")
            
            if successful_count > 0:
                total_scores = [r.get('总分', 0) for r in results if not r.get('error', False)]
                avg_score = sum(total_scores) / len(total_scores)
                print(f"  平均分: {avg_score:.1f}")
                print(f"  最高分: {max(total_scores)}")
                print(f"  最低分: {min(total_scores)}")
        
        if choice == '1':
            print(f"\n💡 提示：要处理所有{len(students)}个学生，请重新运行并选择选项2")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")

if __name__ == "__main__":
    main()