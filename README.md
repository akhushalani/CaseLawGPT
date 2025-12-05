# CaseLawGPT

Local Retrieval-Augmented Generation (RAG) system for U.S. caselaw using Streamlit, SQLite, FAISS, and local Hugging Face models.

## Pipeline
1) Ingest CAP JSON cases: `python ingestion.py --raw-dir data/raw_cases`
2) Chunk opinions: `python preprocessing.py`
3) Build embeddings/index: `python vectorstore.py --build`
4) Launch UI: `streamlit run app.py`

All models run locally (no external APIs). Ensure `data/raw_cases` contains CAP JSON with `casebody/opinions`.
