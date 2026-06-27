"""
多模型支持模块
支持不同的AI评分模型
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from openai import OpenAI
import requests
from dataclasses import dataclass
from enum import Enum

class ModelType(Enum):
    """模型类型枚举"""
    QWEN_PLUS = "qwen-plus"
    QWEN_FLASH = "qwen-flash"
    QWEN_TURBO = "qwen-turbo"
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3 = "claude-3-sonnet"
    CUSTOM = "custom"

@dataclass
class ModelConfig:
    """模型配置"""
    model_type: ModelType
    model_name: str
    api_base: str
    api_key: str
    max_tokens: int = 2000
    temperature: float = 0.3
    timeout: int = 60
    enable_thinking: bool = False
    description: str = ""
    cost_per_token: float = 0.0

class BaseScoringModel(ABC):
    """评分模型基类"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def score_student(self, student_info: Dict[str, Any]) -> Dict[str, Any]:
        """为学生评分的抽象方法"""
        pass
    
    @abstractmethod
    def create_scoring_prompt(self, student_info: str) -> str:
        """创建评分提示词的抽象方法"""
        pass
    
    def create_enhanced_scoring_prompt(self, student_info: str, custom_criteria: Dict[str, Any] = None) -> str:
        """创建增强评分提示词"""
        base_prompt = self.create_scoring_prompt(student_info)
        
        if custom_criteria:
            additional_criteria = "\n\n自定义评分标准:\n"
            for criterion, weight in custom_criteria.items():
                additional_criteria += f"- {criterion}: 权重 {weight}\n"
            base_prompt += additional_criteria
        
        return base_prompt

class QwenModel(BaseScoringModel):
    """通义千问模型"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base
        )
    
    def score_student(self, student_info: Dict[str, Any]) -> Dict[str, Any]:
        """使用千问模型评分"""
        try:
            # 构建学生信息
            info_parts = []
            if student_info.get('name'):
                info_parts.append(f"姓名: {student_info['name']}")
            if student_info.get('id'):
                info_parts.append(f"学号: {student_info['id']}")
            if student_info.get('content'):
                info_parts.append(f"个人信息: {student_info['content']}")
            
            student_info_str = "\n".join(info_parts)
            prompt = self.create_scoring_prompt(student_info_str)
            
            # 调用API
            if self.config.enable_thinking and "thinking" in self.config.model_name.lower():
                return self._call_with_thinking(prompt)
            else:
                return self._call_standard(prompt)
        
        except Exception as e:
            self.logger.error(f"千问模型评分失败: {e}")
            return self._create_error_result(student_info, str(e))
    
    def _call_with_thinking(self, prompt: str) -> Dict[str, Any]:
        """调用带思考功能的模型"""
        messages = [
            {"role": "system", "content": "你是一位专业的算法竞赛团队选拔专家。"},
            {"role": "user", "content": prompt}
        ]
        
        completion = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            extra_body={"enable_thinking": True},
            stream=True
        )
        
        reasoning_content = ""
        answer_content = ""
        is_answering = False
        
        for chunk in completion:
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            
            if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                reasoning_content += delta.reasoning_content
            
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    is_answering = True
                answer_content += delta.content
        
        return self._parse_response(answer_content, reasoning_content)
    
    def _call_standard(self, prompt: str) -> Dict[str, Any]:
        """调用标准模型"""
        messages = [
            {"role": "system", "content": "你是一位专业的算法竞赛团队选拔专家。"},
            {"role": "user", "content": prompt}
        ]
        
        completion = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        answer_content = completion.choices[0].message.content
        return self._parse_response(answer_content)
    
    def _parse_response(self, answer_content: str, thinking_content: str = "") -> Dict[str, Any]:
        """解析模型响应"""
        try:
            # 尝试解析JSON
            import json
            result = json.loads(answer_content)
            
            if thinking_content:
                result['AI思考过程'] = thinking_content
            
            return result
        
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            result = self._extract_json_from_response(answer_content)
            if result:
                if thinking_content:
                    result['AI思考过程'] = thinking_content
                return result
            else:
                return {
                    '思考过程': thinking_content or "无思考过程",
                    '原始回复': answer_content,
                    '解析错误': "无法解析为JSON格式",
                    '学习态度': {'分数': 0, '理由': 'JSON解析失败'},
                    '自学能力': {'分数': 0, '理由': 'JSON解析失败'},
                    '算法基础': {'分数': 0, '理由': 'JSON解析失败'},
                    '团队合作能力': {'分数': 0, '理由': 'JSON解析失败'},
                    '总分': 0,
                    '综合评价': '响应解析失败',
                    'error': True
                }
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """从响应中提取JSON"""
        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        
        except Exception:
            pass
        
        return None
    
    def _create_error_result(self, student_info: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            '学生信息': {
                'id': student_info.get('id', ''),
                'name': student_info.get('name', ''),
                'content': student_info.get('content', '')
            },
            '思考过程': f"评分失败: {error_msg}",
            '学习态度': {'分数': 0, '理由': '评分失败'},
            '自学能力': {'分数': 0, '理由': '评分失败'},
            '算法基础': {'分数': 0, '理由': '评分失败'},
            '团队合作能力': {'分数': 0, '理由': '评分失败'},
            '总分': 0,
            '综合评价': f'评分失败: {error_msg}',
            'error': True
        }
    
    def create_scoring_prompt(self, student_info: str) -> str:
        """创建千问模型的评分提示词"""
        return f"""你是一位专业的算法竞赛团队选拔专家。请根据以下学生信息，从四个维度对该学生进行评分：

