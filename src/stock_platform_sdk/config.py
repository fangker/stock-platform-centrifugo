"""
Centrifugo 配置常量
"""
import os

# 后端服务器配置（用于获取 JWT）
CENTRIFUGO_BACKEND_URL = os.getenv(
    "CENTRIFUGO_BACKEND_URL",
    "http://localhost:8888"
)

# Centrifugo WebSocket 服务器
CENTRIFUGO_CENTRIFUGO_URL = os.getenv(
    "CENTRIFUGO_CENTRIFUGO_URL",
    "http://localhost:8000"
)

# 默认请求超时时间（秒）
CENTRIFUGO_TIMEOUT = 10
