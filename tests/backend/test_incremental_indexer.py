from pathlib import Path

from incremental_indexer import IncrementalIndexBuilder


def _touch(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_collect_records_reuses_cached_entries(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    _touch(dataset_dir / "a.pdf", "a")
    _touch(dataset_dir / "b.pdf", "b")
    cache_path = tmp_path / "document_cache.json"

    builder = IncrementalIndexBuilder(str(dataset_dir), str(cache_path))
    calls = []

    def fake_extract(file_path: Path, filename: str):
        calls.append(filename)
        return [f"token-{filename}"], [f"title-{filename}"]

    builder._extract_tokens_for_document = fake_extract  # type: ignore[attr-defined]
    records, stats, cache = builder.collect_records()

    assert len(records) == 2
    assert stats["created"] == 2
    assert stats["reused"] == 0
    assert sorted(calls) == ["a.pdf", "b.pdf"]

    builder.save_cache(cache)

    builder2 = IncrementalIndexBuilder(str(dataset_dir), str(cache_path))
    calls2 = []

    def fake_extract_second(file_path: Path, filename: str):
        calls2.append(filename)
        return [f"token-{filename}"], [f"title-{filename}"]

    builder2._extract_tokens_for_document = fake_extract_second  # type: ignore[attr-defined]
    records2, stats2, _ = builder2.collect_records()

    assert len(records2) == 2
    assert stats2["created"] == 0
    assert stats2["updated"] == 0
    assert stats2["reused"] == 2
    assert calls2 == []


def test_collect_records_tracks_updates_and_deletes(tmp_path: Path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    a_file = dataset_dir / "a.pdf"
    b_file = dataset_dir / "b.pdf"
    _touch(a_file, "old-a")
    _touch(b_file, "old-b")
    cache_path = tmp_path / "document_cache.json"

    builder = IncrementalIndexBuilder(str(dataset_dir), str(cache_path))
    builder._extract_tokens_for_document = lambda p, n: ([f"token-{n}"], [f"title-{n}"])  # type: ignore[attr-defined]
    _, _, cache = builder.collect_records()
    builder.save_cache(cache)

    _touch(a_file, "new-a-content")
    b_file.unlink()

    builder2 = IncrementalIndexBuilder(str(dataset_dir), str(cache_path))
    calls = []

    def fake_extract(file_path: Path, filename: str):
        calls.append(filename)
        return [f"updated-{filename}"], [f"title-{filename}"]

    builder2._extract_tokens_for_document = fake_extract  # type: ignore[attr-defined]
    records, stats, cache2 = builder2.collect_records()

    assert len(records) == 1
    assert records[0]["filename"] == "a.pdf"
    assert stats["updated"] == 1
    assert stats["deleted"] == 1
    assert calls == ["a.pdf"]
    assert "b.pdf" not in cache2


def test_collect_records_supports_gdrive_sources(tmp_path: Path):
    cache_path = tmp_path / "document_cache.json"
    sources = [
        {
            "filename": "gdrive_abc.pdf",
            "title": "GDrive Thesis",
            "source_type": "gdrive",
            "source_url": "https://drive.google.com/file/d/abc/view",
        }
    ]

    builder = IncrementalIndexBuilder(str(tmp_path), str(cache_path), sources=sources)
    builder._extract_tokens_for_source = lambda source: (["token"], ["title"])  # type: ignore[attr-defined]

    records, stats, cache = builder.collect_records()

    assert len(records) == 1
    assert records[0]["source_type"] == "gdrive"
    assert records[0]["source_url"] == "https://drive.google.com/file/d/abc/view"
    assert stats["created"] == 1
    assert cache["gdrive_abc.pdf"].source_type == "gdrive"
