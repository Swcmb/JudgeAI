"""
算法竞赛团队AI评分系统主程序
命令行界面，支持批量处理学生信息并进行AI评分
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

from file_reader import FileReader
from api_client import BaiLianAPIClient
from result_processor import ResultProcessor


class TeamScoringSystem:
    """算法竞赛团队评分系统"""
    
    def __init__(self, api_key: str = None, log_level: str = "INFO"):
        """
        初始化评分系统
        
        Args:
            api_key: API密钥
            log_level: 日志级别
        """
        # 设置日志
        self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.file_reader = FileReader()
        self.api_client = BaiLianAPIClient(api_key)
        self.result_processor = ResultProcessor()
        
        self.logger.info("算法竞赛团队AI评分系统初始化完成")
    
    def _setup_logging(self, log_level: str):
        """设置日志配置"""
        level = getattr(logging, log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('scoring_system.log', encoding='utf-8')
            ]
        )
    
    def process_file(self, input_file: str, output_dir: str = "output") -> Dict[str, str]:
        """
        处理单个文件
        
        Args:
            input_file: 输入文件路径
            output_dir: 输出目录
            
        Returns:
            保存的文件路径字典
        """
        self.logger.info(f"开始处理文件: {input_file}")
        
        try:
            # 1. 读取文件
            self.logger.info("正在读取学生信息...")
            students = self.file_reader.read_file(input_file)
            validated_students = self.file_reader.validate_data(students)
            
            if not validated_students:
                raise ValueError("没有找到有效的学生信息")
            
            self.logger.info(f"成功读取 {len(validated_students)} 条学生信息")
            
            # 2. 批量评分
            self.logger.info("开始AI评分...")
            results = self._batch_score(validated_students)
            
            # 3. 保存结果
            self.logger.info("正在保存结果...")
            saved_files = self.result_processor.save_all_formats(results, output_dir)
            
            self.logger.info("文件处理完成")
            return saved_files
            
        except Exception as e:
            self.logger.error(f"处理文件失败: {e}")
            raise
    
    def _batch_score(self, students: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量评分
        
        Args:
            students: 学生信息列表
            
        Returns:
            评分结果列表
        """
        results = []
        total = len(students)
        
        for i, student in enumerate(students, 1):
            try:
                self.logger.info(f"正在评分 ({i}/{total}): {student.get('name', 'Unknown')}")
                
                # 调用API评分
                result = self.api_client.score_student(student)
                results.append(result)
                
                # 显示进度
                if i % 5 == 0 or i == total:
                    self.logger.info(f"评分进度: {i}/{total} ({i/total*100:.1f}%)")
                
            except Exception as e:
                self.logger.error(f"评分学生 {student.get('name', 'Unknown')} 失败: {e}")
                # 添加错误结果
                error_result = {
                    '学生信息': {
                        'id': student.get('id', ''),
                        'name': student.get('name', ''),
                        'content': student.get('content', '')
                    },
                    '思考过程': f"评分失败: {str(e)}",
                    '学习态度': {'分数': 0, '理由': '评分失败'},
                    '自学能力': {'分数': 0, '理由': '评分失败'},
                    '算法基础': {'分数': 0, '理由': '评分失败'},
                    '团队合作能力': {'分数': 0, '理由': '评分失败'},
                    '总分': 0,
                    '综合评价': f'评分失败: {str(e)}',
                    'error': True
                }
                results.append(error_result)
        
        successful_count = len([r for r in results if not r.get('error', False)])
        self.logger.info(f"批量评分完成: 成功 {successful_count}/{total}")
        
        return results
    
    def process_multiple_files(self, input_files: List[str], output_dir: str = "output") -> Dict[str, Dict[str, str]]:
        """
        处理多个文件
        
        Args:
            input_files: 输入文件路径列表
            output_dir: 输出目录
            
        Returns:
            每个文件的保存路径字典
        """
        all_results = {}
        
        for input_file in input_files:
            try:
                self.logger.info(f"处理文件: {input_file}")
                
                # 为每个文件创建子目录
                file_name = Path(input_file).stem
                file_output_dir = Path(output_dir) / file_name
                
                saved_files = self.process_file(input_file, str(file_output_dir))
                all_results[input_file] = saved_files
                
            except Exception as e:
                self.logger.error(f"处理文件 {input_file} 失败: {e}")
                all_results[input_file] = {"error": str(e)}
        
        return all_results


