import os
import pickle
from pathlib import Path

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

from index_runtime import ActiveManifest
import backend


def test_build_engine_rejects_non_index_objects(tmp_path: Path):
    content_path = tmp_path / "content.pkl"
    title_path = tmp_path / "title.pkl"
    content_path.write_bytes(pickle.dumps({"bad": 1}))
    title_path.write_bytes(pickle.dumps({"bad": 2}))

    manifest = ActiveManifest(
        version="invalid",
        doc_count=1,
        built_at="2026-01-01T00:00:00Z",
        content_index_path=content_path,
        title_index_path=title_path,
    )

    try:
        backend._build_engine_from_manifest(manifest)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "Invalid index object" in str(exc)
