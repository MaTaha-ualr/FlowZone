"""
RAG Services Package
=====================
Implements the three RAG systems described in the FlowZone architecture:

1. Global Knowledge Base (System 1)
2. Per-User Context Store (System 2)
3. Cross-User Pattern Engine (System 3)

High-level responsibilities:
    - `chroma_store`      : ChromaDB client + collection helpers
    - `embedding_service` : SentenceTransformer wrapper
    - `document_processor`: Ingestion pipeline for documents
    - `knowledge_base`    : Global KB schemas + seeding
    - `retriever`         : Unified retrieval across systems 1–3
    - `rag_classifier`    : Rule-based RAG trigger logic
    - `google_drive`      : Google Drive OAuth + file access helpers
"""

