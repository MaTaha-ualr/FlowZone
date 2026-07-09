"""Tests for mentor note submission and dashboard."""
import pytest
from unittest.mock import patch, AsyncMock
from app.middleware.rate_limit import concurrency_guard


@pytest.fixture(autouse=True)
async def reset():
    concurrency_guard._active_users.clear()
    yield
    concurrency_guard._active_users.clear()


async def _make_user(client):
    c = await client.post("/api/v1/users", json={"name": "Mentor Test", "age": 15, "user_type": "juvenile_justice"})
    uid = c.json()["id"]
    return uid, {"X-User-ID": uid}


async def _make_mentor(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Coach Dana",
            "username": "coach_dana",
            "password": "secure123",
            "age": 32,
            "role": "mentor",
        },
    )
    assert r.status_code == 201, r.text
    return {"X-User-ID": r.json()["user"]["id"]}


@pytest.mark.asyncio
async def test_submit_note(client):
    uid, _ = await _make_user(client)
    mentor_headers = await _make_mentor(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Sanitized content."
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach Ray",
            "note_type": "observation", "content": "Raw note content.",
        }, headers=mentor_headers)
        assert r.status_code == 201
        assert r.json()["mentor_name"] == "Coach Dana"
        m.assert_called_once()


@pytest.mark.asyncio
async def test_submit_vouch(client):
    uid, _ = await _make_user(client)
    mentor_headers = await _make_mentor(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Vouch."
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "vouch", "content": "Showed up.", "vouch_points": 15,
        }, headers=mentor_headers)
        assert r.status_code == 201
        assert r.json()["vouch_points"] == 15


@pytest.mark.asyncio
async def test_get_notes(client):
    uid, headers = await _make_user(client)
    mentor_headers = await _make_mentor(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Clean."
        await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "observation", "content": "Raw.",
        }, headers=mentor_headers)
    r = await client.get(f"/api/v1/mentors/notes/{uid}", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_dashboard(client):
    uid, headers = await _make_user(client)
    r = await client.get(f"/api/v1/mentors/dashboard/{uid}", headers=headers)
    assert r.status_code == 200
    assert "user" in r.json()
    assert "trust_score_trend" in r.json()


@pytest.mark.asyncio
async def test_note_nonexistent_user(client):
    mentor_headers = await _make_mentor(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock):
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": "00000000-0000-0000-0000-000000000000",
            "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "observation", "content": "Test.",
        }, headers=mentor_headers)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_risk_flag_red(client):
    uid, _ = await _make_user(client)
    mentor_headers = await _make_mentor(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Flagged."
        r = await client.post("/api/v1/mentors/notes", json={
            "user_id": uid, "mentor_id": "m1", "mentor_name": "Coach",
            "note_type": "risk_flag", "content": "Concerning.",
            "risk_flag_level": "red",
        }, headers=mentor_headers)
        assert r.status_code == 201
        assert r.json()["risk_flag_level"] == "red"


@pytest.mark.asyncio
async def test_youth_cannot_submit_mentor_note(client):
    uid, youth_headers = await _make_user(client)
    r = await client.post("/api/v1/mentors/notes", json={
        "user_id": uid,
        "mentor_id": uid,
        "mentor_name": "Not a mentor",
        "note_type": "vouch",
        "content": "Award myself points.",
        "vouch_points": 50,
    }, headers=youth_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_risk_flag_creates_alert_queue_item(client):
    uid, _ = await _make_user(client)
    mentor_headers = await _make_mentor(client)
    with patch("app.api.routes.mentors.sanitize_mentor_note", new_callable=AsyncMock) as m:
        m.return_value = "Flagged."
        note = await client.post("/api/v1/mentors/notes", json={
            "user_id": uid,
            "note_type": "risk_flag",
            "content": "Concerning.",
            "risk_flag_level": "red",
        }, headers=mentor_headers)
    assert note.status_code == 201, note.text

    alerts = await client.get("/api/v1/mentors/alerts", headers=mentor_headers)
    assert alerts.status_code == 200, alerts.text
    assert alerts.json()[0]["user_id"] == uid
    assert alerts.json()[0]["severity"] == "red"
