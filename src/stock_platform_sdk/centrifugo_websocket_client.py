"""
Centrifugo WebSocket 客户端

使用官方 centrifuge-python SDK
"""
import asyncio
import logging
from typing import Dict, Callable, Any, Optional
from datetime import datetime
from centrifuge.handlers import (
    ClientEventHandler,
    SubscriptionEventHandler,
    ConnectedContext,
    ConnectingContext,
    DisconnectedContext,
    ErrorContext,
    SubscribedContext,
    SubscribingContext,
    SubscriptionErrorContext,
    UnsubscribedContext,
    PublicationContext,
    JoinContext,
    LeaveContext,
    ServerSubscribedContext,
    ServerSubscribingContext,
    ServerUnsubscribedContext,
    ServerPublicationContext,
    ServerJoinContext,
    ServerLeaveContext,
)

# HTTP 客户端（用于获取 token）
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logging.warning("aiohttp not installed. Run: pip install aiohttp")

# 官方 Centrifuge Python SDK
try:
    from centrifuge import Client
    from centrifuge.handlers import (
        ClientEventHandler,
        ConnectedContext,
        DisconnectedContext,
    )
    CENTRIFUGE_AVAILABLE = True
except ImportError:
    CENTRIFUGE_AVAILABLE = False
    Client = None
    ClientEventHandler = None
    ConnectedContext = None
    DisconnectedContext = None
    logging.warning("centrifuge-python not installed. Run: pip install centrifuge-python")

# 导入事件处理器
from .handlers import ClientEventLoggerHandler, SubscriptionEventLoggerHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 导入配置常量
from .config import CENTRIFUGO_BACKEND_URL, CENTRIFUGO_CENTRIFUGO_URL, CENTRIFUGO_TIMEOUT


class CentrifugoClientConfig:
    """Centrifugo 客户端配置"""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        strategy_name: str,  # New required parameter
        backend_url: str = None,
        centrifugo_url: str = None,
        timeout: int = 10
    ):
        self.backend_url = backend_url or CENTRIFUGO_BACKEND_URL
        self.centrifugo_url = centrifugo_url or CENTRIFUGO_CENTRIFUGO_URL
        self.login_endpoint = "/qmt/login"
        self.timeout = timeout or CENTRIFUGO_TIMEOUT
        self.access_key = access_key
        self.secret_key = secret_key
        self.strategy_name = strategy_name  # Store strategy_name

    @property
    def websocket_url(self) -> str:
        """生成 WebSocket URL"""
        return self.centrifugo_url.replace("http", "ws") + "/connection/websocket"

    @property
    def login_url(self) -> str:
        """完整的登录 URL"""
        return self.backend_url + self.login_endpoint


