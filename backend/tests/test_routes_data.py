import pytest
import backend.services.data_store as ds
from backend.routes.data import _calc_theo_flow_and_efficiency


# ── Unit tests for the pure calculation function ──────────────────────────────

def test_calc_theo_flow_and_efficiency_nominal():
    theo, eff = _calc_theo_flow_and_efficiency(s1=1200, f1=250.0, input_factor=11.0)
    assert abs(theo - round(1200 * 11 / 231, 2)) < 0.01
    expected_eff = round((250.0 * 0.01 / (1200 * 11 / 231)) * 100, 2)
    assert abs(eff - expected_eff) < 0.01


def test_calc_theo_flow_zero_s1_no_division_error():
    theo, eff = _calc_theo_flow_and_efficiency(s1=0, f1=250.0, input_factor=11.0)
    assert theo == 0.0
    assert eff == 0.0


def test_calc_theo_flow_zero_f1():
    theo, eff = _calc_theo_flow_and_efficiency(s1=1200, f1=0.0, input_factor=11.0)
    assert theo > 0
    assert eff == 0.0


# ── /get_live_data ────────────────────────────────────────────────────────────

def test_get_live_data_has_efficiency_fields(client, seeded_settings):
    resp = client.get("/get_live_data")
    assert resp.status_code == 200
    body = resp.json()
    assert "efficiency" in body
    assert "theo_flow" in body
    assert "input_factor" in body
    assert body["input_factor"] == 11.0


def test_get_live_data_zero_s1_no_division_error(client, seeded_settings):
    ds.latest["s1"] = 0
    ds.latest["f1"] = 0
    resp = client.get("/get_live_data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["theo_flow"] == 0.0
    assert body["efficiency"] == 0.0


def test_get_live_data_efficiency_calc(client, seeded_settings):
    ds.latest["s1"] = 1200
    ds.latest["f1"] = 250.0
    resp = client.get("/get_live_data")
    assert resp.status_code == 200
    body = resp.json()
    expected_theo = round(1200 * 11 / 231, 2)
    expected_eff = round((250.0 * 0.01 / expected_theo) * 100, 2)
    assert abs(body["theo_flow"] - expected_theo) < 0.01
    assert abs(body["efficiency"] - expected_eff) < 0.01


# ── /get_signal_data ──────────────────────────────────────────────────────────

def test_get_signal_data_valid_signal(client, seeded_testlog):
    resp = client.get("/get_signal_data?signal=S1")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    assert "timestamp" in items[0]
    assert "value" in items[0]


def test_get_signal_data_unknown_signal_returns_400(client):
    resp = client.get("/get_signal_data?signal=XX")
    assert resp.status_code == 400


def test_get_signal_data_case_insensitive(client, seeded_testlog):
    resp = client.get("/get_signal_data?signal=s1")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_get_signal_data_all_valid_signals(client, seeded_testlog):
    for signal in ["S1", "SP", "TP", "F1", "F2", "F3", "T1", "T3", "P1", "P2", "P3", "P4", "P5"]:
        resp = client.get(f"/get_signal_data?signal={signal}")
        assert resp.status_code == 200, f"Signal {signal} failed with {resp.status_code}"


# ── /get_csv_data ─────────────────────────────────────────────────────────────

def test_get_csv_data_returns_rows(client, seeded_testlog):
    resp = client.get("/get_csv_data")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert len(body["data"]) == 3
    row = body["data"][0]
    assert "S1" in row
    assert "F1" in row
    assert "Date" in row
    assert "Time" in row


def test_get_csv_data_empty_returns_empty_list(client):
    resp = client.get("/get_csv_data")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_get_csv_data_respects_20_row_limit(client, db_session):
    from datetime import datetime, timezone
    from backend.db.models import TestLog
    for i in range(25):
        db_session.add(TestLog(
            logged_at=datetime.now(timezone.utc), s1=i, sp=0, tp=0,
            cycle=0, cycle_timer=0, lc_setpoint=0, lc_regulate=0,
            step="Running", f1=0.0, f2=0.0, f3=0.0, t1=0, t3=0,
            p1=0, p2=0, p3=0, p4=0, p5=0, trending=1,
        ))
    db_session.commit()
    resp = client.get("/get_csv_data")
    assert len(resp.json()["data"]) <= 20
