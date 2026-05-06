"""Tests for frontend-facing auth, profile, and vibe APIs."""

import pytest


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(real_auth_client, username: str = "marcus_j") -> dict:
    response = await real_auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Marcus Johnson",
            "username": username,
            "password": "secure123",
            "email": f"{username}@example.com",
            "phone": "501-555-0100",
            "age": 17,
            "role": "youth",
            "school_name": "Central High",
            "city": "Little Rock",
            "state": "AR",
            "has_probation": False,
            "has_case_worker": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_register_login_and_profile_use_real_bearer_token(real_auth_client):
    registered = await _register(real_auth_client)
    token = registered["access_token"]
    user = registered["user"]

    assert registered["token_type"] == "bearer"
    assert user["username"] == "marcus_j"
    assert user["role"] == "youth"
    assert user["current_character_name"] == "Yogi"
    assert user["intake_completed"] is True

    profile_response = await real_auth_client.get(
        "/api/v1/profile/me",
        headers=_auth_headers(token),
    )
    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()
    assert profile["id"] == user["id"]
    assert profile["check_in_streak"] == 0
    assert profile["display_score"] == 0.0
    assert profile["phone"] == "501-555-0100"

    login_response = await real_auth_client.post(
        "/api/v1/auth/login",
        json={"username": "MARCUS_J", "password": "secure123"},
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["user"]["id"] == user["id"]

    duplicate_response = await real_auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Someone Else",
            "username": "marcus_j",
            "password": "secure123",
            "age": 17,
        },
    )
    assert duplicate_response.status_code == 409

    bad_login_response = await real_auth_client.post(
        "/api/v1/auth/login",
        json={"username": "marcus_j", "password": "wrong-password"},
    )
    assert bad_login_response.status_code == 401


@pytest.mark.asyncio
async def test_profile_rewards_and_rainbow_circle(real_auth_client):
    registered = await _register(real_auth_client, username="rainbow_user")
    headers = _auth_headers(registered["access_token"])

    rewards_response = await real_auth_client.get("/api/v1/profile/rewards", headers=headers)
    assert rewards_response.status_code == 200, rewards_response.text
    rewards = rewards_response.json()
    assert rewards["current_score"] == 0.0
    assert rewards["can_redeem"] is False
    assert rewards["next_unlock_tier"] == "The Flex"
    assert {item["key"] for item in rewards["available_vouches"]} == {
        "curfew_extension",
        "social_pass",
        "reduced_monitoring",
    }
    assert all(item["locked"] for item in rewards["available_vouches"])

    rainbow_response = await real_auth_client.get(
        "/api/v1/profile/rainbow-circle",
        headers=headers,
    )
    assert rainbow_response.status_code == 200, rainbow_response.text
    rainbow = rainbow_response.json()
    assert rainbow["current_tier"] == "the_watch"
    assert rainbow["current_tier_name"] == "The Watch"
    assert rainbow["total_tiers"] == 3
    assert rainbow["tier_index"] == 0
    assert rainbow["all_tiers"][0]["unlocked"] is True


@pytest.mark.asyncio
async def test_register_accepts_mentor_role(real_auth_client):
    response = await real_auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Dana Mentor",
            "username": "mentor_dana",
            "password": "secure123",
            "age": 32,
            "role": "mentor",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["user"]["role"] == "mentor"


@pytest.mark.asyncio
async def test_vibe_check_updates_session_character_and_safe_harbor(real_auth_client):
    registered = await _register(real_auth_client, username="vibe_user")
    user_id = registered["user"]["id"]
    headers = _auth_headers(registered["access_token"])

    session_response = await real_auth_client.post(
        f"/api/v1/sessions/{user_id}",
        headers=headers,
    )
    assert session_response.status_code == 201, session_response.text
    session_id = session_response.json()["id"]

    vibe_response = await real_auth_client.post(
        "/api/v1/vibe/check",
        headers=headers,
        json={
            "session_id": session_id,
            "vibe": "angry",
            "notes": "Got in a fight at school",
        },
    )
    assert vibe_response.status_code == 200, vibe_response.text
    vibe = vibe_response.json()
    assert vibe["vibe"] == "angry"
    assert vibe["character_assigned"] == "challenger"
    assert vibe["character_name"] == "Vex"
    assert vibe["safe_harbor_level"] == "yellow"
    assert vibe["vibe_emoji"]

    current_session_response = await real_auth_client.get(
        f"/api/v1/sessions/{user_id}/current",
        headers=headers,
    )
    assert current_session_response.status_code == 200, current_session_response.text
    current_session = current_session_response.json()
    assert current_session["vibe_selected"] == "angry"
    assert current_session["character_active"] == "challenger"
    assert current_session["safe_harbor_level"] == "yellow"
