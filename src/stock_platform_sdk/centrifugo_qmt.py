"""
Centrifugo QMT SDK - 核心实现

提供与 qmt.py 完全兼容的接口，使用 WebSocket 代替 Redis Stream
"""
import threading
import queue
import asyncio
import time
from datetime import datetime

# 导入内部模块
from .qmt_state import QMTState
from .centrifugo_websocket_client import create_websocket_handler
from . import get_config


# ============================================================================
# 全局变量
# ============================================================================

# WebSocket 客户端线程
ws_client = None

# 消息队列（线程安全）
message_queue = queue.Queue()

# 策略状态对象（相当于 qmt.py 的 A）
A = None


# ============================================================================
# WebSocket 后台线程
# ============================================================================

class CentrifugoWebSocketThread:
    """
    WebSocket 后台线程

    在独立线程中运行异步 WebSocket 连接，接收消息后放入队列
    """

    def __init__(self, config, msg_queue):
        """
        初始化 WebSocket 线程

        Args:
            config: CentrifugoClientConfig 配置对象
            msg_queue: queue.Queue 消息队列
        """
        self.config = config
        self.message_queue = msg_queue
        self.thread = None
        self.handler = None
        self._running = False

    def start(self):
        """启动后台线程"""
        if self.thread is None or not self.thread.is_alive():
            self._running = True
            self.thread = threading.Thread(
                target=self._run_async_loop,
                daemon=True
            )
            self.thread.start()
            print("✓ Centrifugo WebSocket 线程已启动")

    def stop(self):
        """停止后台线程"""
        self._running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _run_async_loop(self):
        """
        在后台线程中运行异步事件循环，带自动重连机制
        """
        while self._running:
            try:
                asyncio.run(self._connect_and_listen())
            except Exception as e:
                if self._running:
                    print(f"WebSocket 连接异常: {e}")
                    print("5 秒后尝试重新连接...")
                    time.sleep(5)
                    # 继续循环，重新连接
                else:
                    # 主动停止，退出循环
                    break

    async def _connect_and_listen(self):
        """
        连接 WebSocket 并监听消息

        收到消息后放入队列，供 QMT 主线程处理
        """
        if not self.config:
            raise ValueError("配置未初始化，请先调用 configure()")

        # 创建 WebSocket 处理器
        self.handler = create_websocket_handler(
            self.config.access_key,
            self.config.secret_key,
            self.config.strategy_name
        )

        # 连接服务器
        if not await self.handler.connect():
            raise ConnectionError("WebSocket 连接失败")

        print("✓ WebSocket 连接成功")

        # 获取用户频道
        user_id = self.handler.get_uid()
        channel = f"test:{self.config.strategy_name}"
        print(f"✓ 订阅频道: {channel}")

        # 定义消息回调
        def on_message(data):
            """
            收到消息时的回调

            将消息放入队列，供 QMT 主线程处理
            """
            try:
                self.message_queue.put(data)
                print(f"📨 收到消息: {data}")
            except Exception as e:
                print(f"消息处理异常: {e}")

        # 订阅频道
        await self.handler.listen_for_signals(on_message)

        # 持续监听
        while self._running and self.handler.is_connected:
            await asyncio.sleep(0.1)

        # 连接断开
        if self._running:
            raise ConnectionError("WebSocket 连接已断开")


# ============================================================================
# QMT 初始化和消息处理
# ============================================================================

def init(C):
    """
    初始化 Centrifugo QMT SDK

    在 QMT 策略的 init(C) 函数中调用

    Args:
        C: QMT ContextInfo 对象
    """
    global ws_client, A, message_queue

    # 获取配置
    config = get_config()
    if not config:
        raise ValueError(
            "配置未初始化！请先调用 configure() 设置连接参数。\n"
            "示例：\n"
            "  from centrifugo import configure\n"
            "  configure(access_key='xxx', secret_key='xxx')"
        )

    # 初始化状态对象
    A = QMTState()
    A.start_time = '091500'
    A.end_time = '150000'

    # 获取沪深A股列表
    try:
        A.hsa = C.get_stock_list_in_sector('沪深A股')
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        A.hsa = []

    print(f"✓ 状态初始化完成，沪深A股数量: {len(A.hsa)}")

    # 创建消息队列
    message_queue = queue.Queue()

    # 启动 WebSocket 线程
    ws_client = CentrifugoWebSocketThread(config, message_queue)
    ws_client.start()

    # 注册 QMT 定时任务（每秒检查一次消息队列）
    now = datetime.now()
    C.run_time("process_centrifugo_messages", "1nSecond", now, "SH")

    print("✓ Centrifugo QMT SDK 初始化完成")


