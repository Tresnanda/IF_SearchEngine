from pathlib import Path
import pytest

from index_runtime import IndexRuntime


def test_bootstrap_creates_active_manifest(tmp_path: Path):
    runtime = IndexRuntime(base_dir=tmp_path)
    runtime.bootstrap_if_missing()

    manifest = runtime.read_active_manifest()
    assert manifest.version.startswith("bootstrap-")
    assert manifest.content_index_path.exists()
    assert manifest.title_index_path.exists()


def test_promote_candidate_is_atomic(tmp_path: Path):
    runtime = IndexRuntime(base_dir=tmp_path)
    runtime.bootstrap_if_missing()
    candidate = runtime.create_candidate_layout(version="v2")

    candidate.content_index_path.write_bytes(b"content-v2")
    candidate.title_index_path.write_bytes(b"title-v2")
    runtime.promote_candidate(candidate, doc_count=10)

    manifest = runtime.read_active_manifest()
    assert manifest.version == "v2"
    assert manifest.doc_count == 10
    assert manifest.content_index_path.read_bytes() == b"content-v2"


def test_fallback_to_previous_snapshot_when_active_invalid(tmp_path: Path):
    runtime = IndexRuntime(base_dir=tmp_path)
    runtime.bootstrap_if_missing()

    first = runtime.create_candidate_layout(version="v1")
    first.content_index_path.write_bytes(b"c1")
    first.title_index_path.write_bytes(b"t1")
    runtime.promote_candidate(first, doc_count=1)

    second = runtime.create_candidate_layout(version="v2")
    second.content_index_path.write_bytes(b"c2")
    second.title_index_path.write_bytes(b"t2")
    runtime.promote_candidate(second, doc_count=2)

    runtime.read_active_manifest().content_index_path.unlink()

    recovered = runtime.recover_active_manifest()
    assert recovered.version == "v1"
    assert recovered.content_index_path.exists()
    assert recovered.doc_count == 1


def test_recover_raises_when_no_fallback_snapshot(tmp_path: Path):
    runtime = IndexRuntime(base_dir=tmp_path)
    runtime.bootstrap_if_missing()

    runtime.read_active_manifest().content_index_path.unlink()

    with pytest.raises(RuntimeError, match="No valid fallback snapshot"):
        runtime.recover_active_manifest()


def test_recover_uses_latest_valid_snapshot_when_newest_is_broken(tmp_path: Path):
    runtime = IndexRuntime(base_dir=tmp_path)
    runtime.bootstrap_if_missing()

    first = runtime.create_candidate_layout(version="v1")
    first.content_index_path.write_bytes(b"c1")
    first.title_index_path.write_bytes(b"t1")
    runtime.promote_candidate(first, doc_count=11)

    second = runtime.create_candidate_layout(version="v2")
    second.content_index_path.write_bytes(b"c2")
    second.title_index_path.write_bytes(b"t2")
    runtime.promote_candidate(second, doc_count=22)

    third = runtime.create_candidate_layout(version="v3")
    third.content_index_path.write_bytes(b"c3")
    third.title_index_path.write_bytes(b"t3")
    runtime.promote_candidate(third, doc_count=33)

    (runtime.snapshots_dir / "v3" / "content_index.pkl").unlink()
    (runtime.snapshots_dir / "v2" / "title_index.pkl").unlink()

    recovered = runtime.recover_active_manifest()
    assert recovered.version == "v1"
    assert recovered.doc_count == 11


def test_bootstrap_seeds_from_legacy_root_indexes_when_available(tmp_path: Path):
    runtime = IndexRuntime(base_dir=tmp_path / "runtime")
    legacy_content = tmp_path / "content_index.pkl"
    legacy_title = tmp_path / "title_index.pkl"
    legacy_content.write_bytes(b"legacy-content")
    legacy_title.write_bytes(b"legacy-title")

    runtime.bootstrap_if_missing(
        seed_content_index_path=legacy_content,
        seed_title_index_path=legacy_title,
    )

    manifest = runtime.read_active_manifest()
    assert manifest.content_index_path.read_bytes() == b"legacy-content"
    assert manifest.title_index_path.read_bytes() == b"legacy-title"
