# Centrifugo 技术指南

## 📦 目录结构概览

```
centrifugo/
├── 核心模块
│   ├── __init__.py                      # 包入口，导出公共接口
│   ├── centrifugo_websocket_client.py   # WebSocket客户端基础实现
│   ├── centrifugo_qmt.py                # QMT集成核心（兼容层）
│   ├── handlers.py                      # 事件处理器（日志记录）
│   ├── qmt_state.py                     # QMT策略状态管理类
│   ├── qmt_mock.py                      # QMT ContextInfo Mock实现
│   ├── constants.py                     # 常量定义（订单状态、配置等）
│   └── config.py                        # 配置常量
│
├── 测试文件
│   ├── simple_test.py                   # 模拟QMT环境测试
│   ├── test_sdk.py                      # SDK测试
│   ├── test_constants.py                # 常量模块测试
│   ├── test_websocket_client.py         # WebSocket客户端测试
│   ├── test_integration.py              # 集成测试
│   └── example_qmt_strategy.py          # QMT策略示例
│
└── 文档
    ├── TECHNICAL.md                     # 技术指南
    ├── USAGE.md                         # 使用指南
    ├── OPTIMIZATION_ANALYSIS.md         # 代码优化分析报告
    └── config.json.example              # 配置示例
```

---

## 🧩 核心模块详解

### 1. `centrifugo_websocket_client.py` - WebSocket 客户端基础实现

**作用：** 提供基于官方 centrifuge-python SDK 的 WebSocket 通信能力

**核心类：**
- `CentrifugoClientConfig` - 配置类（access_key、secret_key、strategy_name、URLs）
- `CentrifugoWebSocketHandler` - 基础 WebSocket 处理器
- `QMTCentrifugoWebSocketHandler` - QMT 专用处理器（继承自基础处理器）

**核心方法：**

| 方法 | 说明 |
|------|------|
| `connect()` | 连接到 Centrifugo，通过 proxy 认证 |
| `subscribe(channel, callback)` | 订阅频道并设置回调 |
| `publish(channel, data)` | 发布消息到频道 |
| `send_buy_signal()` / `send_sell_signal()` | 发送交易信号 |
| `get_uid()` | 获取当前用户 ID |
| `get_channels()` | 获取可订阅频道列表 |

**认证流程：**
```
Client创建 → 无需JWT → 通过data传递access_key/secret_key
    → Proxy认证(/proxy/connect) → 返回token+channels → 解析uid
```

---

### 2. `centrifugo_qmt.py` - QMT 集成核心（兼容层）

**作用：** 将 WebSocket 消息桥接到 QMT 策略环境，提供与原 qmt.py 兼容的接口

**核心组件：**

| 组件 | 说明 |
|------|------|
| `CentrifugoWebSocketThread` | 后台线程，运行异步 WebSocket |
| `message_queue` | 线程安全的消息队列 |
| `init(C)` | QMT策略初始化入口 |
| `process_centrifugo_messages(C)` | QMT定时器调用的消息处理函数 |
| `handle_buy_signal()` / `handle_sell_signal()` | 交易信号处理 |
| `refresh_*` 系列函数 | 订单状态管理 |

**数据流：**
```
WebSocket消息 → message_queue → QMT定时器(每秒) → process_signal()
    → handle_buy_signal()/handle_sell_signal() → passorder()下单
```

**全局变量：**
- `ws_client` - WebSocket客户端线程
- `message_queue` - 消息队列（queue.Queue）
- `A` - QMTState状态对象（相当于qmt.py的A对象）

---

### 3. `handlers.py` - 事件处理器

**作用：** 提供 Centrifugo SDK 事件的日志记录

**核心类：**
- `ClientEventLoggerHandler` - 客户端事件（连接、断开、错误等）
- `SubscriptionEventLoggerHandler` - 订阅事件（订阅、消息推送等）

---

### 4. `qmt_state.py` - QMT 策略状态管理类

**作用：** 管理策略运行时的所有状态，相当于原 qmt.py 中的 `A` 对象

**状态字段：**

