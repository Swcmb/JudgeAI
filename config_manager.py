"""
配置管理系统
自定义评分标准和权重
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import sqlite3
from datetime import datetime

class ScoringDimension(Enum):
    """评分维度枚举"""
    LEARNING_ATTITUDE = "学习态度"
    SELF_STUDY = "自学能力"
    ALGORITHM = "算法基础"
    TEAMWORK = "团队合作"

@dataclass
class DimensionConfig:
    """维度配置"""
    name: str
    weight: float
    max_score: int
    description: str
    scoring_criteria: List[Dict[str, Any]]
    
    def __post_init__(self):
        """验证配置"""
        if self.weight <= 0:
            raise ValueError("权重必须大于0")
        if self.max_score <= 0:
            raise ValueError("最高分必须大于0")

@dataclass
class ScoringSystemConfig:
    """评分系统配置"""
    system_name: str
    version: str
    description: str
    dimensions: Dict[str, DimensionConfig]
    default_model: str
    enable_thinking: bool
    custom_prompts: Dict[str, str]
    output_formats: List[str]
    notification_settings: Dict[str, Any]
    
    def __post_init__(self):
        """验证总分权重为100"""
        total_weight = sum(dim.weight for dim in self.dimensions.values())
        if abs(total_weight - 100.0) > 0.01:
            raise ValueError(f"维度权重总和必须为100，当前为{total_weight}")

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "scoring_config.json", db_path: str = "config_history.db"):
        self.config_file = config_file
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.current_config: Optional[ScoringSystemConfig] = None
        self._init_database()
        self._load_config()
    
    def _init_database(self):
        """初始化配置历史数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_name TEXT,
                version TEXT,
                config_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                description TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT UNIQUE,
                template_data TEXT,
                category TEXT,
                description TEXT,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self.current_config = self._parse_config(config_data)
            else:
                # 创建默认配置
                self.current_config = self._create_default_config()
                self.save_config()
        
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            self.current_config = self._create_default_config()
    
    def _parse_config(self, config_data: Dict[str, Any]) -> ScoringSystemConfig:
        """解析配置数据"""
        dimensions = {}
        for dim_name, dim_data in config_data.get('dimensions', {}).items():
            dimensions[dim_name] = DimensionConfig(
                name=dim_data['name'],
                weight=dim_data['weight'],
                max_score=dim_data['max_score'],
                description=dim_data['description'],
                scoring_criteria=dim_data.get('scoring_criteria', [])
            )
        
        return ScoringSystemConfig(
            system_name=config_data.get('system_name', '算法竞赛团队AI评分系统'),
            version=config_data.get('version', '1.0.0'),
            description=config_data.get('description', ''),
            dimensions=dimensions,
            default_model=config_data.get('default_model', 'qwen-plus-2025-09-11'),
            enable_thinking=config_data.get('enable_thinking', True),
            custom_prompts=config_data.get('custom_prompts', {}),
            output_formats=config_data.get('output_formats', ['csv', 'excel', 'json', 'txt']),
            notification_settings=config_data.get('notification_settings', {})
        )
    
    def _create_default_config(self) -> ScoringSystemConfig:
        """创建默认配置"""
        default_dimensions = {
            "学习态度": DimensionConfig(
                name="学习态度",
                weight=25.0,
                max_score=25,
                description="评估学生的学习积极性和学习意愿",
                scoring_criteria=[
                    {
                        "score_range": "20-25",
                        "description": "积极主动、有强烈的学习意愿和上进心",
                        "indicators": ["主动学习新知识", "参加培训课程", "表现出强烈兴趣"]
                    },
                    {
                        "score_range": "10-19",
                        "description": "学习态度一般，需要督促，但有一定学习意愿",
                        "indicators": ["能够在督促下完成学习", "有一定主动性", "但需要外部推动"]
                    },
                    {
                        "score_range": "0-9",
                        "description": "态度消极、缺乏学习动力，表现出被动学习特征",
                        "indicators": ["缺乏主动性", "需要频繁督促", "表现出消极态度"]
                    }
                ]
            ),
            "自学能力": DimensionConfig(
                name="自学能力",
                weight=25.0,
                max_score=25,
                description="评估学生独立学习和解决问题的能力",
                scoring_criteria=[
                    {
                        "score_range": "20-25",
                        "description": "具备独立解决问题的能力、能够自主学习新的算法和技术",
                        "indicators": ["有自学经历", "能独立解决问题", "学习能力强"]
                    },
                    {
                        "score_range": "10-19",
                        "description": "有一定自学能力但需要指导，能够在帮助下学习新知识",
                        "indicators": ["需要一些指导", "能完成大部分自学", "但有依赖性"]
                    },
                    {
                        "score_range": "0-9",
                        "description": "依赖他人指导较多，缺乏独立学习能力",
                        "indicators": ["严重依赖指导", "自学能力弱", "缺乏独立性"]
                    }
                ]
            ),
            "算法基础": DimensionConfig(
                name="算法基础",
                weight=25.0,
                max_score=25,
                description="评估学生的算法知识和编程基础",
                scoring_criteria=[
                    {
                        "score_range": "20-25",
                        "description": "有一定的算法知识储备，熟悉常见的算法和数据结构",
                        "indicators": ["有竞赛经验", "算法知识扎实", "编程基础好"]
                    },
                    {
                        "score_range": "10-19",
                        "description": "有一定编程基础但算法经验不足，了解基本概念",
                        "indicators": ["有编程基础", "算法知识一般", "了解基本概念"]
                    },
                    {
                        "score_range": "0-9",
                        "description": "算法基础薄弱或零基础，但如果有强烈学习意愿可适当给分",
                        "indicators": ["基础薄弱", "零基础", "但有学习意愿"]
                    }
                ]
            ),
            "团队合作能力": DimensionConfig(
                name="团队合作能力",
                weight=25.0,
                max_score=25,
                description="评估学生的团队协作和沟通能力",
                scoring_criteria=[
                    {
                        "score_range": "20-25",
                        "description": "能够与他人有效合作、沟通顺畅，有团队项目经验",
                        "indicators": ["沟通能力强", "有团队经验", "合作效果好"]
                    },
                    {
                        "score_range": "10-19",
                        "description": "有一定合作意识，能够参与团队活动",
                        "indicators": ["有合作意识", "能参与活动", "但能力一般"]
                    },
                    {
                        "score_range": "0-9",
                        "description": "团队合作能力欠佳，更倾向于独立工作",
                        "indicators": ["合作能力弱", "倾向独立", "沟通不足"]
                    }
                ]
            )
        }
        
        return ScoringSystemConfig(
            system_name="算法竞赛团队AI评分系统",
            version="1.0.0",
            description="基于AI的算法竞赛团队选拔评分系统",
            dimensions=default_dimensions,
            default_model="qwen-plus-2025-09-11",
            enable_thinking=True,
            custom_prompts={},
            output_formats=["csv", "excel", "json", "txt"],
            notification_settings={
                "email_enabled": False,
                "webhook_enabled": False,
                "threshold_score": 60
            }
        )
    
    def save_config(self, description: str = "配置更新", created_by: str = "system") -> bool:
        """保存配置"""
        try:
            if not self.current_config:
                self.logger.error("没有配置可保存")
                return False
            
            # 验证配置
            total_weight = sum(dim.weight for dim in self.current_config.dimensions.values())
            if abs(total_weight - 100.0) > 0.01:
                raise ValueError(f"维度权重总和必须为100，当前为{total_weight}")
            
            # 保存到文件
            config_data = self._serialize_config()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # 保存到数据库
            self._save_config_history(description, created_by)
            
            self.logger.info("配置保存成功")
            return True
        
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False
    
    def _serialize_config(self) -> Dict[str, Any]:
        """序列化配置"""
        if not self.current_config:
            return {}
        
        return {
            "system_name": self.current_config.system_name,
            "version": self.current_config.version,
            "description": self.current_config.description,
            "dimensions": {
                dim_name: asdict(dim_config) for dim_name, dim_config in self.current_config.dimensions.items()
            },
            "default_model": self.current_config.default_model,
            "enable_thinking": self.current_config.enable_thinking,
            "custom_prompts": self.current_config.custom_prompts,
            "output_formats": self.current_config.output_formats,
            "notification_settings": self.current_config.notification_settings
        }
    
    def _save_config_history(self, description: str, created_by: str):
        """保存配置历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        config_data = json.dumps(self._serialize_config(), ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO config_history 
            (config_name, version, config_data, created_by, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            self.current_config.system_name,
            self.current_config.version,
            config_data,
            created_by,
            description
        ))
        
        conn.commit()
        conn.close()
    
    def update_dimension(self, dimension_name: str, updates: Dict[str, Any]) -> bool:
        """更新维度配置"""
        try:
            if dimension_name not in self.current_config.dimensions:
                self.logger.error(f"维度 {dimension_name} 不存在")
                return False
            
            dim_config = self.current_config.dimensions[dimension_name]
            
            # 更新属性
            if 'weight' in updates:
                dim_config.weight = updates['weight']
            if 'max_score' in updates:
                dim_config.max_score = updates['max_score']
            if 'description' in updates:
                dim_config.description = updates['description']
            if 'scoring_criteria' in updates:
                dim_config.scoring_criteria = updates['scoring_criteria']
            
            # 验证权重总和
            total_weight = sum(dim.weight for dim in self.current_config.dimensions.values())
            if abs(total_weight - 100.0) > 0.01:
                raise ValueError(f"维度权重总和必须为100，当前为{total_weight}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"更新维度配置失败: {e}")
            return False
    
    def add_dimension(self, dimension_config: DimensionConfig) -> bool:
        """添加新维度"""
        try:
            if not self.current_config:
                return False
            
            # 验证总权重
            total_weight = sum(dim.weight for dim in self.current_config.dimensions.values()) + dimension_config.weight
            if abs(total_weight - 100.0) > 0.01:
                raise ValueError(f"添加维度后权重总和将为{total_weight}，必须为100")
            
            self.current_config.dimensions[dimension_config.name] = dimension_config
            return True
        
        except Exception as e:
            self.logger.error(f"添加维度失败: {e}")
            return False
    
    def remove_dimension(self, dimension_name: str) -> bool:
        """移除维度"""
        try:
            if not self.current_config or dimension_name not in self.current_config.dimensions:
                return False
            
            # 至少保留一个维度
            if len(self.current_config.dimensions) <= 1:
                raise ValueError("至少需要保留一个评分维度")
            
            del self.current_config.dimensions[dimension_name]
            return True
        
        except Exception as e:
            self.logger.error(f"移除维度失败: {e}")
            return False
    
    def create_scoring_prompt(self, custom_criteria: Optional[Dict[str, Any]] = None) -> str:
        """创建评分提示词"""
        if not self.current_config:
            return self._get_default_prompt()
        
        prompt_parts = [
            f"你是{self.current_config.system_name}的专业评分专家。",
            f"请根据以下学生信息，从以下维度对学生进行评分："
        ]
        
        # 添加维度说明
        for dim_name, dim_config in self.current_config.dimensions.items():
            prompt_parts.append(f"\n{dim_name}（{dim_config.weight}%，最高{dim_config.max_score}分）：")
            prompt_parts.append(f"{dim_config.description}")
            
            for criterion in dim_config.scoring_criteria:
                prompt_parts.append(f"- {criterion['score_range']}分：{criterion['description']}")
        
        # 添加自定义标准
        if custom_criteria:
            prompt_parts.append("\n自定义评分标准：")
            for key, value in custom_criteria.items():
                prompt_parts.append(f"- {key}：{value}")
        
        # 添加返回格式说明
        prompt_parts.append(f"\n请按照以下JSON格式返回评分结果：")
        prompt_parts.append('{')
        
        for dim_name in self.current_config.dimensions.keys():
            prompt_parts.append(f'    "{dim_name}": {{')
            prompt_parts.append(f'        "分数": 分数(0-{self.current_config.dimensions[dim_name].max_score}),')
            prompt_parts.append(f'        "理由": "具体评分理由"')
            prompt_parts.append('    },')
        
        prompt_parts.extend([
            '    "总分": 总分(0-100),',
            '    "综合评价": "对该学生的综合评价和建议"',
            '}'
        ])
        
        return '\n'.join(prompt_parts)
    
    def _get_default_prompt(self) -> str:
        """获取默认提示词"""
        return """你是算法竞赛团队选拔专家。请从学习态度、自学能力、算法基础、团队合作四个维度对学生进行评分，每个维度25分，总分100分。"""
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        if not self.current_config:
            return {}
        
        return {
            "system_name": self.current_config.system_name,
            "version": self.current_config.version,
            "description": self.current_config.description,
            "dimension_count": len(self.current_config.dimensions),
            "dimensions": [
                {
                    "name": dim.name,
                    "weight": dim.weight,
                    "max_score": dim.max_score,
                    "description": dim.description
                }
                for dim in self.current_config.dimensions.values()
            ],
            "default_model": self.current_config.default_model,
            "enable_thinking": self.current_config.enable_thinking,
            "output_formats": self.current_config.output_formats
        }
    
    def export_config(self, output_path: str) -> bool:
        """导出配置"""
        try:
            config_data = self._serialize_config()
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, config_path: str) -> bool:
        """导入配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            new_config = self._parse_config(config_data)
            self.current_config = new_config
            return self.save_config("导入配置", "import")
        except Exception as e:
            self.logger.error(f"导入配置失败: {e}")
            return False
    
    def create_template(self, template_name: str, category: str, description: str, is_default: bool = False) -> bool:
        """创建配置模板"""
        try:
            if not self.current_config:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            template_data = json.dumps(self._serialize_config(), ensure_ascii=False)
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_templates
                (template_name, template_data, category, description, is_default)
                VALUES (?, ?, ?, ?, ?)
            ''', (template_name, template_data, category, description, is_default))
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            self.logger.error(f"创建模板失败: {e}")
            return False
    
    def get_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取配置模板"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute('''
                SELECT * FROM config_templates WHERE category = ? ORDER BY created_at DESC
            ''', (category,))
        else:
            cursor.execute('SELECT * FROM config_templates ORDER BY created_at DESC')
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        templates = []
        for row in rows:
            template = dict(zip(columns, row))
            if template.get('template_data'):
                try:
                    template['parsed_data'] = json.loads(template['template_data'])
                except:
                    pass
            templates.append(template)
        
        conn.close()
        return templates
    
    def apply_template(self, template_name: str) -> bool:
        """应用配置模板"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT template_data FROM config_templates WHERE template_name = ?
            ''', (template_name,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return False
            
            template_data = json.loads(row[0])
            self.current_config = self._parse_config(template_data)
            
            return self.save_config(f"应用模板: {template_name}", "template")
        
        except Exception as e:
            self.logger.error(f"应用模板失败: {e}")
            return False
    
    def list_templates(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取配置模板列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute('''
                    SELECT * FROM config_templates 
                    ORDER BY is_default DESC, created_at DESC
                ''')
            else:
                cursor.execute('SELECT * FROM config_templates ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            templates = []
            for row in rows:
                template = dict(zip(columns, row))
                if template.get('template_data'):
                    try:
                        template['parsed_data'] = json.loads(template['template_data'])
                    except:
                        pass
                templates.append(template)
            
            conn.close()
            return templates
            
        except Exception as e:
            self.logger.error(f"获取模板列表失败: {e}")
            return []
    
    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """获取单个配置模板"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM config_templates WHERE id = ?
            ''', (template_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            template = dict(zip(columns, row))
            
            if template.get('template_data'):
                try:
                    template['parsed_data'] = json.loads(template['template_data'])
                except:
                    pass
            
            return template
            
        except Exception as e:
            self.logger.error(f"获取模板失败: {e}")
            return None
    
    def list_custom_dimensions(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取自定义维度列表"""
        try:
            if not self.current_config:
                return []
            
            dimensions = []
            for dim_name, dim_config in self.current_config.dimensions.items():
                dimensions.append({
                    'name': dim_config.name,
                    'weight': dim_config.weight,
                    'max_score': dim_config.max_score,
                    'description': dim_config.description,
                    'scoring_criteria': dim_config.scoring_criteria
                })
            
            return dimensions
            
        except Exception as e:
            self.logger.error(f"获取维度列表失败: {e}")
            return []
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not self.current_config:
            validation_result["valid"] = False
            validation_result["errors"].append("没有找到配置")
            return validation_result
        
        try:
            # 验证权重总和
            total_weight = sum(dim.weight for dim in self.current_config.dimensions.values())
            if abs(total_weight - 100.0) > 0.01:
                validation_result["valid"] = False
                validation_result["errors"].append(f"维度权重总和为{total_weight}，必须为100")
            
            # 验证维度配置
            for dim_name, dim_config in self.current_config.dimensions.items():
                if dim_config.weight <= 0:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"维度 {dim_name} 权重必须大于0")
                
                if dim_config.max_score <= 0:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"维度 {dim_name} 最高分必须大于0")
                
                if not dim_config.scoring_criteria:
                    validation_result["warnings"].append(f"维度 {dim_name} 没有评分标准")
            
            # 验证模型配置
            if not self.current_config.default_model:
                validation_result["warnings"].append("没有设置默认模型")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"验证过程中出错: {str(e)}")
        
        return validation_result


