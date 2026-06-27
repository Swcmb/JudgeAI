"""
历史记录管理模块
学生评分历史追踪和比较功能
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

@dataclass
class StudentProgress:
    """学生进度数据类"""
    student_id: str
    student_name: str
    scoring_history: List[Dict[str, Any]]
    improvement_trend: float
    best_score: int
    latest_score: int
    total_assessments: int
    average_score: float
    strength_dimensions: List[str]
    weak_dimensions: List[str]
    improvement_suggestions: List[str]

class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self, db_path: str = "scoring_history.db"):
        """
        初始化历史记录管理器
        
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
        
        # 创建历史记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scoring_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                student_name TEXT,
                assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assessment_session TEXT,
                model_version TEXT,
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
                raw_response TEXT,
                metadata TEXT,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        # 创建学生信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                student_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # 创建进度追踪表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_score INTEGER,
                improvement_rate REAL,
                trend_direction TEXT,
                milestone_reached TEXT,
                notes TEXT,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        # 创建比较分析表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comparison_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                comparison_type TEXT,
                student_ids TEXT,
                analysis_result TEXT,
                insights TEXT,
                recommendations TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_scoring_result(self, result: Dict[str, Any], session_id: str = None) -> bool:
        """
        保存评分结果到历史记录
        
        Args:
            result: 评分结果
            session_id: 评分会话ID
            
        Returns:
            是否保存成功
        """
        try:
            student_info = result.get('学生信息', {})
            student_id = student_info.get('id', '')
            student_name = student_info.get('name', '')
            
            if not student_id:
                self.logger.warning("学生ID为空，无法保存历史记录")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新或创建学生记录
            cursor.execute('''
                INSERT OR REPLACE INTO students (student_id, student_name, updated_at, metadata)
                VALUES (?, ?, ?, ?)
            ''', (
                student_id,
                student_name,
                datetime.now(),
                json.dumps({k: v for k, v in student_info.items() if k not in ['id', 'name']})
            ))
            
            # 保存评分结果
            dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
            dimension_scores = {}
            dimension_reasons = {}
            
            for dim in dimensions:
                dim_data = result.get(dim, {})
                if isinstance(dim_data, dict):
                    dimension_scores[dim] = dim_data.get('分数', 0)
                    dimension_reasons[dim] = dim_data.get('理由', '')
            
            cursor.execute('''
                INSERT INTO scoring_history (
                    student_id, student_name, assessment_session, model_version,
                    total_score, learning_attitude_score, learning_attitude_reason,
                    self_study_score, self_study_reason, algorithm_score, algorithm_reason,
                    teamwork_score, teamwork_reason, ai_thinking, overall_evaluation,
                    raw_response, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                student_id, student_name, session_id, result.get('model_version', 'qwen-plus'),
                result.get('总分', 0),
                dimension_scores.get('学习态度', 0), dimension_reasons.get('学习态度', ''),
                dimension_scores.get('自学能力', 0), dimension_reasons.get('自学能力', ''),
                dimension_scores.get('算法基础', 0), dimension_reasons.get('算法基础', ''),
                dimension_scores.get('团队合作能力', 0), dimension_reasons.get('团队合作能力', ''),
                result.get('AI思考过程', '') or result.get('思考过程', ''),
                result.get('综合评价', ''),
                json.dumps(result),
                json.dumps({k: v for k, v in result.items() 
                          if k not in ['学生信息', '总分', '学习态度', '自学能力', '算法基础', 
                                     '团队合作能力', 'AI思考过程', '思考过程', '综合评价']})
            ))
            
            # 更新进度追踪
            self._update_progress_tracking(cursor, student_id, result.get('总分', 0))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"已保存学生 {student_id} 的评分历史记录")
            return True
            
        except Exception as e:
            self.logger.error(f"保存评分历史记录失败: {e}")
            return False
    
    def _update_progress_tracking(self, cursor, student_id: str, current_score: int):
        """更新进度追踪"""
        # 获取历史评分记录
        cursor.execute('''
            SELECT total_score, assessment_date FROM scoring_history 
            WHERE student_id = ? ORDER BY assessment_date DESC LIMIT 5
        ''', (student_id,))
        
        records = cursor.fetchall()
        
        if len(records) >= 2:
            # 计算改进率
            scores = [record[0] for record in records]
            dates = [record[1] for record in records]
            
            # 简单线性趋势
            recent_scores = scores[:3]
            if len(recent_scores) >= 2:
                improvement_rate = (recent_scores[0] - recent_scores[-1]) / len(recent_scores)
            else:
                improvement_rate = 0
            
            # 确定趋势方向
            if improvement_rate > 1:
                trend_direction = "improving"
            elif improvement_rate < -1:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
            
            # 检查里程碑
            milestone_reached = None
            if current_score >= 90:
                milestone_reached = "excellent"
            elif current_score >= 80:
                milestone_reached = "good"
            elif current_score >= 70:
                milestone_reached = "satisfactory"
            elif current_score >= 60:
                milestone_reached = "passing"
            
            # 保存进度记录
            cursor.execute('''
                INSERT INTO progress_tracking (
                    student_id, total_score, improvement_rate, trend_direction, milestone_reached
                ) VALUES (?, ?, ?, ?, ?)
            ''', (student_id, current_score, improvement_rate, trend_direction, milestone_reached))
    
    def get_student_history(self, student_id: str) -> List[Dict[str, Any]]:
        """
        获取学生的评分历史
        
        Args:
            student_id: 学生ID
            
        Returns:
            评分历史列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM scoring_history 
            WHERE student_id = ? 
            ORDER BY assessment_date DESC
        ''', (student_id,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        history = []
        for row in rows:
            record = dict(zip(columns, row))
            if record.get('raw_response'):
                try:
                    record['raw_response'] = json.loads(record['raw_response'])
                except:
                    pass
            if record.get('metadata'):
                try:
                    record['metadata'] = json.loads(record['metadata'])
                except:
                    pass
            history.append(record)
        
        conn.close()
        return history
    
    def get_student_progress(self, student_id: str) -> Optional[StudentProgress]:
        """
        获取学生的学习进度分析
        
        Args:
            student_id: 学生ID
            
        Returns:
            学生进度对象
        """
        history = self.get_student_history(student_id)
        
        if not history:
            return None
        
        # 获取学生信息
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT student_name FROM students WHERE student_id = ?', (student_id,))
        result = cursor.fetchone()
        student_name = result[0] if result else f"学生{student_id}"
        conn.close()
        
        # 计算统计数据
        scores = [record['total_score'] for record in history]
        latest_score = scores[0]
        best_score = max(scores)
        average_score = sum(scores) / len(scores)
        total_assessments = len(scores)
        
        # 计算改进趋势
        if len(scores) >= 2:
            improvement_trend = scores[0] - scores[-1]
        else:
            improvement_trend = 0
        
        # 分析强项和弱项
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        dimension_scores = {}
        
        for dim in dimensions:
            scores_dim = []
            for record in history:
                if dim == '学习态度':
                    scores_dim.append(record['learning_attitude_score'])
                elif dim == '自学能力':
                    scores_dim.append(record['self_study_score'])
                elif dim == '算法基础':
                    scores_dim.append(record['algorithm_score'])
                elif dim == '团队合作能力':
                    scores_dim.append(record['teamwork_score'])
            
            if scores_dim:
                dimension_scores[dim] = {
                    'average': sum(scores_dim) / len(scores_dim),
                    'latest': scores_dim[0],
                    'trend': scores_dim[0] - scores_dim[-1] if len(scores_dim) >= 2 else 0
                }
        
        # 确定强项和弱项
        sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1]['average'], reverse=True)
        strength_dimensions = [dim for dim, scores in sorted_dims[:2] if scores['average'] >= 20]
        weak_dimensions = [dim for dim, scores in sorted_dims[-2:] if scores['average'] <= 15]
        
        # 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(
            dimension_scores, latest_score, student_id
        )
        
        return StudentProgress(
            student_id=student_id,
            student_name=student_name,
            scoring_history=history,
            improvement_trend=improvement_trend,
            best_score=best_score,
            latest_score=latest_score,
            total_assessments=total_assessments,
            average_score=average_score,
            strength_dimensions=strength_dimensions,
            weak_dimensions=weak_dimensions,
            improvement_suggestions=improvement_suggestions
        )
    
    def _generate_improvement_suggestions(self, dimension_scores: Dict, latest_score: int, student_id: str) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于总分给出建议
        if latest_score < 60:
            suggestions.append("整体基础较弱，建议加强基础知识学习，可以从简单算法开始练习")
        elif latest_score < 80:
            suggestions.append("有一定基础，建议重点提升薄弱维度的能力")
        
        # 基于各维度给出具体建议
        for dim, scores in dimension_scores.items():
            if scores['average'] < 15:
                if dim == '学习态度':
                    suggestions.append("学习态度需要改进，建议制定学习计划，培养学习兴趣")
                elif dim == '自学能力':
                    suggestions.append("自学能力需要提升，建议多独立解决问题，总结学习方法")
                elif dim == '算法基础':
                    suggestions.append("算法基础薄弱，建议系统学习数据结构和算法，多做练习")
                elif dim == '团队合作能力':
                    suggestions.append("团队合作能力需要加强，建议多参与团队项目，提升沟通能力")
            elif scores['trend'] < -5:
                suggestions.append(f"{dim}有所下降，需要重点关注和改进")
        
        return suggestions
    
    def compare_students(self, student_ids: List[str]) -> Dict[str, Any]:
        """
        比较多个学生
        
        Args:
            student_ids: 学生ID列表
            
        Returns:
            比较分析结果
        """
        if len(student_ids) < 2:
            return {"error": "至少需要2个学生进行比较"}
        
        student_data = {}
        for student_id in student_ids:
            progress = self.get_student_progress(student_id)
            if progress:
                student_data[student_id] = progress
        
        if len(student_data) < 2:
            return {"error": "有效学生数据不足"}
        
        # 生成比较分析
        comparison_result = {
            "comparison_date": datetime.now().isoformat(),
            "student_count": len(student_data),
            "students": {},
            "rankings": {},
            "insights": [],
            "recommendations": []
        }
        
        # 收集学生数据
        for student_id, progress in student_data.items():
            comparison_result["students"][student_id] = {
                "name": progress.student_name,
                "latest_score": progress.latest_score,
                "average_score": progress.average_score,
                "best_score": progress.best_score,
                "improvement_trend": progress.improvement_trend,
                "strength_dimensions": progress.strength_dimensions,
                "weak_dimensions": progress.weak_dimensions,
                "total_assessments": progress.total_assessments
            }
        
        # 生成排名
        latest_scores = [(sid, data["latest_score"]) for sid, data in comparison_result["students"].items()]
        latest_scores.sort(key=lambda x: x[1], reverse=True)
        comparison_result["rankings"]["latest_score"] = latest_scores
        
        avg_scores = [(sid, data["average_score"]) for sid, data in comparison_result["students"].items()]
        avg_scores.sort(key=lambda x: x[1], reverse=True)
        comparison_result["rankings"]["average_score"] = avg_scores
        
        improvement_scores = [(sid, data["improvement_trend"]) for sid, data in comparison_result["students"].items()]
        improvement_scores.sort(key=lambda x: x[1], reverse=True)
        comparison_result["rankings"]["improvement"] = improvement_scores
        
        # 生成洞察
        best_student = latest_scores[0][0]
        most_improved = improvement_scores[0][0]
        
        comparison_result["insights"].append(f"最高分学生: {student_data[best_student].student_name} ({latest_scores[0][1]}分)")
        comparison_result["insights"].append(f"进步最大学生: {student_data[most_improved].student_name} (改进{improvement_scores[0][1]}分)")
        
        # 分析维度差异
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        for dim in dimensions:
            dim_scores = []
            for student_id, progress in student_data.items():
                # 获取该维度的最新分数
                latest_record = progress.scoring_history[0] if progress.scoring_history else None
                if latest_record:
                    if dim == '学习态度':
                        dim_scores.append((student_id, latest_record['learning_attitude_score']))
                    elif dim == '自学能力':
                        dim_scores.append((student_id, latest_record['self_study_score']))
                    elif dim == '算法基础':
                        dim_scores.append((student_id, latest_record['algorithm_score']))
                    elif dim == '团队合作能力':
                        dim_scores.append((student_id, latest_record['teamwork_score']))
            
            if dim_scores:
                dim_scores.sort(key=lambda x: x[1], reverse=True)
                top_student = dim_scores[0][0]
                comparison_result["insights"].append(f"{dim}最强: {student_data[top_student].student_name} ({dim_scores[0][1]}分)")
        
        # 生成建议
        comparison_result["recommendations"] = self._generate_comparison_recommendations(student_data)
        
        # 保存比较分析结果
        self._save_comparison_analysis(comparison_result, student_ids)
        
        return comparison_result
    
    def _generate_comparison_recommendations(self, student_data: Dict[str, StudentProgress]) -> List[str]:
        """生成比较建议"""
        recommendations = []
        
        # 分析整体表现
        scores = [progress.latest_score for progress in student_data.values()]
        avg_score = sum(scores) / len(scores)
        
        # 为不同水平的学生提供建议
        for student_id, progress in student_data.items():
            if progress.latest_score < avg_score - 10:
                recommendations.append(f"{progress.student_name}需要重点加强基础学习")
            elif progress.improvement_trend < -5:
                recommendations.append(f"{progress.student_name}近期表现有所下降，需要关注")
        
        # 分析团队合作机会
        strengths = []
        for student_id, progress in student_data.items():
            strengths.extend(progress.strength_dimensions)
        
        if len(set(strengths)) >= 2:
            recommendations.append("学生们在不同维度各有优势，可以考虑组建互补的学习小组")
        
        return recommendations
    
    def _save_comparison_analysis(self, comparison_result: Dict[str, Any], student_ids: List[str]):
        """保存比较分析结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO comparison_analysis (
                comparison_type, student_ids, analysis_result, insights, recommendations
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            "multi_student",
            json.dumps(student_ids),
            json.dumps(comparison_result),
            json.dumps(comparison_result.get("insights", [])),
            json.dumps(comparison_result.get("recommendations", []))
        ))
        
        conn.commit()
        conn.close()
    
    def generate_progress_report(self, student_id: str, output_path: str = None) -> str:
        """
        生成学生进度报告
        
        Args:
            student_id: 学生ID
            output_path: 输出路径
            
        Returns:
            报告内容
        """
        progress = self.get_student_progress(student_id)
        
        if not progress:
            return "未找到学生的评分历史记录"
        
        # 生成图表
        if output_path:
            self._generate_progress_charts(progress, output_path)
        
        # 生成文本报告
        report = f"""
