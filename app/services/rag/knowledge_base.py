"""
Knowledge Base Content & Seeder
==================================
Populates the four global RAG collections:
    1. global_therapeutic  — CBT, DBT, grounding, regulation exercises
    2. global_legal        — Juvenile justice rights, IEP protections
    3. global_resources    — Crisis hotlines, Memphis-area resources
    4. global_playbooks    — Mask detection protocol, Safe Harbor Red, academic turnaround

Usage:
    from app.services.rag.knowledge_base import seed_all_knowledge
    await seed_all_knowledge(db)
"""

import logging
from app.services.rag.document_processor import ingest_text_directly
from app.services.rag import chroma_store

logger = logging.getLogger(__name__)


# ============================================================
# THERAPEUTIC TECHNIQUES (global_therapeutic)
# ============================================================

THERAPEUTIC_ENTRIES = [
    {
        "id": "ther_grounding_54321",
        "text": (
            "5-4-3-2-1 Grounding Technique\n\n"
            "When to use: The user is overwhelmed, panicking, dissociating, or experiencing "
            "emotional flooding. Works for storm and angry vibes.\n\n"
            "Steps to guide the user through:\n"
            "1. Name 5 things you can SEE right now.\n"
            "2. Name 4 things you can TOUCH. What do they feel like?\n"
            "3. Name 3 things you can HEAR right now.\n"
            "4. Name 2 things you can SMELL (or like the smell of).\n"
            "5. Name 1 thing you can TASTE (or like the taste of).\n\n"
            "After completion: Acknowledge the effort. 'You just completed a grounding exercise. "
            "That earns you Regulation Points. It wasn't easy, especially when your head is spinning. "
            "But you did it.'\n\n"
            "Tips: Keep your voice steady and slow. If the user gets stuck, offer suggestions. "
            "Don't rush them. If they can only do 3 of the 5 steps, that still counts."
        ),
        "metadata": {
            "category": "crisis", "framework": "general",
            "technique_name": "5-4-3-2-1 Grounding",
            "triggers": "panic,overwhelm,dissociation,flooding",
            "character_affinity": "navigator",
            "regulation_points": "true",
        },
    },
    {
        "id": "ther_dbt_opposite_action",
        "text": (
            "DBT Opposite Action\n\n"
            "When to use: The user's emotional urge is pushing them toward a destructive action. "
            "For example anger says fight, shame says hide, fear says avoid.\n\n"
            "Core principle: When an emotion is unjustified or acting on it would be destructive, "
            "do the OPPOSITE of what the emotion tells you to do.\n\n"
            "Examples for youth:\n"
            "- Anger says 'fight that kid' -> Opposite: walk away, put headphones on\n"
            "- Shame says 'don't go to school' -> Opposite: show up anyway\n"
            "- Fear says 'don't talk to your PO' -> Opposite: call your PO first\n"
            "- Boredom says 'hit up Trey' -> Opposite: text DeAndre, go to the gym\n\n"
            "How to frame it: 'Your anger is giving you bad intel right now. The opposite move "
            "is usually the one that earns you the most. What would the opposite look like?'\n\n"
            "Reward: Choosing opposite action earns Honesty Points if they disclose the urge, "
            "and Regulation Points if they execute the opposite."
        ),
        "metadata": {
            "category": "behavioral", "framework": "DBT",
            "technique_name": "Opposite Action",
            "triggers": "anger,shame,avoidance,peer_pressure",
            "character_affinity": "challenger,navigator",
        },
    },
    {
        "id": "ther_breathing_box",
        "text": (
            "Box Breathing (Tactical Reset)\n\n"
            "When to use: Quick regulation when the user needs to calm down before a decision. "
            "Can be done anywhere.\n\n"
            "Steps:\n"
            "1. Breathe IN for 4 seconds\n"
            "2. HOLD for 4 seconds\n"
            "3. Breathe OUT for 4 seconds\n"
            "4. HOLD for 4 seconds\n"
            "5. Repeat 3-4 times\n\n"
            "Frame for skeptical youth: 'This isn't meditation. Navy SEALs use this before combat. "
            "It literally changes your brain chemistry in 60 seconds. Try it once.'\n\n"
            "Completion earns Regulation Points. Set a 60-second timer."
        ),
        "metadata": {
            "category": "crisis", "framework": "general",
            "technique_name": "Box Breathing",
            "triggers": "anger,anxiety,pressure,pre_decision",
            "character_affinity": "navigator,straight_shooter",
            "regulation_points": "true",
        },
    },
    {
        "id": "ther_cbt_thought_record",
        "text": (
            "CBT Thought Record (Simplified)\n\n"
            "When to use: User stuck in negative thought patterns, catastrophizing. "
            "Good for Strategist character, solid or guarded vibes.\n\n"
            "Simplified version:\n"
            "1. THE SITUATION: What happened? Just facts.\n"
            "2. THE THOUGHT: What story are you telling yourself?\n"
            "3. THE EVIDENCE: What supports this thought? What contradicts it?\n"
            "4. THE REFRAME: Is there another way to see this?\n"
            "5. THE MOVE: What's one thing you can do differently?\n\n"
            "Example:\n"
            "Situation: 'PO called, wants to meet tomorrow.'\n"
            "Thought: 'I'm going to get locked up.'\n"
            "Evidence for: 'Missed curfew once.' Against: 'Clean drug test, community service.'\n"
            "Reframe: 'One curfew violation with clean record isn't lockup-level.'\n"
            "Move: 'Go prepared with community service log and attendance.'\n\n"
            "Frame: 'Your brain is a bad news anchor right now. Let's be the investigative journalist.'"
        ),
        "metadata": {
            "category": "long_term", "framework": "CBT",
            "technique_name": "Simplified Thought Record",
            "triggers": "catastrophizing,assumptions,anxiety,negative_patterns",
            "character_affinity": "strategist,navigator",
        },
    },
    {
        "id": "ther_motivational_interviewing",
        "text": (
            "Motivational Interviewing Principles (for AI Characters)\n\n"
            "These guide how characters converse, not techniques taught to youth.\n\n"
            "1. EXPRESS EMPATHY: Reflect without judgment.\n"
            "2. DEVELOP DISCREPANCY: Show gap between current state and goals.\n"
            "3. ROLL WITH RESISTANCE: Don't argue. Agree and redirect.\n"
            "4. SUPPORT SELF-EFFICACY: Remind them of past successes.\n\n"
            "What NOT to do:\n"
            "- Don't argue for change (they'll argue against)\n"
            "- Don't tell them what to do (they'll resist harder)\n"
            "- Don't use 'but' after validation\n\n"
            "FlowZone adaptation: Reframe MI through strategy and self-interest. "
            "'I'm not trying to make you a better person. I'm helping you get what you want faster.'"
        ),
        "metadata": {
            "category": "framework", "framework": "motivational_interviewing",
            "technique_name": "MI Core Principles",
            "triggers": "resistance,disengagement,ambivalence",
            "character_affinity": "challenger,navigator,strategist",
        },
    },
]


