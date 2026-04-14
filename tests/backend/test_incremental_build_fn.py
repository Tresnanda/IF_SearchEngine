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

    from backend import Thesis, db

    with backend.app.app_context():
        Thesis.query.delete()
        db.session.commit()
        db.session.add(Thesis(title="Doc 1", filename="doc1.docx", source_type="local", is_indexed=False))
        db.session.commit()

    content_target = tmp_path / "content_index.pkl"
    title_target = tmp_path / "title_index.pkl"

    doc_count, stats = backend._build_indices_incremental(str(content_target), str(title_target))

    assert doc_count == 1
    assert stats["created"] == 1
    assert stats["updated"] == 0
    assert content_target.exists()
    assert title_target.exists()
    assert cache_path.exists()


def test_incremental_build_fn_includes_gdrive_sources(monkeypatch, tmp_path: Path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "local.docx").write_text("abstrak sistem informasi", encoding="utf-8")

    cache_path = tmp_path / "doc_cache.json"

    monkeypatch.setattr(backend, "DOWNLOADS_DIR", str(dataset))
    monkeypatch.setattr(backend, "DOCUMENT_CACHE_PATH", str(cache_path))

    from backend import Thesis, db

    with backend.app.app_context():
        Thesis.query.delete()
        db.session.commit()
        db.session.add(Thesis(title="Local", filename="local.docx", source_type="local", is_indexed=False))
        db.session.add(
            Thesis(
                title="Drive",
                filename="gdrive_abc.pdf",
                source_type="gdrive",
                source_url="https://drive.google.com/file/d/abc/view",
                source_file_id="abc",
                is_indexed=False,
            )
        )
        db.session.commit()

    from incremental_indexer import IncrementalIndexBuilder

    original_collect_records = IncrementalIndexBuilder.collect_records

    def fake_collect_records(self):
        assert any(source["source_type"] == "gdrive" for source in self.sources)
        return (
            [
                {
                    "filename": "local.docx",
                    "title": "Local",
                    "year": "2024",
                    "path": str(dataset / "local.docx"),
                    "source_type": "local",
                    "source_url": None,
                    "content_tokens": ["local"],
                    "title_tokens": ["local"],
                },
                {
                    "filename": "gdrive_abc.pdf",
                    "title": "Drive",
                    "year": "2023",
                    "path": "",
                    "source_type": "gdrive",
                    "source_url": "https://drive.google.com/file/d/abc/view",
                    "content_tokens": ["drive"],
                    "title_tokens": ["drive"],
                },
            ],
            {"created": 2, "updated": 0, "reused": 0, "deleted": 0},
            {},
        )

    monkeypatch.setattr(IncrementalIndexBuilder, "collect_records", fake_collect_records)

    content_target = tmp_path / "content_index.pkl"
    title_target = tmp_path / "title_index.pkl"

    try:
        doc_count, stats = backend._build_indices_incremental(str(content_target), str(title_target))
    finally:
        monkeypatch.setattr(IncrementalIndexBuilder, "collect_records", original_collect_records)

    assert doc_count == 2
    assert stats["created"] == 2


def test_incremental_build_fn_returns_zero_when_no_sources(monkeypatch, tmp_path: Path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    cache_path = tmp_path / "doc_cache.json"

    monkeypatch.setattr(backend, "DOWNLOADS_DIR", str(dataset))
    monkeypatch.setattr(backend, "DOCUMENT_CACHE_PATH", str(cache_path))

    from backend import Thesis, db

    with backend.app.app_context():
        Thesis.query.delete()
        db.session.commit()

    content_target = tmp_path / "content_index.pkl"
    title_target = tmp_path / "title_index.pkl"

    doc_count, stats = backend._build_indices_incremental(str(content_target), str(title_target))

    assert doc_count == 0
    assert stats == {"created": 0, "updated": 0, "reused": 0, "deleted": 0}
    assert not content_target.exists()
    assert not title_target.exists()
