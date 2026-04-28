import os
import pytest
import backend.services.data_store as ds
from backend.db.models import TestLog


def test_set_debug_mode_enable(client):
    resp = client.post("/set_debug_mode", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["debug_mode"] is True
    assert ds.debug_mode is True


def test_set_debug_mode_disable(client):
    ds.debug_mode = True
    resp = client.post("/set_debug_mode", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["debug_mode"] is False
    assert ds.debug_mode is False


def test_set_debug_mode_missing_body_returns_422(client):
    resp = client.post("/set_debug_mode", json={})
    assert resp.status_code == 422


def test_clear_data_table_removes_rows(client, db_session, seeded_testlog):
    assert db_session.query(TestLog).count() == 3
    resp = client.post("/clear_data_table")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert db_session.query(TestLog).count() == 0


def test_clear_data_table_empty_table_returns_200(client):
    resp = client.post("/clear_data_table")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_export_data_no_rows_returns_404(client, seeded_settings, mock_sharepoint):
    resp = client.post("/export_data")
    assert resp.status_code == 404


@pytest.mark.slow
def test_export_data_with_rows_returns_xlsx(
    client, seeded_settings, seeded_testlog, mock_sharepoint, tmp_path, monkeypatch
):
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path))
    import backend.routes.export as export_route
    monkeypatch.setattr(export_route, "EXPORT_DIR", str(tmp_path))

    resp = client.post("/export_data")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers.get("content-type", "")
