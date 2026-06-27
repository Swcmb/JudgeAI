"""
增强配置管理系统
支持动态配置、自定义评分维度和实时配置更�?"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import sqlite3
from datetime import datetime
import threading
import copy

from config_manager import ScoringDimension, DimensionConfig, ScoringSystemConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigChangeType(Enum):
    """配置变更类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"

@dataclass
class ConfigChange:
    """配置变更记录"""
    id: int
    config_id: str
    config_type: str
    change_type: ConfigChangeType
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    changed_by: str
    timestamp: datetime
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字�?""
        data = asdict(self)
        data['change_type'] = self.change_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class CustomDimension:
    """自定义维�?""
    id: str
    name: str
    weight: float
    max_score: int
    description: str
    scoring_criteria: List[Dict[str, Any]]
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    
    def __post_init__(self):
        """验证配置"""
        if self.weight <= 0:
            raise ValueError("权重必须大于0")
        if self.max_score <= 0:
            raise ValueError("最高分必须大于0")
        if not self.scoring_criteria:
            raise ValueError("评分标准不能为空")

@dataclass
class ScoringTemplate:
    """评分模板"""
    id: str
    name: str
    description: str
    dimensions: List[str]  # 维度ID列表
    is_default: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""

class EnhancedConfigManager:
    """增强配置管理�?""
    
    def __init__(self, db_path: str = "enhanced_config.db"):
        """
        初始化增强配置管理器
        
        Args:
            db_path: 配置数据库路�?        """
        self.db_path = db_path
        self.lock = threading.RLock()
        self._config_cache = {}
        self._template_cache = {}
        
        # 初始化数据库
        self._init_database()
        
        # 加载默认配置
        self._load_default_config()
        
        logger.info("增强配置管理器已初始�?)
    
    def _init_database(self):
        """初始化配置数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 自定义维度表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS custom_dimensions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    weight REAL NOT NULL,
                    max_score INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    scoring_criteria TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_by TEXT NOT NULL
                )
            ''')
            
            # 评分模板�?            conn.execute('''
                CREATE TABLE IF NOT EXISTS scoring_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    dimensions TEXT NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_by TEXT NOT NULL
                )
            ''')
            
            # 配置变更历史�?            conn.execute('''
                CREATE TABLE IF NOT EXISTS config_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id TEXT NOT NULL,
                    config_type TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    description TEXT NOT NULL
                )
            ''')
            
            # 系统配置�?            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TEXT NOT NULL,
                    updated_by TEXT NOT NULL
                )
            ''')
            
            conn.commit()
    
    def _load_default_config(self):
        """加载默认配置"""
        # 检查是否已有配�?        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM custom_dimensions")
            if cursor.fetchone()[0] > 0:
                return  # 已有配置，不加载默认配置
        
        # 创建默认维度
        default_dimensions = [
            {
                'id': 'learning_attitude',
                'name': '学习态度',
                'weight': 0.25,
                'max_score': 25,
                'description': '评估学生的学习积极性和态度',
                'scoring_criteria': [
                    {'range': '20-25', 'description': '积极主动，有强烈学习意愿'},
                    {'range': '10-19', 'description': '态度一般，需要督�?},
                    {'range': '0-9', 'description': '态度消极，缺乏动�?}
                ]
            },
            {
                'id': 'self_study',
                'name': '自学能力',
                'weight': 0.25,
                'max_score': 25,
                'description': '评估学生的独立学习和解决问题能力',
                'scoring_criteria': [
                    {'range': '20-25', 'description': '具备独立解决问题能力'},
                    {'range': '10-19', 'description': '有一定自学能力但需指导'},
                    {'range': '0-9', 'description': '依赖他人指导较多'}
                ]
            },
            {
                'id': 'algorithm',
                'name': '算法基础',
                'weight': 0.25,
                'max_score': 25,
                'description': '评估学生的算法知识储�?,
                'scoring_criteria': [
                    {'range': '20-25', 'description': '熟悉常见算法和数据结�?},
                    {'range': '10-19', 'description': '有一定编程基础但算法经验不�?},
                    {'range': '0-9', 'description': '算法基础薄弱或零基础'}
                ]
            },
            {
                'id': 'teamwork',
                'name': '团队合作能力',
                'weight': 0.25,
                'max_score': 25,
                'description': '评估学生的团队协作能�?,
                'scoring_criteria': [
                    {'range': '20-25', 'description': '能够有效合作、沟通顺�?},
                    {'range': '10-19', 'description': '有一定合作意�?},
                    {'range': '0-9', 'description': '团队合作能力欠佳'}
                ]
            }
        ]
        
        for dim_data in default_dimensions:
            self.create_custom_dimension(
                name=dim_data['name'],
                weight=dim_data['weight'],
                max_score=dim_data['max_score'],
                description=dim_data['description'],
                scoring_criteria=dim_data['scoring_criteria'],
                created_by='system'
            )
        
        # 创建默认模板
        self.create_template(
            name='默认评分模板',
            description='包含四个基础维度的标准评分模�?,
            dimension_ids=['learning_attitude', 'self_study', 'algorithm', 'teamwork'],
            is_default=True,
            created_by='system'
        )
        
        logger.info("默认配置已加�?)
    
    def create_custom_dimension(self, 
                              name: str, 
                              weight: float, 
                              max_score: int, 
                              description: str,
                              scoring_criteria: List[Dict[str, Any]],
                              created_by: str = "") -> str:
        """创建自定义维�?""
        dimension_id = f"dim_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name.lower().replace(' ', '_')}"
        
        dimension = CustomDimension(
            id=dimension_id,
            name=name,
            weight=weight,
            max_score=max_score,
            description=description,
            scoring_criteria=scoring_criteria,
            created_by=created_by
        )
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO custom_dimensions 
                    (id, name, weight, max_score, description, scoring_criteria, 
                     is_active, created_at, updated_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dimension.id,
                    dimension.name,
                    dimension.weight,
                    dimension.max_score,
                    dimension.description,
                    json.dumps(dimension.scoring_criteria, ensure_ascii=False),
                    dimension.is_active,
                    dimension.created_at.isoformat(),
                    dimension.updated_at.isoformat(),
                    dimension.created_by
                ))
                conn.commit()
            
            # 记录配置变更
            self._log_config_change(
                config_id=dimension_id,
                config_type='dimension',
                change_type=ConfigChangeType.CREATE,
                old_value=None,
                new_value=asdict(dimension),
                changed_by=created_by,
                description=f"创建自定义维�? {name}"
            )
            
            # 清除缓存
            self._config_cache.clear()
        
        logger.info(f"自定义维度已创建: {name} (ID: {dimension_id})")
        return dimension_id
    
    def update_custom_dimension(self, 
                              dimension_id: str, 
                              name: Optional[str] = None,
                              weight: Optional[float] = None,
                              max_score: Optional[int] = None,
                              description: Optional[str] = None,
                              scoring_criteria: Optional[List[Dict[str, Any]]] = None,
                              updated_by: str = "") -> bool:
        """更新自定义维�?""
        with self.lock:
            # 获取当前配置
            old_dimension = self.get_custom_dimension(dimension_id)
            if not old_dimension:
                return False
            
            # 准备更新数据
            updates = {}
            if name is not None:
                updates['name'] = name
            if weight is not None:
                updates['weight'] = weight
            if max_score is not None:
                updates['max_score'] = max_score
            if description is not None:
                updates['description'] = description
            if scoring_criteria is not None:
                updates['scoring_criteria'] = json.dumps(scoring_criteria, ensure_ascii=False)
            
            if not updates:
                return False
            
            updates['updated_at'] = datetime.now().isoformat()
            
            # 构建SQL
            set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values())
            values.append(dimension_id)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f'''
                    UPDATE custom_dimensions 
                    SET {set_clause}
                    WHERE id = ?
                ''', values)
                conn.commit()
            
            # 记录配置变更
            new_dimension = self.get_custom_dimension(dimension_id)
            self._log_config_change(
                config_id=dimension_id,
                config_type='dimension',
                change_type=ConfigChangeType.UPDATE,
                old_value=asdict(old_dimension),
                new_value=asdict(new_dimension) if new_dimension else None,
                changed_by=updated_by,
                description=f"更新自定义维�? {old_dimension.name}"
            )
            
            # 清除缓存
            self._config_cache.clear()
        
        logger.info(f"自定义维度已更新: {dimension_id}")
        return True
    
    def delete_custom_dimension(self, dimension_id: str, deleted_by: str = "") -> bool:
        """删除自定义维�?""
        with self.lock:
            # 获取当前配置
            old_dimension = self.get_custom_dimension(dimension_id)
            if not old_dimension:
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM custom_dimensions WHERE id = ?', (dimension_id,))
                conn.commit()
            
            # 记录配置变更
            self._log_config_change(
                config_id=dimension_id,
                config_type='dimension',
                change_type=ConfigChangeType.DELETE,
                old_value=asdict(old_dimension),
                new_value=None,
                changed_by=deleted_by,
                description=f"删除自定义维�? {old_dimension.name}"
            )
            
            # 清除缓存
            self._config_cache.clear()
        
        logger.info(f"自定义维度已删除: {dimension_id}")
        return True
    
    def get_custom_dimension(self, dimension_id: str) -> Optional[CustomDimension]:
        """获取自定义维�?""
        # 检查缓�?        if dimension_id in self._config_cache:
            return self._config_cache[dimension_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, name, weight, max_score, description, scoring_criteria,
                       is_active, created_at, updated_at, created_by
                FROM custom_dimensions WHERE id = ?
            ''', (dimension_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            dimension = CustomDimension(
                id=row[0],
                name=row[1],
                weight=row[2],
                max_score=row[3],
                description=row[4],
                scoring_criteria=json.loads(row[5]),
                is_active=bool(row[6]),
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
                created_by=row[9]
            )
            
            # 缓存结果
            self._config_cache[dimension_id] = dimension
            return dimension
    
    def list_custom_dimensions(self, active_only: bool = True) -> List[CustomDimension]:
        """列出自定义维�?""
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT id, name, weight, max_score, description, scoring_criteria,
                       is_active, created_at, updated_at, created_by
                FROM custom_dimensions
            '''
            params = []
            
            if active_only:
                query += ' WHERE is_active = 1'
            
            query += ' ORDER BY created_at'
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            dimensions = []
            for row in rows:
                dimension = CustomDimension(
                    id=row[0],
                    name=row[1],
                    weight=row[2],
                    max_score=row[3],
                    description=row[4],
                    scoring_criteria=json.loads(row[5]),
                    is_active=bool(row[6]),
                    created_at=datetime.fromisoformat(row[7]),
                    updated_at=datetime.fromisoformat(row[8]),
                    created_by=row[9]
                )
                dimensions.append(dimension)
            
            return dimensions
    
    def create_template(self, 
                       name: str, 
                       description: str, 
                       dimension_ids: List[str],
                       is_default: bool = False,
                       created_by: str = "") -> str:
        """创建评分模板"""
        template_id = f"tpl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name.lower().replace(' ', '_')}"
        
        # 如果设置为默认，先取消其他默认模�?        if is_default:
            self._clear_default_templates()
        
        template = ScoringTemplate(
            id=template_id,
            name=name,
            description=description,
            dimensions=dimension_ids,
            is_default=is_default,
            created_by=created_by
        )
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO scoring_templates 
                    (id, name, description, dimensions, is_default, is_active,
                     created_at, updated_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    template.id,
                    template.name,
                    template.description,
                    json.dumps(template.dimensions),
                    template.is_default,
                    template.is_active,
                    template.created_at.isoformat(),
                    template.updated_at.isoformat(),
                    template.created_by
                ))
                conn.commit()
            
            # 记录配置变更
            self._log_config_change(
                config_id=template_id,
                config_type='template',
                change_type=ConfigChangeType.CREATE,
                old_value=None,
                new_value=asdict(template),
                changed_by=created_by,
                description=f"创建评分模板: {name}"
            )
            
            # 清除缓存
            self._template_cache.clear()
        
        logger.info(f"评分模板已创�? {name} (ID: {template_id})")
        return template_id
    
    def get_template(self, template_id: str) -> Optional[ScoringTemplate]:
        """获取评分模板"""
        # 检查缓�?        if template_id in self._template_cache:
            return self._template_cache[template_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, name, description, dimensions, is_default, is_active,
                       created_at, updated_at, created_by
                FROM scoring_templates WHERE id = ?
            ''', (template_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            template = ScoringTemplate(
                id=row[0],
                name=row[1],
                description=row[2],
                dimensions=json.loads(row[3]),
                is_default=bool(row[4]),
                is_active=bool(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                updated_at=datetime.fromisoformat(row[7]),
                created_by=row[8]
            )
            
            # 缓存结果
            self._template_cache[template_id] = template
            return template
    
    def list_templates(self, active_only: bool = True) -> List[ScoringTemplate]:
        """列出评分模板"""
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT id, name, description, dimensions, is_default, is_active,
                       created_at, updated_at, created_by
                FROM scoring_templates
            '''
            params = []
            
            if active_only:
                query += ' WHERE is_active = 1'
            
            query += ' ORDER BY is_default DESC, created_at'
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            templates = []
            for row in rows:
                template = ScoringTemplate(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    dimensions=json.loads(row[3]),
                    is_default=bool(row[4]),
                    is_active=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                    created_by=row[8]
                )
                templates.append(template)
            
            return templates
    
    def get_default_template(self) -> Optional[ScoringTemplate]:
        """获取默认模板"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, name, description, dimensions, is_default, is_active,
                       created_at, updated_at, created_by
                FROM scoring_templates 
                WHERE is_default = 1 AND is_active = 1
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if not row:
                return None
            
            template = ScoringTemplate(
                id=row[0],
                name=row[1],
                description=row[2],
                dimensions=json.loads(row[3]),
                is_default=bool(row[4]),
                is_active=bool(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                updated_at=datetime.fromisoformat(row[7]),
                created_by=row[8]
            )
            
            return template
    
    def set_default_template(self, template_id: str, updated_by: str = "") -> bool:
        """设置默认模板"""
        with self.lock:
            # 取消所有默认模�?            self._clear_default_templates()
            
            # 设置新的默认模板
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE scoring_templates 
                    SET is_default = 1, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), template_id))
                conn.commit()
            
            # 记录配置变更
            self._log_config_change(
                config_id=template_id,
                config_type='template',
                change_type=ConfigChangeType.ACTIVATE,
                old_value=None,
                new_value={'is_default': True},
                changed_by=updated_by,
                description=f"设置默认模板: {template_id}"
            )
            
            # 清除缓存
            self._template_cache.clear()
        
        logger.info(f"默认模板已设�? {template_id}")
        return True
    
    def _clear_default_templates(self):
        """清除所有默认模�?""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE scoring_templates SET is_default = 0')
            conn.commit()
    
    def generate_scoring_prompt(self, template_id: Optional[str] = None, custom_dimensions: Optional[List[str]] = None) -> str:
        """生成评分提示�?""
        # 获取模板
        if template_id:
            template = self.get_template(template_id)
        else:
            template = self.get_default_template()
        
        if not template:
            # 使用默认维度
            dimensions = self.list_custom_dimensions(active_only=True)[:4]  # 最�?个维�?        else:
            # 使用模板指定的维�?            dimensions = []
            for dim_id in template.dimensions:
                dimension = self.get_custom_dimension(dim_id)
                if dimension:
                    dimensions.append(dimension)
        
        if not dimensions:
            raise ValueError("没有可用的评分维�?)
        
        # 生成提示�?        prompt = f"""你是一位专业的算法竞赛团队选拔专家。请根据以下学生信息，从以下维度对该学生进行评分�?
评分维度及标准：
"""
        
        # 添加维度描述
        total_weight = sum(dim.weight for dim in dimensions)
        for i, dimension in enumerate(dimensions, 1):
            weight_percent = (dimension.weight / total_weight) * 100
            prompt += f"""
{i}. {dimension.name}（{dimension.max_score}分，权重{weight_percent:.1f}%）：{dimension.description}
评分标准�?"""
            for criterion in dimension.scoring_criteria:
                prompt += f"- {criterion['range']}分：{criterion['description']}\n"
        
        prompt += """
请按照以下JSON格式返回评分结果�?{
    "思考过�?: "详细分析该学生在各维度的表现，说明评分理�?,
"""
        
        # 添加维度字段
        for dimension in dimensions:
            prompt += f'''
    "{dimension.name}": {{
        "分数": 分数(0-{dimension.max_score}),
        "理由": "具体评分理由"
    }},
'''
        
        prompt += '''
    "总分": 总分(0-100),
    "综合评价": "对该学生的综合评价和建议"
}

注意�?- 请严格按照JSON格式返回，不要包含其他内�?- 分数必须是整�?- 总分根据各维度权重计�?- 评分要客观公正，有理有据"""
        
        return prompt
    
    def _log_config_change(self, 
                          config_id: str, 
                          config_type: str, 
                          change_type: ConfigChangeType,
                          old_value: Optional[Dict[str, Any]], 
                          new_value: Optional[Dict[str, Any]],
                          changed_by: str, 
                          description: str):
        """记录配置变更"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO config_changes 
                (config_id, config_type, change_type, old_value, new_value, changed_by, timestamp, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config_id,
                config_type,
                change_type.value,
                json.dumps(old_value, ensure_ascii=False) if old_value else None,
                json.dumps(new_value, ensure_ascii=False) if new_value else None,
                changed_by,
                datetime.now().isoformat(),
                description
            ))
            conn.commit()
    
    def get_config_changes(self, 
                          config_id: Optional[str] = None,
                          config_type: Optional[str] = None,
                          limit: int = 100) -> List[ConfigChange]:
        """获取配置变更历史"""
            INSERT INTO config_changes 
            query = 'SELECT * FROM config_changes WHERE 1=1'
            params = []
            
            if config_id:
                query += ' AND config_id = ?'
                params.append(config_id)
            
            if config_type:
                query += ' AND config_type = ?'
                params.append(config_type)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            changes = []
            for row in rows:
                change = ConfigChange(
                    id=row[0],
                    config_id=row[1],
                    config_type=row[2],
                    change_type=ConfigChangeType(row[3]),
                    old_value=json.loads(row[4]) if row[4] else None,
                    new_value=json.loads(row[5]) if row[5] else None,
                    changed_by=row[6],
                    timestamp=datetime.fromisoformat(row[7]),
                    description=row[8]
                )
                changes.append(change)
            
            return changes
    
    def export_config(self, include_history: bool = False) -> Dict[str, Any]:
        """导出配置"""
        export_data = {
            'export_time': datetime.now().isoformat(),
            'dimensions': [asdict(dim) for dim in self.list_custom_dimensions()],
            'templates': [asdict(tpl) for tpl in self.list_templates()]
        }
        
        if include_history:
            export_data['changes'] = [change.to_dict() for change in self.get_config_changes()]
        
        return export_data
    
    def import_config(self, config_data: Dict[str, Any], import_by: str = "") -> bool:
        """导入配置"""
        try:
            with self.lock:
                # 导入维度
                if 'dimensions' in config_data:
                    for dim_data in config_data['dimensions']:
                        # 检查是否已存在
                        existing = self.get_custom_dimension(dim_data['id'])
                        if existing:
                            # 更新现有维度
                            self.update_custom_dimension(
                                dimension_id=dim_data['id'],
                                name=dim_data['name'],
                                weight=dim_data['weight'],
                                max_score=dim_data['max_score'],
                                description=dim_data['description'],
                                scoring_criteria=dim_data['scoring_criteria'],
                                updated_by=import_by
                            )
                        else:
                            # 创建新维�?                            self.create_custom_dimension(
                                name=dim_data['name'],
                                weight=dim_data['weight'],
                                max_score=dim_data['max_score'],
                                description=dim_data['description'],
                                scoring_criteria=dim_data['scoring_criteria'],
                                created_by=import_by
                            )
                
                # 导入模板
                if 'templates' in config_data:
                    for tpl_data in config_data['templates']:
                        # 检查是否已存在
                        existing = self.get_template(tpl_data['id'])
                        if existing:
                            # 跳过已存在的模板
                            continue
                        else:
                            # 创建新模�?                            self.create_template(
                                name=tpl_data['name'],
                                description=tpl_data['description'],
                                dimension_ids=tpl_data['dimensions'],
                                is_default=tpl_data['is_default'],
                                created_by=import_by
                            )
                
                logger.info(f"配置导入成功，由 {import_by} 执行")
                return True
                
        except Exception as e:
            logger.error(f"配置导入失败: {e}")
            return False

# 全局配置管理器实�?_config_manager = None

def get_enhanced_config_manager() -> EnhancedConfigManager:
    """获取增强配置管理器实�?""
    global _config_manager
    if _config_manager is None:
        _config_manager = EnhancedConfigManager()
    return _config_manager

def init_enhanced_config_manager(db_path: str = "enhanced_config.db") -> EnhancedConfigManager:
    """初始化增强配置管理器"""
    global _config_manager
    _config_manager = EnhancedConfigManager(db_path=db_path)
    return _config_manager
