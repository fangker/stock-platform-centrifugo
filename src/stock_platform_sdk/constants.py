# centrifugo/constants.py
"""
交易相关常量定义
"""
from enum import IntEnum


# ============================================================================
# 订单状态枚举
# ============================================================================

class OrderStatus(IntEnum):
    """
    QMT 订单状态枚举

    状态码说明：
    - 48: 已报
    - 49: 部成
    - 50: 已受理
    - 51: 已拒绝
    - 52: 撤单已报
    - 53: 部撤
    - 54: 已撤
    - 55: 撤单拒绝
    - 56: 已成
    - 57: 废单
    - 86: 已确认
    - 255: 未知
    """

    SUBMITTING = 48           # 已报
    PARTIAL_FILLED = 49       # 部成
    ACCEPTED = 50             # 已受理
    REJECTED = 51             # 已拒绝
    CANCEL_SUBMITTING = 52    # 撤单已报
    PARTIAL_CANCELLED = 53    # 部撤
    CANCELLED = 54            # 已撤
    CANCEL_REJECTED = 55      # 撤单拒绝
    FILLED = 56               # 已成
    INVALID = 57              # 废单
    CONFIRMED = 86            # 已确认
    UNKNOWN = 255             # 未知

    @classmethod
    def is_terminal(cls, status: int) -> bool:
        """
        判断是否为终态

        终态：已成、部撤、已撤、废单、撤单拒绝、已拒绝、已确认
        """
        return status in [
            cls.FILLED,
            cls.PARTIAL_CANCELLED,
            cls.CANCELLED,
            cls.INVALID,
            cls.CANCEL_REJECTED,
            cls.REJECTED,
            cls.CONFIRMED
        ]

    @classmethod
    def is_removable(cls, status: int) -> bool:
        """
        判断是否可从等待列表中移除

        可移除状态：已成、部撤、已撤、废单
        """
        return status in [cls.FILLED, cls.PARTIAL_CANCELLED, cls.CANCELLED, cls.INVALID]

    @classmethod
    def is_cancellable(cls, status: int) -> bool:
        """
        判断是否可撤单

        可撤单状态：已报、部成、已受理、撤单已报、已确认、未知
        """
        return status in [
            cls.SUBMITTING,
            cls.PARTIAL_FILLED,
            cls.ACCEPTED,
            cls.CANCEL_SUBMITTING,
            cls.CONFIRMED,
            cls.UNKNOWN
        ]


# ============================================================================
# 交易配置常量
# ============================================================================

class TradeConfig:
    """交易配置常量"""

    # 价格调整乘数
    BUY_PRICE_MULTIPLIER: float = 1.012    # 买入价格乘数（+1.2%）
    SELL_PRICE_MULTIPLIER: float = 0.988   # 卖出价格乘数（-1.2%）

    # 交易限制
    MAX_AMOUNT_PER_ORDER: float = 50000.0  # 单笔最大金额（元）
    MIN_VOLUME: int = 100                  # 最小成交量（股）
    VOLUME_MULTIPLE: int = 100             # 成交量倍数（必须是100的整数倍）

    # 默认值
    DEFAULT_PERCENTAGE: float = 100.0      # 默认交易比例（%）
    DEFAULT_WITHDRAW_SECS: int = 10        # 默认撤单等待秒数

    # QMT 订单类型
    ORDER_TYPE_BUY: int = 23               # 买入订单类型
    ORDER_TYPE_SELL: int = 24              # 卖出订单类型
    ORDER_MARKET: int = 11                 # 市场类型


# ============================================================================
# 时间配置
# ============================================================================

class TimeConfig:
    """时间配置常量"""

    # 交易时间段
    TRADING_START: str = "091500"  # 交易开始时间
    TRADING_END: str = "150000"    # 交易结束时间

    # 早晨缓冲期（不撤单）
    MORNING_BUFFER_START: str = "091500"  # 早晨缓冲开始时间
    MORNING_BUFFER_END: str = "093000"    # 早晨缓冲结束时间

    # 日期格式
    DATE_FORMAT: str = "%Y-%m-%d"          # 日期格式
    TIMESTAMP_FORMAT: str = "%Y%m%d%H%M%S"  # 时间戳格式
    TIME_FORMAT: str = "%H%M%S"            # 时间格式


# ============================================================================
# 频道命名规范
# ============================================================================

