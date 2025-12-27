import math
from config.system import SYSTEM_CONFIG


def calculate_position_size(
    symbol,
    balance,
    atr,
    price,
    min_qty,
    step,
    write_log,
):
    """
    专业版仓位管理：
    1. ATR 风险预算
    2. 最大仓位限制（balance × leverage × max_position_ratio）
    3. minQty 对齐
    4. stepSize 对齐
    """

    risk_factor = SYSTEM_CONFIG["risk_factor"]
    max_position_ratio = SYSTEM_CONFIG["max_position_ratio"]
    leverage = SYSTEM_CONFIG["default_leverage"]

    # ================================
    # 1. ATR 风险预算
    # ================================
    if atr <= 0:
        write_log(f"[{symbol}] ATR 无效，atr={atr}")
        return 0

    risk_value = balance * risk_factor
    qty_atr = risk_value / atr

    write_log(f"[{symbol}] ATR 仓位计算: risk={risk_value:.4f}, atr={atr:.4f}, qty_atr={qty_atr:.4f}")

    # ================================
    # 2. 最大仓位限制（名义价值）
    # ================================
    max_notional = balance * leverage * max_position_ratio
    qty_max = max_notional / price

    write_log(
        f"[{symbol}] 最大仓位限制: balance={balance}, leverage={leverage}, "
        f"ratio={max_position_ratio}, max_notional={max_notional:.2f}, qty_max={qty_max:.4f}"
    )

    # ================================
    # 3. 取最小值（风险预算 vs 最大仓位）
    # ================================
    qty = min(qty_atr, qty_max)

    # ================================
    # 4. 对齐 stepSize
    # ================================
    if step > 0:
        qty = qty - (qty % step)

    # ================================
    # 5. 确保不低于 minQty
    # ================================
    if qty < min_qty:
        qty = min_qty

    write_log(f"[{symbol}] 最终仓位数量: {qty}")

    return qty


# ================================
# 兼容旧版本 position_handler 的入口
# ================================
def calc_final_position_size(
    symbol,
    balance,
    atr,
    price,
    min_qty,
    step,
    write_log,
):
    """
    兼容旧版本 position_handler 的入口函数。
    内部调用新版 calculate_position_size。
    """
    return calculate_position_size(
        symbol=symbol,
        balance=balance,
        atr=atr,
        price=price,
        min_qty=min_qty,
        step=step,
        write_log=write_log,
    )