| 字段 | 说明 |
|------|------|
| `pa` | 持仓分析数据 (DataFrame) |
| `waiting_dict` | 委托等待字典 {stock_code: message} |
| `all_order_ref_dict` | 所有委托引用字典 {message: timestamp} |
| `bought_list` | 已买入股票列表 |
| `sold_list` | 已卖出股票列表 |
| `withdraw_secs` | 撤单等待时间（秒） |
| `hsa` | 沪深A股列表 |

---

### 5. `config.py` - 配置常量

**作用：** 定义 Centrifugo 连接的默认配置

```python
CENTRIFUGO_BACKEND_URL = "http://localhost:8888"      # 后端认证服务
CENTRIFUGO_CENTRIFUGO_URL = "http://localhost:8000"   # WebSocket服务器
CENTRIFUGO_TIMEOUT = 10
```

---

### 6. `qmt_mock.py` - QMT ContextInfo Mock 实现

**作用：** 在测试环境中模拟 QMT 的 ContextInfo 对象，支持定时任务、下单、撤单等功能

**核心类：**
- `MockContextInfo` - QMT ContextInfo 的完整 Mock 实现

**核心方法：**

| 方法 | 说明 |
|------|------|
| `run_time(func_name, interval, start_time, market)` | 注册定时任务 |
| `stop_task(func_name)` | 停止指定的定时任务 |
| `stop_all_tasks()` | 停止所有定时任务 |
| `register_callback(func_name, callback)` | 注册定时任务的回调函数 |
| `order(symbol, price, amount, direction, **kwargs)` | 模拟下单 |
| `cancel(order_id)` | 模拟撤单 |

**支持的间隔格式：**
- `1nSecond` - 1秒
- `5nSecond` - 5秒
- `1nMinute` - 1分钟
- `1nHour` - 1小时

**使用示例：**
```python
from centrifugo import MockContextInfo

# 创建 Mock 对象
C = MockContextInfo()

# 注册回调函数
def my_callback(context):
    print("定时任务执行")

C.register_callback("my_task", my_callback)

# 启动定时任务（每秒执行一次）
from datetime import datetime
C.run_time("my_task", "1nSecond", datetime.now(), "SH")

# 停止任务
C.stop_task("my_task")
```

---

### 7. `constants.py` - 常量定义

**作用：** 集中管理所有魔法数字和配置常量，提高代码可维护性

**核心组件：**

| 组件 | 说明 |
|------|------|
| `OrderStatus` | 订单状态枚举（56已成、54已撤、57废单等） |
| `TradeConfig` | 交易配置（价格乘数、交易限制等） |
| `TimeConfig` | 时间配置（交易时间段、日期格式等） |
| `ChannelPrefix` | 频道命名规范 |
| `TradeAction` | 交易信号动作（BUY、SELL） |
| `ErrorMessages` | 标准错误消息 |
| 辅助函数 | `format_order_message`, `validate_volume`, `round_price` |

**使用示例：**
```python
from centrifugo.constants import OrderStatus, TradeConfig, format_order_message

# 使用订单状态枚举
if status == OrderStatus.FILLED:
    print("订单已成")

if OrderStatus.is_terminal(status):
    print("订单已结束")

# 使用交易配置
buy_price = round(original_price * TradeConfig.BUY_PRICE_MULTIPLIER, 2)

# 使用辅助函数
msg = format_order_message("000001.SZ", "buy", 100, 10.50)
# 结果: "20260302154322_000001.SZ_buy_100股@10.50元"

# 验证成交量
if validate_volume(100):
    print("成交量有效")
```

**主要优势：**
- ✅ 消除魔法数字，提高代码可读性
- ✅ 集中管理配置，便于修改
- ✅ 类型安全，使用枚举避免错误
- ✅ 提供辅助函数，简化常用操作

---

### 8. `__init__.py` - 包入口

**作用：** 导出公共接口，简化导入

```python
from centrifugo import configure, init, MockContextInfo, ...
```

**核心函数：**
- `configure()` - 配置连接参数（设置全局 _config）
- `get_config()` - 获取当前配置

**导出的类：**
- `CentrifugoClientConfig` - 客户端配置类
- `QMTState` - QMT 策略状态管理类
- `MockContextInfo` - QMT ContextInfo Mock 类

**导出的模块：**
- `constants` - 常量定义模块

---

## 🔄 完整数据流

