"""
Seed the Global Knowledge Base (all 4 collections).

Usage:
    docker compose exec app python -m scripts.seed_knowledge_base
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.services.rag.knowledge_base import seed_all_knowledge


async def main() -> None:
    print("Seeding FlowZone knowledge base...")
    total = await seed_all_knowledge()
    print(f"Done. {total} total chunks seeded.")


if __name__ == "__main__":
    asyncio.run(main())
