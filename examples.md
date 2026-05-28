# Prompting Examples

Natural language prompts that work with any MCP-compatible AI agent (Claude, Cursor, Hermes, etc.).

## Account & Portfolio

```
"Check my balance"
"Show my open positions"
"What orders do I have open?"
"Show my TONUSDT orders"
```

## Technical Analysis

```
"Analyze BTC"
"Give me TA on ETH across 4h and 1d"
"Is ZEC oversold? Check 1h and 4h"
"What's the RSI and MACD on SOLUSDT?"
"Scan TON — is it a buy or sell?"
```

## Market Data

```
"Show me BTC price"
"What's the 24h volume on ETHUSDT?"
"Get the orderbook for TONUSDT"
"Show me 4h candles for the last 100 on BTC"
"What pairs are available on Aster?"
```

## Entering Positions

```
"Long BTC with $5 margin at 5x"
"Buy 0.01 BTC at market"
"Market buy ETHUSDT $10 margin 5x leverage"
"Limit buy SOL at $150, quantity 1"
"Open a short on TON with $5 margin at 10x"
```

## Managing Positions

```
"Set stop-loss on my BTC position at $60000"
"Set take-profit on TON at $2.00"
"Cancel all my orders"
"Cancel order 12345 on TONUSDT"
"Change leverage to 10x on BTCUSDT"
```

## Combined Workflows

```
"Analyze ZEC — if it's oversold, enter a long with $5 at 5x and set SL at $500"

"Check my positions, then analyze TON. If RSI is below 35 on 4h, add $5 to my long"

"What's the BTC orderbook looking like? If there's strong bid support, place a limit buy at the bid price"
```

## Tips

- **Be specific with amounts** — "$5 margin at 5x" is clearer than "small position"
- **Mention leverage** — defaults vary, always specify if you care
- **Use natural names** — "BTC" works, you don't need "BTCUSDT" (most agents figure it out)
- **Chain commands** — AI agents can call multiple tools in one request
- **Ask for analysis first** — "analyze then enter" is safer than blind entry
