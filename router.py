# router.py — RAG / Salary router (covers baseline.json as RAG)
from __future__ import annotations
from typing import Dict, Any, Tuple
import re

from tools.rag_tool import answer_with_rag
from tools.salary_tool import salary_tool

DOC_HINTS = [
    "according to", "from the document", "osca", "ict", "job family",
    "explain", "describe", "responsibilit", "dutie", "scope",
    "role of", "summari", "what does", "overview", "tasks",
    "main tasks", "primary duty", "kind of work", "core duties",
    "responsibilities of", "what is the role", "what is the responsibility",
    "what kind of work", "key duties", "key tasks"
]

SALARY_HINTS = [
    "salary", "median salary", "typical salary", "average salary",
    "typical pay", "average pay", "pay", "wage",
    "how much does", "how much do", "how much would", "annual salary", "yearly salary",
    "earn", "earns", "earning", "compensation", "remuneration",
    "hobart", "launceston", "tasmania", "regional",
    "part-time", "part time", "junior", "graduate", "entry level"
]

def _detect_intents(query: str) -> Tuple[bool, bool]:
    ql = query.lower()
    salary_like = any(k in ql for k in SALARY_HINTS)
    doc_like    = any(k in ql for k in DOC_HINTS)
    return salary_like, doc_like

def _safe_rag(query: str) -> Dict[str, Any]:
    rag = answer_with_rag(query)
    return {"rag": rag, "rag_error": rag.get("error")}

def _safe_salary(query: str) -> Dict[str, Any]:
    try:
        out = salary_tool(query)
        return {"tool": {"name": "salary_tool", "output": out}}
    except Exception as e:
        return {"tool": {"name": "salary_tool", "error": str(e)}}

def route(query: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    q = (query or "").strip()
    if not q:
        return {"route": "rag", "error": "empty query"}

    salary_like, doc_like = _detect_intents(q)

    if salary_like and doc_like:
        result["route"] = "both"
        result.update(_safe_rag(q))
        result["tools"] = [{"name": "salary_tool", "output": _safe_salary(q)["tool"].get("output", {})}]
        return result

    if salary_like and not doc_like:
        result["route"] = "salary"
        result.update(_safe_salary(q))
        return result

    result["route"] = "rag"
    result.update(_safe_rag(q))
    return result
