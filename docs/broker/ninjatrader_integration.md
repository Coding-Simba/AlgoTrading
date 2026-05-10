# NinjaTrader integration design

Status: design only. Drives Appendix F sign-off and the live broker
adapter implementation. **No live trading code ships from this doc** —
the live adapter remains a refusing stub until the prerequisites here
are satisfied and Appendix F is signed.

## TL;DR

- **Broker:** NinjaTrader Brokerage (parent: NinjaTrader Group).
- **Runtime:** Python codebase runs on Windows 11 in Parallels,
  alongside the NinjaTrader 8 desktop.
- **Bridge:** custom C# **NinjaScript AddOn** named `AlgotradingBridge`
  that listens on a localhost TCP port and translates JSON commands
  into NT8's native `Order` / `Account` API calls.
- **Python adapter:** `src/algotrading/broker/ninjascript_bridge_adapter.py`
  (refusing stub today).
- **C# AddOn skeleton:** `tools/ninjascript_bridge/AlgotradingBridge.cs`
  (refusing stub today).
- **Rate sheet:** `configs/broker_rate_sheet.yml` (unsigned).
- **Plan tier:** Free plan (no monthly fee, $0.39/side commission on MES).

## Why a custom NinjaScript bridge

You're running NT8 desktop on a Windows 11 VM (Parallels). Three real
options were considered:

| Path | Cost (ongoing) | Effort | Selected |
|---|---|---|---|
| Custom NinjaScript AddOn (localhost TCP/JSON) | $0 | one-time C# write (~200-400 LoC) | **YES** |
| CrossTrade REST bridge addon | ~$15-30/mo | low; install + configure | no |
| Tradovate cloud REST/WebSocket | $0 | medium; OAuth flow + WS sync | no |

Why custom wins for this setup:
1. **Zero ongoing cost.** At $1,000 capital, $15/mo of CrossTrade =
   1.5% of capital monthly in tooling alone.
2. **Same machine = lowest latency.** Loopback TCP is microsecond
   round-trip. The reconciliation loop stays cheap.
3. **No third-party in the trade path.** CrossTrade's add-on sees every
   order; Tradovate cloud rewrites them through their own routing.
   Neither is wrong, but a localhost bridge is the smallest blast
   radius.
4. **Total control.** OCO semantics, protected-flatten paths, and the
   reconciliation contract are owned by code we can read.

The Tradovate cloud option is kept as a fallback if the operator later
moves Python off the Windows VM. For now we don't ship adapter code
for it.

## Architecture

```
+--------------------------------------+
|  Windows 11 VM (Parallels)           |
|                                      |
|  +----------------+    TCP/JSON      |
|  | Python algo    | <-------------+  |
|  |  src/algotrad… |  127.0.0.1   |  |
|  +----------------+               v  |
|         ^                  +-----------+
|         |                  | Algotra…  |
|         |   NT8 events     | Bridge    |
|         |   (positions,    | AddOn     |
|         |    fills,        | (C#)      |
|         |    state)        +-----------+
|         |                       |
|         |                       v
|         |                  +-----------+
|         +----------------- | NT8       |
|                            | desktop   |
|                            +-----------+
|                                 |
+---------------------------------|----+
                                  v
                              broker
```

## Wire protocol (Python ↔ AddOn)

JSON line-oriented over TCP. One JSON object per line. Bearer-token
authentication on the first message of every connection; reconnect
required on token rotation.

Inbound (Python → AddOn):

| `op` | Fields | Response |
|---|---|---|
| `auth` | `token` | `{"ok": true}` or `{"error": "auth_failed"}` |
| `place_bracket` | `client_order_id`, `symbol`, `side`, `qty`, `entry_type`, `entry_price`, `stop_loss`, `take_profit` | `{"order_id": "..."}` |
| `cancel` | `order_id` | `{"cancelled": true}` |
| `cancel_all` | — | `{"count": <n>}` |
| `positions` | — | `{"positions": {"MES": <int>}}` |
| `working` | — | `{"orders": [...]}` |
| `flatten_protected` | — | `{"submitted": true}` |
| `ping` | — | `{"pong": <epoch_ms>}` |

Outbound events (AddOn → Python, async after auth):

| Event | Fields |
|---|---|
| `fill` | `order_id`, `symbol`, `side`, `qty`, `price`, `ts_ms` |
| `order_state` | `order_id`, `state` ∈ {`accepted`, `working`, `cancelled`, `rejected`, `filled`} |
| `position` | `symbol`, `qty` |
| `account_state` | `daily_pnl`, `daily_loss_limit_hit`, `account_locked` |

## Account & API setup (Operator runbook)

Until each step below is done, the gate stays BLOCKED.

1. Open a NinjaTrader Brokerage account (free plan; min funding
   matches the $1,000 figure in `configs/risk_limits.yml`).
