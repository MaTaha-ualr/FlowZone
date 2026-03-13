"""
RAG Classifier
=================
Determines WHEN to trigger RAG retrieval for a given message.
Not every message needs RAG — "I'm feeling angry" doesn't need a knowledge base lookup,
but "what are my rights if my PO shows up at school?" does.

This is a rule-based classifier for the MVP.
Can be upgraded to an LLM-based classifier later if needed.

Returns a RagDecision that tells the retriever what to search.
"""

import re
from dataclasses import dataclass
from app.core.constants import Character, Vibe, SafeHarborLevel


@dataclass
class RagDecision:
    """What the retriever should do for this message."""
    include_knowledge_base: bool = False
    include_user_docs: bool = False
    include_patterns: bool = False
    knowledge_filter: dict = None  # Optional ChromaDB metadata filter
    reason: str = "no_rag_needed"


# Keywords that trigger knowledge base retrieval
QUESTION_INDICATORS = ["?", "what", "how", "why", "can i", "should i", "do i", "am i", "is it"]
LEGAL_KEYWORDS = ["right", "legal", "law", "court", "judge", "lawyer", "probation", "violation",
                  "arrest", "search", "curfew", "expunge", "record", "hearing"]
RESOURCE_KEYWORDS = ["help", "hotline", "shelter", "food", "resource", "service", "program",
                     "support", "counselor", "therapist", "doctor"]
CRISIS_KEYWORDS = ["hurt", "harm", "die", "kill", "suicide", "cut", "end it", "give up",
                   "can't take", "no point", "not worth"]
SCHOOL_KEYWORDS = ["iep", "school", "grade", "teacher", "suspend", "expel", "attendance",
                   "failing", "homework", "eligibility"]
PERSONAL_REFERENCE_KEYWORDS = ["my court", "my po", "my grade", "my case", "my condition",
                               "my hearing", "my record", "my curfew", "my test"]


def classify(
    message: str,
    character: Character,
    vibe: Vibe = None,
    safe_harbor_level: SafeHarborLevel = SafeHarborLevel.GREEN,
    has_user_docs: bool = False,
) -> RagDecision:
    """
    Analyze a message and decide what RAG retrieval is needed.

    Args:
        message: The user's message text
        character: Currently active character
        vibe: User's selected vibe for this session
        safe_harbor_level: Current safe harbor level
        has_user_docs: Whether this user has documents in ChromaDB

    Returns:
        RagDecision with flags for what to retrieve
    """
    msg_lower = message.lower().strip()
    decision = RagDecision()

    # ---- Rule 1: Crisis always triggers ----
    if any(kw in msg_lower for kw in CRISIS_KEYWORDS):
        decision.include_knowledge_base = True
        decision.knowledge_filter = None  # Search all collections
        decision.include_user_docs = has_user_docs  # Check for crisis history
        decision.reason = "crisis_keywords_detected"
        return decision

    # ---- Rule 2: Safe Harbor Red — always retrieve ----
    if safe_harbor_level == SafeHarborLevel.RED:
        decision.include_knowledge_base = True
        decision.knowledge_filter = None
        decision.reason = "safe_harbor_red"
        return decision

    # ---- Rule 3: Navigator in crisis mode — therapeutic techniques ----
    if character == Character.NAVIGATOR and vibe in (Vibe.STORM, Vibe.ANGRY):
        decision.include_knowledge_base = True
        decision.reason = "navigator_crisis_mode"
        return decision

    # ---- Rule 4: Questions (contains ? or question words) ----
    is_question = "?" in msg_lower or any(
        msg_lower.startswith(q) or f" {q} " in msg_lower
        for q in QUESTION_INDICATORS
    )

    if is_question:
        # Legal question
        if any(kw in msg_lower for kw in LEGAL_KEYWORDS):
            decision.include_knowledge_base = True
            decision.include_user_docs = has_user_docs  # Check their court docs
            decision.reason = "legal_question"
            return decision

        # Resource question
        if any(kw in msg_lower for kw in RESOURCE_KEYWORDS):
            decision.include_knowledge_base = True
            decision.reason = "resource_question"
            return decision

        # School question
        if any(kw in msg_lower for kw in SCHOOL_KEYWORDS):
            decision.include_knowledge_base = True
            decision.include_user_docs = has_user_docs
            decision.reason = "school_question"
            return decision

        # General question — light retrieval
        decision.include_knowledge_base = True
        decision.reason = "general_question"
        return decision

    # ---- Rule 5: Personal document references ----
    if has_user_docs and any(kw in msg_lower for kw in PERSONAL_REFERENCE_KEYWORDS):
        decision.include_user_docs = True
        decision.reason = "personal_reference"
        return decision

    # ---- Rule 6: Challenger active + user mentions trap-related content ----
    if character == Character.CHALLENGER:
        trap_words = ["friend", "boy", "money", "offer", "tempt", "hook up", "deal"]
        if any(tw in msg_lower for tw in trap_words):
            decision.include_user_docs = has_user_docs  # Check court conditions
            decision.include_patterns = True  # What worked for similar users
            decision.reason = "challenger_trap_reference"
            return decision

    # ---- Rule 7: Strategist always benefits from patterns ----
    if character == Character.STRATEGIST:
        decision.include_patterns = True
        decision.reason = "strategist_pattern_lookup"
        return decision

    # ---- Default: No RAG needed ----
    # Short emotional expressions, greetings, continuations
    return decision

