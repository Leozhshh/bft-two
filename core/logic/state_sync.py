# core/logic/state_sync.py
from core.client_manager import get_futures_client
from services.logger import log_system


def sync_state(snapshot, symbol, ctx, default_snap):
    """
    用 Binance 真实持仓覆盖 snapshot 的基础字段
    并尝试从订单历史恢复 entry_time
    
    改进：
    1. 同步持仓信息（side, qty, entry_price）
    2. 如果有持仓但 snapshot 中没有 entry_time，尝试从订单历史恢复
    3. 如果无法恢复，使用当前时间作为 fallback
    """
    pos = ctx["position"]

    sym_snap = snapshot.get(symbol, default_snap())
    
    # 同步基础持仓信息
    sym_snap["side"] = pos["side"]
    sym_snap["qty"] = pos["qty"]
    sym_snap["entry_price"] = pos["entry_price"]

    # 如果有持仓但缺少 entry_time，尝试从订单历史恢复
    if pos["side"] != "NONE" and pos["qty"] > 0:
        if not sym_snap.get("entry_time"):
            entry_time = _try_recover_entry_time(symbol, pos["side"], pos["entry_price"])
            if entry_time:
                sym_snap["entry_time"] = entry_time
                log_system(f"{symbol} 从订单历史恢复 entry_time: {entry_time}", module="state_sync")
            else:
                # 如果无法恢复，使用当前时间（但标记为估算值）
                import time
                sym_snap["entry_time"] = int(time.time())
                log_system(f"{symbol} 无法恢复 entry_time，使用当前时间作为估算值", module="state_sync")

    return sym_snap


def _try_recover_entry_time(symbol, side, entry_price):
    """
    尝试从最近的订单历史中恢复 entry_time
    
    Returns:
        int: 时间戳，如果无法恢复则返回 None
    """
    try:
        client = get_futures_client()
        
        # 获取最近的订单（最多50个）
        orders = client.futures_get_all_orders(symbol=symbol, limit=50)
        
        if not orders:
            return None
        
        # 查找匹配的开仓订单
        # 匹配条件：1) 方向一致 2) 价格接近（允许0.1%误差）
        target_side = "BUY" if side == "LONG" else "SELL"
        price_tolerance = entry_price * 0.001  # 0.1% 误差
        
        for order in reversed(orders):  # 从最新到最旧
            if order.get("status") != "FILLED":
                continue
            
            order_side = order.get("side")
            order_price = float(order.get("avgPrice", order.get("price", 0)))
            
            # 检查方向和价格是否匹配
            if order_side == target_side:
                if abs(order_price - entry_price) <= price_tolerance:
                    # 找到匹配的订单，返回其时间戳
                    time_ms = order.get("updateTime", order.get("time", 0))
                    return int(time_ms / 1000)  # 转换为秒级时间戳
        
        return None
        
    except Exception as e:
        # 如果获取订单历史失败，静默返回 None
        # 不记录错误日志，因为这不是关键功能
        return None