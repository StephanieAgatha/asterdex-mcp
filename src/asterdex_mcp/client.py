"""Aster DEX API client wrapper using kairos-aster-sdk."""

import os
from typing import Any

from .sdk import FuturesClient


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
        self._require_auth()
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
        self._require_auth()
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
        self._require_auth()
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
        self._require_auth()
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
        self._require_auth()
        result = self.client.cancel_order(symbol=symbol.upper(), orderId=order_id)
        return {
            "order_id": result.get("orderId"),
            "symbol": result.get("symbol"),
            "status": result.get("status"),
            "message": "Order cancelled",
        }

    def cancel_all_orders(self, symbol: str | None = None) -> dict[str, Any]:
        """Cancel all open orders."""
        self._require_auth()
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
        self._require_auth()
        result = self.client.set_leverage(symbol=symbol.upper(), leverage=leverage)
        return {
            "symbol": result.get("symbol", symbol.upper()),
            "leverage": result.get("leverage", leverage),
            "max_notional": result.get("maxNotionalValue"),
        }

    def get_account_info(self) -> dict[str, Any]:
        """Full account info with join margin."""
        self._require_auth()
        return self.client.account_with_join_margin()

    def get_position_margin_history(
        self, symbol: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """History of margin changes for a position."""
        self._require_auth()
        return self.client.position_margin_history(symbol.upper(), limit)

    def modify_order(
        self,
        symbol: str,
        order_id: int,
        price: str = "",
        quantity: str = "",
    ) -> dict[str, Any]:
        """Modify an existing LIMIT order."""
        self._require_auth()
        result = self.client.modify_order(
            symbol=symbol.upper(),
            order_id=order_id,
            quantity=quantity or None,
            price=price or None,
        )
        return {
            "order_id": result.get("orderId"),
            "symbol": result.get("symbol"),
            "status": result.get("status"),
            "price": result.get("price"),
            "quantity": result.get("origQty"),
            "message": "Order modified",
        }

    def place_chase_order(
        self,
        symbol: str,
        side: str,
        quantity: str,
        quantity_unit: str = "BASE",
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """Place a BBO-pegged chase order."""
        self._require_auth()
        result = self.client.chase_order(
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            quantity_unit=quantity_unit,
            time_in_force=time_in_force,
        )
        return {
            "strategy_id": result.get("strategyId"),
            "symbol": result.get("symbol"),
            "side": result.get("side"),
            "quantity": result.get("quantity"),
            "status": result.get("strategyStatus"),
            "chase_offset": result.get("chaseOffset"),
            "price_limit": result.get("priceLimit"),
        }

    def cancel_chase_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel a chase order (uses standard cancel)."""
        self._require_auth()
        result = self.client.cancel_order(symbol=symbol.upper(), orderId=order_id)
        return {
            "order_id": result.get("orderId"),
            "symbol": result.get("symbol"),
            "status": result.get("status"),
            "message": "Chase order cancelled",
        }

    def noop(self) -> dict[str, Any]:
        """Cancel in-flight transactions."""
        self._require_auth()
        return self.client.noop()

    def set_stp_mode(self, stp_mode: str) -> dict[str, Any]:
        """Set Self-Trade Prevention mode."""
        self._require_auth()
        return self.client.set_stp_mode(stp_mode)

    def get_stp_mode(self) -> dict[str, Any]:
        """Get current STP mode."""
        self._require_auth()
        return self.client.get_stp_mode()

    def set_mmp(
        self, window_ms: int, freeze_ms: int, qty_limit: float, delta_limit: float
    ) -> dict[str, Any]:
        """Configure Market Maker Protection."""
        self._require_auth()
        return self.client.set_mmp(window_ms, freeze_ms, qty_limit, delta_limit)

    def get_mmp(self) -> dict[str, Any]:
        """Get MMP config."""
        self._require_auth()
        return self.client.get_mmp()

    def delete_mmp(self) -> dict[str, Any]:
        """Delete MMP config."""
        self._require_auth()
        return self.client.delete_mmp()

    def reset_mmp(self) -> dict[str, Any]:
        """Reset MMP (unfreeze)."""
        self._require_auth()
        return self.client.reset_mmp()

    # ── Market Data ───────────────────────────────────────────────────

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """OHLCV candle data."""
        raw = self.client.klines(symbol=symbol.upper(), interval=interval, limit=limit)
        candles = []
        for k in raw:
            candles.append({
                "open_time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": k[6],
                "quote_volume": float(k[7]),
                "trades": int(k[8]),
            })
        return candles

    def get_ticker(self, symbol: str | None = None) -> Any:
        """24h price/volume ticker."""
        raw = self.client.ticker_24hr(symbol=symbol.upper() if symbol else None)
        if isinstance(raw, list):
            return [
                {
                    "symbol": t.get("symbol"),
                    "price": float(t.get("lastPrice", 0)),
                    "change_24h": float(t.get("priceChange", 0)),
                    "change_pct": float(t.get("priceChangePercent", 0)),
                    "high_24h": float(t.get("highPrice", 0)),
                    "low_24h": float(t.get("lowPrice", 0)),
                    "volume": float(t.get("volume", 0)),
                    "quote_volume": float(t.get("quoteVolume", 0)),
                }
                for t in raw
            ]
        return {
            "symbol": raw.get("symbol"),
            "price": float(raw.get("lastPrice", 0)),
            "change_24h": float(raw.get("priceChange", 0)),
            "change_pct": float(raw.get("priceChangePercent", 0)),
            "high_24h": float(raw.get("highPrice", 0)),
            "low_24h": float(raw.get("lowPrice", 0)),
            "volume": float(raw.get("volume", 0)),
            "quote_volume": float(raw.get("quoteVolume", 0)),
        }

    def get_orderbook(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        """L2 orderbook depth."""
        raw = self.client.depth(symbol=symbol.upper(), limit=limit)
        return {
            "symbol": symbol.upper(),
            "bids": [[float(p), float(q)] for p, q in raw.get("bids", [])],
            "asks": [[float(p), float(q)] for p, q in raw.get("asks", [])],
            "bid_count": len(raw.get("bids", [])),
            "ask_count": len(raw.get("asks", [])),
        }

    def get_historical_trades(
        self, symbol: str, limit: int = 50, from_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Old trades lookup."""
        raw = self.client.historical_trades(symbol.upper(), limit, from_id)
        return [
            {
                "id": t.get("id"),
                "price": float(t.get("price", 0)),
                "qty": float(t.get("qty", 0)),
                "time": t.get("time"),
                "is_buyer_maker": t.get("isBuyerMaker"),
            }
            for t in raw
        ]

    def get_index_klines(
        self, pair: str, interval: str = "1h", limit: int = 100
    ) -> list[dict[str, Any]]:
        """Index price kline data."""
        raw = self.client.index_price_klines(pair.upper(), interval, limit)
        return self._parse_klines(raw)

    def get_mark_klines(
        self, symbol: str, interval: str = "1h", limit: int = 100
    ) -> list[dict[str, Any]]:
        """Mark price kline data."""
        raw = self.client.mark_price_klines(symbol.upper(), interval, limit)
        return self._parse_klines(raw)

    def get_funding_info(self, symbol: str = "") -> Any:
        """Funding rate config (interval, cap, floor)."""
        return self.client.funding_info(symbol.upper() if symbol else None)

    def get_index_references(self, symbol: str) -> dict[str, Any]:
        """Index price component exchanges and weights."""
        return self.client.index_references(symbol.upper())

    @staticmethod
    def _parse_klines(raw: list) -> list[dict[str, Any]]:
        candles = []
        for k in raw:
            candles.append({
                "open_time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": k[6],
                "quote_volume": float(k[7]),
                "trades": int(k[8]),
            })
        return candles

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
