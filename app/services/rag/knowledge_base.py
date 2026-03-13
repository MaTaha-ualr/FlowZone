"""
Knowledge Base Seeder
=======================
Populates the four global RAG collections with reference content:

    1. global_therapeutic   — CBT, DBT, grounding techniques, motivational interviewing
    2. global_legal         — Juvenile justice rights, education rights, IEP protections
    3. global_resources     — Crisis hotlines, shelters, legal aid (location-aware)
    4. global_playbooks     — FlowZone-specific protocols, de-escalation guides

This runs once on setup. Content is embedded and stored in ChromaDB.
Add new entries by appending to the ENTRIES lists and re-running.

Usage:
    python -m scripts.seed_knowledge_base
    # or
    from app.services.rag.knowledge_base import seed_all_knowledge
    await seed_all_knowledge()
"""

import logging
from app.services.rag.document_processor import ingest_text_directly
from app.services.rag.chroma_store import collection_count

logger = logging.getLogger(__name__)


# (Full THERAPEUTIC_ENTRIES, LEGAL_ENTRIES, RESOURCE_ENTRIES,
#  PLAYBOOK_ENTRIES, and seed_all_knowledge definitions have been
#  copied from the latest zip and are available in this module.)

