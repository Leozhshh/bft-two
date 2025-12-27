# core/logic/filters.py

def pass_filters(sym_snap, now_ts, current_price, MIN_HOLD_SECONDS, MIN_PRICE_CHANGE_PCT, write_log, symbol):
    entry_time = sym_snap.get("entry_time")
    entry_price = sym_snap.get("entry_price")

    # 最小持仓时间过滤
    if entry_time:
        hold_seconds = now_ts - int(entry_time)
        if hold_seconds < MIN_HOLD_SECONDS:
            write_log(
                f"[{symbol}] 信号反转，但持仓仅 {hold_seconds}s < {MIN_HOLD_SECONDS}s，避免做T"
            )
            return False

    # 最小价差过滤
    if entry_price > 0:
        price_change_pct = abs(current_price - entry_price) / entry_price
        if price_change_pct < MIN_PRICE_CHANGE_PCT:
            write_log(
                f"[{symbol}] 信号反转，但价格变动 {price_change_pct:.4%} < {MIN_PRICE_CHANGE_PCT:.2%}，避免小波动做T"
            )
            return False

    return True