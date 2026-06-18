"""Snapshot/restore helpers for the data-table backup feature.

A backup captures the raw TestLog rows plus the metadata that was active at the
time, gzipped into a single `DataBackup` record. This lets old data be
re-exported later using the current export logic (see routes/backups.py).
"""
import gzip
import json
import logging

from sqlalchemy.orm import Session

from backend.db.models import DataBackup
from backend.services import data_store
from backend.time_utils import get_export_now

logger = logging.getLogger(__name__)

# Columns copied from each TestLog row into the snapshot. `logged_at` is stored
# as an ISO string so the payload is JSON-serializable; build_export parses it back.
_ROW_COLUMNS = (
    "s1", "sp", "tp", "cycle", "cycle_timer", "lc_setpoint", "lc_regulate", "step",
    "f1", "f2", "f3", "t1", "t3", "p1", "p2", "p3", "p4", "p5",
    "tp_reversed", "trending", "ee_dir_switch",
)


def serialize_test_log_rows(rows) -> list[dict]:
    """Turn TestLog ORM rows into plain JSON-friendly dicts used by build_export."""
    out = []
    for r in rows:
        row = {"logged_at": r.logged_at.isoformat()}
        for col in _ROW_COLUMNS:
            row[col] = getattr(r, col, None)
        out.append(row)
    return out


def create_data_backup(db: Session, rows, trigger: str, headers: dict) -> DataBackup:
    """Create a DataBackup from the given TestLog rows. Caller commits/deletes."""
    row_dicts = serialize_test_log_rows(rows)

    # Direction switch best reflects the test itself: prefer the last logged row,
    # fall back to the current live value, then 0.
    dir_switch_val = row_dicts[-1].get("ee_dir_switch") if row_dicts else None
    if dir_switch_val is None:
        dir_switch_val = data_store.latest.get("ee_dir_switch", 0)

    metadata = {"headers": headers, "ee_dir_switch": dir_switch_val}
    rows_json = gzip.compress(json.dumps(row_dicts).encode("utf-8"))

    now = get_export_now()
    label = f"Backup {now.strftime('%m-%d-%Y %I-%M %p')} ({len(rows)} rows)"

    backup = DataBackup(
        label=label,
        trigger=trigger,
        row_count=len(rows),
        first_logged_at=rows[0].logged_at,
        last_logged_at=rows[-1].logged_at,
        metadata_json=json.dumps(metadata),
        rows_json=rows_json,
    )
    db.add(backup)
    db.flush()  # assign id without committing; clear_data_table commits the txn
    logger.info("Created data backup %s (%d rows, trigger=%s)", backup.id, len(rows), trigger)
    return backup


def load_backup_payload(backup: DataBackup) -> tuple[list[dict], dict, object]:
    """Decompress a backup into (row_dicts, headers, dir_switch_val) for re-export."""
    row_dicts = json.loads(gzip.decompress(backup.rows_json).decode("utf-8"))
    metadata = json.loads(backup.metadata_json) if backup.metadata_json else {}
    headers = metadata.get("headers", {})
    dir_switch_val = metadata.get("ee_dir_switch", 0)
    return row_dicts, headers, dir_switch_val


def load_backup_headers(backup: DataBackup) -> dict:
    """Parse just the header snapshot (no row decompression) for listing/editing."""
    metadata = json.loads(backup.metadata_json) if backup.metadata_json else {}
    return metadata.get("headers", {})


def update_backup_headers(db: Session, backup: DataBackup, new_headers: dict) -> dict:
    """Merge edited header fields into a backup's metadata snapshot. Caller-safe commit."""
    metadata = json.loads(backup.metadata_json) if backup.metadata_json else {}
    merged = {**metadata.get("headers", {}), **new_headers}
    metadata["headers"] = merged
    backup.metadata_json = json.dumps(metadata)
    db.commit()
    return merged
