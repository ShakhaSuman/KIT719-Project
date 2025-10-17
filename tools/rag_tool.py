# tools/rag_tool.py
from __future__ import annotations

import os
import re
import traceback
from typing import Any, Dict, List

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

from rag.generate import (
    build_context_and_citations,
    make_answer_from_hits,
    render_answer_with_citations,
)
from rag.search import search

# --- NEW: robust extractor for "Main tasks / duties / responsibilities" ---
TASK_HINTS = re.compile(
    r"(main\s*tasks?|dut(?:y|ies)|responsibilit(?:y|ies)|key\s*tasks?|core\s*duties?)",
    re.IGNORECASE,
)


def _extract_tasks_from_text(txt: str) -> List[str]:
    """
    Handles formats like:
      'Main tasks * Gathers requirements ... * Maps business processes ... * Develops ...'
    and also bulleted layouts with -, •, * on new lines.
    """
    # 1) Try to zoom into the "Main tasks" section if present
    m = re.search(r"(?is)main\s*tasks?\s*[:\-—]?\s*(.+)", txt)
    section = m.group(1).strip() if m else txt

    # 2) If tasks are inline separated by '*' (common in your doc), split them
    if " * " in section or section.strip().startswith("* "):
        parts = re.split(r"\*\s+", section)
        parts = [p.strip(" -•\n\r\t .") for p in parts if p.strip()]
        # remove the leading "Main tasks" phrase if it leaked in
        parts = [p for p in parts if not p.lower().startswith("main task")]
        # keep only reasonably short task-like snippets
        parts = [p for p in parts if len(p.split()) >= 3]
        return parts[:10]

    # 3) Otherwise, look for bullets on newlines
    bullets = re.findall(r"(?m)^[\-\•\*]\s+(.+)$", section)
    bullets = [b.strip(" -•\n\r\t .") for b in bullets if b.strip()]
    bullets = [b for b in bullets if len(b.split()) >= 3]
    if bullets:
        return bullets[:10]

    # 4) Last resort: split sentences after 'Main tasks' heuristically
    sentences = re.split(r"(?<=[\.\!\?])\s+", section)
    sentences = [s.strip() for s in sentences if len(s.split()) >= 5]
    return sentences[:6]


def _compose_tasks_answer(tasks: List[str], citations: List[Dict[str, Any]]) -> str:
    lines = ["**Answer:**"]
    lines += [f"- {t}" for t in tasks]
    # references (short form)
    if citations:
        lines.append("\nReferences:")
        for i, c in enumerate(citations, 1):
            src = c.get("source") or c.get("role_title") or "OSCA ICT Roles"
            lines.append(f"[{i}] {src} · chunk {c.get('chunk_id')}")
    return "\n".join(lines)


# --------------------------------------------------------------------------


