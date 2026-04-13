from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import uuid


@dataclass
class ActiveManifest:
    version: str
    doc_count: int
    built_at: str
    content_index_path: Path
    title_index_path: Path


@dataclass
class CandidateLayout:
    version: str
    root: Path
    content_index_path: Path
    title_index_path: Path


class IndexRuntime:
    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)
        self.active_pointer_path = self.base_dir / "active.json"
        self.snapshots_dir = self.base_dir / "snapshots"
        self.candidates_dir = self.base_dir / "candidates"

    def bootstrap_if_missing(
        self,
        seed_content_index_path: Path | str | None = None,
        seed_title_index_path: Path | str | None = None,
    ) -> None:
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        if self.active_pointer_path.exists():
            return

        seeded_content = Path(seed_content_index_path) if seed_content_index_path else None
        seeded_title = Path(seed_title_index_path) if seed_title_index_path else None
        can_seed = (
            seeded_content is not None
            and seeded_title is not None
            and seeded_content.exists()
            and seeded_title.exists()
        )

        version = f"bootstrap-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        snapshot_dir = self.snapshots_dir / version
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        content_index_path = snapshot_dir / "content_index.pkl"
        title_index_path = snapshot_dir / "title_index.pkl"
        if can_seed:
            shutil.copy2(str(seeded_content), str(content_index_path))
            shutil.copy2(str(seeded_title), str(title_index_path))
        else:
            content_index_path.write_bytes(b"")
            title_index_path.write_bytes(b"")

        payload = {
            "version": version,
            "doc_count": 0,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_index_path": str(content_index_path),
            "title_index_path": str(title_index_path),
        }
        self._write_snapshot_manifest(snapshot_dir=snapshot_dir, payload=payload)
        self._write_atomic_json(self.active_pointer_path, payload)

    def set_active_manifest(self, manifest: ActiveManifest) -> None:
        payload = {
            "version": manifest.version,
            "doc_count": manifest.doc_count,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_index_path": str(manifest.content_index_path),
            "title_index_path": str(manifest.title_index_path),
        }
        self._write_atomic_json(self.active_pointer_path, payload)

    def create_candidate_layout(self, version: str | None = None) -> CandidateLayout:
        resolved_version = version or f"cand-{uuid.uuid4().hex[:10]}"
        root = self.candidates_dir / resolved_version
        root.mkdir(parents=True, exist_ok=True)

        return CandidateLayout(
            version=resolved_version,
            root=root,
            content_index_path=root / "content_index.pkl",
            title_index_path=root / "title_index.pkl",
        )

    def promote_candidate(self, candidate: CandidateLayout, doc_count: int) -> None:
        snapshot_dir = self.snapshots_dir / candidate.version
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
        shutil.move(str(candidate.root), str(snapshot_dir))

        payload = {
            "version": candidate.version,
            "doc_count": doc_count,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_index_path": str(snapshot_dir / "content_index.pkl"),
            "title_index_path": str(snapshot_dir / "title_index.pkl"),
        }
        self._write_snapshot_manifest(snapshot_dir=snapshot_dir, payload=payload)
        self._write_atomic_json(self.active_pointer_path, payload)

    def read_active_manifest(self) -> ActiveManifest:
        data = json.loads(self.active_pointer_path.read_text(encoding="utf-8"))
        return ActiveManifest(
            version=data["version"],
            doc_count=data["doc_count"],
            built_at=data["built_at"],
            content_index_path=Path(data["content_index_path"]),
            title_index_path=Path(data["title_index_path"]),
        )

    def recover_active_manifest(self) -> ActiveManifest:
        active = self.read_active_manifest()
        if active.content_index_path.exists() and active.title_index_path.exists():
            return active

        fallback = self._find_latest_valid_fallback(exclude_version=active.version)
        if fallback is None:
            raise RuntimeError("No valid fallback snapshot available for recovery")

        payload = {
            "version": fallback.version,
            "doc_count": fallback.doc_count,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_index_path": str(fallback.content_index_path),
            "title_index_path": str(fallback.title_index_path),
        }
        self._write_atomic_json(self.active_pointer_path, payload)
        return self.read_active_manifest()

    def _find_latest_valid_fallback(self, exclude_version: str) -> ActiveManifest | None:
        candidates: list[ActiveManifest] = []
        for snapshot_dir in self.snapshots_dir.iterdir():
            if not snapshot_dir.is_dir():
                continue

            manifest = self._read_snapshot_manifest(snapshot_dir)
            if manifest is None or manifest.version == exclude_version:
                continue
            if not manifest.content_index_path.exists() or not manifest.title_index_path.exists():
                continue

            candidates.append(manifest)

        if not candidates:
            return None

        return max(candidates, key=lambda candidate: candidate.built_at)

    def _read_snapshot_manifest(self, snapshot_dir: Path) -> ActiveManifest | None:
        manifest_path = snapshot_dir / "manifest.json"
        if not manifest_path.exists():
            return None

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return ActiveManifest(
            version=data["version"],
            doc_count=data["doc_count"],
            built_at=data["built_at"],
            content_index_path=Path(data["content_index_path"]),
            title_index_path=Path(data["title_index_path"]),
        )

    def _write_snapshot_manifest(self, snapshot_dir: Path, payload: dict) -> None:
        self._write_atomic_json(snapshot_dir / "manifest.json", payload)

    def _write_atomic_json(self, target: Path, payload: dict) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp_path, target)
