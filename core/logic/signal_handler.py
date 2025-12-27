# core/logic/signal_handler.py

from services.logger import log_signal


def handle_signal(raw_signal, sym_snap, write_log, symbol):
    """
    信号处理逻辑：
    - 记录原始信号
    - 首次出现的方向信号不交易（防抖）
    - 更新 last_signal
    """

    last_signal = sym_snap.get("last_signal", "HOLD")

    # 写入专业版信号日志（结构化）
    log_signal(
        f"原始信号={raw_signal}, 上次信号={last_signal}",
        module=symbol
    )

    # ============================
    #   信号确认：首次出现不交易
    # ============================
    if raw_signal in ("LONG", "SHORT") and raw_signal != last_signal:

        # 写入旧日志系统（兼容）
        write_log(
            f"[{symbol}] 信号首次出现 {raw_signal}, 上次为 {last_signal} → 仅记录，不交易"
        )

        # 写入专业版信号日志
        log_signal(
            f"首次出现方向信号：{raw_signal}（上次={last_signal}）→ 不交易",
            module=symbol
        )

        sym_snap["last_signal"] = raw_signal
        return None  # 不交易

    # ============================
    #   信号未变化 → 直接返回
    # ============================
    sym_snap["last_signal"] = raw_signal

    # 写入专业版信号日志
    log_signal(
        f"处理后信号={raw_signal}（可执行）",
        module=symbol
    )

    return raw_signal