# ============================================================
# LEGAL / RIGHTS (global_legal)
# ============================================================

LEGAL_ENTRIES = [
    {
        "id": "legal_juvenile_rights_interrogation",
        "text": (
            "Juvenile Rights During Police Questioning\n\n"
            "1. RIGHT TO REMAIN SILENT.\n"
            "2. RIGHT TO AN ATTORNEY. If you can't afford one, one will be appointed.\n"
            "3. MIRANDA WARNINGS must be read before custodial interrogation.\n"
            "4. SCHOOL ADMINS are NOT police. They CAN question without Miranda.\n"
            "5. SEARCHES: Say 'I do not consent to a search.'\n\n"
            "Straight Shooter: 'Three sentences if you get stopped: I want to remain silent. "
            "I want a lawyer. I do not consent to a search. Then shut up.'\n\n"
            "IMPORTANT: Never resist arrest. Comply, document, report later."
        ),
        "metadata": {
            "category": "juvenile_rights", "jurisdiction": "general_us",
            "topic": "police_interrogation",
            "character_affinity": "straight_shooter",
        },
    },
    {
        "id": "legal_iep_rights",
        "text": (
            "IEP and Special Education Rights (IDEA)\n\n"
            "1. RIGHT TO EVALUATION within 60 days if requested.\n"
            "2. FREE APPROPRIATE PUBLIC EDUCATION (FAPE).\n"
            "3. PARENTS participate in all IEP meetings.\n"
            "4. DISCIPLINE: 10+ day suspension requires Manifestation Determination Review.\n"
            "5. STAY-PUT: Student stays in placement during disputes.\n\n"
            "Frame: 'If you have an IEP, you have legal armor.'\n"
            "Action: Request IEP meeting in writing. Document everything."
        ),
        "metadata": {
            "category": "education_rights", "jurisdiction": "general_us",
            "topic": "iep_special_education",
            "character_affinity": "straight_shooter,strategist",
        },
    },
    {
        "id": "legal_probation_violations",
        "text": (
            "Understanding Probation Violations\n\n"
            "Types: TECHNICAL (missed curfew, failed test), NEW OFFENSES, ABSCONDING.\n\n"
            "Consequences: First = warning. Pattern = hearing. Serious = detention.\n\n"
            "SELF-REPORTING earns Honesty Bonus. Tell PO before they find out.\n\n"
            "Challenger: 'You missed curfew. Wait for PO to find out, or call first. "
            "Second move costs nothing, earns everything.'"
        ),
        "metadata": {
            "category": "juvenile_justice", "jurisdiction": "general_us",
            "topic": "probation_violations",
            "character_affinity": "challenger,straight_shooter",
        },
    },
]


