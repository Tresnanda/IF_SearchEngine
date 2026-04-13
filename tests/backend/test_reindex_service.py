from pathlib import Path

from index_runtime import IndexRuntime
from reindex_service import ReindexService


def test_rejects_concurrent_reindex(tmp_path: Path):
    runtime = IndexRuntime(tmp_path)
    runtime.bootstrap_if_missing()

    service = ReindexService(runtime=runtime)
    service._state.status = "running"

    ok, _ = service.start(actor="admin@unud.ac.id", build_fn=lambda *_: 1)
    assert ok is False


def test_failed_build_keeps_active_version(tmp_path: Path):
    runtime = IndexRuntime(tmp_path)
    runtime.bootstrap_if_missing()
    before = runtime.read_active_manifest().version

    service = ReindexService(runtime=runtime)

    def failing_build(*_args):
        raise RuntimeError("boom")

    ok, _ = service.start(actor="admin@unud.ac.id", build_fn=failing_build)
    assert ok is True

    service.wait_for_idle(timeout_seconds=5)

    after = runtime.read_active_manifest().version
    assert before == after
    assert service.status().status == "failed"


def test_candidate_creation_failure_sets_failed_and_finished_at(tmp_path: Path, monkeypatch):
    runtime = IndexRuntime(tmp_path)
    runtime.bootstrap_if_missing()
    service = ReindexService(runtime=runtime)

    def fail_create_candidate_layout():
        raise RuntimeError("candidate-create-failed")

    monkeypatch.setattr(runtime, "create_candidate_layout", fail_create_candidate_layout)

    ok, _ = service.start(actor="admin@unud.ac.id", build_fn=lambda *_: 1)
    assert ok is True

    service.wait_for_idle(timeout_seconds=5)
    state = service.status()
    assert state.status == "failed"
    assert state.last_error == "candidate-create-failed"
    assert state.finished_at is not None


def test_successful_reindex_updates_state_and_active_manifest(tmp_path: Path):
    runtime = IndexRuntime(tmp_path)
    runtime.bootstrap_if_missing()
    service = ReindexService(runtime=runtime)

    def successful_build(content_path: str, title_path: str) -> int:
        Path(content_path).write_bytes(b"content-v2")
        Path(title_path).write_bytes(b"title-v2")
        return 42

    ok, _ = service.start(actor="admin@unud.ac.id", build_fn=successful_build)
    assert ok is True

    service.wait_for_idle(timeout_seconds=5)

    state = service.status()
    active = runtime.read_active_manifest()
    assert state.status == "succeeded"
    assert state.finished_at is not None
    assert state.active_version == active.version
    assert state.last_doc_count == 42
    assert active.doc_count == 42


def test_callback_failure_after_promote_recovers_previous_active(tmp_path: Path):
    runtime = IndexRuntime(tmp_path)
    runtime.bootstrap_if_missing()
    before = runtime.read_active_manifest().version
    service = ReindexService(runtime=runtime)

    def successful_build(content_path: str, title_path: str) -> int:
        Path(content_path).write_bytes(b"content-v2")
        Path(title_path).write_bytes(b"title-v2")
        return 7

    callback_calls: list[str] = []

    def flaky_callback(active_manifest) -> None:
        callback_calls.append(active_manifest.version)
        if len(callback_calls) == 1:
            raise RuntimeError("engine reload failed")

    ok, _ = service.start(
        actor="admin@unud.ac.id",
        build_fn=successful_build,
        on_success=flaky_callback,
    )
    assert ok is True

    service.wait_for_idle(timeout_seconds=5)

    state = service.status()
    assert state.status == "failed"
    assert state.last_error == "engine reload failed"
    assert runtime.read_active_manifest().version == before
    assert len(callback_calls) == 2
    assert callback_calls[1] == before
