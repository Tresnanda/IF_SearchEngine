import os

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

import backend


def test_select_reindex_builder_incremental(monkeypatch):
    monkeypatch.setattr(backend, "REINDEX_MODE", "incremental")
    build_fn, mode = backend._select_reindex_builder()
    assert build_fn == backend._build_indices_incremental
    assert mode == "incremental"


def test_select_reindex_builder_full(monkeypatch):
    monkeypatch.setattr(backend, "REINDEX_MODE", "full")
    build_fn, mode = backend._select_reindex_builder()
    assert build_fn == backend._build_indices
    assert mode == "full"
