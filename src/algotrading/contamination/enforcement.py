"""Contamination enforcement.

The validation harness must call :func:`enforce_no_validation_before_freeze`
before opening any file or partition labelled ``validation``. This guard
checks two preconditions:

1. The data-partition lock (``configs/data_partitions.yml``) is signed
   (``locked: true`` with ``locked_by`` and ``locked_at_iso`` set).
2. The contamination log records a ``validation_freeze`` event for the
   strategy version about to be queried.

If either is missing the call raises :class:`PartitionLockMissing`.

The guard is intentionally noisy and refuses by default. There is no override
flag — bypassing it requires a Change Request and a code edit reviewed by
the Risk Reviewer.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .log import ContaminationLog, ContaminationError


class PartitionLockMissing(RuntimeError):
    pass


def is_partition_lock_signed(path: str | Path) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return False
    if not raw.get("locked"):
        return False
    if not raw.get("locked_by") or not raw.get("locked_at_iso"):
        return False
    parts = raw.get("partitions") or {}
    for name in ("training", "validation", "final_holdback"):
        p = parts.get(name) or {}
        if not p.get("start") or not p.get("end"):
            return False
    return True


def enforce_no_validation_before_freeze(
    *,
    strategy_version: str,
    partitions_path: str | Path,
    contamination_log_path: str | Path,
) -> None:
    if not is_partition_lock_signed(partitions_path):
        raise PartitionLockMissing(
            f"partition lock at {partitions_path} is not signed; "
            "validation queries are blocked"
        )
    log = ContaminationLog(Path(contamination_log_path))
    try:
        rows = log.read_all()
    except ContaminationError as exc:
        raise PartitionLockMissing(
            f"contamination log unreadable: {exc}"
        ) from exc

    has_freeze = any(
        r.strategy_version == strategy_version
        and r.action_type == "other"
        and "validation_freeze" in r.description.lower()
        for r in rows
    )
    if not has_freeze:
        raise PartitionLockMissing(
            f"no 'validation_freeze' event logged for {strategy_version}; "
            "validation queries are blocked"
        )
