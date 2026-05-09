# Gate state machine — v1.4-r1

| State                       | Allowed                                            | Blocked until                                                   |
| --------------------------- | -------------------------------------------------- | --------------------------------------------------------------- |
| Now                         | Framework work per Sprint 1 build order            | —                                                               |
| v0.2 strategy code          | Implementation of B.7 / B.8 rules                  | Pre-code sign-off (Appendices B, C, D, E, H)                    |
| Approved v0.2 backtest      | Research-report-quality backtest runs              | Broker rate sheet replaces §D.2 placeholders                    |
| Validation / OOS query      | One-shot OOS test per strategy version             | Validation freeze (Week 3)                                      |
| Family final-holdback query | Family-level approval                              | OOS pass + holdback partition trade-count threshold met         |
| Paper trading               | Paper-account live execution                       | Appendix F finalized for chosen broker + Appendix I counsel sign-off |
| Small-size live             | Real capital at minimum size                       | Paper gate per §E.3                                             |
| Scale-up                    | Size > 1 MES                                       | Appendix G signed off                                           |

## Pre-code sign-off rows (errata §3)

The FROZEN status applies to: Appendix B, C, D (with placeholder note), E, H.
Subsequent gates are signed at each phase; their unsigned state does not
unfreeze the document and does not block framework engineering.

## Appendix I (errata §4)

- Required before paper or live trading.
- Not required before v0.2 strategy code, **provided** the capital base is
  internal-proprietary only.
- If external / client capital enters scope before strategy code, Appendix I
  becomes a coding prerequisite.

## Broker rate sheet (errata §5)

- Required before any approved v0.2 strategy backtest, validation, or OOS run.
- Not required before framework engineering or fill-model unit tests.
- Placeholder costs in §D.2 are permitted **only** for unit-test scaffolding
  and must never appear in approved backtest output, research reports, or
  pass/fail evaluation. CI fails if a backtest report carries the placeholder
  marker `D2_PLACEHOLDER`.

## §C.9 / §B.13 (errata §6)

§B.13 is canonical. The v0.2 OOS partition is clean for v0.3 only if v0.3
rules were registered in the strategy registry **before** the v0.2 OOS query
was run. Otherwise the v0.2 OOS partition is contaminated for v0.3 and may be
used as a diagnostic comparison only.
