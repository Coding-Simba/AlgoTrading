# Day 0 Procurement Checklist

**Issued:** 2026-05-09
**Owner:** Ops (with Director Sponsor cc on every external request)
**Rule:** All requests are sent same-day. Vendor responses are stored under
`docs/vendor-replies/` (gitignored if NDA-restricted; metadata stub only
otherwise). No backtest pass/fail uses placeholder costs (errata §5).

## Outbound requests — Day 0

- [ ] Broker rate sheet — commission, exchange, clearing, NFA, platform / routing fees.
- [ ] Written confirmation of OCO residence — server / exchange / platform-local — with redundancy and failure modes.
- [ ] Written confirmation of disconnect behaviour — what happens to working
      orders, OCO pairs, and stops on TCP / session loss; reconnect semantics.
- [ ] Primary data vendor — historical MES tick + BBO availability, history
      depth, gap policy, corporate-action handling.
- [ ] Secondary data vendor — identify a second source for cross-checks. Must
      be independent of primary (different upstream feed if possible).
- [ ] Economic-calendar provider of record — release-time precision, revisions
      policy, change history.

## Internal lock — Day 0

- [ ] Lock training / validation / final-holdback date ranges per §C.9. File:
      `configs/data_partitions.yml`. Once committed, edits require a Change
      Request.

## Definition of done for procurement

A request is "sent" only when:

1. The outbound message is on file with timestamp + recipient.
2. Vendor reply ETA is logged.
3. The reply (or its metadata stub) is committed under
   `docs/vendor-replies/<vendor>-<topic>.md`.

Until all six outbound requests above are sent, **no v0.2 backtest may be
approved**, even if pre-code sign-off otherwise passes (errata §5).

## Tracking

| Item                    | Sent date | Vendor    | Reply received | Reply file |
| ----------------------- | --------- | --------- | -------------- | ---------- |
| Broker rate sheet       |           |           |                |            |
| OCO residence confirm   |           |           |                |            |
| Disconnect behaviour    |           |           |                |            |
| Primary MES tick + BBO  |           |           |                |            |
| Secondary data vendor   |           |           |                |            |
| Economic calendar       |           |           |                |            |
| Partition lock (§C.9)   |           | internal  |                |            |
