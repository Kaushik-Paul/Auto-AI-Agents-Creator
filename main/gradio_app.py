#!/usr/bin/env python
import os
import sys
import threading
import time
import re
from typing import Optional, Tuple

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import gradio as gr
from main.pipeline import run_pipeline

# Single example replaced with the current system_message from main/agent.py
EXAMPLE_PROMPTS = [
    (
        "You are a creative entrepreneur. Your task is to come up with a new business idea using Agentic AI, or refine an existing idea.\n"
        "Your personal interests are in these sectors: Healthcare, Education.\n"
        "You are drawn to ideas that involve disruption.\n"
        "You are less interested in ideas that are purely automation.\n"
        "You are optimistic, adventurous and have risk appetite. You are imaginative - sometimes too much so.\n"
        "Your weaknesses: you're not patient, and can be impulsive.\n"
        "You should respond with your business ideas in an engaging and clear way."
    )
]

def _safe_markdown(md: Optional[str]) -> str:
    return md or "No idea content available."

def run_pipeline_wrapper(agent_prompt: str):
    # Initial state: show progress, keep result boxes hidden, disable button
    bar_len = 24
    pct = 1
    filled = int(bar_len * pct / 100)
    bar = ("█" * filled) + ("░" * (bar_len - filled))
    yield (
        gr.update(value=f"[{bar}] {pct}% - Generating agents…", visible=True),
        gr.update(visible=False),  # results_col - initially hidden
        gr.update(value="", visible=False),   # agents_url_box
        gr.update(value="", visible=False),   # ideas_url_box
        gr.update(visible=False),  # last_idea_md - no initial message
        gr.update(interactive=False, value="Running…")  # run_btn
    )

    result_holder = {"result": None}
    done = threading.Event()

    def worker():
        try:
            result_holder["result"] = run_pipeline(agent_prompt)
        finally:
            done.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    start = time.time()
    total = 60.0  # 1 minute
    last_pct = 1

    while not done.is_set():
        elapsed = time.time() - start
        pct = min(95, max(1, int((elapsed / total) * 95)))
        if pct != last_pct:
            last_pct = pct
            filled = int(bar_len * pct / 100)
            bar = ("█" * filled) + ("░" * (bar_len - filled))
            status = "Generating agents…" if elapsed < (total / 2.0) else "Creating ideas…"
            yield (
                gr.update(value=f"[{bar}] {pct}% - {status}", visible=True),
                gr.update(visible=False),  # Keep results_col hidden during processing
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(interactive=False, value="Running…")
            )
        time.sleep(1.0)

    t.join()

    agents_url, ideas_url, last_idea_md = result_holder["result"] or (None, None, None)

    # Minimal validation for URLs
    def valid_url(u: Optional[str]) -> str:
        if not u:
            return ""
        ok = re.match(r"^https?://[A-Za-z0-9._:-]+(?:/\S*)?$", u)
        return u if ok else ""

    # Final state: hide progress, show results, re-enable button
    agents_url_valid = valid_url(agents_url)
    ideas_url_valid = valid_url(ideas_url)
    
    yield (
        gr.update(value="", visible=False),  # progress_md - hide progress
        gr.update(visible=bool(agents_url_valid or ideas_url_valid)),  # Show results only if we have URLs
        gr.update(value=agents_url_valid, visible=bool(agents_url_valid)),  # agents_url_box
        gr.update(value=ideas_url_valid, visible=bool(ideas_url_valid)),    # ideas_url_box
        gr.update(value=_safe_markdown(last_idea_md), visible=bool(last_idea_md)),  # last_idea_md
        gr.update(interactive=True, value="Auto generate agents")  # run_btn
    )

