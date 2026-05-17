# Evidence Corpus

This directory holds the clinical evidence documents that power ToothTrust's RAG pipeline.

## What belongs here

- ADA clinical practice guidelines (PDF)
- Cochrane systematic reviews (PDF or HTML)
- Journal articles on evidence-based dentistry
- AAP periodontal guidelines
- AAPD pediatric dentistry guidelines

## What does NOT belong here

- Patient records or any PHI
- Proprietary content without a license to use it

## Ingestion

Run `src/ingest.py` (or notebook `01_corpus_ingestion.ipynb`) to chunk and embed documents into ChromaDB:

```bash
python -m src.ingest --source data/corpus/ --collection dental_evidence
```

## Corpus inventory

| File | Source | Date | Topics |
|---|---|---|---|
| (empty — add documents here) | | | |

## Licensing notes

Verify licensing before adding any document. ADA guidelines may require a license for commercial use. Cochrane abstracts are open-access; full text requires a subscription or author permission.
