# centrifugo/qmt_mock.py
"""
QMT ContextInfo 对象的 Mock 实现

用于在测试环境中模拟 QMT 的 ContextInfo 对象，支持定时任务、下单、撤单等功能。
"""
import re
import threading
import time
from datetime import datetime


class MockContextInfo:
    """模拟 QMT ContextInfo 对象，支持真正的定时任务"""

    def __init__(self):
        self.account_id = "test_account"
        self.accID = "test_account"
        self._scheduled_tasks = {}  # 存储定时任务 {func_name: {'interval': int, 'thread': threading.Thread, 'running': bool}}
        self._task_callbacks = {}    # 存储回调函数 {func_name: callable}

    def _parse_interval(self, interval_str):
        """
        解析 QMT 间隔格式

        Args:
            interval_str: 如 "1nSecond", "5nSecond", "1nMinute" 等

        Returns:
            int: 间隔秒数
        """
        # QMT 格式: 数字 + n + 单位
        # 例如: 1nSecond = 1秒, 5nMinute = 5分钟
        match = re.match(r'(\d+)n(\w+)', interval_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()

            unit_map = {
                'second': 1,
                'minute': 60,
                'hour': 3600,
            }
            return value * unit_map.get(unit, 1)
        return 1  # 默认1秒

    def _run_scheduled_task(self, func_name, interval, context_obj):
        """
        定时任务执行线程

        Args:
            func_name: 要调用的函数名
            interval: 间隔秒数
            context_obj: 传递给函数的 ContextInfo 对象
        """
        task_info = self._scheduled_tasks.get(func_name)
        if not task_info:
            return

        # 等待到开始时间
        start_time = task_info.get('start_time')
        if start_time and start_time > datetime.now():
            wait_seconds = (start_time - datetime.now()).total_seconds()
            if wait_seconds > 0:
                print(f"[QMT] 定时任务 {func_name} 等待 {wait_seconds:.1f} 秒后开始...")
                time.sleep(wait_seconds)

        # 定期执行任务
        while task_info.get('running', False):
            try:
                callback = self._task_callbacks.get(func_name)
                if callback:
                    print(f"[QMT] 执行定时任务: {func_name} (间隔: {interval}秒)")
                    callback(context_obj)
                else:
                    print(f"[QMT] 警告: 未找到回调函数 {func_name}")
            except Exception as e:
                print(f"[QMT] 定时任务 {func_name} 执行异常: {e}")

            # 等待下一个周期
            time.sleep(interval)

    def run_time(self, func_name, interval, start_time, market="SH"):
        """
        注册定时任务（真正的实现）

        Args:
            func_name: 要调用的函数名
            interval: 间隔，如 "1nSecond" (1秒), "5nMinute" (5分钟)
            start_time: 开始时间 (datetime 对象)
            market: 市场代码，如 "SH", "SZ"
        """
        # 解析间隔
        interval_seconds = self._parse_interval(interval)
        print(f"[QMT] 注册定时任务: {func_name}, 间隔: {interval} ({interval_seconds}秒)")

        # 如果任务已存在，先停止
        if func_name in self._scheduled_tasks:
            self.stop_task(func_name)

        # 启动新的定时任务线程
        task_info = {
            'interval': interval_seconds,
            'thread': None,
            'running': True,
            'start_time': start_time,
            'market': market
        }

        thread = threading.Thread(
            target=self._run_scheduled_task,
            args=(func_name, interval_seconds, self),
            daemon=True
        )
        task_info['thread'] = thread
        self._scheduled_tasks[func_name] = task_info
        thread.start()

    def stop_task(self, func_name):
        """停止指定的定时任务"""
        if func_name in self._scheduled_tasks:
            task_info = self._scheduled_tasks[func_name]
            task_info['running'] = False
            if task_info['thread']:
                task_info['thread'].join(timeout=2)
            del self._scheduled_tasks[func_name]
            print(f"[QMT] 停止定时任务: {func_name}")

    def stop_all_tasks(self):
        """停止所有定时任务"""
        for func_name in list(self._scheduled_tasks.keys()):
            self.stop_task(func_name)

    def register_callback(self, func_name, callback):
        """
        注册定时任务的回调函数

        Args:
            func_name: 函数名
            callback: 回调函数，接收 ContextInfo 对象作为参数
        """
        self._task_callbacks[func_name] = callback
        print(f"[QMT] 注册回调函数: {func_name} -> {callback.__name__ if hasattr(callback, '__name__') else callback}")

    def order(self, symbol, price, amount, direction, **kwargs):
        """下单"""
        print(f"[QMT] 下单: {direction} {symbol} {price}元 x {amount}股")
        if kwargs:
            print(f"[QMT] 额外参数: {kwargs}")
        return f"ORDER_{int(datetime.now().timestamp())}"

    def cancel(self, order_id):
        """撤单"""
        print(f"[QMT] 撤单: {order_id}")
