"""Corpus ingestion: load PDFs and markdown files → chunk → embed → store in ChromaDB."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from src.config import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    CORPUS_DIR,
    EMBEDDING_MODEL,
)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


def _load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _load_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_document(path: Path) -> str:
    if path.suffix == ".pdf":
        return _load_pdf(path)
    return _load_markdown(path)


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += size - overlap
    return [c for c in chunks if c.strip()]


def _doc_id(source: str, chunk_idx: int) -> str:
    h = hashlib.md5(source.encode()).hexdigest()[:8]
    return f"{h}_{chunk_idx}"


def ingest(source_dir: Path = CORPUS_DIR, collection_name: str = CHROMA_COLLECTION) -> int:
    """Ingest all PDFs and markdown files in source_dir into ChromaDB. Returns chunk count."""
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(collection_name)

    doc_files = sorted(
        [p for p in source_dir.glob("**/*.pdf")]
        + [p for p in source_dir.glob("**/*.md") if p.name != "README.md"]
    )
    if not doc_files:
        print(f"No documents found in {source_dir}")
        return 0

    total = 0
    for doc_path in doc_files:
        print(f"Ingesting {doc_path.name}...")
        text = _load_document(doc_path)
        chunks = _chunk_text(text)
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()
        ids = [_doc_id(doc_path.name, i) for i in range(len(chunks))]
        metadatas = [{"source": doc_path.name, "chunk": i} for i in range(len(chunks))]
        collection.upsert(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        total += len(chunks)
        print(f"  → {len(chunks)} chunks")

    print(f"Done. {total} total chunks in collection '{collection_name}'.")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=CORPUS_DIR)
    parser.add_argument("--collection", default=CHROMA_COLLECTION)
    args = parser.parse_args()
    ingest(args.source, args.collection)
