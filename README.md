# Meta App Builder (Gradio + FastAPI on HF Spaces)

**Endpoints**
- `POST /submit` — build & deploy (or update) a static app to GitHub Pages
- `POST /revise` — same schema; round-2 updates
- `GET /healthz` — health
- `/` — tiny Gradio UI (manual preview only)

**Env (HF Space → Settings → Variables & secrets)**
- `STUDENT_EMAIL` — your email
- `STUDENT_SECRET` — your shared secret
- `GITHUB_TOKEN` — PAT with `repo` scope
- `GH_USERNAME` — your GitHub username
- `GH_REPO_PREFIX` — optional (default `tds-`)
- `OPENAI_API_KEY` — optional (for real LLM generation)
- `OPENAI_MODEL` — optional (default `gpt-4o-mini`)

**Test**
```bash
curl -X POST "https://<user>-<space>.hf.space/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"student@example.com",
    "secret":"change-me",
    "task":"sum-of-sales",
    "round":1,
    "nonce":"ab12-xyz",
    "brief":"Publish a single-page site that fetches data.csv from attachments, sums its sales column, sets the title to \"Sales Summary ${seed}\", displays the total inside #total-sales, and loads Bootstrap 5 from jsdelivr.",
    "checks":[
      "js: document.title === `Sales Summary ${seed}`",
      "js: !!document.querySelector(\"link[href*='bootstrap']\")",
      "js: Math.abs(parseFloat(document.querySelector(\"#total-sales\").textContent) - ${result}) < 0.01"
    ],
    "evaluation_url":"https://httpbin.org/post",
    "attachments":[{"name":"data.csv","url":"data:text/csv;base64,PHByb2R1Y3Qsc2FsZXMK..."}]
  }'