```
┌──────────────────────────────────────────────────────────────────┐
│                         QMT 策略环境                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  init(C) 调用 centrifugo.init(C)                           │ │
│  │    ├─ 初始化 A (QMTState)                                  │ │
│  │    ├─ 创建 message_queue                                   │ │
│  │    ├─ 启动 CentrifugoWebSocketThread (后台线程)            │ │
│  │    └─ 注册 QMT 定时器 process_centrifugo_messages (每秒)   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           CentrifugoWebSocketThread (后台线程)              │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ CentrifugoWebSocketHandler.connect()                  │ │ │
│  │  │   ├─ 通过 /proxy/connect 认证                        │ │ │
│  │  │   ├─ 返回 token + channels                           │ │ │
│  │  │   └─ 解析 uid                                        │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ listen_for_signals(callback)                         │ │ │
│  │  │   └─ on_message(data) → message_queue.put(data)      │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  QMT 定时器 (每秒执行一次)                                  │ │
│  │  process_centrifugo_messages(C)                            │ │
│  │    └─ message_queue.get() → process_signal()               │ │
│  │                                  │                         │ │
│  │                ┌─────────────────┴─────────────────┐       │ │
│  │                ▼                                   ▼       │ │
│  │       handle_buy_signal()                  handle_sell_signal()│
│  │                │                                   │       │ │
│  │                └───────────────┬───────────────────┘       │ │
│  │                                ▼                            │ │
│  │                    passorder() 下单                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🧪 测试文件说明

| 文件 | 用途 |
|------|------|
| `simple_test.py` | 模拟 QMT 环境测试，包含 MockContextInfo |
| `test_sdk.py` | SDK 基础功能测试 |
| `test_websocket_client.py` | WebSocket 客户端测试 |
| `test_integration.py` | 集成测试 |
| `example_qmt_strategy.py` | QMT 策略示例代码 |

---

## 💡 关键设计要点

1. **线程模型：** WebSocket 运行在独立后台线程，通过 `queue.Queue` 与 QMT 主线程通信

2. **认证方式：** 使用 proxy 认证，无需预先获取 JWT token，通过 `data` 字段传递 access_key/secret_key

3. **兼容性：** 提供与原 qmt.py 完全兼容的接口，方便迁移

4. **状态管理：** 使用全局 `A` 对象（QMTState）管理策略状态

5. **定时任务：** 通过 QMT 的 `run_time()` 注册定时任务，每秒检查消息队列

---

## 架构设计

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| WebSocket SDK | centrifuge-python | 官方 Python SDK |
| HTTP 客户端 | aiohttp | 异步 HTTP，获取 JWT |
| 异步框架 | asyncio | Python 标准库 |

### 架构图

```
Python 应用
    │
    └─ CentrifugoWebSocketHandler
        ├─ centrifuge.Client (无 JWT)
        ├─ access_key/secret_key via data
        └─ Proxy 认证 (/proxy/connect)
            │
            ▼
┌─────────────────────┐    ┌─────────────────────┐
│   后端 Go 服务        │    │  Centrifugo 服务器   │
│   :8888              │    │  :8000              │
│   /proxy/connect     │    │                     │
│   返回 token+channels │    └─────────────────────┘
└─────────────────────┘
```

---

## 协议细节

### Proxy 认证协议

**连接请求：**
```json
{
  "data": {
    "access_key": "your_key",
    "secret_key": "your_secret"
  }
}
```

**Proxy 响应：**
```json
{
  "result": {
    "user": "1",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "channels": ["test:1"]
    },
    "info": {
      "authenticated": true
    }
  }
}
```

### JWT Token 结构

```json
{
  "header": {"alg": "HS256", "typ": "JWT"},
  "payload": {
    "channels": ["*"],
    "exp": 1772174136,
    "sub": "1"
  }
}
```

### WebSocket 协议

**连接（无 JWT，通过 data 传递凭证）：**
```python
Client(
    "ws://localhost:8000/connection/websocket",
    token=None,
    data={
        "access_key": "your_key",
        "secret_key": "your_secret"
    }
)
```

**订阅：**
```json
{"id": 2, "method": "subscribe", "params": {"channel": "test_1"}}
```

**接收消息（Push）：**
```json
{
  "push": {
    "channel": "test_1",
    "pub": {"data": {"action": "BUY", "code": "000001.SZ"}}
  }
}
```

---

## 事件处理

### 客户端事件

```python
from centrifuge.handlers import ClientEventHandler

