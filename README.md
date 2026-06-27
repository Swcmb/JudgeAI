# JudgeAI - 企业级AI智能评分系统 🚀

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://typescriptlang.org)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![AI](https://img.shields.io/badge/AI-多模型支持-orange.svg)](https://dashscope.aliyun.com)

## 📋 项目简介

JudgeAI是一个功能完整的企业级AI智能评分平台，专门用于评估学生是否适合参加算法竞赛团队。项目采用现代化的API架构，提供REST API接口、数据可视化、异步处理、多模型支持等高级功能。

### 🎯 核心价值
- **智能化评估**: 基于先进AI模型，提供客观、公正的评分
- **全栈架构**: 支持传统Flask和现代Next.js两种部署方式
- **企业级特性**: 完整的用户管理、权限控制、审计日志
- **高度可定制**: 灵活的评分维度和模板系统
- **高性能设计**: 异步处理、智能缓存、批量优化

## ✨ 核心特性

### 🎯 AI智能评分
- 🧠 **深度思考评分**: 基于阿里云百炼qwen-plus模型，启用AI深度思考功能
- 📊 **四维度评估**: 学习态度、自学能力、算法基础、团队合作能力（每维度25分）
- 🎯 **智能分析**: 详细推理过程，客观公正的评分理由
- ⚙️ **自定义评分**: 支持自定义评分维度、权重和标准

### 🌐 现代化API接口
- 📡 **REST API**: 完整的RESTful API接口，支持JSON格式
- 📚 **API文档**: 详细的API文档和SDK示例
- 🔌 **第三方集成**: 支持与其他系统无缝集成
- 📡 **Webhook支持**: 事件驱动的通知机制

### ⚡ 高性能架构
- 🚀 **异步处理**: 大文件异步处理，支持1000+并发用户
- 🗄️ **智能缓存**: API结果缓存，减少重复调用，提升性能
- 📈 **批量优化**: 批量请求处理，智能频率控制
- 🔧 **任务管理**: 完整的任务队列和进度追踪系统

### 🔒 企业级安全
- 🔐 **JWT认证**: 安全的用户认证和授权机制
- 👥 **权限管理**: 基于角色的访问控制（RBAC）
- 📝 **审计日志**: 完整的操作审计和变更追踪
- 🔒 **数据加密**: 敏感数据加密存储和传输

### 🔌 开放API生态
- 🌐 **REST API**: 完整的RESTful API接口
- 📚 **API文档**: 详细的API文档和SDK示例
- 🔗 **第三方集成**: 支持与其他系统无缝集成
- 📡 **Webhook支持**: 事件驱动的通知机制

## 🚀 快速开始

JudgeAI提供基于API的部署方式，专注于后端服务。

### 📋 系统要求

- Python 3.8+
- 阿里云百炼API密钥
- 4GB+ RAM（推荐）

### ⚡ 一键启动

```bash
# 安装依赖
pip install -r requirements.txt

# 设置API密钥
export DASHSCOPE_API_KEY="your_api_key_here"
export JWT_SECRET_KEY="your_jwt_secret_key"

# 启动API服务器
python quick_start.py
```
API访问: http://localhost:5000/api

### 📖 详细文档

| 文档类型 | 描述 | 链接 |
|---------|------|------|
| 📚 **完整使用指南** | 系统详细使用说明 | [查看文档](./COMPLETE_USER_GUIDE.md) |
| 🔌 **API文档** | 完整REST API接口说明和示例 | [查看文档](./API_DOCUMENTATION.md) |
| 🔧 **功能扩展指南** | 高级功能配置和自定义说明 | [查看文档](./EXTENSION_GUIDE.md) |

## 📊 评分标准

系统基于以下四个维度进行评分，每个维度25分，总分100分：

### 📚 学习态度（25分）
- **20-25分**: 积极主动、有强烈学习意愿，主动学习新知识
- **10-19分**: 学习态度一般，需要督促，但有一定学习意愿
- **0-9分**: 态度消极、缺乏学习动力

### 💡 自学能力（25分）
- **20-25分**: 具备独立解决问题能力，有自学经历
- **10-19分**: 有一定自学能力但需要指导
- **0-9分**: 依赖他人指导较多

### 🔧 算法基础（25分）
- **20-25分**: 有算法知识储备，有竞赛经历
- **10-19分**: 有一定编程基础但算法经验不足
- **0-9分**: 算法基础薄弱或零基础

### 👥 团队合作能力（25分）
- **20-25分**: 能有效合作、沟通顺畅，有团队项目经验
- **10-19分**: 有一定合作意识，能够参与团队活动
- **0-9分**: 团队合作能力欠佳

## 🛠️ 核心模块

### 🌉 API网关 (`api_gateway.py`)
- 完整的REST API接口
- 第三方集成支持，Webhook通知
- API文档，SDK示例

