def calc_pnl_and_pct(side: str, entry_price: float, close_price: float):
    """
    计算盈亏（USDT）和收益率（百分比）
    side: LONG / SHORT
    """
    if entry_price <= 0:
        return 0.0, 0.0

    if side == "LONG":
        diff = close_price - entry_price
    else:  # SHORT
        diff = entry_price - close_price

    pct = diff / entry_price * 100
    return diff, pct


def calc_duration(entry_ms: int, close_ms: int):
    """根据毫秒时间戳计算持仓时长（分钟）"""
    if not entry_ms or not close_ms or close_ms <= entry_ms:
        return "未知"

    minutes = int((close_ms - entry_ms) / 60000)
    if minutes <= 0:
        return "<1 分钟"
    return f"{minutes} 分钟"


def format_pnl(pnl: float):
    """格式化盈亏显示"""
    sign = "+" if pnl >= 0 else "-"
    return f"{sign}{abs(pnl):.4f} USDT"


def format_pct(pct: float):
    """格式化收益率显示"""
    sign = "+" if pct >= 0 else "-"
    return f"{sign}{abs(pct):.2f}%"