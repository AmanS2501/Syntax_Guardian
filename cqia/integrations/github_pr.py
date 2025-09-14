from __future__ import annotations
import os
import json
import requests
from typing import Optional

class GitHubPRClient:
    def __init__(self, token: Optional[str] = None, api_base: str = "https://api.github.com"):
        self.api_base = api_base.rstrip("/")
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not self.token:
            raise ValueError("Missing GitHub token (set GITHUB_TOKEN or GH_TOKEN).")

    def _headers(self) -> dict:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def comment_issue(self, owner: str, repo: str, number: int, body: str) -> dict:
        # Works for PRs (they are issues)
        url = f"{self.api_base}/repos/{owner}/{repo}/issues/{number}/comments"
        r = requests.post(url, headers=self._headers(), json={"body": body}, timeout=60)
        r.raise_for_status()
        return r.json()

    def review_comment_on_pr(self, owner: str, repo: str, pull_number: int, body: str,
                             commit_id: str, path: str, line: int, side: str = "RIGHT") -> dict:
        url = f"{self.api_base}/repos/{owner}/{repo}/pulls/{pull_number}/comments"
        payload = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "line": int(line),
            "side": side,
        }
        r = requests.post(url, headers=self._headers(), json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
