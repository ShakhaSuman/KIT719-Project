import os
import re

from rag.search import DATA_FILE, _load_bm25_corpus

print("BM25 data file:", DATA_FILE)
raw_chunks, bm = _load_bm25_corpus()
print("Total chunks:", len(raw_chunks))

# Show a couple of chunks that contain "ICT Business Analyst" and "Main tasks"
hits_roles = [i for i, c in enumerate(raw_chunks) if "ICT Business Analyst" in c]
hits_tasks = [
    i for i, c in enumerate(raw_chunks) if re.search(r"(?i)main\\s*tasks?", c)
]

print("Chunks containing 'ICT Business Analyst':", hits_roles[:5])
print("Chunks containing 'Main tasks':", hits_tasks[:5])


# Print small previews so you can eyeball the correct role block
def preview(i):
    txt = raw_chunks[i].splitlines()
    head = "\n".join(txt[:3])
    print(f"\n--- PREVIEW chunk {i} ---\n{head}\n...")


for i in hits_roles[:2] + hits_tasks[:2]:
    if i is not None and i < len(raw_chunks):
        preview(i)
