"""
异步任务管理器
支持大文件异步处理和批量评分任务
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time

from file_reader import FileReader
from api_client import BaiLianAPIClient
from enhanced_api_client import EnhancedBaiLianAPIClient, get_enhanced_api_client
from result_processor import ResultProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class TaskProgress:
    """任务进度信息"""
    current: int = 0
    total: int = 0
    percentage: float = 0.0
    message: str = ""
    estimated_remaining: int = 0  # 预估剩余时间（秒）

@dataclass
class TaskResult:
    """任务结果信息"""
    success: bool = False
    data: Any = None
    error_message: str = ""
    execution_time: float = 0.0
    created_files: List[str] = None

    def __post_init__(self):
        if self.created_files is None:
            self.created_files = []

@dataclass
class AsyncTask:
    """异步任务数据类"""
    task_id: str
    task_type: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: TaskProgress = None
    result: TaskResult = None
    parameters: Dict[str, Any] = None
    callback_url: Optional[str] = None

    def __post_init__(self):
        if self.progress is None:
            self.progress = TaskProgress()
        if self.result is None:
            self.result = TaskResult()
        if self.parameters is None:
            self.parameters = {}

class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_workers: int = 4, max_queue_size: int = 100):
        """
        初始化异步任务管理器
        
        Args:
            max_workers: 最大工作线程数
            max_queue_size: 最大队列大小
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.tasks: Dict[str, AsyncTask] = {}
        self.task_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.workers: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
        
        # 任务处理器注册
        self.task_handlers: Dict[str, Callable] = {
            'batch_scoring': self._handle_batch_scoring,
            'file_processing': self._handle_file_processing,
            'data_analysis': self._handle_data_analysis
        }
        
        logger.info(f"异步任务管理器初始化完成，最大工作线程数: {max_workers}")

    def start(self):
        """启动任务管理器"""
        with self.lock:
            if self.running:
                logger.warning("任务管理器已在运行中")
                return
            
            self.running = True
            
            # 启动工作线程
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"TaskWorker-{i+1}",
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)
            
            logger.info(f"任务管理器已启动，启动了 {len(self.workers)} 个工作线程")

    def stop(self):
        """停止任务管理器"""
        with self.lock:
            if not self.running:
                logger.warning("任务管理器未在运行")
                return
            
            self.running = False
            
            # 等待所有工作线程结束
            for worker in self.workers:
                worker.join(timeout=5)
            
            self.workers.clear()
            logger.info("任务管理器已停止")

    def submit_task(self, 
                   task_type: str, 
                   parameters: Dict[str, Any],
                   priority: TaskPriority = TaskPriority.NORMAL,
                   callback_url: Optional[str] = None) -> str:
        """
        提交异步任务
        
        Args:
            task_type: 任务类型
            parameters: 任务参数
            priority: 任务优先级
            callback_url: 完成回调URL
            
        Returns:
            任务ID
        """
        if task_type not in self.task_handlers:
            raise ValueError(f"不支持的任务类型: {task_type}")
        
        task_id = str(uuid.uuid4())
        task = AsyncTask(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now(),
            parameters=parameters,
            callback_url=callback_url
        )
        
        with self.lock:
            self.tasks[task_id] = task
            
            # 使用优先级的负数作为排序键（PriorityQueue是最小堆）
            priority_value = -priority.value
            try:
                self.task_queue.put((priority_value, task_id), block=False)
                logger.info(f"任务已提交: {task_id}, 类型: {task_type}, 优先级: {priority.name}")
            except queue.Full:
                # 队列满了，移除任务
                del self.tasks[task_id]
                raise RuntimeError("任务队列已满，请稍后重试")
        
        return task_id

    def get_task_status(self, task_id: str) -> Optional[AsyncTask]:
        """获取任务状态"""
        with self.lock:
            return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"任务已取消: {task_id}")
            return True

    def get_task_list(self, 
                     status: Optional[TaskStatus] = None,
                     limit: int = 50) -> List[AsyncTask]:
        """
        获取任务列表
        
        Args:
            status: 过滤状态
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        with self.lock:
            tasks = list(self.tasks.values())
            
            # 状态过滤
            if status:
                tasks = [t for t in tasks if t.status == status]
            
            # 按创建时间倒序排序
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            return tasks[:limit]

    def cleanup_completed_tasks(self, days: int = 7):
        """清理已完成的任务"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                    and task.completed_at 
                    and task.completed_at < cutoff_date):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            logger.info(f"清理了 {len(tasks_to_remove)} 个过期任务")

    def _worker_loop(self):
        """工作线程主循环"""
        logger.info(f"工作线程 {threading.current_thread().name} 已启动")
        
        while self.running:
            try:
                # 获取任务（阻塞等待，超时1秒）
                priority_value, task_id = self.task_queue.get(timeout=1)
                
                with self.lock:
                    task = self.tasks.get(task_id)
                    if not task or task.status != TaskStatus.PENDING:
                        continue
                    
                    # 更新任务状态
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                
                # 执行任务
                self._execute_task(task)
                
                # 标记任务完成
                self.task_queue.task_done()
                
            except queue.Empty:
                # 超时，继续循环
                continue
            except Exception as e:
                logger.error(f"工作线程异常: {e}")
                continue
        
        logger.info(f"工作线程 {threading.current_thread().name} 已停止")

    def _execute_task(self, task: AsyncTask):
        """执行任务"""
        start_time = time.time()
        
        try:
            logger.info(f"开始执行任务: {task.task_id}, 类型: {task.task_type}")
            
            # 获取任务处理器
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"未找到任务处理器: {task.task_type}")
            
            # 执行任务
            result_data = handler(task.parameters, task.progress)
            
            # 更新任务结果
            execution_time = time.time() - start_time
            task.result = TaskResult(
                success=True,
                data=result_data,
                execution_time=execution_time
            )
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            logger.info(f"任务执行成功: {task.task_id}, 耗时: {execution_time:.2f}秒")
            
            # 执行回调
            if task.callback_url:
                self._execute_callback(task)
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            
            # 更新任务结果
            task.result = TaskResult(
                success=False,
                error_message=error_message,
                execution_time=execution_time
            )
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            logger.error(f"任务执行失败: {task.task_id}, 错误: {error_message}")

    def _execute_callback(self, task: AsyncTask):
        """执行任务完成回调"""
        try:
            import requests
            
            callback_data = {
                'task_id': task.task_id,
                'status': task.status.value,
                'result': asdict(task.result) if task.result else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            }
            
            response = requests.post(task.callback_url, json=callback_data, timeout=10)
            response.raise_for_status()
            
            logger.info(f"回调执行成功: {task.task_id}")
            
        except Exception as e:
            logger.error(f"回调执行失败: {task.task_id}, 错误: {e}")

    def _handle_batch_scoring(self, parameters: Dict[str, Any], progress: TaskProgress) -> Dict[str, Any]:
        """处理批量评分任务"""
        filepath = parameters.get('filepath')
        api_key = parameters.get('api_key')
        batch_size = parameters.get('batch_size', 10)
        
        if not filepath or not api_key:
            raise ValueError("缺少必要参数: filepath 或 api_key")
        
        # 读取文件
        file_reader = FileReader()
        students = file_reader.read_file(filepath)
        validated_students = file_reader.validate_data(students)
        
        if not validated_students:
            raise ValueError("文件中没有找到有效的学生数据")
        
        # 初始化增强版评分系统
        api_client = get_enhanced_api_client(
            api_key=api_key,
            enable_cache=True,
            cache_ttl=3600,  # 1小时缓存
            enable_batch=True,
            batch_size=5
        )
        result_processor = ResultProcessor()
        
        # 更新进度信息
        progress.total = len(validated_students)
        progress.current = 0
        progress.message = "开始批量评分..."
        
        results = []
        start_time = time.time()
        
        # 使用增强版API客户端的批量处理功能
        logger.info(f"开始批量评分，使用增强版API客户端，批量大小: {batch_size}")
        
        # 批量处理
        for i in range(0, len(validated_students), batch_size):
            batch = validated_students[i:i + batch_size]
            
            try:
                # 批量评分
                batch_results = api_client.score_students_batch(batch, use_cache=True)
                results.extend(batch_results)
                
                # 更新进度
                progress.current += len(batch)
                progress.percentage = (progress.current / progress.total) * 100
                
                # 估算剩余时间
                elapsed_time = time.time() - start_time
                if progress.current > 0:
                    avg_time_per_student = elapsed_time / progress.current
                    remaining_students = progress.total - progress.current
                    progress.estimated_remaining = int(avg_time_per_student * remaining_students)
                
                progress.message = f"已评分 {progress.current}/{progress.total} 个学生"
                
                # 获取API客户端统计信息
                api_stats = api_client.get_stats()
                logger.info(f"API统计: 总请求 {api_stats.get('total_requests', 0)}, "
                          f"缓存命中 {api_stats.get('cache_hits', 0)}, "
                          f"缓存命中率 {api_stats.get('cache_hit_rate', 0):.1f}%")
                
            except Exception as e:
                logger.error(f"批量评分失败: {e}")
                # 如果批量失败，尝试逐个评分
                for student in batch:
                    try:
                        result = api_client.score_student(student, use_cache=True)
                        results.append(result)
                        progress.current += 1
                    except Exception as individual_error:
                        logger.error(f"评分学生失败: {student.get('name', '未知')}, 错误: {individual_error}")
                        results.append({
                            'error': True,
                            'error_message': str(individual_error),
                            'student': student
                        })
                        progress.current += 1
                
                # 更新进度百分比
                progress.percentage = (progress.current / progress.total) * 100
                progress.message = f"已评分 {progress.current}/{progress.total} 个学生（部分失败）"
        
        # 保存结果
        output_dir = f"results/batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        saved_files = result_processor.save_all_formats(results, output_dir)
        
        return {
            'total_students': len(validated_students),
            'successful_count': len([r for r in results if not r.get('error')]),
            'failed_count': len([r for r in results if r.get('error')]),
            'results': results,
            'saved_files': saved_files,
            'output_dir': output_dir
        }

    def _handle_file_processing(self, parameters: Dict[str, Any], progress: TaskProgress) -> Dict[str, Any]:
        """处理文件处理任务"""
        filepath = parameters.get('filepath')
        processing_type = parameters.get('type', 'validate')
        
        if not filepath:
            raise ValueError("缺少必要参数: filepath")
        
        file_reader = FileReader()
        
        progress.message = "正在读取文件..."
        
        # 读取文件
        students = file_reader.read_file(filepath)
        
        progress.message = f"已读取 {len(students)} 条记录，正在验证..."
        
        if processing_type == 'validate':
            validated_students = file_reader.validate_data(students)
            
            return {
                'total_records': len(students),
                'valid_records': len(validated_students),
                'invalid_records': len(students) - len(validated_students),
                'validated_data': validated_students
            }
        
        elif processing_type == 'analyze':
            # 文件分析
            analysis = {
                'total_records': len(students),
                'columns': list(students[0].keys()) if students else [],
                'sample_data': students[:5] if students else [],
                'data_types': {col: type(students[0][col]).__name__ for col in students[0].keys()} if students else {}
            }
            
            return analysis
        
        else:
            raise ValueError(f"不支持的文件处理类型: {processing_type}")

    def _handle_data_analysis(self, parameters: Dict[str, Any], progress: TaskProgress) -> Dict[str, Any]:
        """处理数据分析任务"""
        results = parameters.get('results', [])
        analysis_type = parameters.get('type', 'basic')
        
        if not results:
            raise ValueError("缺少必要参数: results")
        
        progress.message = "正在分析数据..."
        
        successful_results = [r for r in results if not r.get('error')]
        
        if analysis_type == 'basic':
            # 基础统计分析
            if successful_results:
                total_scores = [r.get('总分', 0) for r in successful_results]
                
                # 维度分析
                dimensions = ['学习态度', '自学能力', '算法基础', '团队合作能力']
                dimension_stats = {}
                
                for dim in dimensions:
                    scores = []
                    for r in successful_results:
                        dim_data = r.get(dim, {})
                        if isinstance(dim_data, dict):
                            scores.append(dim_data.get('分数', 0))
                    
                    if scores:
                        dimension_stats[dim] = {
                            'average': sum(scores) / len(scores),
                            'max': max(scores),
                            'min': min(scores),
                            'count': len(scores)
                        }
                
                analysis = {
                    'total_count': len(results),
                    'successful_count': len(successful_results),
                    'failed_count': len(results) - len(successful_results),
                    'score_statistics': {
                        'average': sum(total_scores) / len(total_scores),
                        'max': max(total_scores),
                        'min': min(total_scores),
                        'count': len(total_scores)
                    },
                    'dimension_statistics': dimension_stats
                }
            else:
                analysis = {
                    'total_count': len(results),
                    'successful_count': 0,
                    'failed_count': len(results),
                    'error': '没有成功的评分结果'
                }
            
            return analysis
        
        elif analysis_type == 'advanced':
            # 高级分析
            # 这里可以添加更复杂的分析逻辑
            return {'message': '高级分析功能待实现'}
        
        else:
            raise ValueError(f"不支持的分析类型: {analysis_type}")

# 全局任务管理器实例
task_manager = None

def init_task_manager():
    """初始化任务管理器"""
    global task_manager
    if task_manager is None:
        task_manager = AsyncTaskManager()
        task_manager.start()
        logger.info("异步任务管理器已初始化")

def get_task_manager() -> AsyncTaskManager:
    """获取任务管理器实例"""
    global task_manager
    if task_manager is None:
        init_task_manager()
    return task_manager