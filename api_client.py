"""
阿里云百炼API调用模块
用于调用qwen-plus模型进行AI评分
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional
from openai import OpenAI


class BaiLianAPIClient:
    """阿里云百炼API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥，如果为None则从环境变量DASHSCOPE_API_KEY获取
            base_url: API基础URL
        """
        self.logger = logging.getLogger(__name__)
        
        # 获取API密钥
        if api_key is None:
            api_key = os.getenv("DASHSCOPE_API_KEY")
            
        if not api_key:
            raise ValueError("API密钥未设置，请设置环境变量DASHSCOPE_API_KEY或直接传入api_key参数")
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        self.model = "qwen-flash"
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def create_scoring_prompt(self, student_info: str) -> str:
        """
        创建评分提示词
        
        Args:
            student_info: 学生信息
            
        Returns:
            格式化的提示词
        """
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
    
    def call_api(self, prompt: str) -> Dict[str, Any]:
        """
        调用API进行评分（启用思考功能）
        
        Args:
            prompt: 提示词
            
        Returns:
            API响应结果
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"正在调用API，尝试第 {attempt + 1} 次...")
                
                messages = [
                    {"role": "system", "content": "你是一位专业的算法竞赛团队选拔专家，需要客观公正地评估学生的能力。"},
                    {"role": "user", "content": prompt}
                ]
                
                completion = self.client.chat.completions.create(
                    model="qwen-plus-2025-09-11",  # 使用支持思考的模型
                    messages=messages,
                    temperature=0.3,  # 降低随机性，提高一致性
                    # 启用思考过程
                    extra_body={"enable_thinking": True},
                    stream=True
                )
                
                # 处理流式响应
                reasoning_content = ""  # 完整思考过程
                answer_content = ""  # 完整回复
                is_answering = False  # 是否进入回复阶段
                
                self.logger.info("开始接收AI思考过程...")
                
                for chunk in completion:
                    if not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # 收集思考内容
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                        reasoning_content += delta.reasoning_content
                    
                    # 收集回复内容
                    if hasattr(delta, "content") and delta.content:
                        if not is_answering:
                            is_answering = True
                            self.logger.info("AI开始生成回复...")
                        answer_content += delta.content
                
                self.logger.info("API调用成功，开始解析响应...")
                
                # 尝试解析JSON响应
                try:
                    result = json.loads(answer_content)
                    # 将思考过程添加到结果中
                    if reasoning_content:
                        result['AI思考过程'] = reasoning_content
                    return result
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON解析失败，尝试提取JSON内容: {e}")
                    # 尝试从响应中提取JSON部分
                    result = self._extract_json_from_response(answer_content)
                    if result:
                        # 将思考过程添加到结果中
                        if reasoning_content:
                            result['AI思考过程'] = reasoning_content
                        return result
                    else:
                        # 如果无法解析JSON，返回原始内容和思考过程
                        return {
                            '思考过程': reasoning_content if reasoning_content else "无思考过程",
                            '原始回复': answer_content,
                            '解析错误': f"无法解析为JSON格式: {str(e)}",
                            '学习态度': {'分数': 0, '理由': 'JSON解析失败'},
                            '自学能力': {'分数': 0, '理由': 'JSON解析失败'},
                            '算法基础': {'分数': 0, '理由': 'JSON解析失败'},
                            '团队合作能力': {'分数': 0, '理由': 'JSON解析失败'},
                            '总分': 0,
                            '综合评价': f'API响应解析失败: {str(e)}',
                            'error': True
                        }
                
            except Exception as e:
                self.logger.error(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    self.logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # 指数退避
                else:
                    raise Exception(f"API调用失败，已重试 {self.max_retries} 次: {e}")
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从响应中提取JSON内容
        
        Args:
            response: API响应内容
            
        Returns:
            提取的JSON数据，如果失败返回None
        """
        try:
            # 查找JSON代码块
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            
            # 查找花括号包围的内容
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
                
        except Exception as e:
            self.logger.error(f"提取JSON失败: {e}")
        
        return None
    
    def score_student(self, student_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        为单个学生评分
        
        Args:
            student_info: 学生信息字典
            
        Returns:
            评分结果
        """
        try:
            # 构建学生信息字符串
            info_parts = []
            if student_info.get('name'):
                info_parts.append(f"姓名: {student_info['name']}")
            if student_info.get('id'):
                info_parts.append(f"学号: {student_info['id']}")
            if student_info.get('content'):
                info_parts.append(f"个人信息: {student_info['content']}")
            
            # 添加其他字段
            for key, value in student_info.items():
                if key not in ['name', 'id', 'content'] and value:
                    info_parts.append(f"{key}: {value}")
            
            student_info_str = "\n".join(info_parts)
            
            # 创建提示词
            prompt = self.create_scoring_prompt(student_info_str)
            
            # 调用API
            result = self.call_api(prompt)
            
            # 添加学生基本信息到结果中
            result['学生信息'] = {
                'id': student_info.get('id', ''),
                'name': student_info.get('name', ''),
                'content': student_info.get('content', '')
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"为学生 {student_info.get('name', 'Unknown')} 评分失败: {e}")
            # 返回错误结果
            return {
                '学生信息': {
                    'id': student_info.get('id', ''),
                    'name': student_info.get('name', ''),
                    'content': student_info.get('content', '')
                },
                '思考过程': f"评分失败: {str(e)}",
                '学习态度': {'分数': 0, '理由': '评分失败'},
                '自学能力': {'分数': 0, '理由': '评分失败'},
                '算法基础': {'分数': 0, '理由': '评分失败'},
                '团队合作能力': {'分数': 0, '理由': '评分失败'},
                '总分': 0,
                '综合评价': f'评分失败: {str(e)}',
                'error': True
            }


def main():
    """测试函数"""
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据
    test_student = {
        'id': '001',
        'name': '张三',
        'content': '我对算法很感兴趣，经常自学新的算法知识，参加过多次编程竞赛，获得过省级奖项。在团队项目中担任技术负责人，能够很好地与队友协作完成任务。'
    }
    
    try:
        # 检查环境变量
        if not os.getenv("DASHSCOPE_API_KEY"):
            print("请设置环境变量 DASHSCOPE_API_KEY")
            return
        
        client = BaiLianAPIClient()
        result = client.score_student(test_student)
        
        print("评分结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    main()