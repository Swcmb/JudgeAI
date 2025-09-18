"""
评分结果处理和输出模块
用于处理AI评分结果并输出到不同格式的文件
"""

import json
import pandas as pd
import logging
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime


class ResultProcessor:
    """评分结果处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_results(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        处理评分结果，转换为DataFrame格式
        
        Args:
            results: AI评分结果列表
            
        Returns:
            处理后的DataFrame
        """
        processed_data = []
        
        for result in results:
            try:
                student_info = result.get('学生信息', {})
                
                # 基本信息
                row = {
                    '学号': student_info.get('id', ''),
                    '姓名': student_info.get('name', ''),
                    '个人信息': student_info.get('content', ''),
                }
                
                # AI思考过程（优先使用新的AI思考过程字段）
                ai_thinking = result.get('AI思考过程', '') or result.get('思考过程', '')
                row['AI思考'] = ai_thinking
                
                # 各维度分数
                dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
                for dim in dimensions:
                    dim_data = result.get(dim, {})
                    if isinstance(dim_data, dict):
                        row[f'{dim}_分数'] = dim_data.get('分数', 0)
                        row[f'{dim}_理由'] = dim_data.get('理由', '')
                    else:
                        row[f'{dim}_分数'] = 0
                        row[f'{dim}_理由'] = '数据格式错误'
                
                # 总分和综合评价
                row['AI打分'] = result.get('总分', 0)
                row['综合评价'] = result.get('综合评价', '')
                
                # 错误标记
                row['评分状态'] = '失败' if result.get('error', False) else '成功'
                
                processed_data.append(row)
                
            except Exception as e:
                self.logger.error(f"处理结果时出错: {e}")
                # 添加错误行
                processed_data.append({
                    '学号': '',
                    '姓名': '',
                    '个人信息': '',
                    'AI思考': f'处理错误: {str(e)}',
                    'AI打分': 0,
                    '评分状态': '处理失败'
                })
        
        df = pd.DataFrame(processed_data)
        return df
    
    def save_to_csv(self, df: pd.DataFrame, output_path: str) -> None:
        """
        保存结果到CSV文件
        
        Args:
            df: 结果DataFrame
            output_path: 输出文件路径
        """
        try:
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"结果已保存到CSV文件: {output_path}")
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {e}")
            raise
    
    def save_to_excel(self, df: pd.DataFrame, output_path: str) -> None:
        """
        保存结果到Excel文件
        
        Args:
            df: 结果DataFrame
            output_path: 输出文件路径
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 主要结果表
                main_df = df[['学号', '姓名', '个人信息', 'AI思考', 'AI打分', '综合评价', '评分状态']].copy()
                main_df.to_excel(writer, sheet_name='评分结果', index=False)
                
                # 详细分数表
                detail_columns = ['学号', '姓名']
                for dim in ['学习态度', '自学能力', '算法基础', '团队合作能力']:
                    detail_columns.extend([f'{dim}_分数', f'{dim}_理由'])
                detail_columns.extend(['AI打分', '评分状态'])
                
                detail_df = df[detail_columns].copy()
                detail_df.to_excel(writer, sheet_name='详细评分', index=False)
                
                # 统计信息表
                stats_df = self._generate_statistics(df)
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)
            
            self.logger.info(f"结果已保存到Excel文件: {output_path}")
        except Exception as e:
            self.logger.error(f"保存Excel文件失败: {e}")
            raise
    
    def save_to_json(self, results: List[Dict[str, Any]], output_path: str) -> None:
        """
        保存原始结果到JSON文件
        
        Args:
            results: 原始评分结果列表
            output_path: 输出文件路径
        """
        try:
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'total_students': len(results),
                'results': results
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"结果已保存到JSON文件: {output_path}")
        except Exception as e:
            self.logger.error(f"保存JSON文件失败: {e}")
            raise
    
    def _generate_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成统计信息
        
        Args:
            df: 结果DataFrame
            
        Returns:
            统计信息DataFrame
        """
        stats = []
        
        # 成功评分的学生
        successful_df = df[df['评分状态'] == '成功']
        
        if len(successful_df) > 0:
            # 总分统计
            total_scores = successful_df['AI打分']
            stats.extend([
                {'统计项目': '总学生数', '数值': len(df)},
                {'统计项目': '成功评分数', '数值': len(successful_df)},
                {'统计项目': '失败评分数', '数值': len(df) - len(successful_df)},
                {'统计项目': '平均总分', '数值': f"{total_scores.mean():.2f}"},
                {'统计项目': '最高总分', '数值': total_scores.max()},
                {'统计项目': '最低总分', '数值': total_scores.min()},
                {'统计项目': '总分标准差', '数值': f"{total_scores.std():.2f}"},
            ])
            
            # 各维度统计
            dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
            for dim in dimensions:
                dim_scores = successful_df[f'{dim}_分数']
                stats.extend([
                    {'统计项目': f'{dim}_平均分', '数值': f"{dim_scores.mean():.2f}"},
                    {'统计项目': f'{dim}_最高分', '数值': dim_scores.max()},
                    {'统计项目': f'{dim}_最低分', '数值': dim_scores.min()},
                ])
            
            # 分数段分布
            score_ranges = [
                (90, 100, '优秀'),
                (80, 89, '良好'),
                (70, 79, '中等'),
                (60, 69, '及格'),
                (0, 59, '不及格')
            ]
            
            for min_score, max_score, level in score_ranges:
                count = len(successful_df[(successful_df['AI打分'] >= min_score) & 
                                        (successful_df['AI打分'] <= max_score)])
                percentage = (count / len(successful_df)) * 100 if len(successful_df) > 0 else 0
                stats.append({
                    '统计项目': f'{level}({min_score}-{max_score}分)',
                    '数值': f"{count}人 ({percentage:.1f}%)"
                })
        else:
            stats.append({'统计项目': '无成功评分数据', '数值': '无法生成统计'})
        
        return pd.DataFrame(stats)
    
    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """
        生成评分总结报告
        
        Args:
            df: 结果DataFrame
            
        Returns:
            总结报告文本
        """
        successful_df = df[df['评分状态'] == '成功']
        
        if len(successful_df) == 0:
            return "无成功评分数据，无法生成报告。"
        
        report = []
        report.append("=" * 50)
        report.append("算法竞赛团队AI评分总结报告")
        report.append("=" * 50)
        report.append(f"评分时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"总学生数: {len(df)}")
        report.append(f"成功评分: {len(successful_df)}")
        report.append(f"失败评分: {len(df) - len(successful_df)}")
        report.append("")
        
        # 总分统计
        total_scores = successful_df['AI打分']
        report.append("总分统计:")
        report.append(f"  平均分: {total_scores.mean():.2f}")
        report.append(f"  最高分: {total_scores.max()}")
        report.append(f"  最低分: {total_scores.min()}")
        report.append(f"  标准差: {total_scores.std():.2f}")
        report.append("")
        
        # 各维度平均分
        report.append("各维度平均分:")
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        for dim in dimensions:
            avg_score = successful_df[f'{dim}_分数'].mean()
            report.append(f"  {dim}: {avg_score:.2f}")
        report.append("")
        
        # 推荐学生（总分前5名）
        top_students = successful_df.nlargest(5, 'AI打分')
        report.append("推荐学生（总分前5名）:")
        for idx, (_, student) in enumerate(top_students.iterrows(), 1):
            report.append(f"  {idx}. {student['姓名']} (学号: {student['学号']}) - 总分: {student['AI打分']}")
        report.append("")
        
        # 需要关注的学生（总分后5名）
        bottom_students = successful_df.nsmallest(5, 'AI打分')
        report.append("需要关注的学生（总分后5名）:")
        for idx, (_, student) in enumerate(bottom_students.iterrows(), 1):
            report.append(f"  {idx}. {student['姓名']} (学号: {student['学号']}) - 总分: {student['AI打分']}")
        
        report.append("=" * 50)
        
        return "\n".join(report)
    
    def save_all_formats(self, results: List[Dict[str, Any]], output_dir: str = "output") -> Dict[str, str]:
        """
        保存所有格式的结果文件
        
        Args:
            results: 评分结果列表
            output_dir: 输出目录
            
        Returns:
            保存的文件路径字典
        """
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 处理结果
        df = self.process_results(results)
        
        # 保存文件
        saved_files = {}
        
        try:
            # CSV文件
            csv_path = output_path / f"评分结果_{timestamp}.csv"
            self.save_to_csv(df, str(csv_path))
            saved_files['csv'] = str(csv_path)
            
            # Excel文件
            excel_path = output_path / f"评分结果_{timestamp}.xlsx"
            self.save_to_excel(df, str(excel_path))
            saved_files['excel'] = str(excel_path)
            
            # JSON文件
            json_path = output_path / f"评分结果_{timestamp}.json"
            self.save_to_json(results, str(json_path))
            saved_files['json'] = str(json_path)
            
            # 总结报告
            report = self.generate_summary_report(df)
            report_path = output_path / f"评分报告_{timestamp}.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            saved_files['report'] = str(report_path)
            
            self.logger.info(f"所有结果文件已保存到目录: {output_dir}")
            
        except Exception as e:
            self.logger.error(f"保存文件时出错: {e}")
            raise
        
        return saved_files


def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据
    test_results = [
        {
            '学生信息': {'id': '001', 'name': '张三', 'content': '测试学生1'},
            '思考过程': '该学生表现优秀...',
            '学习态度': {'分数': 22, '理由': '学习态度积极'},
            '自学能力': {'分数': 20, '理由': '自学能力较强'},
            '算法基础': {'分数': 18, '理由': '算法基础良好'},
            '团队合作能力': {'分数': 19, '理由': '团队合作能力好'},
            '总分': 79,
            '综合评价': '综合表现良好'
        },
        {
            '学生信息': {'id': '002', 'name': '李四', 'content': '测试学生2'},
            '思考过程': '该学生表现一般...',
            '学习态度': {'分数': 15, '理由': '学习态度一般'},
            '自学能力': {'分数': 12, '理由': '自学能力较弱'},
            '算法基础': {'分数': 10, '理由': '算法基础薄弱'},
            '团队合作能力': {'分数': 13, '理由': '团队合作能力一般'},
            '总分': 50,
            '综合评价': '需要加强学习'
        }
    ]
    
    processor = ResultProcessor()
    
    try:
        # 测试保存所有格式
        saved_files = processor.save_all_formats(test_results, "test_output")
        
        print("测试完成，保存的文件:")
        for format_type, file_path in saved_files.items():
            print(f"  {format_type}: {file_path}")
            
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    main()