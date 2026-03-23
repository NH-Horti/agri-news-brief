from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from io_github import github_get_file, github_put_file


LOG = logging.getLogger("replay_snapshot_repo")


def _session_factory() -> requests.Session:
    return requests.Session()


def _log_http_error(prefix: str, response: Any) -> None:
    try:
        detail = response.text
    except Exception:
        detail = "<no-body>"
    LOG.error("%s status=%s body=%s", prefix, getattr(response, "status_code", "?"), detail[:500])


def fetch_snapshot(args: argparse.Namespace) -> int:
    # GitHub Contents API has 1 MB limit; use raw download for large snapshots
    raw_url = f"https://raw.githubusercontent.com/{args.repo}/{args.ref}/{args.remote_path}"
    sess = _session_factory()
    resp = sess.get(raw_url, timeout=60)
    if resp.status_code == 404:
        LOG.warning("Snapshot not found via raw URL: %s", raw_url)
        # Fallback to Contents API for smaller files
        raw, _sha = github_get_file(
            args.repo,
            args.remote_path,
            args.token,
            ref=args.ref,
            session_factory=_session_factory,
            log_http_error=_log_http_error,
        )
        if raw is None:
            return 2
    elif not resp.ok:
        _log_http_error("[RAW FETCH ERROR]", resp)
        return 2
    else:
        raw = resp.text
    if not raw or not raw.strip():
        LOG.error("Fetched snapshot is empty")
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(raw, encoding="utf-8")
    LOG.info("Snapshot saved: %s (%d bytes)", output, len(raw))
    return 0


def push_snapshot(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    raw = input_path.read_text(encoding="utf-8")
    old_raw, sha = github_get_file(
        args.repo,
        args.remote_path,
        args.token,
        ref=args.branch,
        session_factory=_session_factory,
        log_http_error=_log_http_error,
    )
    if old_raw is not None and old_raw.strip() == raw.strip():
        LOG.info("Replay snapshot unchanged: %s", args.remote_path)
        return 0
    github_put_file(
        args.repo,
        args.remote_path,
        raw,
        args.token,
        args.message,
        sha=sha,
        branch=args.branch,
        session_factory=_session_factory,
        logger=LOG,
        log_http_error=_log_http_error,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch or publish replay snapshot files via GitHub Contents API.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--repo", required=True)
    fetch_parser.add_argument("--token", required=True)
    fetch_parser.add_argument("--ref", required=True)
    fetch_parser.add_argument("--remote-path", required=True)
    fetch_parser.add_argument("--output", required=True)
    fetch_parser.set_defaults(func=fetch_snapshot)

    push_parser = subparsers.add_parser("push")
    push_parser.add_argument("--repo", required=True)
    push_parser.add_argument("--token", required=True)
    push_parser.add_argument("--branch", required=True)
    push_parser.add_argument("--remote-path", required=True)
    push_parser.add_argument("--input", required=True)
    push_parser.add_argument("--message", required=True)
    push_parser.set_defaults(func=push_snapshot)

    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
