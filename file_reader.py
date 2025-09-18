"""
文件读取和数据解析模块
支持多种文件格式的学生信息读取
"""

import pandas as pd
import csv
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

class FileReader:
    """文件读取器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def read_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        读取文件并返回学生信息列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            学生信息列表，每个元素包含学生的详细信息
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        file_extension = file_path.suffix.lower()
        
        try:
            if file_extension == '.csv':
                return self._read_csv(file_path)
            elif file_extension == '.txt':
                return self._read_txt(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                return self._read_excel(file_path)
            elif file_extension == '.json':
                return self._read_json(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_extension}")
                
        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            raise
    
    def _read_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """读取CSV文件"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='gbk')
            
        return self._dataframe_to_list(df)
    
    def _read_txt(self, file_path: Path) -> List[Dict[str, Any]]:
        """读取TXT文件，每行作为一个学生信息"""
        students = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                lines = f.readlines()
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line:  # 跳过空行
                students.append({
                    'id': i + 1,
                    'content': line,
                    'name': f'学生{i + 1}'
                })
        
        return students
    
    def _read_excel(self, file_path: Path) -> List[Dict[str, Any]]:
        """读取Excel文件"""
        df = pd.read_excel(file_path)
        return self._dataframe_to_list(df)
    
    def _read_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """读取JSON文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            raise ValueError("JSON文件格式不正确，应为列表或字典")
    
    def _dataframe_to_list(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """将DataFrame转换为字典列表"""
        students = []
        
        for index, row in df.iterrows():
            student_info = {}
            
            # 处理常见的列名映射
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['姓名', 'name', '学生姓名']:
                    student_info['name'] = str(row[col])
                elif col_lower in ['学号', 'id', 'student_id', '编号']:
                    student_info['id'] = str(row[col])
                elif col_lower in ['描述', 'description', 'content', '个人介绍', '自我介绍']:
                    student_info['content'] = str(row[col])
                else:
                    student_info[col] = str(row[col])
            
            # 确保必要字段存在
            if 'id' not in student_info:
                student_info['id'] = str(index + 1)
            if 'name' not in student_info:
                student_info['name'] = f'学生{index + 1}'
            if 'content' not in student_info:
                # 将所有非id、name字段合并为content
                content_parts = []
                for key, value in student_info.items():
                    if key not in ['id', 'name'] and pd.notna(value):
                        content_parts.append(f"{key}: {value}")
                student_info['content'] = "; ".join(content_parts)
            
            students.append(student_info)
        
        return students
    
    def validate_data(self, students: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和清洗学生数据
        
        Args:
            students: 原始学生数据列表
            
        Returns:
            清洗后的学生数据列表
        """
        valid_students = []
        
        for student in students:
            # 检查必要字段
            if not student.get('content') or student['content'].strip() == '':
                self.logger.warning(f"学生 {student.get('name', 'Unknown')} 缺少内容信息，跳过")
                continue
            
            # 清理数据
            student['content'] = student['content'].strip()
            student['name'] = student.get('name', '').strip()
            student['id'] = str(student.get('id', ''))
            
            valid_students.append(student)
        
        self.logger.info(f"成功读取 {len(valid_students)} 条有效学生信息")
        return valid_students


def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    reader = FileReader()
    
    # 创建测试数据
    test_data = [
        {"name": "张三", "content": "我对算法很感兴趣，经常自学新的算法知识，参加过多次编程竞赛"},
        {"name": "李四", "content": "学习态度一般，需要老师督促才能完成作业，团队合作能力较弱"},
        {"name": "王五", "content": "自学能力强，能够独立解决复杂问题，有良好的算法基础和团队协作经验"}
    ]
    
    # 保存测试文件
    with open('test_students.json', 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # 测试读取
    try:
        students = reader.read_file('test_students.json')
        validated_students = reader.validate_data(students)
        
        print("读取到的学生信息:")
        for student in validated_students:
            print(f"ID: {student['id']}, 姓名: {student['name']}")
            print(f"内容: {student['content'][:50]}...")
            print("-" * 50)
            
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    main()