class ChannelPrefix:
    """频道命名前缀"""

    TEST: str = "test"       # 测试频道前缀
    TRADE: str = "trade"     # 交易频道前缀
    SIGNAL: str = "signal"   # 信号频道前缀

    @classmethod
    def make_test_channel(cls, strategy_name: str) -> str:
        """生成测试频道名"""
        return f"{cls.TEST}:{strategy_name}"

    @classmethod
    def make_trade_channel(cls, strategy_name: str) -> str:
        """生成交易频道名"""
        return f"{cls.TRADE}:{strategy_name}"

    @classmethod
    def make_signal_channel(cls, strategy_name: str) -> str:
        """生成信号频道名"""
        return f"{cls.SIGNAL}:{strategy_name}"


# ============================================================================
# 交易信号动作
# ============================================================================

class TradeAction:
    """交易信号动作类型"""

    BUY: str = "BUY"    # 买入信号
    SELL: str = "SELL"  # 卖出信号

    @classmethod
    def is_valid(cls, action: str) -> bool:
        """验证动作类型是否有效"""
        return action in [cls.BUY, cls.SELL]


# ============================================================================
# 消息队列配置
# ============================================================================

class QueueConfig:
    """消息队列配置"""

    CHECK_INTERVAL: float = 0.1  # 消息队列检查间隔（秒）
    MAX_QUEUE_SIZE: int = 1000   # 最大队列大小


# ============================================================================
# 日志配置
# ============================================================================

class LogConfig:
    """日志配置"""

    # 日志格式
    FORMAT: str = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'

    # 日志级别
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    # 日志标记
    MARKERS = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️ ',
        'info': 'ℹ️ ',
        'trade': '📊',
        'message': '📨',
        'clock': '⏰',
        'check': '✓',
        'cross': '✗'
    }


# ============================================================================
# QMT API 常量
# ============================================================================

class QMTApi:
    """QMT API 相关常量"""

    # 市场代码
    MARKET_SH: str = "SH"  # 上海市场
    MARKET_SZ: str = "SZ"  # 深圳市场

    # 数据类型
    DATA_TYPE_STOCK: str = "stock"
    DATA_TYPE_OPTION: str = "option"
    DATA_TYPE_FUTURE: str = "future"

    # 查询类型
    QUERY_ORDER: str = "order"       # 订单查询
    QUERY_POSITION: str = "position"  # 持仓查询
    QUERY_ACCOUNT: str = "account"    # 账户查询

    # 板块名称
    SECTOR_HSA: str = "沪深A股"       # 沪深A股板块


# ============================================================================
# 错误消息
# ============================================================================

class ErrorMessages:
    """标准错误消息"""

    # 验证错误
    MISSING_STOCK_CODE = "消息中缺少股票代码"
    INVALID_PRICE = "无法获取股票的成交价格"
    INVALID_SIGNAL = "未知的交易信号类型"

    # 账户错误
    INSUFFICIENT_CASH = "没有足够的现金"
    INSUFFICIENT_POSITION = "没有足够的持仓"
    ALREADY_BOUGHT = "股票已在买入列表中"
    ALREADY_SOLD = "股票已在卖出列表中"

    # 连接错误
    CONNECTION_FAILED = "HTTP 连接失败"
    AUTH_FAILED = "认证失败"
    QUERY_FAILED = "查询信号失败"

    # 配置错误
    CONFIG_NOT_INITIALIZED = "配置未初始化，请先调用 configure()"


# ============================================================================
# 辅助函数
# ============================================================================

def format_order_message(stock_code: str, action: str, volume: int, price: float) -> str:
    """
    生成订单消息字符串

    Args:
        stock_code: 股票代码
        action: 操作类型
        volume: 数量
        price: 价格

    Returns:
        订单消息字符串
    """
    from datetime import datetime
    timestamp = datetime.now().strftime(TimeConfig.TIMESTAMP_FORMAT)
    return f"{timestamp}_{stock_code}_{action}_{volume}股@{price:.2f}元"


def validate_volume(volume: int) -> bool:
    """
    验证成交量是否有效

    Args:
        volume: 成交量

    Returns:
        是否有效
    """
    return volume >= TradeConfig.MIN_VOLUME and volume % TradeConfig.VOLUME_MULTIPLE == 0


def round_price(price: float, multiplier: float = 1.0) -> float:
    """
    按乘数调整价格并保留两位小数

    Args:
        price: 原始价格
        multiplier: 乘数

    Returns:
        调整后的价格
    """
    return round(price * multiplier, 2)


# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # 枚举
    'OrderStatus',

    # 配置类
    'TradeConfig',
    'TimeConfig',
    'QueueConfig',
    'LogConfig',
    'ChannelPrefix',
    'TradeAction',
    'QMTApi',
    'ErrorMessages',

    # 辅助函数
    'format_order_message',
    'validate_volume',
    'round_price',
]
