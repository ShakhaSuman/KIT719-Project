# rag/search.py
import yaml, chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rank_bm25 import BM25Okapi 

def load_cfg(): return yaml.safe_load(open("config.yml","r",encoding="utf-8"))

def chroma_client(cfg):
    embed = SentenceTransformerEmbeddingFunction(model_name=cfg["embed_model"])
    client = chromadb.PersistentClient(path=cfg["index_dir"])
    col = client.get_or_create_collection(name=cfg["collection"], embedding_function=embed)
    return col

def vector_search(col, query, k):
    r = col.query(query_texts=[query], n_results=k,
                  include=["documents","metadatas","distances"])
    hits = []
    for i, doc in enumerate(r["documents"][0]):
        meta = r["metadatas"][0][i]
        dist = r["distances"][0][i]          # cosine distance
        score = max(0.0, min(1.0, 1.0 - dist)) 
        hits.append({"doc": doc, "meta": meta, "score": score})
    return hits

def search(query:str):
    cfg = load_cfg()
    col = chroma_client(cfg)
    hits = vector_search(col, query, cfg["top_k"])
    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits
