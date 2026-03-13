"""Tests for session management."""
import pytest
from app.middleware.rate_limit import concurrency_guard


@pytest.fixture(autouse=True)
async def reset_concurrency():
    concurrency_guard._active_users.clear()
    yield
    concurrency_guard._active_users.clear()


async def _make_user(client, name="Sess User"):
    c = await client.post("/api/v1/users", json={"name": name, "age": 15})
    uid = c.json()["id"]
    await client.post(f"/api/v1/users/{uid}/intake", json={
        "q1_intent": "check_box", "q2_heat_level": 5,
        "q3_trap": "friends", "q4_autonomy_prize": "curfew", "q5_collaboration": "yes",
    })
    return uid


@pytest.mark.asyncio
async def test_start_session(client):
    uid = await _make_user(client)
    r = await client.post(f"/api/v1/sessions/{uid}")
    assert r.status_code == 201
    assert r.json()["is_active"] is True


@pytest.mark.asyncio
async def test_session_requires_intake(client):
    c = await client.post("/api/v1/users", json={"name": "No Intake", "age": 15})
    r = await client.post(f"/api/v1/sessions/{c.json()['id']}")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_resume_session(client):
    uid = await _make_user(client)
    s1 = await client.post(f"/api/v1/sessions/{uid}")
    s2 = await client.post(f"/api/v1/sessions/{uid}")
    assert s1.json()["id"] == s2.json()["id"]


@pytest.mark.asyncio
async def test_end_session(client):
    uid = await _make_user(client)
    s = await client.post(f"/api/v1/sessions/{uid}")
    r = await client.put(f"/api/v1/sessions/{s.json()['id']}/end")
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_end_already_ended(client):
    uid = await _make_user(client)
    s = await client.post(f"/api/v1/sessions/{uid}")
    sid = s.json()["id"]
    await client.put(f"/api/v1/sessions/{sid}/end")
    r = await client.put(f"/api/v1/sessions/{sid}/end")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_get_current_session(client):
    uid = await _make_user(client)
    await client.post(f"/api/v1/sessions/{uid}")
    r = await client.get(f"/api/v1/sessions/{uid}/current")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_no_current_session(client):
    uid = await _make_user(client)
    r = await client.get(f"/api/v1/sessions/{uid}/current")
    assert r.status_code == 404
