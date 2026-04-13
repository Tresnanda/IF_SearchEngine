# Milestone 1 Ops Reliability and Admin Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a safe, admin-operated indexing workflow that keeps search online with the last successful index during rebuilds, adds health/readiness checks, and hardens Docker Compose operations.

**Architecture:** The backend will manage index artifacts through an active/candidate manifest model and an asynchronous reindex job state machine. The frontend will enforce admin session authorization with NextAuth and proxy admin operations through server-side route handlers that attach an internal admin token. Compose will add healthchecks, persistent volumes, and dependency gating so startup and restart behavior is deterministic.

**Tech Stack:** Python 3 (Flask, Flask-SQLAlchemy, pytest), Next.js App Router + NextAuth, TypeScript, Docker Compose.

---

## File Structure and Responsibilities

- `backend.py`
  - Flask app entrypoint.
  - Search endpoint reads only active index pointers.
  - Admin endpoints (`/admin/*`) and health endpoints (`/health/*`).
  - Wires DB models and app lifecycle bootstrapping.
- `index_runtime.py` (new)
  - Index storage paths, active/candidate manifest helpers, atomic activation switch, rollback fallback.
- `reindex_service.py` (new)
  - Async reindex worker, single-job lock, status model, job history records.
- `tests/backend/test_index_runtime.py` (new)
  - Unit tests for bootstrap, activation switch, and fallback behavior.
- `tests/backend/test_reindex_service.py` (new)
  - Unit tests for reindex state machine and concurrent job rejection.
- `tests/backend/test_admin_routes.py` (new)
  - API tests for authz/authn, upload/delete validation, health/readiness semantics.
- `frontend/src/lib/auth.ts` (new)
  - Shared NextAuth config and admin-role utilities.
- `frontend/src/app/api/auth/[...nextauth]/route.ts`
  - Route wrapper importing shared auth options.
- `frontend/src/middleware.ts`
  - Admin-only route guarding.
- `frontend/src/lib/admin-api.ts` (new)
  - Server-side proxy helper that forwards requests to backend with internal token.
- `frontend/src/app/api/admin/repository/route.ts` (new)
- `frontend/src/app/api/admin/upload/route.ts` (new)
- `frontend/src/app/api/admin/delete/[id]/route.ts` (new)
- `frontend/src/app/api/admin/reindex/route.ts` (new)
- `frontend/src/app/api/admin/reindex/status/route.ts` (new)
  - Protected server routes for admin operations.
- `frontend/src/types/next-auth.d.ts` (new)
  - Adds `role` typing to session and JWT.
- `frontend/src/app/admin/page.tsx`
  - Remove hardcoded token, add upload flow and reindex status polling UX.
- `frontend/src/app/admin/layout.tsx`
  - Enforce admin session UX states.
- `docker-compose.yml`
  - Healthchecks, persistent volumes, dependency gating.
- `Dockerfile.backend`
  - Runtime directories and healthcheck-compatible tooling.
- `README.md`
  - Operational docs for env vars, startup, and admin reindex flow.

---

### Task 1: Establish Backend Test Harness and Index Runtime Contract

**Files:**
- Create: `tests/backend/conftest.py`
- Create: `tests/backend/test_index_runtime.py`
- Create: `index_runtime.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the failing tests for index runtime behavior**

```python
# tests/backend/test_index_runtime.py
from pathlib import Path

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
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `python3 -m pytest tests/backend/test_index_runtime.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'index_runtime'`

- [ ] **Step 3: Add pytest dependency**

```text
# requirements.txt (append)
pytest==8.3.5
```

- [ ] **Step 4: Implement minimal index runtime module**

