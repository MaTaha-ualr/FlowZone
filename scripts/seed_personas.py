"""
Seed Script: Remaining 4 Test Personas
=========================================
Loads Aaliyah Jenkins, Jordan Rivera, DeShawn Mitchell, and Kaya Thompson.

Run AFTER seed_data.py (which loads Marcus Cole):
    python -m scripts.seed_personas

Or via Docker:
    docker compose exec app python -m scripts.seed_personas
"""

import asyncio
import sys
from datetime import datetime, date
from uuid import uuid4

sys.path.insert(0, ".")

from app.database import engine, async_session, Base
from app.models import *  # noqa: F401, F403
from app.core.constants import Character, SafeHarborLevel, TrustTier


async def seed_personas():
    """Insert the remaining 4 test personas."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:

        # ============================================================
        # PERSONA 2: Aaliyah Jenkins (Juvenile Justice — Navigator path)
        # ============================================================
        aaliyah_id = uuid4()
        aaliyah = User(
            id=aaliyah_id,
            name="Aaliyah Jenkins",
            age=16,
            date_of_birth=datetime(2009, 9, 3),
            school_name="Central High School",
            city="Memphis",
            state="Tennessee",
            user_type="juvenile_justice",
            has_probation=True,
            has_case_worker=False,
            intake_completed=True,
            intake_answers={
                "q1_intent": "win_freedom",
                "q2_heat_level": 9,
                "q3_trap": "temper",
                "q4_autonomy_prize": "fewer_meetings",
                "q5_collaboration": "well_see",
            },
            baseline_trust_score=55.0,
            current_trust_score=55.0,
            heat_level=9,
            weight_multiplier=1.5,
            current_character=Character.NAVIGATOR,
            current_tier=TrustTier.THE_WATCH,
            check_in_streak=0,
            safe_harbor_floor=SafeHarborLevel.YELLOW,
            has_trauma_history=True,
            has_crisis_history=True,
        )
        db.add(aaliyah)
        print(f"  Added: Aaliyah Jenkins ({aaliyah_id})")

        # School data
        db.add(SchoolData(
            user_id=aaliyah_id,
            school_name="Central High School",
            gpa=3.2,
            attendance_rate=0.85,
            tardiness_count=4,
            classes_failing=[],
            classes_excelling=["AP English", "Biology", "Drama"],
            disciplinary_incidents=[
                {"date": "2024-10-15", "type": "assault", "consequence": "10_day_suspension"},
                {"date": "2024-11-01", "type": "verbal_altercation", "consequence": "detention"},
            ],
            has_iep=False,
            athletic_eligible=True,
            source="manual",
            academic_period="Fall 2024",
        ))

        # Documents
        aaliyah_docs = [
            DocumentRef(
                user_id=aaliyah_id,
                filename="Aaliyah_Jenkins_Disposition_Order_JV-2024-01293.pdf",
                document_type="court_legal",
                processing_status="completed",
                chunk_count=7,
                chroma_collection=f"user_{aaliyah_id}_documents",
                extracted_metadata={
                    "case_number": "JV-2024-01293",
                    "charge": "Simple Assault, Class A Misdemeanor",
                    "context": "Defendant struck a male student who was physically bullying her younger brother (age 11) in the school hallway",
                    "dates": {"issued": "2024-11-20", "probation_end": "2025-05-20"},
                    "conditions": ["anger_management_program", "weekly_checkin", "no_contact_victim", "school_attendance"],
                    "risk_level": "low",
                    "mitigating_factors": ["defending_sibling", "no_prior_record", "strong_academics"],
                },
            ),
            DocumentRef(
                user_id=aaliyah_id,
                filename="Central_HS_ReportCard_Fall2024_AaliyahJenkins.pdf",
                document_type="school_record",
                processing_status="completed",
                chunk_count=4,
                chroma_collection=f"user_{aaliyah_id}_documents",
                extracted_metadata={
                    "gpa": 3.2,
                    "attendance_rate": 0.85,
                    "note": "Significant GPA drop from 3.8 pre-incident. Student was on honor roll prior to October.",
                    "teacher_comments": "Aaliyah is exceptionally bright and articulate but has become withdrawn since the incident. She participates less in class discussions.",
                },
            ),
            DocumentRef(
                user_id=aaliyah_id,
                filename="MH_Assessment_AaliyahJenkins_Nov2024.pdf",
                document_type="medical_mental_health",
                processing_status="completed",
                chunk_count=6,
                chroma_collection=f"user_{aaliyah_id}_documents",
                extracted_metadata={
                    "diagnoses": ["PTSD_F43.10"],
                    "trauma_history": True,
                    "trauma_context": "Witnessed domestic violence in home ages 6-10. Father was removed by CPS. Assault on student was a protective response triggered by witnessing her brother being physically threatened.",
                    "phq_a_score": 14,
                    "suicidal_ideation": False,
                    "self_harm_history": False,
                    "therapy_type": "Trauma-focused CBT",
                    "therapy_compliance": "6/6 sessions (100%)",
                    "medications": [{"name": "sertraline", "dose": "50mg", "compliance": "consistent"}],
                    "risk_level": "moderate",
                    "safe_harbor_floor": "yellow",
                },
            ),
            DocumentRef(
                user_id=aaliyah_id,
                filename="Parent_Email_JenkinsToJudge_Jan2025.pdf",
                document_type="parent_communication",
                processing_status="completed",
                chunk_count=3,
                chroma_collection=f"user_{aaliyah_id}_documents",
                extracted_metadata={
                    "author": "Ms. Tanya Jenkins (mother)",
                    "tone_assessment": "desperate",
                    "key_claims": [
                        "daughter_was_protecting_sibling",
                        "school_failed_to_protect_brother",
                        "legal_fees_devastating_family",
                        "daughter_was_honor_student",
                    ],
                    "requests_made": ["reduced_probation", "record_expungement"],
                },
            ),
        ]
        for doc in aaliyah_docs:
            db.add(doc)

        # Mentor note
        db.add(MentorNote(
            user_id=aaliyah_id,
            mentor_id="mentor_davis_001",
            mentor_name="Ms. Karen Davis",
            note_type="observation",
            raw_content="Aaliyah is angry at everyone and I can't blame her. She did the right thing protecting her brother and got punished for it. She needs someone to tell her that. She's brilliant but she's shutting down.",
            sanitized_content="Aaliyah presents with elevated frustration directed at the justice system. She perceives her involvement as unjust given the protective context of the incident. Academic disengagement is increasing despite strong capability.",
            is_sanitized=True,
        ))

        # Trust score
        ts = TrustScore(
            user_id=aaliyah_id, score_date=date(2025, 3, 12),
            consistency_c=0, weight_w=1.5, honesty_bonus_h=0,
            regulation_bonus_r=0, mentor_vouch_m=0, penalty_p=0, time_t=1,
        )
        ts.calculate()
        db.add(ts)

        # ============================================================
        # PERSONA 3: Jordan Rivera (At-Risk — Navigator/Strategist path)
        # ============================================================
        jordan_id = uuid4()
        jordan = User(
            id=jordan_id,
            name="Jordan Rivera",
            age=14,
            date_of_birth=datetime(2011, 3, 17),
            school_name="Riverside Middle School",
            city="Memphis",
            state="Tennessee",
            user_type="at_risk",
            has_probation=False,
            has_case_worker=True,
            intake_completed=True,
            intake_answers={
                "q1_intent": "check_box",
                "q2_heat_level": 4,
                "q3_trap": "home",
                "q4_autonomy_prize": "trust_to_walk",
                "q5_collaboration": "well_see",
            },
            baseline_trust_score=70.0,
            current_trust_score=70.0,
            heat_level=4,
            weight_multiplier=1.0,
            current_character=Character.NAVIGATOR,
            current_tier=TrustTier.THE_WATCH,
            check_in_streak=0,
            safe_harbor_floor=SafeHarborLevel.YELLOW,
            has_trauma_history=True,
            has_crisis_history=False,
        )
        db.add(jordan)
        print(f"  Added: Jordan Rivera ({jordan_id})")

        # School data
        db.add(SchoolData(
            user_id=jordan_id,
            school_name="Riverside Middle School",
            gpa=2.4,
            attendance_rate=0.58,
            tardiness_count=22,
            classes_failing=["Math 8", "Science 8"],
            classes_excelling=["Language Arts"],
            disciplinary_incidents=[],
            has_iep=False,
            athletic_eligible=None,
            source="manual",
            academic_period="Fall 2024",
        ))

        # Documents — Jordan has NO court docs (not in justice system)
        jordan_docs = [
            DocumentRef(
                user_id=jordan_id,
                filename="Riverside_MS_ReportCard_Fall2024_JordanRivera.pdf",
                document_type="school_record",
                processing_status="completed",
                chunk_count=4,
                chroma_collection=f"user_{jordan_id}_documents",
                extracted_metadata={
                    "gpa": 2.4,
                    "attendance_rate": 0.58,
                    "truancy_flag": True,
                    "counselor_notes": "Jordan is creative and thoughtful in Language Arts but rarely attends other classes. Suspected home neglect — often arrives without lunch, wearing same clothes multiple days. School social worker assigned.",
                },
            ),
            DocumentRef(
                user_id=jordan_id,
                filename="SocialWorker_Report_JordanRivera_Feb2025.pdf",
                document_type="caseworker_report",
                processing_status="completed",
                chunk_count=5,
                chroma_collection=f"user_{jordan_id}_documents",
                extracted_metadata={
                    "report_type": "progress_note",
                    "author_role": "social_worker",
                    "compliance_rating": "partial",
                    "concerns_flagged": ["suspected_neglect", "social_isolation", "gender_identity_conflict", "family_rejection"],
                    "strengths_noted": ["creative_writing_talent", "empathetic_nature", "self_aware"],
                    "home_environment": {
                        "stability": "unstable",
                        "primary_caregivers": "both parents present but emotionally unavailable",
                        "concerns": ["parents_dismissive_of_identity", "minimal_supervision", "food_insecurity"],
                    },
                    "recommendations": ["therapy_referral", "lgbtq_support_group", "school_meal_program"],
                },
            ),
            DocumentRef(
                user_id=jordan_id,
                filename="Parent_Communication_Rivera_Jan2025.pdf",
                document_type="parent_communication",
                processing_status="completed",
                chunk_count=2,
                chroma_collection=f"user_{jordan_id}_documents",
                extracted_metadata={
                    "author": "Mr. Carlos Rivera (father)",
                    "tone_assessment": "dismissive",
                    "key_claims": ["kid_is_just_going_through_a_phase", "school_is_overreacting", "we_handle_things_at_home"],
                    "context": "Father responded to school's truancy concern letter. Minimized attendance issues and dismissed counselor's recommendation for support services.",
                },
            ),
        ]
        for doc in jordan_docs:
            db.add(doc)

        db.add(MentorNote(
            user_id=jordan_id,
            mentor_id="mentor_santos_001",
            mentor_name="Ms. Elena Santos",
            note_type="observation",
            raw_content="Jordan is painfully quiet but writes the most beautiful poetry I've ever seen from a kid this age. They recently came out as non-binary to me but said their parents 'would kill them' if they knew. I don't think that's literal but the fear is real. This kid needs a safe adult desperately.",
            sanitized_content="Jordan demonstrates exceptional creative writing ability and emotional depth. Has disclosed gender identity to mentor but reports significant anxiety about family acceptance. Appears to be seeking a trusted adult connection. Emotional support needs are high.",
            is_sanitized=True,
        ))

        ts2 = TrustScore(
            user_id=jordan_id, score_date=date(2025, 3, 12),
            consistency_c=0, weight_w=1.0, honesty_bonus_h=50,
            regulation_bonus_r=0, mentor_vouch_m=0, penalty_p=0, time_t=1,
        )
        ts2.calculate()
        db.add(ts2)

        # ============================================================
        # PERSONA 4: DeShawn "Dee" Mitchell (At-Risk — Challenger/Navigator transition)
        # ============================================================
        deshawn_id = uuid4()
        deshawn = User(
            id=deshawn_id,
            name="DeShawn Mitchell",
            age=15,
            date_of_birth=datetime(2010, 1, 22),
            school_name="Westwood High School",
            city="Memphis",
            state="Tennessee",
            user_type="at_risk",
            has_probation=False,
            has_case_worker=False,
            intake_completed=True,
            intake_answers={
                "q1_intent": "win_freedom",
                "q2_heat_level": 7,
                "q3_trap": "temper",
                "q4_autonomy_prize": "trust_to_walk",
                "q5_collaboration": "yes",
            },
            baseline_trust_score=45.0,
            current_trust_score=45.0,
            heat_level=7,
            weight_multiplier=1.2,
            current_character=Character.CHALLENGER,
            current_tier=TrustTier.THE_WATCH,
            check_in_streak=1,
            last_check_in=datetime(2025, 3, 11, 19, 30),
            safe_harbor_floor=SafeHarborLevel.YELLOW,
            has_trauma_history=True,
            has_crisis_history=False,
        )
        db.add(deshawn)
        print(f"  Added: DeShawn Mitchell ({deshawn_id})")

        # School data — was a star athlete, now spiraling
        db.add(SchoolData(
            user_id=deshawn_id,
            school_name="Westwood High School",
            gpa=2.6,
            attendance_rate=0.78,
            tardiness_count=8,
            classes_failing=["Algebra I"],
            classes_excelling=["Physical Education", "History"],
            disciplinary_incidents=[
                {"date": "2025-01-15", "type": "fight", "consequence": "3_day_suspension"},
                {"date": "2025-02-03", "type": "fight", "consequence": "5_day_suspension"},
                {"date": "2025-02-20", "type": "fight", "consequence": "10_day_suspension_expulsion_hearing"},
            ],
            has_iep=False,
            athletic_eligible=False,
            source="manual",
            academic_period="Spring 2025",
        ))

        deshawn_docs = [
            DocumentRef(
                user_id=deshawn_id,
                filename="Westwood_HS_ReportCard_Spring2025_DeshawnMitchell.pdf",
                document_type="school_record",
                processing_status="completed",
                chunk_count=4,
                chroma_collection=f"user_{deshawn_id}_documents",
                extracted_metadata={
                    "gpa": 2.6,
                    "gpa_previous": 3.4,
                    "note": "Dramatic decline from 3.4 GPA (Fall 2024). Was captain of JV basketball team. Now ineligible due to disciplinary record. 3 fights in 5 weeks, all initiated by DeShawn.",
                    "counselor_notes": "DeShawn's older brother Darius was shot in December 2024 and is now paralyzed from the waist down. DeShawn has not spoken about it to any adult at school. The anger is clearly connected.",
                },
            ),
            DocumentRef(
                user_id=deshawn_id,
                filename="MH_Referral_DeshawnMitchell_Mar2025.pdf",
                document_type="medical_mental_health",
                processing_status="completed",
                chunk_count=4,
                chroma_collection=f"user_{deshawn_id}_documents",
                extracted_metadata={
                    "record_type": "referral",
                    "referral_reason": "Escalating aggression following brother's shooting. Three fights in school in five weeks.",
                    "diagnoses": [],
                    "rule_outs": ["PTSD_F43.10", "adjustment_disorder_F43.25"],
                    "trauma_history": True,
                    "trauma_context": "Older brother Darius (18) shot in gang-related incident Dec 2024, resulting in paraplegia. DeShawn was not present but visited brother in ICU.",
                    "suicidal_ideation": False,
                    "self_harm_history": False,
                    "risk_level": "moderate_high",
                    "therapy_status": "not_yet_started",
                    "safe_harbor_floor": "yellow",
                },
            ),
            DocumentRef(
                user_id=deshawn_id,
                filename="Parent_Letter_MitchellFamily_Feb2025.pdf",
                document_type="parent_communication",
                processing_status="completed",
                chunk_count=3,
                chroma_collection=f"user_{deshawn_id}_documents",
                extracted_metadata={
                    "author": "Mrs. Keisha Mitchell (mother)",
                    "tone_assessment": "supportive",
                    "key_claims": [
                        "deshawn_changed_after_brothers_shooting",
                        "family_in_crisis",
                        "mother_caring_for_paralyzed_son_and_working",
                        "deshawn_feels_responsible",
                    ],
                    "context": "Mother wrote to principal explaining family circumstances. Requests leniency on expulsion hearing given trauma context.",
                },
            ),
        ]
        for doc in deshawn_docs:
            db.add(doc)

        # DeShawn shares mentor with Marcus (Coach Ray)
        db.add(MentorNote(
            user_id=deshawn_id,
            mentor_id="mentor_ray_001",
            mentor_name="Coach Ray Patterson",
            note_type="risk_flag",
            risk_flag_level="yellow",
            raw_content="Dee is going to get himself expelled or worse. Every time someone looks at him wrong he swings. I've known this kid since he was 12 and he was the sweetest, hardest-working athlete I'd ever coached. Since Darius got shot, it's like a different kid. He won't talk about it. He just fights. I'm scared for him.",
            sanitized_content="DeShawn displays escalating reactive aggression in response to perceived provocations. This represents a significant behavioral change from his previous baseline. The behavioral shift correlates temporally with a traumatic family event. He is not engaging in verbal processing of the underlying trauma. Risk level elevated.",
            is_sanitized=True,
        ))

        ts3 = TrustScore(
            user_id=deshawn_id, score_date=date(2025, 3, 11),
            consistency_c=1, weight_w=1.2, honesty_bonus_h=0,
            regulation_bonus_r=0, mentor_vouch_m=0, penalty_p=0, time_t=1,
        )
        ts3.calculate()
        db.add(ts3)

        # ============================================================
        # PERSONA 5: Kaya Thompson (At-Risk — Positive Masking / Strategist path)
        # ============================================================
        kaya_id = uuid4()
        kaya = User(
            id=kaya_id,
            name="Kaya Thompson",
            age=14,
            date_of_birth=datetime(2011, 7, 8),
            school_name="Lakewood Middle School",
            city="Memphis",
            state="Tennessee",
            user_type="at_risk",
            has_probation=False,
            has_case_worker=True,
            intake_completed=True,
            intake_answers={
                "q1_intent": "win_freedom",
                "q2_heat_level": 3,
                "q3_trap": "dont_know",
                "q4_autonomy_prize": "trust_to_walk",
                "q5_collaboration": "yes",
            },
            baseline_trust_score=25.0,
            current_trust_score=25.0,
            heat_level=3,
            weight_multiplier=1.0,
            current_character=Character.STRATEGIST,
            current_tier=TrustTier.THE_WATCH,
            check_in_streak=5,
            last_check_in=datetime(2025, 3, 12, 16, 0),
            safe_harbor_floor=SafeHarborLevel.GREEN,
            has_trauma_history=True,
            has_crisis_history=False,
        )
        db.add(kaya)
        print(f"  Added: Kaya Thompson ({kaya_id})")

        # School data — hardworking but behind
        db.add(SchoolData(
            user_id=kaya_id,
            school_name="Lakewood Middle School",
            gpa=2.2,
            attendance_rate=0.92,
            tardiness_count=2,
            classes_failing=[],
            classes_excelling=[],
            disciplinary_incidents=[],
            has_iep=True,
            iep_accommodations=["extended_test_time", "modified_assignments", "check_in_with_counselor"],
            athletic_eligible=True,
            source="manual",
            academic_period="Fall 2024",
        ))

        kaya_docs = [
            DocumentRef(
                user_id=kaya_id,
                filename="Lakewood_MS_ReportCard_Fall2024_KayaThompson.pdf",
                document_type="school_record",
                processing_status="completed",
                chunk_count=4,
                chroma_collection=f"user_{kaya_id}_documents",
                extracted_metadata={
                    "gpa": 2.2,
                    "attendance_rate": 0.92,
                    "note": "Kaya is conscientious and eager to please. She completes all work but struggles with grade-level material due to gaps from multiple school changes (3 schools in 2 years). IEP accommodations helping. No behavioral concerns — teachers describe her as 'a delight.'",
                    "concern": "Teachers report Kaya never asks for help even when struggling. She would rather turn in wrong work than admit she doesn't understand.",
                },
            ),
            DocumentRef(
                user_id=kaya_id,
                filename="CPS_Placement_History_KayaThompson.pdf",
                document_type="caseworker_report",
                processing_status="completed",
                chunk_count=6,
                chroma_collection=f"user_{kaya_id}_documents",
                extracted_metadata={
                    "report_type": "placement_history",
                    "author_role": "case_manager",
                    "placements": [
                        {"number": 1, "type": "kinship_care", "duration": "8_months", "reason_ended": "relative_unable_to_continue"},
                        {"number": 2, "type": "foster_family", "duration": "14_months", "reason_ended": "foster_parent_relocation"},
                        {"number": 3, "type": "foster_family", "duration": "4_months_current", "status": "active"},
                    ],
                    "concerns_flagged": ["attachment_disruption", "people_pleasing_as_survival", "fear_of_displacement"],
                    "strengths_noted": ["resilient", "academically_motivated", "kind_to_peers", "no_behavioral_issues"],
                    "risk_level": "moderate",
                    "note": "Kaya's compliance and agreeableness, while positive on the surface, may mask significant emotional distress. She has learned that 'being good' prevents being moved. This creates a pattern where she suppresses all negative emotions.",
                },
            ),
            DocumentRef(
                user_id=kaya_id,
                filename="MH_Progress_KayaThompson_Jan2025.pdf",
                document_type="medical_mental_health",
                processing_status="completed",
                chunk_count=5,
                chroma_collection=f"user_{kaya_id}_documents",
                extracted_metadata={
                    "diagnoses": ["adjustment_disorder_F43.20"],
                    "trauma_history": True,
                    "trauma_context": "Multiple placement disruptions. Bio parents had parental rights terminated when Kaya was 9 due to chronic neglect. Kaya has not seen bio parents in 3 years.",
                    "phq_a_score": 6,
                    "suicidal_ideation": False,
                    "self_harm_history": False,
                    "therapy_type": "Attachment-focused therapy",
                    "therapy_compliance": "8/8 sessions (100%)",
                    "key_insight": "Kaya presents as happy and compliant in every session. Therapist notes this is consistent with a 'positive masking' pattern — she has learned that showing distress leads to being moved. Breakthrough moments are rare but significant.",
                    "risk_level": "low_moderate",
                },
            ),
            DocumentRef(
                user_id=kaya_id,
                filename="FosterParent_Note_KayaThompson_Feb2025.pdf",
                document_type="parent_communication",
                processing_status="completed",
                chunk_count=2,
                chroma_collection=f"user_{kaya_id}_documents",
                extracted_metadata={
                    "author": "Mrs. Linda Chen (current foster parent)",
                    "tone_assessment": "supportive",
                    "key_claims": [
                        "kaya_is_wonderful_child",
                        "never_causes_problems",
                        "concerned_she_never_cries_or_gets_angry",
                        "found_her_crying_alone_at_3am_once",
                        "kaya_denied_anything_was_wrong",
                    ],
                    "context": "Foster parent reaching out to case manager because she senses something beneath Kaya's perfect behavior. Wants to help but doesn't know how to get Kaya to open up.",
                },
            ),
        ]
        for doc in kaya_docs:
            db.add(doc)

        db.add(MentorNote(
            user_id=kaya_id,
            mentor_id="mentor_chen_001",
            mentor_name="Mrs. Linda Chen",
            note_type="observation",
            raw_content="Kaya is the easiest kid in the world. She does everything right. She never complains. And that's what scares me. I found her crying in the bathroom at 3am and when I asked what was wrong she smiled and said 'nothing, I'm fine!' and went back to bed. Something is very wrong underneath all that fine.",
            sanitized_content="Kaya consistently presents as positive and compliant. Foster parent reports an instance of nighttime distress that Kaya immediately masked when approached. The discrepancy between observed distress and verbal self-report suggests significant emotional suppression.",
            is_sanitized=True,
        ))

        ts4 = TrustScore(
            user_id=kaya_id, score_date=date(2025, 3, 12),
            consistency_c=5, weight_w=1.0, honesty_bonus_h=0,
            regulation_bonus_r=0, mentor_vouch_m=0, penalty_p=0, time_t=5,
        )
        ts4.calculate()
        db.add(ts4)

        # ============================================================
        # ADDITIONAL CROSS-USER PATTERNS
        # ============================================================
        extra_patterns = [
            Pattern(
                trap_type="anger",
                user_profile={"heat_level": "high", "vibe": "angry", "character": "navigator"},
                intervention_used="box_breathing_tactical_reset",
                outcome="positive", confidence=0.75,
                context_tags=["post_fight", "school_incident"], source="literature",
            ),
            Pattern(
                trap_type="positive_masking",
                user_profile={"heat_level": "low", "vibe": "solid", "character": "strategist"},
                intervention_used="gentle_curiosity_probe",
                outcome="positive", confidence=0.5,
                context_tags=["foster_care", "attachment_disruption"], source="literature",
            ),
            Pattern(
                trap_type="grief",
                user_profile={"heat_level": "high", "vibe": "storm", "character": "navigator"},
                intervention_used="grounding_exercise_5_4_3_2_1",
                outcome="positive", confidence=0.7,
                context_tags=["loss", "violence_exposure"], source="literature",
            ),
            Pattern(
                trap_type="family_rejection",
                user_profile={"heat_level": "low", "vibe": "guarded", "character": "navigator"},
                intervention_used="identity_affirmation",
                outcome="positive", confidence=0.6,
                context_tags=["lgbtq", "coming_out", "unsupportive_family"], source="literature",
            ),
        ]
        for p in extra_patterns:
            db.add(p)

        await db.commit()

        print("\nAll personas loaded successfully!")
        print(f"  Aaliyah Jenkins  — Juvenile Justice, PTSD, Navigator path")
        print(f"  Jordan Rivera    — At-Risk, non-binary, neglect, Navigator/Strategist")
        print(f"  DeShawn Mitchell — At-Risk, brother shot, grief, Challenger/Navigator")
        print(f"  Kaya Thompson    — At-Risk, foster care, positive masking, Strategist")
        print(f"  Documents: {len(aaliyah_docs) + len(jordan_docs) + len(deshawn_docs) + len(kaya_docs)}")
        print(f"  Patterns: {len(extra_patterns)}")
        print(f"  Mentor Notes: 4")


if __name__ == "__main__":
    asyncio.run(seed_personas())
