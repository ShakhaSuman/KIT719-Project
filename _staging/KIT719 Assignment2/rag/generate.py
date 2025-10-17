# rag/generate.py
from collections import OrderedDict
from textwrap import shorten

def extract_bullets(text: str):
    items = []
    for line in text.splitlines():
        line = line.strip(" -*\u2022")
        if not line: 
            continue
        if line.lower().startswith(("main tasks", "alternative title", "specialisation")):
            continue
        if line and ("*" in text): 
            parts = [p.strip(" -*") for p in text.split("*") if p.strip()]
            return parts
        items.append(line)
    return items or [text.strip()]

def build_context_and_citations(hits):
    seen = OrderedDict()
    citations = []
    for h in hits:
        meta = h["meta"]
        doc  = h["doc"].strip()
        key = (meta.get("role_title"), meta.get("chunk_id"))
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

def render_answer_with_citations(points, citations):
    lines = ["**Answer:**"]
    for p in points[:6]:
        lines.append(f"- {p}")
    lines += ["", "References:"]
    for i, c in enumerate(citations, 1):
        lines.append(f"[{i}] {c['source']} · {c['role_title']} · {c['chunk_id']} — {c['preview']}")
    return "\n".join(lines)

def make_answer_from_hits(hits):
    bucket = OrderedDict()
    for h in hits:
        for b in extract_bullets(h["doc"]):
            if len(b) >= 6:
                bucket[b] = 1
    return list(bucket.keys())[:8]

