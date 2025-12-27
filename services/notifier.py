from services.notifier_base import send_telegram
from services.logger import write_log


# 开仓通知
def notify_open(symbol, side, qty, price, balance):
    side_cn = "多单" if side == "BUY" else "空单"

    msg = (
        "🚀 <b>Big系统状态更新</b>\n"
        f"📌 {symbol}: <b>{side_cn}</b> {qty} 张 | 开仓价: {price:.2f}\n"
        f"💰 账户余额: {balance:.2f} USDT"
    )
    send_telegram(msg)


# 反手开仓通知
def notify_reverse_open(symbol, side, qty, price):
    side_cn = "多单" if side == "BUY" else "空单"

    msg = (
        "🔄 <b>Big反手开仓</b>\n"
        f"📌 {symbol}: <b>{side_cn}</b> {qty} 张 | 开仓价: {price:.2f}"
    )
    send_telegram(msg)


# 平仓通知
def notify_close(
    symbol,
    side,
    qty,
    entry_price,
    close_price,
    pnl_usdt,
    pnl_pct,
    reason,
    balance,
):
    side_cn = "多单" if side == "LONG" else "空单"

    msg = (
        "📤 <b>Big平仓</b>\n"
        f"📌 {symbol}: {side_cn} {qty} 张\n"
        f"⏳ 开仓价: {entry_price:.2f}\n"
        f"🏁 平仓价: {close_price:.2f}\n"
        f"💵 盈亏: {pnl_usdt} ({pnl_pct})\n"
        f"📘 原因: {reason}\n"
        f"💰 当前余额: {balance:.2f} USDT"
    )
    send_telegram(msg)


# 错误通知（增强版）
def notify_error(symbol, error, price=None, qty=None):
    """
    错误通知（增强版）
    - 保留原有风格
    - 自动识别名义价值错误（notional < 20）
    - 输出更详细的诊断信息
    """

    # 基础错误信息
    msg = [
        f"❌ <b>{symbol} 运行错误</b>",
        f"{error}",
    ]

    # 如果是名义价值错误，自动补充详细信息
    if "notional" in str(error).lower():
        msg.append("\n📌 <b>订单名义价值过小（notional < 20 USDT）</b>")

        if price is not None and qty is not None:
            notional = price * qty
            msg.append(f"📉 当前价格: {price}")
            msg.append(f"📦 下单数量: {qty}")
            msg.append(f"💲 名义价值: {notional:.2f} USDT")
            msg.append("📏 Binance 最低要求: 20 USDT")
            msg.append("🛠 建议：提高下单数量或调整仓位计算逻辑")

    # 发送 Telegram
    send_telegram("\n".join(msg))

    # 终端输出（保持你当前的风格）
    write_log(f"[{symbol}] ❌ 运行错误: {error}")