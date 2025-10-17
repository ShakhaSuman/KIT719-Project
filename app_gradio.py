from __future__ import annotations

import json
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import gradio as gr

from router import route


def ask(q: str):
    if not q.strip():
        return "Please enter a question.", "", "", ""
    r = route(q.strip())
    route_txt = f'Route: {r.get("route","<unknown>")}'
    rag_ans = ""
    cits = ""
    tool_json = ""
    if "rag" in r:
        rag = r["rag"] or {}
        rag_ans = rag.get("answer", "")
        cs = rag.get("citations", [])
        if cs:
            lines = [
                f'[{i+1}] {(c.get("source") or c.get("role_title"))} (chunk {c.get("chunk_id")}): {c.get("preview","")}'
                for i, c in enumerate(cs)
            ]
            cits = "\n".join(lines)
    if "tool" in r:
        tool_json = json.dumps(r["tool"], indent=2)
    if "tools" in r:
        tool_json = json.dumps(r["tools"], indent=2)
    return route_txt, rag_ans, cits, tool_json or "<no tool output>"


with gr.Blocks(title="KIT719 QA System – Member C") as demo:
    gr.Markdown("# KIT719 QA System – Member C\n**RAG + Salary Tool**")
    q = gr.Textbox(label="Your question")
    btn = gr.Button("Ask")
    route_box = gr.Textbox(label="Routing", interactive=False)
    with gr.Tab("RAG Answer"):
        rag_box = gr.TextArea(label="Answer (Grounded)", interactive=False, lines=10)
        cits_box = gr.TextArea(label="Citations", interactive=False, lines=6)
    with gr.Tab("Tools / Errors"):
        tool_box = gr.Code(label="Tool Results / Errors", language="json")
    btn.click(fn=ask, inputs=[q], outputs=[route_box, rag_box, cits_box, tool_box])
    q.submit(fn=ask, inputs=[q], outputs=[route_box, rag_box, cits_box, tool_box])
if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
