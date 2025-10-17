# rag/search.py (patched with BM25 fallback)
import os

import chromadb
import yaml
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rank_bm25 import BM25Okapi


def load_cfg():
    return yaml.safe_load(open("config.yml", "r", encoding="utf-8"))


# --- ABSOLUTE PATH + ROBUST CHUNKING ---
import re

# search.py lives in ./rag, project root is one directory up
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(PROJECT_DIR, "data_processed", "osca_ict_roles.utf8.txt")


def _load_bm25_corpus():
    path = DATA_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(f"osca_ict_roles.utf8.txt not found at: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # Normalize newlines and bullets
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = (
        text.replace("•", "* ").replace("·", "* ").replace("‧", "* ").replace("∙", "* ")
    )

    # Primary split: start of a role line like "- 273232 ICT Business Analyst" or "273232 ICT Business Analyst"
    blocks = re.split(r"(?m)(?=^\s*(?:-\s*)?\d{6}\s+[A-Z].+)", text)

    # Fallback if the above didn’t work well
    if len(blocks) < 5:
        blocks = re.split(r"\n{2,}", text)

    # Clean up
    raw_chunks = [b.strip() for b in blocks if b and b.strip()]
    tokenized = [c.split() for c in raw_chunks]
    return raw_chunks, BM25Okapi(tokenized)


# ---------------------------------------


def chroma_client(cfg):
    embed = SentenceTransformerEmbeddingFunction(model_name=cfg["embed_model"])
    client = chroma.PersistentClient(path=cfg["index_dir"])
    col = client.get_or_create_collection(
        name=cfg["collection"], embedding_function=embed
    )
    return col


def vector_search(col, query, k):
    r = col.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for i, doc in enumerate(r["documents"][0]):
        meta = r["metadatas"][0][i]
        dist = r["distances"][0][i]
        score = max(0.0, min(1.0, 1.0 - dist))
        hits.append({"doc": doc, "meta": meta, "score": score})
    return hits


# rag/search.py
def bm25_search(query: str, k: int):
    import re

    chunks, bm = _load_bm25_corpus()
    scores = bm.get_scores(query.split())
    ranked = sorted(list(enumerate(scores)), key=lambda t: t[1], reverse=True)

    TASK_HINTS = re.compile(
        r"(main\s*tasks?|dut(?:y|ies)|responsibilit(?:y|ies)|key\s*tasks?|core\s*duties?)",
        re.IGNORECASE,
    )

    def infer_role_title(txt: str) -> str:
        m = re.search(r"(?m)^\s*(\d{6}\s+[A-Za-z].+)$", txt) or re.search(
            r"(?m)^\s*-\s*(\d{6}\s+[A-Za-z].+)$", txt
        )
        if m:
            return m.group(1).strip()
        for line in txt.splitlines():
            if line.strip() and any(
                w in line.lower()
                for w in ["ict", "analyst", "developer", "manager", "engineer"]
            ):
                return line.strip()
        return "OSCA ICT Roles"

    hits = []
    mx = max(scores) if scores is not None and len(scores) else 1.0
    for idx, sc in ranked[: max(k * 3, k)]:  # look a bit deeper before taking top k
        doc = chunks[idx]
        bonus = 0.15 if TASK_HINTS.search(doc) else 0.0
        norm = (float(sc) / float(mx) if mx else 0.0) + bonus
        rt = infer_role_title(doc)
        hits.append(
            {
                "doc": doc,
                "meta": {
                    "source": "OSCA ICT Roles (BM25 Fallback)",
                    "role_title": rt,
                    "chunk_id": idx,
                },
                "score": min(norm, 1.0),
            }
        )

    # return the best k after re-scoring
    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits[:k]


def search(query: str):
    cfg = load_cfg()
    try:
        col = chroma_client(cfg)
        hits = vector_search(col, query, cfg["top_k"])
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits
    except Exception:
        return bm25_search(query, cfg.get("top_k", 4))
