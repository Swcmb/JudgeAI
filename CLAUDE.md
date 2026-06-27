# JudgeAI - 企业级AI智能评分系统

## 项目概述

JudgeAI 是一个基于 Python Flask 的 REST API 服务，用于评估学生是否适合参加算法竞赛团队。系统调用阿里云百炼（DashScope）大模型，从学习态度、自学能力、算法基础、团队合作四个维度进行自动评分，每维度 25 分，总分 100 分。

## 核心入口

| 文件 | 用途 | 启动方式 |
|:-----|:-----|:---------|
| `quick_start.py` | API 服务器启动脚本（带环境检查、依赖检测、交互式菜单） | `python quick_start.py` |
| `main.py` | CLI 工具，命令行批量评分 | `python main.py --input students.csv --output results.xlsx` |

## 关键模块

| 模块 | 职责 |
|:-----|:-----|
| `api_gateway.py` | Flask REST API 网关，定义所有 `/api/v1/*` 路由，集成安全、任务管理等中间件 |
| `api_client.py` | 基础百炼 API 客户端，封装 OpenAI 兼容接口调用 |
| `enhanced_api_client.py` | 增强版客户端，增加缓存、批量处理、智能重试 |
| `async_task_manager.py` | 多线程异步任务队列，支持进度追踪和状态管理 |
| `enhanced_security.py` | JWT 认证、RBAC 权限控制、审计日志 |
| `user_management.py` | 用户 CRUD 与角色管理 |
| `enhanced_config_manager.py` | 动态评分维度配置、模板系统、变更追踪 |
| `config_manager.py` | 基础配置管理 |
| `file_reader.py` | 多格式文件读取（CSV / Excel / JSON / TXT） |
| `result_processor.py` | 评分结果后处理、报告生成 |
| `batch_import.py` | 批量数据导入 |
| `visualization_enhanced.py` | Plotly / Matplotlib 数据可视化 |
| `history_manager.py` | 评分历史记录管理 |
| `multi_model_support.py` | 多 AI 模型适配层 |

## 开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 设置必需的环境变量
export DASHSCOPE_API_KEY="your_api_key"
export JWT_SECRET_KEY="your_jwt_secret"

# 启动开发服务器（默认 http://localhost:5000）
python quick_start.py

# 运行 CLI 批量评分
python main.py --input students.csv --output results.xlsx

# 生产部署（gunicorn）
gunicorn -w 4 -b 0.0.0.0:5000 "api_gateway:app"

# Docker 构建与运行
docker build -t judgeai-api:latest .
docker run -d -p 5000:5000 \
  -e DASHSCOPE_API_KEY="your_key" \
  -e JWT_SECRET_KEY="your_secret" \
  judgeai-api:latest

# 运行测试
python test_system.py
python test_upload.py
```

## 架构说明

```
客户端 (浏览器 / 移动端 / 第三方)
        |
        v
  api_gateway.py  (Flask REST API, /api/v1/*)
        |
        +-- enhanced_security.py   (JWT 认证 + RBAC)
        +-- async_task_manager.py  (异步任务队列)
        +-- enhanced_config_manager.py (评分维度/模板配置)
        |
        v
  enhanced_api_client.py  (缓存 + 批量 + 重试)
        |
        v
  阿里云百炼 DashScope API  (qwen-plus 深度思考模型)
        |
        v
  result_processor.py  (结果后处理 + 报告生成)
```

- **前端**：Flask 提供纯 REST API，无内置前端页面
- **AI 引擎**：通过 OpenAI 兼容接口调用阿里云百炼 qwen-plus 模型，启用深度思考功能
- **数据格式**：输入支持 CSV / Excel / JSON / TXT，输出支持 Excel / CSV / JSON 统计报告
- **安全层**：JWT 令牌认证，RBAC 权限控制，审计日志
- **任务系统**：大文件异步处理，支持任务队列和进度追踪

## 环境变量

| 变量 | 必需 | 说明 |
|:-----|:-----|:-----|
| `DASHSCOPE_API_KEY` | 是 | 阿里云百炼 API 密钥，无此密钥无法调用 AI 评分 |
| `JWT_SECRET_KEY` | 是 | JWT 签名密钥，用于用户认证 |
| `ADMIN_USERNAME` | 否 | 管理员用户名，默认 `admin` |
| `ADMIN_PASSWORD` | 否 | 管理员密码，默认 `admin123` |

## 注意事项

- `DASHSCOPE_API_KEY` 是核心依赖，缺失将导致所有 AI 评分功能不可用
- `quick_start.py` 会自动检测 Python 版本（需 3.8+）和依赖安装情况
- 生产环境应使用 gunicorn 而非 Flask 内置开发服务器
- Docker 镜像采用多阶段构建，基于 `python:3.11-slim`，以非 root 用户运行
- 项目使用 `security.db`（SQLite）存储用户和会话数据
- `uploads/` 和 `downloads/` 目录用于文件输入输出，Docker 中需挂载卷持久化