def process_centrifugo_messages(C):
    """
    处理 Centrifugo 消息队列中的消息

    由 QMT 定时器调用（每秒一次）

    Args:
        C: QMT ContextInfo 对象
    """
    global message_queue

    # 检查队列中的所有消息
    while not message_queue.empty():
        try:
            msg = message_queue.get_nowait()
            process_signal(msg, C)
        except queue.Empty:
            break
        except Exception as e:
            print(f"处理消息异常: {e}, 消息内容: {msg}")


def process_signal(message_content, C):
    """
    分发消息到对应的处理函数

    Args:
        message_content: 消息内容字典
        C: QMT ContextInfo 对象
    """
    try:
        action = message_content.get('action')

        if action == 'BUY':
            handle_buy_signal(message_content, C)
        elif action == 'SELL':
            handle_sell_signal(message_content, C)
        else:
            print(f"⚠️  未知 action 类型: {action}")
    except Exception as e:
        print(f"❌ process_signal 异常: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# 交易信号处理（从 qmt.py 完整复制）
# ============================================================================

def handle_buy_signal(message_content, C):
    """
    处理买入信号

    Args:
        message_content: 消息内容，包含:
            - code: 股票代码
            - price: 价格
            - pct: 买入比例
            - strategy: 策略名称
            - time: 时间戳
        C: QMT ContextInfo 对象
    """
    global A

    refresh_waiting_dict(C)
    refresh_bought_list(C)
    refresh_timeout_orders(C)

    # 获取账户信息
    try:
        acct_info = get_trade_detail_data(C.accID, 'stock', 'account')
        cash = acct_info[0].m_dAvailable
    except Exception as e:
        print(f"获取账户信息失败: {e}")
        return

    stock_code = message_content.get('code')
    if not stock_code:
        print("消息中缺少股票代码")
        return

    # 检查现金和是否已买入
    if cash > 0 and stock_code not in A.bought_list:
        message_time_str = message_content.get('time', '')
        pct = float(message_content.get('pct', 100))
        strategy = message_content.get('strategy', 'centrifugo')

        today = datetime.now().strftime("%Y-%m-%d")
        print(f"今天的日期是: {today}")

        buy_price1 = float(message_content.get('price', 0))
        buy_price = round(buy_price1 * 1.012, 2)

        if buy_price is not None and buy_price > 0:
            if message_time_str[:10] == today:
                max_shares = cash / buy_price
                max_allowed_amount = 50000
                max_buy_volume = max_allowed_amount / buy_price
                buy_volume = max(
                    100,
                    min(
                        int(pct * max_shares // 100) * 100,
                        int(max_buy_volume // 100) * 100
                    )
                )

                msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_buy_{buy_volume}股"

                passorder(
                    23, 1101, C.accID, stock_code, 11,
                    float(buy_price), int(buy_volume), strategy, 2, msg, C
                )

                A.waiting_list.append(msg)
                A.bought_list.append(stock_code)
                A.waiting_dict[stock_code] = msg
                A.all_order_ref_dict[msg] = time.time()

                print(f"✅ 买入 {stock_code} {buy_volume} 股 @ {buy_price}")
            else:
                # 非交易日
                buy_volume = 0
                msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_buy_{buy_volume}股"
                passorder(
                    23, 1101, C.accID, stock_code, 11,
                    float(buy_price), int(buy_volume), strategy, 2, msg, C
                )
                A.waiting_list.append(msg)
                A.waiting_dict[stock_code] = msg
                A.all_order_ref_dict[msg] = time.time()
                print(f"⚠️  买入 {stock_code} {buy_volume} 股 @ {buy_price} (非交易日)")
        else:
            # 价格获取失败，使用备选方案
            print(f"❌ 无法获取股票 {stock_code} 的买入价格，使用备选方案")
            if message_time_str[:10] == today:
                msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_buy_{pct*100}%"
                t1 = int(datetime.now().strftime('%H%M'))
                if t1 >= 930:
                    # 涨停价买入
                    passorder(23, 1123, C.accID, stock_code, 12, 0, pct, strategy, 2, msg, C)
                    A.waiting_list.append(msg)
                    A.bought_list.append(stock_code)
                    A.waiting_dict[stock_code] = msg
                    A.all_order_ref_dict[msg] = time.time()
                    print(f"🔄 买入 {stock_code} 以涨停价 {pct*100}%")
                else:
                    # 卖5价买入
                    passorder(23, 1123, C.accID, stock_code, 0, 0, pct, strategy, 2, msg, C)
                    A.waiting_list.append(msg)
                    A.bought_list.append(stock_code)
                    A.waiting_dict[stock_code] = msg
                    A.all_order_ref_dict[msg] = time.time()
                    print(f"🔄 买入 {stock_code} 以卖5价 {pct * 100}%")
    else:
        print(f"⚠️  没有足够的现金或已买入股票 {stock_code}")


def handle_sell_signal(message_content, C):
    """
    处理卖出信号

    Args:
        message_content: 消息内容
        C: QMT ContextInfo 对象
    """
    global A

    stock_code = message_content.get('code')
    if not stock_code:
        print("消息中缺少股票代码")
        return

    pct = float(message_content.get('pct', 100))
    strategy = message_content.get('strategy', 'centrifugo')

    if stock_code not in A.waiting_dict or stock_code not in A.sold_list:
        message_time_str = message_content.get('time', '')
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"今天的日期是: {today}")

        sell_price1 = float(message_content.get('price', 0))
        sell_price = round(sell_price1 * 0.988, 2)

        if sell_price is not None and sell_price > 0:
            if message_time_str[:10] == today:
                # 获取持仓信息
                try:
                    position_info = get_trade_detail_data(C.accID, 'stock', 'position')
                    held_stocks = {}

                    for pos in position_info:
                        full_code = f"{pos.m_strInstrumentID}.{pos.m_strExchangeID}"
                        if full_code == stock_code:
                            num = pos.m_nVolume
                            num_s = pos.m_nCanUseVolume
                            held_stocks[stock_code] = {'num': num, 'num_s': num_s}
                            print(f"当前持有 {stock_code} 的数量是: {held_stocks[stock_code]['num']}")

                    if stock_code in held_stocks and held_stocks[stock_code]['num'] > 0:
                        sell_volume = int(pct * held_stocks[stock_code]['num'] / 100) * 100
                        sell_volume = min(sell_volume, held_stocks[stock_code]['num'])

                        msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_sell_{sell_volume}股"

                        passorder(
                            24, 1101, C.accID, stock_code, 11,
                            float(sell_price), int(sell_volume), strategy, 2, msg, C
                        )

                        A.sold_list.append(stock_code)
                        print(f"✅ 卖出 {stock_code} {sell_volume} 股 @ {sell_price}")
                    else:
                        print(f"⚠️  没有足够的 {stock_code} 持仓来执行卖出操作")
                except Exception as e:
                    print(f"❌ 获取持仓信息失败: {e}")
            else:
                # 非交易日
                sell_volume = 0
                msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_sell_{sell_volume}股"
                passorder(
                    24, 1101, C.accID, stock_code, 11,
                    float(sell_price), int(sell_volume), strategy, 2, msg, C
                )
                print(f"⚠️  卖出 {stock_code} {sell_volume} 股 @ {sell_price} (非交易日)")
        else:
            # 价格获取失败，使用备选方案
            print(f"❌ 无法获取股票 {stock_code} 的卖出价格，使用备选方案")
            if message_time_str[:10] == today:
                # 获取持仓信息
                try:
                    position_info = get_trade_detail_data(C.accID, 'stock', 'position')
                    held_stocks = {}

                    for pos in position_info:
                        full_code = f"{pos.m_strInstrumentID}.{pos.m_strExchangeID}"
                        if full_code == stock_code:
                            num = pos.m_nVolume
                            num_s = pos.m_nCanUseVolume
                            held_stocks[stock_code] = {'num': num, 'num_s': num_s}
                            print(f"当前持有 {stock_code} 的数量是: {held_stocks[stock_code]['num']}")

                    if stock_code in held_stocks and held_stocks[stock_code]['num'] > 0:
                        sell_volume = int(pct * held_stocks[stock_code]['num'] / 100) * 100
                        sell_volume = min(sell_volume, held_stocks[stock_code]['num'])
                        msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_sell_{sell_volume}股"
                        t1 = int(datetime.now().strftime('%H%M'))

                        if t1 >= 930:
                            # 买5价卖出
                            passorder(24, 1101, C.accID, stock_code, 10, 0, int(sell_volume), strategy, 2, msg, C)
                            A.sold_list.append(stock_code)
                            print(f"🔄 卖出 {stock_code} 以买5价 {sell_volume} 股")
                        else:
                            # 跌停价卖出
                            passorder(24, 1101, C.accID, stock_code, 12, 0, int(sell_volume), strategy, 2, msg, C)
                            A.sold_list.append(stock_code)
                            print(f"🔄 卖出 {stock_code} 以跌停价 {sell_volume} 股")
                    else:
                        print(f"⚠️  没有足够的 {stock_code} 持仓来执行卖出操作")
                except Exception as e:
                    print(f"❌ 获取持仓信息失败: {e}")
    else:
        print(f"⚠️  股票 {stock_code} 在卖出列表或等待列表中")


# ============================================================================
# 订单管理函数（从 qmt.py 完整复制）
# ============================================================================

def refresh_waiting_dict(C):
    """
    更新委托状态，入参为ContextInfo对象

    从委托对象的 投资备注 和 委托状态 更新等待字典
    """
    global A

    try:
        orders = get_trade_detail_data(C.accID, 'stock', 'order')
        ref_dict = {i.m_strRemark: int(i.m_nOrderStatus) for i in orders}
        del_list = []

        for stock_code in A.waiting_dict:
            if A.waiting_dict[stock_code] in ref_dict:
                status = ref_dict[A.waiting_dict[stock_code]]
                if status in [56, 53, 54]:  # 56已成 53部撤 54已撤
                    print(
                        f'✓ 查到投资备注 {A.waiting_dict[stock_code]}，'
                        f'委托状态 {status} (56已成 53部撤 54已撤) 从等待字典中删除'
                    )
                    del_list.append(stock_code)
                elif status == 57:  # 废单
                    print(f"✓ 投资备注为 {A.waiting_dict[stock_code]} 的委托状态为废单，停止等待")
                    del_list.append(stock_code)

        for stock_code in del_list:
            del A.waiting_dict[stock_code]

    except Exception as e:
        print(f"❌ refresh_waiting_dict 异常: {e}")


def refresh_bought_list(C):
    """
    更新买入列表，移除已撤、部撤或废单状态的订单
    """
    global A

    try:
        detailed_orders = get_trade_detail_data(C.accID, 'stock', 'order')
        order_status_dict = {order.m_strRemark: order.m_nOrderStatus for order in detailed_orders}
        stocks_to_remove = []

        for stock_code in A.bought_list:
            for order in detailed_orders:
                full_instrument_id = f'{order.m_strInstrumentID}.{order.m_strExchangeID}'
                if full_instrument_id == stock_code and order.m_strOptName == '限价买入':
                    remark = order.m_strRemark
                    if remark in order_status_dict:
                        status = order_status_dict[remark]
                        if status in [53, 54, 57]:  # 部撤、已撤或废单
                            print(
                                f'✓ 投资备注为 {remark} 的委托状态为 {status} '
                                f'(53-部撤, 54-已撤, 57-废单)，准备从买入列表中移除'
                            )
                            stocks_to_remove.append(stock_code)
                    break

        for stock_code in stocks_to_remove:
            A.bought_list.remove(stock_code)

        print("移除部撤、已撤或废单的买入列表:", A.bought_list)

    except Exception as e:
        print(f"❌ refresh_bought_list 异常: {e}")


def refresh_timeout_orders(C):
    """
    刷新超时委托状态，撤销超时的委托
    """
    global A

    try:
        now = datetime.now()
        now_timestr = now.strftime("%H%M%S")

        # 获取委托信息
        orders = get_trade_detail_data(C.accID, 'stock', 'order')

        # 在指定时间范围内不撤单
        if '091500' <= now_timestr <= '093000':
            return

        for order in orders:
            # 非本策略本次运行记录的委托不撤
            if order.m_strRemark not in A.all_order_ref_dict:
                continue

            # 委托后时间不到撤单等待时间的不撤
            if time.time() - A.all_order_ref_dict[order.m_strRemark] < A.withdraw_secs:
                continue

            # 对所有可撤状态的委托撤单
            if order.m_nOrderStatus in [48, 49, 50, 51, 52, 55, 86, 255]:
                print(f"⏰ 超时撤单 停止等待 {order.m_strRemark}")
                cancel(order.m_strOrderSysID, C.accID, 'stock', C)

        # 如果有未查到委托，查询委托
        if A.waiting_list:
            found_list = []
            orders = get_trade_detail_data(C.accID, 'stock', 'order')
            for order in orders:
                if order.m_strRemark in A.waiting_list:
                    found_list.append(order.m_strRemark)

            A.waiting_list = [i for i in A.waiting_list if i not in found_list]

        if A.waiting_list:
            print(f"⚠️  当前有未查到委托 {A.waiting_list} 暂停后续报单")

    except Exception as e:
        print(f"❌ refresh_timeout_orders 异常: {e}")


def refresh_order_status(C):
    """
    刷新订单状态信息

    Returns:
        list: 订单状态信息列表
    """
    try:
        orders = get_trade_detail_data(C.accID, 'stock', 'order')
        order_status_info = []

        for o in orders:
            stock_code = f"{o.m_strInstrumentID}.{o.m_strExchangeID}"
            order_info = {
                'stock': stock_code,
                'order_volume': o.m_nVolumeTotalOriginal,
                'traded_volume': o.m_nVolumeTraded,
                'order_status': o.m_nOrderStatus,
                'direction': o.m_strOptName,
                'remark': o.m_strRemark,
                'order_price': o.m_dLimitPrice,
                'order_info': o.m_strOptName
            }
            order_status_info.append(order_info)
            print(
                f'股票代码: {stock_code}, '
                f'委托数量: {o.m_nVolumeTotalOriginal}, 成交数量: {o.m_nVolumeTraded}, '
                f'委托状态: {o.m_nOrderStatus}, '
                f'方向: {o.m_strOptName}, '
                f'策略: {o.m_strRemark}'
            )

        return order_status_info

    except Exception as e:
        print(f"❌ refresh_order_status 异常: {e}")
        return []


# ============================================================================
# QMT API 占位符（实际使用时由 QMT 环境提供）
# ============================================================================

# 这些函数在 QMT 环境中是内置的
# 这里定义占位符是为了避免 IDE 报错
def passorder(*args, **kwargs):
    """QMT 下单函数（由 QMT 环境提供）"""
    raise NotImplementedError("passorder 需要在 QMT 环境中运行")


def get_trade_detail_data(*args, **kwargs):
    """QMT 获取交易明细函数（由 QMT 环境提供）"""
    raise NotImplementedError("get_trade_detail_data 需要在 QMT 环境中运行")


def cancel(*args, **kwargs):
    """QMT 撤单函数（由 QMT 环境提供）"""
    raise NotImplementedError("cancel 需要在 QMT 环境中运行")