# tools/rag_tool.py
def answer_with_rag(query: str) -> Dict[str, Any]:
    try:
        cfg = yaml.safe_load(open("config.yml", "r", encoding="utf-8"))
        hits = search(query)
        if not hits:
            return {
                "answer": "No relevant passages found.",
                "citations": [],
                "used": True,
                "score": 0.0,
            }

        top = float(hits[0].get("score", 0.0))
        context, cits = build_context_and_citations(hits)

        # 1) Try the standard structured renderer first (works great when vectors are available)
        points = make_answer_from_hits(hits)
        answer = render_answer_with_citations(points, cits)

        # --------------------------------------------------------------------
        # 2) Robust task extractor operating on COMBINED CONTEXT (top hits)
        TASKY_Q = re.search(
            r"(main\s*tasks?|dut(?:y|ies)|responsibilit(?:y|ies)|key\s*tasks?|core\s*duties?)",
            query,
            re.IGNORECASE,
        )

        def normalize_bullets(s: str) -> str:
            # unify common bullet/separator characters to " * "
            s = s.replace("•", " * ")
            s = s.replace("·", " * ")
            s = s.replace("‧", " * ")
            s = s.replace("∙", " * ")
            s = re.sub(r"[–—\-]{2,}", " - ", s)  # long dash runs
            return s

        def extract_tasks_global(txt: str) -> list[str]:
            t = normalize_bullets(txt)

            # Try to zoom into "Main tasks" (tolerate odd spacing)
            m = re.search(
                r"(?is)m\s*a\s*i\s*n\s*[\s\-–—]*\s*t\s*a\s*s\s*k\s*s?\s*[:\-–—]?\s*(.+)",
                t,
            )
            section = m.group(1).strip() if m else t

            # First pass: split on asterisks
            parts = re.split(r"\*\s+", section)
            parts = [p.strip(" -•\n\r\t .") for p in parts if p.strip()]
            # Filter obviously non-task lines
            parts = [
                p
                for p in parts
                if len(p.split()) >= 3
                and not p.lower().startswith(
                    ("business analysts (non", "business analysts (non-")
                )
            ]

            # If too few, try line-bullets
            if len(parts) <= 1:
                bullets = re.findall(r"(?m)^[\-\•\*]\s+(.+)$", section)
                parts = [b.strip(" -•\n\r\t .") for b in bullets if len(b.split()) >= 3]

            # Last resort: sentence split, keep plausible task-like clauses
            if len(parts) <= 1:
                sents = re.split(r"(?<=[\.\!\?])\s+", section)
                parts = [
                    s.strip() for s in sents if len(s.split()) >= 6 and len(s) <= 220
                ]
                parts = [
                    p
                    for p in parts
                    if not p.lower().startswith(
                        ("business analysts (non", "business analysts (non-")
                    )
                ]

            # Keep it tidy
            parts = parts[:10]
            return parts

        def infer_role_from_hits(hs: list[dict]) -> str | None:
            # try meta; otherwise scan lines for "273232 ICT ..." style
            for h in hs[:6]:
                meta_role = h.get("meta", {}).get("role_title")
                if meta_role:
                    return meta_role
            pat = re.compile(r"(?m)^\s*(\d{6}\s+[A-Za-z].+)$")
            for h in hs[:6]:
                doc = h.get("doc") or ""
                m = pat.search(doc)
                if m:
                    return m.group(1).strip()
            return None

        empty_structured = (
            (not points)
            or (not answer)
            or (answer.strip() in {"**Answer:**", "**Answer:**\n"})
        )

        if TASKY_Q and empty_structured:
            # Build a combined context from the top few hits so we don't miss the right chunk
            combined = "\n\n".join([(h.get("doc") or "") for h in hits[:6]])
            tasks = extract_tasks_global(combined)
            if tasks:
                lines = ["**Answer:**"]
                maybe_role = infer_role_from_hits(hits)
                if maybe_role:
                    lines.append(f"- {maybe_role}")
                lines += [f"- {t}" for t in tasks]

                if cits:
                    lines.append("\nReferences:")
                    for i, c in enumerate(cits, 1):
                        src = c.get("source") or c.get("role_title") or "OSCA ICT Roles"
                        lines.append(f"[{i}] {src} · chunk {c.get('chunk_id')}")
                answer = "\n".join(lines)
        # --------------------------------------------------------------------

        # 3) Final safety net: stitched summary (rarely needed now)
        if not answer or answer.strip() in {"**Answer:**", "**Answer:**\n"}:
            stitched = []
            for h in hits[:2]:
                doc = (h.get("doc") or "").strip()
                if doc:
                    stitched.append(doc[:600])
            fallback_text = (
                "\n\n".join(stitched).strip()
                or "I retrieved passages, but couldn't compose a structured answer."
            )
            answer = (
                "**Answer (best-effort):**\n"
                + fallback_text
                + "\n\n"
                + "References:\n"
                + "\n".join(
                    f"[{i+1}] {(c.get('source') or c.get('role_title') or 'OSCA ICT Roles')} · chunk {c.get('chunk_id')}"
                    for i, c in enumerate(cits)
                )
            )

        low_conf = float(cfg.get("low_conf_score", 0.55)) if cfg else 0.55
        if top < low_conf:
            answer = (
                "⚠️ I'm not fully confident about this answer; based on retrieved snippets, it might be:\n"
                + answer
            )

        return {"answer": answer, "citations": cits, "used": True, "score": top}
    except Exception as e:
        tb = traceback.format_exc(limit=3)
        return {
            "answer": "",
            "citations": [],
            "used": False,
            "score": 0.0,
            "error": f"{type(e).__name__}: {e}",
            "trace": tb,
        }
