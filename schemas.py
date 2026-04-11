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
    size: NotRequired[int]


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

    out: NaverSearchResponse = {"items": []}

    raw_items = data.get("items", [])
    if isinstance(raw_items, list):
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue

            item: NaverNewsItem = {}
            title = raw.get("title")
            description = raw.get("description")
            link = raw.get("link")
            originallink = raw.get("originallink")
            pub_date = raw.get("pubDate")

            if isinstance(title, str):
                item["title"] = title
            if isinstance(description, str):
                item["description"] = description
            if isinstance(link, str):
                item["link"] = link
            if isinstance(originallink, str):
                item["originallink"] = originallink
            if isinstance(pub_date, str):
                item["pubDate"] = pub_date

            out["items"].append(item)

    total = data.get("total")
    start = data.get("start")
    display = data.get("display")
    error_code = data.get("errorCode")
    error_message = data.get("errorMessage")
    message = data.get("message")

    if isinstance(total, int):
        out["total"] = total
    if isinstance(start, int):
        out["start"] = start
    if isinstance(display, int):
        out["display"] = display
    if isinstance(error_code, str):
        out["errorCode"] = error_code
    if isinstance(error_message, str):
        out["errorMessage"] = error_message
    if isinstance(message, str):
        out["message"] = message

    return out


def ensure_github_dir_items(value: Any) -> list[GithubDirItem]:
    if not isinstance(value, list):
        return []

    out: list[GithubDirItem] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue

        item: GithubDirItem = {}
        name = raw.get("name")
        path = raw.get("path")
        sha = raw.get("sha")
        item_type = raw.get("type")
        size = raw.get("size")

        if isinstance(name, str):
            item["name"] = name
        if isinstance(path, str):
            item["path"] = path
        if isinstance(sha, str):
            item["sha"] = sha
        if isinstance(item_type, str):
            item["type"] = item_type
        if isinstance(size, int):
            item["size"] = size

        out.append(item)

    return out
