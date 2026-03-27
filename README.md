# Stock Platform SDK

QMT trading SDK with WebSocket (Centrifugo) integration.

## Installation

```bash
pip install stock-platform-sdk
```

QMT 环境指定安装路径：

```bash
pip install stock-platform-sdk -t E:\xt\bin.x64\Lib\site-packages
```

## Usage

```python
from stock_platform_sdk import configure, init

# Step 1: Configure connection
configure(
    access_key="your_access_key",
    secret_key="your_secret_key",
    strategy_name="my_strategy",
    backend_url="http://localhost:8888",      # optional
    centrifugo_url="http://localhost:8000"    # optional
)

# Step 2: Initialize in QMT strategy
def init(C):
    from stock_platform_sdk import init as sdk_init
    sdk_init(C)
```

## API

- `configure(access_key, secret_key, strategy_name, ...)` - Set connection parameters
- `init(C)` - Initialize SDK with QMT ContextInfo
- `get_config()` - Get current configuration
- `create_websocket_handler(access_key, secret_key, strategy_name)` - Create WebSocket handler

## Constants

```python
from stock_platform_sdk import constants

constants.OrderStatus.FILLED          # 56
constants.TradeConfig.BUY_PRICE_MULTIPLIER  # 1.012
constants.ChannelPrefix.make_trade_channel("my_strategy")  # "trade:my_strategy"
```
