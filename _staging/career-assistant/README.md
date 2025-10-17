# Career Assistant – LLM + RAG + Tool QA System

## 1. Overview
This project implements a **Question Answering (QA) system** that combines **Retrieval-Augmented Generation (RAG)** and **tool-calling** capabilities.  
The system helps graduates and career changers in Australia explore occupations, identify skills, and understand salary expectations.

---

## 2. RAG Knowledge Base (Member A)
The RAG component (developed by Member A) grounds responses using the *Occupation Standard Classification Australia (OSCA)* dataset  
(≈ 20 pages of long-form text).  
It uses document chunking, embedding (SentenceTransformers), and Chroma DB to retrieve relevant content for each query.

When a question requires factual grounding (“What are a data analyst’s key tasks?”),  
the RAG retriever provides the supporting context before generation.

---

## 3. Tools & Evaluation Module (Member B – Ritham Chhetri)

### 3.1 Tools Implemented
| Tool | File | Description |
|------|------|--------------|
| **Salary Tool** | `tools/salary_tool.py` | Performs live salary lookup via DuckDuckGo (`duckduckgo-search v6.1.0`).  Includes exponential backoff for rate-limits and a labelled AU fallback table so the system never crashes. |
| **Calculator Tool** | `tools/calc_tool.py` | Safely evaluates arithmetic expressions (e.g., salary growth or hourly → annual conversion) using Python AST. |

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
}
