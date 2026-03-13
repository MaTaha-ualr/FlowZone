"""
Seed the Global Knowledge Base (System 1).

Usage (from project root inside Docker):
    docker compose exec app python -m scripts.seed_knowledge_base
"""

import asyncio

from app.services.rag.knowledge_base import seed_minimal_therapeutic_kb


async def main() -> None:
    seed_minimal_therapeutic_kb()
    print("Seeded minimal therapeutic knowledge base.")


if __name__ == "__main__":
    asyncio.run(main())

