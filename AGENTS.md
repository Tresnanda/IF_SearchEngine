# AGENTS.md

Welcome, AI Engineer!

This document outlines the architecture, conventions, and preferred workflows for this repository. If you are reading this, you are likely about to implement a new feature or fix a bug in the Information Retrieval System.

## Architecture
This project is an **Information Retrieval System** built for a university thesis dataset. It uses a **traditional IR stack (Okapi BM25)** instead of AI embeddings or vector databases, to keep costs zero and latency low.

### Backend (Python/Flask)
- **`backend.py`**: The Flask API server. Exposes `/search`, `/admin/*`, and `/health/*`. Handles query processing, snippet generation, admin operations, and readiness reporting.
- **`vsm.py`**: The core Vector Space Model logic. We recently migrated this from TF-IDF to **BM25**. The `b` and `k1` parameters are tuned differently for titles vs. content.
- **`indexer.py`**: Parses the corpus of documents. Handles both `.pdf` (using `PyPDF2`) and `.docx` (using `python-docx`) files.
- **`test_docx_indexer.py`**: The build script used to generate the `.pkl` indices. You must run this script after adding new documents.
- **`index_runtime.py`**: Active/candidate index manifest manager for safe snapshot switching and fallback.
- **`reindex_service.py`**: Async reindex job state machine with single-job lock and status reporting.
- **`scraper.py`**: A custom script built to bypass Google Drive rate limits using a hybrid `curl`/`gdown` approach. It reads a `.csv` file and downloads thesis files to `new_dataset/`.

### Frontend (Next.js/React)
- **Framework**: Next.js App Router (`frontend/src/app`).
- **Styling**: Tailwind CSS. We use the **Swiss Modernism** aesthetic (monochrome zinc palette, `Inter` font, extremely minimal borders, no glassmorphism).
- **Core Components**:
  - `page.tsx`: The main layout, featuring a centered "Command Palette" container.
  - `SearchResults.tsx`: Maps over BM25 results, includes client-side filters and explainability chips.
  - `SearchFeedback.tsx`: A small thumbs up/down component at the bottom of the results.
  - `app/api/admin/*`: Session-protected server routes proxying admin actions to backend.

## Conventions
- **No Vector DBs / Embeddings**: If a user asks to improve search relevance, stick to traditional IR methods (query expansion, better stemming, adjusting BM25 parameters, or field boosting).
- **Styling Consistency**: If you add new UI elements, strictly adhere to the zinc/grayscale palette defined in `globals.css`. Avoid bright colors except for specific active states (e.g., `text-blue-600`).
- **Data Isolation**: Never commit actual `.pdf` or `.docx` files. Ensure they stay in `.gitignore` under `new_dataset/` or `dataset/`.
- **Absolute Paths**: When writing shell commands for agents to run, always verify the current working directory. The frontend is in the `frontend/` subdirectory.
- **Admin Security**: Never hardcode admin tokens/credentials in client-side code. Use NextAuth session checks and env-based internal token forwarding from server routes.
- **Ops Safety**: Preserve active-index behavior during reindex. Do not introduce any in-place overwrite strategy for serving index files.

## VPS Deployment Notes
- Use Docker Compose as the default deployment method.
- Required env vars in production-like environments: `ADMIN_INTERNAL_TOKEN`, `NEXTAUTH_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `BACKEND_URL`, `NEXTAUTH_URL`.
- Required persistent directories: `new_dataset/`, `data/index/`, `data/db/`.
- Health endpoints for probes: `/health/live`, `/health/ready`.
- Reindex policy: system must keep serving last successful index while candidate build runs.

## Agent Workflow
When tasked with a feature:
1. **Understand**: Use `grep` to find where the feature touches the stack (e.g., `grep -rn "BM25" .`).
2. **Plan**: Formulate a short plan.
3. **Execute**: Modify the necessary Python or TypeScript files.
4. **Verify**:
   - Backend tests: `./venv/bin/python -m pytest tests/backend -q`
   - Frontend tests/build: `npm run test && npm run build` in `frontend/`
   - Compose smoke (when Docker available): `bash scripts/smoke/test_compose_health.sh`