学生信息：
{student_info}

评分维度及标准：
1. 学习态度（25分）：积极主动、有强烈的学习意愿和上进心，如提到主动学习新知识、参加培训课程等，可得较高分数（20-25分）；学习态度一般，需要督促，但有一定学习意愿（10-19分）；态度消极、缺乏学习动力则分数较低（0-9分）。

2. 自学能力（25分）：具备独立解决问题的能力、能够自主学习新的算法和技术，如描述了自学经历、解决难题的过程等，可得较高分数（20-25分）；有一定自学能力但需要指导（10-19分）；依赖他人指导较多则分数较低（0-9分）。

3. 算法基础（25分）：有一定的算法知识储备，熟悉常见的算法和数据结构，如提及相关课程学习、算法竞赛经历等，可得较高分数（20-25分）；有一定编程基础但算法经验不足（10-19分）；算法基础薄弱或零基础，但如果有强烈学习意愿可适当给分（0-9分）。

4. 团队合作能力（25分）：能够与他人有效合作、沟通顺畅，如分享了团队项目经验、协作成果等，可得较高分数（20-25分）；有一定合作意识（10-19分）；团队合作能力欠佳则分数较低（0-9分）。

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

注意：请严格按照JSON格式返回，分数必须是整数，总分为四个维度分数之和。"""

class OpenAIModel(BaseScoringModel):
    """OpenAI模型"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base
        )
    
    def score_student(self, student_info: Dict[str, Any]) -> Dict[str, Any]:
        """使用OpenAI模型评分"""
        try:
            info_parts = []
            if student_info.get('name'):
                info_parts.append(f"姓名: {student_info['name']}")
            if student_info.get('id'):
                info_parts.append(f"学号: {student_info['id']}")
            if student_info.get('content'):
                info_parts.append(f"个人信息: {student_info['content']}")
            
            student_info_str = "\n".join(info_parts)
            prompt = self.create_scoring_prompt(student_info_str)
            
            messages = [
                {"role": "system", "content": "你是一位专业的算法竞赛团队选拔专家，需要客观公正地评估学生的能力。"},
                {"role": "user", "content": prompt}
            ]
            
            completion = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            answer_content = completion.choices[0].message.content
            return self._parse_response(answer_content)
            
        except Exception as e:
            self.logger.error(f"OpenAI模型评分失败: {e}")
            return self._create_error_result(student_info, str(e))
    
    def _parse_response(self, answer_content: str) -> Dict[str, Any]:
        """解析OpenAI响应"""
        try:
            import json
            result = json.loads(answer_content)
            result['AI思考过程'] = "OpenAI模型评分"
            return result
        except json.JSONDecodeError:
            result = self._extract_json_from_response(answer_content)
            if result:
                result['AI思考过程'] = "OpenAI模型评分"
                return result
            else:
                return {
                    '思考过程': "OpenAI模型评分",
                    '原始回复': answer_content,
                    '解析错误': "无法解析为JSON格式",
                    '学习态度': {'分数': 0, '理由': 'JSON解析失败'},
                    '自学能力': {'分数': 0, '理由': 'JSON解析失败'},
                    '算法基础': {'分数': 0, '理由': 'JSON解析失败'},
                    '团队合作能力': {'分数': 0, '理由': 'JSON解析失败'},
                    '总分': 0,
                    '综合评价': '响应解析失败',
                    'error': True
                }
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """从响应中提取JSON"""
        # 实现与QwenModel相同的JSON提取逻辑
        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception:
            pass
        return None
    
    def _create_error_result(self, student_info: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            '学生信息': {
                'id': student_info.get('id', ''),
                'name': student_info.get('name', ''),
                'content': student_info.get('content', '')
            },
            '思考过程': f"评分失败: {error_msg}",
            '学习态度': {'分数': 0, '理由': '评分失败'},
            '自学能力': {'分数': 0, '理由': '评分失败'},
            '算法基础': {'分数': 0, '理由': '评分失败'},
            '团队合作能力': {'分数': 0, '理由': '评分失败'},
            '总分': 0,
            '综合评价': f'评分失败: {error_msg}',
            'error': True
        }
    
    def create_scoring_prompt(self, student_info: str) -> str:
        """创建OpenAI模型的评分提示词"""
        return f"""As a professional algorithm competition team selection expert, please evaluate the student based on the following information from four dimensions:

Student Information:
{student_info}

Scoring Dimensions and Criteria:
1. Learning Attitude (25 points): Proactive with strong learning motivation (20-25 pts); Average attitude needing supervision (10-19 pts); Negative attitude lacking motivation (0-9 pts).

2. Self-Study Ability (25 points): Independent problem-solving skills (20-25 pts); Some self-study ability needing guidance (10-19 pts); Dependent on others' guidance (0-9 pts).

3. Algorithm Foundation (25 points): Strong algorithm knowledge reserve (20-25 pts); Some programming basics but limited algorithm experience (10-19 pts); Weak or zero algorithm foundation (0-9 pts).

4. Teamwork Ability (25 points): Effective collaboration skills (20-25 pts); Some cooperative awareness (10-19 pts); Poor teamwork ability (0-9 pts).

Please return the scoring results in the following JSON format:
{{
    "思考过程": "Detailed analysis of the student's performance in four dimensions",
    "学习态度": {{
        "分数": score(0-25),
        "理由": "Specific scoring reason"
    }},
    "自学能力": {{
        "分数": score(0-25),
        "理由": "Specific scoring reason"
    }},
    "算法基础": {{
        "分数": score(0-25),
        "理由": "Specific scoring reason"
    }},
    "团队合作能力": {{
        "分数": score(0-25),
        "理由": "Specific scoring reason"
    }},
    "总分": total_score(0-100),
    "综合评价": "Overall evaluation and suggestions"
}}

Note: Please return in strict JSON format, scores must be integers, and total score is the sum of the four dimensions."""

