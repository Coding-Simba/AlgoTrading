# NinjaTrader integration design

Status: design only. Drives Appendix F sign-off and the live broker
adapter implementation. **No live trading code ships from this doc** —
the live adapter remains a refusing stub until the prerequisites here
are satisfied and Appendix F is signed.

## TL;DR

- **Broker:** NinjaTrader Brokerage (parent: NinjaTrader Group).
- **API:** Tradovate REST + WebSocket (Tradovate is the actual order-routing
  platform under NT Brokerage post-2022 acquisition).
- **Adapter file:** `src/algotrading/broker/tradovate_adapter.py` (stub).
- **Rate sheet:** `configs/broker_rate_sheet.yml` (unsigned).
- **Plan tier:** Free plan (no monthly fee, $0.39/side commission on MES).
- **OS constraint:** None for the algo (Python/Linux). Operator must
  also have a Windows or macOS machine for the NinjaTrader desktop UI
  to manage account-level controls and review fills out-of-band.

## Why Tradovate, not NinjaScript

NinjaTrader's primary scripting surface is **NinjaScript** — C# inside
the NinjaTrader 8 desktop app on Windows. The codebase here is Python on
Linux. To make Python the source of truth for order intent we need a
network-accessible API. Four options were considered:

| Path | Native to Linux/Python | Cost | Maturity | Selected |
|---|---|---|---|---|
| Tradovate REST + WebSocket | yes | free with NT Brokerage account | production | **YES** |
| NinjaTrader Web API (newer) | yes | free | thin docs, partial coverage | no |
| CrossTrade REST bridge | no (NT8 desktop required) | ~$15-30/mo | mature third-party | no |
| Custom NinjaScript socket bridge | no (NT8 desktop required) | free | engineering work | no |

Tradovate wins because:
1. It runs from Linux/Python natively. No Windows VM, no addon, no
   subscription beyond the brokerage account.
2. NT Brokerage orders route through Tradovate already, so there is no
   feature gap vs. NinjaScript for the operations this strategy needs
   (market / limit / stop / OCO / cancel / position query).
3. OAuth2 client-credentials flow gives clean key isolation suitable for
   `account_controls_configured` (one of the six conditions in
   `assert_live_unblocked`).

## Account & API setup (Operator runbook)

Until each step below is done, the gate stays BLOCKED.

1. Open a NinjaTrader Brokerage account (free plan; minimum funding
   matches the $1,000 figure in `configs/risk_limits.yml`).
2. Request Tradovate API access for the same account. NT support
   provisions an OAuth2 application: `client_id`, `client_secret`, and a
   `name` field for the app.
3. Enable the **Demo** environment first (`demo.tradovateapi.com`).
   Live (`live.tradovateapi.com`) is a separate URL that must NOT be
   used until paper trading passes per Appendix E.
4. Confirm the account permissions: market data subscription for CME
   E-mini Equity (covers MES), order entry, position queries.
5. Configure account-level controls inside the NinjaTrader desktop app:
   - Daily loss limit: $90 (matches `configs/risk_limits.yml`).
   - Max position size: 1 contract per the v0.2 §B spec.
   - Trailing max drawdown: $200 (matches the 20% aggregate ceiling).
   These are belt-and-braces: the algo enforces them in code, but the
   broker-side controls are independent and survive an algo bug.
6. Capture credentials in the operator's secret store. They never enter
   the repo. The adapter reads them from environment variables:
   - `TRADOVATE_CLIENT_ID`
   - `TRADOVATE_CLIENT_SECRET`
   - `TRADOVATE_USERNAME`
   - `TRADOVATE_PASSWORD`
   - `TRADOVATE_APP_NAME`
   - `TRADOVATE_ENV` ∈ {`demo`, `live`}

## Order types & OCO

The v0.2 strategy needs market entry + bracket (stop-loss + take-profit)
exit. Three things to know:

1. **Tradovate native OCO** is supported via `placeOSO` (Order Sends
   Order) and `placeOCO` (One-Cancels-Other). Use `placeOSO` for entry
   so that fill of the parent triggers the OCO bracket children.
2. **NinjaScript-side `AtmStrategyCreate` cannot chain OCO with entry
   orders**; that limitation belongs to the desktop UI path, not the
   Tradovate API path. We are not constrained by it.
3. **Protected flatten** (Appendix H §1.e) is implemented by sending a
   market order with the `isAutomated: false` flag, so the operator
   can also manually flatten from the desktop UI without confusing the
   reconciliation loop.

## Reconciliation loop

The Tradovate WebSocket stream is the source of truth for fills,
positions, and order state. The adapter:
1. Subscribes to `user/syncrequest` on connect to seed state.
2. Subscribes to `user/orders`, `user/fills`, `user/positions` for
   incremental updates.
3. Reconciles every 1s by re-issuing `position/list` and comparing to
   the in-memory mirror; any divergence triggers a protected flatten
   and a hard stop.

## Cost-model wiring

`src/algotrading/fillmodel/rate_sheet_costs.py` will load
`configs/broker_rate_sheet.yml` and emit fills with `cost_tag=""` (no
`D2_PLACEHOLDER`) once the rate sheet is signed. Until then the gate
stays BLOCKED on placeholder costs (errata §5).

## Open questions before Appendix F can be signed

- [ ] Is the operator's NT Brokerage account actually Tradovate-routed?
      (Confirm with NT support; not all sub-products are.)
- [ ] Demo-environment soak test: 1,000 simulated round-trips with no
      reconciliation divergence.
- [ ] Slippage calibration: capture observed slippage on demo for at
      least 100 fills and update `configs/broker_rate_sheet.yml`'s
      `slippage.ticks_per_side` if the empirical value differs.
- [ ] Account-controls evidence: screenshot or API-confirmed read of
      the daily-loss-limit, max-position, and trailing-drawdown caps,
      attached to the Appendix F sign-off PR.
- [ ] OCO failure-mode test: kill the WebSocket mid-bracket and confirm
      the protected-flatten path runs.
- [ ] Two-key live-enable: confirm the live-enable flag requires both
      the algo-side `explicit_live_enable_flag=True` AND a
      broker-side credential rotation that is intentionally rotated
      out at the end of every paper-trading day.

## What does NOT change in this design

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
- Tradovate Developer Documentation (`developer.tradovate.com`).
- NinjaTrader Developer Community API page.
- CrossTrade NT8 REST API blog (for the rejected option's tradeoffs).
