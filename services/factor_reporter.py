import numpy as np
from services.notifier_base import send_telegram
from services.logger import log_factors   # ← 新增：专业因子日志
from core.strategy import calc_rsi, calc_atr


def compute_factors(prices, klines):
    """
    计算 MA、RSI、ATR、波动状态
    """
    ma_fast = np.mean(prices[-5:])
    ma_slow = np.mean(prices[-20:])
    trend = "LONG" if ma_fast > ma_slow else "SHORT"

    rsi = calc_rsi(prices)

    atr = calc_atr(klines)
    avg_price = np.mean(prices[-20:])
    atr_threshold = avg_price * 0.002  # 0.2%

    volatility = "HIGH" if atr >= atr_threshold else "LOW"

    return {
        "ma_fast": round(ma_fast, 4),
        "ma_slow": round(ma_slow, 4),
        "trend": trend,
        "rsi": round(rsi, 2),
        "atr": round(atr, 4),
        "volatility": volatility,
    }


def build_output(symbol, factors):
    """
    构建专业级因子状态输出
    """
    lines = [
        f"📊 <b>{symbol} 因子状态</b>",
        f"MA趋势: {factors['trend']}",
        f"RSI: {factors['rsi']}",
        f"ATR波动率: {factors['atr']}",
        f"波动状态: {factors['volatility']}",
    ]

    # 波动率异常提醒
    if factors["volatility"] == "LOW":
        lines.append(f"⚠️ {symbol} 波动率极低，趋势策略可能失效")
    elif factors["atr"] > factors["ma_fast"] * 0.02:
        lines.append(f"⚠️ {symbol} 波动率异常偏高，注意假突破风险")

    return "\n".join(lines)


def hourly_factor_report(symbols, client):
    """
    每执行一次因子状态汇报
    """
    msg_lines = ["🕒 <b>因子状态汇报</b>\n"]

    for symbol in symbols:
        klines = client.futures_klines(symbol=symbol, interval="1m", limit=100)
        prices = [float(k[4]) for k in klines]

        factors = compute_factors(prices, klines)

        # ================================
        # 写入专业版因子日志（结构化 JSON）
        # ================================
        log_factors(
            f"{symbol} 因子状态: {factors}",
            module=symbol
        )

        output = build_output(symbol, factors)

        msg_lines.append(output)
        msg_lines.append("")  # 空行分隔

    send_telegram("\n".join(msg_lines))