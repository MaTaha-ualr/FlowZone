"""
Safe Harbor Protocol
=====================
Manages the three-tier privacy/safety system:
  Green (The Vault)   — Private, only youth + AI
  Yellow (The Support) — Trends shared with mentors for intervention
  Red (The Emergency)  — Imminent danger, system interrupt, alert Rainbow Circle

Architecture Note:
    The Safe Harbor level is determined per-session and can escalate
    (never de-escalate) within a session. A user with trauma history
    starts at Yellow floor minimum. Red requires human review to reset.
"""

from app.core.constants import SafeHarborLevel

# Keywords/phrases that trigger escalation checks
# These are checked by the analytical model, not by keyword matching alone
RED_ESCALATION_INDICATORS = [
    "self_harm_ideation",
    "suicidal_ideation",
    "homicidal_ideation",
    "immediate_danger",
    "abuse_disclosure",
    "weapon_access",
]

YELLOW_ESCALATION_INDICATORS = [
    "trauma_reference",
    "substance_use_disclosure",
    "violence_exposure",
    "emotional_flooding",
    "family_crisis",
    "running_away",
]


def determine_floor(has_trauma_history: bool, has_crisis_history: bool) -> SafeHarborLevel:
    """
    Determine the minimum Safe Harbor level for a user based on their profile.
    This floor can never be lowered — only the current level can rise above it.
    """
    if has_crisis_history:
        return SafeHarborLevel.YELLOW
    if has_trauma_history:
        return SafeHarborLevel.YELLOW
    return SafeHarborLevel.GREEN


def can_escalate(current: SafeHarborLevel, target: SafeHarborLevel) -> bool:
    """Safe Harbor levels can only escalate within a session, never de-escalate."""
    order = {SafeHarborLevel.GREEN: 0, SafeHarborLevel.YELLOW: 1, SafeHarborLevel.RED: 2}
    return order[target] > order[current]
