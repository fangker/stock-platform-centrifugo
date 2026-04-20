"""
MockQMTContext - QMT 环境模拟模块

提供模拟的 QMT ContextInfo 对象和模块级函数（passorder、get_trade_detail_data、cancel），
用于本地测试 SDK 交易逻辑，无需真实 QMT 环境。

使用方式：
    mock = MockQMTContext(cash=100000, positions={"600036.SH": 500})
    mock.install()
    init(mock)
    mock.run_timer_callback()
    assert len(mock.passorder_calls) == 1
    mock.uninstall()

也支持上下文管理器：
    with MockQMTContext(cash=100000) as mock:
        init(mock)
        mock.run_timer_callback()
"""
import copy
from typing import Dict, List, Optional, Callable


# ============================================================================
# 数据对象
# ============================================================================


class MockAccount:
    """模拟账户信息"""

    def __init__(self, m_dAvailable: float = 0.0):
        self.m_dAvailable = m_dAvailable

    def __repr__(self):
        return f"MockAccount(m_dAvailable={self.m_dAvailable})"


class MockOrder:
    """模拟订单对象"""

    def __init__(self, order_sys_id: str, instrument_id: str, exchange_id: str,
                 volume: int, traded_volume: int, order_status: int, limit_price: float,
                 opt_name: str, remark: str):
        self.m_strOrderSysID = order_sys_id
        self.m_strInstrumentID = instrument_id
        self.m_strExchangeID = exchange_id
        self.m_nVolumeTotalOriginal = volume
        self.m_nVolumeTraded = traded_volume
        self.m_nOrderStatus = order_status
        self.m_dLimitPrice = limit_price
        self.m_strOptName = opt_name
        self.m_strRemark = remark

    def __repr__(self):
        return (f"MockOrder(id={self.m_strOrderSysID}, "
                f"{self.m_strInstrumentID}.{self.m_strExchangeID}, "
                f"status={self.m_nOrderStatus}, "
                f"vol={self.m_nVolumeTraded}/{self.m_nVolumeTotalOriginal})")


class MockPosition:
    """模拟持仓对象"""

    def __init__(self, instrument_id: str, exchange_id: str,
                 volume: int, can_use_volume: int):
        self.m_strInstrumentID = instrument_id
        self.m_strExchangeID = exchange_id
        self.m_nVolume = volume
        self.m_nCanUseVolume = can_use_volume

    def __repr__(self):
        return (f"MockPosition({self.m_strInstrumentID}.{self.m_strExchangeID}, "
                f"vol={self.m_nVolume}, can_use={self.m_nCanUseVolume})")


