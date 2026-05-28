# asterdex-mcp

Model Context Protocol (MCP) server for [Aster DEX](https://asterdex.com) — a Binance-compatible perpetual futures DEX.

## Features

- **Account** — balance, positions, open orders
- **Trading** — place/cancel/modify orders (market, limit, stop, TP/SL)
- **Market Data** — klines/OHLCV, 24h ticker, orderbook, exchange info
- **Auth** — EIP-712 typed data signing (delegation model)

## Quick Start

```bash
uvx asterdex-mcp
```

### Environment Variables

| Variable | Description |
|---|---|
| `ASTER_PRIVATE_KEY` | Agent wallet private key |
| `ASTER_WALLET` | Main wallet address |
| `ASTER_SIGNER` | Agent wallet address |

## MCP Configuration

```json
{
  "mcpServers": {
    "asterdex": {
      "command": "uvx",
      "args": ["asterdex-mcp"],
      "env": {
        "ASTER_PRIVATE_KEY": "0x...",
        "ASTER_WALLET": "0x...",
        "ASTER_SIGNER": "0x..."
      }
    }
  }
}
```

## Tools

| Tool | Description |
|---|---|
| `get_balance` | Account balance and margin summary |
| `get_positions` | Open positions with PnL |
| `get_open_orders` | Pending orders |
| `place_order` | Place market/limit/stop orders |
| `cancel_order` | Cancel order by ID |
| `cancel_all_orders` | Bulk cancel |
| `get_klines` | OHLCV candle data |
| `get_ticker` | 24h price/volume ticker |
| `get_orderbook` | L2 orderbook depth |
| `get_exchange_info` | Pairs, leverage limits, precision |

## Tech Stack

- Python 3.11+
- [`mcp`](https://github.com/modelcontextprotocol/python-sdk) — MCP Python SDK
- [`kairos-aster-sdk`](https://github.com/Valisthea/kairos-aster-sdk) — Aster DEX API client

## License

MIT
