# llm_generator.py
import os
from textwrap import dedent
from typing import Dict, List

# SAFE init: only create client if a key exists
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client = None
_model = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        # short timeout to avoid long hangs
        _client = OpenAI(api_key=OPENAI_API_KEY, timeout=15.0)
        _model = OPENAI_MODEL
    except Exception as e:
        print("[llm] init failed, falling back:", e)
        _client = None
        _model = None


MIT_LICENSE = """\
MIT License

Copyright (c) {year}

Permission is hereby granted, free of charge, to any person obtaining a copy...
"""

def _index_html_prompt(brief: str, checks: List[str], attachments: List[str]) -> str:
    return dedent(f"""
    You are a senior front-end engineer. Build a **static**, GitHub Pages–friendly
    single-page app that satisfies:

    Brief:
    {brief}

    Checks to consider (selectors/behaviors expected by graders):
    {chr(10).join('- ' + c for c in checks)}

    Attachments in repo (filenames):
    {chr(10).join('- ' + f for f in attachments) if attachments else '- (none)'}

    Rules:
    - No build step, no bundlers, no frameworks. Plain HTML+CSS+JS.
    - If checks mention Bootstrap, include its CSS from jsDelivr.
    - Create elements/IDs referenced in checks (e.g., #total-sales, #product-sales).
    - Parse query params if checks mention ?url= or ?token=.
    - If data files are present (e.g., data.csv, rates.json), load via fetch('./data.csv').
    - Include an aria-live region if instructed.
    - Keep the page accessible and responsive.
    - Link to style.css and script.js.

    Return ONLY the HTML for index.html.
    """)

def _script_js_prompt(brief: str, checks: List[str], attachments: List[str]) -> str:
    return dedent(f"""
    Write vanilla JavaScript implementing the page logic.

    Brief:
    {brief}

    Checks:
    {chr(10).join('- ' + c for c in checks)}

    Attachments available locally:
    {chr(10).join('- ' + f for f in attachments) if attachments else '- (none)'}

    Requirements:
    - Implement the calculations/DOM updates implied by checks.
    - If 'data.csv' exists, fetch('./data.csv') and parse CSV to compute totals.
    - If 'rates.json' exists, fetch('./rates.json') and use it for conversion.
    - If checks reference localStorage or aria-live, implement it.
    - Populate the specific IDs referenced by checks (e.g., #github-created-at).
    - Keep JS short, commented, and robust.

    Return ONLY the JavaScript (no HTML).
    """)

def _style_css() -> str:
    return dedent("""
    :root { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
    body { margin: 0; padding: 1rem; background: #fafafa; color: #222; }
    main { max-width: 900px; margin: 0 auto; }
    #result { margin-top: .75rem; padding: .5rem; background: #fff; border: 1px solid #ddd; border-radius: 6px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #eee; padding: .5rem; text-align: left; }
    """)

def _fallback_index_html(brief: str, checks: List[str], attachments: List[str]) -> str:
    return dedent(f"""
    <!doctype html><html lang="en"><head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width,initial-scale=1"/>
      <title>Generated App (fallback)</title>
      <link rel="stylesheet" href="style.css">
    </head><body>
      <main>
        <h1>Generated App (No LLM configured)</h1>
        <p><strong>Brief:</strong> {brief}</p>
        <p><strong>Checks:</strong> {', '.join(checks) or '(none)'} </p>
        <div id="result">Set OPENAI_API_KEY to enable full generation.</div>
        <script src="script.js"></script>
      </main>
    </body></html>
    """).strip()

def _fallback_script_js() -> str:
    return dedent("""
    (function () {
      const out = document.getElementById('result');
      const q = new URLSearchParams(location.search);
      if (out) out.textContent = 'Params: ' + q.toString();
    })();
    """).strip()
    
def generate_app_files(brief: str, checks: List[str], attachments: List[str]) -> Dict[str, str]:
    """
    Returns {path -> UTF-8 text}. Attachments are handled separately.
    """
    use_fallback = False
    html = js = css = ""

    if _client:
        try:
            html = _client.chat.completions.create(
                model=_model, temperature=0.2,
                messages=[
                    {"role": "system", "content": "You write compact, production-ready HTML/CSS/JS."},
                    {"role": "user", "content": _index_html_prompt(brief, checks, attachments)},
                ],
            ).choices[0].message.content.strip()
        except Exception as e:
            # Log and fallback
            print(f"[llm] HTML gen failed: {e}")
            use_fallback = True

        if not use_fallback:
            try:
                js = _client.chat.completions.create(
                    model=_model, temperature=0.2,
                    messages=[
                        {"role": "system", "content": "You write robust, minimal vanilla JS for static pages."},
                        {"role": "user", "content": _script_js_prompt(brief, checks, attachments)},
                    ],
                ).choices[0].message.content.strip()
            except Exception as e:
                print(f"[llm] JS gen failed: {e}")
                use_fallback = True

    else:
        use_fallback = True

    if use_fallback:
        html = _fallback_index_html(brief, checks, attachments)
        js = _fallback_script_js()

    css = _style_css()

    readme = dedent(f"""
    # Generated App (GitHub Pages)

    **Brief**
    {brief}

    **Checks**
    {chr(10).join('- ' + c for c in checks)}

    ## Notes
    - Static site; loads local files via fetch if present.
    - Elements and IDs are created to satisfy automated checks when possible.
    """)

    license_txt = MIT_LICENSE.format(year="2025")

    return {
        "index.html": html,
        "style.css": css,
        "script.js": js,
        "README.md": readme,
        "LICENSE": license_txt,
    }
