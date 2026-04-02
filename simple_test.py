# coding:utf-8

# 错误的方式: from centrifugo_qmt import configure, init as centrifugo_init
# 正确的方式: 从 centrifugo 包导入
import sys
import os
import time
from datetime import datetime

# 确保可以找到包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 方法1: 从 centrifugo 包导入（推荐）
from centrifugo import configure, init as centrifugo_init, MockContextInfo

# 步骤 1: 配置连接参数
configure(
    access_key="1234567",  # 替换为你的 access_key
    secret_key="1234567",  # 替换为你的 secret_key
    strategy_name="default",  # 策略名称
    backend_url="http://localhost:8888",      # 可选，默认从 config.py 读取
    centrifugo_url="http://localhost:8000"    # 可选，默认从 config.py 读取
)

# 步骤 2: 定义初始化函数（QMT 策略入口）
def init(C):

    import centrifugo

    # 注册定时任务回调函数
    C.register_callback("process_centrifugo_messages", centrifugo.process_centrifugo_messages)

    print("Initializing Centrifugo QMT SDK...")

    # 调用 SDK 的 init 函数
    centrifugo_init(C)

    print("Centrifugo QMT SDK started")
    print("Listening for trading signals...")
    print("Background thread receiving messages, QMT timer processing automatically")
    print("Buy, sell, cancel, order management all handled automatically")

# 步骤 3: 模拟 QMT 环境运行
if __name__ == "__main__":
    print("="*60)
    print("Simulating QMT environment to start strategy")
    print("="*60)

    # 创建模拟的 ContextInfo 对象
    C = MockContextInfo()
    print(f"Mock QMT ContextInfo created")

    # 调用策略的 init 函数（QMT 会自动调用）
    print("\nCalling strategy init function...")
    init(C)

    print("\n" + "="*60)
    print("Strategy started, waiting for trading signals...")
    print("="*60)

    # 保持运行，观察 WebSocket 连接状态
    import time
    
    # 检查是否有 WebSocket 客户端
    try:
        import centrifugo.centrifugo_qmt as centrifugo_qmt
        import centrifugo

        ws_client = centrifugo_qmt.ws_client

        # 获取配置检查
        try:
            config = centrifugo.get_config()
            if config:
                print(f"\nConfig info:")
                print(f"  Backend URL: {config.backend_url}")
                print(f"  Centrifugo URL: {config.centrifugo_url}")
        except:
            pass

        if ws_client:
            print(f"\nWebSocket client status:")
            print(f"  Thread alive: {ws_client.thread.is_alive() if ws_client.thread else False}")
            print(f"  Handler type: {type(ws_client.handler).__name__}")

            # 等待一段时间观察
            print("\nWaiting 5 seconds to check connection status...")
            time.sleep(5)

            print(f"  Thread alive: {ws_client.thread.is_alive() if ws_client.thread else False}")
        else:
            print("\nWebSocket client not initialized")
    except Exception as e:
        print(f"\nWebSocket status check error: {e}")
        print("Note: Actual usage requires running in QMT environment")

    # 保持程序运行，持续监听 WebSocket 消息
    print("\n" + "="*60)
    print("Program running, press Ctrl+C to exit...")
    print("="*60)
    print("\nScheduled tasks status:")
    for func_name, task_info in C._scheduled_tasks.items():
        status = "Running" if task_info.get('running') else "Stopped"
        print(f"  - {func_name}: {status}, interval: {task_info['interval']}s")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        C.stop_all_tasks()
        print("All scheduled tasks stopped")
        print("Program exited")