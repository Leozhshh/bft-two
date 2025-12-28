import json
import os
from core.runner import run_once
from services.logger import write_log
from services.position_snapshot import load_snapshot, print_positions
from core.context import get_account_context
from services.notifier_base import send_telegram

if __name__ == "__main__":
    write_log("=" * 60)
    write_log("✅ Binance Quant v1.0 启动（模拟测试模式）")
    write_log("=" * 60)
    
    # ================================
    # 首次启动：显示账户信息和持仓状态
    # ================================
    write_log("\n📊 系统初始化中...")
    
    # 读取交易对配置
    with open("config/symbols.json") as f:
        symbols = json.load(f)["symbols"]
    
    write_log(f"📌 监控交易对: {', '.join(symbols)}")
    
    # 获取账户余额（使用第一个交易对获取）
    balance = None
    if symbols:
        try:
            ctx = get_account_context(symbols[0])
            balance = ctx["balance"]
            write_log(f"💰 账户余额: {balance:.2f} USDT")
        except Exception as e:
            write_log(f"⚠️ 获取账户余额失败: {e}")
            balance = None
    
    # 查询并显示当前持仓状态
    write_log("\n🔍 查询当前持仓状态...")
    snapshot = load_snapshot()
    
    # 如果快照文件不存在或为空，从交易所查询实际持仓
    if not snapshot or all(snap.get("side") == "NONE" or snap.get("qty", 0) == 0 
                          for snap in snapshot.values()):
        write_log("📝 快照文件为空，正在从交易所查询实际持仓...")
        snapshot = {}
        for symbol in symbols:
            try:
                ctx = get_account_context(symbol)
                pos = ctx["position"]
                if pos["side"] != "NONE" and pos["qty"] > 0:
                    snapshot[symbol] = {
                        "side": pos["side"],
                        "qty": pos["qty"],
                        "entry_price": pos["entry_price"],
                        "entry_time": None,
                        "last_signal": "HOLD",
                    }
                    write_log(f"  ✓ {symbol}: 发现持仓 {pos['side']} {pos['qty']} 张 @ {pos['entry_price']:.2f}")
            except Exception as e:
                write_log(f"  ⚠️ {symbol}: 查询持仓失败: {e}")
    
    # 打印持仓状态
    if snapshot:
        print_positions(snapshot)
    else:
        write_log("📌 当前无持仓")
    
    # 构建并发送 Telegram 启动通知（包含余额和持仓）
    msg_lines = ["🚀 <b>系统启动通知</b>"]
    msg_lines.append("✅ Binance Quant v1.0 启动（模拟测试模式）")
    msg_lines.append(f"📌 监控交易对: {', '.join(symbols)}")
    
    if balance is not None:
        msg_lines.append(f"💰 账户余额: <b>{balance:.2f} USDT</b>\n")
    else:
        msg_lines.append("⚠️ 获取账户余额失败\n")
    
    # 添加持仓信息
    has_position = False
    for symbol in symbols:
        try:
            ctx = get_account_context(symbol)
            pos = ctx["position"]
            
            side = pos["side"]
            qty = pos["qty"]
            entry_price = pos["entry_price"]
            current_price = pos["current_price"]
            unrealized_pnl = pos["unrealized_pnl"]
            
            if side == "NONE" or qty == 0:
                msg_lines.append(f"📌 {symbol}: 无持仓")
                continue
            
            has_position = True
            side_cn = "多单" if side == "LONG" else "空单"
            
            # 计算浮动盈亏百分比
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
        except Exception as e:
            msg_lines.append(f"⚠️ {symbol}: 查询持仓失败: {e}\n")
    
    if not has_position:
        msg_lines.append("📌 当前无持仓")
    
    # 发送 Telegram 通知
    send_telegram("\n".join(msg_lines))
    
    write_log("\n" + "=" * 60)
    write_log("🚀 开始执行交易策略循环...")
    write_log("=" * 60 + "\n")

    while True:
        try:
            run_once()
        except Exception as e:
            write_log(f"❌ 运行错误: {e}")

        # 每 60 秒执行一次
        import time
        time.sleep(60)