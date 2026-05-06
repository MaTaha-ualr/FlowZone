"""Tests for Trust Score Calculator."""
import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4

from app.models.user import User
from app.models.session import Session
from app.models.trust_score import TrustScore
from app.core.constants import Character, Vibe, SafeHarborLevel, TrustTier, TRUST_TIER_THRESHOLDS
from app.services.trust_engine.calculator import (
    recalculate_after_session, _calculate_tier, _update_streak, redeem_vouch,
)


class TestShieldFormula:
    def test_basic_calculation(self):
        ts = TrustScore(user_id=uuid4(), score_date=date.today(),
                        consistency_c=5, weight_w=1.0, honesty_bonus_h=25.0,
                        regulation_bonus_r=10.0, mentor_vouch_m=15.0, penalty_p=10.0, time_t=3)
        assert ts.calculate() == 45.0

    def test_hard_day_multiplier(self):
        ts = TrustScore(user_id=uuid4(), score_date=date.today(),
                        consistency_c=5, weight_w=1.5, time_t=1)
        assert ts.calculate() == 7.5

    def test_penalty_reduces(self):
        ts = TrustScore(user_id=uuid4(), score_date=date.today(),
                        consistency_c=3, weight_w=1.0, penalty_p=50.0, time_t=1)
        assert ts.calculate() == -47.0

    def test_zero_time(self):
        ts = TrustScore(user_id=uuid4(), score_date=date.today(),
                        consistency_c=10, weight_w=1.0, time_t=0)
        assert ts.calculate() == 10.0

    def test_time_is_metadata_only(self):
        ts1 = TrustScore(user_id=uuid4(), score_date=date.today(), consistency_c=10, weight_w=1.0, time_t=1)
        ts10 = TrustScore(user_id=uuid4(), score_date=date.today(), consistency_c=10, weight_w=1.0, time_t=10)
        assert ts1.calculate() == ts10.calculate()


class TestTierCalculation:
    def test_watch(self):
        assert _calculate_tier(0) == TrustTier.THE_WATCH
        assert _calculate_tier(199) == TrustTier.THE_WATCH

    def test_flex(self):
        assert _calculate_tier(200) == TrustTier.THE_FLEX
        assert _calculate_tier(350) == TrustTier.THE_FLEX

    def test_vetted(self):
        assert _calculate_tier(500) == TrustTier.THE_VETTED

    def test_thresholds_ascending(self):
        vals = [TRUST_TIER_THRESHOLDS[t] for t in [TrustTier.THE_WATCH, TrustTier.THE_FLEX, TrustTier.THE_VETTED]]
        assert vals == sorted(vals)


class TestStreaks:
    @pytest.mark.asyncio
    async def test_first_checkin(self, db_session):
        u = User(id=uuid4(), name="S1", age=15, check_in_streak=0, last_check_in=None)
        db_session.add(u); await db_session.flush()
        assert await _update_streak(u, db_session) == 1

    @pytest.mark.asyncio
    async def test_same_day(self, db_session):
        u = User(id=uuid4(), name="S2", age=15, check_in_streak=5, last_check_in=datetime.utcnow())
        db_session.add(u); await db_session.flush()
        assert await _update_streak(u, db_session) == 5

    @pytest.mark.asyncio
    async def test_consecutive(self, db_session):
        u = User(id=uuid4(), name="S3", age=15, check_in_streak=3,
                 last_check_in=datetime.utcnow() - timedelta(days=1))
        db_session.add(u); await db_session.flush()
        assert await _update_streak(u, db_session) == 4

    @pytest.mark.asyncio
    async def test_missed_day_resets(self, db_session):
        u = User(id=uuid4(), name="S4", age=15, check_in_streak=10,
                 last_check_in=datetime.utcnow() - timedelta(days=2))
        db_session.add(u); await db_session.flush()
        assert await _update_streak(u, db_session) == 1


class TestRecalculation:
    @pytest.mark.asyncio
    async def test_positive_session(self, db_session):
        u = User(id=uuid4(), name="Pos", age=15, current_trust_score=100.0,
                 current_tier=TrustTier.THE_WATCH, check_in_streak=2,
                 last_check_in=datetime.utcnow() - timedelta(days=1))
        db_session.add(u); await db_session.flush()
        s = Session(id=uuid4(), user_id=u.id, session_type="flowquest",
                    character_active=Character.CHALLENGER, vibe_selected=Vibe.ANGRY,
                    mask_detected=False, honesty_disclosures=1,
                    interventions_completed=["breathing_exercise"])
        db_session.add(s); await db_session.flush()
        result = await recalculate_after_session(u.id, s, db_session)
        assert result["delta"] > 0
        assert result["new_score"] > 100.0

    @pytest.mark.asyncio
    async def test_score_never_negative(self, db_session):
        u = User(id=uuid4(), name="Low", age=15, current_trust_score=5.0,
                 current_tier=TrustTier.THE_WATCH, check_in_streak=0, last_check_in=None)
        db_session.add(u); await db_session.flush()
        s = Session(id=uuid4(), user_id=u.id, session_type="flowquest",
                    character_active=Character.CHALLENGER, mask_detected=True,
                    honesty_disclosures=0, interventions_completed=[])
        db_session.add(s); await db_session.flush()
        result = await recalculate_after_session(u.id, s, db_session)
        assert result["new_score"] >= 0


class TestVouches:
    @pytest.mark.asyncio
    async def test_redeem_success(self, db_session):
        u = User(id=uuid4(), name="Flex", age=16, current_trust_score=300.0, current_tier=TrustTier.THE_FLEX)
        db_session.add(u); await db_session.flush()
        r = await redeem_vouch(u.id, "social_pass", db_session)
        assert r["success"] is True
        assert r["credits_spent"] == 30

    @pytest.mark.asyncio
    async def test_redeem_wrong_tier(self, db_session):
        u = User(id=uuid4(), name="Watch", age=15, current_trust_score=50.0, current_tier=TrustTier.THE_WATCH)
        db_session.add(u); await db_session.flush()
        r = await redeem_vouch(u.id, "curfew_extension", db_session)
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_redeem_insufficient(self, db_session):
        u = User(id=uuid4(), name="Broke", age=16, current_trust_score=10.0, current_tier=TrustTier.THE_FLEX)
        db_session.add(u); await db_session.flush()
        r = await redeem_vouch(u.id, "reduced_monitoring", db_session)
        assert r["success"] is False
