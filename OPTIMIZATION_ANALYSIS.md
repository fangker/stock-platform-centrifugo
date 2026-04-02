# Centrifugo 代码优化分析报告

生成时间: 2026-03-02
分析范围: `/Users/cyan/Desktop/code/stock-platform/centrifugo`

---

## 📊 总体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码组织 | ⭐⭐⭐⭐ | 模块划分清晰，职责明确 |
| 可维护性 | ⭐⭐⭐ | 存在全局变量和重复代码 |
| 性能 | ⭐⭐⭐ | 基本合理，有优化空间 |
| 类型安全 | ⭐⭐ | 缺少类型提示 |
| 错误处理 | ⭐⭐ | 异常处理不够完善 |
| 测试覆盖 | ⭐⭐⭐ | 有基础测试，可增强 |

---

## 🔴 严重问题

### 1. 过度使用全局变量

**位置：** `centrifugo_qmt.py`

**问题：**
```python
# 全局变量
ws_client = None
message_queue = queue.Queue()
A = None

# 在多个函数中使用
def init(C):
    global ws_client, A, message_queue
    # ...

def handle_buy_signal(message_content, C):
    global A
    # ...
```

**影响：**
- 状态管理混乱，难以追踪
- 多线程环境下可能出现竞态条件
- 难以进行单元测试
- 无法支持多策略实例

**建议：**
```python
# 使用单例类或依赖注入
class CentrifugoQMTManager:
    def __init__(self):
        self.ws_client = None
        self.message_queue = queue.Queue()
        self.state = QMTState()

    def init(self, C):
        # 使用实例变量
        self.state = QMTState()
        # ...

# 全局单例
_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = CentrifugoQMTManager()
    return _manager
```

---

### 2. 魔法数字（Magic Numbers）

**位置：** `centrifugo_qmt.py`

**问题：**
```python
# 订单状态码
if status in [56, 53, 54]:  # 56已成 53部撤 54已撤
elif status == 57:  # 废单

# 价格调整
buy_price = round(buy_price1 * 1.012, 2)  # 硬编码 1.012
sell_price = round(sell_price1 * 0.988, 2)  # 硬编码 0.988

# 时间段
if '091500' <= now_timestr <= '093000':  # 硬编码时间

# 最大金额
max_allowed_amount = 50000  # 硬编码
```

**建议：**
```python
# 在 qmt_state.py 或新建 constants.py 中定义
from enum import IntEnum

class OrderStatus(IntEnum):
    """QMT 订单状态枚举"""
    FILLED = 56        # 已成
    PARTIAL_CANCELLED = 53  # 部撤
    CANCELLED = 54     # 已撤
    REJECTED = 57      # 废单
    SUBMITTING = 48    # 已报
    UNKNOWN = 255      # 未知

class TradeConfig:
    """交易配置常量"""
    BUY_PRICE_MULTIPLIER = 1.012    # 买入价格乘数（+1.2%）
    SELL_PRICE_MULTIPLIER = 0.988   # 卖出价格乘数（-1.2%）
    MAX_AMOUNT_PER_ORDER = 50000    # 单笔最大金额
    MORNING_BUFFER_START = "091500"  # 早晨缓冲开始时间
    MORNING_BUFFER_END = "093000"    # 早晨缓冲结束时间
    DEFAULT_WITHDRAW_SECS = 10       # 默认撤单等待秒数

# 使用
if status in [OrderStatus.FILLED, OrderStatus.PARTIAL_CANCELLED, OrderStatus.CANCELLED]:
    # ...

buy_price = round(buy_price1 * TradeConfig.BUY_PRICE_MULTIPLIER, 2)
```

---

### 3. 重复的订单状态查询

**位置：** `centrifugo_qmt.py:454-487`

**问题：**
```python
def refresh_bought_list(C):
    # 查询订单一次
    detailed_orders = get_trade_detail_data(C.accID, 'stock', 'order')
    order_status_dict = {order.m_strRemark: order.m_nOrderStatus for order in detailed_orders}

    for stock_code in A.bought_list:
        # 对每个股票代码，遍历所有订单
        for order in detailed_orders:
            # O(n*m) 复杂度
            full_instrument_id = f'{order.m_strInstrumentID}.{order.m_strExchangeID}'
            if full_instrument_id == stock_code and order.m_strOptName == '限价买入':
                # ...
                break
```

**影响：** 当股票和订单数量增加时，性能下降明显

