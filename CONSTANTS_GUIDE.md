# Centrifugo 常量模块使用指南

## 概述

`constants.py` 模块集中管理了所有 QMT SDK 相关的常量，包括订单状态、交易配置、时间格式等。

---

## 快速开始

### 1. 导入常量

```python
# 方式1：从 centrifugo 包导入
from centrifugo.constants import OrderStatus, TradeConfig, format_order_message

# 方式2：从子模块导入
from centrifugo import constants
status = constants.OrderStatus.FILLED
```

### 2. 使用订单状态枚举

```python
from centrifugo.constants import OrderStatus

# 直接使用枚举值
if order.m_nOrderStatus == OrderStatus.FILLED:
    print("订单已成")

# 使用枚举方法判断
if OrderStatus.is_terminal(order.m_nOrderStatus):
    print("订单已结束，无需等待")

if OrderStatus.is_removable(order.m_nOrderStatus):
    print("可以从等待列表中移除")

if OrderStatus.is_cancellable(order.m_nOrderStatus):
    print("可以撤单")
```

### 3. 使用交易配置

```python
from centrifugo.constants import TradeConfig, round_price

# 计算买入价格（+1.2%）
buy_price = round_price(original_price * TradeConfig.BUY_PRICE_MULTIPLIER)

# 计算卖出价格（-1.2%）
sell_price = round_price(original_price * TradeConfig.SELL_PRICE_MULTIPLIER)

# 检查交易金额
if amount * price > TradeConfig.MAX_AMOUNT_PER_ORDER:
    print(f"超过单笔最大金额 {TradeConfig.MAX_AMOUNT_PER_ORDER}")

# 验证成交量
if volume >= TradeConfig.MIN_VOLUME and volume % 100 == 0:
    print("成交量符合要求")
```

### 4. 生成订单消息

```python
from centrifugo.constants import format_order_message

# 生成标准订单消息
msg = format_order_message("000001.SZ", "buy", 100, 10.50)
# 结果: "20260302154322_000001.SZ_buy_100股@10.50元"

passorder(23, 1101, accID, "000001.SZ", 11, 10.50, 100, strategy, 2, msg, C)
```

### 5. 频道命名

```python
from centrifugo.constants import ChannelPrefix

# 生成测试频道
test_channel = ChannelPrefix.make_test_channel("my_strategy")
# 结果: "test:my_strategy"

# 生成交易频道
trade_channel = ChannelPrefix.make_trade_channel("my_strategy")
# 结果: "trade:my_strategy"
```

### 6. 验证交易信号

```python
from centrifugo.constants import TradeAction

action = message_content.get('action')

if not TradeAction.is_valid(action):
    print(f"未知的交易信号类型: {action}")
    return

if action == TradeAction.BUY:
    handle_buy_signal(message_content, C)
elif action == TradeAction.SELL:
    handle_sell_signal(message_content, C)
```

---

## 完整示例

### 重构前（使用魔法数字）

```python
# centrifugo_qmt.py (旧代码)
def handle_buy_signal(message_content, C):
    # 魔法数字：56, 53, 54
    if status in [56, 53, 54]:
        print('已完成')

    # 魔法数字：1.012
    buy_price = round(price1 * 1.012, 2)

    # 魔法数字：50000
    max_amount = 50000

    # 魔法字符串格式
    msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_buy_{volume}股"
```

### 重构后（使用常量）

```python
# centrifugo_qmt.py (新代码)
from centrifugo.constants import (
    OrderStatus, TradeConfig, TimeConfig,
    format_order_message, TradeAction
)

def handle_buy_signal(message_content, C):
    # 使用枚举
    if OrderStatus.is_removable(status):
        print('已完成')

    # 使用常量
    buy_price = round_price(
        price1 * TradeConfig.BUY_PRICE_MULTIPLIER
    )

    # 使用常量
    max_amount = TradeConfig.MAX_AMOUNT_PER_ORDER

    # 使用辅助函数
    msg = format_order_message(stock_code, "buy", volume, buy_price)
```

---

## 迁移指南

### 步骤 1：导入常量

在文件顶部添加导入：

```python
# centrifugo_qmt.py
from centrifugo.constants import (
    OrderStatus,
    TradeConfig,
    TimeConfig,
    ChannelPrefix,
    TradeAction,
    ErrorMessages,
    format_order_message,
    validate_volume,
    round_price,
)
```