def create_interface():
    """Create and return the Gradio interface."""
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", secondary_hue="indigo")) as demo:
        # Header
        with gr.Row(elem_classes=["header"]):
            with gr.Column():
                gr.Markdown("# 🚀 Auto AI Agents Creator", elem_classes=["brand"])
                gr.Markdown(
                    "Let AI spin up a smart team of agents that talk to each other and execute tasks crafted for your needs.",
                    elem_classes=["subtitle"],
                )

        # Main content
        with gr.Row():
            with gr.Column(scale=3):
                agent_prompt = gr.Textbox(
                    label="Agent Prompt",
                    placeholder="Describe what kind of AI agent you want to create...",
                    lines=8,
                    max_lines=12,
                    elem_classes=["card"],
                )
            with gr.Column(scale=2):
                gr.Markdown("### Example", elem_classes=["section-title"])
                gr.Markdown("Click to auto-fill the Agent Prompt:")
                gr.Examples(
                    examples=[[p] for p in EXAMPLE_PROMPTS],
                    inputs=[agent_prompt],
                    label="Examples"
                )

        # Centered Run button
        with gr.Row(elem_classes=["center-row"]):
            run_btn = gr.Button("Run Pipeline", variant="primary", elem_id="run-btn")

        # Progress display (shown during run)
        with gr.Row(elem_classes=["progress-container"]):
            progress_md = gr.Markdown(
                value="",
                elem_classes=["progress-text"],
                visible=False,
                container=False,
                elem_id="progress_md",
            )

        # Results below the button, initially hidden
        with gr.Column(visible=False) as results_col:
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Generated Agents", elem_classes=["section-title"])
                    agents_url_box = gr.Textbox(
                        label="Agents URL",
                        placeholder="Agents will appear here after generation...",
                        interactive=False,
                        elem_classes=["card"],
                        show_copy_button=True,
                    )
                with gr.Column(scale=1):
                    gr.Markdown("### Generated Ideas", elem_classes=["section-title"])
                    ideas_url_box = gr.Textbox(
                        label="Ideas URL",
                        placeholder="Ideas will appear here after generation...",
                        interactive=False,
                        elem_classes=["card"],
                        show_copy_button=True,
                    )

            with gr.Row():
                last_idea_md = gr.Markdown(
                    value="",
                    elem_classes=[],
                    visible=False,
                    container=False,
                    elem_id="last_idea_md",
                )

        # Connect the button to the pipeline
        run_btn.click(
            fn=run_pipeline_wrapper,
            inputs=[agent_prompt],
            outputs=[
                progress_md,
                results_col,
                agents_url_box,
                ideas_url_box,
                last_idea_md,
                run_btn
            ],
            show_progress="hidden",
        )

        # Custom CSS for the app
        demo.css = """
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700;800&family=Manrope:wght@400;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
        html, body { background: #0b1220; color: #e2e8f0; font-family: Manrope, Inter, Helvetica, Arial, sans-serif; overflow-x: hidden; }
        .gradio-container { max-width: 100% !important; width: 100% !important; margin: 0 auto !important; padding: 0 16px; }
        .header { max-width: 100%; margin: 24px auto 8px; padding: 12px 16px; text-align: center; }
        .brand { font-family: Space Grotesk, Manrope, Inter, sans-serif; font-weight: 800; font-size: 40px; letter-spacing: .3px; background: linear-gradient(90deg,#06b6d4 0%,#a78bfa 45%,#fb7185 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 4px 36px rgba(167,139,250,.35); }
        .subtitle { 
            margin: 8px auto 12px;
            font-weight: 500;
            font-family: 'Manrope', sans-serif;
            letter-spacing: 0.03em;
            line-height: 1.6;
            max-width: 720px;
            text-align: center;
            font-size: 1.1rem;
            background: linear-gradient(90deg, #06b6d4 0%, #a78bfa 50%, #fb7185 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 2px 8px rgba(167,139,250,0.3);
        }
        .section-title { color: #93c5fd; }
        .card { border: 1px solid rgba(148,163,184,.18); border-radius: 14px; padding: 10px; background: linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.02)); box-shadow: 0 6px 18px rgba(0,0,0,.28); backdrop-filter: blur(4px); }
        #run-btn { background: linear-gradient(90deg,#06b6d4,#a78bfa,#fb7185); color: white; padding: 12px 24px; font-size: 16px; border-radius: 10px; border: none; transition: transform .15s ease, opacity .2s ease; }
        #run-btn:hover:not(:disabled) { transform: translateY(-1px); }
        #run-btn:disabled { cursor: not-allowed !important; opacity: .7 !important; }
        .center-row { display: flex; justify-content: center; }
        /* Center the progress bar and text */
        .progress-container { display: grid; grid-template-columns: 1fr; justify-items: stretch; width: 100%; margin: 10px 0; gap: 0; }
        .md-container { display: grid; grid-template-columns: 1fr; justify-items: stretch; width: 100%; gap: 0; }
        .progress-container > *, .md-container > * { grid-column: 1 / -1; width: 100%; }
        #progress_md, #last_idea_md { width: 100%; }
        #progress_md > div, #last_idea_md > div { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; }
        .progress-text, .progress-pre { text-align: center; width: 100%; font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; letter-spacing: 0.5px; }
        .progress-pre { background: transparent; color: #0b1220; margin: 0; white-space: pre; }
        /* Single white card used by HTML templates */
        .single-card { background: #ffffff; color: #0b1220; border-radius: 12px; border: 1px solid rgba(148,163,184,.2); box-shadow: 0 6px 18px rgba(0,0,0,.16); padding: 14px; width: 100%; display: block; background-clip: padding-box; overflow: hidden; }
        #progress_md .single-card, #last_idea_md .single-card { width: 100%; display: block; box-sizing: border-box; overflow: hidden; }
        .md-body { line-height: 1.65; }
        .md-body h1, .md-body h2, .md-body h3 { color: #0f172a; margin: 12px 0; font-family: Manrope, Inter, sans-serif; }
        .md-body h1 { font-size: 28px; }
        .md-body h2 { font-size: 22px; }
        .md-body h3 { font-size: 18px; }
        .md-body p { margin: 10px 0; }
        .md-body ul { padding-left: 20px; }
        .md-body li { margin: 4px 0; }
        """
        
        demo.queue()
        return demo