**建议：**
```python
def refresh_bought_list(C):
    """优化版本：预先建立股票代码到订单的映射"""
    global A

    try:
        detailed_orders = get_trade_detail_data(C.accID, 'stock', 'order')

        # 预先建立股票代码 -> 订单列表的映射
        stock_orders = {}
        for order in detailed_orders:
            full_instrument_id = f'{order.m_strInstrumentID}.{order.m_strExchangeID}'
            if full_instrument_id not in stock_orders:
                stock_orders[full_instrument_id] = []
            stock_orders[full_instrument_id].append(order)

        # 直接查找，O(n) 复杂度
        stocks_to_remove = []
        for stock_code in A.bought_list:
            if stock_code not in stock_orders:
                continue

            for order in stock_orders[stock_code]:
                if order.m_strOptName == '限价买入':
                    status = order.m_nOrderStatus
                    if status in [OrderStatus.PARTIAL_CANCELLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                        print(f'✓ 投资备注为 {order.m_strRemark} 的委托状态为 {status}，准备从买入列表中移除')
                        stocks_to_remove.append(stock_code)
                    break

        for stock_code in stocks_to_remove:
            A.bought_list.remove(stock_code)

        print("移除部撤、已撤或废单的买入列表:", A.bought_list)

    except Exception as e:
        print(f"❌ refresh_bought_list 异常: {e}")
```

---

## 🟡 中等问题

### 4. 缺少类型提示

**问题：** 大部分函数缺少类型注解

**示例：**
```python
# 当前代码
def handle_buy_signal(message_content, C):
    """处理买入信号"""
    # ...

def refresh_waiting_dict(C):
    """更新委托状态"""
    # ...
```

**建议：**
```python
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class TradeSignal:
    """交易信号数据类"""
    action: str  # "BUY" or "SELL"
    code: str
    price: float
    pct: float
    strategy: str
    time: str

def handle_buy_signal(message_content: Dict[str, Any], C: Any) -> None:
    """
    处理买入信号

    Args:
        message_content: 消息内容字典
        C: QMT ContextInfo 对象
    """
    # ...

def refresh_waiting_dict(C: Any) -> None:
    """
    更新委托状态，入参为 ContextInfo 对象

    Args:
        C: QMT ContextInfo 对象
    """
    # ...

def get_trade_detail_data(accID: str, market: str, data_type: str) -> List[Any]:
    """
    获取交易明细数据

    Args:
        accID: 账户ID
        market: 市场类型
        data_type: 数据类型 ('order', 'position', 'account')

    Returns:
        数据对象列表
    """
    # ...
```

---

### 5. 日志系统混乱

**问题：** 混用 `print()` 和 `logging`，没有统一的日志策略

**示例：**
```python
# 有的地方用 print
print(f"✅ 买入 {stock_code} {buy_volume} 股 @ {buy_price}")
print(f"❌ 获取持仓信息失败: {e}")

# 有的地方用 logging
logger.info("✓ WebSocket 连接成功")
logger.error("连接失败: {e}")
```

**建议：**
```python
# 创建统一的日志模块 logger.py
import logging
from typing import Optional

# 定义日志格式
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

class QMTLogger:
    """QMT 统一日志管理器"""

    def __init__(self, name: str = 'centrifugo', level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
            self.logger.addHandler(console_handler)
            self.logger.setLevel(level)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def success(self, msg: str, *args, **kwargs):
        """成功消息（使用 ✅ 标记）"""
        self.logger.info(f"✅ {msg}", *args, **kwargs)

    def trade(self, action: str, code: str, volume: int, price: float, **kwargs):
        """交易消息格式化"""
        self.logger.info(f"📊 {action} {code} {volume}股 @ {price}元", **kwargs)

# 全局实例
logger = QMTLogger()

# 使用
from centrifugo.logger import logger

# 替换所有 print
logger.trade("买入", stock_code, buy_volume, buy_price)
logger.error(f"获取持仓信息失败: {e}")
logger.success(f"WebSocket 连接成功")
```

---

### 6. 买入/卖出信号处理重复代码

**位置：** `centrifugo_qmt.py:256-414`

**问题：** `handle_buy_signal` 和 `handle_sell_signal` 有大量重复逻辑

**重复部分：**
1. 股票代码验证
2. 日期判断逻辑
3. 非交易日处理
4. 订单消息格式

