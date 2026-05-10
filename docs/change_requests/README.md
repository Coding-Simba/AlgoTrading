# Change Requests

Change Requests (CRs) are the canonical mechanism for modifying frozen
specifications, locked governance artifacts, or any value/rule covered by a
sign-off row.

## Conventions

- One file per CR: `CR-NNN_short_title.md`.
- Each CR includes a fenced YAML sign-off block tagged `# CR-NNN SIGNOFFS`
  (see `CR-001_v0.3_v0.4_registration_and_capital.md` for the template).
- Apply scripts live under `tools/` and are named `cr_NNN_apply.py`.
- Apply scripts MUST be idempotent and refuse if preconditions are not met.
- A CR's apply script never executes an action that bypasses governance; it
  only mechanizes actions that the underlying governance permits *once* the
  CR has been countersigned by the appropriate roles.
- The independence rule (docs/OWNERS.md) applies: Director Sponsor and Risk
  Reviewer signer IDs must differ.

## CRs

| Number  | Title                                              | Status                       |
|---------|----------------------------------------------------|------------------------------|
| CR-001  | v0.3 / v0.4 registration + capital scaling target  | Draft, awaiting countersign  |
