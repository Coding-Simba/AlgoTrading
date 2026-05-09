# Pre-code reviewer checklist — v1.4-r1

**Status:** Reviewer-facing checklist for the Phase 1 (pre-code) sign-off.
**Issued:** 2026-05-09
**Owner:** Risk Reviewer (counter-signs each appendix sign-off PR per
`docs/OWNERS.md` independence rule).

This checklist is the falsifiable companion to
`docs/signoff/pre_code_signoff_packet.md`. Each item is a concrete,
verifiable check; items beginning "Confirm" require the reviewer to inspect
the cited file or test before ticking the box. **Decline conditions** at
the bottom are mandatory hard stops.

---

## 1. Appendix B — strategy specification & registry rules

Signer role: Director Sponsor. Independent ack: Risk Reviewer.

1. [ ] Confirm the strategy registry is append-only and content-addressed
       (cite `src/algotrading/registry/registry.py:111-157`,
       `entry_id` derived from `(timestamp, version, rules_hash)`).
2. [ ] Confirm the registry validator detects rules-hash mismatches and
       supersedes-cycle errors (cite
       `tests/test_registry.py:test_rules_hash_change_detected`,
       `tests/test_registry.py:test_supersedes_must_reference_known_id`).
3. [ ] Confirm the §B.13 registry-first rule is documented as canonical
       over §C.9 in `docs/v1.4r1_errata_and_kickoff.md` §6, and that the
       appendix B sign-off block explicitly references it.
4. [ ] Confirm the v0.2 locked parameter set in
       `docs/appendices/B_strategy_spec_v0_2.md` is unambiguous — every
       parameter has a value or an explicit "Director-set" pointer.
5. [ ] Confirm `tests/test_sprint1_freeze.py` still rejects forbidden
       symbols (`b7_entry`, `b8_entry`, `compute_ema_signal`,
       `compute_vwap_signal`, `compute_atr_signal`, `V0_2*Strategy`).
6. [ ] Confirm no entry in the live registry file already carries
       `strategy_version` containing `v0.2` (registry must be empty of
       v0.2 records before code lands).

## 2. Appendix C — data partition & contamination protocol

Signer role: Risk Reviewer.

1. [ ] Confirm `configs/data_partitions.yml` has non-empty start/end ISO
       dates for training, validation, and final_holdback (cite
       `src/algotrading/contamination/enforcement.py:is_partition_lock_signed`).
2. [ ] Confirm the three partitions do not overlap (validate by date
       arithmetic; final_holdback.start > validation.end > training.end).
3. [ ] Confirm the contamination log header matches the documented schema
       (cite `src/algotrading/contamination/log.py:HEADER` and
       `docs/research_contamination_log/README.md` field table).
4. [ ] Confirm the partition guard rejects unsigned locks (cite
       `tests/test_contamination.py:test_partition_lock_unsigned_blocks_validation`).
5. [ ] Confirm the partition guard rejects signed locks lacking a
       validation_freeze event (cite
       `tests/test_contamination.py:test_signed_lock_without_freeze_event_blocks`).
6. [ ] Confirm vendor selection criteria for primary and independent
       secondary feeds are written in
       `docs/appendices/C_data_qa_partitioning.md` and that the
       Day-0 outbound-request rows in `docs/PROCUREMENT.md` for primary
       MES and secondary data have been sent (date filled in the table).
7. [ ] Confirm the §B.13 deference clause is reproduced verbatim in
       Appendix C wherever §C.9 is invoked.

## 3. Appendix D — fill model

Signer role: Engineering. Counter-sign: Risk Reviewer (independence).

1. [ ] Confirm stop-trigger is gated on print-through, not quote-touch
       (cite `src/algotrading/fillmodel/model.py:120-127`,
       `tests/test_fillmodel.py:test_stop_triggered_on_print_through`).
