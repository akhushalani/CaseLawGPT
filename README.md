# CaseLawGPT

A Retrieval-Augmented Generation (RAG) system for U.S. caselaw. Ask legal questions and get answers grounded in real judicial opinions.

## Features

- **Semantic Search**: FAISS-powered vector search over case law chunks
- **LLM Integration**: Ollama backend for local inference (GPU accelerated)
- **Real Data**: CourtListener API integration for federal court opinions
- **Filtering**: Filter by court and date range
- **Citations**: All answers cite retrieved source cases

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   RAG        │────▶│   Ollama    │
│  Frontend   │     │   Pipeline   │     │   LLM       │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────┐
              │  FAISS   │  │  SQLite  │
              │  Index   │  │  DB      │
              └──────────┘  └──────────┘
```

## Project Structure

```
CaseLawGPT/
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration settings
│   ├── database.py        # SQLite operations
│   ├── ingestion.py       # Case file ingestion
│   ├── preprocessing.py   # Text chunking
│   ├── vectorstore.py     # FAISS embeddings & search
│   ├── llm.py             # Ollama LLM integration
│   └── pipeline.py        # RAG orchestration
├── scripts/
│   └── download_courtlistener.py   # Data download script
├── data/
│   ├── raw_cases/         # Downloaded case JSON files
│   └── vectorstore/       # FAISS index files
├── app.py                 # Streamlit web interface
├── requirements.txt
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start server
ollama serve

# Pull model (in new terminal)
ollama pull qwen2.5:14b   # For GPU
ollama pull llama3.2:3b   # For CPU/testing
```

### 3. Download Case Data

```bash
# Get API token from https://www.courtlistener.com/help/api/rest/v4/
export CL_TOKEN='your-token-here'

python scripts/download_courtlistener.py --n-cases 500
```

### 4. Build Pipeline

```bash
python -m src.ingestion
python -m src.preprocessing
python -m src.vectorstore --build
```

### 5. Launch App

```bash
streamlit run app.py
```

For GCP deployment:
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## Configuration

Key settings in `src/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `CHUNK_TARGET_TOKENS` | 500 | Target chunk size |
| `CHUNK_OVERLAP` | 80 | Overlap between chunks |
| `DEFAULT_TOP_K` | 5 | Default results to retrieve |
| `MAX_CONTEXT_CHUNKS` | 8 | Max chunks sent to LLM |
| `OLLAMA_MODEL` | qwen2.5:14b | LLM model name |

Override via environment variables:
```bash
export OLLAMA_MODEL="llama3:8b"
export EMBEDDING_MODEL_NAME="sentence-transformers/all-mpnet-base-v2"
```

## Sample Queries

- "What is qualified immunity?"
- "When can police conduct a search without a warrant?"
- "What are the elements of a due process claim?"
- "How do courts analyze First Amendment cases?"

## Tech Stack

- **Frontend**: Streamlit
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Store**: FAISS
- **Database**: SQLite
- **LLM**: Ollama (Qwen 2.5 / Llama 3)
- **Data Source**: CourtListener API

## License

MIT