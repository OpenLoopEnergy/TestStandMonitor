import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from backend.db.database import Base, get_db
from backend.db.models import AppSettings, TestLog, ExportedFile
from backend.main import app
import backend.services.data_store as ds


@pytest.fixture(scope="session")
def engine():
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_data_store():
    ds.latest.clear()
    ds.latest.update({
        "s1": 0, "sp": 0, "tp": 0, "delay": 0, "trending": 0,
        "cycle": 0, "cycleTimer": 0, "lcSetpoint": 0, "lcRegulate": 0,
        "step": "Unknown", "t1": 0, "t3": 0, "f1": 0, "f2": 0, "f3": 0,
        "p1": 0, "p2": 0, "p3": 0, "p4": 0, "p5": 0,
        "pi_connected": False, "debug_mode": False,
        "tp_reved": 0, "m2_tp9a_dir": 0, "ee_dir_switch": 0,
    })
    ds.debug_mode = False
    ds.frontend_connections.clear()
    yield


@pytest.fixture
def seeded_settings(db_session):
    for key, value in {
        "programName": "Test Program",
        "description": "Test Description",
        "compSet": "0",
        "inputFactor": "11",
        "inputFactorType": "cu/in",
        "serialNumber": "0",
        "employeeId": "0",
        "customerId": "0",
    }.items():
        db_session.add(AppSettings(key=key, value=value))
    db_session.commit()


@pytest.fixture
def seeded_testlog(db_session):
    rows = []
    for i in range(3):
        r = TestLog(
            logged_at=datetime.now(timezone.utc),
            s1=1200 + i * 100,
            sp=1200,
            tp=512,
            cycle=i,
            cycle_timer=100,
            lc_setpoint=300,
            lc_regulate=0,
            step="Running",
            f1=250.0,
            f2=0.0,
            f3=0.0,
            t1=720,
            t3=680,
            p1=1200,
            p2=800,
            p3=600,
            p4=400,
            p5=200,
            tp_reversed=False,
            ee_dir_switch=0,
            trending=1,
        )
        db_session.add(r)
        rows.append(r)
    db_session.commit()
    return rows


@pytest.fixture
def seeded_exported_file(db_session):
    ef = ExportedFile(
        filename="test_file.xlsx",
        created_at=datetime.now(timezone.utc),
        file_data=b"PK\x03\x04fake_xlsx_bytes",
    )
    db_session.add(ef)
    db_session.commit()
    return ef


@pytest.fixture
def mock_sharepoint(monkeypatch):
    import backend.services.sharepoint_upload as sp
    monkeypatch.setattr(sp, "upload_to_sharepoint", lambda *a, **kw: None)
