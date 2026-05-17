"""Tests for the evidence retrieval layer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.retrieval import EvidenceRetriever


def _mock_chroma_result():
    return {
        "documents": [["Evidence passage about crown preparation.", "Evidence passage about SRP."]],
        "metadatas": [[{"source": "ADA_guidelines.pdf", "chunk": 0}, {"source": "AAP_guidelines.pdf", "chunk": 3}]],
        "distances": [[0.12, 0.31]],
    }


@patch("src.retrieval.chromadb.PersistentClient")
@patch("src.retrieval.SentenceTransformer")
def test_retrieve_returns_chunks(mock_st, mock_chroma):
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    mock_st.return_value = mock_model

    mock_collection = MagicMock()
    mock_collection.query.return_value = _mock_chroma_result()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    retriever = EvidenceRetriever(top_k=2)
    chunks = retriever.retrieve("crown preparation evidence")

    assert len(chunks) == 2
    assert chunks[0]["source"] == "ADA_guidelines.pdf"
    assert chunks[0]["score"] == round(1 - 0.12, 4)


@patch("src.retrieval.chromadb.PersistentClient")
@patch("src.retrieval.SentenceTransformer")
def test_format_context_numbered(mock_st, mock_chroma):
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    mock_st.return_value = mock_model

    mock_collection = MagicMock()
    mock_collection.query.return_value = _mock_chroma_result()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    retriever = EvidenceRetriever(top_k=2)
    chunks = retriever.retrieve("SRP evidence")
    context = retriever.format_context(chunks)

    assert "[1]" in context
    assert "[2]" in context
    assert "ADA_guidelines.pdf" in context


@patch("src.retrieval.chromadb.PersistentClient")
@patch("src.retrieval.SentenceTransformer")
def test_retrieve_empty_query(mock_st, mock_chroma):
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)
    mock_st.return_value = mock_model

    empty_result = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    mock_collection = MagicMock()
    mock_collection.query.return_value = empty_result
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

    retriever = EvidenceRetriever(top_k=5)
    chunks = retriever.retrieve("")

    assert chunks == []
