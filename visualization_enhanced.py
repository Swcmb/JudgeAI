"""
增强数据可视化模块
提供更丰富的数据分析和可视化功能
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class EnhancedVisualization:
    """增强数据可视化类"""
    
    def __init__(self):
        self.colors = {
            'primary': '#007bff',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8',
            'secondary': '#6c757d'
        }
    
    def create_comprehensive_dashboard(self, results: List[Dict[str, Any]], output_path: str = None):
        """创建综合仪表板"""
        if output_path:
            self._create_matplotlib_dashboard(results, output_path)
        return self._create_plotly_dashboard(results)
    
    def _create_matplotlib_dashboard(self, results: List[Dict[str, Any]], output_path: str):
        """创建基于matplotlib的仪表板"""
        # 设置图表大小
        fig = plt.figure(figsize=(20, 24))
        gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
        
        # 提取数据
        successful_results = [r for r in results if not r.get('error', False)]
        if not successful_results:
            return
        
        total_scores = [r.get('总分', 0) for r in successful_results]
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        
        # 1. 总分分布直方图
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.hist(total_scores, bins=20, color=self.colors['primary'], alpha=0.7, edgecolor='black')
        ax1.set_title('总分分布', fontsize=14, fontweight='bold')
        ax1.set_xlabel('分数')
        ax1.set_ylabel('人数')
        ax1.grid(True, alpha=0.3)
        
        # 2. 等级分布饼图
        ax2 = fig.add_subplot(gs[0, 1])
        grades = self._calculate_grades(total_scores)
        ax2.pie(grades.values(), labels=grades.keys(), autopct='%1.1f%%', 
                colors=[self.colors['success'], self.colors['info'], self.colors['warning'], 
                       '#ff9800', self.colors['danger']])
        ax2.set_title('分数等级分布', fontsize=14, fontweight='bold')
        
        # 3. 四维度雷达图
        ax3 = fig.add_subplot(gs[0, 2], projection='polar')
        self._create_radar_chart(ax3, successful_results, dimensions)
        
        # 4. 各维度箱线图
        ax4 = fig.add_subplot(gs[1, 0])
        dimension_data = []
        for dim in dimensions:
            scores = []
            for r in successful_results:
                dim_data = r.get(dim, {})
                if isinstance(dim_data, dict) and dim_data.get('分数'):
                    scores.append(dim_data['分数'])
            dimension_data.append(scores)
        
        bp = ax4.boxplot(dimension_data, labels=dimensions, patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor(self.colors['info'])
            patch.set_alpha(0.7)
        ax4.set_title('各维度分数分布', fontsize=14, fontweight='bold')
        ax4.set_ylabel('分数')
        ax4.grid(True, alpha=0.3)
        
        # 5. 维度相关性热力图
        ax5 = fig.add_subplot(gs[1, 1])
        correlation_data = []
        for dim in dimensions:
            scores = []
            for r in successful_results:
                dim_data = r.get(dim, {})
                if isinstance(dim_data, dict) and dim_data.get('分数'):
                    scores.append(dim_data['分数'])
            correlation_data.append(scores)
        
        df_corr = pd.DataFrame(dict(zip(dimensions, correlation_data)))
        correlation_matrix = df_corr.corr()
        
        im = ax5.imshow(correlation_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
        ax5.set_xticks(range(len(dimensions)))
        ax5.set_yticks(range(len(dimensions)))
        ax5.set_xticklabels(dimensions, rotation=45)
        ax5.set_yticklabels(dimensions)
        ax5.set_title('维度相关性热力图', fontsize=14, fontweight='bold')
        
        # 添加数值标签
        for i in range(len(dimensions)):
            for j in range(len(dimensions)):
                text = ax5.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                               ha="center", va="center", color="black", fontweight='bold')
        
        # 6. 散点图矩阵
        ax6 = fig.add_subplot(gs[1, 2])
        self._create_scatter_matrix(ax6, successful_results, dimensions)
        
        # 7. 学生排名柱状图
        ax7 = fig.add_subplot(gs[2, :])
        sorted_results = sorted(successful_results, key=lambda x: x.get('总分', 0), reverse=True)
        top_10 = sorted_results[:10]
        
        names = [f"{r.get('学生信息', {}).get('name', f'学生{i+1}')} ({r.get('总分', 0)}分)" 
                for i, r in enumerate(top_10)]
        scores = [r.get('总分', 0) for r in top_10]
        
        bars = ax7.barh(range(len(names)), scores, color=self.colors['success'])
        ax7.set_yticks(range(len(names)))
        ax7.set_yticklabels(names)
        ax7.set_xlabel('分数')
        ax7.set_title('前10名学生排名', fontsize=14, fontweight='bold')
        ax7.grid(True, alpha=0.3, axis='x')
        
        # 添加数值标签
        for i, (bar, score) in enumerate(zip(bars, scores)):
            ax7.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                    str(score), ha='left', va='center', fontweight='bold')
        
        # 8. 时间序列图（如果有时序数据）
        ax8 = fig.add_subplot(gs[3, 0])
        ax8.plot(range(1, len(total_scores) + 1), total_scores, 
                marker='o', color=self.colors['primary'], linewidth=2, markersize=4)
        ax8.set_title('分数变化趋势', fontsize=14, fontweight='bold')
        ax8.set_xlabel('学生序号')
        ax8.set_ylabel('总分')
        ax8.grid(True, alpha=0.3)
        
        # 9. 统计摘要表
        ax9 = fig.add_subplot(gs[3, 1:])
        ax9.axis('off')
        
        # 计算统计数据
        stats_data = []
        for dim in dimensions + ['总分']:
            if dim == '总分':
                scores = total_scores
            else:
                scores = []
                for r in successful_results:
                    dim_data = r.get(dim, {})
                    if isinstance(dim_data, dict) and dim_data.get('分数'):
                        scores.append(dim_data['分数'])
            
            if scores:
                avg = np.mean(scores)
                std = np.std(scores)
                median = np.median(scores)
                q1, q3 = np.percentile(scores, [25, 75])
                max_score = np.max(scores)
                min_score = np.min(scores)
                
                stats_data.append([
                    dim,
                    f'{avg:.2f}',
                    f'{std:.2f}',
                    f'{median:.2f}',
                    f'{q1:.2f}',
                    f'{q3:.2f}',
                    f'{min_score}',
                    f'{max_score}'
                ])
        
        # 创建表格
        table = ax9.table(cellText=stats_data,
                        colLabels=['维度', '平均分', '标准差', '中位数', 'Q1', 'Q3', '最低分', '最高分'],
                        cellLoc='center',
                        loc='center',
                        bbox=[0, 0, 1, 1])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # 设置表格样式
        for i in range(len(stats_data[0]) + 1):
            for j in range(len(stats_data) + 1):
                cell = table[(j, i)]
                if i == 0 or j == 0:
                    cell.set_facecolor(self.colors['primary'])
                    cell.set_text_props(weight='bold', color='white')
                else:
                    cell.set_facecolor('#f8f9fa')
        
        ax9.set_title('详细统计摘要', fontsize=14, fontweight='bold', pad=20)
        
        plt.suptitle('算法竞赛团队AI评分系统 - 综合分析报告', fontsize=18, fontweight='bold', y=0.98)
        
        # 保存图表
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
    
    def _create_radar_chart(self, ax, results: List[Dict[str, Any]], dimensions: List[str]):
        """创建雷达图"""
        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        angles += angles[:1]  # 闭合
        
        # 计算各维度平均分
        avg_scores = []
        for dim in dimensions:
            scores = []
            for r in results:
                dim_data = r.get(dim, {})
                if isinstance(dim_data, dict) and dim_data.get('分数'):
                    scores.append(dim_data['分数'])
            avg_scores.append(np.mean(scores) if scores else 0)
        
        avg_scores += avg_scores[:1]  # 闭合
        
        # 绘制雷达图
        ax.plot(angles, avg_scores, 'o-', linewidth=2, color=self.colors['primary'], label='平均分')
        ax.fill(angles, avg_scores, alpha=0.25, color=self.colors['primary'])
        
        # 添加完美分数参考线
        perfect_scores = [25] * len(dimensions) + [25]
        ax.plot(angles, perfect_scores, '--', linewidth=1, color=self.colors['secondary'], alpha=0.7, label='满分')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dimensions)
        ax.set_ylim(0, 25)
        ax.set_title('四维度能力雷达图', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True)
        ax.legend()
    
    def _create_scatter_matrix(self, ax, results: List[Dict[str, Any]], dimensions: List[str]):
        """创建简化版散点图"""
        # 选择两个主要维度进行对比
        dim1, dim2 = dimensions[0], dimensions[1]
        
        scores1 = []
        scores2 = []
        
        for r in results:
            data1 = r.get(dim1, {})
            data2 = r.get(dim2, {})
            if (isinstance(data1, dict) and data1.get('分数') and
                isinstance(data2, dict) and data2.get('分数')):
                scores1.append(data1['分数'])
                scores2.append(data2['分数'])
        
        if scores1 and scores2:
            ax.scatter(scores1, scores2, alpha=0.6, color=self.colors['info'], s=50)
            ax.set_xlabel(dim1)
            ax.set_ylabel(dim2)
            ax.set_title(f'{dim1} vs {dim2}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # 添加趋势线
            z = np.polyfit(scores1, scores2, 1)
            p = np.poly1d(z)
            ax.plot(scores1, p(scores1), "r--", alpha=0.8)
    
    def _calculate_grades(self, scores: List[int]) -> Dict[str, int]:
        """计算分数等级"""
        grades = {
            '优秀 (90-100)': 0,
            '良好 (80-89)': 0,
            '中等 (70-79)': 0,
            '及格 (60-69)': 0,
            '不及格 (0-59)': 0
        }
        
        for score in scores:
            if score >= 90:
                grades['优秀 (90-100)'] += 1
            elif score >= 80:
                grades['良好 (80-89)'] += 1
            elif score >= 70:
                grades['中等 (70-79)'] += 1
            elif score >= 60:
                grades['及格 (60-69)'] += 1
            else:
                grades['不及格 (0-59)'] += 1
        
        return grades
    
    def _create_plotly_dashboard(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建基于Plotly的交互式仪表板"""
        successful_results = [r for r in results if not r.get('error', False)]
        if not successful_results:
            return {}
        
        total_scores = [r.get('总分', 0) for r in successful_results]
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        
        # 1. 分数分布直方图
        hist_fig = px.histogram(
            x=total_scores,
            nbins=20,
            title="总分分布",
            labels={'x': '分数', 'y': '人数'},
            color_discrete_sequence=[self.colors['primary']]
        )
        
        # 2. 雷达图
        avg_scores = []
        for dim in dimensions:
            scores = []
            for r in successful_results:
                dim_data = r.get(dim, {})
                if isinstance(dim_data, dict) and dim_data.get('分数'):
                    scores.append(dim_data['分数'])
            avg_scores.append(np.mean(scores) if scores else 0)
        
        radar_fig = go.Figure()
        radar_fig.add_trace(go.Scatterpolar(
            r=avg_scores + [avg_scores[0]],
            theta=dimensions + [dimensions[0]],
            fill='toself',
            name='平均分',
            line_color=self.colors['primary']
        ))
        radar_fig.add_trace(go.Scatterpolar(
            r=[25] * 5,
            theta=dimensions + [dimensions[0]],
            fill='toself',
            name='满分',
            line_dash='dash',
            line_color=self.colors['secondary']
        ))
        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 25]
                )),
            showlegend=True,
            title="四维度能力雷达图"
        )
        
        # 3. 3D散点图
        fig_3d = go.Figure()
        
        # 选择前三个维度
        dim_scores = {}
        for i, dim in enumerate(dimensions[:3]):
            scores = []
            for r in successful_results:
                dim_data = r.get(dim, {})
                if isinstance(dim_data, dict) and dim_data.get('分数'):
                    scores.append(dim_data['分数'])
                else:
                    scores.append(0)
            dim_scores[dim] = scores
        
        fig_3d.add_trace(go.Scatter3d(
            x=dim_scores[dimensions[0]],
            y=dim_scores[dimensions[1]],
            z=dim_scores[dimensions[2]],
            mode='markers',
            marker=dict(
                size=5,
                color=total_scores,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="总分")
            ),
            text=[f"总分: {score}" for score in total_scores],
            name="学生分布"
        ))
        
        fig_3d.update_layout(
            scene=dict(
                xaxis_title=dimensions[0],
                yaxis_title=dimensions[1],
                zaxis_title=dimensions[2]
            ),
            title="三维维度分布图"
        )
        
        return {
            'histogram': hist_fig.to_html(include_plotlyjs='cdn'),
            'radar': radar_fig.to_html(include_plotlyjs='cdn'),
            '3d_scatter': fig_3d.to_html(include_plotlyjs='cdn')
        }
    
    def create_student_comparison_chart(self, results: List[Dict[str, Any]], student_ids: List[str]) -> str:
        """创建学生对比图表"""
        successful_results = [r for r in results if not r.get('error', False)]
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        
        # 筛选指定学生
        selected_results = [r for r in successful_results 
                          if r.get('学生信息', {}).get('id') in student_ids]
        
        if not selected_results:
            return ""
        
        fig = go.Figure()
        
        for result in selected_results:
            student_name = result.get('学生信息', {}).get('name', '未知学生')
            scores = []
            
            for dim in dimensions:
                dim_data = result.get(dim, {})
                if isinstance(dim_data, dict) and dim_data.get('分数'):
                    scores.append(dim_data['分数'])
                else:
                    scores.append(0)
            
            fig.add_trace(go.Scatterpolar(
                r=scores + [scores[0]],
                theta=dimensions + [dimensions[0]],
                fill='toself',
                name=student_name
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 25]
                )),
            showlegend=True,
            title="学生能力对比图"
        )
        
        return fig.to_html(include_plotlyjs='cdn')
    
    def export_detailed_report(self, results: List[Dict[str, Any]], output_path: str):
        """导出详细分析报告"""
        successful_results = [r for r in results if not r.get('error', False)]
        if not successful_results:
            return
        
        # 创建HTML报告
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>算法竞赛团队AI评分系统 - 详细分析报告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; color: #007bff; margin-bottom: 30px; }}
                .section {{ margin: 30px 0; }}
                .stats-table {{ border-collapse: collapse; width: 100%; }}
                .stats-table th, .stats-table td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                .stats-table th {{ background-color: #007bff; color: white; }}
                .student-card {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .high-score {{ background-color: #d4edda; }}
                .low-score {{ background-color: #f8d7da; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>算法竞赛团队AI评分系统</h1>
                <h2>详细分析报告</h2>
                <p>生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h3>总体统计</h3>
                {self._generate_statistics_html(successful_results)}
            </div>
            
            <div class="section">
                <h3>优秀学生展示 (前10名)</h3>
                {self._generate_top_students_html(successful_results)}
            </div>
            
            <div class="section">
                <h3>需要关注的学生 (后5名)</h3>
                {self._generate_bottom_students_html(successful_results)}
            </div>
            
            <div class="section">
                <h3>详细评分数据</h3>
                {self._generate_detailed_table_html(successful_results)}
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_statistics_html(self, results: List[Dict[str, Any]]) -> str:
        """生成统计信息的HTML"""
        total_scores = [r.get('总分', 0) for r in results]
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        
        stats_html = f"""
        <p><strong>总学生数:</strong> {len(results)}</p>
        <p><strong>平均分:</strong> {np.mean(total_scores):.2f}</p>
        <p><strong>最高分:</strong> {max(total_scores)}</p>
        <p><strong>最低分:</strong> {min(total_scores)}</p>
        <p><strong>标准差:</strong> {np.std(total_scores):.2f}</p>
        """
        
        return stats_html
    
    def _generate_top_students_html(self, results: List[Dict[str, Any]]) -> str:
        """生成优秀学生HTML"""
        sorted_results = sorted(results, key=lambda x: x.get('总分', 0), reverse=True)
        top_10 = sorted_results[:10]
        
        html = ""
        for i, result in enumerate(top_10):
            student_name = result.get('学生信息', {}).get('name', f'学生{i+1}')
            total_score = result.get('总分', 0)
            evaluation = result.get('综合评价', '暂无评价')
            
            html += f"""
            <div class="student-card high-score">
                <h4>第{i+1}名: {student_name}</h4>
                <p><strong>总分:</strong> {total_score}</p>
                <p><strong>综合评价:</strong> {evaluation}</p>
            </div>
            """
        
        return html
    
    def _generate_bottom_students_html(self, results: List[Dict[str, Any]]) -> str:
        """生成需要关注的学生HTML"""
        sorted_results = sorted(results, key=lambda x: x.get('总分', 0))
        bottom_5 = sorted_results[:5]
        
        html = ""
        for i, result in enumerate(bottom_5):
            student_name = result.get('学生信息', {}).get('name', f'学生{i+1}')
            total_score = result.get('总分', 0)
            evaluation = result.get('综合评价', '暂无评价')
            
            html += f"""
            <div class="student-card low-score">
                <h4>倒数第{i+1}名: {student_name}</h4>
                <p><strong>总分:</strong> {total_score}</p>
                <p><strong>综合评价:</strong> {evaluation}</p>
            </div>
            """
        
        return html
    
    def _generate_detailed_table_html(self, results: List[Dict[str, Any]]) -> str:
        """生成详细表格HTML"""
        dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
        
        html = """
        <table class="stats-table">
            <thead>
                <tr>
                    <th>姓名</th>
                    <th>学号</th>
        """
        
        for dim in dimensions:
            html += f"<th>{dim}</th>"
        
        html += "<th>总分</th><th>综合评价</th></tr></thead><tbody>"
        
        for result in results:
            student_name = result.get('学生信息', {}).get('name', '-')
            student_id = result.get('学生信息', {}).get('id', '-')
            total_score = result.get('总分', 0)
            evaluation = result.get('综合评价', '暂无评价')
            
            html += f"""
            <tr>
                <td>{student_name}</td>
                <td>{student_id}</td>
            """
            
            for dim in dimensions:
                dim_data = result.get(dim, {})
                score = dim_data.get('分数', 0) if isinstance(dim_data, dict) else 0
                html += f"<td>{score}</td>"
            
            html += f"<td>{total_score}</td><td>{evaluation}</td></tr>"
        
        html += "</tbody></table>"
        
        return html


def main():
    """测试增强可视化功能"""
    from result_processor import ResultProcessor
    import json
    
    # 读取示例结果数据
    try:
        with open('test_results.json', 'r', encoding='utf-8') as f:
            results = json.load(f).get('results', [])
    except FileNotFoundError:
        print("未找到测试数据，请先运行评分系统生成结果文件")
        return
    
    # 创建增强可视化
    viz = EnhancedVisualization()
    
    # 生成综合仪表板
    print("生成综合仪表板...")
    viz.create_comprehensive_dashboard(results, 'enhanced_dashboard.png')
    
    # 导出详细HTML报告
    print("生成详细HTML报告...")
    viz.export_detailed_report(results, 'detailed_report.html')
    
    # 创建学生对比图
    print("生成学生对比图...")
    if results:
        student_ids = [r.get('学生信息', {}).get('id') for r in results[:5]]
        comparison_html = viz.create_student_comparison_chart(results, student_ids)
        
        with open('student_comparison.html', 'w', encoding='utf-8') as f:
            f.write(comparison_html)
    
    print("增强可视化功能测试完成！")
    print("生成的文件:")
    print("- enhanced_dashboard.png: 综合仪表板")
    print("- detailed_report.html: 详细HTML报告")
    print("- student_comparison.html: 学生对比图")


if __name__ == "__main__":
    main()