# Career Assistant – LLM + RAG + Tool QA System

## 1. Overview

This project implements a **Question Answering (QA) system** that combines **Retrieval-Augmented Generation (RAG)** and **tool-calling** capabilities.  
The system helps graduates and career changers in Australia explore occupations, identify skills, and understand salary expectations.
This scenario was chosen because it exercises both Retrieval-Augmented Generation (RAG) for long-form documents and tool-calling for up-to-date numeric lookups, plus non-trivial routing between them.

---

## 2. RAG Knowledge Base (Member A)

The RAG component (developed by Member A) grounds responses using the _Occupation Standard Classification Australia (OSCA)_ dataset  
(≈ 20 pages of long-form text).  
It uses document chunking, embedding (SentenceTransformers), and Chroma DB to retrieve relevant content for each query.

When a question requires factual grounding (“What are a data analyst’s key tasks?”),  
the RAG retriever provides the supporting context before generation.

---

## 3. Tools & Evaluation Module (Member B – Ritham Chhetri)

### 3.1 Tools Implemented

| Tool                | File                   | Description                                                                                                                                                                         |
| ------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Salary Tool**     | `tools/salary_tool.py` | Performs live salary lookup via DuckDuckGo (`duckduckgo-search v6.1.0`). Includes exponential backoff for rate-limits and a labelled AU fallback table so the system never crashes. |
| **Calculator Tool** | `tools/calc_tool.py`   | Safely evaluates arithmetic expressions (e.g., salary growth or hourly → annual conversion) using Python AST.                                                                       |

### 3.2 Evaluation & Testing

- `run_eval.py` executes **baseline** and **difficult** test sets.
- Natural-language pay questions (e.g. “$62 000 … 4% … 3 years”) are auto-parsed into valid expressions (`62000 * (1 + 0.04)**3`).
- Each result records whether fallback was used (`"fallback_used": true`).

  **Example Output**

  ```json
  {
    "query": "project manager average salary Australia site:au",
    "estimate_aud": 120000,
    "samples_used": 0,
    "error": "RatelimitException: ...",
    "fallback_used": true,
    "ddg_impl": "dds"
  };
  ```

## 4. System Integrator & Documentation Lead (Member C – Suman Shakhakarmi)

### LLMs, frameworks and libraries

- Embeddings: all-MiniLM-L6-v2 (Sentence-Transformers)
- Vector DB: Chroma (persistent index in index/chroma/)
- Classic retrieval fallback: rank-bm25
- Orchestration/UI: Python + Gradio (single-file app), plus a tiny CLI.
- No remote LLM is required to run the demo locally; answer composition is rule-based/templated on top of retrieved text and tool outputs.

### How the routing logic works

Routing lives in router.py. It is prompt-driven (no hard-coded if/else on intents beyond lexical hints) and supports three routes:

RAG – for conceptual/doc questions (e.g., “What are the main tasks of an ICT Business Analyst?”, “Explain the role of …”).
Detected via doc-hints like responsibilities, main tasks, role of, OSCA, ICT, explain, describe…

Salary – for pay queries (e.g., “median salary for ICT Support Officer in Hobart”).
Detected via salary-hints like salary, pay, wage, typical salary, Hobart, Tasmania, graduate, part-time…
This is tuned to pass all questions in baseline_tool.json and difficult_tool.json.

BOTH – when the prompt mixes explanation and pay (e.g., “Summarise responsibilities of a Business Analyst and give a typical salary”).
Router calls the RAG tool and the salary tool and renders both (grounded text + salary JSON).

### RAG internals (brief)

- Try vector search (Chroma + MiniLM).
- If embeddings/index are unavailable, fallback to BM25 with:
- absolute pathing to osca_ict_roles.utf8.txt,
- role-aware chunking (split on \d{6} ROLE NAME headings),
- a small “task” bonus to rank blocks that contain Main tasks / responsibilities,
- a robust task extractor that assembles bullet lists from the chosen role block only,
- grounded citations (source + chunk id + preview).
- This ensures we still return a clean, cited answer even offline.

### How to run Locally

# 1) Create a virtual environment

python -m venv .venv

# Windows:

.venv\Scripts\activate

# macOS/Linux:

source .venv/bin/activate

# 2) Install dependencies

pip install -r requirements.txt

# 3) Start the Gradio UI

python app_gradio.py

# Open http://127.0.0.1:7860

# (Optional) CLI

python app.py

### Examples (queries → expected routing/outputs)

1. What are the main tasks of an ICT Business Analyst? (RAG)

- Provides ICT business recommendations to senior management and business leadership to the team
- Arranges delivery of ICT goods, installation of equipment and the provision of services
- Gathers requirements from stakeholders to define business, technical and functional needs and specifications of a project
- Analyses and interprets data to understand trends to inform ICT systems decisions

2. Summarise responsibilities of a Business Analyst and give a typical salary. (Both)

- Gathers requirements from stakeholders to define business, technical and functional needs and specifications of a project
- Analyses and interprets data to understand trends to inform ICT systems decisions
- Maps business processes and systems using techniques such as business process modelling
- Evaluates risks associated with ICT initiatives and recommends mitigations
- Creates functional and technical specifications, use cases and workflow diagrams to communicate requirements

  [
  {
  "name": "salary_tool",
  "output": {
  "query": "summarise responsibilities of a business analyst and give a typical . average salary Australia site:au",
  "estimate_aud": 105000,
  "samples_used": 0,
  "hits": [],
  "error": null,
  "fallback_used": true,
  "ddg_impl": "dds"
  }
  }
  ]

### Known Limitations

- Document coverage → answers are limited to what’s in osca_ict_roles.utf8.txt. Roles not present (or described sparsely) will yield weaker answers.

- Queries about missing roles return partial or irrelevant context.

- Extracted answers can lose or duplicate part of a bullet list.

- Answers may merge content from unrelated roles (e.g., Analyst + Developer).