### 🤖 AI评分引擎 (`enhanced_api_client.py`)
- 增强版API客户端，支持缓存和批量处理
- 智能重试机制，错误处理优化
- 多模型支持，自定义评分模板

### ⚡ 异步任务管理 (`async_task_manager.py`)
- 多线程异步任务处理
- 任务队列、进度追踪、状态管理
- 支持大规模并发评分

### 🔒 安全管理 (`enhanced_security.py`)
- JWT认证、数据加密、权限控制
- 用户管理、审计日志、会话管理
- Flask安全集成中间件

### ⚙️ 配置管理 (`enhanced_config_manager.py`)
- 动态配置管理，自定义评分维度
- 评分模板系统，配置变更追踪
- 配置导入导出，实时更新

### 🌉 API网关 (`api_gateway.py`)
- 完整的REST API接口
- 第三方集成支持，Webhook通知
- API文档，SDK示例

## 📱 移动端支持

### API特性
- 📱 响应式API设计，支持移动端调用
- 🔄 RESTful接口，易于移动端集成
- 📊 JSON格式数据，便于移动端处理
- 🔌 标准HTTP接口，跨平台兼容

## 🔌 API集成

### 认证
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### 提交评分任务
```bash
curl -X POST http://localhost:5000/api/v1/scoring/submit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "students": [
      {
        "id": "001",
        "name": "张三",
        "content": "我是一名计算机专业的学生..."
      }
    ],
    "async": true
  }'
```

### 查询任务状态
```bash
curl -X GET http://localhost:5000/api/v1/tasks/{task_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 数据格式

### 支持的文件格式
- 📄 **CSV**: 逗号分隔值文件
- 📊 **Excel**: .xlsx/.xls 文件
- 📋 **JSON**: 结构化数据文件
- 📝 **TXT**: 纯文本文件

### 数据格式示例
```json
[
  {
    "id": "001",
    "name": "张三",
    "content": "我是一名计算机专业的学生，对算法竞赛很感兴趣...",
    "template_id": "custom_template"
  }
]
```

## 📈 输出结果

系统会生成多格式的评分结果：

### 📊 Excel报告
- **评分结果**: 主要评分信息和统计数据
- **详细评分**: 四个维度的详细分数和理由
- **分析图表**: 可视化图表和趋势分析

### 📄 CSV数据
- 结构化的评分数据，便于进一步处理
- 包含AI思考过程和评分理由

### 📋 JSON格式
- 完整的API响应数据
- 便于系统集成和二次开发

### 📑 统计报告
- 整体统计分析
- 推荐学生名单
- 改进建议

## 🔧 高级配置

### 环境变量
```bash
# 必需配置
export DASHSCOPE_API_KEY="your_dashscope_api_key"
export JWT_SECRET_KEY="your_jwt_secret_key"

# 可选配置
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="admin123"
export ADMIN_EMAIL="admin@example.com"
```

### 自定义评分维度
```python
from enhanced_config_manager import get_enhanced_config_manager

config_manager = get_enhanced_config_manager()

# 创建自定义维度
dimension_id = config_manager.create_custom_dimension(
    name="创新思维",
    weight=0.2,
    max_score=20,
    description="评估学生的创新能力和思维方式",
    scoring_criteria=[
        {"range": "16-20", "description": "具有很强创新能力"},
        {"range": "10-15", "description": "有一定创新意识"},
        {"range": "0-9", "description": "创新能力较弱"}
    ],
    created_by="admin"
)
```

### 自定义评分模板
```python
# 创建评分模板
template_id = config_manager.create_template(
    name="算法竞赛专项模板",
    description="专门用于算法竞赛选拔的评分模板",
    dimension_ids=["learning_attitude", "self_study", "algorithm", "teamwork", "innovation"],
    is_default=True,
    created_by="admin"
)
```

## 📁 项目结构

JudgeAI 采用 Python Flask API 架构，支持命令行和 REST API 两种使用方式：

```
JudgeAI/
├── 🚀 应用入口
│   ├── quick_start.py                # 一键启动脚本
│   ├── main.py                       # 命令行工具
│   └── wsgi.py                       # WSGI入口（gunicorn使用）
│
├── 🤖 AI评分引擎
│   ├── api_client.py                 # 基础API客户端
│   ├── enhanced_api_client.py        # 增强版API客户端
│   └── multi_model_support.py        # 多模型支持
│
├── ⚡ 核心服务
│   ├── async_task_manager.py         # 异步任务管理
│   ├── file_reader.py                # 文件读取
│   ├── result_processor.py           # 结果处理
│   └── batch_import.py               # 批量导入
│
├── 🔒 安全系统
│   ├── enhanced_security.py          # 增强安全管理
│   └── user_management.py            # 用户管理
│
├── ⚙️ 配置管理
│   ├── config_manager.py             # 基础配置管理
│   └── enhanced_config_manager.py    # 增强配置管理
│
├── 🌉 API网关
│   └── api_gateway.py                # API网关（Flask REST API）
│
├── 📊 数据分析
│   ├── visualization_enhanced.py     # 数据可视化
│   └── history_manager.py            # 历史管理
│
├── 🐳 Docker 部署
│   ├── Dockerfile                    # Docker镜像定义（多阶段构建）
│   ├── docker-compose.yml            # Docker Compose编排
│   └── .dockerignore                 # Docker构建忽略规则
│
├── 📚 文档
│   ├── README.md                     # 主文档（本文档）
│   ├── CLAUDE.md                     # AI开发助手上下文
│   ├── API_DOCUMENTATION.md          # API详细文档
│   └── EXTENSION_GUIDE.md            # 功能扩展指南
│
├── 📦 配置文件
│   ├── requirements.txt              # Python依赖
│   ├── .env.example                  # 环境变量示例
│   └── .gitignore                    # Git忽略规则
│
└── 📋 数据文件
    ├── ApplicationForm.xlsx          # 示例数据
    └── uploads/                      # 上传文件目录