# ============================================================
# RESOURCES (global_resources)
# ============================================================

RESOURCE_ENTRIES = [
    {
        "id": "resource_crisis_hotlines",
        "text": (
            "Crisis Resources\n\n"
            "If in immediate danger, call 911.\n\n"
            "988 Suicide & Crisis Lifeline: Call or text 988\n"
            "Crisis Text Line: Text HOME to 741741\n"
            "SAMHSA: 1-800-662-4357\n"
            "Runaway Safeline: 1-800-786-2929\n"
            "Boys Town: 1-800-448-3000\n"
            "Trevor Project (LGBTQ+): 1-866-488-7386\n"
            "Childhelp: 1-800-422-4453\n"
            "DV Hotline: 1-800-799-7233"
        ),
        "metadata": {
            "category": "crisis_resources", "resource_type": "hotlines",
            "character_affinity": "navigator",
        },
    },
    {
        "id": "resource_memphis_local",
        "text": (
            "Memphis-Area Youth Resources\n\n"
            "Mental Health: Memphis Youth Behavioral Health, Alliance Healthcare\n"
            "Academic: Knowledge Quest (898 Mississippi Blvd)\n"
            "Employment: Mayor's Youth Programs (ages 14-24), WIN (480 Beale St)\n"
            "Recreation: Memphis Athletic Ministries, Grizzlies Foundation\n"
            "Food: Memphis Food Bank (volunteer hours), Mid-South Food Bank"
        ),
        "metadata": {
            "category": "local_resources", "city": "Memphis", "state": "Tennessee",
            "character_affinity": "navigator,straight_shooter",
        },
    },
]


# ============================================================
# PLAYBOOKS (global_playbooks)
# ============================================================

