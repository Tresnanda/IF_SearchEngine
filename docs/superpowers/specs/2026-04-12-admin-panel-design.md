# Information Retrieval System: Admin Dashboard & Authentication

## Overview
This specification details the addition of a secure, NextAuth-powered Admin Dashboard to manage the thesis repository. This provides a user-friendly way for university staff to add, delete, and re-index `.pdf` and `.docx` files into the BM25 search engine without interacting with Python scripts or the server terminal.

The system will use a local SQLite database to track document metadata (title, uploader, indexing status) alongside the physical files in `new_dataset/`.

## Architecture & Authentication

### 1. Frontend Authentication (NextAuth.js)
*   **Provider:** `CredentialsProvider` configured with a hardcoded dummy user (`admin@informatika.unud.ac.id` / `password`). This is a placeholder designed for a seamless 5-line swap to a custom OAuth provider (e.g., Udayana University IMISSU) later.
*   **Session Management:** JWT strategy stored in an HTTP-only cookie.
*   **Route Protection:** Next.js Middleware will protect all routes under `/admin/*`, redirecting unauthenticated users to `/login`.
*   **Backend Security:** The frontend API routes (which run securely on the server) will communicate with the Flask backend using a hardcoded secret header `X-Admin-Token` to authorize file uploads, deletions, and indexing requests.

### 2. Backend Database (Flask-SQLAlchemy)
A lightweight local SQLite database (`repository.db`) will be added to track metadata for the documents in `new_dataset/`.

**Table: `Thesis`**
*   `id` (Integer, Primary Key)
*   `title` (String, max 255)
*   `filename` (String, unique, max 255)
*   `uploader_email` (String)
*   `upload_date` (DateTime, default UTC)
*   `is_indexed` (Boolean, default False) - Tracks whether the document has been successfully processed into the `.pkl` index files.

## Admin Dashboard UI (Swiss Modernism)
The Admin Dashboard will strictly follow the established "Swiss Modernism / Notion" design system (grayscale palette, `Inter` font, subtle borders, no glassmorphism).

### 1. Layout Structure
*   **Sidebar (Left, 250px):** Minimal vertical navigation. Links: `Dashboard`, `Repository`, `Settings`.
*   **Main Content Area (Right):** Large, clean workspace with maximum `max-w-5xl` constraints.

### 2. Repository Management View (`/admin/repository`)
*   **Action Bar:** 
    *   "Upload Document" button (primary CTA, black or subtle blue).
    *   "Rebuild Search Index" button (secondary, gray outline).
*   **Data Table:** A clean, grid-based table listing all thesis documents.
    *   **Columns:** Title, Filename, Upload Date, Status Badge (Indexed vs Pending).
    *   **Row Actions:** Delete (Trash icon).

### 3. File Upload Flow
*   Clicking "Upload Document" opens a clean, centered Modal.
*   User can select or drag-and-drop a `.pdf` or `.docx` file.
*   Upon submission:
    1. Frontend posts the `FormData` (file) to a Next.js API route.
    2. Next.js API route forwards the file to the secure Flask `/api/admin/upload` endpoint.
    3. Flask saves the physical file to `new_dataset/` and creates a new `Thesis` record in SQLite with `is_indexed = False`.

### 4. Indexing Flow
*   Clicking "Rebuild Search Index" triggers a secure call to Flask's `/api/admin/index` endpoint.
*   The Flask backend synchronously executes the BM25 indexer logic (parsing all files in `new_dataset/` and rewriting `content_index.pkl` and `title_index.pkl`).
*   Upon success, Flask updates all `Thesis` records in the SQLite database to `is_indexed = True`.

## Implementation Requirements
1.  **Dependencies:** 
    *   Frontend: `next-auth` (v4)
    *   Backend: `flask-sqlalchemy`
2.  **API Routes:**
    *   `/api/admin/repository` (GET) - Returns all DB rows.
    *   `/api/admin/upload` (POST) - Accepts file, saves it, creates DB row.
    *   `/api/admin/delete/<id>` (DELETE) - Removes DB row and physical file.
    *   `/api/admin/index` (POST) - Runs the BM25 indexing process and updates DB.
3.  **Synchronization Script:** Since `new_dataset/` currently has ~229 files that aren't in the new database, we need a small migration script (or logic in `backend.py` startup) that scans `new_dataset/` and inserts any missing files into the SQLite database automatically.