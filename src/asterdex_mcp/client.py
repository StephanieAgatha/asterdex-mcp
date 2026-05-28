"""Aster DEX API client wrapper using kairos-aster-sdk."""

import os
from typing import Any

from kairos_aster import FuturesClient


class AsterClient:
    """Wrapper around kairos_aster FuturesClient for Aster DEX."""

    def __init__(self):
        pk = os.environ.get("ASTER_PRIVATE_KEY")
        if not pk:
            raise RuntimeError(
                "ASTER_PRIVATE_KEY not set. Pass via env var or MCP config."
            )
        self.user = os.environ.get("ASTER_WALLET")
        self.signer = os.environ.get("ASTER_SIGNER")
        self.client = FuturesClient(
            user=self.user,
            signer=self.signer,
            private_key=pk,
        )

    # ── Account ───────────────────────────────────────────────────────

    def get_balance(self) -> dict[str, Any]:
        """Account balance and margin summary."""
        bal = self.client.balance()
        result = {}
        for item in bal:
            b = float(item.get("balance", 0))
            if b != 0:
                result[item.get("asset", "?")] = {
                    "balance": b,
                    "available": float(item.get("availableBalance", 0)),
                    "cross_wallet_balance": float(item.get("crossWalletBalance", 0)),
                }
        return {
            "balances": result,
            "total_balance": sum(v["balance"] for v in result.values()),
            "total_available": sum(v["available"] for v in result.values()),
        }

    def get_positions(self) -> list[dict[str, Any]]:
        """Open positions with PnL."""
        positions = self.client.positions()
        active = []
        for p in positions:
            amt = float(p.get("positionAmt", 0))
            if amt == 0:
                continue
            entry = float(p.get("entryPrice", 0))
            mark = float(p.get("markPrice", 0))
            pnl = float(p.get("unRealizedProfit", 0))
            leverage = int(p.get("leverage", 1))
            notional = abs(amt) * mark
            margin = notional / leverage if leverage > 0 else notional
            pnl_pct = ((mark - entry) / entry * 100 * (1 if amt > 0 else -1)) if entry > 0 else 0

            active.append({
                "symbol": p.get("symbol"),
                "side": "LONG" if amt > 0 else "SHORT",
                "amount": amt,
                "entry_price": entry,
                "mark_price": mark,
                "unrealized_pnl": round(pnl, 4),
                "pnl_pct": round(pnl_pct, 2),
                "leverage": leverage,
                "margin": round(margin, 4),
                "notional": round(notional, 4),
                "liquidation_price": float(p.get("liquidationPrice", 0)),
                "margin_type": p.get("marginType", "cross"),
            })
        return active

    # ── Orders ────────────────────────────────────────────────────────

    def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Pending orders, optionally filtered by symbol."""
        kwargs = {}
        if symbol:
            kwargs["symbol"] = symbol.upper()
        orders = self.client.open_orders(**kwargs)
        result = []
        for o in orders:
            stop_px = o.get("stopPrice", "0")
            price = o.get("price", "0")
            display_price = stop_px if stop_px and stop_px != "0" else price
            display_price = display_price if display_price and display_price != "0" else "MARKET"

            result.append({
                "order_id": o.get("orderId"),
                "symbol": o.get("symbol"),
                "side": o.get("side"),
                "type": o.get("type"),
                "price": price,
                "stop_price": stop_px,
                "display_price": display_price,
                "quantity": o.get("origQty"),
                "executed_qty": o.get("executedQty"),
                "status": o.get("status"),
                "time_in_force": o.get("timeInForce"),
                "reduce_only": o.get("reduceOnly", False),
                "close_position": o.get("closePosition", False),
                "working_type": o.get("workingType"),
                "update_time": o.get("updateTime"),
            })
        return result

    def place_order(
        self,
        symbol: str,
        side: str,
        type: str,
        quantity: str | None = None,
        price: str | None = None,
        stop_price: str | None = None,
        close_position: bool = False,
        working_type: str = "MARK_PRICE",
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        leverage: int | None = None,
    ) -> dict[str, Any]:
        """Place an order. Handles TP/SL with close_position."""
        symbol = symbol.upper()
        side = side.upper()
        order_type = type.upper()

        # Set leverage first if requested
        if leverage is not None:
            try:
                self.client.set_leverage(symbol=symbol, leverage=leverage)
            except Exception as e:
                return {"error": f"Failed to set leverage: {e}"}

        # Build order params
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "working_type": working_type,
        }

        if close_position:
            params["close_position"] = True
            params["stop_price"] = stop_price
        else:
            if quantity:
                params["quantity"] = quantity
            if order_type == "LIMIT":
                params["price"] = price
                params["time_in_force"] = time_in_force
            elif order_type in ("STOP_MARKET", "TAKE_PROFIT_MARKET", "STOP"):
                params["stop_price"] = stop_price
                if not close_position and quantity:
                    params["quantity"] = quantity

        if reduce_only and not close_position:
            params["reduce_only"] = True

        result = self.client.place_order(**params)

        # Clean up response
        return {
            "order_id": result.get("orderId"),
            "symbol": result.get("symbol"),
            "side": result.get("side"),
            "type": result.get("type"),
            "status": result.get("status"),
            "price": result.get("price", "0"),
            "stop_price": result.get("stopPrice", "0"),
            "quantity": result.get("origQty", "0"),
            "reduce_only": result.get("reduceOnly", False),
            "close_position": result.get("closePosition", False),
            "working_type": result.get("workingType"),
        }

    def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel a specific order."""
        result = self.client.cancel_order(symbol=symbol.upper(), orderId=order_id)
        return {
            "order_id": result.get("orderId"),
            "symbol": result.get("symbol"),
            "status": result.get("status"),
            "message": "Order cancelled",
        }

    def cancel_all_orders(self, symbol: str | None = None) -> dict[str, Any]:
        """Cancel all open orders."""
        orders = self.get_open_orders(symbol)
        cancelled = []
        errors = []
        for o in orders:
            try:
                self.client.cancel_order(
                    symbol=o["symbol"],
                    orderId=o["order_id"],
                )
                cancelled.append(o["order_id"])
            except Exception as e:
                errors.append({"order_id": o["order_id"], "error": str(e)})

        return {
            "cancelled": len(cancelled),
            "errors": len(errors),
            "cancelled_ids": cancelled,
            "error_details": errors if errors else None,
        }

    # ── Exchange ──────────────────────────────────────────────────────

    def set_leverage(self, symbol: str, leverage: int) -> dict[str, Any]:
        """Set leverage for a pair."""
        result = self.client.set_leverage(symbol=symbol.upper(), leverage=leverage)
        return {
            "symbol": result.get("symbol", symbol.upper()),
            "leverage": result.get("leverage", leverage),
            "max_notional": result.get("maxNotionalValue"),
        }

    def get_exchange_info(self, symbol: str | None = None) -> Any:
        """Get exchange info for a symbol or all pairs."""
        info = self.client.exchange_info()
        symbols = info.get("symbols", [])

        if symbol:
            symbol = symbol.upper()
            for s in symbols:
                if s.get("symbol") == symbol:
                    return {
                        "symbol": s.get("symbol"),
                        "status": s.get("status"),
                        "base_asset": s.get("baseAsset"),
                        "quote_asset": s.get("quoteAsset"),
                        "price_precision": s.get("pricePrecision"),
                        "quantity_precision": s.get("quantityPrecision"),
                        "filters": s.get("filters"),
                    }
            return {"error": f"Symbol {symbol} not found"}

        # Summary of all pairs
        return [
            {
                "symbol": s.get("symbol"),
                "status": s.get("status"),
                "base": s.get("baseAsset"),
                "quote": s.get("quoteAsset"),
            }
            for s in symbols
            if s.get("status") == "TRADING"
        ]
