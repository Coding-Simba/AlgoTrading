# Research Contamination Log

## Purpose

This log records every action that touches strategy parameters, rules, or
validation data during the research phase of a systematic trading strategy.
It exists to make casual curve-fitting visible and uncomfortable.

The log is reviewed by the Risk Reviewer at validation freeze (Week 3 of the
build plan). Strategies whose contamination logs reveal undisclosed
exploration are rejected without further review.

## Files

- `research_contamination_log.csv` — the data file. Append-only. Header row +
  data rows. No comments inside the CSV.
- `README.md` — this file. Field definitions, conventions, examples.

## Append-only rule

Rows are never edited or deleted in place. Corrections are appended as new
rows whose `description` field references the original row's `datetime_iso`
and `researcher`.

Example correction row:

```
2026-05-12T14:30:00-04:00,j_smith,v0.2,other,"Correction to row 2026-05-10T09:15:00-04:00 by j_smith: dataset_used was incorrectly recorded as training; actual dataset was validation. This is a contamination event escalated to risk reviewer.",none,N/A,escalated,,
```

## Field definitions

| Field              | Description                                  | Allowed values / format                                                                       |
| ------------------ | -------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `datetime_iso`     | Local timestamp of the action                | ISO-8601 with timezone offset, e.g. `2026-05-09T14:32:00-04:00`                               |
| `researcher`       | Named person performing the action           | Identifier (e.g., `j_smith`) — do not use display names                                       |
| `strategy_version` | Which strategy and variant                   | e.g., `v0.2`, `v0.2-exploratory-3`                                                            |
| `action_type`      | What kind of action                          | `parameter_change` \| `rule_change` \| `variant_tested` \| `validation_query` \| `data_qa_check` \| `other` |
| `description`      | What was done and why                        | Free text. Quote any specific parameter changes.                                              |
| `dataset_used`     | Which dataset partition was queried          | `training` \| `validation` \| `live` \| `paper` \| `none`                                     |
| `result_observed`  | Brief summary of what was seen               | Free text. Numeric where applicable (e.g., `OOS expectancy = +0.07R`).                        |
| `decision`         | What was done with the result                | `kept` \| `discarded` \| `logged_for_next_version` \| `escalated`                             |
| `reviewer_initials`| Risk reviewer initials at periodic review    | Filled by reviewer, not researcher                                                            |
| `reviewer_date`    | Date of risk reviewer pass                   | ISO-8601 date, filled by reviewer                                                            |

## CSV escaping (RFC 4180)

Fields containing commas, quotes, or newlines must be quoted with double
quotes. Embedded double quotes are doubled.

```
2026-05-09T14:32:00-04:00,j_smith,v0.2,parameter_change,"Tested ATR threshold values 1.0, 1.25, and 1.5. Settled on 1.5 per spec.",training,"All produced positive expectancy on training; 1.5 was largest sample.",kept,,
```

## Validation queries

Any query against the validation dataset is logged. There is no such thing as
a "small peek." Logs that show validation queries before the documented Week
3 freeze step are evidence of contamination and result in strategy
rejection.

## What does NOT need to be logged

- Reading raw market data or session calendars
- Running unit tests on the backtest engine, fill model, or operational controls
- Reading the strategy spec
- Running baselines on training data (logged at the strategy-version level
  once, not per execution)

## What DOES need to be logged

- Any change to a parameter value the spec leaves locked
- Any change to a rule
- Any new variant tested (even if discarded)
- Any query against validation data
- Any data-QA correction that affects training or validation rows

## Ownership

The log is owned by the Strategy Owner. The Risk Reviewer audits it at every
gate review. Engineers and researchers append entries. No one deletes entries.

## Tooling

`src/algotrading/contamination/` provides:

- `ContaminationLog` — append-only writer with RFC 4180 escaping.
- `validate_log()` — schema check used by the contamination test in CI.
- `enforce_no_validation_before_freeze()` — Week-3-freeze guard called by the
  validation harness before any partition labelled `validation` is opened.
