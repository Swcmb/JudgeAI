"""
WSGI入口文件
供gunicorn等WSGI服务器使用
"""

from flask import Flask
from api_gateway import init_api_gateway

# 创建Flask应用实例
app = Flask(__name__)

# 初始化API网关（注册路由、错误处理等）
init_api_gateway(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