class ModelManager:
    """模型管理器"""
    
    def __init__(self, config_file: str = "model_configs.json"):
        self.config_file = config_file
        self.models: Dict[str, BaseScoringModel] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
        self.logger = logging.getLogger(__name__)
        self._load_configs()
        self._init_models()
    
    def _load_configs(self):
        """加载模型配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    configs_data = json.load(f)
                
                for config_data in configs_data.get('models', []):
                    config = ModelConfig(
                        model_type=ModelType(config_data['model_type']),
                        model_name=config_data['model_name'],
                        api_base=config_data['api_base'],
                        api_key=config_data.get('api_key', ''),
                        max_tokens=config_data.get('max_tokens', 2000),
                        temperature=config_data.get('temperature', 0.3),
                        timeout=config_data.get('timeout', 60),
                        enable_thinking=config_data.get('enable_thinking', False),
                        description=config_data.get('description', ''),
                        cost_per_token=config_data.get('cost_per_token', 0.0)
                    )
                    self.model_configs[config.model_name] = config
            else:
                # 创建默认配置
                self._create_default_configs()
        
        except Exception as e:
            self.logger.error(f"加载模型配置失败: {e}")
            self._create_default_configs()
    
    def _create_default_configs(self):
        """创建默认模型配置"""
        default_configs = [
            {
                "model_type": "qwen-plus",
                "model_name": "qwen-plus-2025-09-11",
                "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
                "max_tokens": 2000,
                "temperature": 0.3,
                "timeout": 60,
                "enable_thinking": True,
                "description": "阿里云百炼qwen-plus模型，支持思考功能",
                "cost_per_token": 0.02
            },
            {
                "model_type": "qwen-flash",
                "model_name": "qwen-flash",
                "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
                "max_tokens": 2000,
                "temperature": 0.3,
                "timeout": 60,
                "enable_thinking": False,
                "description": "阿里云百炼qwen-flash模型，快速响应",
                "cost_per_token": 0.01
            }
        ]
        
        for config_data in default_configs:
            config = ModelConfig(
                model_type=ModelType(config_data['model_type']),
                model_name=config_data['model_name'],
                api_base=config_data['api_base'],
                api_key=config_data['api_key'],
                max_tokens=config_data['max_tokens'],
                temperature=config_data['temperature'],
                timeout=config_data['timeout'],
                enable_thinking=config_data['enable_thinking'],
                description=config_data['description'],
                cost_per_token=config_data['cost_per_token']
            )
            self.model_configs[config.model_name] = config
        
        # 保存默认配置
        self._save_configs()
    
    def _save_configs(self):
        """保存模型配置"""
        try:
            configs_data = {
                "models": []
            }
            
            for config in self.model_configs.values():
                config_dict = {
                    "model_type": config.model_type.value,
                    "model_name": config.model_name,
                    "api_base": config.api_base,
                    "api_key": config.api_key,
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "timeout": config.timeout,
                    "enable_thinking": config.enable_thinking,
                    "description": config.description,
                    "cost_per_token": config.cost_per_token
                }
                configs_data["models"].append(config_dict)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(configs_data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            self.logger.error(f"保存模型配置失败: {e}")
    
    def _init_models(self):
        """初始化模型实例"""
        for config in self.model_configs.values():
            try:
                if not config.api_key:
                    self.logger.warning(f"模型 {config.model_name} 缺少API密钥，跳过初始化")
                    continue
                
                if config.model_type in [ModelType.QWEN_PLUS, ModelType.QWEN_FLASH, ModelType.QWEN_TURBO]:
                    model = QwenModel(config)
                elif config.model_type in [ModelType.GPT_4, ModelType.GPT_35_TURBO]:
                    model = OpenAIModel(config)
                else:
                    self.logger.warning(f"不支持的模型类型: {config.model_type}")
                    continue
                
                self.models[config.model_name] = model
                self.logger.info(f"成功初始化模型: {config.model_name}")
            
            except Exception as e:
                self.logger.error(f"初始化模型 {config.model_name} 失败: {e}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        available_models = []
        
        for config in self.model_configs.values():
            model_info = {
                "model_name": config.model_name,
                "model_type": config.model_type.value,
                "description": config.description,
                "enable_thinking": config.enable_thinking,
                "cost_per_token": config.cost_per_token,
                "available": config.model_name in self.models
            }
            available_models.append(model_info)
        
        return available_models
    
    def get_model(self, model_name: str) -> Optional[BaseScoringModel]:
        """获取指定模型"""
        return self.models.get(model_name)
    
    def add_model(self, config: ModelConfig) -> bool:
        """添加新模型"""
        try:
            self.model_configs[config.model_name] = config
            self._save_configs()
            self._init_models()
            return True
        except Exception as e:
            self.logger.error(f"添加模型失败: {e}")
            return False
    
    def remove_model(self, model_name: str) -> bool:
        """移除模型"""
        try:
            if model_name in self.model_configs:
                del self.model_configs[model_name]
            if model_name in self.models:
                del self.models[model_name]
            self._save_configs()
            return True
        except Exception as e:
            self.logger.error(f"移除模型失败: {e}")
            return False
    
    def compare_models(self, student_info: Dict[str, Any], model_names: List[str]) -> Dict[str, Any]:
        """比较多个模型的评分结果"""
        comparison_result = {
            "student_info": student_info,
            "model_results": {},
            "analysis": {},
            "recommendation": ""
        }
        
        for model_name in model_names:
            model = self.get_model(model_name)
            if model:
                try:
                    result = model.score_student(student_info)
                    comparison_result["model_results"][model_name] = result
                except Exception as e:
                    self.logger.error(f"模型 {model_name} 评分失败: {e}")
                    comparison_result["model_results"][model_name] = {
                        "error": str(e),
                        "total_score": 0
                    }
            else:
                comparison_result["model_results"][model_name] = {
                    "error": "模型不可用",
                    "total_score": 0
                }
        
        # 分析结果
        valid_results = {k: v for k, v in comparison_result["model_results"].items() 
                        if not v.get("error")}
        
        if valid_results:
            scores = [result["total_score"] for result in valid_results.values()]
            comparison_result["analysis"] = {
                "average_score": sum(scores) / len(scores),
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "score_variance": max(scores) - min(scores),
                "model_count": len(valid_results)
            }
            
            # 推荐模型
            best_model = max(valid_results.items(), key=lambda x: x[1]["total_score"])
            comparison_result["recommendation"] = f"推荐使用 {best_model[0]} 模型，得分 {best_model[1]['total_score']}"
        
        return comparison_result


def main():
    """测试多模型支持功能"""
    manager = ModelManager()
    
    # 显示可用模型
    available_models = manager.get_available_models()
    print("可用模型:")
    for model in available_models:
        status = "✅" if model["available"] else "❌"
        print(f"  {status} {model['model_name']}: {model['description']}")
    
    # 测试评分
    test_student = {
        'id': '001',
        'name': '张三',
        'content': '我对算法竞赛非常感兴趣，自学能力强，有良好的算法基础，团队合作能力优秀。'
    }
    
    print("\n测试评分:")
    for model_name in manager.models.keys():
        try:
            model = manager.get_model(model_name)
            if model:
                result = model.score_student(test_student)
                print(f"\n{model_name} 评分结果:")
                print(f"  总分: {result.get('总分', 0)}")
                print(f"  综合评价: {result.get('综合评价', '无')}")
        except Exception as e:
            print(f"  错误: {e}")
    
    # 模型比较
    if len(manager.models) >= 2:
        model_names = list(manager.models.keys())[:2]
        comparison = manager.compare_models(test_student, model_names)
        print(f"\n模型比较结果:")
        print(f"  平均分: {comparison['analysis'].get('average_score', 0):.2f}")
        print(f"  推荐: {comparison['recommendation']}")


if __name__ == "__main__":
    main()