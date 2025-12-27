import time
from core.client_manager import get_futures_client
from core.indicators.atr import get_atr
from utils.position_sizer import calculate_position_size

from services.logger import log_trade, log_error


# 缓存：避免重复请求 exchangeInfo
_symbol_filters_cache = {}


# ============================
#   账户余额
# ============================
def get_futures_balance():
    client = get_futures_client()
    balances = client.futures_account_balance()
    for b in balances:
        if b["asset"] == "USDT":
            return float(b["balance"])
    return 0.0


# ============================
#   持仓信息
# ============================
def get_futures_position(symbol):
    client = get_futures_client()
    positions = client.futures_position_information(symbol=symbol)
    if not positions:
        return {"positionAmt": "0", "entryPrice": "0"}
    return positions[0]


# ============================
#   LOT_SIZE（minQty + stepSize）
# ============================
def _get_symbol_lot_filter(symbol):
    if symbol in _symbol_filters_cache:
        return _symbol_filters_cache[symbol]

    client = get_futures_client()
    info = client.futures_exchange_info()

    for s in info["symbols"]:
        if s["symbol"] == symbol:
            for f in s["filters"]:
                if f["filterType"] == "LOT_SIZE":
                    lot_filter = {
                        "minQty": float(f["minQty"]),
                        "stepSize": float(f["stepSize"]),
                    }
                    _symbol_filters_cache[symbol] = lot_filter
                    return lot_filter

    # 兜底
    lot_filter = {"minQty": 0.01, "stepSize": 0.01}
    _symbol_filters_cache[symbol] = lot_filter
    return lot_filter


def get_symbol_min_qty(symbol):
    return _get_symbol_lot_filter(symbol)["minQty"]


# ============================
#   下单结果类
# ============================
class OrderResult:
    """下单结果封装类"""
    
    def __init__(self, success=False, symbol=None, side=None, qty=0.0, 
                 avg_price=0.0, order_id=None, error=None, warning=None):
        self.success = success
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.avg_price = avg_price
        self.order_id = order_id
        self.error = error
        self.warning = warning
    
    def is_success(self):
        """检查订单是否成功成交"""
        return self.success and self.qty > 0
    
    def __repr__(self):
        if self.success:
            return f"OrderResult(success=True, symbol={self.symbol}, side={self.side}, qty={self.qty}, price={self.avg_price})"
        else:
            return f"OrderResult(success=False, error={self.error}, warning={self.warning})"


# ============================
#   下单（改进版：明确的返回值）
# ============================
def place_market_order(symbol, side, qty):
    """
    下市价单
    
    Returns:
        OrderResult: 包含成功/失败状态和详细信息的对象
        
    Raises:
        Exception: 仅在网络错误或API错误时抛出
    """
    client = get_futures_client()
    
    try:
        # 创建订单
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=qty,
            newOrderRespType="RESULT",
        )

        order_id = order["orderId"]
        status = order.get("status", "UNKNOWN")

        # 如果订单创建时就已经成交
        if status == "FILLED":
            avg_price = float(order.get("avgPrice", order.get("price", 0)))
            executed_qty = float(order.get("executedQty", qty))

            log_trade(
                f"✅ 订单立即成交: {symbol} {side} qty={executed_qty} price={avg_price}",
                module="execution"
            )

            return OrderResult(
                success=True,
                symbol=symbol,
                side=side,
                qty=executed_qty,
                avg_price=avg_price,
                order_id=order_id
            )

        # 轮询直到成交（最多20次，每次0.2秒，总共4秒）
        for attempt in range(20):
            result = client.futures_get_order(symbol=symbol, orderId=order_id)
            status = result.get("status", "UNKNOWN")
            
            if status == "FILLED":
                avg_price = float(result.get("avgPrice", 0))
                executed_qty = float(result.get("executedQty", 0))

                log_trade(
                    f"✅ 订单成交: {symbol} {side} qty={executed_qty} price={avg_price}",
                    module="execution"
                )

                return OrderResult(
                    success=True,
                    symbol=symbol,
                    side=side,
                    qty=executed_qty,
                    avg_price=avg_price,
                    order_id=order_id
                )
            
            # 检查是否被取消或拒绝
            if status in ["CANCELED", "REJECTED", "EXPIRED"]:
                log_error(
                    f"❌ 订单被{status}: {symbol} {side} qty={qty} orderId={order_id}",
                    module="execution"
                )
                return OrderResult(
                    success=False,
                    symbol=symbol,
                    side=side,
                    qty=0.0,
                    order_id=order_id,
                    error=f"订单状态: {status}"
                )

            time.sleep(0.2)

        # 超时未成交 - 检查最终状态
        final_result = client.futures_get_order(symbol=symbol, orderId=order_id)
        final_status = final_result.get("status", "UNKNOWN")
        executed_qty = float(final_result.get("executedQty", 0))
        
        if executed_qty > 0:
            # 部分成交
            avg_price = float(final_result.get("avgPrice", 0))
            log_trade(
                f"⚠️ 订单部分成交: {symbol} {side} executed={executed_qty}/{qty} price={avg_price} status={final_status}",
                module="execution"
            )
            return OrderResult(
                success=True,  # 部分成交也算成功
                symbol=symbol,
                side=side,
                qty=executed_qty,
                avg_price=avg_price,
                order_id=order_id,
                warning=f"部分成交，状态: {final_status}"
            )
        else:
            # 完全未成交
            log_error(
                f"⚠️ 订单未成交: {symbol} {side} qty={qty} orderId={order_id} status={final_status}",
                module="execution"
            )
            return OrderResult(
                success=False,
                symbol=symbol,
                side=side,
                qty=0.0,
                order_id=order_id,
                error=f"订单未成交，状态: {final_status}"
            )

    except Exception as e:
        log_error(f"❌ 下单异常: {symbol} {side} qty={qty} error={e}", module="execution")
        return OrderResult(
            success=False,
            symbol=symbol,
            side=side,
            qty=0.0,
            error=str(e)
        )


# ============================
#   开仓入口（ATR 仓位管理）
# ============================
def open_position(symbol, side, price, write_log):
    """
    开仓入口：自动计算仓位（基于 ATR + system.json），并执行下单。
    
    Returns:
        OrderResult: 下单结果，如果计算仓位为0则返回None
    """
    # 1. 账户余额
    balance = get_futures_balance()

    # 2. ATR（周期 14）
    atr = get_atr(symbol, period=14)

    # 3. 交易所规则
    lot_filter = _get_symbol_lot_filter(symbol)
    min_qty = lot_filter["minQty"]
    step = lot_filter["stepSize"]

    # 4. 使用你现在的专业仓位管理模块
    qty = calculate_position_size(
        symbol=symbol,
        balance=balance,
        atr=atr,
        price=price,
        min_qty=min_qty,
        step=step,
        write_log=write_log,
    )

    if qty <= 0:
        write_log(f"[{symbol}] 计算仓位为 0，跳过开仓")
        return None

    write_log(f"[{symbol}] 开仓 {side}，数量={qty}")

    # 5. 执行下单
    return place_market_order(symbol, side, qty)