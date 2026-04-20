"""
QMT 策略状态管理类

相当于 qmt.py 中的 A 对象，用于管理策略运行时的所有状态
"""


class QMTState:
    """策略状态管理类"""

    def __init__(self):
        # 持仓分析数据（延迟初始化，避免导入时触发 pandas）
        self.pa = None

        # 日期相关
        self.last_day = ''

        # 委托等待字典 {stock_code: message}
        self.waiting_dict = {}

        # 所有委托引用字典 {message: timestamp}
        self.all_order_ref_dict = {}

        # 已买入股票列表
        self.bought_list = []

        # 已卖出股票列表
        self.sold_list = []

        # 撤单等待时间（秒）
        self.withdraw_secs = 10

        # 交易时间段
        self.start_time = '091500'
        self.end_time = '150000'

        # 等待列表（等待查询的委托）
        self.waiting_list = []

        # 沪深A股列表
        self.hsa = []
