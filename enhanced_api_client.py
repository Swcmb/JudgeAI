"""
增强版阿里云百炼API调用模块
支持缓存、批量请求和智能重试机制
"""

import os
import json
import time
import logging
import hashlib
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import sqlite3
from openai import OpenAI

from api_client import BaiLianAPIClient
from config_manager import get_config_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    timestamp: datetime
    ttl: int  # 生存时间（秒）
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)

class APICache:
    """API结果缓存管理器"""
    
    def __init__(self, db_path: str = "api_cache.db", default_ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            db_path: SQLite数据库路径
            default_ttl: 默认缓存时间（秒）
        """
        self.db_path = db_path
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
        
        # 初始化数据库
        self._init_database()
        
        logger.info(f"API缓存管理器已初始化，数据库路径: {db_path}")
    
    def _init_database(self):
        """初始化缓存数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS api_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ttl INTEGER NOT NULL
                )
            ''')
            conn.commit()
    
    def _generate_key(self, prompt: str, model: str) -> str:
        """生成缓存键"""
        content = f"{prompt}:{model}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        key = self._generate_key(prompt, model)
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        'SELECT data, timestamp, ttl FROM api_cache WHERE key = ?',
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    data_json, timestamp_str, ttl = row
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # 检查是否过期
                    if datetime.now() > timestamp + timedelta(seconds=ttl):
                        # 删除过期缓存
                        conn.execute('DELETE FROM api_cache WHERE key = ?', (key,))
                        conn.commit()
                        return None
                    
                    logger.debug(f"缓存命中: {key[:8]}...")
                    return json.loads(data_json)
                    
            except Exception as e:
                logger.error(f"获取缓存失败: {e}")
                return None
    
    def set(self, prompt: str, model: str, data: Dict[str, Any], ttl: Optional[int] = None):
        """设置缓存"""
        key = self._generate_key(prompt, model)
        ttl = ttl or self.default_ttl
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO api_cache (key, data, timestamp, ttl)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        key,
                        json.dumps(data, ensure_ascii=False),
                        datetime.now().isoformat(),
                        ttl
                    ))
                    conn.commit()
                    
                logger.debug(f"缓存已设置: {key[:8]}...")
                
            except Exception as e:
                logger.error(f"设置缓存失败: {e}")
    
    def clear(self, expired_only: bool = False):
        """清理缓存"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    if expired_only:
                        # 只清理过期缓存
                        cursor = conn.execute('''
                            SELECT key, timestamp, ttl FROM api_cache
                        ''')
                        expired_keys = []
                        
                        for key, timestamp_str, ttl in cursor.fetchall():
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if datetime.now() > timestamp + timedelta(seconds=ttl):
                                expired_keys.append(key)
                        
                        for key in expired_keys:
                            conn.execute('DELETE FROM api_cache WHERE key = ?', (key,))
                        
                        logger.info(f"清理了 {len(expired_keys)} 个过期缓存条目")
                    else:
                        # 清理所有缓存
                        cursor = conn.execute('DELETE FROM api_cache')
                        logger.info(f"清理了 {cursor.rowcount} 个缓存条目")
                    
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"清理缓存失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('SELECT COUNT(*) FROM api_cache')
                    total_count = cursor.fetchone()[0]
                    
                    cursor = conn.execute('''
                        SELECT COUNT(*) FROM api_cache 
                        WHERE datetime(timestamp, '+' || ttl || ' seconds') < datetime('now')
                    ''')
                    expired_count = cursor.fetchone()[0]
                    
                    return {
                        'total_entries': total_count,
                        'expired_entries': expired_count,
                        'valid_entries': total_count - expired_count
                    }
                    
            except Exception as e:
                logger.error(f"获取缓存统计失败: {e}")
                return {'error': str(e)}

class BatchProcessor:
    """批量请求处理器"""
    
    def __init__(self, batch_size: int = 5, delay_between_batches: float = 1.0):
        """
        初始化批量处理器
        
        Args:
            batch_size: 批量大小
            delay_between_batches: 批次间延迟（秒）
        """
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.request_times = []  # 记录请求时间
        
    def calculate_delay(self) -> float:
        """计算动态延迟时间"""
        now = time.time()
        
        # 移除超过1分钟的记录
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # 根据最近请求频率调整延迟
        if len(self.request_times) > 30:  # 1分钟内超过30次请求
            return self.delay_between_batches * 2
        elif len(self.request_times) > 20:  # 1分钟内超过20次请求
            return self.delay_between_batches * 1.5
        else:
            return self.delay_between_batches
    
    def process_batch(self, api_client: BaiLianAPIClient, prompts: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理API请求
        
        Args:
            api_client: API客户端
            prompts: 提示词列表
            
        Returns:
            结果列表
        """
        results = []
        
        for i in range(0, len(prompts), self.batch_size):
            batch = prompts[i:i + self.batch_size]
            batch_results = []
            
            for prompt in batch:
                try:
                    # 记录请求时间
                    self.request_times.append(time.time())
                    
                    # 调用API
                    result = api_client.call_api(prompt)
                    batch_results.append(result)
                    
                    # 计算延迟
                    delay = self.calculate_delay()
                    if delay > 0:
                        time.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"批量请求失败: {e}")
                    batch_results.append({'error': str(e)})
            
            results.extend(batch_results)
            
            # 批次间延迟
            if i + self.batch_size < len(prompts):
                time.sleep(self.delay_between_batches)
        
        return results

class EnhancedBaiLianAPIClient(BaiLianAPIClient):
    """增强版阿里云百炼API客户端"""
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 enable_cache: bool = True,
                 cache_ttl: int = 3600,
                 enable_batch: bool = True,
                 batch_size: int = 5):
        """
        初始化增强版API客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            enable_cache: 是否启用缓存
            cache_ttl: 缓存生存时间（秒）
            enable_batch: 是否启用批量处理
            batch_size: 批量大小
        """
        super().__init__(api_key, base_url)
        
        # 初始化缓存
        self.enable_cache = enable_cache
        if enable_cache:
            self.cache = APICache(default_ttl=cache_ttl)
        
        # 初始化批量处理器
        self.enable_batch = enable_batch
        if enable_batch:
            self.batch_processor = BatchProcessor(batch_size=batch_size)
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_requests': 0,
            'errors': 0
        }
        
        logger.info("增强版API客户端已初始化")
    
    def call_api(self, prompt: str, use_cache: Optional[bool] = None) -> Dict[str, Any]:
        """
        调用API（支持缓存）
        
        Args:
            prompt: 提示词
            use_cache: 是否使用缓存，None则使用客户端默认设置
            
        Returns:
            API响应结果
        """
        use_cache = use_cache if use_cache is not None else self.enable_cache
        self.stats['total_requests'] += 1
        
        # 检查缓存
        if use_cache and hasattr(self, 'cache'):
            cached_result = self.cache.get(prompt, self.model)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result
            else:
                self.stats['cache_misses'] += 1
        
        try:
            # 调用原始API
            result = super().call_api(prompt)
            
            # 缓存结果
            if use_cache and hasattr(self, 'cache') and not result.get('error'):
                self.cache.set(prompt, self.model, result)
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"API调用失败: {e}")
            raise
    
    def create_scoring_prompt(self, student_info: str, template_id: Optional[str] = None) -> str:
        """
        创建评分提示词（支持自定义配置）
        
        Args:
            student_info: 学生信息
            template_id: 评分模板ID，如果为None则使用默认模板
            
        Returns:
            格式化的提示词
        """
        try:
            # 使用增强配置管理器生成提示词
            config_manager = get_config_manager()
            prompt = config_manager.generate_scoring_prompt(template_id=template_id)
            
            # 插入学生信息
            student_section = f"""
学生信息：
{student_info}

"""
            
            # 在评分维度前插入学生信息
            prompt = prompt.replace("评分维度及标准：", student_section + "评分维度及标准：")
            
            return prompt
            
        except Exception as e:
            logger.error(f"生成自定义评分提示词失败: {e}")
            # 回退到默认提示词
            return self._create_default_prompt(student_info)
    
    def _create_default_prompt(self, student_info: str) -> str:
        """创建默认评分提示词（回退方案）"""
        prompt = f"""你是一位专业的算法竞赛团队选拔专家。请根据以下学生信息，从四个维度对该学生进行评分：

学生信息：
{student_info}

评分维度及标准：
1. 学习态度（25分）：积极主动、有强烈的学习意愿和上进心，如提到主动学习新知识、参加培训课程等，可得较高分数（20-25分）；学习态度一般，需要督促，但有一定学习意愿（10-19分）；态度消极、缺乏学习动力则分数较低（0-9分）。

2. 自学能力（25分）：具备独立解决问题的能力、能够自主学习新的算法和技术，如描述了自学经历、解决难题的过程等，可得较高分数（20-25分）；有一定自学能力但需要指导（10-19分）；依赖他人指导较多则分数较低（0-9分）。

3. 算法基础（25分）：有一定的算法知识储备，熟悉常见的算法和数据结构，如提及相关课程学习、算法竞赛经历等，可得较高分数（20-25分）；有一定编程基础但算法经验不足（10-19分）；算法基础薄弱或零基础，但如果有强烈学习意愿可适当给分（0-9分）。

4. 团队合作能力（25分）：能够与他人有效合作、沟通顺畅，如分享了团队项目经验、协作成果等，可得较高分数（20-25分）；有一定合作意识（10-19分）；团队合作能力欠佳则分数较低（0-9分）。

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
    "综合评价": "对该学生的综合评价和建议"
}}

注意：
- 请严格按照JSON格式返回，不要包含其他内容
- 分数必须是整数
- 总分为四个维度分数之和
- 评分要客观公正，有理有据"""

        return prompt

    def score_student(self, student_info: Dict[str, Any], use_cache: Optional[bool] = None) -> Dict[str, Any]:
        """
        评分单个学生（支持缓存）
        
        Args:
            student_info: 学生信息
            use_cache: 是否使用缓存
            
        Returns:
            评分结果
        """
        # 生成提示词
        student_str = json.dumps(student_info, ensure_ascii=False, indent=2)
        template_id = student_info.get('template_id')  # 从学生信息中获取模板ID
        prompt = self.create_scoring_prompt(student_str, template_id=template_id)
        
        # 调用API
        result = self.call_api(prompt, use_cache)
        
        # 添加学生信息到结果
        if not result.get('error'):
            result['student_id'] = student_info.get('id', '')
            result['student_name'] = student_info.get('name', '')
        
        return result
    
    def score_students_batch(self, students: List[Dict[str, Any]], use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        批量评分学生
        
        Args:
            students: 学生信息列表
            use_cache: 是否使用缓存
            
        Returns:
            评分结果列表
        """
        if not self.enable_batch:
            # 如果未启用批量处理，则逐个处理
            results = []
            for student in students:
                try:
                    result = self.score_student(student, use_cache)
                    results.append(result)
                except Exception as e:
                    logger.error(f"评分学生失败: {student.get('name', '未知')}, 错误: {e}")
                    results.append({
                        'error': True,
                        'error_message': str(e),
                        'student_id': student.get('id', ''),
                        'student_name': student.get('name', '')
                    })
            return results
        
        # 生成提示词列表
        prompts = []
        for student in students:
            student_str = json.dumps(student, ensure_ascii=False, indent=2)
            prompt = self.create_scoring_prompt(student_str)
            prompts.append(prompt)
        
        # 批量处理
        self.stats['batch_requests'] += 1
        api_results = self.batch_processor.process_batch(self, prompts)
        
        # 组装结果
        results = []
        for i, (student, api_result) in enumerate(zip(students, api_results)):
            if not api_result.get('error'):
                api_result['student_id'] = student.get('id', '')
                api_result['student_name'] = student.get('name', '')
            else:
                api_result.update({
                    'student_id': student.get('id', ''),
                    'student_name': student.get('name', '')
                })
            results.append(api_result)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        stats = self.stats.copy()
        
        if self.enable_cache and hasattr(self, 'cache'):
            cache_stats = self.cache.get_stats()
            stats.update({
                'cache_stats': cache_stats,
                'cache_hit_rate': (self.stats['cache_hits'] / max(self.stats['total_requests'], 1)) * 100
            })
        
        return stats
    
    def clear_cache(self, expired_only: bool = False):
        """清理缓存"""
        if hasattr(self, 'cache'):
            self.cache.clear(expired_only)
            logger.info(f"缓存已清理（expired_only={expired_only}）")
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_requests': 0,
            'errors': 0
        }
        logger.info("统计信息已重置")

# 全局增强API客户端实例
_enhanced_client = None

def get_enhanced_api_client(api_key: Optional[str] = None, **kwargs) -> EnhancedBaiLianAPIClient:
    """获取增强版API客户端实例"""
    global _enhanced_client
    
    if _enhanced_client is None:
        _enhanced_client = EnhancedBaiLianAPIClient(api_key, **kwargs)
    
    return _enhanced_client

def init_enhanced_api_client(api_key: Optional[str] = None, **kwargs) -> EnhancedBaiLianAPIClient:
    """初始化增强版API客户端"""
    global _enhanced_client
    _enhanced_client = EnhancedBaiLianAPIClient(api_key, **kwargs)
    return _enhanced_client