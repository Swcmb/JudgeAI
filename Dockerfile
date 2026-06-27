# ============================================================
# 多阶段构建：JudgeAI API 服务
# 基于 python:3.11-slim，使用 gunicorn 作为生产 WSGI 服务器
# ============================================================

# --- 第一阶段：构建依赖 ---
FROM python:3.11-slim AS builder

# 设置构建环境变量，禁止生成 .pyc 并启用无缓冲输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# 安装编译依赖（部分 Python 包需要编译 C 扩展）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# 单独复制并安装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- 第二阶段：生产镜像 ---
FROM python:3.11-slim AS production

LABEL maintainer="JudgeAI Team" \
      description="算法竞赛团队AI评分系统 API 服务" \
      version="1.0.0"

# 设置运行环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    GUNICORN_WORKERS=4 \
    GUNICORN_BIND=0.0.0.0:5000

WORKDIR /app

# 从构建阶段复制已安装的 Python 包
COPY --from=builder /install /usr/local

# 安装运行时最小依赖（curl 用于健康检查）
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r judgeai && \
    useradd -r -g judgeai -d /app -s /sbin/nologin judgeai

# 创建必要的运行时目录
RUN mkdir -p uploads downloads charts reports logs && \
    chown -R judgeai:judgeai /app

# 复制应用代码
COPY --chown=judgeai:judgeai *.py ./
COPY --chown=judgeai:judgeai sample_students*.csv ./

# 切换到非 root 用户
USER judgeai

# 暴露服务端口
EXPOSE 5000

# 环境变量声明（部署时通过 -e 或 .env 注入）
# DASHSCOPE_API_KEY  - 通义千问 API 密钥
# JWT_SECRET_KEY     - JWT 签名密钥

# 健康检查：每30秒检测 /health 端点
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 使用 gunicorn 启动应用
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
