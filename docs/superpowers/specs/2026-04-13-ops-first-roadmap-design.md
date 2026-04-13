# Information Retrieval System: Ops-First Improvement Roadmap and Milestone 1 Design

## Overview
This specification defines an ops-first delivery roadmap for improving the Information Retrieval System across four priorities:

1. Ops reliability
2. Search relevance quality
3. Performance and scalability
4. Product features

The implementation strategy is milestone-based. We will complete a deep, production-safe Milestone 1 first, then move to later milestones with separate specs.

## Confirmed Decisions
- Delivery model: one master roadmap with a detailed Milestone 1 spec now; separate specs for subsequent milestones.
- Priority order: Ops reliability -> Relevance quality -> Performance -> Product features.
- Deployment target for Milestone 1: local Docker Compose first, with direct portability to VPS later.
- Reliability scope: full bundle in Milestone 1 (health/readiness, crash recovery, persistent volumes, reindex safety).
- Reindex serving policy: keep search online using the last successful index while candidate rebuild runs.
- Reindex trigger: admin-controlled API endpoint.
- Admin access model: NextAuth session login with admin role authorization.

## Master Roadmap

### Milestone 1 - Ops Reliability and Admin Control
Goal: make the system safe to operate continuously, support admin-managed corpus updates, and avoid search downtime during reindex.

### Milestone 2 - Search Relevance Quality
Goal: improve top-3 result quality for representative thesis queries using BM25-safe techniques (field weighting, query handling, typo and snippet quality improvements) without introducing embeddings/vector DB.

### Milestone 3 - Performance and Scalability
Goal: reduce p95 query latency and improve index build throughput as corpus grows.

### Milestone 4 - Product Feature Layer
Goal: deliver search filters, history, and explainability UX; apply `ui-ux-pro-max` for any UI/UX refinements while preserving established design language.

## Milestone 1 Detailed Design

### Architecture
Milestone 1 keeps two primary services in Compose (`backend`, `frontend`) and introduces a safe index lifecycle manager in backend runtime.

- Active index: currently serving all search traffic.
- Candidate index: temporary build target used during rebuild jobs.

Reindex lifecycle:
1. Admin triggers reindex from admin panel.
2. Backend builds candidate index in an isolated temporary location.
3. Backend validates candidate index completeness and loadability.
4. Backend performs an atomic activation switch to promote candidate to active.
5. Previous active index is retained as rollback snapshot.

Search endpoint behavior:
- `/api/search` always reads from active index only.
- Reindex job never mutates active index files in place.

Health visibility:
- Expose service and index runtime state through health endpoints, including active index metadata, reindex state, and last job outcome.

### Components and API Boundaries

#### Frontend and auth
- Keep NextAuth session login for admin.
- Replace hardcoded admin token pattern in UI with session-authorized calls.
- Restrict admin UI actions to authenticated users with `role=admin`.

#### Backend admin endpoints
- `GET /admin/repository`: list indexed corpus metadata and status.
- `POST /admin/upload`: upload `.pdf`/`.docx` files into managed dataset store.
- `DELETE /admin/delete/<id>`: remove a thesis file and metadata record.
- `POST /admin/reindex`: start asynchronous reindex job.
- `GET /admin/reindex/status`: return current and last job status.

#### Health/readiness endpoints
- `GET /health/live`: process liveness.
- `GET /health/ready`: readiness based on active index availability.

#### Compose hardening
- Add healthchecks for both services.
- Keep restart policy (`unless-stopped`) and persistent volumes for dataset/index artifacts.
- Gate frontend startup on backend health rather than bare container start.

### Data Flow and Safety Model

#### Upload flow
1. Admin uploads `.pdf` or `.docx` via panel.
2. Backend validates extension, size limits, and filename safety.
3. File is stored in dataset directory and marked pending reindex in repository metadata.

#### Reindex flow (no downtime)
1. Reindex job snapshots current dataset state.
2. Candidate index is built in temp directory.
3. Candidate manifest is written with version, timestamp, doc count, and integrity metadata.
4. Atomic activation switch promotes candidate index.
5. Search workers reload active index reference.
6. Previous active snapshot is retained for rollback.

Failure behavior:
- If candidate build or validation fails, active index remains unchanged.
- Failure cause is persisted in status/history and exposed to admin UI.

#### Delete flow
1. Admin confirms delete action.
2. Backend removes file and metadata record.
3. Corpus state becomes pending reindex until next successful rebuild.

#### Recovery flow
- On restart, backend loads latest valid active manifest.
- If active manifest is invalid, backend falls back to previous snapshot and reports degraded status.

#### Auditability
- Maintain reindex history records with actor, timestamps, duration, status, and error message when relevant.

### Error Handling, Security, and Operational Guards

#### Access control and authn/authz
- Require authenticated admin session for all admin operations.
- Return `401` for unauthenticated requests and `403` for non-admin users.
- Keep secrets in environment variables only; remove client-side hardcoded admin credentials/tokens.

#### Input and mutation safety
- Enforce file type and size constraints for uploads.
- Reject path traversal and unsafe filenames.
- Prevent concurrent reindex jobs; return `409` when a job is already running.

#### Runtime resilience
- Health endpoint can report degraded mode if process is alive but active index has issues.
- Structured logging events for upload/delete/reindex lifecycle.
- Admin UX disables conflicting actions while jobs run and surfaces actionable failure messages.

### Testing and Acceptance Criteria

#### Backend verification
- Search remains available during reindex.
- Failed candidate build does not replace active index.
- Concurrent reindex request is rejected.
- Upload/delete validations and state transitions are enforced.
- Liveness/readiness semantics are accurate.

#### Frontend verification
- Admin-only access and action authorization work as expected.
- Upload, delete, reindex trigger, and status polling are functional.
- No hardcoded admin token remains in client code paths.

#### Container verification
- `docker-compose up` reaches healthy state for both services.
- Active index persists and reloads correctly across restarts.
- Volume-backed artifacts survive container recreation.

#### Milestone 1 acceptance
- Admin can upload/delete theses and trigger reindex in panel.
- Search serves last successful index while reindex runs.
- Health/readiness endpoints reflect real service/index conditions.
- Service recovers from restart without requiring manual reindex.

## Non-Goals for Milestone 1
- No BM25 ranking logic changes.
- No relevance tuning experiments.
- No major UI redesign; only functional admin UX updates required for reliability workflows.
