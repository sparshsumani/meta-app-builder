# app.py
import os
import time
from typing import Dict, Tuple

from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import gradio as gr

from schemas import SubmitPayload
from attachments import decode_and_collect_attachments
from llm_generator import generate_app_files
from github_pages import ensure_repo_exists, commit_files, enable_pages_root

# ---------------- ENV / Config ----------------
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "student@example.com")
STUDENT_SECRET = os.getenv("STUDENT_SECRET", "change-me")

GH_TOKEN = os.getenv("GITHUB_TOKEN")     # GitHub PAT with 'repo' scope
GH_USERNAME = os.getenv("GH_USERNAME")   # your GitHub username
GH_REPO_PREFIX = os.getenv("GH_REPO_PREFIX", "tds-")

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))

if not GH_TOKEN or not GH_USERNAME:
    raise RuntimeError("Missing GITHUB_TOKEN or GH_USERNAME env vars")

# ---------------- FastAPI ----------------
api = FastAPI(title="Meta App Builder (Build → Deploy → Revise)")

# Permissive CORS if this is called from browsers
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api.get("/healthz")
def healthz():
    return {"ok": True, "service": "meta-app-builder"}

def _auth(payload: SubmitPayload):
    if payload.email != STUDENT_EMAIL or payload.secret != STUDENT_SECRET:
        raise HTTPException(status_code=401, detail="email/secret mismatch")

async def _notify(url: str, body: Dict) -> Dict:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
            try:
                return r.json()
            except Exception:
                return {"status_code": r.status_code, "text": r.text}
    except Exception as e:
        return {"error": str(e)}

def _repo_name(task: str) -> str:
    return f"{GH_REPO_PREFIX}{task}".replace("/", "-").replace(" ", "-")

def _deploy_once(payload: SubmitPayload) -> Tuple[str, str, str]:
    """
    Returns: (repo_url, pages_url, commit_sha)
    """
    repo = _repo_name(payload.task)

    # 1) Ensure repo exists (public)
    repo_html_url, _repo_api = ensure_repo_exists(GH_USERNAME, repo, GH_TOKEN)

    # 2) Decode attachments (data URIs -> bytes) => {filename: bytes}
    attachment_files = decode_and_collect_attachments(payload.attachments)

    # 3) Generate app files (text) from brief + checks + attachment names
    app_files_text = generate_app_files(
        brief=payload.brief,
        checks=payload.checks,
        attachments=list(attachment_files.keys()),
    )

    # 4) Merge app files (utf-8) + attachments (bytes)
    files_to_commit: Dict[str, bytes] = {}
    for path, text in app_files_text.items():
        files_to_commit[path] = text.encode("utf-8")
    for path, blob in attachment_files.items():
        files_to_commit[path] = blob

    # 5) Commit to main
    commit_sha = commit_files(
        owner=GH_USERNAME,
        repo=repo,
        token=GH_TOKEN,
        files=files_to_commit,
        message=f"{'revise' if payload.round > 1 else 'initial'}: {payload.task}",
    )

    # 6) Enable GitHub Pages (idempotent)
    pages_url = enable_pages_root(owner=GH_USERNAME, repo=repo, token=GH_TOKEN)

    return repo_html_url, pages_url, commit_sha

@api.post("/submit")
async def submit(payload: SubmitPayload):
    """
    Round 1 (and can handle round 2 as well if you call it again):
    - verify
    - build/update static app
    - deploy to GitHub Pages
    - ping evaluation_url
    - respond with required JSON
    """
    t0 = time.time()
    _auth(payload)

    # This is the updated line:
    repo_url, pages_url, commit_sha = await run_in_threadpool(_deploy_once, payload)

    elapsed_ms = int((time.time() - t0) * 1000)

    notify_body = {
        "email": payload.email,
        "task": payload.task,
        "round": payload.round,
        "nonce": payload.nonce,
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha,
        "latency_ms": elapsed_ms,
    }
    _ = await _notify(payload.evaluation_url, notify_body)

    # Respond EXACTLY as required
    return JSONResponse(
        {
            "email": payload.email,
            "task": payload.task,
            "round": payload.round,
            "nonce": payload.nonce,
            "repo_url": repo_url,
            "commit_sha": commit_sha,
            "pages_url": pages_url,
        }
    )

@api.post("/revise")
async def revise(payload: SubmitPayload):
    # Same contract; you can route round-2 here if preferred
    return await submit(payload)

# ---------------- Gradio UI (for manual smoke tests) ----------------
def ui_preview(task, brief, checks_text):
    # trivial view only
    return {
        "task": task,
        "brief": brief,
        "checks": [c.strip() for c in (checks_text or "").split("\n") if c.strip()],
        "hint": "POST JSON to /submit from your client for real deployment",
    }

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🧰 Meta App Builder\nLLM-assisted builder that deploys static apps to GitHub Pages.")
    with gr.Row():
        t = gr.Textbox(label="task", value="sum-of-sales")
        b = gr.Textbox(label="brief", lines=4, value="Publish a single-page site that sums data.csv sales…")
    c = gr.Textbox(label="checks (one per line)", lines=4)
    btn = gr.Button("Preview payload")
    out = gr.JSON(label="Preview")
    btn.click(ui_preview, [t, b, c], out)

# Mount Gradio UI at "/" and keep FastAPI routes
app = gr.mount_gradio_app(api, demo, path="/")