class EventHandler(ClientEventHandler):
    async def on_connected(self, ctx):
        # 从 proxy 返回的 data 中提取用户 ID
        uid = None
        if ctx.data and isinstance(ctx.data, dict):
            # 方法 1: 从 JWT token 解析
            token = ctx.data.get('token')
            if token:
                import base64, json
                payload_b64 = token.split('.')[1]
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64))
                uid = payload.get('sub')

            # 方法 2: 从 channels 解析 (如 ["test:1"])
            if not uid:
                channels = ctx.data.get('channels', [])
                if channels:
                    channel = channels[0]
                    if ':' in channel:
                        uid = channel.split(':')[-1]

        print(f"✓ 连接成功, UID: {uid}")

    async def on_disconnected(self, ctx):
        print("连接断开")

    async def on_error(self, ctx):
        print(f"错误: {ctx.error}")
```

### 订阅事件

```python
from centrifuge.handlers import SubscriptionEventHandler

class SubEventHandler(SubscriptionEventHandler):
    async def on_subscribed(self, ctx):
        print("✓ 订阅成功")

    async def on_publication(self, ctx):
        print(f"消息: {ctx.pub.data}")

    async def on_error(self, ctx):
        print(f"订阅错误: {ctx.error}")
```

---

## 频道命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 用户专属 | `test:{uid}` | `test:1` |
| 公共频道 | `test` | `test` |
| 信号频道 | `signals:{uid}` | `signals:1` |

---

## 错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 0 | 成功 | - |
| 100 | Token 过期 | 重新登录 |
| 103 | 权限拒绝 | 检查 Centrifugo 配置 |
| 109 | 频道不存在 | 检查频道名称 |

---

## 性能优化

### 连接复用

```python
class ConnectionPool:
    def __init__(self, size=5):
        self.pool = asyncio.Queue(maxsize=size)

    async def get(self):
        return await self.pool.get()

    async def put(self, handler):
        await self.pool.put(handler)
```

### 批量消息

```python
async def publish_batch(handler, messages):
    for msg in messages:
        await handler.publish("test_1", msg)
        await asyncio.sleep(0.01)
```

---

## 安全考虑

### Token 安全

- 不要在日志中打印完整 Token
- Token 过期后立即清除
- 使用环境变量存储密钥

### 连接安全

```python
# 使用 WSS（加密连接）
CENTRIFUGO_CENTRIFUGO_URL = "https://localhost:8000"
```

### 输入验证

```python
import re

def validate_channel(channel):
    if not re.match(r'^[a-zA-Z0-9:_-]+$', channel):
        raise ValueError("无效频道名")
    return channel
```

---

## 监控调试

### 启用调试日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('centrifuge').setLevel(logging.DEBUG)
```

### 连接监控

```python
class ConnectionMonitor:
    async def on_connected(self, ctx):
        self.start_time = time.time()
        print(f"✓ 连接建立: {self.start_time}")

    async def on_disconnected(self, ctx):
        duration = time.time() - self.start_time
        print(f"✗ 断开，持续: {duration:.2f}秒")
```

---

## 变更历史

- **2026-02-02**: Proxy 认证架构升级
  - 移除独立的 `/qmt/login` HTTP 认证端点
  - 客户端通过 `/proxy/connect` 统一认证
  - 无需预先获取 JWT token，由 proxy 处理
  - 客户端从 proxy 响应的 data 中提取 user ID
    - 支持从 JWT token 的 `sub` 字段解析
    - 支持从 channels 数组解析（如 `["test:1"]`）
  - API 调用从 `auth_client.get_uid()` 改为 `get_uid()`

- **2026-01-30**: 使用官方 centrifuge-python SDK 重写
  - 移除自定义 WebSocket 实现
  - 统一事件处理模式

---

## 相关资源

- [USAGE.md](USAGE.md) - 使用指南
- [centrifuge-python GitHub](https://github.com/centrifugal/centrifuge-python)
- [Centrifugo 官方文档](https://centrifugal.dev/)
