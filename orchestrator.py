from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable


@dataclass(frozen=True)
class OrchestratorContext:
    repo: str
    end_kst: datetime
    maintenance_task: str
    force_report_date: str
    force_run_anyday: bool
    naver_ready: bool
    kakao_ready: bool


@dataclass(frozen=True)
class OrchestratorHandlers:
    run_ux_patch: Callable[[str, datetime], None]
    run_maintenance_rebuild: Callable[[str, datetime, str], None]
    run_force_rebuild: Callable[[str, datetime], None]
    run_daily: Callable[[str, datetime, str], None]
    is_business_day: Callable[[datetime], bool]
    on_skip_non_business: Callable[[datetime], None]


def execute_orchestration(ctx: OrchestratorContext, handlers: OrchestratorHandlers) -> None:
    task = (ctx.maintenance_task or "").strip().lower()

    if task == "ux_patch":
        handlers.run_ux_patch(ctx.repo, ctx.end_kst)
        return

    if task == "replay_date":
        handlers.run_maintenance_rebuild(ctx.repo, ctx.end_kst, task)
        return

    if task in ("rebuild_date", "backfill_rebuild"):
        if not ctx.naver_ready:
            raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
        handlers.run_maintenance_rebuild(ctx.repo, ctx.end_kst, task)
        return

    if ctx.force_report_date:
        if not ctx.naver_ready:
            raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
        handlers.run_force_rebuild(ctx.repo, ctx.end_kst)
        return

    if not ctx.naver_ready:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
    if not ctx.kakao_ready:
        raise RuntimeError("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN is not set")

    if (not ctx.force_run_anyday) and (not handlers.is_business_day(ctx.end_kst)):
        handlers.on_skip_non_business(ctx.end_kst)
        return

    handlers.run_daily(ctx.repo, ctx.end_kst, task)
