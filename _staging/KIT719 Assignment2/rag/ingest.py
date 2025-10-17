# rag/ingest.py
import re, pathlib, unicodedata, yaml, chardet, string
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

def simple_clean(text: str) -> str:
    lines = []
    for ln in text.splitlines():
        t = ln.strip()
        if not t:
            continue
        if not re.match(r"^[\w\s\-\*,.:;/()'’]+$", t):
            continue
        lines.append(t)
    out, last = [], None
    for t in lines:
        if t != last:
            out.append(t)
            last = t
    return "\n".join(out)

def load_cfg(path="config.yml"):
    return yaml.safe_load(open(path, "r", encoding="utf-8"))

def normalize_to_utf8(p: pathlib.Path) -> str:
    raw = p.read_bytes()
    enc = chardet.detect(raw)["encoding"] or "utf-8"
    text = raw.decode(enc, errors="replace")
    text = unicodedata.normalize("NFKC", text)
    out = pathlib.Path("data_processed")/ (p.stem + ".utf8.txt")
    out.write_text(text, encoding="utf-8")
    return str(out)

def split_sections(text: str):

    blocks = re.split(r"\n(?=\d{5,}\s+[A-Z].+)", text)  
    out = []
    for b in blocks:
        if not b.strip(): continue

        m = re.match(r"(\d{5,})\s+([^\n]+)", b)
        role_code, role_title = (m.group(1), m.group(2).strip()) if m else ("", "Unknown")

        sections = re.split(r"\n(?=Skill level:|Main tasks|Specialisation|Alternative title)", b)
        for s in sections:
            s2 = s.strip()
            if len(s2) < 50: continue
            out.append({"role_title": role_title, "section": s2})
    return out

def sliding_chunks(text: str, chunk_size=320, overlap=64):
    words = text.split()
    i, res = 0, []
    while i < len(words):
        res.append(" ".join(words[i:i+chunk_size]))
        i += max(1, chunk_size - overlap)
    return res

def main():
    cfg = load_cfg()
    src_dir = pathlib.Path(cfg["data_raw_dir"])
    files = sorted(src_dir.glob("*.txt")) + sorted(src_dir.glob("*.utf8.txt"))
    assert files, f"No source files in {src_dir}"

    embed = SentenceTransformerEmbeddingFunction(model_name=cfg["embed_model"])
    client = chromadb.PersistentClient(path=cfg["index_dir"])
    col = client.get_or_create_collection(name=cfg["collection"], embedding_function=embed)

    total_chunks = 0
    for f in files:
        norm_path = normalize_to_utf8(f)
        text = pathlib.Path(norm_path).read_text(encoding="utf-8")
        sections = split_sections(text)

        ids, docs, metas = [], [], []
        for si, sec in enumerate(sections):
            chs = sliding_chunks(sec["section"], cfg["chunk_size"], cfg["overlap"])
            for ci, ch in enumerate(chs):
                cid = f'{cfg["source_name"]}:{si}:{ci}'
                ids.append(cid)
                docs.append(ch)
                metas.append({
                    "source": cfg["source_name"],
                    "role_title": sec["role_title"],
                    "section_idx": si,
                    "chunk_idx": ci,
                    "chunk_id": cid
                })
        if ids:
            col.upsert(ids=ids, documents=docs, metadatas=metas)
            total_chunks += len(ids)
    print(f"Ingest done. Total chunks: {total_chunks}")

if __name__ == "__main__":
    main()
