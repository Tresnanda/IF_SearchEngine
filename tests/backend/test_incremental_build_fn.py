import os
from pathlib import Path

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

import backend


def test_incremental_build_fn_writes_indices_and_cache(monkeypatch, tmp_path: Path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "doc1.docx").write_text("abstrak sistem informasi", encoding="utf-8")

    cache_path = tmp_path / "doc_cache.json"

    monkeypatch.setattr(backend, "DOWNLOADS_DIR", str(dataset))
    monkeypatch.setattr(backend, "DOCUMENT_CACHE_PATH", str(cache_path))

    content_target = tmp_path / "content_index.pkl"
    title_target = tmp_path / "title_index.pkl"

    doc_count, stats = backend._build_indices_incremental(str(content_target), str(title_target))

    assert doc_count == 1
    assert stats["created"] == 1
    assert stats["updated"] == 0
    assert content_target.exists()
    assert title_target.exists()
    assert cache_path.exists()
