# AGENTS.md

Welcome, AI Engineer!

This document outlines the architecture, conventions, and preferred workflows for this repository. If you are reading this, you are likely about to implement a new feature or fix a bug in the Information Retrieval System.

## Architecture
This project is an **Information Retrieval System** built for a university thesis dataset. It uses a **traditional IR stack (Okapi BM25)** instead of AI embeddings or vector databases, to keep costs zero and latency low.

### Backend (Python/Flask)
- **`backend.py`**: The Flask API server. Exposes the `/api/search` endpoint. Handles receiving the query from the Next.js frontend, generating snippets, and returning JSON.
- **`vsm.py`**: The core Vector Space Model logic. We recently migrated this from TF-IDF to **BM25**. The `b` and `k1` parameters are tuned differently for titles vs. content.
- **`indexer.py`**: Parses the corpus of documents. Handles both `.pdf` (using `PyPDF2`) and `.docx` (using `python-docx`) files.
- **`test_docx_indexer.py`**: The build script used to generate the `.pkl` indices. You must run this script after adding new documents.
- **`scraper.py`**: A custom script built to bypass Google Drive rate limits using a hybrid `curl`/`gdown` approach. It reads a `.csv` file and downloads thesis files to `new_dataset/`.

### Frontend (Next.js/React)
- **Framework**: Next.js App Router (`frontend/src/app`).
- **Styling**: Tailwind CSS. We use the **Swiss Modernism** aesthetic (monochrome zinc palette, `Inter` font, extremely minimal borders, no glassmorphism).
- **Core Components**:
  - `page.tsx`: The main layout, featuring a centered "Command Palette" container.
  - `SearchResults.tsx`: Maps over the BM25 results, displaying the title, score pill, and the contextual text snippet in a clean grid.
  - `SearchFeedback.tsx`: A small thumbs up/down component at the bottom of the results.

## Conventions
- **No Vector DBs / Embeddings**: If a user asks to improve search relevance, stick to traditional IR methods (query expansion, better stemming, adjusting BM25 parameters, or field boosting).
- **Styling Consistency**: If you add new UI elements, strictly adhere to the zinc/grayscale palette defined in `globals.css`. Avoid bright colors except for specific active states (e.g., `text-blue-600`).
- **Data Isolation**: Never commit actual `.pdf` or `.docx` files. Ensure they stay in `.gitignore` under `new_dataset/` or `dataset/`.
- **Absolute Paths**: When writing shell commands for agents to run, always verify the current working directory. The frontend is in the `frontend/` subdirectory.

## Agent Workflow
When tasked with a feature:
1. **Understand**: Use `grep` to find where the feature touches the stack (e.g., `grep -rn "BM25" .`).
2. **Plan**: Formulate a short plan.
3. **Execute**: Modify the necessary Python or TypeScript files.
4. **Verify**: Run `python3 backend.py` and `npm run build` in the `frontend` folder to ensure your changes didn't break compilation.