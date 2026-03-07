from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict


class GithubContentFile(TypedDict, total=False):
    content: str
    sha: str
    name: str
    path: str
    type: str


class GithubDirItem(TypedDict, total=False):
    name: str
    path: str
    sha: str
    type: str


class NaverNewsItem(TypedDict, total=False):
    title: str
    description: str
    link: str
    originallink: str
    pubDate: str


class NaverSearchResponse(TypedDict, total=False):
    items: list[NaverNewsItem]
    total: NotRequired[int]
    start: NotRequired[int]
    display: NotRequired[int]
    errorCode: NotRequired[str]
    errorMessage: NotRequired[str]
    message: NotRequired[str]


@dataclass(frozen=True)
class NaverSearchParams:
    query: str
    display: int
    start: int
    sort: str = "date"

    def to_request_params(self) -> dict[str, Any]:
        return {
            "query": str(self.query or ""),
            "display": max(1, int(self.display)),
            "start": max(1, int(self.start)),
            "sort": str(self.sort or "date"),
        }


@dataclass(frozen=True)
class GithubPutRequest:
    message: str
    content_b64: str
    branch: str = "main"
    sha: str | None = None

    def to_request_json(self) -> dict[str, str]:
        payload: dict[str, str] = {
            "message": self.message,
            "content": self.content_b64,
            "branch": self.branch,
        }
        if self.sha:
            payload["sha"] = self.sha
        return payload


def ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def ensure_naver_response(value: Any) -> NaverSearchResponse:
    data = ensure_dict(value)
    items = data.get("items", [])
    if not isinstance(items, list):
        items = []
    out: NaverSearchResponse = dict(data)
    out["items"] = items
    return out


def ensure_github_dir_items(value: Any) -> list[GithubDirItem]:
    if not isinstance(value, list):
        return []
    out: list[GithubDirItem] = []
    for item in value:
        if isinstance(item, dict):
            out.append(item)
    return out