# coding:utf-8
"""
Docker 入口脚本

启动 WebSocket 客户端，收到信号后写入 Redis Stream。
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime


def setup_logging():
    log_dir = "/app/logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bridge.log")

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # 同时输出到 stdout（docker logs 可看）
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    return logging.getLogger("bridge")


def main():
    log = setup_logging()
    info = log.info
    # 等待 Redis 就绪
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD", "") or None
    redis_stream = os.getenv("REDIS_STREAM_NAME", "smallgo")

    info("=" * 60)
    info("Stock Platform Redis Bridge")
    info("=" * 60)

    # 配置 SDK
    from stock_platform_sdk import configure

    configure(
        access_key=os.getenv("ACCESS_KEY"),
        secret_key=os.getenv("SECRET_KEY"),
        strategy_name=os.getenv("STRATEGY_NAME", "default"),
        backend_url=os.getenv("BACKEND_URL"),
        centrifugo_url=os.getenv("CENTRIFUGO_URL"),
    )
    info(f"SDK 配置完成, strategy: {os.getenv('STRATEGY_NAME', 'default')}")

    # 创建 Redis writer
    from stock_platform_sdk.redis_bridge import create_redis_writer

    write_to_redis = None
    for attempt in range(30):
        try:
            write_to_redis = create_redis_writer(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                stream_name=redis_stream,
            )
            break
        except Exception as e:
            info(f"等待 Redis 就绪... ({attempt + 1}/30): {e}")
            time.sleep(2)

    if not write_to_redis:
        info("无法连接 Redis，退出")
        sys.exit(1)

    # 启动 WebSocket
    from stock_platform_sdk.centrifugo_websocket_client import create_websocket_handler

    config = __import__("stock_platform_sdk", fromlist=["get_config"]).get_config()
    handler = create_websocket_handler(
        config.access_key, config.secret_key, config.strategy_name, config=config
    )

    async def run():
        info("正在连接 WebSocket...")
        if not await handler.connect():
            info("WebSocket 连接失败，退出")
            sys.exit(1)

        info(f"WebSocket 连接成功, UID: {handler.get_uid()}")

        def on_message(data):
            info(f"收到信号: action={data.get('action')}, code={data.get('code')}, price={data.get('price')}")
            write_to_redis(data)

        channel = f"trade:{config.strategy_name}"
        await handler.subscribe(channel, on_message)
        info(f"订阅频道: {channel}")
        info("Bridge 就绪，等待信号...")

        while handler.is_connected:
            await asyncio.sleep(1)

        info("WebSocket 连接断开")

    # 自动重连
    while True:
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            info("退出")
            break
        except Exception as e:
            log.error(f"异常: {e}, 5 秒后重连...")
            time.sleep(5)


if __name__ == "__main__":
    main()
