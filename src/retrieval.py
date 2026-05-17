"""Retrieval: embed a query and fetch top-k evidence chunks from ChromaDB."""

from __future__ import annotations

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    TOP_K_RETRIEVAL,
)


class EvidenceRetriever:
    def __init__(
        self,
        collection_name: str = CHROMA_COLLECTION,
        top_k: int = TOP_K_RETRIEVAL,
    ) -> None:
        self._model = SentenceTransformer(EMBEDDING_MODEL)
        self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self._collection = self._client.get_or_create_collection(collection_name)
        self._top_k = top_k

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """Return a list of {text, source, score} dicts for the given query."""
        k = top_k or self._top_k
        embedding = self._model.encode(query).tolist()
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "chunk_index": meta.get("chunk", -1),
                    "distance": dist,
                    "score": round(1 - dist, 4),
                }
            )
        return chunks

    def format_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks as a numbered context block for LLM prompts."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(f"[{i}] Source: {chunk['source']}\n{chunk['text']}")
        return "\n\n".join(parts)