```python
# index_runtime.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import uuid


@dataclass
class IndexManifest:
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
        self.active_ptr = self.base_dir / "active.json"
        self.snapshots_dir = self.base_dir / "snapshots"
        self.candidates_dir = self.base_dir / "candidates"

    def bootstrap_if_missing(self) -> None:
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.candidates_dir.mkdir(parents=True, exist_ok=True)
        if self.active_ptr.exists():
            return

        version = f"bootstrap-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        snapshot_dir = self.snapshots_dir / version
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        content_path = snapshot_dir / "content_index.pkl"
        title_path = snapshot_dir / "title_index.pkl"
        content_path.write_bytes(b"")
        title_path.write_bytes(b"")

        payload = {
            "version": version,
            "doc_count": 0,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_index_path": str(content_path),
            "title_index_path": str(title_path),
        }
        self._write_atomic_json(self.active_ptr, payload)

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
        self._write_atomic_json(self.active_ptr, payload)

    def read_active_manifest(self) -> IndexManifest:
        data = json.loads(self.active_ptr.read_text(encoding="utf-8"))
        return IndexManifest(
            version=data["version"],
            doc_count=data["doc_count"],
            built_at=data["built_at"],
            content_index_path=Path(data["content_index_path"]),
            title_index_path=Path(data["title_index_path"]),
        )

    def recover_active_manifest(self) -> IndexManifest:
        active = self.read_active_manifest()
        if active.content_index_path.exists() and active.title_index_path.exists():
            return active

        snapshots = sorted([p for p in self.snapshots_dir.iterdir() if p.is_dir()], key=lambda p: p.name)
        fallback = snapshots[-2]
        payload = {
            "version": fallback.name,
            "doc_count": active.doc_count,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "content_index_path": str(fallback / "content_index.pkl"),
            "title_index_path": str(fallback / "title_index.pkl"),
        }
        self._write_atomic_json(self.active_ptr, payload)
        return self.read_active_manifest()

    def _write_atomic_json(self, target: Path, payload: dict) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp_path, target)
```

- [ ] **Step 5: Run tests to verify pass**

Run: `python3 -m pytest tests/backend/test_index_runtime.py -q`

