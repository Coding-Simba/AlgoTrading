# `AlgotradingBridge` — NinjaScript AddOn

A minimal, refusing-by-default C# AddOn that lets the Python algo (running
in the same Windows VM) talk to NinjaTrader 8 over a localhost TCP/JSON
socket. The Python adapter that calls into this is
`src/algotrading/broker/ninjascript_bridge_adapter.py`.

> **Status: stub only.** The five SDK seams (`PlaceBracketSeam`,
> `CancelSeam`, `CancelAllSeam`, `PositionsJsonSeam`,
> `FlattenProtectedSeam`) all throw `NotImplementedException`. Order
> dispatch returns `{"error":"not_implemented"}`. Do **not** route a
> live account through this AddOn until the seams are filled and
> Appendix F is signed.

## Files

| File | Purpose |
|---|---|
| `AlgotradingBridge.cs` | The AddOn. Compiles in NT8 as-is. |
| `README.md` (this file) | Deployment and wire-protocol reference. |

## Deploy

1. Copy `AlgotradingBridge.cs` to:
   ```
   Documents\NinjaTrader 8\bin\Custom\AddOns\AlgotradingBridge.cs
   ```
   (on the Windows VM, not the host Mac).
2. In NT8: **Tools → Edit NinjaScript → AddOn**. Open the file and
   compile (F5). The status bar should report 0 errors.
3. Restart NT8.
4. Configure listen host / port / token / default account in the
   AddOn's settings (`Tools → Algotrading Bridge`).
   - Host MUST be `127.0.0.1`, `localhost`, or `::1`. Any other value
     causes the AddOn to refuse to bind.
   - Port: any unused 1024-65535 port.
   - Token: 32+ random bytes (run
     `python -c 'import secrets; print(secrets.token_hex(32))'`).
   - Default account: select the NT account this AddOn is allowed to
     route orders to. The first version routes everything to one
     account.

5. Set the matching environment variables on the Windows VM where
   Python runs:
   ```
   $Env:NT_BRIDGE_HOST     = "127.0.0.1"
   $Env:NT_BRIDGE_PORT     = "<port>"
   $Env:NT_BRIDGE_TOKEN    = "<token>"
   $Env:NT_BRIDGE_ACCOUNT  = "<account name>"
   $Env:NT_BRIDGE_ENV      = "sim"
   ```

6. Smoke test:
   ```
   python -c "from algotrading.broker import NinjaScriptBridgeAdapter; \
              from pathlib import Path; \
              a = NinjaScriptBridgeAdapter.from_env(Path('.')); \
              print(a.base_url())"
   # → tcp://127.0.0.1:<port>
   ```
   Today this prints the URL but every order method still raises
   `BlockedLiveTrading` because the Python adapter is also a stub.

## Wire protocol

JSON line-oriented over TCP. One JSON object per line, terminated with
`\n`. UTF-8 throughout. The AddOn closes the connection on bad JSON
or unauthenticated ops other than `auth`.

### Authentication

First message of every connection must be:
```json
{"op":"auth","token":"<bearer>"}
```
On success: `{"ok":true}`. On failure: `{"error":"auth_failed"}` and
the AddOn closes the socket.

### Inbound ops (Python → AddOn)

| `op` | Required fields | Success response | Failure response |
|---|---|---|---|
| `auth` | `token` | `{"ok":true}` | `{"error":"auth_failed"}` |
| `ping` | — | `{"pong":<epoch_ms>}` | — |
| `place_bracket` | `client_order_id`, `symbol`, `side` ∈ {`buy`,`sell`}, `qty`, `entry_type` ∈ {`market`,`limit`,`stop`}, `entry_price` (null for market), `stop_loss`, `take_profit` | `{"order_id":"..."}` | `{"error":"..."}` |
| `cancel` | `order_id` | `{"cancelled":true}` | `{"error":"..."}` |
| `cancel_all` | — | `{"count":<n>}` | `{"error":"..."}` |
| `positions` | — | `{"positions":{"MES":<int>}}` | `{"error":"..."}` |
| `working` | — | `{"orders":[...]}` | `{"error":"..."}` |
| `flatten_protected` | — | `{"submitted":true}` | `{"error":"..."}` |

Today every non-`ping` op authed past `auth` returns
`{"error":"not_implemented","op":"..."}`.

### Outbound events (AddOn → Python, async after auth)

The same connection used for commands also receives async events on
the same stream. Each event is a JSON object with an `event` field.

| `event` | Fields |
|---|---|
| `fill` | `order_id`, `symbol`, `side`, `qty`, `price`, `ts_ms` |
| `order_state` | `order_id`, `state` ∈ {`accepted`,`working`,`cancelled`,`rejected`,`filled`} |
| `position` | `symbol`, `qty` |
| `account_state` | `daily_pnl`, `daily_loss_limit_hit` (bool), `account_locked` (bool) |

Events are not delivered until after the `auth` handshake.

## Security model

- Loopback bind only. `IsLoopback()` rejects every other address.
- Bearer-token auth on the first message; constant-time comparison.
- One concurrent client at a time.
- Token rotation: change the token in the AddOn config, restart NT8.
  Python adapter reconnects with the new value from
  `NT_BRIDGE_TOKEN`.

## Out of scope (today)

- TLS. Loopback-only means no network attacker reaches the socket
  without first compromising the VM.
- Multi-account routing. The first version routes every order to the
  default account. Multi-account is a CR after Appendix F.
- Multiple concurrent clients. The accept loop is single-threaded.
- Persistent state across NT restarts. The AddOn rebuilds state from
  NT's account on connect.

## When to remove this README warning

When all five SDK seams are implemented, the protected-flatten path
has been exercised in sim, and Appendix F is signed.
