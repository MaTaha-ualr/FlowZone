"""
Context Builder — The Truth Engine's Data Assembly
=====================================================
Before every LLM call, this service assembles the user-specific context
that gets injected into the system prompt alongside the character personality.

This is the implementation of the Truth Engine's "structured context injection"
discussed in the RAG architecture. It pulls from:
    - User profile (intake answers, current scores)
    - School data (GPA, attendance — for discrepancy detection)
    - Recent mentor notes (sanitized only)
    - Document metadata (conditions, flags — NOT raw document text)
    - Session history (traps mentioned, vibe trends)

The assembled context is a structured text block that the LLM reads
to understand the youth's current situation before responding.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID

from app.models.user import User
from app.models.school_data import SchoolData
from app.models.mentor_note import MentorNote
from app.models.document_ref import DocumentRef
from app.models.trust_score import TrustScore
from app.models.session import Session
from app.core.constants import VIBE_EMOJI_MAP, Vibe, TrustTier, TRUST_TIER_THRESHOLDS


async def build_user_context(user_id: UUID, db: AsyncSession) -> str:
    """
    Assemble the full user context string for injection into the system prompt.
    Target: ~200-400 tokens. Enough for the LLM to understand the situation,
    not so much that it dominates the context window.
    """
    parts = []

    # ---- User Profile ----
    user = await db.get(User, user_id)
    if not user:
        return "[No user context available]"

    parts.append(f"USER: {user.name}, age {user.age}, {user.user_type.replace('_', ' ')}")
    parts.append(f"Current trust score: {user.current_trust_score:.0f} | "
                 f"Tier: {user.current_tier} | Streak: {user.check_in_streak} days")

    if user.intake_answers:
        answers = user.intake_answers
        parts.append(f"Intake: Intent='{answers.get('q1_intent')}', "
                     f"Heat={answers.get('q2_heat_level')}/10, "
                     f"Trap='{answers.get('q3_trap')}', "
                     f"Wants='{answers.get('q4_autonomy_prize')}'")

    # ---- School Data ----
    school_result = await db.execute(
        select(SchoolData)
        .where(SchoolData.user_id == user_id)
        .order_by(desc(SchoolData.last_synced))
        .limit(1)
    )
    school = school_result.scalar_one_or_none()
    if school:
        parts.append(f"\nSCHOOL: {school.school_name or 'Unknown'} | "
                     f"GPA: {school.gpa} | Attendance: {school.attendance_rate:.0%}")
        if school.classes_failing:
            parts.append(f"  Failing: {', '.join(school.classes_failing)}")
        if school.classes_excelling:
            parts.append(f"  Excelling: {', '.join(school.classes_excelling)}")
        if school.has_iep:
            parts.append(f"  IEP active: {', '.join(school.iep_accommodations or [])}")
        if school.athletic_eligible is False:
            parts.append("  Athletic eligibility: INELIGIBLE")

    # ---- Key Document Metadata (conditions, flags) ----
    doc_result = await db.execute(
        select(DocumentRef)
        .where(DocumentRef.user_id == user_id)
        .where(DocumentRef.processing_status == "completed")
    )
    docs = doc_result.scalars().all()

    court_conditions = []
    no_contact = []
    risk_level = None
    therapy_info = None

    for doc in docs:
        meta = doc.extracted_metadata or {}

        if doc.document_type == "court_legal":
            conditions = meta.get("conditions", [])
            court_conditions.extend(conditions)
            nc = meta.get("no_contact_persons", [])
            no_contact.extend([p.get("name", "unknown") for p in nc])
            risk_level = meta.get("risk_level", risk_level)

        elif doc.document_type == "medical_mental_health":
            diagnoses = meta.get("diagnoses", [])
            if diagnoses:
                parts.append(f"\nCLINICAL: {', '.join(diagnoses)}")
            if meta.get("therapy_type"):
                therapy_info = meta["therapy_type"]
                compliance = meta.get("therapy_compliance", "unknown")
                parts.append(f"  Therapy: {therapy_info} (compliance: {compliance})")
            if meta.get("trauma_history"):
                parts.append("  ⚠️ Trauma history documented")

    if court_conditions:
        parts.append(f"\nCOURT CONDITIONS: {', '.join(court_conditions[:6])}")
    if no_contact:
        parts.append(f"NO-CONTACT ORDER: {', '.join(no_contact)}")
    if risk_level:
        parts.append(f"Risk level: {risk_level}")

    # ---- Recent Mentor Notes (sanitized) ----
    note_result = await db.execute(
        select(MentorNote)
        .where(MentorNote.user_id == user_id)
        .where(MentorNote.is_sanitized == True)
        .order_by(desc(MentorNote.created_at))
        .limit(2)
    )
    notes = note_result.scalars().all()
    if notes:
        parts.append("\nMENTOR OBSERVATIONS:")
        for note in notes:
            parts.append(f"  [{note.mentor_name}]: {note.sanitized_content}")

    # ---- Trust Score Trend ----
    score_result = await db.execute(
        select(TrustScore)
        .where(TrustScore.user_id == user_id)
        .order_by(desc(TrustScore.score_date))
        .limit(3)
    )
    scores = score_result.scalars().all()
    if scores:
        score_trend = [f"{s.score_date}: {s.total_score:.1f}" for s in scores]
        parts.append(f"\nTRUST SCORE TREND: {' → '.join(reversed(score_trend))}")

    # ---- Next Tier Info ----
    for tier, threshold in sorted(TRUST_TIER_THRESHOLDS.items(), key=lambda x: x[1]):
        if threshold > user.current_trust_score:
            gap = threshold - user.current_trust_score
            parts.append(f"Next tier ({tier}): {gap:.0f} points needed")
            break

    return "\n".join(parts)
