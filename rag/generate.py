# rag/generate.py
from __future__ import annotations
from collections import OrderedDict, defaultdict
from textwrap import shorten
import re

TASK_SECTION_HEADERS = [
    r"main\s+tasks?", r"key\s+tasks?", r"typical\s+tasks?",
    r"duties", r"key\s+responsibilit(y|ies)", r"responsibilit(y|ies)",
    r"job\s+tasks?", r"what\s+you'?ll\s+do", r"what\s+you\s+will\s+do",
    r"position\s+duties", r"role\s+responsibilit(y|ies)"
]
NON_TASK_HEADERS = [
    r"alternative\s+title", r"specialisation", r"exclusion", r"not\s+included",
    r"occupation\s+level", r"classification", r"overview", r"summary"
]

TASK_VERBS = [
    "analyse", "analyze", "assess", "evaluate", "elicit", "document",
    "gather", "map", "model", "design", "specify", "define", "facilitate",
    "coordinate", "collaborate", "communicate", "liaise", "translate",
    "plan", "prioritise", "prioritize", "validate", "verify", "test",
    "recommend", "implement", "monitor", "support", "improve", "optimise",
    "optimize", "manage", "lead", "present", "report"
]

_BULLET_LEAD = re.compile(r"^\s*(?:[-*•\u2022]|[0-9]{1,2}[.)]|–|—)\s*")
_SENT_SPLIT = re.compile(r"[;•\u2022]|(?<=[.?!])\s+(?=[A-Z])", re.UNICODE | re.MULTILINE)

def _normalize_line(s: str) -> str:
    s = _BULLET_LEAD.sub("", s.strip())
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(" •;,-")
    return s

def _looks_like_task(line: str) -> bool:
    if len(line) < 6: 
        return False
    low = line.lower()
    if re.match(rf"^({'|'.join(TASK_VERBS)})\b", low):
        return True
    if any(k in low for k in ["requirements", "specification", "user story", "use case",
                              "process model", "workflow", "backlog", "acceptance criteria",
                              "gap analysis", "feasibility", "business case"]):
        return True
    if any(k in low for k in ["are excluded", "included in occupation", "classification"]):
        return False
    return bool(re.match(r"^[a-z][a-z]+(e|ing|es)\b", low))

def _slice_task_sections(text: str) -> list[str]:
    lines = text.splitlines()
    blocks, buf, in_task = [], [], False
    for raw in lines:
        line = raw.strip()
        if not line:
            if in_task and buf:
                blocks.append("\n".join(buf)); buf = []
            continue

        if re.match(rf"^({'|'.join(TASK_SECTION_HEADERS)})\b", line.strip().lower()):
            if in_task and buf:
                blocks.append("\n".join(buf)); buf = []
            in_task = True
            continue

        if re.match(rf"^({'|'.join(NON_TASK_HEADERS)})\b", line.strip().lower()):
            if in_task and buf:
                blocks.append("\n".join(buf)); buf = []
            in_task = False
            continue

        if in_task:
            buf.append(line)

    if in_task and buf:
        blocks.append("\n".join(buf))

    return blocks if blocks else [text]

def extract_bullets(text: str) -> list[str]:
    results = []
    for block in _slice_task_sections(text):
        for raw in block.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            line = _normalize_line(raw)
            if not line:
                continue
            if _looks_like_task(line):
                results.append(line)

        if not results:
            for sent in _SENT_SPLIT.split(block):
                line = _normalize_line(sent)
                if _looks_like_task(line):
                    results.append(line)

    out = list(OrderedDict((r, 1) for r in results if r).keys())
    return out

def build_context_and_citations(hits: list[dict]) -> tuple[str, list[dict]]:
    seen = OrderedDict()
    citations = []
    for h in hits:
        meta = h.get("meta", {})
        doc  = (h.get("doc") or "").strip()
        key = (meta.get("source"), meta.get("chunk_id"))
        if key in seen:
            continue
        seen[key] = doc
        citations.append({
            "source": meta.get("source"),
            "role_title": meta.get("role_title"),
            "chunk_id": meta.get("chunk_id"),
            "preview": shorten(doc, width=140, placeholder="...")
        })
    context = "\n\n".join(seen.values())
    return context, citations

def make_answer_from_hits(hits: list[dict]) -> list[tuple[str, dict]]:
    scored = []
    for rank, h in enumerate(hits):
        meta = h.get("meta", {})
        doc  = h.get("doc") or ""
        weight = 1.0 / (1 + rank) 
        for bullet in extract_bullets(doc):
            score = weight
            low = bullet.lower()
            if any(k in low for k in ["task", "dutie", "responsibilit"]):
                score += 0.25
            if re.match(rf"^({'|'.join(TASK_VERBS)})\b", low):
                score += 0.25
            scored.append((score, bullet, meta))

    seen = set()
    points = []
    for s, b, m in sorted(scored, key=lambda x: x[0], reverse=True):
        if b in seen: 
            continue
        seen.add(b)
        points.append((b, m))
        if len(points) >= 8:
            break
    return points

def render_answer_with_citations(points_with_meta: list[tuple[str, dict]], citations: list[dict]) -> str:
    lines = ["**Answer:**"]
    for p, _ in points_with_meta[:6]:
        lines.append(f"- {p}")

    used_keys = OrderedDict()
    for _, m in points_with_meta:
        used_keys[(m.get("source"), m.get("chunk_id"))] = True

    ordered_cites = []
    rest_cites = []
    for c in citations:
        key = (c.get("source"), c.get("chunk_id"))
        if key in used_keys:
            ordered_cites.append(c)
        else:
            rest_cites.append(c)

    lines += ["", "References:"]
    idx = 1
    for c in ordered_cites + rest_cites:
        lines.append(f"[{idx}] {c.get('source')} · {c.get('role_title')} · {c.get('chunk_id')} — {c.get('preview')}")
        idx += 1
    return "\n".join(lines)

def make_grounded_answer(hits: list[dict]) -> str:
    _, citations = build_context_and_citations(hits)
    points = make_answer_from_hits(hits)
    return render_answer_with_citations(points, citations)