### 步骤 2：替换订单状态

```python
# 替换前
if status == 56:
    print("已成")

# 替换后
if status == OrderStatus.FILLED:
    print("已成")

# 或者使用方法
if OrderStatus.is_terminal(status):
    print("订单已结束")
```

### 步骤 3：替换价格乘数

```python
# 替换前
buy_price = round(price1 * 1.012, 2)
sell_price = round(price1 * 0.988, 2)

# 替换后
buy_price = round_price(price1, TradeConfig.BUY_PRICE_MULTIPLIER)
sell_price = round_price(price1, TradeConfig.SELL_PRICE_MULTIPLIER)
```

### 步骤 4：替换错误消息

```python
# 替换前
if not stock_code:
    print("消息中缺少股票代码")
    return

# 替换后
if not stock_code:
    print(ErrorMessages.MISSING_STOCK_CODE)
    return
```

---

## API 参考

### OrderStatus 枚举

| 状态码 | 枚举名称 | 说明 |
|--------|----------|------|
| 48 | SUBMITTING | 已报 |
| 49 | PARTIAL_FILLED | 部成 |
| 50 | ACCEPTED | 已受理 |
| 53 | PARTIAL_CANCELLED | 部撤 |
| 54 | CANCELLED | 已撤 |
| 56 | FILLED | 已成 |
| 57 | INVALID | 废单 |

**方法：**
- `is_terminal(status)` - 判断是否为终态
- `is_removable(status)` - 判断是否可从等待列表移除
- `is_cancellable(status)` - 判断是否可撤单

### TradeConfig 配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| BUY_PRICE_MULTIPLIER | 1.012 | 买入价格乘数 |
| SELL_PRICE_MULTIPLIER | 0.988 | 卖出价格乘数 |
| MAX_AMOUNT_PER_ORDER | 50000.0 | 单笔最大金额 |
| MIN_VOLUME | 100 | 最小成交量 |

### 辅助函数

#### format_order_message()

生成标准订单消息字符串。

```python
format_order_message(stock_code, action, volume, price) -> str
```

#### validate_volume()

验证成交量是否有效。

```python
validate_volume(volume: int) -> bool
```

**规则：**
- 必须 >= 100 股
- 必须是 100 的整数倍

#### round_price()

按乘数调整价格并保留两位小数。

```python
round_price(price: float, multiplier: float = 1.0) -> float
```

---

## 测试

运行常量模块测试：

```bash
python /Users/cyan/Desktop/code/stock-platform/centrifugo/test_constants.py
```

预期输出：

```
============================================================
常量模块测试
============================================================

[测试 1] OrderStatus 枚举
✓ 枚举值正确: FILLED=56, CANCELLED=54, INVALID=57
✓ 终态判断正确
✓ 可移除判断正确
✓ 可撤单判断正确

...

============================================================
✅ 所有测试通过！
============================================================
```

---

## 最佳实践

1. **始终使用枚举而非魔法数字**
   ```python
   # ✓ 好
   if status == OrderStatus.FILLED:

   # ✗ 差
   if status == 56:
   ```

2. **使用辅助函数而非重复代码**
   ```python
   # ✓ 好
   msg = format_order_message(code, "buy", 100, 10.50)

   # ✗ 差
   msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{code}_buy_100股"
   ```

3. **使用常量配置而非硬编码**
   ```python
   # ✓ 好
   if amount > TradeConfig.MAX_AMOUNT_PER_ORDER:

   # ✗ 差
   if amount > 50000:
   ```

4. **利用枚举方法简化判断**
   ```python
   # ✓ 好
   if OrderStatus.is_terminal(status):

   # ✗ 差
   if status in [56, 53, 54, 57]:
   ```

---

## 常见问题

### Q: 为什么使用枚举而非常量？

A: 枚举提供类型安全、IDE 自动补全、更好的错误提示，并且可以包含方法。

### Q: 如何添加新的订单状态？

A: 在 `OrderStatus` 枚举类中添加新状态，并更新相应的判断方法。

### Q: 辅助函数可以自定义吗？

A: 可以，但建议先使用 `constants.py` 提供的辅助函数，确保一致性。

---

## 相关文档

- [TECHNICAL.md](TECHNICAL.md) - 技术指南
- [USAGE.md](USAGE.md) - 使用指南
- [OPTIMIZATION_ANALYSIS.md](OPTIMIZATION_ANALYSIS.md) - 优化分析
