# tools/rag_tool.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import yaml

from rag.search import search
from rag.generate import (
    build_context_and_citations,
    render_answer_with_citations,
    make_answer_from_hits,
)

def answer_with_rag(query: str) -> Dict[str, Any]:
    cfg = yaml.safe_load(open("config.yml", "r", encoding="utf-8"))

    # 检索
    hits = search(query)
    if not hits:
        return {
            "answer": (
                "I couldn’t find grounded evidence in the OSCA corpus. "
                "Please rephrase or be more specific."
            ),
            "citations": [],
            "used": True,
            "score": 0.0,
        }

    top_score: float = float(hits[0].get("score", 0.0))

    retrieval_threshold: float = float(cfg.get("threshold", 0.40))
    if top_score < retrieval_threshold:
        return {
            "answer": (
                "I couldn’t find grounded evidence in the OSCA corpus. "
                "Please rephrase or be more specific."
            ),
            "citations": [],
            "used": True,
            "score": top_score,
        }

    _, citations = build_context_and_citations(hits)
    points = make_answer_from_hits(hits)
    answer = render_answer_with_citations(points, citations)

    low_conf_score: float = float(cfg.get("low_conf_score", 0.55))
    if top_score < low_conf_score:
        answer = (
            "⚠️ I'm not fully confident about this answer; based on retrieved "
            "snippets, it might be:\n" + answer
        )

    return {"answer": answer, "citations": citations, "used": True, "score": top_score}
