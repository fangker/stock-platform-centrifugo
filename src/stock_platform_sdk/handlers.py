"""Centrifugo 事件处理器"""
import logging

# 官方 Centrifuge Python SDK
try:
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
    CENTRIFUGE_AVAILABLE = True
except ImportError:
    CENTRIFUGE_AVAILABLE = False
    ClientEventHandler = None
    SubscriptionEventHandler = None
    ConnectedContext = None
    ConnectingContext = None
    DisconnectedContext = None
    ErrorContext = None
    SubscribedContext = None
    SubscribingContext = None
    SubscriptionErrorContext = None
    UnsubscribedContext = None
    PublicationContext = None
    JoinContext = None
    LeaveContext = None
    ServerSubscribedContext = None
    ServerSubscribingContext = None
    ServerUnsubscribedContext = None
    ServerPublicationContext = None
    ServerJoinContext = None
    ServerLeaveContext = None
    logging.warning("centrifuge-python not installed. Run: pip install centrifuge-python")

logger = logging.getLogger(__name__)


class ClientEventLoggerHandler(ClientEventHandler):
    """客户端事件日志处理器"""

    async def on_connecting(self, ctx: ConnectingContext) -> None:
        logger.info("connecting: %s", ctx)

    async def on_connected(self, ctx: ConnectedContext) -> None:
        logger.info("connected: %s", ctx)

    async def on_disconnected(self, ctx: DisconnectedContext) -> None:
        logger.info("disconnected: %s", ctx)

    async def on_error(self, ctx: ErrorContext) -> None:
        logger.error("client error: %s", ctx)

    async def on_subscribed(self, ctx: ServerSubscribedContext) -> None:
        logger.info("subscribed server-side sub: %s", ctx)

    async def on_subscribing(self, ctx: ServerSubscribingContext) -> None:
        logger.info("subscribing server-side sub: %s", ctx)

    async def on_unsubscribed(self, ctx: ServerUnsubscribedContext) -> None:
        logger.info("unsubscribed from server-side sub: %s", ctx)

    async def on_publication(self, ctx: ServerPublicationContext) -> None:
        logger.info("publication from server-side sub: %s", ctx.pub.data)

    async def on_join(self, ctx: ServerJoinContext) -> None:
        logger.info("join in server-side sub: %s", ctx)

    async def on_leave(self, ctx: ServerLeaveContext) -> None:
        logger.info("leave in server-side sub: %s", ctx)


class SubscriptionEventLoggerHandler(SubscriptionEventHandler):
    """订阅事件日志处理器"""

    async def on_subscribing(self, ctx: SubscribingContext) -> None:
        logging.info("subscribing: %s", ctx)

    async def on_subscribed(self, ctx: SubscribedContext) -> None:
        logging.info("subscribed: %s", ctx)

    async def on_unsubscribed(self, ctx: UnsubscribedContext) -> None:
        logging.info("unsubscribed: %s", ctx)

    async def on_publication(self, ctx: PublicationContext) -> None:
        logging.info("publication: %s", ctx.pub.data)

    async def on_join(self, ctx: JoinContext) -> None:
        logging.info("join: %s", ctx)

    async def on_leave(self, ctx: LeaveContext) -> None:
        logging.info("leave: %s", ctx)

    async def on_error(self, ctx: SubscriptionErrorContext) -> None:
        logging.error("subscription error: %s", ctx)
