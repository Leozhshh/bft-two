from core.client_manager import get_futures_client


def get_account_context(symbol):
    """
    获取账户上下文（余额 + 持仓信息）
    使用统一的客户端管理器
    """
    client = get_futures_client()

    # 获取账户余额
    balance_info = client.futures_account_balance()
    usdt_balance = 0.0
    for item in balance_info:
        if item["asset"] == "USDT":
            usdt_balance = float(item["balance"])
            break

    # 获取持仓信息
    pos_data = client.futures_position_information(symbol=symbol)[0]

    qty = float(pos_data["positionAmt"])
    entry_price = float(pos_data["entryPrice"])
    mark_price = float(pos_data["markPrice"])
    unrealized_pnl = float(pos_data["unRealizedProfit"])

    if qty > 0:
        side = "LONG"
    elif qty < 0:
        side = "SHORT"
    else:
        side = "NONE"

    return {
        "position": {
            "side": side,
            "qty": abs(qty),
            "entry_price": entry_price,
            "current_price": mark_price,
            "unrealized_pnl": unrealized_pnl,
        },
        "balance": usdt_balance,
    }