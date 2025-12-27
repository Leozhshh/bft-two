import os
import json
from core.context import get_account_context
from services.notifier_base import send_telegram

REPORTER_SNAPSHOT = os.path.join("logs", "reporter_snapshot.json")


def load_reporter_snapshot():
    if not os.path.exists(REPORTER_SNAPSHOT):
        return {}
    try:
        with open(REPORTER_SNAPSHOT, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_reporter_snapshot(data):
    os.makedirs("logs", exist_ok=True)
    with open(REPORTER_SNAPSHOT, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def report_startup(symbols):
    last = load_reporter_snapshot()
    current = {}

    # 读取账户余额（所有 symbol 共用同一个 futures 账户）
    if symbols:
        ctx0 = get_account_context(symbols[0])
        balance = ctx0["balance"]
    else:
        balance = None

    msg_lines = ["🚀 <b>系统状态更新</b>"]

    if balance is not None:
        msg_lines.append(f"💰 账户余额: <b>{balance:.2f} USDT</b>\n")

    has_position = False

    for symbol in symbols:
        ctx = get_account_context(symbol)
        pos = ctx["position"]

        side = pos["side"]
        qty = pos["qty"]
        entry_price = pos["entry_price"]
        current_price = pos["current_price"]
        unrealized_pnl = pos["unrealized_pnl"]

        current[symbol] = {
            "side": side,
            "qty": qty,
            "entry_price": entry_price,
        }

        if side == "NONE" or qty == 0:
            msg_lines.append(f"📌 {symbol}: 无持仓")
            continue

        has_position = True

        # 中文方向
        side_cn = "多单" if side == "LONG" else "空单"

        # 浮动盈亏百分比
        if entry_price > 0:
            pnl_pct = unrealized_pnl / (entry_price * qty) * 100
        else:
            pnl_pct = 0.0

        pnl_str = f"{unrealized_pnl:+.2f}"
        pnl_pct_str = f"{pnl_pct:+.2f}%"

        msg_lines.append(
            f"📌 {symbol}: <b>{side_cn}</b> {qty} 张 | 开仓价: {entry_price:.2f}"
        )
        msg_lines.append(f"   📊 当前价: {current_price:.2f}")
        msg_lines.append(f"   💵 浮动盈亏: {pnl_str} ({pnl_pct_str})\n")

    # snapshot 去重
    if current == last:
        return

    save_reporter_snapshot(current)
    send_telegram("\n".join(msg_lines))