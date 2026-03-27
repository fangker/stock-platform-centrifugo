"""
Stock Platform SDK

QMT trading SDK with WebSocket (Centrifugo) integration.
Provides QMT-compatible interfaces using WebSocket instead of Redis Stream.
"""

# Global config
_config = None


def configure(access_key, secret_key, strategy_name, backend_url=None, centrifugo_url=None):
    """
    Configure Centrifugo connection parameters.

    Args:
        access_key: Access key
        secret_key: Secret key
        strategy_name: Strategy name
        backend_url: Backend server URL (optional)
        centrifugo_url: Centrifugo server URL (optional)
    """
    global _config
    from .centrifugo_websocket_client import CentrifugoClientConfig
    _config = CentrifugoClientConfig(
        access_key=access_key,
        secret_key=secret_key,
        strategy_name=strategy_name,
        backend_url=backend_url,
        centrifugo_url=centrifugo_url
    )


def get_config():
    """Get current configuration."""
    return _config


# Export all public interfaces
from .centrifugo_websocket_client import (
    CentrifugoClientConfig,
    create_websocket_handler,
)
from .qmt_state import QMTState
from .qmt_mock import MockContextInfo
from . import constants
from .centrifugo_qmt import (
    init,
    process_centrifugo_messages,
    process_signal,
    handle_buy_signal,
    handle_sell_signal,
    refresh_waiting_dict,
    refresh_bought_list,
    refresh_timeout_orders,
    refresh_order_status,
)


__all__ = [
    # Config
    'configure',
    'get_config',

    # Classes
    'CentrifugoClientConfig',
    'QMTState',
    'MockContextInfo',

    # Core functions
    'init',
    'process_centrifugo_messages',
    'process_signal',
    'handle_buy_signal',
    'handle_sell_signal',
    'refresh_waiting_dict',
    'refresh_bought_list',
    'refresh_timeout_orders',
    'refresh_order_status',

    # Factory
    'create_websocket_handler',

    # Constants module
    'constants',
]
