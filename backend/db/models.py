import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, Text, DateTime, String, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import types

from backend.db.database import Base


# UUID type that works for both SQLite (stores as string) and PostgreSQL
class UUIDType(types.TypeDecorator):
    impl = types.String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return uuid.UUID(value) if value is not None else None


class TestLog(Base):
    """One row per 5-second logging tick while trending is active."""
    __tablename__ = "test_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    logged_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    session_id = Column(UUIDType, nullable=True)

    # Sensor values — stored raw (same units as CAN bus)
    s1 = Column(Integer)
    sp = Column(Integer)
    tp = Column(Integer)
    cycle = Column(Integer)
    cycle_timer = Column(Integer)
    lc_setpoint = Column(Integer)
    lc_regulate = Column(Integer)
    step = Column(Text)
    f1 = Column(Float)
    f2 = Column(Float)
    f3 = Column(Float)
    t1 = Column(Integer)
    t3 = Column(Integer)
    p1 = Column(Integer)
    p2 = Column(Integer)
    p3 = Column(Integer)
    p4 = Column(Integer)
    p5 = Column(Integer)
    tp_reversed = Column(Boolean, nullable=True)
    ee_dir_switch = Column(Integer, nullable=True)
    trending = Column(Integer, nullable=True)


class DebugLog(Base):
    """Debug log — one row per 5-second tick capturing all debug-screen signals."""
    __tablename__ = "debug_log"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    logged_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    session_id = Column(UUIDType, nullable=True)

    # ── Core sensors (same as TestLog) ──────────────────────────────────────
    s1 = Column(Integer); sp = Column(Integer); tp = Column(Integer)
    cycle = Column(Integer); cycle_timer = Column(Integer)
    lc_setpoint = Column(Integer); lc_regulate = Column(Integer)
    step = Column(Text)
    f1 = Column(Float); f2 = Column(Float); f3 = Column(Float)
    t1 = Column(Integer); t3 = Column(Integer)
    p1 = Column(Integer); p2 = Column(Integer); p3 = Column(Integer)
    p4 = Column(Integer); p5 = Column(Integer)
    tp_reversed = Column(Boolean, nullable=True)
    ee_dir_switch = Column(Integer, nullable=True)
    trending = Column(Integer, nullable=True)

    # ── Machine state ────────────────────────────────────────────────────────
    started  = Column(Integer, nullable=True)
    stopped  = Column(Integer, nullable=True)
    e_stopped = Column(Integer, nullable=True)

    # ── M1 command outputs ───────────────────────────────────────────────────
    sol_a       = Column(Integer, nullable=True)
    sol_b       = Column(Integer, nullable=True)
    tp9a_enable = Column(Integer, nullable=True)
    tp9a_dir    = Column(Integer, nullable=True)

    # ── LC1 control loop ─────────────────────────────────────────────────────
    lc1          = Column(Integer, nullable=True)
    lc1_feedback = Column(Integer, nullable=True)
    lc1_enable   = Column(Integer, nullable=True)
    lc1_state    = Column(Integer, nullable=True)

    # ── SP circuit ───────────────────────────────────────────────────────────
    sp_feedback = Column(Integer, nullable=True)
    sp_enable   = Column(Integer, nullable=True)
    sp_regulate = Column(Integer, nullable=True)
    sp_rev      = Column(Integer, nullable=True)

    # ── M2 data ──────────────────────────────────────────────────────────────
    m2_pot      = Column(Integer, nullable=True)
    m2_tp9a     = Column(Integer, nullable=True)
    m2_tp9a_dir = Column(Integer, nullable=True)

    # ── M1 port flags (flattened from m1_ports nested dict) ─────────────────
    m1_sp_open         = Column(Integer, nullable=True)
    m1_sp_short        = Column(Integer, nullable=True)
    m1_sp_enable_open  = Column(Integer, nullable=True)
    m1_sp_enable_short = Column(Integer, nullable=True)
    m1_sp_rev_open     = Column(Integer, nullable=True)
    m1_sp_rev_short    = Column(Integer, nullable=True)
    m1_tp_open         = Column(Integer, nullable=True)
    m1_tp_short        = Column(Integer, nullable=True)
    m1_tp_enable_open  = Column(Integer, nullable=True)
    m1_tp_enable_short = Column(Integer, nullable=True)
    m1_tp_rev_open     = Column(Integer, nullable=True)
    m1_tp_rev_short    = Column(Integer, nullable=True)
    m1_lc1_open        = Column(Integer, nullable=True)
    m1_lc1_short       = Column(Integer, nullable=True)
    m1_lc1_pwr_open    = Column(Integer, nullable=True)
    m1_lc1_pwr_short   = Column(Integer, nullable=True)
    m1_led_open        = Column(Integer, nullable=True)
    m1_led_short       = Column(Integer, nullable=True)
    m1_blink           = Column(Integer, nullable=True)

    # ── M2 port flags (flattened from m2_ports nested dict) ─────────────────
    m2_polarity_open   = Column(Integer, nullable=True)
    m2_polarity_short  = Column(Integer, nullable=True)
    m2_stop_lamp_open  = Column(Integer, nullable=True)
    m2_stop_lamp_short = Column(Integer, nullable=True)
    m2_sol_a_open      = Column(Integer, nullable=True)
    m2_sol_a_short     = Column(Integer, nullable=True)
    m2_sol_b_open      = Column(Integer, nullable=True)
    m2_sol_b_short     = Column(Integer, nullable=True)
    m2_tp9a_open       = Column(Integer, nullable=True)
    m2_tp9a_short      = Column(Integer, nullable=True)
    m2_tp9a_fwd_open   = Column(Integer, nullable=True)
    m2_tp9a_fwd_short  = Column(Integer, nullable=True)
    m2_tp9a_rev_open   = Column(Integer, nullable=True)
    m2_tp9a_rev_short  = Column(Integer, nullable=True)
    m2_blink           = Column(Integer, nullable=True)
    m2_supply_voltage  = Column(Integer, nullable=True)

    # ── EE motor config ──────────────────────────────────────────────────────
    ee_sm_rpm      = Column(Integer, nullable=True)
    ee_sm_rate     = Column(Integer, nullable=True)
    ee_sm_timer    = Column(Integer, nullable=True)
    ee_cycle_delay = Column(Integer, nullable=True)

    # ── EE cycle profile ─────────────────────────────────────────────────────
    ee_cycle_time1 = Column(Integer, nullable=True)
    ee_cycle_time2 = Column(Integer, nullable=True)
    ee_cycle_time3 = Column(Integer, nullable=True)
    ee_cycle_time4 = Column(Integer, nullable=True)
    ee_cycle_time5 = Column(Integer, nullable=True)
    ee_cycle_psi1  = Column(Integer, nullable=True)
    ee_cycle_psi2  = Column(Integer, nullable=True)
    ee_cycle_psi3  = Column(Integer, nullable=True)
    ee_cycle_psi4  = Column(Integer, nullable=True)
    ee_cycle_psi5  = Column(Integer, nullable=True)


class AppSettings(Base):
    """Key-value store for user-configurable settings (program name, input factor, etc.)."""
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)


class ExportedFile(Base):
    """Exported test result Excel files stored as binary blobs."""
    __tablename__ = "exported_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    file_data = Column(LargeBinary, nullable=False)


class DataBackup(Base):
    """Snapshot of the live data table taken right before it is cleared.

    Stores the raw TestLog rows plus the metadata that was active at backup time,
    so the data can be re-exported later using the current export logic.
    """
    __tablename__ = "data_backups"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    label           = Column(String(500), nullable=False)   # auto-named, renamable
    trigger         = Column(String(50))                    # "manual" | "auto"
    row_count       = Column(Integer, nullable=False)
    first_logged_at = Column(DateTime(timezone=True), nullable=True)
    last_logged_at  = Column(DateTime(timezone=True), nullable=True)
    metadata_json   = Column(Text)          # AppSettings snapshot + ee_dir_switch, as JSON
    rows_json       = Column(LargeBinary)   # gzipped JSON of the raw TestLog rows
