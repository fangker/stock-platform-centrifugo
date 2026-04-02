# Centrifugo 使用指南

使用官方 centrifuge-python SDK 实现 WebSocket 实时通信。

## 快速开始

### 1. 安装依赖

```bash
cd /Users/cyan/Desktop/code/stock-platform/centrifugo
pip install -r requirements.txt
```

**主要依赖：**
- `centrifuge-python>=0.12.0` - 官方 SDK
- `aiohttp>=3.9.0` - HTTP 客户端

### 2. 配置

编辑 `config.py`：

```python
CENTRIFUGO_BACKEND_URL = "http://localhost:8888"      # 后端认证服务
CENTRIFUGO_CENTRIFUGO_URL = "http://localhost:8000"   # WebSocket 服务器
CENTRIFUGO_TIMEOUT = 10
```

### 3. 运行示例

```bash
export NO_PROXY=localhost
python demo.py
```

---

## WebSocket 客户端

### 基本使用

```python
from centrifugo_websocket_client import create_websocket_handler
import asyncio

async def main():
    # 创建处理器（无需预先获取 JWT token）
    handler = create_websocket_handler(
        access_key="your_key",
        secret_key="your_secret"
    )

    # 连接（通过 proxy 认证）
    if await handler.connect():
        print("✓ 连接成功")

        # 获取用户 ID
        uid = handler.get_uid()
        print(f"用户 ID: {uid}")

        # 订阅频道
        channel = f"test:{uid}" if uid else "test"
        await handler.subscribe(channel, lambda data: print(f"收到: {data}"))

        # 发送消息
        await handler.publish(channel, {"message": "Hello"})

        # 保持连接
        while handler.is_connected:
            await asyncio.sleep(1)

asyncio.run(main())
```

### API 参考

| 方法 | 说明 |
|------|------|
| `connect()` | 连接到服务器（通过 proxy 认证） |
| `disconnect()` | 断开连接 |
| `subscribe(channel, callback)` | 订阅频道 |
| `publish(channel, data)` | 发布消息 |
| `get_uid()` | 获取当前用户 ID |
| `get_channels()` | 获取可订阅频道列表 |
| `send_buy_signal(code, price, ...)` | 发送买入信号 |
| `send_sell_signal(code, price, ...)` | 发送卖出信号 |

---

## QMT SDK 集成

### 在 QMT 策略中使用

```python
from centrifugo import configure, init

# 配置连接
configure(
    access_key="your_key",
    secret_key="your_secret"
)

def init(C):
    """QMT 策略初始化"""
    import centrifugo
    centrifugo.init(C)
    print("✓ Centrifugo SDK 已启动")
```

### 交易信号格式

**买入信号：**
```python
{
    "action": "BUY",
    "code": "000001.SZ",
    "price": 10.50,
    "pct": 100.0,
    "strategy": "my_strategy"
}
```

**卖出信号：**
```python
{
    "action": "SELL",
    "code": "000001.SZ",
    "price": 11.00,
    "pct": 50.0,
    "strategy": "my_strategy"
}
```

### 工作流程

```
Centrifugo Server (ws://localhost:8000)
    ↓ WebSocket (无 JWT，通过 data 传递凭证)
CentrifugoWebSocketThread (后台线程)
    ↓ Proxy 认证 (/proxy/connect)
    ↓ 返回 token + channels
CentrifugoWebSocketThread (解析 uid)
    ↓ Queue
QMT 定时器 (每秒检查)
    ↓
handle_buy_signal() / handle_sell_signal()
    ↓
QMT passorder() 下单
```

---

## 故障排除

### 认证失败
```
ERROR: 登录失败: access_key and secret_key are required
```
检查 access_key 和 secret_key 是否正确。

### 连接超时
```
ERROR: 连接失败: Cannot connect to host localhost:8888
```
检查后端服务是否运行。

### SOCKS 代理错误
```
ERROR: python-socks is required to use a SOCKS proxy
```
```bash
export NO_PROXY=localhost
```

---

## 测试与开发

### MockContextInfo - 模拟 QMT 环境

在开发或测试时，可以使用 `MockContextInfo` 模拟 QMT 的 ContextInfo 对象：

```python
from centrifugo import configure, MockContextInfo
from datetime import datetime

# 1. 配置连接
configure(
    access_key="1234567",
    secret_key="1234567",
    strategy_name="test_strategy"
)

# 2. 创建 Mock 对象
C = MockContextInfo()
print(f"账户ID: {C.accID}")

# 3. 注册回调函数
def process_messages(context):
    """处理消息的回调函数"""
    print("定时任务执行")

C.register_callback("process_messages", process_messages)

# 4. 启动定时任务
C.run_time("process_messages", "1nSecond", datetime.now(), "SH")

# 5. 模拟下单
order_id = C.order("000001.SZ", 10.50, 100, "buy")
print(f"订单ID: {order_id}")

# 6. 模拟撤单
C.cancel(order_id)

# 7. 停止任务
C.stop_task("process_messages")
C.stop_all_tasks()
```

**MockContextInfo API：**

| 方法 | 说明 |
|------|------|
| `run_time(func_name, interval, start_time, market)` | 注册定时任务 |
| `stop_task(func_name)` | 停止指定的定时任务 |
| `stop_all_tasks()` | 停止所有定时任务 |
| `register_callback(func_name, callback)` | 注册回调函数 |
| `order(symbol, price, amount, direction, **kwargs)` | 模拟下单 |
| `cancel(order_id)` | 模拟撤单 |

**支持的时间间隔格式：**
- `1nSecond` - 1秒
- `5nSecond` - 5秒
- `1nMinute` - 1分钟
- `1nHour` - 1小时

### 语法检查
```bash
python -m py_compile centrifugo_websocket_client.py
python -m py_compile centrifugo/__init__.py
```

### 连接测试
```bash
python demo.py access_key secret_key
```

### QMT 环境测试

在 QMT 中运行测试策略，查看控制台输出：
```
✓ Centrifugo WebSocket 线程已启动
✓ WebSocket 连接成功
✓ 订阅频道: test_123
```

---

## 相关文档

- [TECHNICAL.md](TECHNICAL.md) - 技术细节与协议
- [centrifuge-python GitHub](https://github.com/centrifugal/centrifuge-python)