def main():
    """测试配置管理系统"""
    manager = ConfigManager()
    
    # 显示当前配置
    print("当前配置摘要:")
    summary = manager.get_config_summary()
    print(f"系统名称: {summary.get('system_name')}")
    print(f"版本: {summary.get('version')}")
    print(f"维度数量: {summary.get('dimension_count')}")
    
    print("\n维度详情:")
    for dim in summary.get('dimensions', []):
        print(f"  {dim['name']}: 权重{dim['weight']}%, 最高{dim['max_score']}分")
    
    # 验证配置
    validation = manager.validate_config()
    print(f"\n配置验证: {'✅ 通过' if validation['valid'] else '❌ 失败'}")
    if validation['errors']:
        print("错误:")
        for error in validation['errors']:
            print(f"  - {error}")
    if validation['warnings']:
        print("警告:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    # 生成评分提示词
    prompt = manager.create_scoring_prompt()
    print(f"\n评分提示词（前200字符）: {prompt[:200]}...")
    
    # 创建模板
    success = manager.create_template(
        "基础算法竞赛评分模板",
        "算法竞赛",
        "适合基础算法竞赛团队选拔的评分配置"
    )
    print(f"\n创建模板: {'✅ 成功' if success else '❌ 失败'}")
    
    # 导出配置
    export_success = manager.export_config("test_config.json")
    print(f"导出配置: {'✅ 成功' if export_success else '❌ 失败'}")


# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


if __name__ == "__main__":
    main()