PLAYBOOK_ENTRIES = [
    {
        "id": "playbook_mask_detection_response",
        "text": (
            "Mask Detection Response Protocol\n\n"
            "1. NEVER punish masking. It's a survival skill.\n"
            "2. Call out with CURIOSITY, not accusation.\n"
            "3. Offer reason to drop mask: trust credits, better support.\n\n"
            "Challenger: 'You said solid but sounds heavier. I get more useful the more real you are.'\n"
            "Navigator: 'I hear fine, but there's weight. How are you really?'\n\n"
            "PENALTY: Mask = -10 pts. Drop mask after callout = penalty reversed + 15 Honesty Bonus."
        ),
        "metadata": {
            "category": "protocol", "playbook_name": "Mask Detection Response",
            "character_affinity": "challenger,navigator,straight_shooter,strategist",
        },
    },
    {
        "id": "playbook_safe_harbor_red",
        "text": (
            "Safe Harbor Red — Emergency\n\n"
            "Triggers: suicidal ideation, danger, abuse, weapon access.\n\n"
            "1. DROP CHARACTER. Neutral calm tone.\n"
            "2. Acknowledge: 'I hear you. What you told me is important.'\n"
            "3. Provide resource (988, Childhelp, 911).\n"
            "4. Alert Rainbow Circle.\n"
            "5. Log Red for human review.\n\n"
            "DO NOT: promise confidentiality, minimize, probe, end abruptly.\n"
            "AFTER: Floor raised to Yellow permanently. Next session = Navigator."
        ),
        "metadata": {
            "category": "protocol", "playbook_name": "Safe Harbor Red",
            "character_affinity": "navigator", "priority": "critical",
        },
    },
    {
        "id": "playbook_academic_turnaround",
        "text": (
            "Academic Turnaround Strategy\n\n"
            "1. MAP THE GAP: 'Need 2.0 GPA, at 1.8. Which two classes?'\n"
            "2. LOW-HANGING FRUIT: Missing assignments first.\n"
            "3. ATTENDANCE MATH: Show direct eligibility connection.\n"
            "4. TIMELINE: Week-by-week plan to tryouts.\n"
            "5. CHECKPOINTS: 'Every Friday we review.'\n\n"
            "Key: Make goal THEIRS. 'Math to get on the court. Compliance is a side effect.'"
        ),
        "metadata": {
            "category": "strategy", "playbook_name": "Academic Turnaround",
            "character_affinity": "strategist,straight_shooter",
        },
    },
]


# ============================================================
# SEED FUNCTIONS
# ============================================================

async def seed_all_knowledge() -> int:
    """Seed all four global collections. Returns total chunk count."""
    total = 0
    for label, entries, collection in [
        ("therapeutic", THERAPEUTIC_ENTRIES, "global_therapeutic"),
        ("legal", LEGAL_ENTRIES, "global_legal"),
        ("resources", RESOURCE_ENTRIES, "global_resources"),
        ("playbooks", PLAYBOOK_ENTRIES, "global_playbooks"),
    ]:
        print(f"  Seeding {label}...")
        for item in entries:
            result = await ingest_text_directly(
                text=item["text"],
                collection_name=collection,
                document_id=item["id"],
                document_type=label,
                metadata=item["metadata"],
                store_text=True,
            )
            chunks = result.get("chunks", 0)
            total += chunks
            print(f"    {item['id']}: {chunks} chunks")

    print(f"\n  Total: {total} chunks")
    return total


def seed_minimal_therapeutic_kb() -> None:
    """
    Synchronous minimal seed for quick testing.
    Embeds first 2 therapeutic entries without a DB session.
    """
    from app.services.rag.embedding_service import embed_texts

    for entry in THERAPEUTIC_ENTRIES[:2]:
        text = entry["text"]
        embedding = embed_texts([text])
        chroma_store.add_documents(
            collection_name="global_therapeutic",
            ids=[entry["id"]],
            texts=[text],
            embeddings=embedding,
            metadatas=[entry["metadata"]],
        )
    logger.info("Minimal therapeutic KB seeded (2 entries)")
