"""
批量数据导入增强模块
支持多种数据源和格式的批量导入功能
"""

import os
import json
import sqlite3
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from datetime import datetime
import zipfile
import tarfile
import csv
from io import StringIO, BytesIO

class BatchImporter:
    """批量数据导入器"""
    
    def __init__(self, db_path: str = "student_data.db"):
        """
        初始化批量导入器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建学生信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE,
                name TEXT,
                content TEXT,
                source_file TEXT,
                import_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # 创建评分结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scoring_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                scoring_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_score INTEGER,
                learning_attitude_score INTEGER,
                learning_attitude_reason TEXT,
                self_study_score INTEGER,
                self_study_reason TEXT,
                algorithm_score INTEGER,
                algorithm_reason TEXT,
                teamwork_score INTEGER,
                teamwork_reason TEXT,
                ai_thinking TEXT,
                overall_evaluation TEXT,
                model_version TEXT,
                metadata TEXT,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        # 创建导入任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS import_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                source_type TEXT,
                source_path TEXT,
                status TEXT DEFAULT 'pending',
                total_records INTEGER DEFAULT 0,
                processed_records INTEGER DEFAULT 0,
                failed_records INTEGER DEFAULT 0,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                error_message TEXT,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def import_from_directory(self, directory_path: str, pattern: str = "*.*") -> Dict[str, Any]:
        """
        从目录批量导入文件
        
        Args:
            directory_path: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            导入结果
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        # 查找匹配的文件
        files = list(directory.glob(pattern))
        if not files:
            return {"success": False, "error": "未找到匹配的文件"}
        
        # 创建导入任务
        task_id = self._create_import_task(
            task_name=f"批量导入_{directory.name}",
            source_type="directory",
            source_path=str(directory_path)
        )
        
        results = {
            "success": True,
            "task_id": task_id,
            "total_files": len(files),
            "processed_files": 0,
            "failed_files": 0,
            "total_students": 0,
            "failed_students": 0,
            "files": []
        }
        
        try:
            for file_path in files:
                try:
                    file_result = self.import_file(str(file_path))
                    if file_result["success"]:
                        results["processed_files"] += 1
                        results["total_students"] += file_result.get("student_count", 0)
                    else:
                        results["failed_files"] += 1
                        self.logger.error(f"文件导入失败: {file_path} - {file_result.get('error')}")
                    
                    results["files"].append({
                        "path": str(file_path),
                        "result": file_result
                    })
                    
                except Exception as e:
                    results["failed_files"] += 1
                    self.logger.error(f"处理文件时出错: {file_path} - {e}")
            
            # 更新任务状态
            self._update_import_task(task_id, {
                "status": "completed" if results["failed_files"] == 0 else "completed_with_errors",
                "processed_records": results["total_students"],
                "failed_records": results["failed_students"]
            })
            
        except Exception as e:
            self._update_import_task(task_id, {
                "status": "failed",
                "error_message": str(e)
            })
            raise
        
        return results
    
    def import_file(self, file_path: str) -> Dict[str, Any]:
        """
        导入单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            导入结果
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {"success": False, "error": "文件不存在"}
        
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.csv':
                return self._import_csv(file_path)
            elif extension in ['.xlsx', '.xls']:
                return self._import_excel(file_path)
            elif extension == '.json':
                return self._import_json(file_path)
            elif extension == '.txt':
                return self._import_txt(file_path)
            elif extension in ['.zip', '.tar', '.gz']:
                return self._import_archive(file_path)
            else:
                return {"success": False, "error": f"不支持的文件格式: {extension}"}
        
        except Exception as e:
            self.logger.error(f"导入文件失败: {file_path} - {e}")
            return {"success": False, "error": str(e)}
    
    def _import_csv(self, file_path: Path) -> Dict[str, Any]:
        """导入CSV文件"""
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                return {"success": False, "error": "无法读取CSV文件，请检查文件编码"}
            
            return self._process_dataframe(df, str(file_path))
            
        except Exception as e:
            return {"success": False, "error": f"CSV处理失败: {str(e)}"}
    
    def _import_excel(self, file_path: Path) -> Dict[str, Any]:
        """导入Excel文件"""
        try:
            # 尝试读取所有工作表
            excel_file = pd.ExcelFile(file_path)
            
            total_students = 0
            failed_students = 0
            results = []
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    sheet_result = self._process_dataframe(df, str(file_path), f"工作表: {sheet_name}")
                    
                    if sheet_result["success"]:
                        total_students += sheet_result.get("student_count", 0)
                    else:
                        failed_students += 1
                    
                    results.append({
                        "sheet_name": sheet_name,
                        "result": sheet_result
                    })
                    
                except Exception as e:
                    failed_students += 1
                    results.append({
                        "sheet_name": sheet_name,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "file_type": "excel",
                "total_students": total_students,
                "failed_sheets": failed_students,
                "sheets": results
            }
            
        except Exception as e:
            return {"success": False, "error": f"Excel处理失败: {str(e)}"}
    
    def _import_json(self, file_path: Path) -> Dict[str, Any]:
        """导入JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理不同的JSON结构
            if isinstance(data, list):
                # JSON数组
                students = data
            elif isinstance(data, dict):
                if 'students' in data:
                    students = data['students']
                elif 'data' in data:
                    students = data['data']
                else:
                    students = [data]  # 单个学生对象
            else:
                return {"success": False, "error": "不支持的JSON结构"}
            
            return self._process_student_list(students, str(file_path))
            
        except Exception as e:
            return {"success": False, "error": f"JSON处理失败: {str(e)}"}
    
    def _import_txt(self, file_path: Path) -> Dict[str, Any]:
        """导入TXT文件"""
        try:
            # 尝试不同编码
            encodings = ['utf-8', 'gbk', 'gb2312']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return {"success": False, "error": "无法读取TXT文件，请检查文件编码"}
            
            # 按行分割
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # 转换为学生对象
            students = []
            for i, line in enumerate(lines, 1):
                students.append({
                    'id': str(i),
                    'name': f'学生{i}',
                    'content': line
                })
            
            return self._process_student_list(students, str(file_path))
            
        except Exception as e:
            return {"success": False, "error": f"TXT处理失败: {str(e)}"}
    
    def _import_archive(self, file_path: Path) -> Dict[str, Any]:
        """导入压缩文件"""
        try:
            # 创建临时解压目录
            temp_dir = file_path.parent / f"temp_{file_path.stem}"
            temp_dir.mkdir(exist_ok=True)
            
            # 解压文件
            if file_path.suffix == '.zip':
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            elif file_path.suffix in ['.tar', '.gz']:
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    tar_ref.extractall(temp_dir)
            
            # 批量导入解压后的文件
            result = self.import_from_directory(temp_dir, "*.*")
            
            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": f"压缩文件处理失败: {str(e)}"}
    
    def _process_dataframe(self, df: pd.DataFrame, source_file: str, sheet_info: str = "") -> Dict[str, Any]:
        """处理DataFrame数据"""
        try:
            # 清理数据
            df = df.dropna(how='all')  # 删除全空行
            df = df.fillna('')   # 填充空值
            
            # 智能识别列
            columns = df.columns.tolist()
            
            # 查找可能的列名
            id_col = self._find_column(columns, ['id', '学号', 'student_id', '编号', '序号'])
            name_col = self._find_column(columns, ['name', '姓名', 'student_name', '名字', '学生姓名'])
            content_col = self._find_column(columns, ['content', '个人介绍', '介绍', '描述', '内容', '个人信息'])
            
            # 如果没找到内容列，尝试使用其他可能包含信息的列
            if not content_col:
                for col in columns:
                    if col not in [id_col, name_col]:
                        sample_values = df[col].dropna().head(5).tolist()
                        if any(isinstance(v, str) and len(v) > 20 for v in sample_values):
                            content_col = col
                            break
            
            students = []
            failed_count = 0
            
            for index, row in df.iterrows():
                try:
                    student = {
                        'id': str(row.get(id_col, index + 1)) if pd.notna(row.get(id_col, index + 1)) else str(index + 1),
                        'name': str(row.get(name_col, f'学生{index + 1}')) if pd.notna(row.get(name_col, f'学生{index + 1}')) else f'学生{index + 1}',
                        'content': str(row.get(content_col, '')) if pd.notna(row.get(content_col, '')) else ''
                    }
                    
                    # 收集其他信息
                    other_info = {}
                    for col in columns:
                        if col not in [id_col, name_col, content_col] and pd.notna(row[col]):
                            other_info[col] = str(row[col])
                    
                    if other_info:
                        student['metadata'] = other_info
                    
                    students.append(student)
                    
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"处理行数据失败: {index} - {e}")
            
            return self._process_student_list(students, source_file, sheet_info)
            
        except Exception as e:
            return {"success": False, "error": f"DataFrame处理失败: {str(e)}"}
    
    def _find_column(self, columns: List[str], possible_names: List[str]) -> Optional[str]:
        """查找列名"""
        for name in possible_names:
            for col in columns:
                if name.lower() in col.lower() or col.lower() in name.lower():
                    return col
        return None
    
    def _process_student_list(self, students: List[Dict[str, Any]], source_file: str, sheet_info: str = "") -> Dict[str, Any]:
        """处理学生列表"""
        success_count = 0
        failed_count = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for student in students:
            try:
                # 准备数据
                student_id = student.get('id', '')
                name = student.get('name', '')
                content = student.get('content', '')
                metadata = json.dumps({k: v for k, v in student.items() if k not in ['id', 'name', 'content']})
                
                # 插入数据库
                cursor.execute('''
                    INSERT OR REPLACE INTO students 
                    (student_id, name, content, source_file, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (student_id, name, content, source_file, metadata))
                
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                self.logger.error(f"保存学生数据失败: {student.get('id', 'unknown')} - {e}")
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "source_file": source_file,
            "sheet_info": sheet_info,
            "student_count": success_count,
            "failed_count": failed_count
        }
    
    def import_from_api(self, api_url: str, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        从API导入数据
        
        Args:
            api_url: API地址
            headers: 请求头
            params: 请求参数
            
        Returns:
            导入结果
        """
        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 创建导入任务
            task_id = self._create_import_task(
                task_name=f"API导入_{api_url}",
                source_type="api",
                source_path=api_url
            )
            
            # 处理API响应数据
            if isinstance(data, list):
                students = data
            elif isinstance(data, dict):
                if 'students' in data:
                    students = data['students']
                elif 'data' in data:
                    students = data['data']
                else:
                    students = [data]
            else:
                return {"success": False, "error": "API返回的数据格式不支持"}
            
            result = self._process_student_list(students, api_url)
            
            # 更新任务状态
            self._update_import_task(task_id, {
                "status": "completed",
                "processed_records": result.get("student_count", 0),
                "failed_records": result.get("failed_count", 0)
            })
            
            return result
            
        except Exception as e:
            return {"success": False, "error": f"API导入失败: {str(e)}"}
    
    def get_student_data(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取学生数据
        
        Args:
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            学生数据列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM students"
        params = []
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params = [limit, offset]
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 获取列名
        columns = [desc[0] for desc in cursor.description]
        
        students = []
        for row in rows:
            student = dict(zip(columns, row))
            if student.get('metadata'):
                try:
                    student['metadata'] = json.loads(student['metadata'])
                except:
                    pass
            students.append(student)
        
        conn.close()
        return students
    
    def get_import_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取导入任务列表
        
        Args:
            status: 任务状态过滤
            
        Returns:
            任务列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM import_tasks"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params = [status]
        
        query += " ORDER BY start_time DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        
        tasks = []
        for row in rows:
            task = dict(zip(columns, row))
            if task.get('metadata'):
                try:
                    task['metadata'] = json.loads(task['metadata'])
                except:
                    pass
            tasks.append(task)
        
        conn.close()
        return tasks
    
    def _create_import_task(self, task_name: str, source_type: str, source_path: str) -> int:
        """创建导入任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO import_tasks (task_name, source_type, source_path, start_time)
            VALUES (?, ?, ?, ?)
        ''', (task_name, source_type, source_path, datetime.now()))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return task_id
    
    def _update_import_task(self, task_id: int, updates: Dict[str, Any]):
        """更新导入任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        params.append(task_id)
        
        query = f"UPDATE import_tasks SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, params)
        
        if 'end_time' not in updates:
            cursor.execute("UPDATE import_tasks SET end_time = ? WHERE id = ?", (datetime.now(), task_id))
        
        conn.commit()
        conn.close()
    
    def export_data(self, output_path: str, format: str = "csv") -> Dict[str, Any]:
        """
        导出数据
        
        Args:
            output_path: 输出路径
            format: 输出格式 (csv, excel, json)
            
        Returns:
            导出结果
        """
        try:
            students = self.get_student_data()
            
            if not students:
                return {"success": False, "error": "没有数据可导出"}
            
            # 转换为DataFrame
            df_data = []
            for student in students:
                row = {
                    'id': student['student_id'],
                    'name': student['name'],
                    'content': student['content'],
                    'source_file': student['source_file'],
                    'import_time': student['import_time']
                }
                
                # 添加元数据字段
                if student.get('metadata') and isinstance(student['metadata'], dict):
                    for key, value in student['metadata'].items():
                        row[f"meta_{key}"] = value
                
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # 根据格式导出
            if format.lower() == 'csv':
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
            elif format.lower() in ['excel', 'xlsx']:
                df.to_excel(output_path, index=False, engine='openpyxl')
            elif format.lower() == 'json':
                df.to_json(output_path, orient='records', force_ascii=False, indent=2)
            else:
                return {"success": False, "error": f"不支持的导出格式: {format}"}
            
            return {
                "success": True,
                "output_path": output_path,
                "format": format,
                "record_count": len(students)
            }
            
        except Exception as e:
            return {"success": False, "error": f"导出失败: {str(e)}"}


def main():
    """测试批量导入功能"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量数据导入工具")
    parser.add_argument("--source", help="数据源路径或URL")
    parser.add_argument("--type", choices=["file", "directory", "api"], default="file", help="数据源类型")
    parser.add_argument("--format", choices=["csv", "excel", "json", "txt"], help="文件格式")
    parser.add_argument("--export", help="导出路径")
    parser.add_argument("--export-format", choices=["csv", "excel", "json"], default="csv", help="导出格式")
    
    args = parser.parse_args()
    
    importer = BatchImporter()
    
    try:
        if args.source:
            if args.type == "file":
                result = importer.import_file(args.source)
            elif args.type == "directory":
                pattern = f"*.{args.format}" if args.format else "*.*"
                result = importer.import_from_directory(args.source, pattern)
            elif args.type == "api":
                result = importer.import_from_api(args.source)
            
            print(f"导入结果: {result}")
        
        if args.export:
            export_result = importer.export_data(args.export, args.export_format)
            print(f"导出结果: {export_result}")
        
        # 显示统计信息
        students = importer.get_student_data()
        tasks = importer.get_import_tasks()
        
        print(f"\n数据库统计:")
        print(f"学生总数: {len(students)}")
        print(f"导入任务数: {len(tasks)}")
        
    except Exception as e:
        print(f"操作失败: {e}")


if __name__ == "__main__":
    main()