2. Install NinjaTrader 8 desktop on the Windows 11 VM. Sign in.
3. Build and deploy the `AlgotradingBridge` AddOn:
   - Copy `tools/ninjascript_bridge/AlgotradingBridge.cs` to
     `Documents\NinjaTrader 8\bin\Custom\AddOns\` on the VM.
   - In NT8: Tools → Edit NinjaScript → AddOn → compile.
   - Restart NT8.
4. Configure the AddOn (in NT8: Tools → Algotrading Bridge):
   - Listen host: `127.0.0.1` (DO NOT expose to the network).
   - Listen port: any unused 1024-65535 port (record it).
   - Bearer token: generate 32+ random bytes; record it.
   - Default account: select the NT account to route orders to.
5. Configure account-level controls inside NT8 (independent of the
   bridge — these survive an algo bug):
   - Daily loss limit: $90 (matches `configs/risk_limits.yml`).
   - Max position size: 1 contract per the v0.2 §B spec.
   - Trailing max drawdown: $200 (matches the 20% aggregate ceiling).
6. Capture the bridge config in the operator's secret store. They
   never enter the repo. Python reads them from environment variables:
   - `NT_BRIDGE_HOST`     (must be loopback: `127.0.0.1`, `localhost`, `::1`)
   - `NT_BRIDGE_PORT`     (1024-65535)
   - `NT_BRIDGE_TOKEN`    (32+ bytes, random)
   - `NT_BRIDGE_ACCOUNT`  (NT account name, e.g., `Sim101` or your live label)
   - `NT_BRIDGE_ENV`      (`sim` or `live`)
7. Run `algotrading bridge ping` (CLI, future) to verify the AddOn is
   reachable and the token authenticates.

## Order types & OCO

The v0.2 strategy needs market entry + bracket (stop-loss +
take-profit) exit. The bridge handles this with one `place_bracket`
command. The AddOn implements OCO using NT's **unmanaged** order
approach: it submits the entry, attaches a custom OCO ID to the
stop-loss and take-profit children, and cancels both on either fill.

NT's `AtmStrategyCreate` is intentionally *not* used; ATM strategies
cannot chain OCO with the entry order programmatically. The unmanaged
approach is the official NT pattern for custom OCO.

**Protected flatten** (Appendix H §1.e): the `flatten_protected`
command submits a market order to close any open position AND cancels
all working orders, in that order, with retries. This must work even
if the WebSocket reconciliation loop has stalled.

## Reconciliation loop

The bridge is the source of truth for fills, positions, and order
state. The Python adapter:
1. Subscribes once to the AddOn's event stream after `auth`.
2. Mirrors `position`, `order_state`, and `fill` events into local
   state.
3. Reconciles every 1s by issuing `positions` and comparing to the
   in-memory mirror. Any divergence triggers `flatten_protected` and
   a hard stop.
4. On TCP disconnect, the adapter MUST issue `flatten_protected`
   immediately on reconnect, before resuming any new orders.

## Cost-model wiring

`src/algotrading/fillmodel/rate_sheet_costs.py` loads
`configs/broker_rate_sheet.yml` and emits fills with `cost_tag=""`
(no `D2_PLACEHOLDER`) once the rate sheet is signed. Until then the
gate stays BLOCKED on placeholder costs (errata §5).

## Open questions before Appendix F can be signed

- [ ] C# AddOn implemented to spec (TCP listener + auth + JSON
      protocol + the eight inbound ops).
- [ ] Sim-account soak test: 1,000 simulated round-trips with no
      reconciliation divergence.
- [ ] Slippage calibration: capture observed slippage on sim for at
      least 100 fills and update `configs/broker_rate_sheet.yml`'s
      `slippage.ticks_per_side` if the empirical value differs.
- [ ] Account-controls evidence: screenshot of the NT8 account-level
      controls (daily loss, max pos, trailing DD) attached to the
      Appendix F sign-off PR.
- [ ] OCO failure-mode test: kill NT8 mid-bracket and confirm the
      protected-flatten path runs on next start.
- [ ] Token rotation: confirm the token can be rotated in the AddOn
      and Python reconnects with the new value without leaking the
      old one to disk.
- [ ] Loopback-only enforcement: confirm the bridge refuses to bind
      to non-loopback addresses even if reconfigured. (Defense in
      depth — Parallels VMs sometimes expose ports to the host.)

## What does NOT change

- `configs/risk_limits.yml` ($1,000 capital, $90 daily, etc.) — those
  numbers are upstream of the broker choice.
- `configs/data_partitions.yml` — partition lock is unaffected.
- The pre-code sign-offs (B/C/D/E/H) — already signed; broker choice
  doesn't reopen them.
- The `D2_PLACEHOLDER`-on-by-default behaviour for synthetic runs —
  remains in place; only `RateSheetCosts` produces unflagged fills.

## Sources

- NinjaTrader free-plan futures commission PDF.
- NinjaTrader account & exchange fees page.
- NinjaScript AddOn framework (NT8 Help Guide).
- Reference patterns for NT-Python TCP bridges in the public domain
  (e.g., `CSharpNinja-Python-NinjaTrader8-trading-api-connector` on
  GitHub).
