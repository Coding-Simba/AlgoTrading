# Appendix B — Strategy Spec v0.4 (Regime Classifier + Switch)

**Status:** Pre-code sign-off candidate (registered via CR-001 §B.13)  
**Scope:** Rule-based regime classifier + strategy-switch policy  
**Strategy family:** MES_intraday (meta-layer over v0.2 / v0.3)  
**Instrument:** MES  
**Session:** CME RTH only  
**v0.4 generates no trades directly.** It selects which underlying strategy is enabled per regime label.

---

## B_v0.4.1 Purpose

v0.4 is the rule-based regime classifier and strategy-switch policy. It
classifies the current RTH session (or the most recently closed 60m RTH
bar) into one of three labels and selects the active underlying strategy
accordingly:

| Regime label | Active underlying strategy |
|--------------|---------------------------|
| TREND        | v0.2 only                 |
| MEANREV      | v0.3 only                 |
| NEUTRAL      | none (no trades)          |

v0.4 does not consume validation or holdback partitions. Correctness is
verified by unit tests over synthetic regime inputs and by audit of
label transitions over OOS data *after* v0.2 and v0.3 have independently
passed §E gates.

## B_v0.4.2 Inputs

Computed once per closed 60m RTH bar:

- `vol_norm = ATR_5m_14 / EMA_5m_200_close`, evaluated at the most
  recently closed 5m bar within the most recently closed 60m bar.
- `trend_strength = (EMA_60m_50 - EMA_60m_200) / EMA_60m_200`,
  evaluated at the most recently closed 60m bar (signed).
- `vwap_dev = (5m_close - session_VWAP) / ATR_5m_14`, evaluated at
  the most recently closed 5m bar within the most recently closed 60m
  bar (signed; in ATR units).

## B_v0.4.3 Classification rules

Apply in order; first matching rule wins. All thresholds are
spec-locked.

```text
IF |trend_strength| >= 0.0030 AND vol_norm <= 0.0008  -> TREND
IF |trend_strength| <= 0.0010 AND vol_norm <= 0.0008  -> MEANREV
IF |trend_strength| <= 0.0010 AND |vwap_dev| >= 1.5    -> MEANREV
ELSE                                                   -> NEUTRAL
```

Thresholds are static for v0.4. Any change is a parameter change
subject to §B.13 contamination logging.

## B_v0.4.4 Switch policy

```text
TREND   -> active = "v0.2", v0.3 disabled
MEANREV -> active = "v0.3", v0.2 disabled
NEUTRAL -> active = None,   both disabled
```

The runner consults `select_active_strategy(regime_label)` at every 5m
signal-bar close. A regime transition mid-session does not flatten an
already-open position; flatten remains governed by §B.10 (or by the
underlying strategy's stop / target).

## B_v0.4.5 Determinism and timing

v0.4 evaluation is pure: same inputs → same label. Inputs are derived
from already-closed bars only — no peek-ahead.

## B_v0.4.6 No-trade conditions

v0.4 does not bypass §B.8 / B_v0.3.8 no-trade conditions. They apply to
the underlying strategy independently of v0.4's classification.

## B_v0.4.7 Sign-off

| Field                | Value |
| -------------------- | ----- |
| Signed               | false |
| Director Sponsor     | DIR-01 |
| Risk Reviewer        | RISK-01 |
| Signed at ISO        | null |
| Commit hash          | null |
