from __future__ import annotations
import json
from tools.salary_tool import salary_tool


def simple_route(q: str) -> str:
    """
    Basic keyword-based routing.
    Since the calculator tool is removed, any pay-related query
    will be directed to the salary tool.
    """
    ql = q.lower()
    if any(k in ql for k in ["salary", "pay", "wage", "average", "convert", "per hour", "raise", "%", "increase"]):
        return "tool:salary"
    return "rag"


def eval_file(path: str):
    """
    Evaluates each query in the provided JSON file.
    Routes to salary_tool for relevant queries.
    """
    cases = json.load(open(path, "r", encoding="utf-8"))
    results = []

    for c in cases:
        q = c["question"]
        route = c.get("expected_route") or simple_route(q)
        out = None

        if route == "tool:salary":
            out = salary_tool(q)
        else:
            out = {"note": "RAG response expected or not applicable in this module."}

        results.append({
            "question": q,
            "route": route,
            "result": out
        })

    return {"file": path, "results": results}


if __name__ == "__main__":
    # Evaluate the baseline dataset
    report = eval_file("career-assistant/ground_truth/baseline_tool.json")
    print(json.dumps(report, indent=2))
