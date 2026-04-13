# Information Retrieval System

A thesis-focused Information Retrieval system using a traditional BM25 stack (no embeddings/vector DB), with Flask backend and Next.js frontend.

## Features
- BM25 ranking with separate content/title scoring.
- PDF and DOCX corpus indexing.
- Snippet generation around matched terms.
- Admin panel for upload, delete, and async reindex control.
- Runtime-safe reindex flow with active/candidate index snapshots.

## Tech Stack
### Backend
- Python 3.12
- Flask + Flask-SQLAlchemy
- PyPDF2 + python-docx
- Sastrawi preprocessing

### Frontend
- Next.js App Router
- React 19
- Tailwind CSS
- NextAuth (credentials provider)

## Local Setup (Non-Docker)
1. Clone repository.
   ```bash
   git clone <repo-url>
   cd Kelompok1_InformationRetrieval
   ```
2. Setup backend environment.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. (Optional) Build initial indices from local corpus.
   ```bash
   python3 test_docx_indexer.py
   ```
4. Start backend.
   ```bash
   python3 backend.py
   ```
5. Start frontend.
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Admin Operations
### Required Environment Variables
- `NEXTAUTH_SECRET`: signing key for NextAuth sessions.
- `ADMIN_INTERNAL_TOKEN`: token used by Next.js server routes to call backend admin endpoints.
- `ADMIN_EMAIL`: admin login email.
- `ADMIN_PASSWORD`: admin login password.

### Reindex Behavior
- Reindex runs asynchronously via admin trigger.
- Search stays online using last successful active index while candidate index is rebuilt.
- On failure, active index remains unchanged.

### Health Endpoints
- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`

## VPS Setup Guide (Docker Compose)

This is the recommended production-like path. If Docker is configured correctly, moving from local to VPS is mostly copy-and-run.

### 1) Prepare VPS
Use Ubuntu 22.04/24.04 (or equivalent), then install Docker Engine + Compose plugin.

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out/in once after `usermod`.

### 2) Clone Project on VPS
```bash
git clone <repo-url>
cd Kelompok1_InformationRetrieval
```

### 3) Configure Environment
Copy `.env.example` to `.env` and set strong values.

```bash
cp .env.example .env
```

Minimum required in `.env`:
- `ADMIN_INTERNAL_TOKEN` (strong random string)
- `NEXTAUTH_SECRET` (long random string)
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `BACKEND_URL=http://backend:5000`
- `NEXTAUTH_URL=https://<your-domain-or-ip>`

### 4) Prepare Data Directories
```bash
mkdir -p new_dataset data/index data/db
```

Upload thesis files (`.pdf` / `.docx`) into `new_dataset/`.

### 5) Start Services
```bash
docker compose up -d --build
docker compose ps
```

Default exposed ports:
- Frontend: `3001`
- Backend: `5000`

### 6) Validate Health
```bash
curl -f http://127.0.0.1:5000/health/live
curl -f http://127.0.0.1:5000/health/ready
```

Optional smoke script (Docker-enabled environment):
```bash
bash scripts/smoke/test_compose_health.sh
```

### 7) First Reindex on VPS
1. Login to admin page (`/login`) using `ADMIN_EMAIL` + `ADMIN_PASSWORD`.
2. Upload files if needed.
3. Trigger reindex from admin panel.
4. Monitor reindex status in admin page.

### 8) Reverse Proxy + HTTPS (Recommended)
Put Nginx/Caddy in front of frontend service and terminate TLS there.

For Nginx, proxy `443 -> localhost:3001` and issue cert with Certbot.

### 9) Updating Deployment
```bash
git pull
docker compose up -d --build
```

### 10) Basic Operations
- Logs:
  ```bash
  docker compose logs -f backend
  docker compose logs -f frontend
  ```
- Restart:
  ```bash
  docker compose restart
  ```
- Backup persistent data:
  - `new_dataset/`
  - `data/index/`
  - `data/db/`

## Architecture Note
This project intentionally avoids vector databases/embeddings to keep cost and latency low while still delivering strong retrieval quality via tuned BM25 and operationally safe indexing.
