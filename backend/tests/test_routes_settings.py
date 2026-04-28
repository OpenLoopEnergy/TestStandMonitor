import pytest
from backend.db.models import AppSettings

VALID_PAYLOAD = {
    "programName": "My Program",
    "description": "Some description",
    "compSet": 5,
    "inputFactor": 11.0,
    "inputFactorType": "cu/in",
    "serialNumber": 12345,
    "employeeId": 42,
    "customerId": 99,
}


def test_get_header_data_returns_settings(client, seeded_settings):
    resp = client.get("/get_header_data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["inputFactor"] == "11"
    assert body["inputFactorType"] == "cu/in"
    assert body["programName"] == "Test Program"


def test_get_header_data_empty_db(client):
    resp = client.get("/get_header_data")
    assert resp.status_code == 200
    assert resp.json() == {}


def test_update_header_data_valid(client, seeded_settings):
    resp = client.post("/update_header_data", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_update_header_data_persists_to_db(client, db_session, seeded_settings):
    payload = {**VALID_PAYLOAD, "programName": "Updated Name"}
    client.post("/update_header_data", json=payload)
    resp = client.get("/get_header_data")
    assert resp.json()["programName"] == "Updated Name"


def test_update_header_data_invalid_factor_type_returns_400(client):
    payload = {**VALID_PAYLOAD, "inputFactorType": "bad_value"}
    resp = client.post("/update_header_data", json=payload)
    assert resp.status_code == 400


def test_update_header_data_cu_cm_is_valid(client, seeded_settings):
    payload = {**VALID_PAYLOAD, "inputFactorType": "cu/cm"}
    resp = client.post("/update_header_data", json=payload)
    assert resp.status_code == 200


def test_update_header_data_missing_field_returns_422(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "programName"}
    resp = client.post("/update_header_data", json=payload)
    assert resp.status_code == 422


def test_update_header_data_creates_new_settings_if_none_exist(client):
    resp = client.post("/update_header_data", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = client.get("/get_header_data").json()
    assert body["programName"] == "My Program"
    assert body["inputFactor"] == "11.0"
