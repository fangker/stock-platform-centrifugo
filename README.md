# Stock Platform SDK

QMT 交易信号 SDK，通过 HTTP API 查询 Redis Stream 中的交易信号。

## 安装

```bash
pip install stock-platform-sdk
```

## 卸载
```PowerShell
Remove-Item -Recurse -Force C:\xt\bin.x64\Lib\site-packages\stock_platform_sdk
```  
QMT 环境（指定安装路径）：

```bash
  py -m pip install stock-platform-sdk -t C:\xt\bin.x64\Lib\site-packages
```

## 生产环境使用

```python
from stock_platform_sdk import configure, init

configure(
    access_key="your_access_key",
    secret_key="your_secret_key",
    strategy_name="your_strategy",
    backend_url="https://your-server.com",
)

# 在 QMT 策略的 init(C) 中调用
init(C)
```

`init(C)` 会：
1. 初始化策略状态（买入列表、卖出列表、等待字典等）
2. 通过 HTTP API 登录后端
3. 注册 QMT 定时任务，每秒查询一次新信号

## 本地测试（MockQMTContext）

使用 `MockQMTContext` 可以在不连接 QMT 和后端服务的情况下，完整测试交易逻辑。

### 基本用法

```python
from stock_platform_sdk import configure, MockQMTContext
from stock_platform_sdk.qmt_trading import init, process_signal
from stock_platform_sdk.constants import TradeAction

# 1. 配置 SDK（backend_url 可以随便填，mock 不走网络）
configure(access_key="test", secret_key="test", strategy_name="test")

# 2. 创建 mock 环境
mock = MockQMTContext(
    account_id="mock_001",
    cash=100000.0,
    positions={"600036.SH": 500, "000001.SZ": 1000},
    stock_list=["000001.SZ", "600036.SH"],
)

# 3. install + init
mock.install()
init(mock)

# 4. 模拟信号
signal = {
    "action": TradeAction.BUY,
    "code": "600036.SH",
    "price": 35.50,
    "pct": 50.0,
    "strategy": "test",
    "time": "2026-04-10 10:30:00",
}
process_signal(signal, mock)

# 5. 验证结果
assert len(mock.passorder_calls) == 1
assert mock.cash < 100000.0  # 资金已扣减
assert mock.positions["600036.SH"] > 500  # 持仓已增加

# 6. 清理
mock.uninstall()
```

### 上下文管理器（推荐）

```python
with MockQMTContext(cash=100000, positions={"600036.SH": 500}) as mock:
    init(mock)
    process_signal(signal, mock)
    assert len(mock.passorder_calls) == 1
# 自动 uninstall
```

### 运行完整测试脚本

```bash
cd /path/to/stock-platform
python sdk_local_test.py
```

## API 参考

### configure()

```python
configure(access_key, secret_key, strategy_name, backend_url=None, log_dir=None)
```

| 参数 | 类型 | 说明 |
|---|---|---|
| access_key | str | 访问密钥 |
| secret_key | str | 密钥 |
| strategy_name | str | 策略名称 |
| backend_url | str | 后端 URL（可选） |
| log_dir | str | 日志目录（可选，默认 ./logs） |

### init(C)

在 QMT 策略的 `init` 函数中调用。初始化策略状态、登录后端、注册定时任务。

| 参数 | 说明 |
|---|---|
| C | QMT ContextInfo 对象，测试时传入 MockQMTContext |

### process_signal(message_content, C)

分发信号到买入/卖出处理函数。

| 参数 | 类型 | 说明 |
|---|---|---|
| message_content | dict | 信号内容 |
| message_content.action | str | "BUY" 或 "SELL" |
| message_content.code | str | 股票代码，如 "600036.SH" |
| message_content.price | float | 价格 |
| message_content.pct | float | 交易比例（0-100） |
| message_content.strategy | str | 策略名称 |
| message_content.time | str | 时间字符串 |
| C | ContextInfo | QMT 上下文对象 |

### process_signal_messages(C)

由 QMT 定时器调用，查询后端新信号并逐条处理。

### handle_buy_signal(message_content, C)

处理买入信号的完整逻辑：检查资金、检查是否已买入、计算买入量、下单。

### handle_sell_signal(message_content, C)

处理卖出信号的完整逻辑：检查持仓、计算卖出量、下单。

### refresh_waiting_dict(C)

更新委托状态，移除已成交/已撤/废单的等待项。

### refresh_bought_list(C)

更新买入列表，移除已撤/部撤/废单的买入记录。