class CentrifugoWebSocketHandler:
    """
    Centrifugo WebSocket 处理器

    使用官方 centrifuge-python SDK
    """

    def __init__(self, config: Optional[CentrifugoClientConfig] = None):
        self.config = config or CentrifugoClientConfig("", "")
        self.client: Optional["Client"] = None
        self.is_connected = False
        self.subscriptions: Dict[str, Any] = {}
        self._uid: Optional[int] = None
        self._channels: list[str] = []

    async def connect(self) -> bool:
        """
        连接到 Centrifugo

        流程：
        1. 使用 centrifuge Client 连接（无需 JWT token，由 proxy 处理认证）
        """
        if not CENTRIFUGE_AVAILABLE:
            logger.error("centrifuge-python 库不可用")
            return False

        try:
            logger.info(f"正在连接: {self.config.websocket_url}")

            # 创建事件处理器
            class EventHandler(ClientEventLoggerHandler):
                def __init__(self, handler):
                    super().__init__()
                    self.handler = handler

                async def on_connected(self, ctx: ConnectedContext) -> None:
                    await super().on_connected(ctx)
                    self.handler.is_connected = True
                    # 从 context 的 data 中提取 user ID
                    # proxy 返回的 data 包含 token 和 channels，需要从 JWT token 或 channels 解析
                    if ctx.data and isinstance(ctx.data, dict):
                        uid = None
                        # 方法 1: 尝试从 JWT token 的 sub 字段解析
                        token = ctx.data.get('token')
                        if token:
                            try:
                                import base64
                                import json
                                # JWT token 格式: header.payload.signature
                                payload_b64 = token.split('.')[1]
                                # 补全 base64 padding
                                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                                payload = json.loads(base64.b64decode(payload_b64))
                                uid = payload.get('sub')
                            except Exception as e:
                                logger.debug(f"解析 JWT token 失败: {e}")

                        # 方法 2: 从 channels 数组解析 (格式如 ["test:1"])
                        if not uid:
                            channels = ctx.data.get('channels', [])
                            if channels:
                                channel = channels[0]
                                # 解析 "test:1" 格式
                                if ':' in channel:
                                    uid = channel.split(':')[-1]

                        if uid:
                            self.handler._uid = int(uid)
                            logger.info(f"✓ 连接成功, UID: {self.handler._uid}")
                        else:
                            logger.warning(f"未获取到 user ID, data={ctx.data}")

                async def on_disconnected(self, ctx: DisconnectedContext) -> None:
                    await super().on_disconnected(ctx)
                    self.handler.is_connected = False

            # 创建 Client - 使用 data 传递 access_key/secret_key
            self.client = Client(
                self.config.websocket_url,
                token=None,  # 无需 token，由 proxy 认证
                data={
                    "access_key": self.config.access_key,
                    "secret_key": self.config.secret_key
                },
                events=EventHandler(self),
                headers={"User-Agent": "centrifuge-python"}
            )

            # 连接（Centrifugo 会调用 /proxy/connect）
            await self.client.connect()

            # 等待连接完成
            for _ in range(50):
                await asyncio.sleep(0.1)
                if self.is_connected:
                    break

            # 设置默认 channels
            self._channels = [f"test:{self.config.strategy_name}"]

            return self.is_connected

        except Exception as e:
            logger.error(f"连接失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def subscribe(self, channel: str, callback: Callable) -> bool:
        """订阅频道"""
        if not self.client or not self.is_connected:
            logger.error("未连接到服务器")
            return False

        try:
            # 创建带回调的事件处理器
            class CallbackSubscriptionHandler(SubscriptionEventLoggerHandler):
                def __init__(self, cb):
                    super().__init__()
                    self.callback = cb

                async def on_publication(self, ctx: PublicationContext) -> None:
                    await super().on_publication(ctx)
                    # 调用用户传入的回调函数
                    if self.callback:
                        data = ctx.pub.data
                        if isinstance(data, str):
                            import json
                            try:
                                data = json.loads(data)
                            except:
                                pass
                        self.callback(data)

            # 创建订阅
            sub = self.client.new_subscription(
                channel,
                events=CallbackSubscriptionHandler(callback)
            )

            await sub.subscribe()
            self.subscriptions[channel] = sub
            logger.info(f"✓ 订阅成功: {channel}")
            return True

        except Exception as e:
            logger.error(f"❌ 订阅出错: {channel} | 错误: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    async def publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """发布消息到频道"""
        if not self.client or not self.is_connected:
            logger.error("未连接到服务器")
            return False

        try:
            # 发布消息
            sub = self.client.get_subscription(channel)
            if sub:
                await sub.publish(data)
                logger.info(f"✓ 已发布到 {channel}: {data}")
                return True
            else:
                logger.error(f"未订阅频道: {channel}")
                return False
        except Exception as e:
            logger.error(f"发布失败: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            logger.info("已断开 WebSocket 连接")

    def get_uid(self) -> Optional[int]:
        return self._uid

    def get_channels(self) -> list[str]:
        return self._channels


class QMTCentrifugoWebSocketHandler(CentrifugoWebSocketHandler):
    """
    QMT 交易信号 WebSocket 处理器
    """

    def __init__(self, config: Optional[CentrifugoClientConfig] = None):
        super().__init__(config)
        self.last_signals: Dict[str, Dict[str, Any]] = {}

    async def send_buy_signal(self, code: str, price: float,
                              pct: float = 100.0,
                              strategy: str = "default") -> bool:
        """发送买入信号"""
        return await self.broadcast_signal("BUY", code, price, pct, strategy)

    async def send_sell_signal(self, code: str, price: float,
                               pct: float = 100.0,
                               strategy: str = "default") -> bool:
        """发送卖出信号"""
        return await self.broadcast_signal("SELL", code, price, pct, strategy)

    async def broadcast_signal(self, action: str, code: str, price: float,
                               pct: float, strategy: str) -> bool:
        """广播交易信号"""
        message = {
            "action": action,
            "code": code,
            "price": price,
            "pct": pct,
            "strategy": strategy,
            "time": datetime.now().isoformat()
        }

        channel = f"trade:{self.config.strategy_name}"

        return await self.publish(channel, message)

    async def listen_for_signals(self, callback: Callable[[Dict[str, Any]], None]):
        """监听交易信号"""
        channel = f"trade:{self.config.strategy_name}"

        await self.subscribe(channel, callback)
        logger.info(f"开始监听交易信号: {channel}")


def create_websocket_handler(
    access_key: str,
    secret_key: str,
    strategy_name: str
) -> QMTCentrifugoWebSocketHandler:
    """
    创建 WebSocket 处理器

    Args:
        access_key: 访问密钥（必需）
        secret_key: 密钥（必需）
        strategy_name: 策略名称（必需）

    Returns:
        QMTCentrifugoWebSocketHandler: WebSocket 处理器实例
    """
    config = CentrifugoClientConfig(
        access_key=access_key,
        secret_key=secret_key,
        strategy_name=strategy_name
    )
    return QMTCentrifugoWebSocketHandler(config)


if __name__ == "__main__":
    async def main():
        """主函数示例"""
        print("=" * 60)
        print("Centrifugo WebSocket 客户端 (官方 SDK)")
        print("=" * 60)

        try:
            handler = create_websocket_handler(
                access_key="1234567",
                secret_key="1234567",
                strategy_name="test_strategy"
            )

            if await handler.connect():
                print("✓ 连接成功")

                # 发送测试信号
                await handler.send_buy_signal(
                    code="000001.SZ",
                    price=10.50,
                    strategy="test_strategy"
                )

                # 监听消息
                def on_message(data):
                    print(f"收到消息: {data}")

                await handler.listen_for_signals(on_message)

                print("\n监听中... 按 Ctrl+C 退出\n")
                while handler.is_connected:
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n\n正在断开连接...")
            await handler.disconnect()
            print("✓ 已断开")

    asyncio.run(main())
