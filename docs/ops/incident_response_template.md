# Incident Response Template — DRAFT

> **DRAFT — broker placeholder. Paper trading is BLOCKED until this template
> is broker-specific and the supporting runbook (`live_runbook_draft.md`) is
> signed (Appendix F).**

**Status:** DRAFT.
**Owner:** Ops (TBD-OPS — see `docs/OWNERS.md`).
**Issued:** 2026-05-09.

---

## How to use this template

1. On any production incident — meaning any ERROR_HALTED entry, any
   unscheduled trading interruption, any reconciliation mismatch, any
   contamination-log write during a session, or any operator escalation —
   copy this file to `docs/ops/incidents/INC-<YYYYMMDD>-<NNN>.md` and fill
   it in.
2. Fields marked **[fill at detection]** are completed by the on-call who
   detected the incident, in real time.
3. Fields marked **[fill during response]** are completed during the
   response and updated as the timeline progresses.
4. Fields marked **[fill at post-incident review]** are completed at the
   review meeting, not before.
5. The incident is **not closed** until the Risk Reviewer sign-off line at
   the bottom of this template is signed.

This template is itself DRAFT. It is not broker-specific. It must be
re-reviewed once the broker is selected and Appendix F is finalized.

---

## Incident record

### Identification

- Incident ID: **[fill at detection]** (format `INC-<YYYYMMDD>-<NNN>`)
- Detection time (UTC, ns precision if available): **[fill at detection]**
- Detector (human name or monitor name + alert id): **[fill at detection]**
- Reporter (the on-call who opened the record): **[fill at detection]**

### Severity

- Severity: **[fill at detection]** — one of `info` / `warn` / `critical` /
  `page`. See `docs/ops/live_runbook_draft.md` §6 for the ladder.
- Justification for severity: **[fill at detection]**
- Severity revisions (with timestamp and reason):
  **[fill during response]**

### System affected

- System / component: **[fill at detection]** — e.g.
  `orders/state_machine`, `monitoring/latency`, `fillmodel`, broker session,
  market-data session, kill-switch, contamination log.
- Module reference (path in repo): **[fill at detection]**
- Strategy / family / version impacted (or "framework-only"):
  **[fill at detection]**

### Financial impact

- Preliminary impact (USD, order of magnitude): **[fill at detection]**
- Final impact (USD, exact, after reconciliation):
  **[fill at post-incident review]**
- Method used to compute final impact:
  **[fill at post-incident review]**
- Was any external party (broker, exchange, counterparty) asked to bust or
  adjust a fill: **[fill during response]**

### Positions at time of incident

Snapshot the following from the local position log and the broker session
(if reachable) at the incident detection time. If they disagree, record
both.

| Symbol | Local qty | Local avg price | Broker qty | Broker avg price | Note |
| ------ | --------- | --------------- | ---------- | ---------------- | ---- |
|        |           |                 |            |                  |      |

- Working orders at detection time:
  **[fill at detection]**
- Net dollar exposure at detection time:
  **[fill at detection]**

### Actions taken (timeline)

Record every operator action and every system event with a UTC timestamp.
Append-only. Do not edit prior entries; add a follow-up entry if a prior
entry needs correction.

| UTC timestamp | Actor (human or system) | Action / event | Result |
| ------------- | ----------------------- | -------------- | ------ |
|               |                         |                |        |

Required entries (if applicable):

- Time the kill-switch was armed.
- Time the kill-switch was triggered.
- Time the broker session was confirmed flat (working orders = 0,
  positions = 0).
- Time of every page sent and acknowledgement received.
- Time the system was moved to `STANDBY` or `ERROR_HALTED`.
- Time the incident channel was opened and who joined.

### Root cause

**[fill at post-incident review]**

- Proximate cause:
- Contributing causes:
- Was this a known failure mode (linked to a prior incident or design
  document)? If yes, reference:
- Was this a regression of a previously-fixed issue? If yes, reference the
  commit or PR:

### Corrective actions

**[fill at post-incident review]**

For each corrective action, record the owner and the target completion
date. Each corrective action must be tracked to closure separately — this
record only lists them.

| ID | Action | Owner | Target date | Status |
| -- | ------ | ----- | ----------- | ------ |
|    |        |       |             |        |

### Owner

- Incident owner (single named individual, accountable for closure):
  **[fill at detection]**
- Backup: **[fill at detection]**

### Sign-off

- Risk Reviewer name: **[fill at post-incident review]**
- Risk Reviewer sign-off (date + initials):
  **[fill at post-incident review]**
- Director Sponsor ack (required if financial impact crosses the
  TBD threshold or if the incident is `page` severity):
  **[fill at post-incident review]**

The incident is **not closed** until the Risk Reviewer sign-off field is
populated.

---

## Required attachments

Each of the following must be attached (committed under
`docs/ops/incidents/<incident-id>/`) before the post-incident review can
proceed. If an attachment is unavailable, record the reason in the
attachment slot rather than leaving it blank.

- [ ] `order_log.jsonl` — the full local order log covering at least
      30 minutes before to 30 minutes after the incident window.
- [ ] `position_log.jsonl` — local position state snapshots over the same
      window.
- [ ] `monitoring_alerts.jsonl` — every `MonitorAlert` (see
      `src/algotrading/monitoring/latency.py`) emitted during the window,
      including the `info` and `warn` events that may have preceded the
      `critical` / `page`.
- [ ] `broker_session.log` — broker session log covering the window
      (TBD-BROKER format).
- [ ] `contamination_log_excerpt.md` — copy of the relevant contamination
      log entries if the incident touched anything that could have biased
      research data (see `src/algotrading/contamination/log.py`). If not
      relevant, attach a short note saying so.
- [ ] `config_snapshot.tar.gz` — committed config at the incident instant
      (preserved automatically on ERROR_HALTED — see
      `live_runbook_draft.md` §4.2).
- [ ] Reconciliation diff (if a reconciliation mismatch is implicated) —
      see `docs/ops/reconciliation_checklist.md`.

---

## Post-incident review schedule

- The post-incident review **must occur within 5 business days** of the
  incident detection time. Slipping this deadline requires written
  approval from the Director Sponsor and is itself recorded as a process
  finding.
- Required attendees:
  - Engineering (the owner of the affected component, plus the
    Engineering workstream lead — see `docs/OWNERS.md`).
  - Risk Reviewer (independent — must not also be Engineering, Quant, or
    Director Sponsor for this incident, per `docs/OWNERS.md`).
  - Director Sponsor.
- Optional attendees: Quant (if a strategy was impacted), Legal (if a
  legal or regulatory question is open), Ops backup.
- Output of the review:
  - Root cause section above is filled.
  - Corrective actions section is filled with owners and dates.
  - Sign-off section is signed.
  - The runbook, this template, and any other ops documents are updated
    if the incident exposed a gap. Updates are recorded as separate PRs,
    linked from the corrective actions table.

---

## Blocker note

This template is **DRAFT**. Until the broker is selected, Appendix F is
finalized, and Appendix I is signed, this template cannot be used to close
out a real production incident — because no production trading is
permitted. Paper trading is **BLOCKED** per `docs/GATES.md`.
