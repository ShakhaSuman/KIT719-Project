from __future__ import annotations
from typing import Dict, Any, List
import re, time, random

# Prefer duckduckgo_search (v6.1.0) which needs 'keywords'; fall back to ddgs if needed.
DDG_KIND = None  # "dds" | "ddgs" | None
try:
    from duckduckgo_search import DDGS as DDGS_DDS  # expects keywords=
    DDG_KIND = "dds"
except Exception:
    DDGS_DDS = None

try:
    from ddgs import DDGS as DDGS_DDGS  # expects query=
    if DDG_KIND is None:
        DDG_KIND = "ddgs"
except Exception:
    DDGS_DDGS = None

# Conservative AU fallback so the tool never crashes in rate-limited envs
_FALLBACK_AU = {
    "software engineer": 110000,
    "data analyst": 85000,
    "project manager": 120000,
    "teacher": 90000,
    "cybersecurity": 120000,
    "business analyst": 105000,
    "data engineer": 125000,
}

def _normalize_query(q: str, region_hint: str) -> str:
    ql = q.lower()
    for t in ["average","salary","pay","wage","per year","australia","aus"]:
        ql = ql.replace(t, "")
    ql = " ".join(ql.split())
    return f"{ql} average salary {region_hint} site:au".strip()

def _extract_numbers(text: str) -> List[int]:
    nums: List[int] = []
    for m in re.findall(r"(?:A\$|\$)\s*([0-9][0-9,]{3,})", text):
        try:
            v = int(m.replace(",", ""))
            if 30000 <= v <= 400000: nums.append(v)
        except: pass
    for m in re.findall(r"AUD\s*([0-9][0-9,]{3,})", text, flags=re.I):
        try:
            v = int(m.replace(",", ""))
            if 30000 <= v <= 400000: nums.append(v)
        except: pass
    for m in re.findall(r"\b([1-3][0-9]{2})k\b", text, flags=re.I):
        try:
            v = int(m) * 1000
            if 30000 <= v <= 400000: nums.append(v)
        except: pass
    return nums

def _search_with_backoff_dds(keywords: str, max_results: int) -> List[dict]:
    # duckduckgo_search v6.1.0 -> keywords=
    attempts = 4
    delays = [0.7, 1.4, 2.8, 5.0]
    for i in range(attempts):
        try:
            with DDGS_DDS() as ddgs:
                return list(ddgs.text(
                    keywords,
                    max_results=max_results,
                    region="au-en",
                    safesearch="off"
                ))
        except Exception as e:
            if i == attempts - 1:
                raise
            time.sleep(delays[i] + random.uniform(0, 0.4))
    return []

def _search_with_backoff_ddgs(query: str, max_results: int) -> List[dict]:
    # ddgs -> query=
    attempts = 4
    delays = [0.7, 1.4, 2.8, 5.0]
    for i in range(attempts):
        try:
            ddgs = DDGS_DDGS()
            return list(ddgs.text(
                query=query,
                max_results=max_results,
                region="au-en",
                safesearch="off",
                backend="lite"
            ))
        except Exception as e:
            if i == attempts - 1:
                raise
            time.sleep(delays[i] + random.uniform(0, 0.4))
    return []

def _ddg_text_auto(q: str, max_results: int) -> List[dict]:
    if DDG_KIND == "dds" and DDGS_DDS is not None:
        return _search_with_backoff_dds(q, max_results)
    if DDG_KIND == "ddgs" and DDGS_DDGS is not None:
        return _search_with_backoff_ddgs(q, max_results)
    raise RuntimeError("No DDGS implementation available.")

def salary_tool(query: str, region_hint: str = "Australia", max_results: int = 6) -> Dict[str, Any]:
    q = _normalize_query(query, region_hint)
    hits: List[Dict[str, Any]] = []
    nums: List[int] = []
    error = None
    fallback_used = False

    try:
        results = _ddg_text_auto(q, max_results=max_results)
        for r in results:
            title = (r.get("title") or "").strip()
            href  = (r.get("href")  or "").strip()
            body  = (r.get("body")  or "").strip()
            if not (title or body):
                continue
            hits.append({"title": title, "href": href, "body": body})
            nums.extend(_extract_numbers(f"{title} {body}"))
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    estimate = int(sum(nums)/len(nums)) if nums else None

    if estimate is None:
        # fallback for common AU roles
        ql = query.lower()
        for k, v in _FALLBACK_AU.items():
            if k in ql:
                estimate = v
                fallback_used = True
                break

    return {
        "query": q,
        "estimate_aud": estimate,
        "samples_used": len(nums),
        "hits": hits[:3],
        "error": error,
        "fallback_used": fallback_used,
        "ddg_impl": DDG_KIND
    }
