import os
import pickle
from io import BytesIO
from pathlib import Path

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

from backend import app


def test_health_live(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_health_ready_when_active_index_present(client, monkeypatch):
    monkeypatch.setattr("backend._build_engine_from_manifest", lambda _manifest: object())
    from backend import index_runtime

    manifest = index_runtime.read_active_manifest()
    manifest.content_index_path.write_bytes(pickle.dumps({"ok": 1}))
    manifest.title_index_path.write_bytes(pickle.dumps({"ok": 1}))

    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ready"] is True
    assert "active_version" in payload


def test_health_ready_false_when_active_index_unloadable(client):
    from backend import index_runtime

    manifest = index_runtime.read_active_manifest()
    original_bytes = manifest.content_index_path.read_bytes()

    try:
        manifest.content_index_path.write_bytes(b"not-a-pickle")
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.get_json()["ready"] is False
    finally:
        manifest.content_index_path.write_bytes(original_bytes)


def test_health_ready_does_not_recover_to_fallback_when_active_missing(client):
    from backend import index_runtime

    fallback = index_runtime.create_candidate_layout(version="ready-fallback")
    fallback.content_index_path.write_bytes(pickle.dumps({"ok": "fallback"}))
    fallback.title_index_path.write_bytes(pickle.dumps({"ok": "fallback"}))
    index_runtime.promote_candidate(fallback, doc_count=1)
    fallback_manifest = index_runtime.read_active_manifest()

    broken = index_runtime.create_candidate_layout(version="ready-broken")
    broken.content_index_path.write_bytes(pickle.dumps({"ok": "broken"}))
    broken.title_index_path.write_bytes(pickle.dumps({"ok": "broken"}))
    index_runtime.promote_candidate(broken, doc_count=2)
    broken_manifest = index_runtime.read_active_manifest()

    broken_manifest.content_index_path.unlink()

    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.get_json()["ready"] is False
        assert index_runtime.read_active_manifest().version == broken_manifest.version
    finally:
        index_runtime.set_active_manifest(fallback_manifest)


def test_health_ready_aligns_stale_engine_version(client, monkeypatch):
    import backend

    manifest = backend.index_runtime.read_active_manifest()
    manifest.content_index_path.write_bytes(pickle.dumps({"ok": 1}))
    manifest.title_index_path.write_bytes(pickle.dumps({"ok": 1}))

    replacement_engine = object()
    monkeypatch.setattr("backend._build_engine_from_manifest", lambda _manifest: replacement_engine)
    monkeypatch.setattr("backend.engine", object())
    monkeypatch.setattr("backend.engine_manifest_version", "stale-version")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.get_json()["ready"] is True
    assert backend.engine is replacement_engine
    assert backend.engine_manifest_version == manifest.version


def test_health_ready_returns_503_when_engine_reload_fails(client, monkeypatch):
    import backend

    manifest = backend.index_runtime.read_active_manifest()
    manifest.content_index_path.write_bytes(pickle.dumps({"ok": 1}))
    manifest.title_index_path.write_bytes(pickle.dumps({"ok": 1}))

    monkeypatch.setattr("backend.engine", object())
    monkeypatch.setattr("backend.engine_manifest_version", "stale-version")

    def fail_reload(_manifest):
        raise RuntimeError("reload failed")

    monkeypatch.setattr("backend._build_engine_from_manifest", fail_reload)

    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["ready"] is False
    assert "reload failed" in payload["last_error"]


def test_admin_endpoint_requires_internal_token(client):
    response = client.get("/admin/repository")
    assert response.status_code == 401

    authorized = client.get(
        "/admin/repository",
        headers={
            "X-Internal-Admin-Token": os.environ.get(
                "ADMIN_INTERNAL_TOKEN",
                "dev-admin-token",
            )
        },
    )
    assert authorized.status_code == 200


def test_upload_rejects_invalid_extension(client, admin_headers):
    response = client.post(
        "/admin/upload",
        data={"file": (BytesIO(b"binary"), "bad.exe")},
        headers=admin_headers,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_upload_rejects_doc_extension(client, admin_headers):
    response = client.post(
        "/admin/upload",
        data={"file": (BytesIO(b"binary"), "legacy.doc")},
        headers=admin_headers,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_reindex_while_running_returns_409(client, admin_headers, monkeypatch):
    from backend import reindex_service

    def fake_start(actor, build_fn, on_success=None, mode=None):
        return False, "reindex already running"

    monkeypatch.setattr(reindex_service, "start", fake_start)
    response = client.post("/admin/reindex", headers=admin_headers)
    assert response.status_code == 409


def test_reindex_status_includes_mode_and_stats(client, admin_headers, monkeypatch):
    class DummyState:
        status = "succeeded"
        mode = "incremental"
        stats = {"created": 2, "updated": 1, "reused": 3, "deleted": 0}
        actor = "admin@unud.ac.id"
        started_at = "2026-01-01T00:00:00Z"
        finished_at = "2026-01-01T00:00:10Z"
        last_error = None
        active_version = "v1"
        last_doc_count = 6

    monkeypatch.setattr("backend.reindex_service.status", lambda: DummyState)

    response = client.get("/admin/reindex/status", headers=admin_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["mode"] == "incremental"
    assert payload["stats"]["created"] == 2


def test_startup_fallback_sets_active_manifest_to_legacy_root(monkeypatch, tmp_path: Path):
    import backend
    from index_runtime import IndexRuntime

    content_path = tmp_path / "content_index.pkl"
    title_path = tmp_path / "title_index.pkl"
    runtime = IndexRuntime(base_dir=tmp_path / "runtime")
    runtime.bootstrap_if_missing()

    monkeypatch.setattr(backend, "CONTENT_INDEX_PATH", str(content_path))
    monkeypatch.setattr(backend, "TITLE_INDEX_PATH", str(title_path))
    monkeypatch.setattr(backend, "DOWNLOADS_DIR", str(tmp_path / "dataset"))
    monkeypatch.setattr(backend, "index_runtime", runtime)

    class FakeIndexer:
        def __init__(self, _corpus_path):
            self.content_index = type("ContentIndex", (), {"num_docs": 7})()

        def build_index(self, **_kwargs):
            return None

        def save_index(self, content_target, title_target):
            Path(content_target).write_bytes(b"content")
            Path(title_target).write_bytes(b"title")

    monkeypatch.setattr(backend, "DocumentCorpusIndexer", FakeIndexer)

    load_calls = {"count": 0}

    def fake_load_engine():
        load_calls["count"] += 1
        if load_calls["count"] == 1:
            return False

        manifest = runtime.read_active_manifest()
        return (
            manifest.content_index_path == content_path.resolve()
            and manifest.title_index_path == title_path.resolve()
        )

    monkeypatch.setattr(backend, "load_engine", fake_load_engine)

    assert backend.initialize_engine_for_startup() is True
    manifest = runtime.read_active_manifest()
    assert manifest.content_index_path == content_path.resolve()
    assert manifest.title_index_path == title_path.resolve()
    assert manifest.doc_count == 7


def test_delete_success(client, admin_headers, tmp_path, monkeypatch):
    from backend import Thesis, db

    monkeypatch.setattr("backend.DOWNLOADS_DIR", str(tmp_path))

    with app.app_context():
        thesis = Thesis(title="x", filename="x.pdf", is_indexed=True)
        db.session.add(thesis)
        db.session.commit()
        thesis_id = thesis.id

    (tmp_path / "x.pdf").write_bytes(b"sample")

    response = client.delete(f"/admin/delete/{thesis_id}", headers=admin_headers)
    assert response.status_code == 200


import pytest


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client
