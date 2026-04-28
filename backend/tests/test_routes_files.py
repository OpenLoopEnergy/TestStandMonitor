import pytest
from backend.db.models import ExportedFile


def test_past_tests_empty(client):
    resp = client.get("/past_tests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["files"] == []
    assert body["db_files"] == []


def test_past_tests_returns_seeded_file(client, seeded_exported_file):
    resp = client.get("/past_tests")
    assert resp.status_code == 200
    files = resp.json()["files"]
    assert len(files) == 1
    assert files[0]["filename"] == "test_file.xlsx"
    assert "created_at" in files[0]


def test_download_existing_file(client, seeded_exported_file):
    resp = client.get("/download_test/test_file.xlsx")
    assert resp.status_code == 200
    assert resp.content == b"PK\x03\x04fake_xlsx_bytes"
    assert "spreadsheetml" in resp.headers["content-type"]


def test_download_missing_file_returns_404(client):
    resp = client.get("/download_test/nonexistent.xlsx")
    assert resp.status_code == 404


def test_delete_file_removes_from_db(client, db_session, seeded_exported_file):
    resp = client.delete("/delete_file/test_file.xlsx")
    assert resp.status_code == 200
    assert db_session.query(ExportedFile).count() == 0


def test_delete_missing_file_returns_404(client):
    resp = client.delete("/delete_file/nonexistent.xlsx")
    assert resp.status_code == 404


def test_rename_appends_xlsx_if_missing(client, db_session, seeded_exported_file):
    resp = client.post("/rename_file", json={
        "old_filename": "test_file.xlsx",
        "new_filename": "renamed_no_ext",
    })
    assert resp.status_code == 200
    assert resp.json()["filename"] == "renamed_no_ext.xlsx"
    assert db_session.query(ExportedFile).filter_by(filename="renamed_no_ext.xlsx").first() is not None


def test_rename_preserves_xlsx_extension(client, seeded_exported_file):
    resp = client.post("/rename_file", json={
        "old_filename": "test_file.xlsx",
        "new_filename": "already_has.xlsx",
    })
    assert resp.status_code == 200
    assert resp.json()["filename"] == "already_has.xlsx"


def test_rename_missing_file_returns_404(client):
    resp = client.post("/rename_file", json={
        "old_filename": "nonexistent.xlsx",
        "new_filename": "new_name",
    })
    assert resp.status_code == 404


def test_past_tests_orders_by_most_recent(client, db_session):
    from datetime import datetime, timezone, timedelta
    older = ExportedFile(
        filename="older.xlsx",
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        file_data=b"old",
    )
    newer = ExportedFile(
        filename="newer.xlsx",
        created_at=datetime.now(timezone.utc),
        file_data=b"new",
    )
    db_session.add(older)
    db_session.add(newer)
    db_session.commit()
    resp = client.get("/past_tests")
    files = resp.json()["files"]
    assert files[0]["filename"] == "newer.xlsx"
    assert files[1]["filename"] == "older.xlsx"