**建议：**
```python
def _validate_signal_message(message_content: Dict[str, Any]) -> Optional[str]:
    """
    验证信号消息

    Args:
        message_content: 消息内容

    Returns:
        股票代码，如果验证失败返回 None
    """
    stock_code = message_content.get('code')
    if not stock_code:
        print("消息中缺少股票代码")
        return None
    return stock_code

def _is_trading_day(message_time_str: str) -> bool:
    """
    判断是否为交易日

    Args:
        message_time_str: 消息时间字符串

    Returns:
        是否为交易日
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return message_time_str[:10] == today

def _generate_order_message(stock_code: str, action: str, volume: int, price: float) -> str:
    """
    生成订单消息

    Args:
        stock_code: 股票代码
        action: 操作类型
        volume: 数量
        price: 价格

    Returns:
        订单消息字符串
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{timestamp}_{stock_code}_{action}_{volume}股"

def handle_buy_signal(message_content: Dict[str, Any], C):
    """处理买入信号（重构后）"""
    global A

    # 通用验证
    stock_code = _validate_signal_message(message_content)
    if not stock_code:
        return

    # 刷新状态
    refresh_waiting_dict(C)
    refresh_bought_list(C)
    refresh_timeout_orders(C)

    # 获取账户信息
    try:
        acct_info = get_trade_detail_data(C.accID, 'stock', 'account')
        cash = acct_info[0].m_dAvailable
    except Exception as e:
        logger.error(f"获取账户信息失败: {e}")
        return

    # 买入逻辑
    if cash > 0 and stock_code not in A.bought_list:
        pct = float(message_content.get('pct', 100))
        strategy = message_content.get('strategy', 'centrifugo')

        buy_price1 = float(message_content.get('price', 0))
        buy_price = round(buy_price1 * TradeConfig.BUY_PRICE_MULTIPLIER, 2)

        if buy_price > 0:
            message_time_str = message_content.get('time', '')

            if _is_trading_day(message_time_str):
                max_shares = cash / buy_price
                max_buy_volume = TradeConfig.MAX_AMOUNT_PER_ORDER / buy_price
                buy_volume = max(
                    100,
                    min(
                        int(pct * max_shares // 100) * 100,
                        int(max_buy_volume // 100) * 100
                    )
                )

                msg = _generate_order_message(stock_code, "buy", buy_volume, buy_price)

                passorder(
                    23, 1101, C.accID, stock_code, 11,
                    float(buy_price), int(buy_volume), strategy, 2, msg, C
                )

                A.waiting_list.append(msg)
                A.bought_list.append(stock_code)
                A.waiting_dict[stock_code] = msg
                A.all_order_ref_dict[msg] = time.time()

                logger.trade("买入", stock_code, buy_volume, buy_price)
            else:
                # 非交易日
                msg = _generate_order_message(stock_code, "buy", 0, buy_price)
                passorder(23, 1101, C.accID, stock_code, 11, float(buy_price), 0, strategy, 2, msg, C)
                A.waiting_list.append(msg)
                A.waiting_dict[stock_code] = msg
                A.all_order_ref_dict[msg] = time.time()
                logger.warning(f"买入 {stock_code} 0股 (非交易日)")
        else:
            logger.error(f"无法获取股票 {stock_code} 的买入价格")
    else:
        logger.warning(f"没有足够的现金或已买入股票 {stock_code}")
```

---

## 🟢 轻微问题

### 7. 字符串格式化不统一

**问题：** 混用多种字符串格式化方式

```python
# f-string
print(f"✓ 连接成功, UID: {uid}")

# format
print("移除部撤、已撤或废单的买入列表: {}".format(A.bought_list))

# % 格式化
print("定时任务执行")
```

**建议：** 统一使用 f-string（Python 3.6+）

```python
# 统一使用 f-string
print(f"移除部撤、已撤或废单的买入列表: {A.bought_list}")
```

---

### 8. 日期格式化重复

**问题：** 多处重复格式化当前日期

```python
# 在多个函数中重复
today = datetime.now().strftime("%Y-%m-%d")
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
```

**建议：** 创建工具函数

```python
# utils.py
from datetime import datetime

def get_today() -> str:
    """获取今天的日期字符串"""
    return datetime.now().strftime("%Y-%m-%d")

def get_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime('%Y%m%d%H%M%S')

def get_time_str() -> str:
    """获取当前时间字符串"""
    return datetime.now().strftime("%H%M%S")

# 使用
from centrifugo.utils import get_today, get_timestamp

today = get_today()
timestamp = get_timestamp()
```

---

