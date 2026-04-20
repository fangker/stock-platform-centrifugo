"""
SDK 配置
"""
import os

BACKEND_URL = os.getenv(
    "STOCK_PLATFORM_BACKEND_URL",
    "http://localhost:8888"
)


class SDKConfig:
    """SDK 配置"""

    def __init__(self, access_key, secret_key, strategy_name, backend_url=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.strategy_name = strategy_name
        self.backend_url = backend_url or BACKEND_URL
        self.token = None
