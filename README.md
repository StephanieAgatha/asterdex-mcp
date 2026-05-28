# asterdex-mcp

[![PyPI version](https://img.shields.io/pypi/v/asterdex-mcp)](https://pypi.org/project/asterdex-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Model Context Protocol (MCP) server for [Aster DEX](https://asterdex.com) — a Binance-compatible perpetual futures DEX on-chain.

## Features

- **Account** — balance, positions, open orders
- **Trading** — place/cancel/modify orders (market, limit, stop, TP/SL)
- **Market Data** — klines/OHLCV, 24h ticker, orderbook, exchange info
- **Analysis** — RSI, MACD, Stochastic, EMA, Bollinger Bands, signals
- **Auth** — EIP-712 typed data signing (delegation model)

## Quick Start

```bash
# Using uvx (recommended — no install needed)
uvx asterdex-mcp

# Or install globally
pip install asterdex-mcp
```

## Wallet Setup Guide

Aster DEX uses a **delegation model** with two wallets:

| Wallet | What it is | Purpose |
|---|---|---|
| **Main Wallet** | Your primary wallet (e.g. MetaMask) | Holds funds, manages API permissions |
| **Agent Wallet** | A separate wallet for automation | Signs trades on your behalf |

### Step 1: Create an Agent Wallet

Generate a new Ethereum-compatible wallet for the agent. This wallet will sign transactions but **never holds funds**.

```bash
# Using ethers.js / viem / any wallet generator
# Or use this quick Python snippet:
python3 -c "
from eth_account import Account
acct = Account.create()
print(f'Address: {acct.address}')
print(f'Private Key: {acct.key.hex()}')
"
```

Save the output — you'll need both the **address** and **private key**.

### Step 2: Set Up API Access on Aster

1. Go to [Aster DEX](https://asterdex.com) and connect your **main wallet**
2. Navigate to **Settings** → **API Management**
3. Click **Create API Key**
4. Enter your **agent wallet address** when prompted
5. **Important:** Enable the following permissions:
   - ✅ Perps Trading (required for placing orders)
   - ✅ Enable IP restriction (recommended for security)
6. Whitelist your server/agent IP address
7. Confirm and sign the transaction from your main wallet

### Step 3: Get Your Credentials

You need three values:

```
ASTER_WALLET=0x...    # Your main wallet address (the one on Aster)
ASTER_SIGNER=0x...    # Your agent wallet address (from Step 1)
ASTER_PRIVATE_KEY=0x...  # Your agent wallet private key (from Step 1)
```

> ⚠️ **Never share your private key.** The agent wallet should have NO funds — it only signs messages.

### Step 4: Install & Configure

#### Claude Code

```bash
# Add the MCP server
claude mcp add asterdex -- uvx asterdex-mcp \
  -e ASTER_PRIVATE_KEY=0xYOUR_AGENT_PRIVATE_KEY \
  -e ASTER_WALLET=0xYOUR_MAIN_WALLET_ADDRESS \
  -e ASTER_SIGNER=0xYOUR_AGENT_WALLET_ADDRESS
```

Verify with:
```bash
claude mcp list
```

#### OpenClaw

Add to your OpenClaw MCP config (`~/.openclaw/mcp.json` or project-level):

```json
{
  "mcpServers": {
    "asterdex": {
      "command": "uvx",
      "args": ["asterdex-mcp"],
      "env": {
        "ASTER_PRIVATE_KEY": "0xYOUR_AGENT_PRIVATE_KEY",
        "ASTER_WALLET": "0xYOUR_MAIN_WALLET_ADDRESS",
        "ASTER_SIGNER": "0xYOUR_AGENT_WALLET_ADDRESS"
      }
    }
  }
}
```

#### Hermes Agent

Add to `~/.hermes/config.yaml` under `mcp_servers`:

```yaml
mcp_servers:
  asterdex:
    command: uvx
    args:
    - asterdex-mcp
    env:
      ASTER_PRIVATE_KEY: '0xYOUR_AGENT_PRIVATE_KEY'
      ASTER_WALLET: '0xYOUR_MAIN_WALLET_ADDRESS'
      ASTER_SIGNER: '0xYOUR_AGENT_WALLET_ADDRESS'
    enabled: true
    timeout: 30
```

Then restart: `hermes gateway restart`

#### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "asterdex": {
      "command": "uvx",
      "args": ["asterdex-mcp"],
      "env": {
        "ASTER_PRIVATE_KEY": "0xYOUR_AGENT_PRIVATE_KEY",
        "ASTER_WALLET": "0xYOUR_MAIN_WALLET_ADDRESS",
        "ASTER_SIGNER": "0xYOUR_AGENT_WALLET_ADDRESS"
      }
    }
  }
}
```

#### Cursor

Add to `.cursor/mcp.json` in your project root (or `~/.cursor/mcp.json` globally):

```json
{
  "mcpServers": {
    "asterdex": {
      "command": "uvx",
      "args": ["asterdex-mcp"],
      "env": {
        "ASTER_PRIVATE_KEY": "0xYOUR_AGENT_PRIVATE_KEY",
        "ASTER_WALLET": "0xYOUR_MAIN_WALLET_ADDRESS",
        "ASTER_SIGNER": "0xYOUR_AGENT_WALLET_ADDRESS"
      }
    }
  }
}
```

### Step 5: Verify

Ask your AI agent to run `get_balance` — if it returns your USDT balance, you're good to go.

## Tools

| Tool | Description |
|---|---|
| `get_balance` | Account balance and margin summary |
| `get_positions` | Open positions with PnL |
| `get_open_orders` | Pending orders (optional symbol filter) |
| `place_order` | Place market/limit/stop/TP/SL orders |
| `cancel_order` | Cancel order by ID |
| `cancel_all_orders` | Bulk cancel all open orders |
| `set_leverage` | Set leverage per trading pair |
| `get_exchange_info` | Pairs, precision, leverage limits |

## Examples

See [examples.md](examples.md) for natural language prompting examples — account, analysis, trading, and combined workflows.

## How Auth Works

Aster DEX uses **EIP-712 typed data signing** (same as Hyperliquid). Instead of API keys with HMAC:

1. Your **agent wallet** signs each request with EIP-712
2. Aster verifies the signature against the **signer address** you registered
3. The **main wallet** is included in the signed data so Aster knows whose account to act on

This means:
- No API key/secret pairs to manage
- Agent wallet can't steal funds (it has none)
- You can revoke access anytime from Aster's API settings

## Tech Stack

- Python 3.11+
- [`mcp`](https://github.com/modelcontextprotocol/python-sdk) — MCP Python SDK
- [`kairos-aster-sdk`](https://github.com/Valisthea/kairos-aster-sdk) — Aster DEX API client

## License

MIT