```

## 🚀 详细部署指南

### 🐍 API服务器部署

#### 开发环境
```bash
# 1. 克隆项目
git clone https://github.com/Swcmb/JudgeAI.git
cd JudgeAI

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 设置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要配置：
# DASHSCOPE_API_KEY=your_api_key
# JWT_SECRET_KEY=your_jwt_secret
# ADMIN_USERNAME=admin
# ADMIN_PASSWORD=admin123

# 5. 初始化系统
python quick_start.py

# 6. 启动API服务器
python quick_start.py
# 选择选项1启动API服务器
```

#### 生产环境
```bash
# 1. 安装生产服务器
pip install gunicorn

# 2. 使用Gunicorn启动
gunicorn -w 4 -b 0.0.0.0:5000 "api_gateway:app"

# 3. Nginx反向代理配置
# 创建 /etc/nginx/sites-available/judgeapi 文件：
"""
server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""

# 4. 启用配置
sudo ln -s /etc/nginx/sites-available/judgeapi /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 🐳 Docker部署

#### API服务器版本
```bash
# 1. 构建镜像
docker build -t judgeai-api:latest .

# 2. 运行容器
docker run -d \
  --name judgeai-api \
  -p 5000:5000 \
  -e DASHSCOPE_API_KEY="your_api_key" \
  -e JWT_SECRET_KEY="your_jwt_secret" \
  -v $(pwd)/data:/app/data \
  judgeai-api:latest

# 3. 使用Docker Compose
docker-compose -f docker-compose.api.yml up -d
```

### ☁️ 云服务部署

#### Railway
```bash
# 1. 安装Railway CLI
npm install -g @railway/cli

# 2. 登录并部署
railway login
railway up
```

#### AWS ECS
```bash
# 1. 构建镜像并推送到ECR
docker build -t judgeai-api:latest .
docker tag judgeai-api:latest your-account.dkr.ecr.region.amazonaws.com/judgeai-api:latest
docker push your-account.dkr.ecr.region.amazonaws.com/judgeai-api:latest

# 2. 部署到ECS
# 使用AWS控制台或CLI创建ECS服务
```

## 📈 监控与日志

### 日志系统
- 📝 结构化日志记录
- 🔄 日志轮转管理
- 📊 日志级别控制
- 🔍 错误追踪

### 性能监控
- 📊 API响应时间监控
- 🗄️ 数据库性能监控
- 💾 内存使用监控
- 🌐 系统资源监控

### 健康检查
```bash
# 系统状态检查
curl http://localhost:5000/api/v1/info

# 数据库连接检查
curl http://localhost:5000/api/v1/health

# API服务状态检查
curl http://localhost:5000/api/v1/status
```

## 🤝 贡献指南

### 开发流程
1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

### 代码规范
- 📝 遵循PEP 8代码风格
- 🧪 编写单元测试
- 📚 更新相关文档
- 🔍 代码审查通过

### 问题反馈
- 🐛 Bug报告：使用GitHub Issues
- 💡 功能建议：在Discussions中讨论
- 📞 技术支持：联系维护团队

## 📄 许可证

本项目采用 [MIT许可证](LICENSE)，详见LICENSE文件。

## 🙏 致谢

- 🚀 [阿里云百炼](https://dashscope.aliyun.com) - 提供强大的AI模型支持
- 📊 [Plotly](https://plotly.com) - 数据可视化库
- 🐍 [Flask](https://flask.palletsprojects.com) - API框架

## 📞 联系我们

- 📧 邮箱: support@judgeai.com
- 🌐 官网: https://judgeai.com
- 📚 文档: https://docs.judgeai.com
- 💬 讨论: https://github.com/Swcmb/JudgeAI/discussions

---

**⭐ 如果这个项目对你有帮助，请给我们一个Star！**