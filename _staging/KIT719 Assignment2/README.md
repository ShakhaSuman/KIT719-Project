Career Assistant (KIT719 Project 2)
Team Handoff — RAG Component Completed ✅

This README documents the current project setup, directory structure, and next steps for continuing Tool Calling, Documentation, and UI development.


📘 Overview
The Career Assistant system is designed to help Australian graduates, students, and career changers explore ICT career paths, identify transferable skills, and understand salary expectations.

RAG Component (Completed):
Retrieves relevant information from the OSCA dataset about ICT roles, tasks, and required skills.

Tool Calling (Pending):
To handle external queries such as “What’s the average salary for a software engineer?” by calling a live salary API or a web search tool.

UI Component (Pending):
To provide an interactive front-end where users can type queries and view responses.


📁 Project Structure
content/
│
├── data_raw/                      # Raw corpus (OSCA role descriptions)
│   └── osca_ict_roles.txt
│
├── data_processed/                # Cleaned UTF-8 normalized corpus
│   └── osca_ict_roles.utf8.txt
│
├── index/chroma/                  # ChromaDB vector index
│   └── chroma.sqlite3
│
├── rag/                           # Retrieval + Generation core
│   ├── ingest.py                  # Data normalization & embedding
│   ├── search.py                  # Search utility (Chroma retrieval)
│   ├── generate.py                # Context building and rendering
│   └── __pycache__/
│
├── tools/                         # High-level RAG interface
│   ├── rag_tool.py                # Unified function `answer_with_rag()`
│   └── __pycache__/
│
├── eval/                          # Evaluation scripts & test data
│   ├── baseline.jsonl             # 10 benchmark test queries
│   └── evaluate.py                # Automated evaluation runner
│
├── sample_data/                   # Example data for experiments
│
└── config.yml                     # Global configuration (chunk size, paths, etc.)


⚙️ How to Rebuild / Run
1. Environment setup
pip install -U sentence-transformers chromadb rapidfuzz rank_bm25 pyyaml chardet tqdm

2. Re-ingest the corpus
When osca_ict_roles.txt is updated, rebuild the embeddings:
python rag/ingest.py

This script:
Normalizes raw text to UTF-8
Splits text into overlapping chunks (as defined in config.yml)
Embeds chunks using all-MiniLM-L6-v2
Stores them in ChromaDB (index/chroma/)

3. Verify retrieval
Run from Python REPL or VSCode terminal:

from tools.rag_tool import answer_with_rag
print(answer_with_rag("What tasks should I expect in project management?")["answer"])

Expected: A combined answer citing OSCA role snippets with “Main tasks” sections.

4. Evaluate accuracy
Run benchmark test:
python eval/evaluate.py

Typical result after tuning:
Summary: 9/10 citations OK, 9/10 answers OK


🔍 Configuration Notes
config.yml controls ingestion parameters:
data_raw_dir: data_raw
index_dir: index/chroma
collection: kit719_rag
source_name: osca_roles
embed_model: all-MiniLM-L6-v2

chunk_size: 800       # Larger chunks preserve context across Main tasks & Specialisation
overlap: 120          # Ensures continuity between chunks
reset_source: true    # Rebuilds cleanly when corpus is updated
threshold: 0.15       # Confidence threshold for retrieval


🧩 Current Features (RAG)
| Feature                   | Description                                     | Status |
| ------------------------- | ----------------------------------------------- | ------ |
| Corpus preprocessing      | Cleans and normalizes OSCA text                 | ✅ Done |
| Embedding + vector search | Implemented with SentenceTransformer + Chroma   | ✅ Done |
| Query answering           | Context-aware retrieval with citation rendering | ✅ Done |
| Confidence handling       | Adds ⚠️ warning when confidence < 0.75          | ✅ Done |
| Evaluation                | Automated benchmark with fuzzy-match scoring    | ✅ Done |


🌐 Next Steps (for Teammates)
1. Tool Calling Module

Implement an external information retriever for salary data, e.g.:

Use a lightweight web search API (SerpAPI, Bing, or DuckDuckGo)

Or mock the API call with static salary datasets for testing

Integrate as a function:
def get_salary_info(job_title: str) -> str:
    # Example placeholder: fetch average salary for "Software Engineer"
    ...

and connect it with the main app’s query dispatcher.

Expected behavior:

“What’s the average salary for a software engineer in Australia?”
→ Tool Calling retrieves live data
→ RAG handles general questions.

2. Documentation

Write brief internal documentation (e.g., docs/system_overview.md)
covering:

How data flows from ingestion → search → answer generation
How RAG differs from Tool Calling in this project
How evaluation metrics are computed.

3. UI Development

Create a simple interface (streamlit / gradio / Flask) that:
Accepts user queries
Shows RAG or Tool Calling results
Displays references for traceability

Example layout:

[ Input Box ]  →  “Submit”
──────────────────────────
Response:
⚠️ I'm not fully confident…
**Answer:**
Main tasks: ...
──────────────────────────
References:
[1] osca_roles · ICT Project Manager ...


🧱 Developer Notes
All paths are relative to content/
Ensure index/chroma/ is not committed to GitHub (too large)
For new corpus versions, always re-run rag/ingest.py
Use the evaluate.py output to tune chunk_size, overlap, and similarity thresholds.


📜 Authors
RAG Implementation: Erik
Tool Calling & API Integration: To be continued by teammate
Documentation & UI Design: To be continued by teammate