def create_sample_data():
    """创建示例数据文件"""
    sample_data = [
        {
            "学号": "2021001",
            "姓名": "张三",
            "个人介绍": "我对算法竞赛非常感兴趣，从大一开始就自学各种算法知识。参加过ACM竞赛，获得过区域赛银牌。平时喜欢在LeetCode上刷题，已经完成了500+题目。在团队项目中担任技术负责人，能够很好地与队友协作完成复杂的算法实现。"
        },
        {
            "学号": "2021002", 
            "姓名": "李四",
            "个人介绍": "学习成绩一般，对编程有一定兴趣但不够主动。需要老师和同学的督促才能完成作业。参加过一次编程竞赛但没有获奖。团队合作能力较弱，更喜欢独自工作。"
        },
        {
            "学号": "2021003",
            "姓名": "王五", 
            "个人介绍": "自学能力很强，能够快速掌握新的编程语言和算法。有扎实的数据结构基础，熟悉各种排序、搜索算法。积极参与开源项目，在GitHub上有多个项目。善于与他人合作，曾经带领团队完成过多个项目。"
        },
        {
            "学号": "2021004",
            "姓名": "赵六",
            "个人介绍": "对算法学习态度积极，但基础相对薄弱。正在努力学习数据结构和算法，经常向老师和同学请教问题。虽然目前水平不高，但学习意愿强烈，进步很快。团队合作意识强，愿意承担团队任务。"
        }
    ]
    
    # 保存为CSV文件
    import pandas as pd
    df = pd.DataFrame(sample_data)
    df.to_csv("sample_students.csv", index=False, encoding='utf-8-sig')
    print("示例数据文件已创建: sample_students.csv")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="算法竞赛团队AI评分系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py -i students.csv                    # 处理单个CSV文件
  python main.py -i students.txt -o results         # 指定输出目录
  python main.py -i file1.csv file2.xlsx           # 处理多个文件
  python main.py --create-sample                    # 创建示例数据文件
  python main.py -i students.csv --log-level DEBUG # 启用调试日志

支持的文件格式: CSV, TXT, Excel (.xlsx, .xls), JSON
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        nargs="+",
        help="输入文件路径（支持多个文件）"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="输出目录（默认: output）"
    )
    
    parser.add_argument(
        "--api-key",
        help="阿里云百炼API密钥（也可通过环境变量DASHSCOPE_API_KEY设置）"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别（默认: INFO）"
    )
    
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="创建示例数据文件"
    )
    
    args = parser.parse_args()
    
    # 创建示例数据
    if args.create_sample:
        create_sample_data()
        return
    
    # 检查输入文件
    if not args.input:
        parser.error("请指定输入文件，或使用 --create-sample 创建示例数据")
    
    # 检查API密钥
    api_key = args.api_key or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("错误: 未设置API密钥")
        print("请通过以下方式之一设置API密钥:")
        print("1. 设置环境变量: export DASHSCOPE_API_KEY=your_api_key")
        print("2. 使用命令行参数: --api-key your_api_key")
        sys.exit(1)
    
    try:
        # 初始化系统
        system = TeamScoringSystem(api_key=api_key, log_level=args.log_level)
        
        # 处理文件
        if len(args.input) == 1:
            # 单个文件
            saved_files = system.process_file(args.input[0], args.output)
            
            print("\n" + "="*50)
            print("评分完成！生成的文件:")
            for format_type, file_path in saved_files.items():
                print(f"  {format_type.upper()}: {file_path}")
        else:
            # 多个文件
            all_results = system.process_multiple_files(args.input, args.output)
            
            print("\n" + "="*50)
            print("批量处理完成！")
            for input_file, saved_files in all_results.items():
                print(f"\n文件: {input_file}")
                if "error" in saved_files:
                    print(f"  错误: {saved_files['error']}")
                else:
                    for format_type, file_path in saved_files.items():
                        print(f"  {format_type.upper()}: {file_path}")
        
        print("\n详细日志请查看: scoring_system.log")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n系统错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()