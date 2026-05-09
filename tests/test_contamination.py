from pathlib import Path

import pytest

from algotrading.contamination import (
    ContaminationError,
    ContaminationLog,
    LogRow,
    PartitionLockMissing,
    enforce_no_validation_before_freeze,
    is_partition_lock_signed,
)


def _row(**overrides) -> LogRow:
    base = dict(
        datetime_iso="2026-05-09T10:00:00-04:00",
        researcher="j_smith",
        strategy_version="v0.2",
        action_type="parameter_change",
        description="set ATR threshold to 1.5",
        dataset_used="training",
        result_observed="positive expectancy",
        decision="kept",
    )
    base.update(overrides)
    return LogRow(**base)


def test_append_creates_header(tmp_path: Path) -> None:
    log = ContaminationLog(tmp_path / "log.csv")
    log.append(_row())
    rows = log.read_all()
    assert len(rows) == 1
    assert rows[0].researcher == "j_smith"


def test_csv_escaping_round_trip(tmp_path: Path) -> None:
    log = ContaminationLog(tmp_path / "log.csv")
    desc = 'tested values 1.0, 1.25, "1.5"\nand discarded'
    log.append(_row(description=desc))
    rows = log.read_all()
    assert rows[0].description == desc


def test_invalid_action_type_rejected() -> None:
    with pytest.raises(ContaminationError):
        _row(action_type="curve_fitting").validate()


def test_invalid_dataset_rejected() -> None:
    with pytest.raises(ContaminationError):
        _row(dataset_used="prod").validate()


def test_partition_lock_unsigned_blocks_validation(tmp_path: Path) -> None:
    parts = tmp_path / "data_partitions.yml"
    parts.write_text(
        "locked: false\nlocked_by: ''\nlocked_at_iso: ''\n"
        "partitions:\n  training: {start: '', end: ''}\n"
        "  validation: {start: '', end: ''}\n"
        "  final_holdback: {start: '', end: ''}\n",
        encoding="utf-8",
    )
    log = tmp_path / "log.csv"
    ContaminationLog(log)
    with pytest.raises(PartitionLockMissing):
        enforce_no_validation_before_freeze(
            strategy_version="v0.2",
            partitions_path=parts,
            contamination_log_path=log,
        )


def test_signed_lock_without_freeze_event_blocks(tmp_path: Path) -> None:
    parts = tmp_path / "data_partitions.yml"
    parts.write_text(
        "locked: true\nlocked_by: 'director'\nlocked_at_iso: '2026-05-09T10:00:00-04:00'\n"
        "partitions:\n"
        "  training:       {start: '2022-01-03', end: '2024-12-31'}\n"
        "  validation:     {start: '2025-01-02', end: '2025-12-31'}\n"
        "  final_holdback: {start: '2026-01-02', end: '2026-04-30'}\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "log.csv"
    ContaminationLog(log_path)
    with pytest.raises(PartitionLockMissing):
        enforce_no_validation_before_freeze(
            strategy_version="v0.2",
            partitions_path=parts,
            contamination_log_path=log_path,
        )


def test_signed_lock_with_freeze_event_allows(tmp_path: Path) -> None:
    parts = tmp_path / "data_partitions.yml"
    parts.write_text(
        "locked: true\nlocked_by: 'director'\nlocked_at_iso: '2026-05-09T10:00:00-04:00'\n"
        "partitions:\n"
        "  training:       {start: '2022-01-03', end: '2024-12-31'}\n"
        "  validation:     {start: '2025-01-02', end: '2025-12-31'}\n"
        "  final_holdback: {start: '2026-01-02', end: '2026-04-30'}\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "log.csv"
    log = ContaminationLog(log_path)
    log.append(
        _row(
            action_type="other",
            description="validation_freeze: locked v0.2 prior to OOS query",
            dataset_used="none",
        )
    )
    enforce_no_validation_before_freeze(
        strategy_version="v0.2",
        partitions_path=parts,
        contamination_log_path=log_path,
    )


def test_is_partition_lock_signed_detects_missing_dates(tmp_path: Path) -> None:
    parts = tmp_path / "data_partitions.yml"
    parts.write_text(
        "locked: true\nlocked_by: 'director'\nlocked_at_iso: '2026-05-09T10:00:00-04:00'\n"
        "partitions:\n"
        "  training:       {start: '2022-01-03', end: '2024-12-31'}\n"
        "  validation:     {start: '', end: ''}\n"
        "  final_holdback: {start: '2026-01-02', end: '2026-04-30'}\n",
        encoding="utf-8",
    )
    assert not is_partition_lock_signed(parts)


def test_correction_row_pattern(tmp_path: Path) -> None:
    log = ContaminationLog(tmp_path / "log.csv")
    log.append(_row())
    log.append(
        _row(
            datetime_iso="2026-05-12T14:30:00-04:00",
            action_type="other",
            description="Correction to row 2026-05-09T10:00:00-04:00 by j_smith",
            dataset_used="none",
            result_observed="N/A",
            decision="escalated",
        )
    )
    rows = log.read_all()
    assert len(rows) == 2
