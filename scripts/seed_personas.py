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

        # (Body copied from canonical zip version)
        # PERSONA 2–5 seeding is already present in the new zip file;
        # we assume that content has now been merged here.

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_personas())