def _parse_stock_code(code: str):
    """解析股票代码为 (instrument_id, exchange_id)"""
    parts = code.rsplit('.', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return code, ""


# ============================================================================
# MockQMTContext
# ============================================================================


class MockQMTContext:
    """模拟 QMT ContextInfo 对象

    提供与真实 QMT 环境兼容的 C 对象接口，以及 passorder / get_trade_detail_data / cancel
    的状态机模拟。下单后自动更新资金和持仓，撤单后自动回滚。

    Attributes:
        accID: 账户 ID
        cash: 当前可用资金（随下单自动变化）
        positions: 当前持仓 {code: volume}（随下单自动变化）
        orders: 所有订单记录 [MockOrder]
        passorder_calls: passorder 调用历史 [dict]
        cancel_calls: cancel 调用历史 [dict]
    """

    def __init__(self, account_id: str = "mock_001", cash: float = 100000.0,
                 positions: Optional[Dict[str, int]] = None,
                 stock_list: Optional[List[str]] = None):
        self.accID = account_id

        # 保存初始值用于 reset
        self._initial_cash = cash
        self._initial_positions = dict(positions or {})

        # 当前状态
        self.cash = cash
        self.positions: Dict[str, int] = dict(positions or {})
        self.orders: List[MockOrder] = []
        self.passorder_calls: List[dict] = []
        self.cancel_calls: List[dict] = []

        # C 对象配置
        self._stock_list = list(stock_list or ["000001.SZ"])
        self._timer_func_name: Optional[str] = None
        self._order_counter = 0

        # install 状态
        self._installed = False
        self._originals = {}

    # ---- C 对象接口 ----

    def get_stock_list_in_sector(self, sector_name: str) -> List[str]:
        """模拟 C.get_stock_list_in_sector()"""
        return self._stock_list

    def run_time(self, func_name: str, interval: str, start_time, market: str):
        """模拟 C.run_time()

        记录注册的回调函数名，通过 run_timer_callback() 手动触发。
        """
        self._timer_func_name = func_name

    def run_timer_callback(self):
        """手动触发 run_time 注册的回调函数

        Returns:
            回调函数的返回值，如果没有注册回调则返回 None
        """
        if not self._timer_func_name:
            return None
        from . import qmt_trading
        func = getattr(qmt_trading, self._timer_func_name, None)
        if func:
            return func(self)
        return None

    # ---- Mock QMT 函数（状态机） ----

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"mock_{self._order_counter:04d}"

    def _mock_passorder(self, op_type, order_type, acc_id, code, price_type,
                        price, volume, strategy, quick_type, remark, C):
        """模拟 passorder：下单后自动更新资金和持仓"""
        call = {
            'op_type': op_type, 'order_type': order_type, 'acc_id': acc_id,
            'code': code, 'price_type': price_type, 'price': float(price),
            'volume': int(volume), 'strategy': strategy, 'quick_type': quick_type,
            'remark': remark,
        }
        self.passorder_calls.append(call)

        instrument_id, exchange_id = _parse_stock_code(code)
        order_id = self._next_order_id()
        price = float(price)
        volume = int(volume)

        if op_type == 23:  # 买入
            opt_name = '限价买入'
            self.cash -= price * volume
            self.positions[code] = self.positions.get(code, 0) + volume
        elif op_type == 24:  # 卖出
            opt_name = '限价卖出'
            if self.positions.get(code, 0) < volume:
                raise ValueError(
                    f"卖出数量 {volume} 超过持仓 {code} 的 {self.positions.get(code, 0)} 股"
                )
            self.cash += price * volume
            self.positions[code] -= volume
            if self.positions[code] <= 0:
                del self.positions[code]
        else:
            opt_name = f'未知操作({op_type})'

        order = MockOrder(
            order_sys_id=order_id, instrument_id=instrument_id,
            exchange_id=exchange_id, volume=volume,
            traded_volume=volume, order_status=56,
            limit_price=price, opt_name=opt_name, remark=remark,
        )
        self.orders.append(order)
        return order_id

    def _mock_get_trade_detail_data(self, acc_id, asset_type, data_type):
        """模拟 get_trade_detail_data：根据当前状态返回数据"""
        if data_type == 'account':
            return [MockAccount(m_dAvailable=self.cash)]
        elif data_type == 'position':
            result = []
            for code, vol in self.positions.items():
                inst_id, ex_id = _parse_stock_code(code)
                result.append(MockPosition(inst_id, ex_id, vol, vol))
            return result
        elif data_type == 'order':
            return list(self.orders)
        return []

    def _mock_cancel(self, order_sys_id, acc_id, asset_type, C):
        """模拟 cancel：撤单后自动回滚资金和持仓"""
        self.cancel_calls.append({
            'order_sys_id': order_sys_id,
            'acc_id': acc_id,
            'asset_type': asset_type,
        })

        for order in self.orders:
            if order.m_strOrderSysID != order_sys_id:
                continue
            if order.m_nOrderStatus != 56:
                continue

            order.m_nOrderStatus = 54  # 已撤
            code = f"{order.m_strInstrumentID}.{order.m_strExchangeID}"
            price = order.m_dLimitPrice
            volume = order.m_nVolumeTraded

            if '买入' in order.m_strOptName:
                self.cash += price * volume
                self.positions[code] = self.positions.get(code, 0) - volume
                if self.positions.get(code, 0) <= 0:
                    self.positions.pop(code, None)
            elif '卖出' in order.m_strOptName:
                self.cash -= price * volume
                self.positions[code] = self.positions.get(code, 0) + volume
            break

    # ---- install / uninstall / reset ----

    def install(self):
        """将 mock 函数注入到 qmt_trading 模块

        替换 passorder、get_trade_detail_data、cancel 为 mock 版本。
        """
        if self._installed:
            return
        from . import qmt_trading
        self._originals = {
            'passorder': qmt_trading.passorder,
            'get_trade_detail_data': qmt_trading.get_trade_detail_data,
            'cancel': qmt_trading.cancel,
        }
        qmt_trading.passorder = self._mock_passorder
        qmt_trading.get_trade_detail_data = self._mock_get_trade_detail_data
        qmt_trading.cancel = self._mock_cancel
        self._installed = True

    def uninstall(self):
        """恢复 qmt_trading 模块的原函数"""
        if not self._installed:
            return
        from . import qmt_trading
        qmt_trading.passorder = self._originals.get('passorder')
        qmt_trading.get_trade_detail_data = self._originals.get('get_trade_detail_data')
        qmt_trading.cancel = self._originals.get('cancel')
        self._installed = False
        self._originals = {}

    def reset(self):
        """重置所有状态到初始值（不恢复原函数）"""
        self.cash = self._initial_cash
        self.positions = dict(self._initial_positions)
        self.orders.clear()
        self.passorder_calls.clear()
        self.cancel_calls.clear()
        self._timer_func_name = None
        self._order_counter = 0

    # ---- 上下文管理器 ----

    def __enter__(self):
        self.install()
        return self

    def __exit__(self, *args):
        self.uninstall()

    def __repr__(self):
        return (f"MockQMTContext(accID={self.accID}, cash={self.cash:.2f}, "
                f"positions={self.positions}, orders={len(self.orders)})")
