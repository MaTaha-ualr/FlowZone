"""
Seed Script: Load Test Data
=============================
Loads the 5 test personas (starting with Marcus Cole) into the database.
Run after the app starts:
    python -m scripts.seed_data

Or via Docker:
    docker compose exec app python -m scripts.seed_data
"""

import asyncio
import sys
from datetime import datetime, date
from uuid import uuid4

# Add project root to path
sys.path.insert(0, ".")

from app.database import engine, async_session, Base
from app.models import *  # noqa: F401, F403
from app.core.constants import Character, SafeHarborLevel, TrustTier, Vibe


async def seed():
    """Create tables and insert test data."""

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    async with async_session() as db:
        # ============================================================
        # PERSONA 1: Marcus Cole (Juvenile Justice)
        # ============================================================
        marcus_id = uuid4()
        marcus = User(
            id=marcus_id,
            name="Marcus Cole",
            age=15,
            date_of_birth=datetime(2010, 6, 14),
            school_name="Westwood High School",
            city="Memphis",
            state="Tennessee",
            user_type="juvenile_justice",
            has_probation=True,
            has_case_worker=False,
            intake_completed=True,
            intake_answers={
                "q1_intent": "check_box",
                "q2_heat_level": 8,
                "q3_trap": "friends",
                "q4_autonomy_prize": "trust_to_walk",
                "q5_collaboration": "well_see",
            },
            baseline_trust_score=95.0,
            current_trust_score=99.8,
            heat_level=8,
            weight_multiplier=1.5,
            current_character=Character.CHALLENGER,
            current_tier=TrustTier.THE_WATCH,
            check_in_streak=3,
            last_check_in=datetime(2025, 3, 12, 20, 42),
            safe_harbor_floor=SafeHarborLevel.YELLOW,
            has_trauma_history=True,
            has_crisis_history=False,
        )
        db.add(marcus)
        await db.flush()  # Flush user to DB before adding child records
        print(f"  Added: Marcus Cole ({marcus_id})")

        # -- School Data --
        marcus_school = SchoolData(
            user_id=marcus_id,
            school_name="Westwood High School",
            gpa=1.8,
            attendance_rate=0.72,
            tardiness_count=18,
            classes_failing=["English 9", "Biology"],
            classes_excelling=["Physical Education", "Art I"],
            disciplinary_incidents=[
                {"date": "2025-02-01", "type": "fight", "consequence": "3_day_suspension"}
            ],
            has_iep=False,
            athletic_eligible=False,
            source="manual",
            academic_period="Fall 2024",
        )
        db.add(marcus_school)

        # -- Document References --
        docs = [
            DocumentRef(
                user_id=marcus_id,
                filename="Marcus_Cole_Disposition_Order_JV-2025-00847.pdf",
                document_type="court_legal",
                processing_status="completed",
                chunk_count=8,
                chroma_collection=f"user_{marcus_id}_documents",
                extracted_metadata={
                    "case_number": "JV-2025-00847",
                    "court_jurisdiction": "Shelby County Juvenile Court, Tennessee",
                    "judge_name": "Hon. Patricia Dawkins",
                    "charge": "Theft of Property, Class A Misdemeanor",
                    "dates": {"issued": "2025-01-15", "probation_end": "2025-07-14"},
                    "conditions": [
                        "curfew_9pm_school_10pm_weekend",
                        "school_attendance_mandatory",
                        "drug_testing_random",
                        "no_contact_trey_washington",
                        "community_service_40hrs",
                        "counseling_as_directed",
                    ],
                    "no_contact_persons": [{"name": "Trey Washington", "dob": "2008-03-22"}],
                    "risk_level": "medium",
                },
            ),
            DocumentRef(
                user_id=marcus_id,
                filename="Westwood_HS_ReportCard_Fall2024_MarcusCole.pdf",
                document_type="school_record",
                processing_status="completed",
                chunk_count=5,
                chroma_collection=f"user_{marcus_id}_documents",
                extracted_metadata={
                    "gpa": 1.8,
                    "attendance_rate": 0.72,
                    "academic_probation": True,
                    "athletic_eligibility": False,
                    "eligibility_requirements": {"min_gpa": 2.0, "max_absences_per_class": 10},
                    "motivator_identified": "basketball_eligibility",
                    "counselor_recommendation": "IEP evaluation + academic support",
                },
            ),
            DocumentRef(
                user_id=marcus_id,
                filename="PO_Report_Feb2025_MarcusCole.pdf",
                document_type="caseworker_report",
                processing_status="completed",
                chunk_count=6,
                chroma_collection=f"user_{marcus_id}_documents",
                extracted_metadata={
                    "compliance_rating": "partial",
                    "curfew_compliance": "partial - 1 violation (02/10, 9:47 PM)",
                    "school_compliance": "non_compliant - 6 unexcused absences Feb",
                    "drug_test_result": "negative",
                    "no_contact_compliance": "unverified - circumstantial concern",
                    "community_service_progress": "8/40 hours",
                    "concerns_flagged": [
                        "curfew_violation", "school_attendance",
                        "possible_trey_contact", "lack_of_engagement"
                    ],
                    "strengths_noted": [
                        "clean_drug_test", "community_service_participation", "no_violence"
                    ],
                    "risk_level": "medium",
                },
            ),
            DocumentRef(
                user_id=marcus_id,
                filename="Email_DeniseCole_to_WestwoodHS_Feb2025.pdf",
                document_type="parent_communication",
                processing_status="completed",
                chunk_count=3,
                chroma_collection=f"user_{marcus_id}_documents",
                extracted_metadata={
                    "author": "Denise Cole (grandmother/guardian)",
                    "tone_assessment": "frustrated",
                    "key_claims": [
                        "iep_referral_not_processed",
                        "school_not_helping",
                        "mother_visits_destabilize_marcus",
                        "coach_williams_is_positive_influence",
                    ],
                    "requests_made": [
                        "meeting_this_month", "iep_process_initiated", "academic_support"
                    ],
                    "positive_adults_identified": ["coach_williams", "ms_rivera"],
                },
            ),
            DocumentRef(
                user_id=marcus_id,
                filename="MH_Intake_Assessment_MarcusCole_Dec2024.pdf",
                document_type="medical_mental_health",
                processing_status="completed",
                chunk_count=7,
                chroma_collection=f"user_{marcus_id}_documents",
                extracted_metadata={
                    "diagnoses": ["adjustment_disorder_mixed_F43.25"],
                    "rule_outs": ["ADHD_combined_F90.2", "PTSD_F43.10"],
                    "trauma_history": True,
                    "phq_a_score": 8,
                    "suicidal_ideation": False,
                    "self_harm_history": False,
                    "risk_level": "low_moderate",
                    "therapy_type": "CBT with trauma-informed approach",
                    "therapy_compliance": "4/8 sessions (50%)",
                    "medications": [],
                    "safe_harbor_floor": "yellow",
                },
            ),
        ]
        for doc in docs:
            db.add(doc)

        # -- Mentor Note --
        mentor_note = MentorNote(
            user_id=marcus_id,
            mentor_id="mentor_ray_001",
            mentor_name="Coach Ray Patterson",
            note_type="observation",
            raw_content=(
                "Marcus was quiet today. Seemed distracted. "
                "Mentioned problems at home but wouldn't elaborate. "
                "He's a good kid but he's carrying too much. "
                "I wish his mama would get her act together."
            ),
            sanitized_content=(
                "Marcus appeared subdued and distracted during session. "
                "Referenced unspecified home difficulties but declined to elaborate. "
                "Emotional load appears elevated."
            ),
            is_sanitized=True,
        )
        db.add(mentor_note)

        # -- Trust Score (Day 3) --
        trust_score = TrustScore(
            user_id=marcus_id,
            score_date=date(2025, 3, 12),
            consistency_c=3,
            weight_w=1.5,
            honesty_bonus_h=25.0,
            regulation_bonus_r=0.0,
            mentor_vouch_m=0.0,
            penalty_p=10.0,
            time_t=3,
            total_score=0.0,
        )
        trust_score.calculate()
        db.add(trust_score)

        # -- Seed Patterns (Literature-Based) --
        patterns = [
            Pattern(
                trap_type="peer_pressure",
                user_profile={
                    "heat_level": "high", "vibe": "guarded",
                    "character": "challenger", "user_type": "juvenile_justice"
                },
                intervention_used="DBT_opposite_action",
                outcome="positive",
                confidence=0.7,
                context_tags=["evening", "first_month"],
                source="literature",
            ),
            Pattern(
                trap_type="financial_stress",
                user_profile={
                    "heat_level": "high", "vibe": "angry",
                    "character": "straight_shooter", "user_type": "at_risk"
                },
                intervention_used="reframe_and_plan",
                outcome="positive",
                confidence=0.6,
                context_tags=["weekday", "school_stress"],
                source="literature",
            ),
            Pattern(
                trap_type="home_instability",
                user_profile={
                    "heat_level": "high", "vibe": "storm",
                    "character": "navigator", "user_type": "at_risk"
                },
                intervention_used="grounding_exercise_5_4_3_2_1",
                outcome="positive",
                confidence=0.8,
                context_tags=["crisis", "evening"],
                source="literature",
            ),
        ]
        for p in patterns:
            db.add(p)

        await db.commit()
        print("\nSeed data loaded successfully!")
        print(f"  Users: 1 (Marcus Cole)")
        print(f"  Documents: {len(docs)}")
        print(f"  Patterns: {len(patterns)}")
        print(f"  Mentor Notes: 1")
        print(f"  Trust Scores: 1 (Day 3 score: {trust_score.total_score:.1f})")


if __name__ == "__main__":
    asyncio.run(seed())
