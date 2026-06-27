"""
API网关
提供完整的REST API接口，支持第三方集成
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify, g
from functools import wraps
import traceback

from file_reader import FileReader
from enhanced_api_client import get_enhanced_api_client
from result_processor import ResultProcessor
from enhanced_security import require_auth, require_permission, get_security_manager
from config_manager import get_config_manager
from async_task_manager import get_task_manager, TaskStatus, TaskPriority

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIGateway:
    """API网关类"""
    
    def __init__(self, app: Flask):
        """
        初始化API网关
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self._register_routes()
        logger.info("API网关已初始化")
    
    def _register_routes(self):
        """注册API路由"""
        
        # 健康检查端点（无需认证）
        @self.app.route('/health')
        def health_check():
            """健康检查"""
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

        # API版本信息
        @self.app.route('/api/v1/info')
        def api_info():
            """获取API信息"""
            return jsonify({
                'name': 'JudgeAI API',
                'version': '1.0.0',
                'description': '算法竞赛团队AI评分系统API',
                'endpoints': {
                    'authentication': '/api/v1/auth/*',
                    'scoring': '/api/v1/scoring/*',
                    'config': '/api/v1/config/*',
                    'tasks': '/api/v1/tasks/*',
                    'files': '/api/v1/files/*'
                },
                'documentation': '/api/v1/docs'
            })
        
        # 认证相关API
        @self.app.route('/api/v1/auth/login', methods=['POST'])
        def api_login():
            """用户登录API"""
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                
                if not username or not password:
                    return jsonify({
                        'success': False,
                        'error': '用户名和密码不能为空',
                        'error_code': 'MISSING_CREDENTIALS'
                    }), 400
                
                security_manager = get_security_manager()
                user = security_manager.authenticate_user(username, password)
                
                if not user:
                    security_manager.log_audit(
                        user_id=0,
                        action='api_login_failed',
                        resource='auth',
                        details={'username': username, 'ip': request.remote_addr},
                        success=False
                    )
                    return jsonify({
                        'success': False,
                        'error': '用户名或密码错误',
                        'error_code': 'INVALID_CREDENTIALS'
                    }), 401
                
                # 生成Token
                token = security_manager.generate_token(user)
                
                # 记录审计日志
                security_manager.log_audit(
                    user_id=user.id,
                    action='api_login_success',
                    resource='auth',
                    details={'ip': request.remote_addr}
                )
                
                return jsonify({
                    'success': True,
                    'data': {
                        'token': token,
                        'user': user.to_dict(),
                        'expires_in': 24 * 3600  # 24小时
                    }
                })
                
            except Exception as e:
                logger.error(f"登录API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        # 评分相关API
        @self.app.route('/api/v1/scoring/submit', methods=['POST'])
        @require_auth
        @require_permission('write')
        def api_submit_scoring():
            """提交评分任务API"""
            try:
                data = request.get_json()
                students = data.get('students', [])
                template_id = data.get('template_id')
                async_mode = data.get('async', True)
                
                if not students:
                    return jsonify({
                        'success': False,
                        'error': '学生数据不能为空',
                        'error_code': 'MISSING_STUDENTS'
                    }), 400
                
                # 验证学生数据格式
                for i, student in enumerate(students):
                    if not isinstance(student, dict):
                        return jsonify({
                            'success': False,
                            'error': f'第{i+1}个学生数据格式错误',
                            'error_code': 'INVALID_STUDENT_FORMAT'
                        }), 400
                    
                    if not student.get('name') and not student.get('id'):
                        return jsonify({
                            'success': False,
                            'error': f'第{i+1}个学生缺少姓名或ID',
                            'error_code': 'MISSING_STUDENT_INFO'
                        }), 400
                
                # 添加模板ID到学生信息
                if template_id:
                    for student in students:
                        student['template_id'] = template_id
                
                user = g.current_user
                api_key = os.getenv("DASHSCOPE_API_KEY")
                
                if async_mode:
                    # 异步模式
                    task_manager = get_task_manager()
                    
                    # 保存学生数据到临时文件
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(students, f, ensure_ascii=False, indent=2)
                        temp_file = f.name
                    
                    # 提交异步任务
                    task_parameters = {
                        'filepath': temp_file,
                        'api_key': api_key,
                        'batch_size': 10,
                        'user_id': user.id
                    }
                    
                    task_id = task_manager.submit_task(
                        task_type='batch_scoring',
                        parameters=task_parameters,
                        priority=TaskPriority.HIGH if len(students) > 50 else TaskPriority.NORMAL
                    )
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'task_id': task_id,
                            'status': 'submitted',
                            'total_students': len(students),
                            'async': True
                        }
                    })
                
                else:
                    # 同步模式
                    api_client = get_enhanced_api_client(api_key=api_key)
                    results = api_client.score_students_batch(students)
                    
                    return jsonify({
                        'success': True,
                        'data': {
                            'results': results,
                            'total_students': len(students),
                            'async': False
                        }
                    })
                
            except Exception as e:
                logger.error(f"提交评分API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR',
                    'details': str(e)
                }), 500
        
        @self.app.route('/api/v1/scoring/student', methods=['POST'])
        @require_auth
        @require_permission('write')
        def api_score_student():
            """评分单个学生API"""
            try:
                data = request.get_json()
                student = data.get('student')
                template_id = data.get('template_id')
                
                if not student:
                    return jsonify({
                        'success': False,
                        'error': '学生数据不能为空',
                        'error_code': 'MISSING_STUDENT'
                    }), 400
                
                if not student.get('name') and not student.get('id'):
                    return jsonify({
                        'success': False,
                        'error': '学生缺少姓名或ID',
                        'error_code': 'MISSING_STUDENT_INFO'
                    }), 400
                
                # 添加模板ID
                if template_id:
                    student['template_id'] = template_id
                
                api_key = os.getenv("DASHSCOPE_API_KEY")
                api_client = get_enhanced_api_client(api_key=api_key)
                
                result = api_client.score_student(student)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'result': result
                    }
                })
                
            except Exception as e:
                logger.error(f"评分学生API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR',
                    'details': str(e)
                }), 500
        
        # 配置相关API
        @self.app.route('/api/v1/config/templates', methods=['GET'])
        @require_auth
        @require_permission('read')
        def api_get_templates():
            """获取评分模板列表API"""
            try:
                config_manager = get_config_manager()
                templates = config_manager.list_templates(active_only=True)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'templates': [tpl.__dict__ for tpl in templates]
                    }
                })
                
            except Exception as e:
                logger.error(f"获取模板API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        @self.app.route('/api/v1/config/templates/<template_id>', methods=['GET'])
        @require_auth
        @require_permission('read')
        def api_get_template(template_id):
            """获取单个评分模板API"""
            try:
                config_manager = get_config_manager()
                template = config_manager.get_template(template_id)
                
                if not template:
                    return jsonify({
                        'success': False,
                        'error': '模板不存在',
                        'error_code': 'TEMPLATE_NOT_FOUND'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'data': {
                        'template': template.__dict__
                    }
                })
                
            except Exception as e:
                logger.error(f"获取模板详情API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        @self.app.route('/api/v1/config/dimensions', methods=['GET'])
        @require_auth
        @require_permission('read')
        def api_get_dimensions():
            """获取评分维度列表API"""
            try:
                config_manager = get_config_manager()
                dimensions = config_manager.list_custom_dimensions(active_only=True)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'dimensions': [dim.__dict__ for dim in dimensions]
                    }
                })
                
            except Exception as e:
                logger.error(f"获取维度API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        # 任务相关API
        @self.app.route('/api/v1/tasks/<task_id>', methods=['GET'])
        @require_auth
        @require_permission('read')
        def api_get_task(task_id):
            """获取任务状态API"""
            try:
                task_manager = get_task_manager()
                task = task_manager.get_task_status(task_id)
                
                if not task:
                    return jsonify({
                        'success': False,
                        'error': '任务不存在',
                        'error_code': 'TASK_NOT_FOUND'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'data': {
                        'task': {
                            'task_id': task.task_id,
                            'task_type': task.task_type,
                            'status': task.status.value,
                            'priority': task.priority.name,
                            'created_at': task.created_at.isoformat(),
                            'started_at': task.started_at.isoformat() if task.started_at else None,
                            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                            'progress': {
                                'current': task.progress.current,
                                'total': task.progress.total,
                                'percentage': task.progress.percentage,
                                'message': task.progress.message,
                                'estimated_remaining': task.progress.estimated_remaining
                            },
                            'result': task.result.__dict__ if task.result else None
                        }
                    }
                })
                
            except Exception as e:
                logger.error(f"获取任务API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        @self.app.route('/api/v1/tasks', methods=['GET'])
        @require_auth
        @require_permission('read')
        def api_list_tasks():
            """获取任务列表API"""
            try:
                status_filter = request.args.get('status')
                limit = int(request.args.get('limit', 20))
                
                task_manager = get_task_manager()
                
                # 转换状态过滤
                task_status = None
                if status_filter:
                    try:
                        task_status = TaskStatus(status_filter)
                    except ValueError:
                        return jsonify({
                            'success': False,
                            'error': f'无效的状态值: {status_filter}',
                            'error_code': 'INVALID_STATUS'
                        }), 400
                
                tasks = task_manager.get_task_list(status=task_status, limit=limit)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'tasks': [
                            {
                                'task_id': task.task_id,
                                'task_type': task.task_type,
                                'status': task.status.value,
                                'priority': task.priority.name,
                                'created_at': task.created_at.isoformat(),
                                'started_at': task.started_at.isoformat() if task.started_at else None,
                                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                                'progress': {
                                    'current': task.progress.current,
                                    'total': task.progress.total,
                                    'percentage': task.progress.percentage,
                                    'message': task.progress.message
                                }
                            }
                            for task in tasks
                        ]
                    }
                })
                
            except Exception as e:
                logger.error(f"获取任务列表API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        # 文件处理API
        @self.app.route('/api/v1/files/upload', methods=['POST'])
        @require_auth
        @require_permission('write')
        def api_upload_file():
            """文件上传API"""
            try:
                if 'file' not in request.files:
                    return jsonify({
                        'success': False,
                        'error': '没有文件',
                        'error_code': 'NO_FILE'
                    }), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        'success': False,
                        'error': '没有选择文件',
                        'error_code': 'NO_FILE_SELECTED'
                    }), 400
                
                # 检查文件类型
                allowed_extensions = {'csv', 'xlsx', 'xls', 'json', 'txt'}
                if not ('.' in file.filename and 
                       file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                    return jsonify({
                        'success': False,
                        'error': '不支持的文件格式',
                        'error_code': 'UNSUPPORTED_FILE_TYPE'
                    }), 400
                
                # 保存文件
                import tempfile
                import uuid
                
                file_id = str(uuid.uuid4())
                temp_dir = tempfile.mkdtemp()
                file_path = os.path.join(temp_dir, file.filename)
                file.save(file_path)
                
                # 读取文件
                file_reader = FileReader()
                students = file_reader.read_file(file_path)
                validated_students = file_reader.validate_data(students)
                
                if not validated_students:
                    return jsonify({
                        'success': False,
                        'error': '文件中没有找到有效的学生数据',
                        'error_code': 'NO_VALID_DATA'
                    }), 400
                
                return jsonify({
                    'success': True,
                    'data': {
                        'file_id': file_id,
                        'filename': file.filename,
                        'total_records': len(students),
                        'valid_records': len(validated_students),
                        'preview': validated_students[:5]  # 前5条预览
                    }
                })
                
            except Exception as e:
                logger.error(f"文件上传API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR',
                    'details': str(e)
                }), 500
        
        # 统计信息API
        @self.app.route('/api/v1/stats', methods=['GET'])
        @require_auth
        @require_permission('read')
        def api_get_stats():
            """获取系统统计信息API"""
            try:
                # API统计
                api_client = get_enhanced_api_client()
                api_stats = api_client.get_stats()
                
                # 任务统计
                task_manager = get_task_manager()
                all_tasks = task_manager.get_task_list(limit=1000)
                
                task_stats = {
                    'total_tasks': len(all_tasks),
                    'completed_tasks': len([t for t in all_tasks if t.status == TaskStatus.COMPLETED]),
                    'running_tasks': len([t for t in all_tasks if t.status == TaskStatus.RUNNING]),
                    'failed_tasks': len([t for t in all_tasks if t.status == TaskStatus.FAILED])
                }
                
                # 配置统计
                config_manager = get_config_manager()
                config_stats = {
                    'total_templates': len(config_manager.list_templates()),
                    'total_dimensions': len(config_manager.list_custom_dimensions())
                }
                
                return jsonify({
                    'success': True,
                    'data': {
                        'api_stats': api_stats,
                        'task_stats': task_stats,
                        'config_stats': config_stats,
                        'system_info': {
                            'version': '1.0.0',
                            'uptime': 'N/A',  # 可以添加实际运行时间
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                })
                
            except Exception as e:
                logger.error(f"获取统计信息API错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        # Webhook支持
        @self.app.route('/api/v1/webhook/scoring-complete', methods=['POST'])
        def api_webhook_scoring_complete():
            """评分完成Webhook"""
            try:
                # 验证webhook签名（可选）
                signature = request.headers.get('X-Signature')
                if signature:
                    # 这里可以添加签名验证逻辑
                    pass
                
                data = request.get_json()
                task_id = data.get('task_id')
                status = data.get('status')
                results = data.get('results', [])
                
                if not task_id or not status:
                    return jsonify({
                        'success': False,
                        'error': '缺少必要参数',
                        'error_code': 'MISSING_PARAMETERS'
                    }), 400
                
                # 处理webhook逻辑
                logger.info(f"收到评分完成Webhook: 任务{task_id}, 状态{status}")
                
                # 这里可以添加：
                # 1. 发送通知
                # 2. 更新数据库
                # 3. 触发其他业务逻辑
                
                return jsonify({
                    'success': True,
                    'message': 'Webhook处理成功'
                })
                
            except Exception as e:
                logger.error(f"Webhook处理错误: {e}")
                return jsonify({
                    'success': False,
                    'error': '服务器内部错误',
                    'error_code': 'INTERNAL_ERROR'
                }), 500
        
        # 错误处理
        @self.app.errorhandler(404)
        def api_not_found(error):
            return jsonify({
                'success': False,
                'error': 'API端点不存在',
                'error_code': 'ENDPOINT_NOT_FOUND'
            }), 404
        
        @self.app.errorhandler(405)
        def api_method_not_allowed(error):
            return jsonify({
                'success': False,
                'error': '请求方法不允许',
                'error_code': 'METHOD_NOT_ALLOWED'
            }), 405
        
        @self.app.errorhandler(500)
        def api_internal_error(error):
            return jsonify({
                'success': False,
                'error': '服务器内部错误',
                'error_code': 'INTERNAL_ERROR'
            }), 500

def init_api_gateway(app: Flask):
    """初始化API网关"""
    return APIGateway(app)