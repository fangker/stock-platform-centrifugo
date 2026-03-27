"""
Centrifugo QMT SDK 使用示例

演示如何在 QMT 策略中使用 Centrifugo WebSocket 接收交易信号
"""

# ============================================================================
# 示例 1: 基本使用
# ============================================================================

from stock_platform_sdk import configure, init

# 步骤 1: 配置连接参数
configure(
    access_key="1234567",  # 替换为你的 access_key
    secret_key="1234567",  # 替换为你的 secret_key
    backend_url="http://localhost:8888",      # 可选，默认从 config.py 读取
    centrifugo_url="http://localhost:8000"    # 可选，默认从 config.py 读取
)

# 步骤 2: 定义初始化函数（QMT 策略入口）
def init(C):
    """
    QMT 策略初始化函数

    Args:
        C: QMT ContextInfo 对象
    """
    import stock_platform_sdk
    print("开始初始化 Centrifugo QMT SDK...")

    # 调用 SDK 的 init 函数
    centrifugo.init(C)

    print("✓ Centrifugo QMT SDK 已启动")
    print("✓ 开始监听交易信号...")
    print("✓ 后台线程自动接收消息，QMT 定时器自动处理")
    print("✓ 买入、卖出、撤单、订单管理全自动处理")


# ============================================================================
# 示例 2: 自定义消息处理
# ============================================================================

from stock_platform_sdk import configure, init as centrifugo_init

configure(access_key="xxx", secret_key="xxx")

def init(C):
    """初始化并添加自定义逻辑"""
    # 先初始化 SDK
    centrifugo_init(C)

    # 添加你自己的初始化逻辑
    C.run_time("my_custom_task", "10nSecond", datetime.now(), "SH")

    print("自定义初始化完成")

def my_custom_task(C):
    """你自己的定时任务"""
    print("执行自定义任务...")
    # 你的逻辑


# ============================================================================
# 示例 3: 监控和调试
# ============================================================================

from stock_platform_sdk import configure, init, get_config

configure(access_key="xxx", secret_key="xxx")

def init(C):
    """带调试信息的初始化"""
    import stock_platform_sdk

    # 打印配置信息
    config = get_config()
    print(f"配置信息:")
    print(f"  Backend URL: {config.backend_url}")
    print(f"  Centrifugo URL: {config.centrifugo_url}")

    # 初始化
    stock_platform_sdk.init(C)

    # 打印状态
    print(f"WebSocket thread status: {stock_platform_sdk.centrifugo_qmt.ws_client.thread.is_alive()}")


# ============================================================================
# 示例 4: 与原 qmt.py 对比
# ============================================================================

# ============ 原来的 qmt.py (Redis) ============
#
# import redis
# from qmt import *
#
# def init(C):
#     global redis_connection
#     redis_connection = redis.Redis(host='xxx', port=6379)
#     C.run_time("process_redis_stream", "5nSecond", ...)
#
# def process_redis_stream(C):
#     while True:
#         messages = redis_connection.xread(...)
#         for msg in messages:
#             process_signal(msg, C)

# ============ 现在的 centrifugo (WebSocket) ============
#
# from stock_platform_sdk import configure, init
#
# configure(access_key="xxx", secret_key="xxx")
#
# def init(C):
#     import stock_platform_sdk
#     centrifugo.init(C)
#     # 不需要定义 process_redis_stream
#     # SDK 自动处理消息接收和分发

# 主要区别：
# 1. 配置方式: configure() vs 硬编码
# 2. 数据源: WebSocket vs Redis Stream
# 3. 异步处理: SDK 内部处理 vs while True 循环
# 4. 接口: 完全兼容


# ============================================================================
# 示例 5: 完整的策略模板
# ============================================================================

from stock_platform_sdk import configure, init as centrifugo_init
from datetime import datetime

# 配置
configure(
    access_key="your_access_key",
    secret_key="your_secret_key"
)

def init(C):
    """策略初始化"""
    print("=" * 60)
    print("策略启动")
    print("=" * 60)

    # 初始化 Centrifugo SDK
    centrifugo_init(C)

    # 添加你自己的定时任务
    C.run_time("my_strategy", "60nSecond", datetime.now(), "SH")

    print("=" * 60)
    print("策略已启动，等待交易信号...")
    print("=" * 60)

def my_strategy(C):
    """你自己的策略逻辑"""
    print("执行策略逻辑...")

    # 你的策略代码
    # ...