### refresh_timeout_orders(C)

检查超时委托并撤单。

### refresh_order_status(C)

查询并返回当前所有订单状态信息。

### MockQMTContext

模拟 QMT 环境的 ContextInfo 对象。

#### 构造参数

```python
MockQMTContext(account_id="mock_001", cash=100000.0, positions=None, stock_list=None)
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| account_id | str | "mock_001" | 账户 ID（C.accID） |
| cash | float | 100000.0 | 初始可用资金 |
| positions | dict | {} | 初始持仓 {code: volume} |
| stock_list | list | ["000001.SZ"] | 股票列表 |

#### 可读属性

| 属性 | 类型 | 说明 |
|---|---|---|
| cash | float | 当前可用资金（随下单自动变化） |
| positions | dict | 当前持仓 {code: volume}（随下单自动变化） |
| orders | list[MockOrder] | 所有订单记录 |
| passorder_calls | list[dict] | passorder 调用历史 |
| cancel_calls | list[dict] | cancel 调用历史 |

#### 方法

| 方法 | 说明 |
|---|---|
| `install()` | 注入 mock 函数到 qmt_trading 模块 |
| `uninstall()` | 恢复原函数 |
| `reset()` | 重置所有状态到初始值 |
| `run_timer_callback()` | 手动触发 run_time 注册的回调 |
| `get_stock_list_in_sector(name)` | 模拟 C.get_stock_list_in_sector() |

#### passorder_calls 元素

```python
{
    'op_type': 23,          # 23=买入, 24=卖出
    'order_type': 1101,
    'acc_id': 'mock_001',
    'code': '600036.SH',
    'price_type': 11,
    'price': 35.5,
    'volume': 200,
    'strategy': 'test',
    'quick_type': 2,
    'remark': '20260410103000_600036.SH_buy_200股',
}
```

#### cancel_calls 元素

```python
{
    'order_sys_id': 'mock_0001',
    'acc_id': 'mock_001',
    'asset_type': 'stock',
}
```

### MockOrder 属性

| 属性 | 说明 |
|---|---|
| m_strOrderSysID | 系统委托号（mock_0001, ...） |
| m_strInstrumentID | 证券代码（600036） |
| m_strExchangeID | 交易所（SH/SZ） |
| m_nVolumeTotalOriginal | 委托数量 |
| m_nVolumeTraded | 成交数量 |
| m_nOrderStatus | 委托状态（56=已成, 54=已撤） |
| m_dLimitPrice | 委托价格 |
| m_strOptName | 操作名称（限价买入/限价卖出） |
| m_strRemark | 投资备注 |

### MockPosition 属性

| 属性 | 说明 |
|---|---|
| m_strInstrumentID | 证券代码 |
| m_strExchangeID | 交易所 |
| m_nVolume | 持仓数量 |
| m_nCanUseVolume | 可用数量 |

### MockAccount 属性

| 属性 | 说明 |
|---|---|
| m_dAvailable | 可用资金 |

## 状态机说明

MockQMTContext 内置状态机，下单/撤单自动更新资金和持仓：

**买入（opType=23）：**
- cash -= price * volume
- positions[code] += volume

**卖出（opType=24）：**
- cash += price * volume
- positions[code] -= volume

**撤单（cancel）：**
- 订单状态 56（已成）→ 54（已撤）
- 买入撤单：退还资金，减回持仓
- 卖出撤单：扣回资金，加回持仓

**get_trade_detail_data 查询：**
- 'account' → 返回当前资金
- 'position' → 返回当前持仓
- 'order' → 返回所有订单

## 常量

```python
from stock_platform_sdk.constants import (
    TradeConfig,    # 交易配置（价格乘数、最大金额、最小成交量）
    TimeConfig,     # 时间配置（交易时段、缓冲期）
    OrderStatus,    # 订单状态枚举（48-255）
    TradeAction,    # 信号动作（BUY/SELL）
    QMTApi,         # QMT API 常量（板块名、查询类型）
)

# 价格乘数
TradeConfig.BUY_PRICE_MULTIPLIER   # 1.012
TradeConfig.SELL_PRICE_MULTIPLIER  # 0.988
TradeConfig.MAX_AMOUNT_PER_ORDER   # 50000.0
TradeConfig.MIN_VOLUME             # 100

# 订单状态判断
OrderStatus.is_removable(56)    # True（已成可移除）
OrderStatus.is_cancellable(48)  # True（已报可撤单）
```
