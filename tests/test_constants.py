#!/usr/bin/env python
"""
Constants module test
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from stock_platform_sdk.constants import (
    OrderStatus, TradeConfig, TimeConfig, ChannelPrefix,
    TradeAction, QMTApi, ErrorMessages,
    format_order_message, validate_volume, round_price
)


def test_order_status():
    """测试订单状态枚举"""
    print("\n[测试 1] OrderStatus 枚举")
    print("-" * 50)

    # 测试基本枚举值
    assert OrderStatus.FILLED == 56, "FILLED 应该是 56"
    assert OrderStatus.CANCELLED == 54, "CANCELLED 应该是 54"
    assert OrderStatus.INVALID == 57, "INVALID 应该是 57"
    print(f"✓ 枚举值正确: FILLED={OrderStatus.FILLED}, CANCELLED={OrderStatus.CANCELLED}, INVALID={OrderStatus.INVALID}")

    # 测试终态判断
    assert OrderStatus.is_terminal(56) == True, "56（已成）应该是终态"
    assert OrderStatus.is_terminal(48) == False, "48（已报）不应该是终态"
    print(f"✓ 终态判断正确: is_terminal(56)={OrderStatus.is_terminal(56)}, is_terminal(48)={OrderStatus.is_terminal(48)}")

    # 测试可移除判断
    assert OrderStatus.is_removable(56) == True, "56（已成）可移除"
    assert OrderStatus.is_removable(57) == True, "57（废单）可移除"
    assert OrderStatus.is_removable(48) == False, "48（已报）不可移除"
    print(f"✓ 可移除判断正确")

    # 测试可撤单判断
    assert OrderStatus.is_cancellable(48) == True, "48（已报）可撤单"
    assert OrderStatus.is_cancellable(56) == False, "56（已成）不可撤单"
    print(f"✓ 可撤单判断正确")


def test_trade_config():
    """测试交易配置"""
    print("\n[测试 2] TradeConfig 交易配置")
    print("-" * 50)

    # 测试价格乘数
    assert TradeConfig.BUY_PRICE_MULTIPLIER == 1.012, "买入价格乘数应该是 1.012"
    assert TradeConfig.SELL_PRICE_MULTIPLIER == 0.988, "卖出价格乘数应该是 0.988"
    print(f"✓ 价格乘数正确: BUY={TradeConfig.BUY_PRICE_MULTIPLIER}, SELL={TradeConfig.SELL_PRICE_MULTIPLIER}")

    # 测试交易限制
    assert TradeConfig.MAX_AMOUNT_PER_ORDER == 50000.0, "单笔最大金额应该是 50000"
    assert TradeConfig.MIN_VOLUME == 100, "最小成交量应该是 100"
    print(f"✓ 交易限制正确: MAX_AMOUNT={TradeConfig.MAX_AMOUNT_PER_ORDER}, MIN_VOLUME={TradeConfig.MIN_VOLUME}")

    # 测试订单类型
    assert TradeConfig.ORDER_TYPE_BUY == 23, "买入订单类型应该是 23"
    assert TradeConfig.ORDER_TYPE_SELL == 24, "卖出订单类型应该是 24"
    print(f"✓ 订单类型正确: BUY={TradeConfig.ORDER_TYPE_BUY}, SELL={TradeConfig.ORDER_TYPE_SELL}")


def test_time_config():
    """测试时间配置"""
    print("\n[测试 3] TimeConfig 时间配置")
    print("-" * 50)

    # 测试交易时间
    assert TimeConfig.TRADING_START == "091500", "交易开始时间应该是 091500"
    assert TimeConfig.TRADING_END == "150000", "交易结束时间应该是 150000"
    print(f"✓ 交易时间正确: START={TimeConfig.TRADING_START}, END={TimeConfig.TRADING_END}")

    # 测试日期格式
    assert "%Y-%m-%d" in TimeConfig.DATE_FORMAT, "日期格式应该包含 %Y-%m-%d"
    print(f"✓ 日期格式正确: {TimeConfig.DATE_FORMAT}")


def test_channel_prefix():
    """测试频道前缀"""
    print("\n[测试 4] ChannelPrefix 频道前缀")
    print("-" * 50)

    # 测试频道生成
    test_channel = ChannelPrefix.make_test_channel("my_strategy")
    assert test_channel == "test:my_strategy", f"测试频道应该是 'test:my_strategy'，实际是 '{test_channel}'"
    print(f"✓ 测试频道: {test_channel}")

    trade_channel = ChannelPrefix.make_trade_channel("my_strategy")
    assert trade_channel == "trade:my_strategy", f"交易频道应该是 'trade:my_strategy'，实际是 '{trade_channel}'"
    print(f"✓ 交易频道: {trade_channel}")

    signal_channel = ChannelPrefix.make_signal_channel("my_strategy")
    assert signal_channel == "signal:my_strategy", f"信号频道应该是 'signal:my_strategy'，实际是 '{signal_channel}'"
    print(f"✓ 信号频道: {signal_channel}")


def test_trade_action():
    """测试交易动作"""
    print("\n[测试 5] TradeAction 交易动作")
    print("-" * 50)

    # 测试动作常量
    assert TradeAction.BUY == "BUY", "买入动作应该是 BUY"
    assert TradeAction.SELL == "SELL", "卖出动作应该是 SELL"
    print(f"✓ 动作常量正确: BUY={TradeAction.BUY}, SELL={TradeAction.SELL}")

    # 测试动作验证
    assert TradeAction.is_valid("BUY") == True, "BUY 应该是有效动作"
    assert TradeAction.is_valid("SELL") == True, "SELL 应该是有效动作"
    assert TradeAction.is_valid("INVALID") == False, "INVALID 不应该是有效动作"
    print(f"✓ 动作验证正确")


def test_qmt_api():
    """测试 QMT API 常量"""
    print("\n[测试 6] QMTApi API 常量")
    print("-" * 50)

    # 测试市场代码
    assert QMTApi.MARKET_SH == "SH", "上海市场代码应该是 SH"
    assert QMTApi.MARKET_SZ == "SZ", "深圳市场代码应该是 SZ"
    print(f"✓ 市场代码正确: SH={QMTApi.MARKET_SH}, SZ={QMTApi.MARKET_SZ}")

    # 测试查询类型
    assert QMTApi.QUERY_ORDER == "order", "订单查询类型应该是 order"
    assert QMTApi.QUERY_POSITION == "position", "持仓查询类型应该是 position"
    print(f"✓ 查询类型正确")


def test_error_messages():
    """测试错误消息"""
    print("\n[测试 7] ErrorMessages 错误消息")
    print("-" * 50)

    # 测试错误消息不为空
    assert ErrorMessages.MISSING_STOCK_CODE != "", "缺少股票代码错误消息不应为空"
    assert ErrorMessages.INVALID_PRICE != "", "无效价格错误消息不应为空"
    assert ErrorMessages.INSUFFICIENT_CASH != "", "现金不足错误消息不应为空"
    print(f"✓ 错误消息定义正确")


def test_helper_functions():
    """测试辅助函数"""
    print("\n[测试 8] 辅助函数")
    print("-" * 50)

    # 测试 format_order_message
    msg = format_order_message("000001.SZ", "buy", 100, 10.50)
    assert "000001.SZ" in msg, "订单消息应该包含股票代码"
    assert "buy" in msg, "订单消息应该包含操作类型"
    assert "100" in msg, "订单消息应该包含数量"
    assert "10.50" in msg, "订单消息应该包含价格"
    print(f"✓ format_order_message: {msg}")

    # 测试 validate_volume
    assert validate_volume(100) == True, "100 股应该是有效的"
    assert validate_volume(200) == True, "200 股应该是有效的"
    assert validate_volume(150) == False, "150 股不应该是有效的（不是100的整数倍）"
    assert validate_volume(50) == False, "50 股不应该是有效的（小于最小成交量）"
    print(f"✓ validate_volume: 100={validate_volume(100)}, 150={validate_volume(150)}, 50={validate_volume(50)}")

    # 测试 round_price
    price1 = round_price(10.0, TradeConfig.BUY_PRICE_MULTIPLIER)
    assert abs(price1 - 10.12) < 0.01, f"价格调整应该约为 10.12，实际是 {price1}"
    price2 = round_price(10.0, TradeConfig.SELL_PRICE_MULTIPLIER)
    assert abs(price2 - 9.88) < 0.01, f"价格调整应该约为 9.88，实际是 {price2}"
    print(f"✓ round_price: 买入 {price1}, 卖出 {price2}")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("常量模块测试")
    print("=" * 60)

    try:
        test_order_status()
        test_trade_config()
        test_time_config()
        test_channel_prefix()
        test_trade_action()
        test_qmt_api()
        test_error_messages()
        test_helper_functions()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n常量模块功能完整，可以正常使用。")

        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
