from core.execution import place_market_order, _get_symbol_lot_filter, OrderResult
from core.indicators.atr import get_atr
from services.notifier import notify_open, notify_close, notify_reverse_open
from services.logger import log_error, log_trade
from utils.trade_calc import calc_pnl_and_pct, format_pnl, format_pct
from utils.position_sizer import calc_final_position_size


def handle_position(symbol, effective_signal, sym_snap, ctx, min_qty, now_ts, write_log, current_price):
    """
    处理仓位逻辑（开仓/平仓/反手/止盈）
    
    改进：
    1. 检查 place_market_order 的返回值
    2. 如果下单失败，不更新 snapshot
    3. 如果平仓成功但反手失败，回滚状态
    4. 止盈逻辑：10%卖50%，15%全平
    """
    side = ctx["position"]["side"]
    qty = ctx["position"]["qty"]
    entry_price = ctx["position"]["entry_price"]
    balance = ctx["balance"]
    
    # 初始化快照中的止盈状态
    if "partial_take_profit_done" not in sym_snap:
        sym_snap["partial_take_profit_done"] = False

    # ================================
    # 计算最终仓位（ATR + 最大仓位限制 + 交易所规则）
    # ================================
    atr = get_atr(symbol, period=14)
    lot_filter = _get_symbol_lot_filter(symbol)
    step = lot_filter["stepSize"]

    final_qty = calc_final_position_size(
        symbol=symbol,
        balance=balance,
        atr=atr,
        price=current_price,
        min_qty=min_qty,
        step=step,
        write_log=write_log,
    )

    # ================================
    # 无持仓 → 开仓
    # ================================
    if side == "NONE":
        sym_snap["entry_time"] = None
        sym_snap["partial_take_profit_done"] = False  # 重置止盈状态

        if effective_signal == "LONG":
            order_result = place_market_order(symbol, "BUY", final_qty)
            if not order_result.is_success():
                log_error(
                    f"❌ {symbol} 开多仓失败: {order_result.error or order_result.warning}",
                    module="position_handler"
                )
                write_log(f"[{symbol}] ❌ 开多仓失败: {order_result.error or order_result.warning}")
                return sym_snap  # 失败时不更新 snapshot
            
            notify_open(symbol, "BUY", order_result.qty, order_result.avg_price, balance)
            
            # 详细交易日志
            log_trade(
                f"✅ {symbol} 开多仓成功 | 数量: {order_result.qty} 张 | "
                f"开仓价: {order_result.avg_price:.2f} | 账户余额: {balance:.2f} USDT",
                module="position_handler"
            )
            
            sym_snap.update({
                "side": "LONG",
                "qty": order_result.qty,  # 使用实际成交数量
                "entry_price": order_result.avg_price,
                "entry_time": now_ts,
                "partial_take_profit_done": False,
            })

        elif effective_signal == "SHORT":
            order_result = place_market_order(symbol, "SELL", final_qty)
            if not order_result.is_success():
                log_error(
                    f"❌ {symbol} 开空仓失败: {order_result.error or order_result.warning}",
                    module="position_handler"
                )
                write_log(f"[{symbol}] ❌ 开空仓失败: {order_result.error or order_result.warning}")
                return sym_snap  # 失败时不更新 snapshot
            
            notify_open(symbol, "SELL", order_result.qty, order_result.avg_price, balance)
            
            # 详细交易日志
            log_trade(
                f"✅ {symbol} 开空仓成功 | 数量: {order_result.qty} 张 | "
                f"开仓价: {order_result.avg_price:.2f} | 账户余额: {balance:.2f} USDT",
                module="position_handler"
            )
            
            sym_snap.update({
                "side": "SHORT",
                "qty": order_result.qty,  # 使用实际成交数量
                "entry_price": order_result.avg_price,
                "entry_time": now_ts,
                "partial_take_profit_done": False,
            })

        return sym_snap

    # ================================
    # 有持仓 → 先检查止盈条件
    # ================================
    if entry_price > 0 and qty > 0:
        # 获取实际盈亏（已考虑杠杆）
        unrealized_pnl = ctx["position"].get("unrealized_pnl", 0.0)
        
        # 计算价格变动百分比（用于显示）
        _, price_pct = calc_pnl_and_pct(side, entry_price, current_price)
        
        # 计算相对于账户余额的盈亏百分比（考虑杠杆后的实际盈亏）
        # 使用账户初始余额作为基准（balance - unrealized_pnl）
        account_base = balance - unrealized_pnl
        if account_base > 0:
            pnl_pct_account = (unrealized_pnl / account_base) * 100
        else:
            # 如果账户基准为0或负数，使用价格变动百分比
            pnl_pct_account = price_pct
        
        # 止盈逻辑：15%全平（基于账户盈亏百分比）
        if pnl_pct_account >= 15.0:
            write_log(f"[{symbol}] 🎯 止盈触发：账户获利 {pnl_pct_account:.2f}% >= 15%（价格变动 {price_pct:.2f}%），全部平仓")
            
            if side == "LONG":
                close_result = place_market_order(symbol, "SELL", qty)
            else:  # SHORT
                close_result = place_market_order(symbol, "BUY", qty)
            
            if close_result.is_success():
                pnl_usdt, price_pct_close = calc_pnl_and_pct(side, entry_price, close_result.avg_price)
                # 计算实际账户盈亏百分比
                pnl_pct_account_close = (pnl_usdt / account_base * 100) if account_base > 0 else price_pct_close
                notify_close(symbol, side, close_result.qty, entry_price, close_result.avg_price,
                           format_pnl(pnl_usdt), format_pct(pnl_pct_account_close), "止盈15%全平", balance)
                
                # 详细交易日志
                log_trade(
                    f"🎯 {symbol} 止盈15%全平 | 方向: {side} | 数量: {close_result.qty} 张 | "
                    f"开仓价: {entry_price:.2f} | 平仓价: {close_result.avg_price:.2f} | "
                    f"盈亏: {format_pnl(pnl_usdt)} (账户: {format_pct(pnl_pct_account_close)}, 价格: {format_pct(price_pct_close)}) | "
                    f"账户余额: {balance:.2f} USDT | 等待下一波段信号",
                    module="position_handler"
                )
                
                sym_snap.update({
                    "side": "NONE",
                    "qty": 0.0,
                    "entry_price": 0.0,
                    "entry_time": None,
                    "partial_take_profit_done": False,
                })
                write_log(f"[{symbol}] ✅ 止盈平仓成功，等待下一波段信号")
                return sym_snap
            else:
                log_error(
                    f"❌ {symbol} 止盈平仓失败: {close_result.error or close_result.warning}",
                    module="position_handler"
                )
                write_log(f"[{symbol}] ❌ 止盈平仓失败: {close_result.error or close_result.warning}")
                return sym_snap
        
        # 止盈逻辑：10%卖50%（仅执行一次，基于账户盈亏百分比）
        elif pnl_pct_account >= 10.0 and not sym_snap.get("partial_take_profit_done", False):
            write_log(f"[{symbol}] 🎯 部分止盈触发：账户获利 {pnl_pct_account:.2f}% >= 10%（价格变动 {price_pct:.2f}%），卖出50%")
            
            # 计算卖出数量（50%）
            close_qty = qty * 0.5
            # 对齐步长
            if step > 0:
                close_qty = close_qty - (close_qty % step)
            # 确保不低于最小下单量
            if close_qty < min_qty:
                close_qty = min_qty
            
            # 确保不超过当前持仓
            close_qty = min(close_qty, qty)
            
            if side == "LONG":
                close_result = place_market_order(symbol, "SELL", close_qty)
            else:  # SHORT
                close_result = place_market_order(symbol, "BUY", close_qty)
            
            if close_result.is_success():
                pnl_usdt, price_pct_partial = calc_pnl_and_pct(side, entry_price, close_result.avg_price)
                remaining_qty = qty - close_result.qty
                # 计算部分止盈的账户盈亏百分比（按比例）
                pnl_usdt_partial = pnl_usdt  # 部分止盈的实际盈亏
                pnl_pct_account_partial = (pnl_usdt_partial / account_base * 100) if account_base > 0 else price_pct_partial
                
                # 详细交易日志
                log_trade(
                    f"🎯 {symbol} 部分止盈10% | 方向: {side} | 卖出: {close_result.qty} 张 | "
                    f"剩余: {remaining_qty:.4f} 张 | 开仓价: {entry_price:.2f} | "
                    f"平仓价: {close_result.avg_price:.2f} | "
                    f"盈亏: {format_pnl(pnl_usdt_partial)} (账户: {format_pct(pnl_pct_account_partial)}, 价格: {format_pct(price_pct_partial)})",
                    module="position_handler"
                )
                
                write_log(f"[{symbol}] ✅ 部分止盈成功：卖出 {close_result.qty} 张，剩余 {remaining_qty:.4f} 张")
                write_log(f"[{symbol}]   部分止盈盈亏: {format_pnl(pnl_usdt_partial)} (账户: {format_pct(pnl_pct_account_partial)}, 价格: {format_pct(price_pct_partial)})")
                
                # 更新持仓数量
                sym_snap["qty"] = remaining_qty
                sym_snap["partial_take_profit_done"] = True
            else:
                log_error(
                    f"❌ {symbol} 部分止盈失败: {close_result.error or close_result.warning}",
                    module="position_handler"
                )
                write_log(f"[{symbol}] ❌ 部分止盈失败: {close_result.error or close_result.warning}")
                return sym_snap

    # ================================
    # 有持仓 → 判断是否反转
    # ================================
    is_long_to_short = side == "LONG" and effective_signal == "SHORT"
    is_short_to_long = side == "SHORT" and effective_signal == "LONG"

    if not (is_long_to_short or is_short_to_long):
        return sym_snap

    # ================================
    # 平仓 + 反手（改进：检查每一步的结果）
    # ================================
    if is_long_to_short:
        # 1. 平多仓
        close_result = place_market_order(symbol, "SELL", qty)
        if not close_result.is_success():
            log_error(
                f"❌ {symbol} 平多仓失败: {close_result.error or close_result.warning}",
                module="position_handler"
            )
            write_log(f"[{symbol}] ❌ 平多仓失败: {close_result.error or close_result.warning}")
            return sym_snap  # 平仓失败，不继续反手
        
        # 平仓成功，计算盈亏
        pnl_usdt, pnl_pct = calc_pnl_and_pct("LONG", entry_price, close_result.avg_price)
        notify_close(symbol, "LONG", close_result.qty, entry_price, close_result.avg_price,
                     format_pnl(pnl_usdt), format_pct(pnl_pct), "信号反转（通过过滤）", balance)
        
        # 详细交易日志：平多仓
        log_trade(
            f"🔄 {symbol} 平多仓（信号反转） | 数量: {close_result.qty} 张 | "
            f"开仓价: {entry_price:.2f} | 平仓价: {close_result.avg_price:.2f} | "
            f"盈亏: {format_pnl(pnl_usdt)} ({format_pct(pnl_pct)})",
            module="position_handler"
        )

        # 2. 开空仓（反手）
        new_order_result = place_market_order(symbol, "SELL", final_qty)
        if not new_order_result.is_success():
            log_error(
                f"❌ {symbol} 平仓成功但反手失败: {new_order_result.error or new_order_result.warning}",
                module="position_handler"
            )
            write_log(f"[{symbol}] ❌ 平仓成功但反手失败: {new_order_result.error or new_order_result.warning}")
            # 平仓成功但反手失败，更新为无持仓状态
            sym_snap.update({
                "side": "NONE",
                "qty": 0.0,
                "entry_price": 0.0,
                "entry_time": None,
            })
            return sym_snap
        
        # 反手成功
        notify_reverse_open(symbol, "SELL", new_order_result.qty, new_order_result.avg_price)
        
        # 详细交易日志：反手开空仓
        log_trade(
            f"🔄 {symbol} 反手开空仓 | 数量: {new_order_result.qty} 张 | "
            f"开仓价: {new_order_result.avg_price:.2f} | 账户余额: {balance:.2f} USDT",
            module="position_handler"
        )
        
        sym_snap.update({
            "side": "SHORT",
            "qty": new_order_result.qty,  # 使用实际成交数量
            "entry_price": new_order_result.avg_price,
            "entry_time": now_ts,
        })

    elif is_short_to_long:
        # 1. 平空仓
        close_result = place_market_order(symbol, "BUY", qty)
        if not close_result.is_success():
            log_error(
                f"❌ {symbol} 平空仓失败: {close_result.error or close_result.warning}",
                module="position_handler"
            )
            write_log(f"[{symbol}] ❌ 平空仓失败: {close_result.error or close_result.warning}")
            return sym_snap  # 平仓失败，不继续反手
        
        # 平仓成功，计算盈亏
        pnl_usdt, pnl_pct = calc_pnl_and_pct("SHORT", entry_price, close_result.avg_price)
        notify_close(symbol, "SHORT", close_result.qty, entry_price, close_result.avg_price,
                     format_pnl(pnl_usdt), format_pct(pnl_pct), "信号反转（通过过滤）", balance)
        
        # 详细交易日志：平空仓
        log_trade(
            f"🔄 {symbol} 平空仓（信号反转） | 数量: {close_result.qty} 张 | "
            f"开仓价: {entry_price:.2f} | 平仓价: {close_result.avg_price:.2f} | "
            f"盈亏: {format_pnl(pnl_usdt)} ({format_pct(pnl_pct)})",
            module="position_handler"
        )

        # 2. 开多仓（反手）
        new_order_result = place_market_order(symbol, "BUY", final_qty)
        if not new_order_result.is_success():
            log_error(
                f"❌ {symbol} 平仓成功但反手失败: {new_order_result.error or new_order_result.warning}",
                module="position_handler"
            )
            write_log(f"[{symbol}] ❌ 平仓成功但反手失败: {new_order_result.error or new_order_result.warning}")
            # 平仓成功但反手失败，更新为无持仓状态
            sym_snap.update({
                "side": "NONE",
                "qty": 0.0,
                "entry_price": 0.0,
                "entry_time": None,
            })
            return sym_snap
        
        # 反手成功
        notify_reverse_open(symbol, "BUY", new_order_result.qty, new_order_result.avg_price)
        
        # 详细交易日志：反手开多仓
        log_trade(
            f"🔄 {symbol} 反手开多仓 | 数量: {new_order_result.qty} 张 | "
            f"开仓价: {new_order_result.avg_price:.2f} | 账户余额: {balance:.2f} USDT",
            module="position_handler"
        )
        
        sym_snap.update({
            "side": "LONG",
            "qty": new_order_result.qty,  # 使用实际成交数量
            "entry_price": new_order_result.avg_price,
            "entry_time": now_ts,
        })

    return sym_snap