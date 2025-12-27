# core/indicators/atr.py

import time
from core.client_manager import get_futures_client

# ATR 缓存，避免重复计算
_atr_cache = {}


def get_klines(symbol, interval="1m", limit=100):
    """
    获取 K 线数据（默认 100 根 1m K 线）
    """
    client = get_futures_client()
    return client.futures_klines(
        symbol=symbol,
        interval=interval,
        limit=limit,
    )


def compute_atr_from_klines(klines, period=14):
    """
    根据 K 线计算 ATR（专业版）
    使用标准公式：
        TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
        ATR = TR 的 period 日 EMA
    """
    trs = []
    prev_close = None

    for k in klines:
        high = float(k[2])
        low = float(k[3])
        close = float(k[4])

        if prev_close is None:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )

        trs.append(tr)
        prev_close = close

    # 取最后 period 个 TR 做 EMA
    if len(trs) < period:
        return trs[-1] if trs else 0  # 兜底

    # 初始值：SMA
    atr = sum(trs[:period]) / period
    alpha = 1 / period

    # EMA
    for tr in trs[period:]:
        atr = alpha * tr + (1 - alpha) * atr

    return atr


def get_atr(symbol, interval="1m", period=14, cache_seconds=10):
    """
    获取 ATR（带缓存）
    - interval: K 线周期（默认 1m）
    - period: ATR 周期（默认 14）
    - cache_seconds: 缓存时间（默认 10 秒）
    """
    key = f"{symbol}_{interval}_{period}"

    # 如果缓存有效，直接返回
    if key in _atr_cache:
        atr_value, ts = _atr_cache[key]
        if time.time() - ts < cache_seconds:
            return atr_value

    # 否则重新计算
    klines = get_klines(symbol, interval=interval, limit=period * 3)
    atr_value = compute_atr_from_klines(klines, period=period)

    # 写入缓存
    _atr_cache[key] = (atr_value, time.time())

    return atr_value