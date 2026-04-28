import pytest
import backend.services.data_store as ds


pytestmark = pytest.mark.asyncio


async def test_update_merges_into_latest():
    await ds.update({"s1": 999})
    assert ds.latest["s1"] == 999


async def test_update_does_not_clobber_other_keys():
    ds.latest["f1"] = 42.0
    await ds.update({"s1": 500})
    assert ds.latest["f1"] == 42.0
    assert ds.latest["s1"] == 500


async def test_broadcast_no_connections_does_not_raise():
    ds.frontend_connections.clear()
    await ds.broadcast({"s1": 1})  # Should not raise


async def test_broadcast_removes_dead_connections():
    class DeadWS:
        async def send_json(self, data):
            raise RuntimeError("connection closed")

    dead = DeadWS()
    ds.frontend_connections.add(dead)
    await ds.broadcast({"s1": 1})
    assert dead not in ds.frontend_connections


async def test_update_calls_broadcast():
    calls = []

    class MockWS:
        async def send_json(self, data):
            calls.append(data)

    ws = MockWS()
    ds.frontend_connections.add(ws)
    await ds.update({"s1": 777})
    assert len(calls) == 1
    assert calls[0]["s1"] == 777