2. [ ] Confirm the fill model rejects bracket bars where high >= target
       AND low <= stop with `ambiguous_collision=True` and records the
       worst-case (stop-loss) outcome (cite
       `src/algotrading/fillmodel/model.py:140-184`,
       `tests/test_fillmodel.py:test_intrabar_collision_marked_ambiguous_and_uses_stop`).
3. [ ] Confirm the placeholder cost tag is the literal `D2_PLACEHOLDER`
       (cite `src/algotrading/fillmodel/model.py:29` and
       `docs/GATES.md` "broker rate sheet" row CI clause).
4. [ ] Confirm `FillResult.is_placeholder()` returns True whenever the
       result was produced with `PlaceholderCosts` (cite
       `src/algotrading/fillmodel/model.py:83-84`,
       `tests/test_fillmodel.py:test_costs_none_disables_placeholder_tag`).
5. [ ] Confirm `commission_per_side_ticks` and `slippage_ticks` are
       integer tick counts (not currency) so the broker rate sheet
       substitution is a type-preserving change (cite
       `src/algotrading/fillmodel/model.py:67-68`).
6. [ ] Confirm no approved backtest output, research report, or pass/fail
       evaluation file in the repo currently carries the
       `D2_PLACEHOLDER` marker (errata §5).

## 4. Appendix E — validation, paper, and live transition criteria

Signer role: Quant. Counter-sign: Risk Reviewer.

1. [ ] Confirm gate thresholds (expectancy floor, max drawdown ceiling,
       win-rate floor, trade-count floor) are written down with numeric
       values in `docs/appendices/E_quant_gates.md` §5.
2. [ ] Confirm the final-holdback partition has a documented trade-count
       requirement and the chosen training/validation/final_holdback
       ranges in `configs/data_partitions.yml` are wide enough to satisfy
       it under realistic per-day trade rates (cross-check with §C.9
       lock).
3. [ ] Confirm the OOS partition is read-once per strategy version (no
       multi-pass loop in any baseline runner;
       `src/algotrading/baselines/` does not import
       validation/final_holdback paths).
4. [ ] Confirm the §B.13 registry-first rule is mirrored in §E (any v0.3
       claim of OOS cleanliness pivots on registry timestamp, not §C.9
       wording).
5. [ ] Confirm the Quant signer is not also the Risk Reviewer for this
       family (`docs/OWNERS.md` independence rule).
6. [ ] Confirm baselines (random, drift-matched random, reversed signal,
       session-exposure) do not import EMA / VWAP / ATR helpers (cite
       `tests/test_sprint1_freeze.py:test_baselines_module_does_not_import_indicators`).

## 5. Appendix H — order state machine

Signer role: Engineering. Counter-sign: Risk Reviewer.

1. [ ] Confirm the allowed-transition table forbids any transition out of
       a terminal state (cite
       `src/algotrading/orders/state_machine.py:36-59`,
       `tests/test_orders.py:test_cannot_transition_from_terminal`).
2. [ ] Confirm the ack-before-submit and overfill paths raise
       `OrderStateError` (cite
       `tests/test_orders.py:test_invalid_transition_ack_before_submit`,
       `tests/test_orders.py:test_overfill_rejected`).
3. [ ] Confirm partial-fill -> filled accumulation is correct and that
       `OrderRecord.history` records every transition with timestamp
       (cite `src/algotrading/orders/state_machine.py:108-119`,
       `tests/test_orders.py:test_history_recorded`).
4. [ ] Confirm `LatencyMonitor` emits `critical` on negative latency and
       graduates `warn` -> `critical` at the configured thresholds (cite
       `src/algotrading/monitoring/latency.py:39-52`,
       `tests/test_monitoring.py:test_latency_warn_and_critical`,
       `tests/test_monitoring.py:test_latency_negative_alerts_critical`).
5. [ ] Confirm `ClockDriftMonitor` thresholds are documented in
       `docs/appendices/H_execution_ops.md` and match the constants in
       `src/algotrading/monitoring/latency.py:65-69` (1ms warn, 10ms
       critical).
