#!/usr/bin/env python3
"""Apply branch protection rules for main branch.

Requires token with repo admin permission (e.g. ADMIN_GITHUB_TOKEN).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def _fail(msg: str) -> None:
    print(f"[BRANCH-PROTECTION] ERROR: {msg}")
    raise SystemExit(1)


def _headers(token: str) -> dict[str, str]:
    if not token:
        _fail("ADMIN_GITHUB_TOKEN is required")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "agri-news-brief-branch-protection",
        "Content-Type": "application/json",
    }


def main() -> None:
    repo = _env("GITHUB_REPOSITORY")
    token = _env("ADMIN_GITHUB_TOKEN")
    contexts_raw = _env("BRANCH_PROTECTION_REQUIRED_CONTEXTS", "agri-news-brief (ci) / lint-and-test")
    required_contexts = [x.strip() for x in contexts_raw.split(",") if x.strip()]

    if not repo:
        _fail("GITHUB_REPOSITORY is required")
    if not required_contexts:
        _fail("At least one required status check context is required")

    url = f"https://api.github.com/repos/{repo}/branches/main/protection"
    payload = {
        "required_status_checks": {
            "strict": True,
            "contexts": required_contexts,
        },
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": 1,
            "require_last_push_approval": True,
        },
        "restrictions": None,
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": True,
        "lock_branch": False,
        "allow_fork_syncing": True,
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PUT", headers=_headers(token))

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                _fail(f"Unexpected response status: {resp.status}")
            out = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        _fail(f"GitHub API HTTP {exc.code}: {detail}")

    print("[BRANCH-PROTECTION] main branch protection applied successfully")
    print(f"[BRANCH-PROTECTION] required checks: {', '.join(required_contexts)}")
    print(f"[BRANCH-PROTECTION] url: {out.get('url', '<unknown>')}")


if __name__ == "__main__":
    main()
