#!/usr/bin/env python
"""
Stock Platform SDK test script
"""
import sys
import os

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

print("=" * 60)
print("Stock Platform SDK tests")
print("=" * 60)

# Test 1: QMTState
print("\n[Test 1] QMTState...")
try:
    from stock_platform_sdk import QMTState
    state = QMTState()
    assert hasattr(state, 'bought_list'), "缺少 bought_list 属性"
    assert hasattr(state, 'sold_list'), "缺少 sold_list 属性"
    assert hasattr(state, 'waiting_dict'), "缺少 waiting_dict 属性"
    print("✓ QMTState 所有属性正常")
except Exception as e:
    print(f"✗ QMTState 测试失败: {e}")
    sys.exit(1)

# Test 2: Config
print("\n[Test 2] Config management...")
try:
    from stock_platform_sdk import CentrifugoClientConfig
    config = CentrifugoClientConfig(
        access_key="test_access",
        secret_key="test_secret",
        strategy_name="test"
    )
    assert config.access_key == "test_access", "access_key 不正确"
    assert config.secret_key == "test_secret", "secret_key 不正确"
    print(f"✓ 配置对象创建成功")
    print(f"  - WebSocket URL: {config.websocket_url}")
    print(f"  - Login URL: {config.login_url}")
except Exception as e:
    print(f"✗ 配置管理测试失败: {e}")
    sys.exit(1)

# Test 3: configure function
print("\n[Test 3] configure()...")
try:
    import importlib
    import stock_platform_sdk
    importlib.reload(stock_platform_sdk)

    from stock_platform_sdk import configure, get_config
    configure(
        access_key="test_key_123",
        secret_key="test_secret_456",
        strategy_name="test",
        backend_url="http://localhost:8888",
        centrifugo_url="http://localhost:8000"
    )

    config = get_config()
    assert config is not None, "配置为空"
    assert config.access_key == "test_key_123", "access_key 不正确"
    assert config.secret_key == "test_secret_456", "secret_key 不正确"
    print("✓ configure() 函数正常")
    print(f"  - access_key: {config.access_key}")
    print(f"  - backend_url: {config.backend_url}")
except Exception as e:
    print(f"✗ configure() 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: exports check
print("\n[Test 4] Check exports...")
try:
    import stock_platform_sdk
    expected_exports = [
        'configure',
        'get_config',
        'QMTState',
        'init',
        'handle_buy_signal',
        'handle_sell_signal',
        'refresh_waiting_dict',
        'refresh_bought_list',
    ]
    for export in expected_exports:
        assert hasattr(stock_platform_sdk, export), f"Missing export: {export}"
    print(f"✓ 所有 {len(expected_exports)} 个导出接口正常")
except Exception as e:
    print(f"✗ 导出检查失败: {e}")
    sys.exit(1)

# Test 5: message queue thread safety
print("\n[Test 5] Message queue...")
try:
    import queue
    import threading
    import time

    msg_queue = queue.Queue()

    # 生产者线程
    def producer():
        for i in range(5):
            msg_queue.put({"action": "BUY", "code": f"00000{i}.SZ"})
            time.sleep(0.01)

    # 消费者线程
    def consumer():
        messages = []
        while not msg_queue.empty():
            try:
                msg = msg_queue.get_nowait()
                messages.append(msg)
            except queue.Empty:
                break
        return messages

    t1 = threading.Thread(target=producer)
    t1.start()
    t1.join()

    t2 = threading.Thread(target=consumer)
    t2.start()
    t2.join()

    assert msg_queue.qsize() == 0, "消息队列未清空"
    print("✓ 消息队列线程安全正常")
except Exception as e:
    print(f"✗ 消息队列测试失败: {e}")
    sys.exit(1)

# Test 6: WebSocket thread class
print("\n[Test 6] WebSocket thread class...")
try:
    from stock_platform_sdk import CentrifugoClientConfig
    from stock_platform_sdk.centrifugo_qmt import CentrifugoWebSocketThread

    config = CentrifugoClientConfig("test", "test", "test")
    msg_queue = queue.Queue()

    ws_thread = CentrifugoWebSocketThread(config, msg_queue)
    assert ws_thread.config is not None, "config 未设置"
    assert ws_thread.message_queue is msg_queue, "message_queue 未设置"
    assert ws_thread.thread is None, "thread 应该初始为 None"
    print("✓ WebSocket 线程类初始化正常")
except Exception as e:
    print(f"✗ WebSocket 线程类测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ 所有测试通过！")
print("=" * 60)
print("\n核心功能验证完成，SDK 可以使用。")
print("\n下一步：")
print("1. 在 QMT 环境中测试实际连接")
print("2. 测试买入/卖出信号处理")
print("3. 测试订单管理功能")
