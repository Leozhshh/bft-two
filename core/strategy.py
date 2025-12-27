import numpy as np


# ================================
# ✅ 判断4小时K线趋势
# ================================
def get_4h_trend(klines_4h, fast=5, slow=20):
    """
    根据4小时K线判断趋势
    返回: "LONG" (上行), "SHORT" (下行), "HOLD" (震荡)
    """
    if len(klines_4h) < slow:
        return "HOLD"
    
    prices_4h = [float(k[4]) for k in klines_4h]  # 收盘价
    
    ma_fast = np.mean(prices_4h[-fast:])
    ma_slow = np.mean(prices_4h[-slow:])
    
    # 判断趋势强度
    if ma_fast > ma_slow * 1.001:  # 快线比慢线高0.1%以上，认为是上行趋势
        return "LONG"
    elif ma_fast < ma_slow * 0.999:  # 快线比慢线低0.1%以上，认为是下行趋势
        return "SHORT"
    else:
        return "HOLD"  # 震荡


# ================================
# ✅ 计算 RSI
# ================================
def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50  # 中性

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 70  # 强势

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ================================
# ✅ 计算 ATR（波动率）
# ================================
def calc_atr(klines, period=14):
    if len(klines) < period + 1:
        return 0

    trs = []
    for i in range(1, len(klines)):
        high = float(klines[i][2])
        low = float(klines[i][3])
        prev_close = float(klines[i - 1][4])

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        trs.append(tr)

    return np.mean(trs[-period:])


# ================================
# ✅ 插针过滤
# ================================
def is_wick_spike(kline):
    open_ = float(kline[1])
    high = float(kline[2])
    low = float(kline[3])
    close = float(kline[4])

    body = abs(close - open_)
    upper_wick = high - max(open_, close)
    lower_wick = min(open_, close) - low

    if body == 0:
        body = 1e-8

    if upper_wick > body * 2 or lower_wick > body * 2:
        return True

    return False


# ================================
# ✅ 多因子策略（MA + RSI + ATR + 插针过滤 + 4小时趋势过滤）
# ================================
def multi_factor_signal(prices, klines, trend_4h="HOLD", fast=5, slow=20):
    """
    专业级 v3.0 策略（多时间框架）：
    - 4小时趋势过滤（主要方向）
    - 插针过滤
    - ATR spike 过滤
    - MA 判断趋势（1分钟）
    - RSI 判断动能
    - ATR 判断波动率
    
    参数:
        trend_4h: 4小时趋势方向 ("LONG", "SHORT", "HOLD")
    """

    last_k = klines[-1]

    # ====== 0. 4小时趋势过滤（最重要：限制交易方向） ======
    if trend_4h == "LONG":
        # 4小时上行趋势，只允许买入（LONG）信号
        allowed_direction = "LONG"
    elif trend_4h == "SHORT":
        # 4小时下行趋势，只允许卖空（SHORT）信号
        allowed_direction = "SHORT"
    else:
        # 4小时震荡，不限制方向
        allowed_direction = None

    # ====== 1. 插针过滤 ======
    if is_wick_spike(last_k):
        return "HOLD", {"reason": "wick_spike", "trend_4h": trend_4h}

    # ====== 2. ATR spike 过滤 ======
    atr = calc_atr(klines)
    high = float(last_k[2])
    low = float(last_k[3])
    range_now = high - low

    if atr > 0 and range_now > atr * 2:
        return "HOLD", {"reason": "atr_spike", "trend_4h": trend_4h}

    # ====== 3. 趋势因子：MA（1分钟） ======
    if len(prices) < slow:
        return "HOLD", {"reason": "insufficient_data", "trend_4h": trend_4h}

    ma_fast = np.mean(prices[-fast:])
    ma_slow = np.mean(prices[-slow:])
    trend = "LONG" if ma_fast > ma_slow else "SHORT"

    # ====== 4. 动能因子：RSI ======
    rsi = calc_rsi(prices)
    if rsi > 55:
        momentum = "LONG"
    elif rsi < 45:
        momentum = "SHORT"
    else:
        momentum = "HOLD"

    # ====== 5. 波动率因子：ATR ======
    atr_threshold = np.mean(prices[-20:]) * 0.002  # 0.2%
    volatility = "HIGH" if atr >= atr_threshold else "LOW"

    # ====== 6. 信号融合（1分钟K线策略） ======
    if trend == momentum and momentum != "HOLD" and volatility == "HIGH":
        raw_signal = trend
    else:
        raw_signal = "HOLD"

    # ====== 7. 应用4小时趋势过滤 ======
    if allowed_direction is not None:
        # 如果4小时趋势明确，只允许同向交易
        if raw_signal == allowed_direction:
            final_signal = raw_signal
        elif raw_signal == "HOLD":
            final_signal = "HOLD"
        else:
            # 1分钟信号与4小时趋势相反，强制为HOLD
            final_signal = "HOLD"
    else:
        # 4小时震荡，使用1分钟信号
        final_signal = raw_signal

    return final_signal, {
        "ma_fast": round(ma_fast, 4),
        "ma_slow": round(ma_slow, 4),
        "trend": trend,
        "rsi": round(rsi, 2),
        "momentum": momentum,
        "atr": round(atr, 4),
        "volatility": volatility,
        "trend_4h": trend_4h,
        "raw_signal": raw_signal,
        "filtered_by_4h": allowed_direction is not None and raw_signal != final_signal
    }
