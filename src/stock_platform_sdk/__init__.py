"""
Stock Platform SDK

QMT 交易信号 SDK，通过 HTTP API 查询 Redis Stream 中的交易信号。
"""
import logging
import os
from logging.handlers import RotatingFileHandler

_config = None
_cached = {}
_logger = None


def configure(access_key, secret_key, strategy_name, backend_url=None, log_dir=None):
    """
    配置连接参数。

    Args:
        access_key: 访问密钥
        secret_key: 密钥
        strategy_name: 策略名称
        backend_url: 后端服务器 URL（可选）
        log_dir: 日志文件目录（可选，默认 ./logs）
    """
    global _config, _logger
    from .config import SDKConfig
    _config = SDKConfig(
        access_key=access_key,
        secret_key=secret_key,
        strategy_name=strategy_name,
        backend_url=backend_url,
    )

    # 初始化日志：同时输出到控制台和文件
    _logger = logging.getLogger("stock_platform_sdk")
    _logger.setLevel(logging.DEBUG)
    _logger.handlers.clear()

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(fmt)
    _logger.addHandler(sh)

    # 文件（按天轮转，保留30天）
    log_dir = log_dir or os.path.join(".", "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.handlers.TimedRotatingFileHandler(
        os.path.join(log_dir, f"sdk_{strategy_name}.log"),
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    _logger.addHandler(fh)


def get_logger():
    """获取 SDK 日志记录器。"""
    return _logger


def get_config():
    """获取当前配置。"""
    return _config


# 直接导出，兼容 Python 3.6（3.6 不支持模块级 __getattr__）
from .signal_client import SignalClient
from .qmt_trading import (
    init, process_signal_messages, process_signal,
    handle_buy_signal, handle_sell_signal,
    refresh_waiting_dict, refresh_bought_list,
    refresh_timeout_orders, refresh_order_status,
)
from .mock_context import MockQMTContext
from .qmt_state import QMTState
from . import constants
from .constants import TimeConfig, QMTApi, TradeAction, TradeConfig, OrderStatus
from .constants import format_order_message, validate_volume, round_price


__all__ = [
    'configure',
    'get_config',
    'get_logger',
    'SignalClient',
    'QMTState',
    'MockQMTContext',
    'init',
    'process_signal_messages',
    'process_signal',
    'handle_buy_signal',
    'handle_sell_signal',
    'refresh_waiting_dict',
    'refresh_bought_list',
    'refresh_timeout_orders',
    'refresh_order_status',
    'constants',
    'TimeConfig',
    'QMTApi',
    'TradeAction',
    'TradeConfig',
    'OrderStatus',
    'format_order_message',
    'validate_volume',
    'round_price',
]
