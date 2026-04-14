from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock, Thread
from time import monotonic, sleep
from typing import Callable
from typing import Any

from index_runtime import ActiveManifest, IndexRuntime


@dataclass
class ReindexState:
    status: str = "idle"
    actor: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    last_error: str | None = None
    active_version: str | None = None
    last_doc_count: int | None = None
    mode: str | None = None
    stats: dict[str, int] | None = None


class ReindexService:
    def __init__(self, runtime: IndexRuntime):
        self.runtime = runtime
        self._lock = Lock()
        active = runtime.read_active_manifest()
        self._state = ReindexState(
            active_version=active.version,
            last_doc_count=active.doc_count,
        )

    def status(self) -> ReindexState:
        with self._lock:
            return ReindexState(**self._state.__dict__)

    def start(
        self,
        actor: str,
        build_fn: Callable[[str, str], int],
        on_success: Callable[[ActiveManifest], None] | None = None,
        mode: str | None = None,
    ) -> tuple[bool, str]:
        with self._lock:
            if self._state.status == "running":
                return False, "reindex already running"

            self._state.status = "running"
            self._state.actor = actor
            self._state.started_at = datetime.now(timezone.utc).isoformat()
            self._state.finished_at = None
            self._state.last_error = None
            self._state.mode = mode
            self._state.stats = None

        worker = Thread(target=self._run_worker, args=(build_fn, on_success), daemon=True)
        worker.start()
        return True, "started"

    def wait_for_idle(self, timeout_seconds: int) -> None:
        deadline = monotonic() + timeout_seconds
        while monotonic() < deadline:
            with self._lock:
                if self._state.status != "running":
                    return
            sleep(0.05)
        raise TimeoutError("reindex still running")

    def _run_worker(
        self,
        build_fn: Callable[[str, str], int],
        on_success: Callable[[ActiveManifest], None] | None,
    ) -> None:
        terminal_status = "failed"
        terminal_error: str | None = None
        terminal_active_version: str | None = None
        terminal_doc_count: int | None = None
        previous_active = self.runtime.read_active_manifest()

        try:
            candidate = self.runtime.create_candidate_layout()
            doc_count = build_fn(
                str(candidate.content_index_path),
                str(candidate.title_index_path),
            )
            build_stats: dict[str, int] | None = None
            if isinstance(doc_count, tuple):
                count_value, stats_value = doc_count
                doc_count = int(count_value)
                if isinstance(stats_value, dict):
                    build_stats = {str(k): int(v) for k, v in stats_value.items()}
            self.runtime.promote_candidate(candidate, doc_count=doc_count)
            active = self.runtime.read_active_manifest()
            if on_success is not None:
                try:
                    on_success(active)
                except Exception:
                    self.runtime.set_active_manifest(previous_active)
                    recovered = self.runtime.read_active_manifest()
                    on_success(recovered)
                    raise
            terminal_status = "succeeded"
            terminal_active_version = active.version
            terminal_doc_count = active.doc_count
            terminal_stats = build_stats
        except Exception as exc:
            terminal_error = str(exc)
            terminal_stats = None
        finally:
            finished_at = datetime.now(timezone.utc).isoformat()
            with self._lock:
                self._state.status = terminal_status
                self._state.finished_at = finished_at
                self._state.last_error = terminal_error
                if terminal_status == "succeeded":
                    self._state.active_version = terminal_active_version
                    self._state.last_doc_count = terminal_doc_count
                    self._state.stats = terminal_stats
