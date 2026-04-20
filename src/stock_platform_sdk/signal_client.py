"""
信号查询 HTTP 客户端

通过 HTTP API 查询 Redis Stream 中的交易信号。
"""
import json
import logging

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests not installed. Run: pip install requests")

logger = logging.getLogger("stock_platform_sdk")


class SignalClient:
    """
    信号查询客户端

    通过 HTTP API 登录获取 JWT token，然后轮询查询 Redis Stream 中的交易信号。
    """

    def __init__(self, config):
        self.config = config
        self._last_id = "-"

    def login(self) -> str:
        """
        登录获取 JWT token。

        Returns:
            JWT token 字符串
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests not installed. Run: pip install requests")

        url = f"{self.config.backend_url}/signal/login"
        resp = requests.post(url, json={
            "access_key": self.config.access_key,
            "secret_key": self.config.secret_key,
        }, timeout=10)

        if resp.status_code != 200:
            raise RuntimeError(f"login failed: status={resp.status_code}, body={resp.text}")

        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"login failed: {data}")

        result = data["data"]
        self.config.token = result["token"]
        logger.info("login success, expire_at=%s", result["expireAt"])
        return self.config.token

    def query_signals(self, last_id=None, count=10):
        """
        查询最新信号。

        Args:
            last_id: 上次最后一条的 Redis Stream ID（可选，默认从上次位置继续）
            count: 返回条数（默认10）

        Returns:
            信号列表，每项包含 id 和 fields

        Raises:
            RuntimeError: 未登录或请求失败
        """
        if not self.config.token:
            raise RuntimeError("not logged in, call login() first")

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests not installed. Run: pip install requests")

        if last_id is None:
            last_id = self._last_id

        url = f"{self.config.backend_url}/signal/latest"
        headers = {"Authorization": f"Bearer {self.config.token}"}
        params = {
            "strategy": self.config.strategy_name,
            "last_id": last_id,
            "count": count,
        }

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"query failed: status={resp.status_code}, body={resp.text}")

        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"query failed: {data}")

        entries = data["data"]

        # 自动更新 last_id
        if entries:
            last_entry = entries[-1]
            self._last_id = last_entry["id"]

        return entries

    def get_last_id(self) -> str:
        """获取上次查询的最后一条 Stream ID。"""
        return self._last_id
