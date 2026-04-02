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


def __getattr__(name):
    """Lazy import to avoid triggering asyncio import in QMT (Python 3.6 without asyncio)."""
    _ws_names = [
        'CentrifugoClientConfig', 'create_websocket_handler',
    ]
    _qmt_names = [
        'init', 'process_centrifugo_messages', 'process_signal',
        'handle_buy_signal', 'handle_sell_signal',
        'refresh_waiting_dict', 'refresh_bought_list',
        'refresh_timeout_orders', 'refresh_order_status',
    ]
    _other_names = ['QMTState', 'MockContextInfo', 'constants']
    if name in _ws_names:
        from . import centrifugo_websocket_client as _ws
        return getattr(_ws, name)
    if name in _qmt_names:
        from . import centrifugo_qmt as _qmt
        return getattr(_qmt, name)
    if name == 'QMTState':
        from .qmt_state import QMTState
        return QMTState
    if name == 'MockContextInfo':
        from .qmt_mock import MockContextInfo
        return MockContextInfo
    if name == 'constants':
        from . import constants
        return constants
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'configure',
    'get_config',
    'CentrifugoClientConfig',
    'QMTState',
    'MockContextInfo',
    'init',
    'process_centrifugo_messages',
    'process_signal',
    'handle_buy_signal',
    'handle_sell_signal',
    'refresh_waiting_dict',
    'refresh_bought_list',
    'refresh_timeout_orders',
    'refresh_order_status',
    'create_websocket_handler',
    'constants',
]
