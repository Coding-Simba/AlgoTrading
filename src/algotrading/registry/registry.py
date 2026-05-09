"""Strategy registry — append-only.

Per §B.13: a v0.3 strategy may treat the v0.2 OOS partition as clean only if
its rules were registered in this registry **before** the v0.2 OOS query was
run. The registry is therefore the canonical record of when each rule set
came into existence.

This module provides a JSON-Lines (JSONL) backed registry. JSONL is chosen
over CSV because rule definitions can contain newlines and structured
metadata. Each line is a complete `RegistryEntry` record. Lines are never
edited or deleted in place; corrections are appended as new records that
reference the original record's `entry_id`.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class RegistryError(RuntimeError):
    """Raised on registry consistency violations."""


@dataclass(frozen=True)
class RegistryEntry:
    entry_id: str
    registered_at: str  # ISO-8601 with offset
    strategy_version: str
    family: str
    rules_hash: str
    rules: dict[str, Any]
    registered_by: str
    note: str = ""
    supersedes: str | None = None  # entry_id of prior record this corrects

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_jsonl(cls, line: str) -> "RegistryEntry":
        data = json.loads(line)
        return cls(**data)


def _hash_rules(rules: dict[str, Any]) -> str:
    payload = json.dumps(rules, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class StrategyRegistry:
    """Append-only JSONL registry."""

    path: Path
    _cache: list[RegistryEntry] = field(default_factory=list, init=False, repr=False)
    _loaded: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _load(self) -> None:
        if self._loaded:
            return
        self._cache = []
        with self.path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                self._cache.append(RegistryEntry.from_jsonl(line))
        self._loaded = True

    def entries(self) -> list[RegistryEntry]:
        self._load()
        return list(self._cache)

    def find_by_id(self, entry_id: str) -> RegistryEntry | None:
        for e in self.entries():
            if e.entry_id == entry_id:
                return e
        return None

    def latest_for_version(self, strategy_version: str) -> RegistryEntry | None:
        latest: RegistryEntry | None = None
        for e in self.entries():
            if e.strategy_version != strategy_version:
                continue
            # Ties on registered_at are broken by file order (later in file
            # is later in time, since the registry is append-only).
            if latest is None or e.registered_at >= latest.registered_at:
                latest = e
        return latest

    def append(
        self,
        *,
        strategy_version: str,
        family: str,
        rules: dict[str, Any],
        registered_by: str,
        note: str = "",
        supersedes: str | None = None,
        registered_at: str | None = None,
    ) -> RegistryEntry:
        if not strategy_version:
            raise RegistryError("strategy_version is required")
        if not family:
            raise RegistryError("family is required")
        if not registered_by:
            raise RegistryError("registered_by is required")
        if not isinstance(rules, dict) or not rules:
            raise RegistryError("rules must be a non-empty dict")

        if supersedes is not None and self.find_by_id(supersedes) is None:
            raise RegistryError(f"supersedes references unknown entry_id: {supersedes}")

        rules_hash = _hash_rules(rules)
        ts = registered_at or _now_iso()
        ident = hashlib.sha256(f"{ts}|{strategy_version}|{rules_hash}".encode()).hexdigest()[:16]
        entry = RegistryEntry(
            entry_id=ident,
            registered_at=ts,
            strategy_version=strategy_version,
            family=family,
            rules_hash=rules_hash,
            rules=rules,
            registered_by=registered_by,
            note=note,
            supersedes=supersedes,
        )

        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(entry.to_jsonl() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._loaded = False
        return entry

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen_ids: set[str] = set()
        for line_no, entry in enumerate(self.entries(), start=1):
            if entry.entry_id in seen_ids:
                errors.append(f"line {line_no}: duplicate entry_id {entry.entry_id}")
            seen_ids.add(entry.entry_id)
            if _hash_rules(entry.rules) != entry.rules_hash:
                errors.append(f"line {line_no}: rules_hash mismatch for {entry.entry_id}")
            if entry.supersedes and entry.supersedes not in seen_ids:
                errors.append(
                    f"line {line_no}: supersedes {entry.supersedes} not seen earlier"
                )
        return errors


def load_registry(path: str | os.PathLike[str]) -> StrategyRegistry:
    return StrategyRegistry(Path(path))


def iter_versions(entries: Iterable[RegistryEntry]) -> set[str]:
    return {e.strategy_version for e in entries}