6. [ ] Confirm OCO residence (server / exchange / platform-local) and
       disconnect-behaviour requests in `docs/PROCUREMENT.md` have been
       sent — Appendix H does not require the replies to be in hand, but
       the requests must be on file.

## 6. Director-set values

Six numeric values populated via `docs/signoff/director_values_template.md`
and copied into `configs/risk_limits.yml`. Each item below is a sanity
check the reviewer performs **before** the Director Sponsor signs.

1. [ ] Confirm all six fields in `configs/risk_limits.yml` are populated
       with non-empty values:
       `allocated_capital_usd`,
       `max_oos_drawdown_pct`,
       `max_acceptable_losing_streak`,
       `daily_loss_limit_usd`,
       `aggregate_program_drawdown_limit_pct`,
       `risk_of_ruin_threshold_pct`.
2. [ ] Confirm `daily_loss_limit_usd` is strictly less than
       `aggregate_program_drawdown_limit_pct * allocated_capital_usd /
       100`.
3. [ ] Confirm `max_oos_drawdown_pct <=
       aggregate_program_drawdown_limit_pct`.
4. [ ] Confirm `risk_of_ruin_threshold_pct` is consistent with
       `allocated_capital_usd` and `aggregate_program_drawdown_limit_pct`
       — the analytical ROR computed from the proposed sizing rule at the
       planned losing-streak length lies under the threshold.
5. [ ] Confirm `max_acceptable_losing_streak` is consistent with the
       position-sizing rule.
6. [ ] Confirm `signed_by` differs from the Risk Reviewer named in
       `docs/OWNERS.md` (independence rule).
7. [ ] Confirm `signed_at_iso` is ISO-8601 with timezone offset, and
       that `locked: true`.

## 7. Three-partition date ranges

1. [ ] Confirm no overlap between training, validation, and
       final_holdback ranges.
2. [ ] Confirm the final_holdback range is wide enough to meet the
       trade-count requirement documented in
       `docs/appendices/E_quant_gates.md` §5 under expected per-day trade
       rates for the v0.2 family.
3. [ ] Confirm MES history depth from the primary vendor reply actually
       covers the chosen training start date. If MES history is
       insufficient, confirm the ES-proxy rule is invoked.
4. [ ] Confirm `locked: true`, `locked_by`, and `locked_at_iso` are
       populated and that
       `src/algotrading/contamination/enforcement.py:is_partition_lock_signed`
       returns True for the file.
5. [ ] Confirm the §B.13 registry-first ack is recorded in the Appendix
       B sign-off block.

## 8. Decline conditions (mandatory)

The reviewer **must decline to sign** if any of the following are true:

1. Any field in `configs/data_partitions.yml` is still a placeholder.
2. Any field in `configs/risk_limits.yml` is empty or `locked: false`.
3. Any approved backtest output, research report, or pass/fail
   evaluation in the repo carries the literal `D2_PLACEHOLDER` marker.
4. The Risk Reviewer named in `docs/OWNERS.md` also appears as the
   Engineering, Quant, or Director Sponsor on this family.
5. Any v0.2 entry exists in the live strategy registry file before all
   five appendix sign-off rows are `signed: true`.
6. Any forbidden symbol detected by `tests/test_sprint1_freeze.py` is
   present in `src/`.
7. External or client capital is in scope but Appendix I has not been
   signed by Legal (errata §4).
8. The contamination log shows a `validation_query` event prior to the
   documented validation-freeze step.
9. The §C.9 lock and the §B.13 registry-first rule have not both been
   acknowledged in writing on the sign-off PR.
10. Any vendor reply file flags an unresolved data-quality risk that
    affects the locked partition ranges.

If any decline condition fires, the reviewer leaves all signature blocks
empty, records the reason in the contamination log as an `other` event,
and notifies the Director Sponsor. The gate state remains "Now" and v0.2
strategy code remains FORBIDDEN.

*End of pre-code reviewer checklist.*
