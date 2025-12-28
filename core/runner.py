import json
import time

from services.factor_reporter import hourly_factor_report
from services.system_reporter import report_startup
from services.position_snapshot import load_snapshot, save_snapshot, print_positions

# 新日志系统
from services.logger import log_system, log_error

# 旧日志系统（兼容 + 终端打印）
from services.logger import write_log

from services.notifier import notify_error
from core.execution import get_symbol_min_qty
from core.client_manager import get_futures_client
from core.context import get_account_context
from core.strategy import multi_factor_signal, get_4h_trend

from core.logic.state_sync import sync_state
from core.logic.signal_handler import handle_signal
from core.logic.filters import pass_filters
from core.logic.position_handler import handle_position


MIN_PRICE_CHANGE_PCT = 0.002
MIN_HOLD_SECONDS = 5 * 60

# 因子状态汇报去重（记录上次发送的分钟数）
_last_factor_report_minute = None


def _default_snap():
    return {
        "side": "NONE",
        "qty": 0.0,
        "entry_price": 0.0,
        "entry_time": None,
        "last_signal": "HOLD",
        "partial_take_profit_done": False,  # 是否已执行部分止盈（10%）
    }


def run_once():

    # ================================
    # 系统运行日志（开始）
    # ================================
    write_log("=== run_once 开始执行 ===")
    log_system("run_once 开始执行")

    with open("config/symbols.json") as f:
        symbols = json.load(f)["symbols"]

    # 使用统一的客户端管理器
    client = get_futures_client()

    # ================================
    # 每 10 分钟因子状态汇报
    # ================================
    global _last_factor_report_minute
    m = time.localtime().tm_min
    # 在整10分钟时触发（00、10、20、30、40、50分），且避免同一分钟内重复发送
    if m % 10 == 0 and _last_factor_report_minute != m:
        write_log("⏱️ 触发因子状态汇报（每 10 分钟）")
        log_system("触发因子状态汇报")
        try:
            hourly_factor_report(symbols, client)
            _last_factor_report_minute = m  # 记录本次发送的分钟数
        except Exception as e:
            write_log(f"⚠️ 因子状态汇报失败: {e}")
            log_error(f"因子状态汇报失败: {e}", module="runner")

    # 系统启动报告（只在首次运行时有效）
    report_startup(symbols)

    snapshot = load_snapshot()
    now_ts = int(time.time())

    for symbol in symbols:
        try:
            write_log(f"\n=== 开始处理 {symbol} ===")
            log_system(f"开始处理 {symbol}")

            ctx = get_account_context(symbol)

            # 获取 4小时 K 线并判断趋势
            klines_4h = client.futures_klines(symbol=symbol, interval="4h", limit=50)
            trend_4h = get_4h_trend(klines_4h)
            write_log(f"[{symbol}] 4小时趋势: {trend_4h}")

            # 获取 1分钟 K 线与价格
            klines = client.futures_klines(symbol=symbol, interval="1m", limit=100)
            prices = [float(k[4]) for k in klines]
            current_price = prices[-1]

            write_log(f"[{symbol}] 当前价格: {current_price}")

            # 计算策略信号（传入4小时趋势）
            raw_signal, factors = multi_factor_signal(prices, klines, trend_4h=trend_4h)
            write_log(f"[{symbol}] 原始信号: {raw_signal} (1分钟策略: {factors.get('raw_signal', 'N/A')})")
            if factors.get("filtered_by_4h"):
                write_log(f"[{symbol}] ⚠️ 信号被4小时趋势过滤: 1分钟信号={factors.get('raw_signal')}, 4小时趋势={trend_4h}")

            # 同步状态
            sym_snap = sync_state(snapshot, symbol, ctx, _default_snap)
            write_log(f"[{symbol}] 上次信号: {sym_snap['last_signal']}")

            # 信号处理（去抖动、方向一致性等）
            effective_signal = handle_signal(raw_signal, sym_snap, write_log, symbol)
            write_log(f"[{symbol}] 处理后信号: {effective_signal}")

            if not effective_signal:
                snapshot[symbol] = sym_snap
                write_log(f"[{symbol}] 信号不可执行 → 跳过")
                log_system(f"{symbol} 信号不可执行，跳过")
                continue

            # 过滤器（持仓时间、最小波动幅度等）
            write_log(f"[{symbol}] 进入过滤器检查...")
            if not pass_filters(
                sym_snap,
                now_ts,
                current_price,
                MIN_HOLD_SECONDS,
                MIN_PRICE_CHANGE_PCT,
                write_log,
                symbol,
            ):
                snapshot[symbol] = sym_snap
                write_log(f"[{symbol}] 未通过过滤器 → 跳过")
                log_system(f"{symbol} 未通过过滤器，跳过")
                continue

            write_log(f"[{symbol}] 过滤器通过")

            # 获取最小下单量
            min_qty = get_symbol_min_qty(symbol)
            write_log(f"[{symbol}] 最小下单量: {min_qty}")

            # 执行开仓/平仓逻辑
            write_log(f"[{symbol}] 执行仓位处理...")
            sym_snap = handle_position(
                symbol,
                effective_signal,
                sym_snap,
                ctx,
                min_qty,
                now_ts,
                write_log,
                current_price,
            )

            snapshot[symbol] = sym_snap

            write_log(f"[{symbol}] 处理完成 ✓")
            log_system(f"{symbol} 处理完成")

        except Exception as e:
            log_error(f"[{symbol}] Big运行错误: {e}", module="runner")
            write_log(f"[{symbol}] ❌ 运行错误: {e}")
            notify_error(symbol, e)

    # 保存快照
    save_snapshot(snapshot)

    # ================================
    # 系统运行日志（结束）
    # ================================
    write_log("=== run_once 执行完成 ===")
    
    # ================================
    # 查询并打印当前持仓状态
    # ================================
    write_log("🔍 查询当前持仓状态...")
    try:
        # 打印持仓状态（使用已保存的快照，其中包含最新信息）
        if snapshot:
            print_positions(snapshot)
        else:
            write_log("📌 当前无持仓")
    except Exception as e:
        write_log(f"⚠️ 查询持仓状态失败: {e}")
    
    write_log("")  # 空行分隔

    # 系统状态播报（每次 run_once 都执行）
    try:
        report_startup(symbols)
    except Exception as e:
        write_log(f"❌ 系统状态播报失败: {e}")

    log_system("run_once 执行完成")