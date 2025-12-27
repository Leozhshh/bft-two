import os
import json
from core.context import get_account_context
from services.logger import write_log

SNAPSHOT_PATH = os.path.join("logs", "position_snapshot.json")


def load_snapshot():
    if not os.path.exists(SNAPSHOT_PATH):
        return {}
    try:
        with open(SNAPSHOT_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_snapshot(data):
    os.makedirs("logs", exist_ok=True)
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================================
# 终端打印持仓（runner 用）
# ================================
def print_positions(snapshot):
    """
    在终端打印当前持仓状态（不推送 Telegram）
    使用 write_log 保持输出格式一致
    """
    write_log("=== 持仓状态 ===")

    has_position = False
    for symbol, snap in snapshot.items():
        side = snap.get("side", "NONE")
        qty = snap.get("qty", 0)
        entry_price = snap.get("entry_price", 0)

        # 获取最新上下文（含 current_price、unrealized_pnl）
        try:
            ctx = get_account_context(symbol)
            pos = ctx["position"]

            current_price = pos["current_price"]
            unrealized_pnl = pos["unrealized_pnl"]

            if side == "NONE" or qty == 0:
                write_log(f"📌 {symbol}: 无持仓")
                continue

            has_position = True
            side_cn = "多单" if side == "LONG" else "空单"

            if entry_price > 0:
                pnl_pct = unrealized_pnl / (entry_price * qty) * 100
            else:
                pnl_pct = 0.0

            pnl_str = f"{unrealized_pnl:+.2f}"
            pnl_pct_str = f"{pnl_pct:+.2f}%"

            write_log(f"📌 {symbol}: {side_cn} {qty} 张 | 开仓价: {entry_price:.2f}")
            write_log(f"   📊 当前价: {current_price:.2f}")
            write_log(f"   💵 浮动盈亏: {pnl_str} ({pnl_pct_str})")
        except Exception as e:
            write_log(f"⚠️ {symbol}: 查询持仓信息失败: {e}")
    
    if not has_position:
        write_log("📌 当前无持仓")