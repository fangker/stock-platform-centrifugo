"""
Redis Stream Bridge

WebSocket 收到信号后，通过 XADD 写入 Redis Stream，供 QMT 消费。
"""

import json
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def create_redis_writer(
    host: str,
    port: int,
    password: Optional[str] = None,
    stream_name: str = "smallgo",
    max_len: Optional[int] = 10000,
) -> Callable[[dict], None]:
    """
    创建 Redis Stream 写入回调。

    Args:
        host: Redis 主机地址
        port: Redis 端口
        password: Redis 密码（可选）
        stream_name: Redis Stream 名称
        max_len: Stream 最大长度，超出后自动裁剪（默认 10000）

    Returns:
        回调函数，接收 dict 参数，写入 Redis Stream
    """
    import redis as redis_lib

    kwargs = {
        "host": host,
        "port": port,
        "decode_responses": True,
    }
    if password:
        kwargs["password"] = password

    r = redis_lib.Redis(**kwargs)

    # 测试连接
    r.ping()
    logger.info(f"Redis 连接成功: {host}:{port}, stream: {stream_name}")

    def write(data: dict) -> None:
        try:
            fields = {}
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    fields[k] = json.dumps(v, ensure_ascii=False)
                else:
                    fields[k] = str(v)

            r.xadd(stream_name, fields, maxlen=max_len)
            logger.info(f"写入 Redis Stream: action={data.get('action')}, code={data.get('code')}")
        except Exception as e:
            logger.error(f"写入 Redis 失败: {e}")

    return write