### 9. 缺少输入验证

**问题：** 对外部输入缺少验证

```python
# 没有验证 price 是否为有效数字
buy_price1 = float(message_content.get('price', 0))

# 没有验证 pct 范围
pct = float(message_content.get('pct', 100))
```

**建议：**
```python
def validate_price(price: Any) -> Optional[float]:
    """验证价格"""
    try:
        p = float(price)
        return p if p > 0 else None
    except (ValueError, TypeError):
        return None

def validate_percentage(pct: Any) -> float:
    """验证百分比"""
    try:
        p = float(pct)
        return max(0, min(100, p))  # 限制在 0-100
    except (ValueError, TypeError):
        return 100.0  # 默认 100%

# 使用
buy_price1 = validate_price(message_content.get('price', 0))
if not buy_price1:
    logger.error(f"无效的买入价格: {message_content.get('price')}")
    return

pct = validate_percentage(message_content.get('pct', 100))
```

---

### 10. MockContextInfo 可以增强

**位置：** `qmt_mock.py`

**建议增强：**
```python
class MockContextInfo:
    """增强版 MockContextInfo"""

    def __init__(self):
        self.account_id = "test_account"
        self.accID = "test_account"
        self._scheduled_tasks = {}
        self._task_callbacks = {}
        self._orders = {}  # 新增：模拟订单存储
        self._positions = {}  # 新增：模拟持仓
        self._cash = 1000000.0  # 新增：模拟现金

    def order(self, symbol, price, amount, direction, **kwargs):
        """下单 - 增强版"""
        order_id = f"ORDER_{int(datetime.now().timestamp())}"
        self._orders[order_id] = {
            'symbol': symbol,
            'price': price,
            'amount': amount,
            'direction': direction,
            'status': 'submitted',
            'timestamp': datetime.now()
        }

        # 更新持仓和现金
        if direction == 'buy':
            self._cash -= price * amount
            self._positions[symbol] = self._positions.get(symbol, 0) + amount
        elif direction == 'sell':
            self._cash += price * amount
            self._positions[symbol] = self._positions.get(symbol, 0) - amount

        print(f"[QMT] 下单: {direction} {symbol} {price}元 x {amount}股 -> {order_id}")
        return order_id

    def cancel(self, order_id):
        """撤单 - 增强版"""
        if order_id in self._orders:
            self._orders[order_id]['status'] = 'cancelled'
            print(f"[QMT] 撤单: {order_id}")
            return True
        print(f"[QMT] 撤单失败: 订单不存在 {order_id}")
        return False

    # 新增方法
    def get_cash(self):
        """获取当前现金"""
        return self._cash

    def get_position(self, symbol):
        """获取持仓"""
        return self._positions.get(symbol, 0)

    def get_order_status(self, order_id):
        """获取订单状态"""
        order = self._orders.get(order_id)
        return order['status'] if order else None
```

---

## 🎯 优先级建议

| 优先级 | 问题 | 影响范围 | 预计工作量 |
|--------|------|----------|-----------|
| 🔴 P0 | 全局变量问题 | 整体架构 | 2-3天 |
| 🔴 P0 | 魔法数字 | 可维护性 | 0.5天 |
| 🟡 P1 | 重复代码优化 | 可维护性 | 1天 |
| 🟡 P1 | 类型提示添加 | 类型安全 | 1天 |
| 🟡 P1 | 统一日志系统 | 可调试性 | 0.5天 |
| 🟢 P2 | 性能优化 | 性能 | 0.5天 |
| 🟢 P2 | 输入验证 | 健壮性 | 0.5天 |

---

## 📋 实施路线图

### 阶段 1：基础设施（1-2天）
1. 创建 `constants.py` - 定义所有常量
2. 创建 `logger.py` - 统一日志系统
3. 创建 `utils.py` - 工具函数

### 阶段 2：重构核心（2-3天）
4. 重构 `centrifugo_qmt.py` - 消除全局变量
5. 添加类型提示
6. 提取重复代码

### 阶段 3：优化完善（1天）
7. 性能优化
8. 输入验证
9. 增强 Mock

### 阶段 4：测试验证（1天）
10. 单元测试
11. 集成测试
12. 文档更新

---

## 📚 参考资源

- [Python 类型提示](https://docs.python.org/3/library/typing.html)
- [Python 日志最佳实践](https://docs.python.org/3/howto/logging.html)
- [Clean Code 原则](https://github.com/ryanmcdermott/clean-code-python)