# 学生学习进度报告

## 基本信息
- 学生ID: {progress.student_id}
- 学生姓名: {progress.student_name}
- 评估次数: {progress.total_assessments}
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 成绩概览
- 最新得分: {progress.latest_score}
- 历史最高分: {progress.best_score}
- 平均得分: {progress.average_score:.2f}
- 改进趋势: {progress.improvement_trend:+.1f}分

## 能力分析
### 强项维度
{', '.join(progress.strength_dimensions) if progress.strength_dimensions else '暂无明显强项'}

### 需要提升的维度
{', '.join(progress.weak_dimensions) if progress.weak_dimensions else '各维度发展均衡'}

## 改进建议
{chr(10).join(f"- {suggestion}" for suggestion in progress.improvement_suggestions)}

## 详细历史记录
"""
        
        for i, record in enumerate(progress.scoring_history[:5], 1):
            report += f"""
### 第{i}次评估 ({record['assessment_date']})
- 总分: {record['total_score']}
- 学习态度: {record['learning_attitude_score']}分
- 自学能力: {record['self_study_score']}分  
- 算法基础: {record['algorithm_score']}分
- 团队合作: {record['teamwork_score']}分
- 综合评价: {record['overall_evaluation']}
"""
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def _generate_progress_charts(self, progress: StudentProgress, output_path: str):
        """生成进度图表"""
        # 创建图表目录
        chart_dir = Path(output_path).parent / "charts"
        chart_dir.mkdir(exist_ok=True)
        
        # 1. 总分趋势图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 总分趋势
        dates = [datetime.fromisoformat(record['assessment_date']).strftime('%m-%d') 
                for record in progress.scoring_history[:10]]
        scores = [record['total_score'] for record in progress.scoring_history[:10]]
        
        ax1.plot(range(len(dates)), scores, marker='o', linewidth=2, markersize=6)
        ax1.set_title('总分变化趋势')
        ax1.set_xlabel('评估次数')
        ax1.set_ylabel('分数')
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(range(len(dates)))
        ax1.set_xticklabels(dates, rotation=45)
        
        # 维度对比
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        latest_record = progress.scoring_history[0] if progress.scoring_history else None
        
        if latest_record:
            dimension_scores = [
                latest_record['learning_attitude_score'],
                latest_record['self_study_score'],
                latest_record['algorithm_score'],
                latest_record['teamwork_score']
            ]
            
            bars = ax2.bar(dimensions, dimension_scores, color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'])
            ax2.set_title('各维度分数对比')
            ax2.set_ylabel('分数')
            ax2.set_ylim(0, 25)
            
            # 添加数值标签
            for bar, score in zip(bars, dimension_scores):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                        str(score), ha='center', va='bottom')
        
        # 雷达图
        if latest_record:
            angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
            angles += angles[:1]
            
            values = dimension_scores + [dimension_scores[0]]
            
            ax3.remove()
            ax3 = fig.add_subplot(2, 2, 3, projection='polar')
            ax3.plot(angles, values, 'o-', linewidth=2)
            ax3.fill(angles, values, alpha=0.25)
            ax3.set_xticks(angles[:-1])
            ax3.set_xticklabels(dimensions)
            ax3.set_ylim(0, 25)
            ax3.set_title('能力雷达图')
        
        # 进步分析
        if len(scores) >= 2:
            improvements = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
            ax4.bar(range(len(improvements)), improvements, 
                   color=['green' if imp > 0 else 'red' for imp in improvements])
            ax4.set_title('每次评估进步情况')
            ax4.set_xlabel('评估间隔')
            ax4.set_ylabel('分数变化')
            ax4.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax4.grid(True, alpha=0.3)
        
        plt.suptitle(f'{progress.student_name} 学习进度分析', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # 保存图表
        chart_path = chart_dir / f"progress_{student_id}_{datetime.now().strftime('%Y%m%d')}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def get_class_statistics(self, limit: int = 50) -> Dict[str, Any]:
        """
        获取班级统计信息
        
        Args:
            limit: 学生数量限制
            
        Returns:
            统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有学生的最新评分
        cursor.execute('''
            SELECT s.student_id, s.student_name, h.total_score, h.assessment_date,
                   h.learning_attitude_score, h.self_study_score, h.algorithm_score, h.teamwork_score
            FROM students s
            LEFT JOIN scoring_history h ON s.student_id = h.student_id
            WHERE h.id IN (
                SELECT MAX(id) FROM scoring_history GROUP BY student_id
            )
            ORDER BY h.total_score DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"error": "没有找到学生数据"}
        
        # 转换为DataFrame
        df = pd.DataFrame(rows, columns=[
            'student_id', 'student_name', 'total_score', 'assessment_date',
            'learning_attitude_score', 'self_study_score', 'algorithm_score', 'teamwork_score'
        ])
        
        # 计算统计数据
        stats = {
            "total_students": len(df),
            "average_score": df['total_score'].mean(),
            "highest_score": df['total_score'].max(),
            "lowest_score": df['total_score'].min(),
            "score_std": df['total_score'].std(),
            "pass_rate": (df['total_score'] >= 60).sum() / len(df) * 100,
            "excellent_rate": (df['total_score'] >= 90).sum() / len(df) * 100,
            "dimension_averages": {
                "学习态度": df['learning_attitude_score'].mean(),
                "自学能力": df['self_study_score'].mean(),
                "算法基础": df['algorithm_score'].mean(),
                "团队合作能力": df['teamwork_score'].mean()
            },
            "top_students": df.nlargest(5, 'total_score')[['student_name', 'total_score']].to_dict('records'),
            "bottom_students": df.nsmallest(5, 'total_score')[['student_name', 'total_score']].to_dict('records')
        }
        
        return stats


def main():
    """测试历史记录管理功能"""
    import json
    
    manager = HistoryManager()
    
    # 模拟保存一些测试数据
    test_results = [
        {
            "学生信息": {"id": "001", "name": "张三"},
            "总分": 85,
            "学习态度": {"分数": 22, "理由": "学习态度积极"},
            "自学能力": {"分数": 20, "理由": "自学能力较强"},
            "算法基础": {"分数": 18, "理由": "算法基础良好"},
            "团队合作能力": {"分数": 25, "理由": "团队合作优秀"},
            "综合评价": "综合表现良好"
        },
        {
            "学生信息": {"id": "002", "name": "李四"},
            "总分": 78,
            "学习态度": {"分数": 20, "理由": "学习态度较好"},
            "自学能力": {"分数": 18, "理由": "自学能力一般"},
            "算法基础": {"分数": 20, "理由": "算法基础不错"},
            "团队合作能力": {"分数": 20, "理由": "团队合作良好"},
            "综合评价": "需要继续努力"
        }
    ]
    
    for result in test_results:
        manager.save_scoring_result(result, "test_session")
    
    # 测试获取学生进度
    progress = manager.get_student_progress("001")
    if progress:
        print(f"学生 {progress.student_name} 的进度分析:")
        print(f"最新分数: {progress.latest_score}")
        print(f"改进趋势: {progress.improvement_trend}")
        print(f"强项: {progress.strength_dimensions}")
        print(f"弱项: {progress.weak_dimensions}")
        print(f"改进建议: {progress.improvement_suggestions}")
    
    # 测试学生比较
    comparison = manager.compare_students(["001", "002"])
    print("\n学生比较结果:")
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    
    # 生成进度报告
    report = manager.generate_progress_report("001", "progress_report_001.md")
    print("\n进度报告已生成")
    
    # 获取班级统计
    class_stats = manager.get_class_statistics()
    print("\n班级统计:")
    print(json.dumps(class_stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()