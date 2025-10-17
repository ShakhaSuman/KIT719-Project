# eval/evaluate.py
import os, sys, json, re, argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.rag_tool import answer_with_rag

try:
    from rapidfuzz import fuzz
    USE_RF = True
except Exception:
    USE_RF = False

def _strip_references(text: str) -> str:
    return (text or "").split("References:")[0]

def normalize(s: str) -> str:
    import string
    s = (s or "")
    s = s.lower()
    s = s.translate(str.maketrans('', '', string.punctuation))
    s = re.sub(r"\s+", " ", s).strip()
    return s

def matches(pred: str, gold: str, threshold: int = 74) -> tuple[bool, int]:
    body_pred = normalize(_strip_references(pred))
    body_gold = normalize(gold)
    if not body_pred or not body_gold:
        return (False, 0)

    if USE_RF:
        s_partial = fuzz.partial_token_set_ratio(body_pred, body_gold)
        s_set     = fuzz.token_set_ratio(body_pred, body_gold)
        score = int(0.7 * s_partial + 0.3 * s_set)
        return (score >= threshold, score)
    else:
        pt = set(body_pred.split())
        gt = body_gold.split()
        ok = all(w in pt for w in gt[: min(8, len(gt))])
        return (ok, 100 if ok else 0)

def contains_citation(answer_text: str, gold_citation: str, threshold: int = 80) -> bool:
    ans = normalize(answer_text)
    gold = normalize(gold_citation)
    if not ans or not gold:
        return False
    if USE_RF:
        return fuzz.partial_ratio(ans, gold) >= threshold
    gt = gold.split()[: min(8, len(gold.split()))]
    return all(w in ans for w in gt)

def iter_jsonl(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            yield json.loads(line)

def run_eval(path="eval/baseline.jsonl", threshold: int = 74, cit_threshold: int = 80, show: bool = True):
    total = hit_cit = hit_ans = 0
    for item in iter_jsonl(path):
        qid   = item["qid"]
        ques  = item["question"]
        goldc = item["gold_citation"]
        golda = item["gold_answer"]

        res = answer_with_rag(ques) or {}
        ans = res.get("answer", "")

        cit_ok = contains_citation(ans, goldc, threshold=cit_threshold)
        ans_ok, score = matches(ans, golda, threshold=threshold)

        hit_cit += int(cit_ok)
        hit_ans += int(ans_ok)
        total   += 1

        if show:
            print(f"{qid}: citation={'OK' if cit_ok else 'MISS'}, "
                  f"answer={'OK' if ans_ok else 'MISS'} (score={score})")

    print(f"Summary: {hit_cit}/{total} citations OK, {hit_ans}/{total} answers OK")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="eval/baseline.jsonl")
    parser.add_argument("--threshold", type=int, default=74, help="answer similarity threshold")
    parser.add_argument("--cit-threshold", type=int, default=80, help="citation fuzzy threshold")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    run_eval(path=args.path, threshold=args.threshold, cit_threshold=args.cit_threshold, show=not args.quiet)
