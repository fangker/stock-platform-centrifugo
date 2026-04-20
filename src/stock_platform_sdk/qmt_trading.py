"""
QMT 交易逻辑 SDK

提供与 qmt.py 完全兼容的接口，使用 HTTP API 查询信号代替 WebSocket。
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

# 导入内部模块
from .qmt_state import QMTState
from .signal_client import SignalClient
from . import get_config, get_logger
from .constants import TimeConfig, QMTApi, TradeAction, TradeConfig, OrderStatus

log = None

# QMT 环境注入的全局函数引用，init() 时从 QMT 环境获取
_qmt_passorder = None
_qmt_get_trade_detail_data = None
_qmt_cancel = None
_caller_globals = None


def _get_acc_id(C):
    """从 QMT ContextInfo 对象获取账户ID，不缓存"""
    # 优先从 C 对象获取
    for attr in ('accID', 'accountID', 'account_id'):
        try:
            aid = getattr(C, attr, None)
            if aid:
                return aid
        except Exception:
            pass
    try:
        aid = C.accID
        if aid:
            return aid
    except Exception:
        pass
    # 模拟模式下 C.accID 不存在，尝试从策略脚本的全局变量获取
    if _caller_globals:
        aid = _caller_globals.get('account', '')
        if aid:
            return aid
    return ''


def _ensure_log():
    global log
    if log is None:
        log = get_logger() or logging.getLogger(__name__)


# ============================================================================
# 全局变量
# ============================================================================

# HTTP 客户端
signal_client = None

# 策略状态对象（相当于 qmt.py 的 A）
A = None


# ============================================================================
# QMT 初始化和信号处理
# ============================================================================

def init(C):
    """
    初始化信号 SDK

    在 QMT 策略的 init(C) 函数中调用

    Args:
        C: QMT ContextInfo 对象
    """
    global signal_client, A, _qmt_passorder, _qmt_get_trade_detail_data, _qmt_cancel, _caller_globals
    _ensure_log()

    # 从 QMT 环境获取内置函数（通过调用栈找到策略脚本的 globals）
    import sys, inspect
    _caller_globals = inspect.currentframe().f_back.f_globals
    _qmt_passorder = _caller_globals.get('passorder') or getattr(_builtins, 'passorder', None) or passorder
    _qmt_get_trade_detail_data = _caller_globals.get('get_trade_detail_data') or getattr(_builtins, 'get_trade_detail_data', None) or get_trade_detail_data
    _qmt_cancel = _caller_globals.get('cancel') or getattr(_builtins, 'cancel', None) or cancel

    # 解析账户ID
    aid = _get_acc_id(C)
    log.info("账户ID: %s", aid if aid else '(将在运行时获取)')

    config = get_config()
    if not config:
        raise ValueError(
            "配置未初始化！请先调用 configure() 设置连接参数。\n"
            "示例：\n"
            "  from stock_platform_sdk import configure\n"
            "  configure(access_key='xxx', secret_key='xxx')"
        )

    # 初始化状态对象
    A = QMTState()
    A.start_time = TimeConfig.TRADING_START
    A.end_time = TimeConfig.TRADING_END

    # 获取沪深A股列表
    try:
        A.hsa = C.get_stock_list_in_sector(QMTApi.SECTOR_HSA)
    except Exception as e:
        log.error("获取股票列表失败: %s", e)
        A.hsa = []

    log.info("状态初始化完成，沪深A股数量: %d", len(A.hsa))

    # 初始化 HTTP 客户端
    signal_client = SignalClient(config)
    log.info("正在登录...")
    signal_client.login()
    log.info("登录成功")
    log.info("信号 SDK 初始化完成")
    log.info("QMT 函数绑定: passorder=%s, get_trade_detail_data=%s, cancel=%s",
             _qmt_passorder.__module__ if hasattr(_qmt_passorder, '__module__') else 'builtin',
             _qmt_get_trade_detail_data.__module__ if hasattr(_qmt_get_trade_detail_data, '__module__') else 'builtin',
             _qmt_cancel.__module__ if hasattr(_qmt_cancel, '__module__') else 'builtin')


def process_signal_messages(C):
    """
    处理从 HTTP API 获取的信号

    由 QMT 定时器调用（每秒一次）

    Args:
        C: QMT ContextInfo 对象
    """
    global signal_client
    _ensure_log()

    if not signal_client:
        log.warning("signal_client 未初始化")
        return

    try:
        entries = signal_client.query_signals()
        for entry in entries:
            fields = entry.get("fields", {})
            # fields 可能是 {"data": "{...json...}"} 格式，需要解析 data 字段
            data_str = fields.get("data")
            if data_str and isinstance(data_str, str):
                try:
                    fields = json.loads(data_str)
                except (json.JSONDecodeError, TypeError):
                    pass
            process_signal(fields, C)

        if entries:
            last_id = signal_client.get_last_id()
            log.info("处理了 %d 条信号，最后 ID: %s", len(entries), last_id)
    except Exception as e:
        log.error("查询信号失败: %s", e)


def process_signal(message_content: Dict[str, Any], C):
    """
    分发消息到对应的处理函数

    Args:
        message_content: 消息内容字典
        C: QMT ContextInfo 对象
    """
    _ensure_log()
    try:
        action = message_content.get('action')

        if action == TradeAction.BUY:
            handle_buy_signal(message_content, C)
        elif action == TradeAction.SELL:
            handle_sell_signal(message_content, C)
        else:
            log.warning("未知 action 类型: %s", action)
    except Exception as e:
        log.error("process_signal 异常: %s", e)
        import traceback
        traceback.print_exc()


# ============================================================================
# 交易信号处理（从 qmt.py 完整复制）
# ============================================================================

def handle_buy_signal(message_content: Dict[str, Any], C):
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

    aid = _get_acc_id(C)
    if not aid:
        log.warning("无法获取 accID")

    refresh_waiting_dict(C)
    refresh_bought_list(C)
    refresh_timeout_orders(C)

    # 获取账户信息
    try:
        acct_info = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'account')
        cash = acct_info[0].m_dAvailable
    except Exception as e:
        log.error("获取账户信息失败: %s", e)
        return

    stock_code = message_content.get('code')
    if not stock_code:
        log.warning("消息中缺少股票代码")
        return

    # 检查现金和是否已买入
    if cash > 0 and stock_code not in A.bought_list:
        message_time_str = message_content.get('time', '')
        pct = float(message_content.get('pct', 100))
        strategy = message_content.get('strategy', 'signal')

        today = datetime.now().strftime("%Y-%m-%d")
        log.info("今天的日期是: %s", today)

        buy_price1 = float(message_content.get('price', 0))
        buy_price = round(buy_price1 * TradeConfig.BUY_PRICE_MULTIPLIER, 2)

        if buy_price is not None and buy_price > 0:
            if message_time_str[:10] == today:
                max_shares = cash / buy_price
                max_allowed_amount = TradeConfig.MAX_AMOUNT_PER_ORDER
                max_buy_volume = max_allowed_amount / buy_price
                buy_volume = max(
                    TradeConfig.MIN_VOLUME,
                    min(
                        int(pct * max_shares // 100) * 100,
                        int(max_buy_volume // 100) * 100
                    )
                )

                msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_buy_{buy_volume}股"

                _qmt_passorder(
                    TradeConfig.ORDER_TYPE_BUY, 1101, _get_acc_id(C), stock_code, 11,
                    float(buy_price), int(buy_volume), strategy, 2, msg, C
                )

                A.waiting_list.append(msg)
                A.bought_list.append(stock_code)
                A.waiting_dict[stock_code] = msg
                A.all_order_ref_dict[msg] = time.time()

                log.info("买入 %s %d 股 @ %s", stock_code, buy_volume, buy_price)
            else:
                # 非交易日，跳过不报单
                log.warning("买入 %s %d 股 @ %s (非交易日，跳过)", stock_code, 0, buy_price)
        else:
            # 价格获取失败，使用备选方案
            log.error("无法获取股票 %s 的买入价格，使用备选方案", stock_code)
            if message_time_str[:10] == today:
                msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_buy_{pct*100}%"
                t1 = int(datetime.now().strftime('%H%M'))
                if t1 >= 930:
                    # 涨停价买入
                    _qmt_passorder(23, 1123, _get_acc_id(C), stock_code, 12, 0, pct, strategy, 2, msg, C)
                    A.waiting_list.append(msg)
                    A.bought_list.append(stock_code)
                    A.waiting_dict[stock_code] = msg
                    A.all_order_ref_dict[msg] = time.time()
                    log.info("买入 %s 以涨停价 %s%%", stock_code, pct*100)
                else:
                    # 卖5价买入
                    _qmt_passorder(23, 1123, _get_acc_id(C), stock_code, 0, 0, pct, strategy, 2, msg, C)
                    A.waiting_list.append(msg)
                    A.bought_list.append(stock_code)
                    A.waiting_dict[stock_code] = msg
                    A.all_order_ref_dict[msg] = time.time()
                    log.info("买入 %s 以卖5价 %s%%", stock_code, pct * 100)
    else:
        log.warning("没有足够的现金或已买入股票 %s", stock_code)


def handle_sell_signal(message_content: Dict[str, Any], C):
    """
    处理卖出信号

    Args:
        message_content: 消息内容
        C: QMT ContextInfo 对象
    """
    global A

    stock_code = message_content.get('code')
    if not stock_code:
        log.warning("消息中缺少股票代码")
        return

    pct = float(message_content.get('pct', 100))
    strategy = message_content.get('strategy', 'signal')

    if stock_code not in A.waiting_dict or stock_code not in A.sold_list:
        message_time_str = message_content.get('time', '')
        today = datetime.now().strftime("%Y-%m-%d")
        log.info("今天的日期是: %s", today)

        sell_price1 = float(message_content.get('price', 0))
        sell_price = round(sell_price1 * TradeConfig.SELL_PRICE_MULTIPLIER, 2)

        if sell_price is not None and sell_price > 0:
            if message_time_str[:10] == today:
                try:
                    position_info = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'position')
                    held_stocks = {}

                    for pos in position_info:
                        full_code = f"{pos.m_strInstrumentID}.{pos.m_strExchangeID}"
                        if full_code == stock_code:
                            num = pos.m_nVolume
                            num_s = pos.m_nCanUseVolume
                            held_stocks[stock_code] = {'num': num, 'num_s': num_s}
                            log.info("当前持有 %s 的数量是: %d", stock_code, held_stocks[stock_code]['num'])

                    if stock_code in held_stocks and held_stocks[stock_code]['num'] > 0:
                        sell_volume = int(pct * held_stocks[stock_code]['num'] / 100) * 100
                        sell_volume = min(sell_volume, held_stocks[stock_code]['num'])

                        msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_sell_{sell_volume}股"

                        _qmt_passorder(
                            TradeConfig.ORDER_TYPE_SELL, 1101, _get_acc_id(C), stock_code, 11,
                            float(sell_price), int(sell_volume), strategy, 2, msg, C
                        )

                        A.sold_list.append(stock_code)
                        log.info("卖出 %s %d 股 @ %s", stock_code, sell_volume, sell_price)
                    else:
                        log.warning("没有足够的 %s 持仓来执行卖出操作", stock_code)
                except Exception as e:
                    log.error("获取持仓信息失败: %s", e)
            else:
                # 非交易日，跳过不报单
                log.warning("卖出 %s %d 股 @ %s (非交易日，跳过)", stock_code, 0, sell_price)
        else:
            log.error("无法获取股票 %s 的卖出价格，使用备选方案", stock_code)
            if message_time_str[:10] == today:
                try:
                    position_info = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'position')
                    held_stocks = {}

                    for pos in position_info:
                        full_code = f"{pos.m_strInstrumentID}.{pos.m_strExchangeID}"
                        if full_code == stock_code:
                            num = pos.m_nVolume
                            num_s = pos.m_nCanUseVolume
                            held_stocks[stock_code] = {'num': num, 'num_s': num_s}
                            log.info("当前持有 %s 的数量是: %d", stock_code, held_stocks[stock_code]['num'])

                    if stock_code in held_stocks and held_stocks[stock_code]['num'] > 0:
                        sell_volume = int(pct * held_stocks[stock_code]['num'] / 100) * 100
                        sell_volume = min(sell_volume, held_stocks[stock_code]['num'])
                        msg = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}_sell_{sell_volume}股"
                        t1 = int(datetime.now().strftime('%H%M'))

                        if t1 >= 930:
                            _qmt_passorder(24, 1101, _get_acc_id(C), stock_code, 10, 0, int(sell_volume), strategy, 2, msg, C)
                            A.sold_list.append(stock_code)
                            log.info("卖出 %s 以买5价 %d 股", stock_code, sell_volume)
                        else:
                            _qmt_passorder(24, 1101, _get_acc_id(C), stock_code, 12, 0, int(sell_volume), strategy, 2, msg, C)
                            A.sold_list.append(stock_code)
                            log.info("卖出 %s 以跌停价 %d 股", stock_code, sell_volume)
                except Exception as e:
                    log.error("获取持仓信息失败: %s", e)
    else:
        log.warning("股票 %s 在卖出列表或等待列表中", stock_code)


# ============================================================================
# 订单管理函数（从 qmt.py 完整复制）
# ============================================================================

def refresh_waiting_dict(C):
    """
    更新委托状态，入参为 ContextInfo 对象

    从委托对象的 投资备注 和 委托状态 更新等待字典
    """
    global A

    try:
        orders = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'order')
        ref_dict = {i.m_strRemark: int(i.m_nOrderStatus) for i in orders}
        del_list = []

        for stock_code in A.waiting_dict:
            if A.waiting_dict[stock_code] in ref_dict:
                status = ref_dict[A.waiting_dict[stock_code]]
                if OrderStatus.is_removable(status):
                    log.info(
                        '查到投资备注 %s，委托状态 %d (56已成 53部撤 54已撤) 从等待字典中删除',
                        A.waiting_dict[stock_code], status
                    )
                    del_list.append(stock_code)

        for stock_code in del_list:
            del A.waiting_dict[stock_code]

    except Exception as e:
        log.error("refresh_waiting_dict 异常: %s", e)


def refresh_bought_list(C):
    """
    更新买入列表，移除已撤、部撤或废单状态的订单
    """
    global A

    try:
        detailed_orders = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'order')
        order_status_dict = {order.m_strRemark: order.m_nOrderStatus for order in detailed_orders}
        stocks_to_remove = []

        for stock_code in A.bought_list:
            for order in detailed_orders:
                full_instrument_id = f'{order.m_strInstrumentID}.{order.m_strExchangeID}'
                if full_instrument_id == stock_code and order.m_strOptName == '限价买入':
                    remark = order.m_strRemark
                    if remark in order_status_dict:
                        status = order_status_dict[remark]
                        if status in [OrderStatus.PARTIAL_CANCELLED,
                                      OrderStatus.CANCELLED,
                                      OrderStatus.INVALID]:
                            log.info(
                                '投资备注为 %s 的委托状态为 %d (53-部撤, 54-已撤, 57-废单)，准备从买入列表中移除',
                                remark, status
                            )
                            stocks_to_remove.append(stock_code)
                        break

        for stock_code in stocks_to_remove:
            if stock_code in A.bought_list:
                A.bought_list.remove(stock_code)

        log.info("移除部撤、已撤或废单的买入列表: %s", A.bought_list)

    except Exception as e:
        log.error("refresh_bought_list 异常: %s", e)


def refresh_timeout_orders(C):
    """
    刷新超时委托状态，撤销超时的委托
    """
    global A

    try:
        now = datetime.now()
        now_timestr = now.strftime("%H%M%S")

        # 获取委托信息
        orders = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'order')

        # 在指定时间范围内不撤单
        if TimeConfig.MORNING_BUFFER_START <= now_timestr <= TimeConfig.MORNING_BUFFER_END:
            return

        for order in orders:
            # 非本策略本次运行记录的委托不撤
            if order.m_strRemark not in A.all_order_ref_dict:
                continue

            # 委托后时间不到撤单等待时间的不撤
            if time.time() - A.all_order_ref_dict[order.m_strRemark] < A.withdraw_secs:
                continue

            # 对所有可撤状态的委托撤单
            if OrderStatus.is_cancellable(order.m_nOrderStatus):
                log.info("超时撤单 停止等待 %s", order.m_strRemark)
                _qmt_cancel(order.m_strOrderSysID, _get_acc_id(C), 'stock', C)

        # 如果有未查到委托，查询委托
        if A.waiting_list:
            found_list = []
            orders = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'order')
            for order in orders:
                if order.m_strRemark in A.waiting_list:
                    found_list.append(order.m_strRemark)

            A.waiting_list = [i for i in A.waiting_list if i not in found_list]

        if A.waiting_list:
            log.warning("当前有未查到委托 %s 暂停后续报单", A.waiting_list)

    except Exception as e:
        log.error("refresh_timeout_orders 异常: %s", e)


def refresh_order_status(C):
    """
    刷新订单状态信息

    Returns:
        list: 订单状态信息列表
    """
    try:
        orders = _qmt_get_trade_detail_data(_get_acc_id(C), 'stock', 'order')
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
            log.info(
                '股票代码: %s, 委托数量: %d, 成交数量: %d, 委托状态: %d, 方向: %s, 策略: %s',
                stock_code, o.m_nVolumeTotalOriginal, o.m_nVolumeTraded,
                o.m_nOrderStatus, o.m_strOptName, o.m_strRemark
            )

        return order_status_info

    except Exception as e:
        log.error("refresh_order_status 异常: %s", e)
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
