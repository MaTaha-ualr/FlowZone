"""Tests for chat with mocked LLM providers."""
import pytest
from app.middleware.rate_limit import concurrency_guard


@pytest.fixture(autouse=True)
async def reset():
    concurrency_guard._active_users.clear()
    yield
    concurrency_guard._active_users.clear()


async def _chat_session(client):
    c = await client.post("/api/v1/users", json={"name": "Chat", "age": 15, "user_type": "juvenile_justice", "has_probation": True})
    uid = c.json()["id"]
    await client.post(f"/api/v1/users/{uid}/intake", json={
        "q1_intent": "check_box", "q2_heat_level": 8,
        "q3_trap": "friends", "q4_autonomy_prize": "curfew", "q5_collaboration": "well_see",
    })
    s = await client.post(f"/api/v1/sessions/{uid}")
    return uid, s.json()["id"]


@pytest.mark.asyncio
async def test_send_message(client, mock_model_router, mock_mask_detection, mock_extract_session_data, mock_trust_calculator):
    uid, sid = await _chat_session(client)
    r = await client.post(f"/api/v1/chat/{sid}", json={"content": "School was whatever.", "vibe": "solid"})
    assert r.status_code == 200
    d = r.json()
    assert "content" in d
    assert d["character"] == "challenger"
    assert "message_id" in d


@pytest.mark.asyncio
async def test_chat_sets_vibe(client, mock_model_router, mock_mask_detection, mock_extract_session_data, mock_trust_calculator):
    uid, sid = await _chat_session(client)
    await client.post(f"/api/v1/chat/{sid}", json={"content": "Angry today.", "vibe": "angry"})
    r = await client.get(f"/api/v1/sessions/{uid}/current")
    assert r.json()["vibe_selected"] == "angry"


@pytest.mark.asyncio
async def test_chat_history(client, mock_model_router, mock_mask_detection, mock_extract_session_data, mock_trust_calculator):
    _, sid = await _chat_session(client)
    await client.post(f"/api/v1/chat/{sid}", json={"content": "First", "vibe": "solid"})
    await client.post(f"/api/v1/chat/{sid}", json={"content": "Second"})
    r = await client.get(f"/api/v1/chat/{sid}/history")
    assert r.status_code == 200
    assert r.json()["total_messages"] >= 4


@pytest.mark.asyncio
async def test_chat_inactive_session(client):
    r = await client.post("/api/v1/chat/00000000-0000-0000-0000-000000000000", json={"content": "hello"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_chat_empty_message(client):
    _, sid = await _chat_session(client)
    r = await client.post(f"/api/v1/chat/{sid}", json={"content": ""})
    assert r.status_code == 422