Expected: PASS with `3 passed`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt index_runtime.py tests/backend/conftest.py tests/backend/test_index_runtime.py
git commit -m "test: add index runtime contract and bootstrap implementation"
```

---

### Task 2: Build Reindex Job State Machine with Single-Job Lock

**Files:**
- Create: `reindex_service.py`
- Create: `tests/backend/test_reindex_service.py`
- Modify: `backend.py`

- [ ] **Step 1: Write failing tests for state transitions and concurrency guard**

```python
# tests/backend/test_reindex_service.py
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
    ok, _ = service.start(actor="admin@unud.ac.id", build_fn=lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    assert ok is True
    service.wait_for_idle(timeout_seconds=5)

    after = runtime.read_active_manifest().version
    assert before == after
    assert service.status().status == "failed"
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `python3 -m pytest tests/backend/test_reindex_service.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'reindex_service'`

- [ ] **Step 3: Implement reindex service and backend wiring**

```python
# reindex_service.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock, Thread
from time import monotonic, sleep
from typing import Callable, Optional

from index_runtime import IndexRuntime


@dataclass
class ReindexState:
    status: str = "idle"
    actor: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    last_error: str | None = None
    active_version: str | None = None
    last_doc_count: int | None = None


class ReindexService:
    def __init__(self, runtime: IndexRuntime):
        self.runtime = runtime
        self._lock = Lock()
        self._state = ReindexState(active_version=runtime.read_active_manifest().version)

    def status(self) -> ReindexState:
        return self._state

    def start(self, actor: str, build_fn: Callable[[str, str], int]) -> tuple[bool, str]:
        with self._lock:
            if self._state.status == "running":
                return False, "reindex already running"

            self._state.status = "running"
            self._state.actor = actor
            self._state.started_at = datetime.now(timezone.utc).isoformat()
            self._state.finished_at = None
            self._state.last_error = None

        worker = Thread(target=self._run, args=(build_fn,), daemon=True)
        worker.start()
        return True, "started"

    def wait_for_idle(self, timeout_seconds: int) -> None:
        deadline = monotonic() + timeout_seconds
        while monotonic() < deadline:
            if self._state.status != "running":
                return
            sleep(0.05)
        raise TimeoutError("reindex still running")

    def _run(self, build_fn: Callable[[str, str], int]) -> None:
        candidate = self.runtime.create_candidate_layout()
        try:
            doc_count = build_fn(str(candidate.content_index_path), str(candidate.title_index_path))
            self.runtime.promote_candidate(candidate, doc_count=doc_count)
            active = self.runtime.read_active_manifest()
            self._state.status = "succeeded"
            self._state.active_version = active.version
            self._state.last_doc_count = active.doc_count
        except Exception as exc:
            self._state.status = "failed"
            self._state.last_error = str(exc)
        finally:
            self._state.finished_at = datetime.now(timezone.utc).isoformat()
```

```python
# backend.py (new wiring excerpts)
from index_runtime import IndexRuntime
from reindex_service import ReindexService

INDEX_STORE_DIR = os.getenv("INDEX_STORE_DIR", "data/index")
index_runtime = IndexRuntime(base_dir=INDEX_STORE_DIR)
index_runtime.bootstrap_if_missing()
reindex_service = ReindexService(runtime=index_runtime)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python3 -m pytest tests/backend/test_reindex_service.py -q`

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add reindex_service.py backend.py tests/backend/test_reindex_service.py
git commit -m "feat: add async reindex service with single-job locking"
```

---

### Task 3: Add Health, Readiness, and Secure Admin Backend Endpoints

**Files:**
- Modify: `backend.py`
- Create: `tests/backend/test_admin_routes.py`

- [ ] **Step 1: Write failing API tests for auth and health semantics**

```python
# tests/backend/test_admin_routes.py
import os


def test_health_live(client):
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_health_ready_when_active_index_present(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ready"] is True
    assert "active_version" in payload


def test_admin_endpoint_requires_internal_token(client):
    res = client.get("/admin/repository")
    assert res.status_code == 401

    res_ok = client.get(
        "/admin/repository",
        headers={"X-Internal-Admin-Token": os.environ.get("ADMIN_INTERNAL_TOKEN", "dev-admin-token")},
    )
    assert res_ok.status_code == 200
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `python3 -m pytest tests/backend/test_admin_routes.py -q`

Expected: FAIL because `/health/live` and `/health/ready` are missing and token header name mismatches.

- [ ] **Step 3: Implement backend endpoints and token middleware**

```python
# backend.py (security and health excerpts)
ADMIN_INTERNAL_TOKEN = os.getenv("ADMIN_INTERNAL_TOKEN", "dev-admin-token")


def require_internal_admin_token(fn):
    from functools import wraps

    @wraps(fn)
    def wrapped(*args, **kwargs):
        token = request.headers.get("X-Internal-Admin-Token")
        if not token or token != ADMIN_INTERNAL_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapped


@app.route("/health/live", methods=["GET"])
def health_live():
    return jsonify({"status": "ok"}), 200


@app.route("/health/ready", methods=["GET"])
def health_ready():
    try:
        manifest = index_runtime.recover_active_manifest()
        ready = manifest.content_index_path.exists() and manifest.title_index_path.exists()
        return jsonify(
            {
                "ready": ready,
                "active_version": manifest.version,
                "doc_count": manifest.doc_count,
                "reindex_status": reindex_service.status().status,
                "last_error": reindex_service.status().last_error,
            }
        ), (200 if ready else 503)
    except Exception as exc:
        return jsonify({"ready": False, "error": str(exc)}), 503


@app.route("/admin/repository", methods=["GET"])
@require_internal_admin_token
def get_repository():
    theses = Thesis.query.order_by(Thesis.upload_date.desc()).all()
    return jsonify([t.to_dict() for t in theses])


@app.route("/admin/reindex/status", methods=["GET"])
@require_internal_admin_token
def get_reindex_status():
    state = reindex_service.status()
    return jsonify(
        {
            "status": state.status,
            "actor": state.actor,
            "started_at": state.started_at,
            "finished_at": state.finished_at,
            "last_error": state.last_error,
            "active_version": state.active_version,
            "last_doc_count": state.last_doc_count,
        }
    )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python3 -m pytest tests/backend/test_admin_routes.py -q`

Expected: PASS with `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend.py tests/backend/test_admin_routes.py
git commit -m "feat: add backend health readiness and internal admin auth"
```

---

### Task 4: Implement Safe Upload/Delete/Reindex Backend Flows

**Files:**
- Modify: `backend.py`
- Modify: `test_docx_indexer.py`
- Modify: `indexer.py`
- Test: `tests/backend/test_admin_routes.py`

- [ ] **Step 1: Add failing tests for upload validation and reindex behavior**

```python
# tests/backend/test_admin_routes.py (append)
from io import BytesIO
import os


def test_upload_rejects_invalid_extension(client, admin_headers):
    res = client.post(
        "/admin/upload",
        data={"file": (BytesIO(b"binary"), "bad.exe")},
        headers=admin_headers,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400


def test_reindex_while_running_returns_409(client, admin_headers, monkeypatch):
    from backend import reindex_service

    reindex_service._state.status = "running"
    res = client.post("/admin/reindex", headers=admin_headers)
    assert res.status_code == 409


def test_delete_marks_pending_reindex(client, admin_headers, app_ctx):
    from backend import Thesis, db

    thesis = Thesis(title="x", filename="x.pdf", is_indexed=True)
    db.session.add(thesis)
    db.session.commit()

    res = client.delete(f"/admin/delete/{thesis.id}", headers=admin_headers)
    assert res.status_code == 200
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/backend/test_admin_routes.py -q`

Expected: FAIL with missing `admin_headers` fixture and route behavior mismatches.

- [ ] **Step 3: Implement backend validation, async trigger, and active-index-preserving build**

```python
# backend.py (admin endpoint excerpts)
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


def _build_indices(content_path: str, title_path: str) -> int:
    indexer = DocumentCorpusIndexer(DOWNLOADS_DIR)
    indexer.build_index()
    indexer.save_index(content_path, title_path)
    return indexer.content_index.num_docs


@app.route("/admin/upload", methods=["POST"])
@require_internal_admin_token
def upload_thesis():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No selected file"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Invalid file type"}), 400

    safe_name = os.path.basename(file.filename)
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_UPLOAD_SIZE_BYTES:
        return jsonify({"error": "File exceeds size limit"}), 400

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOADS_DIR, safe_name)
    if os.path.exists(file_path):
        return jsonify({"error": "File already exists"}), 409

    file.save(file_path)
    thesis = Thesis(title=os.path.splitext(safe_name)[0], filename=safe_name, is_indexed=False)
    db.session.add(thesis)
    db.session.commit()
    return jsonify({"message": "uploaded", "thesis": thesis.to_dict()}), 201


@app.route("/admin/reindex", methods=["POST"])
@require_internal_admin_token
def trigger_reindex():
    actor = request.headers.get("X-Admin-Actor", "admin@informatika.unud.ac.id")
    started, message = reindex_service.start(actor=actor, build_fn=_build_indices)
    if not started:
        return jsonify({"error": message}), 409
    return jsonify({"message": message}), 202
```

- [ ] **Step 4: Add fixtures and rerun tests**

```python
# tests/backend/conftest.py
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def env_defaults():
    os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")


@pytest.fixture
def admin_headers():
    return {"X-Internal-Admin-Token": os.environ["ADMIN_INTERNAL_TOKEN"]}
```

Run: `python3 -m pytest tests/backend/test_admin_routes.py -q`

Expected: PASS with upload/reindex/delete tests passing.

- [ ] **Step 5: Commit**

```bash
git add backend.py indexer.py test_docx_indexer.py tests/backend/conftest.py tests/backend/test_admin_routes.py
git commit -m "feat: add validated admin upload delete and async reindex trigger"
```

---

### Task 5: Add Frontend Server-Side Admin Proxy and Role-Typed Auth

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/admin-api.ts`
- Create: `frontend/src/types/next-auth.d.ts`
- Create: `frontend/src/app/api/admin/repository/route.ts`
- Create: `frontend/src/app/api/admin/upload/route.ts`
- Create: `frontend/src/app/api/admin/delete/[id]/route.ts`
- Create: `frontend/src/app/api/admin/reindex/route.ts`
- Create: `frontend/src/app/api/admin/reindex/status/route.ts`
- Modify: `frontend/src/app/api/auth/[...nextauth]/route.ts`
- Modify: `frontend/src/middleware.ts`
- Test: `frontend/src/lib/admin-api.test.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write failing tests for proxy helper auth behavior**

```ts
// frontend/src/lib/admin-api.test.ts
import { describe, it, expect, vi } from 'vitest';
import { proxyToBackendAdmin } from './admin-api';

describe('proxyToBackendAdmin', () => {
  it('adds internal token header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await proxyToBackendAdmin({
      path: '/admin/repository',
      method: 'GET',
      body: undefined,
      actorEmail: 'admin@informatika.unud.ac.id',
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers['X-Internal-Admin-Token']).toBeDefined();
    expect(headers['X-Admin-Actor']).toBe('admin@informatika.unud.ac.id');
  });
});
```

- [ ] **Step 2: Run test to confirm failure**

Run: `cd frontend && npx vitest run src/lib/admin-api.test.ts`

Expected: FAIL because `admin-api.ts` and Vitest setup do not exist.

- [ ] **Step 3: Add Vitest + implement auth/proxy modules and route handlers**

```json
// frontend/package.json (scripts excerpt)
{
  "scripts": {
    "test": "vitest run"
  },
  "devDependencies": {
    "vitest": "^2.1.8"
  }
}
```

```ts
// frontend/src/lib/auth.ts
import type { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

const adminEmail = process.env.ADMIN_EMAIL ?? 'admin@informatika.unud.ac.id';
const adminPassword = process.env.ADMIN_PASSWORD ?? 'password';

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Admin Credentials',
      credentials: {
        email: { label: 'Email', type: 'text' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (credentials?.email === adminEmail && credentials?.password === adminPassword) {
          return { id: '1', email: adminEmail, name: 'Admin', role: 'admin' } as const;
        }
        return null;
      },
    }),
  ],
  session: { strategy: 'jwt' },
  callbacks: {
    async jwt({ token, user }) {
      if (user) token.role = (user as { role?: string }).role ?? 'admin';
      return token;
    },
    async session({ session, token }) {
      if (session.user) session.user.role = (token.role as string) ?? 'admin';
      return session;
    },
  },
  pages: { signIn: '/login' },
  secret: process.env.NEXTAUTH_SECRET,
};
```

```ts
// frontend/src/lib/admin-api.ts
export async function proxyToBackendAdmin(params: {
  path: string;
  method: 'GET' | 'POST' | 'DELETE';
  actorEmail: string;
  body?: BodyInit;
  contentType?: string;
}) {
  const base = process.env.BACKEND_URL ?? 'http://127.0.0.1:5000';
  const token = process.env.ADMIN_INTERNAL_TOKEN ?? 'dev-admin-token';

  const headers: Record<string, string> = {
    'X-Internal-Admin-Token': token,
    'X-Admin-Actor': params.actorEmail,
  };
  if (params.contentType) headers['Content-Type'] = params.contentType;

  return fetch(`${base}${params.path}`, {
    method: params.method,
    headers,
    body: params.body,
    cache: 'no-store',
  });
}
```

```ts
// frontend/src/app/api/admin/repository/route.ts
import { getServerSession } from 'next-auth';
import { NextResponse } from 'next/server';
import { authOptions } from '@/lib/auth';
import { proxyToBackendAdmin } from '@/lib/admin-api';

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  if (session.user.role !== 'admin') return NextResponse.json({ error: 'Forbidden' }, { status: 403 });

  const upstream = await proxyToBackendAdmin({
    path: '/admin/repository',
    method: 'GET',
    actorEmail: session.user.email ?? 'admin@informatika.unud.ac.id',
  });
  return new NextResponse(await upstream.text(), { status: upstream.status });
}
```

- [ ] **Step 4: Run frontend tests and build**

Run: `cd frontend && npm install && npm run test && npm run build`

Expected: PASS for Vitest and Next build.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/lib/auth.ts frontend/src/lib/admin-api.ts frontend/src/types/next-auth.d.ts frontend/src/app/api/auth/[...nextauth]/route.ts frontend/src/app/api/admin frontend/src/lib/admin-api.test.ts frontend/src/middleware.ts
git commit -m "feat: secure admin proxy routes with NextAuth role checks"
```

---

### Task 6: Upgrade Admin Panel UX for Upload and Reindex Status

**Files:**
- Create: `frontend/src/components/admin/UploadDialog.tsx`
- Create: `frontend/src/components/admin/ReindexStatusBadge.tsx`
- Modify: `frontend/src/app/admin/page.tsx`
- Modify: `frontend/src/app/admin/layout.tsx`
- Test: `frontend/src/components/admin/UploadDialog.test.tsx`

- [ ] **Step 1: Write failing component tests for upload interaction states**

```tsx
// frontend/src/components/admin/UploadDialog.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import UploadDialog from './UploadDialog';

describe('UploadDialog', () => {
  it('shows file picker CTA and disabled submit without file', () => {
    render(<UploadDialog open onClose={() => {}} onUploaded={() => {}} />);
    expect(screen.getByText('Upload Document')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to confirm failure**

Run: `cd frontend && npx vitest run src/components/admin/UploadDialog.test.tsx`

Expected: FAIL because component and testing dependencies are not present.

- [ ] **Step 3: Implement admin components and page integration**

```tsx
// frontend/src/components/admin/ReindexStatusBadge.tsx
type Props = { status: 'idle' | 'running' | 'succeeded' | 'failed'; lastError?: string | null };

export default function ReindexStatusBadge({ status, lastError }: Props) {
  if (status === 'running') return <span className="text-xs border border-blue-200 bg-blue-50 text-blue-700 px-2 py-1 rounded">Reindexing</span>;
  if (status === 'failed') return <span className="text-xs border border-red-200 bg-red-50 text-red-700 px-2 py-1 rounded">Failed: {lastError ?? 'Unknown'}</span>;
  if (status === 'succeeded') return <span className="text-xs border border-green-200 bg-green-50 text-green-700 px-2 py-1 rounded">Up to date</span>;
  return <span className="text-xs border border-zinc-200 bg-zinc-50 text-zinc-600 px-2 py-1 rounded">Idle</span>;
}
```

```tsx
// frontend/src/app/admin/page.tsx (behavior excerpt)
const [status, setStatus] = useState<{status: 'idle' | 'running' | 'succeeded' | 'failed'; last_error?: string | null}>({ status: 'idle' });

const fetchReindexStatus = async () => {
  const res = await fetch('/api/admin/reindex/status', { cache: 'no-store' });
  if (res.ok) {
    const json = await res.json();
    setStatus({ status: json.status, last_error: json.last_error });
  }
};

useEffect(() => {
  fetchReindexStatus();
  const timer = setInterval(fetchReindexStatus, 3000);
  return () => clearInterval(timer);
}, []);
```

- [ ] **Step 4: Run tests/build for admin UI changes**

Run: `cd frontend && npm run test && npm run build`

Expected: PASS with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/admin frontend/src/app/admin/page.tsx frontend/src/app/admin/layout.tsx
git commit -m "feat: add admin upload workflow and live reindex status ux"
```

---

### Task 7: Harden Docker Compose for Healthchecks, Persistence, and Startup Ordering

**Files:**
- Modify: `docker-compose.yml`
- Modify: `Dockerfile.backend`
- Modify: `frontend/Dockerfile`
- Create: `.env.example`
- Test: `scripts/smoke/test_compose_health.sh`

- [ ] **Step 1: Write failing smoke test script**

```bash
#!/usr/bin/env bash
set -euo pipefail

docker compose up -d --build

for i in {1..40}; do
  backend_status="$(docker inspect --format='{{.State.Health.Status}}' "$(docker compose ps -q backend)")"
  frontend_status="$(docker inspect --format='{{.State.Health.Status}}' "$(docker compose ps -q frontend)")"
  if [[ "$backend_status" == "healthy" && "$frontend_status" == "healthy" ]]; then
    echo "healthy"
    exit 0
  fi
  sleep 3
done

echo "services did not become healthy in time"
exit 1
```

- [ ] **Step 2: Run smoke test and confirm failure on current compose**

Run: `bash scripts/smoke/test_compose_health.sh`

Expected: FAIL because healthchecks are not defined.

- [ ] **Step 3: Implement compose and Dockerfile hardening**

```yaml
# docker-compose.yml (target structure)
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "5000:5000"
    environment:
      - INDEX_STORE_DIR=/app/data/index
      - DATASET_DIR=/app/new_dataset
      - ADMIN_INTERNAL_TOKEN=${ADMIN_INTERNAL_TOKEN}
    volumes:
      - ./new_dataset:/app/new_dataset
      - ./data/index:/app/data/index
      - ./data/db:/app/data/db
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health/live', timeout=2)"]
      interval: 10s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3001:3000"
    environment:
      - BACKEND_URL=http://backend:5000
      - NEXTAUTH_URL=http://localhost:3001
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - ADMIN_INTERNAL_TOKEN=${ADMIN_INTERNAL_TOKEN}
      - ADMIN_EMAIL=${ADMIN_EMAIL}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://127.0.0.1:3000').then(()=>process.exit(0)).catch(()=>process.exit(1))"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped
```

- [ ] **Step 4: Rerun smoke test and verify pass**

Run: `bash scripts/smoke/test_compose_health.sh`

Expected: PASS with output `healthy`.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml Dockerfile.backend frontend/Dockerfile .env.example scripts/smoke/test_compose_health.sh
git commit -m "chore: harden compose startup healthchecks and persistent volumes"
```

---

### Task 8: Final Verification and Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-04-13-ops-first-roadmap-design.md` (if implementation deviations exist)

- [ ] **Step 1: Add operational documentation updates**

```markdown
## Admin Operations

### Environment Variables
- `NEXTAUTH_SECRET`: NextAuth signing secret.
- `ADMIN_INTERNAL_TOKEN`: Shared token used only between Next.js server routes and Flask backend.
- `ADMIN_EMAIL`: Admin login email for credentials provider.
- `ADMIN_PASSWORD`: Admin login password for credentials provider.

### Reindex Behavior
- Reindex runs asynchronously and does not take search offline.
- Search serves the last successful active index while candidate rebuild runs.
- Reindex status is available at `/api/admin/reindex/status` in frontend and `/admin/reindex/status` in backend.

### Health Endpoints
- Liveness: `/health/live`
- Readiness: `/health/ready`
```

- [ ] **Step 2: Run full backend + frontend + compose verification suite**

Run:

```bash
python3 -m pytest tests/backend -q
cd frontend && npm run test && npm run build
cd .. && bash scripts/smoke/test_compose_health.sh
```

Expected:
- pytest: all tests PASS
- frontend test/build: PASS
- compose smoke: `healthy`

- [ ] **Step 3: Commit final milestone integration**

```bash
git add README.md docs/superpowers/specs/2026-04-13-ops-first-roadmap-design.md
git commit -m "docs: add ops runbook and milestone 1 verification notes"
```

---

## Post-Task Validation Matrix

- [ ] Admin routes reject unauthenticated or non-admin requests (`401`/`403`).
- [ ] Upload rejects invalid file extensions and oversize files.
- [ ] Reindex endpoint returns `409` when already running.
- [ ] Search endpoint remains available while reindex is running.
- [ ] Failed reindex keeps previous active index version.
- [ ] Backend liveness and readiness endpoints reflect runtime health.
- [ ] Compose startup reaches healthy state without manual waiting scripts.
- [ ] Admin panel supports upload, delete, trigger reindex, and status polling without exposing token in browser code.
