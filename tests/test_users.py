"""Tests for user management and Strategic Intake."""
import pytest


@pytest.mark.asyncio
async def test_create_user(client):
    r = await client.post("/api/v1/users", json={"name": "Test User", "age": 15, "user_type": "at_risk"})
    assert r.status_code == 201
    assert r.json()["name"] == "Test User"
    assert r.json()["intake_completed"] is False


@pytest.mark.asyncio
async def test_create_user_invalid_age(client):
    r = await client.post("/api/v1/users", json={"name": "Young", "age": 10, "user_type": "at_risk"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_user_invalid_type(client):
    r = await client.post("/api/v1/users", json={"name": "Bad", "age": 15, "user_type": "invalid"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_users(client):
    await client.post("/api/v1/users", json={"name": "A", "age": 14})
    await client.post("/api/v1/users", json={"name": "B", "age": 16})
    r = await client.get("/api/v1/users")
    assert r.status_code == 200
    assert r.json()["total"] >= 2


@pytest.mark.asyncio
async def test_get_user(client):
    c = await client.post("/api/v1/users", json={"name": "Get Me", "age": 15})
    uid = c.json()["id"]
    r = await client.get(f"/api/v1/users/{uid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Get Me"


@pytest.mark.asyncio
async def test_get_nonexistent_user(client):
    r = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_user(client):
    c = await client.post("/api/v1/users", json={"name": "Delete Me", "age": 15})
    uid = c.json()["id"]
    r = await client.delete(f"/api/v1/users/{uid}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/v1/users/{uid}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_intake_check_box(client):
    c = await client.post("/api/v1/users", json={"name": "Honest", "age": 15, "user_type": "juvenile_justice", "has_probation": True})
    uid = c.json()["id"]
    r = await client.post(f"/api/v1/users/{uid}/intake", json={
        "q1_intent": "check_box", "q2_heat_level": 8, "q3_trap": "friends",
        "q4_autonomy_prize": "curfew", "q5_collaboration": "well_see",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["baseline_trust_score"] == 85.0  # 50+25+10
    assert d["assigned_character"] == "challenger"
    assert d["weight_multiplier"] == 1.5


@pytest.mark.asyncio
async def test_intake_win_freedom_low_heat(client):
    c = await client.post("/api/v1/users", json={"name": "Eager", "age": 14})
    uid = c.json()["id"]
    r = await client.post(f"/api/v1/users/{uid}/intake", json={
        "q1_intent": "win_freedom", "q2_heat_level": 3, "q3_trap": "dont_know",
        "q4_autonomy_prize": "trust_to_walk", "q5_collaboration": "yes",
    })
    assert r.status_code == 200
    assert r.json()["baseline_trust_score"] == 25.0  # 10+5+10
    assert r.json()["weight_multiplier"] == 1.0


@pytest.mark.asyncio
async def test_intake_cannot_submit_twice(client):
    c = await client.post("/api/v1/users", json={"name": "Once", "age": 15})
    uid = c.json()["id"]
    intake = {"q1_intent": "check_box", "q2_heat_level": 5, "q3_trap": "boredom", "q4_autonomy_prize": "curfew", "q5_collaboration": "yes"}
    assert (await client.post(f"/api/v1/users/{uid}/intake", json=intake)).status_code == 200
    assert (await client.post(f"/api/v1/users/{uid}/intake", json=intake)).status_code == 400
