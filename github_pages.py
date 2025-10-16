# github_pages.py
import base64
from typing import Dict, Tuple
import httpx

API = "https://api.github.com"

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def ensure_repo_exists(owner: str, repo: str, token: str) -> Tuple[str, str]:
    """
    Create if missing, else return. Returns (repo_html_url, repo_api_url).
    """
    headers = _headers(token)
    with httpx.Client(headers=headers, timeout=30) as client:
        r = client.get(f"{API}/repos/{owner}/{repo}")
        if r.status_code == 404:
            c = client.post(f"{API}/user/repos", json={"name": repo, "private": False, "auto_init": True})
            c.raise_for_status()
            data = c.json()
        else:
            r.raise_for_status()
            data = r.json()
        return data["html_url"], data["url"]

def _get_sha_if_exists(owner: str, repo: str, path: str, token: str):
    headers = _headers(token)
    with httpx.Client(headers=headers, timeout=30) as client:
        g = client.get(f"{API}/repos/{owner}/{repo}/contents/{path}")
        if g.status_code == 200:
            return g.json().get("sha")
        return None

def commit_files(owner: str, repo: str, token: str, files: Dict[str, bytes], message: str) -> str:
    """
    PUT /contents for each file on branch 'main'. Returns latest main commit SHA.
    """
    headers = _headers(token)
    with httpx.Client(headers=headers, timeout=60) as client:
        for path, content_bytes in files.items():
            sha = _get_sha_if_exists(owner, repo, path, token)
            payload = {
                "message": message,
                "content": base64.b64encode(content_bytes).decode("ascii"),
                "branch": "main",
            }
            if sha:
                payload["sha"] = sha
            r = client.put(f"{API}/repos/{owner}/{repo}/contents/{path}", json=payload)
            r.raise_for_status()
        ref = client.get(f"{API}/repos/{owner}/{repo}/git/ref/heads/main")
        ref.raise_for_status()
        return ref.json()["object"]["sha"]

def enable_pages_root(owner: str, repo: str, token: str) -> str:
    """
    Enable Pages from 'main' root path. Return the Pages URL.
    """
    headers = _headers(token)
    with httpx.Client(headers=headers, timeout=30) as client:
        payload = {"source": {"branch": "main", "path": "/"}}
        r = client.post(f"{API}/repos/{owner}/{repo}/pages", json=payload)
        if r.status_code not in (201, 204):
            client.put(f"{API}/repos/{owner}/{repo}/pages", json=payload)
        g = client.get(f"{API}/repos/{owner}/{repo}/pages")
        g.raise_for_status()
        data = g.json()
        return data.get("html_url") or data.get("url") or f"https://{owner}.github.io/{repo}/"
