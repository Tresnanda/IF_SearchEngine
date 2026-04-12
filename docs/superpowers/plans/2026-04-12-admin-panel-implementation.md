# Admin Panel & Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a secure Admin Dashboard using NextAuth and Flask-SQLAlchemy to manage the thesis repository and search index.

**Architecture:** We add a local SQLite database (`repository.db`) to the Flask backend to track metadata for files in `new_dataset/`. The Next.js frontend gets `next-auth` for a dummy login that mimics IMISSU OAuth. The Admin Dashboard UI uses the Swiss Modernism aesthetic (zinc grayscale, strict grids).

**Tech Stack:** Next.js (App Router), React, Tailwind CSS, NextAuth.js, Python, Flask, Flask-SQLAlchemy.

---

### Task 1: Setup Flask-SQLAlchemy & Database Models

**Files:**
- Modify: `backend.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt**
Add `Flask-SQLAlchemy` to dependencies.

```text
Flask-SQLAlchemy==3.1.1
```

- [ ] **Step 2: Add SQLAlchemy models and initialization to `backend.py`**
Configure the SQLite database, define the `Thesis` model, and add logic to auto-sync existing files in `new_dataset/` to the database on startup.

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ... existing imports and app config ...

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///repository.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Thesis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    uploader_email = db.Column(db.String(120), nullable=False, default="admin@informatika.unud.ac.id")
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_indexed = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'filename': self.filename,
            'uploader_email': self.uploader_email,
            'upload_date': self.upload_date.isoformat() + "Z" if self.upload_date else None,
            'is_indexed': self.is_indexed
        }

def sync_existing_files_to_db():
    """Scans new_dataset/ and adds missing files to the SQLite DB."""
    if not os.path.exists(DOWNLOADS_DIR):
        os.makedirs(DOWNLOADS_DIR)
        return
        
    existing_files = os.listdir(DOWNLOADS_DIR)
    
    # Simple title extraction: remove extension
    def extract_title(filename):
        return os.path.splitext(filename)[0]
        
    added_count = 0
    for filename in existing_files:
        if filename.endswith(('.pdf', '.docx', '.doc')):
            # Check if it exists in DB
            thesis = Thesis.query.filter_by(filename=filename).first()
            if not thesis:
                # We assume existing files are indexed since they were present during the last run
                # but to be safe, we'll mark them True if content_index.pkl exists
                is_indexed = os.path.exists(CONTENT_INDEX_PATH)
                new_thesis = Thesis(
                    title=extract_title(filename),
                    filename=filename,
                    is_indexed=is_indexed
                )
                db.session.add(new_thesis)
                added_count += 1
                
    if added_count > 0:
        db.session.commit()
        print(f"Synced {added_count} existing files to the database.")

with app.app_context():
    db.create_all()
    sync_existing_files_to_db()

# ... existing load_engine() ...
```

- [ ] **Step 3: Commit**
```bash
git add backend.py requirements.txt
git commit -m "feat: add flask-sqlalchemy and repository db models"
```

---

### Task 2: Create Secure Admin API Endpoints

**Files:**
- Modify: `backend.py`

- [ ] **Step 1: Add Admin API Routes with a secret token check**
Add routes for listing, uploading, deleting, and re-indexing theses. Protect them with a hardcoded `X-Admin-Token` header.

```python
# ... add below existing routes ...
import shutil

ADMIN_SECRET_TOKEN = "super-secret-admin-token-123"

def require_admin_token(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-Admin-Token')
        if not token or token != ADMIN_SECRET_TOKEN:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/admin/repository', methods=['GET'])
@require_admin_token
def get_repository():
    theses = Thesis.query.order_by(Thesis.upload_date.desc()).all()
    return jsonify([t.to_dict() for t in theses])

@app.route('/api/admin/upload', methods=['POST'])
@require_admin_token
def upload_thesis():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and file.filename.endswith(('.pdf', '.docx', '.doc')):
        filename = file.filename
        file_path = os.path.join(DOWNLOADS_DIR, filename)
        
        # Check if already exists in DB
        existing = Thesis.query.filter_by(filename=filename).first()
        if existing:
            return jsonify({'error': 'File already exists in repository'}), 409
            
        file.save(file_path)
        
        title = os.path.splitext(filename)[0]
        new_thesis = Thesis(title=title, filename=filename, is_indexed=False)
        db.session.add(new_thesis)
        db.session.commit()
        
        return jsonify({'message': 'File uploaded successfully', 'thesis': new_thesis.to_dict()}), 201
        
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/admin/delete/<int:id>', methods=['DELETE'])
@require_admin_token
def delete_thesis(id):
    thesis = Thesis.query.get_or_404(id)
    file_path = os.path.join(DOWNLOADS_DIR, thesis.filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    db.session.delete(thesis)
    db.session.commit()
    
    return jsonify({'message': 'Thesis deleted successfully'})

@app.route('/api/admin/index', methods=['POST'])
@require_admin_token
def trigger_index():
    """Runs the indexing process synchronously and updates DB status."""
    try:
        # Import the indexer class defined in indexer.py
        from indexer import DocumentCorpusIndexer
        indexer = DocumentCorpusIndexer(DOWNLOADS_DIR)
        indexer.build_index()
        
        # Reload the engine globally so search starts using new index immediately
        load_engine()
        
        # Mark all files in DB as indexed
        Thesis.query.update({Thesis.is_indexed: True})
        db.session.commit()
        
        return jsonify({'message': 'Index rebuilt successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 2: Commit**
```bash
git add backend.py
git commit -m "feat: add secure admin api routes to backend"
```

---

### Task 3: Setup NextAuth.js in Frontend

**Files:**
- Create: `frontend/src/app/api/auth/[...nextauth]/route.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: Install NextAuth.js**
Run: `cd frontend && npm install next-auth`

- [ ] **Step 2: Configure NextAuth**
Create the NextAuth API route with a dummy Credentials provider mimicking IMISSU.

```typescript
// frontend/src/app/api/auth/[...nextauth]/route.ts
import NextAuth, { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "IMISSU Dummy",
      credentials: {
        email: { label: "Email", type: "text", placeholder: "admin@informatika.unud.ac.id" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Dummy check for now. Will be replaced by real OAuth.
        if (credentials?.email === "admin@informatika.unud.ac.id" && credentials?.password === "password") {
          return { id: "1", name: "Admin", email: "admin@informatika.unud.ac.id", role: "admin" };
        }
        return null;
      }
    })
  ],
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET || "super-secret-key-replace-in-production",
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
```

- [ ] **Step 3: Commit**
```bash
cd frontend && git add package.json package-lock.json src/app/api/auth
git commit -m "feat: setup NextAuth for admin authentication"
```

---

### Task 4: Create Login Page and Middleware

**Files:**
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/middleware.ts`

- [ ] **Step 1: Create Login Page**
Implement a minimal login form using the Swiss Modernism aesthetic.

```tsx
// frontend/src/app/login/page.tsx
'use client';

import { useState } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next-navigation';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    const res = await signIn('credentials', {
      redirect: false,
      email,
      password,
    });

    if (res?.error) {
      setError('Invalid credentials');
    } else {
      router.push('/admin');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4">
      <div className="w-full max-w-md bg-white border border-zinc-200 rounded-xl shadow-sm p-8">
        <h1 className="text-2xl font-semibold text-zinc-900 mb-2">Admin Login</h1>
        <p className="text-zinc-500 text-sm mb-6">Sign in with your university credentials to manage the repository.</p>
        
        {error && <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md border border-red-100">{error}</div>}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Email</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-950 focus:border-zinc-950" 
              placeholder="admin@informatika.unud.ac.id"
              required 
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-zinc-200 rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-950 focus:border-zinc-950" 
              placeholder="password"
              required 
            />
          </div>
          <button 
            type="submit" 
            className="w-full py-2 px-4 bg-zinc-950 hover:bg-zinc-800 text-white text-sm font-medium rounded-md transition-colors mt-2"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add Middleware to Protect /admin Routes**
Create Next.js middleware to automatically redirect unauthenticated users away from the `/admin` paths.

```typescript
// frontend/src/middleware.ts
export { default } from "next-auth/middleware"

export const config = {
  matcher: ["/admin/:path*"],
}
```

- [ ] **Step 3: Commit**
```bash
cd frontend && git add src/app/login src/middleware.ts
git commit -m "feat: create login page and protect admin routes"
```

---

### Task 5: Build the Admin Dashboard Layout & Repository View

**Files:**
- Create: `frontend/src/app/admin/layout.tsx`
- Create: `frontend/src/app/admin/page.tsx`

- [ ] **Step 1: Create Admin Layout**
A simple Swiss sidebar layout for the admin area.

```tsx
// frontend/src/app/admin/layout.tsx
'use client';

import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Database, LayoutDashboard } from "lucide-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const pathname = usePathname();

  if (status === "loading") return <div className="min-h-screen flex items-center justify-center text-zinc-500">Loading...</div>;

  return (
    <div className="min-h-screen bg-zinc-50 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-200 bg-white flex flex-col hidden md:flex">
        <div className="p-6 border-b border-zinc-200">
          <h2 className="font-semibold text-zinc-900">Admin Portal</h2>
          <p className="text-xs text-zinc-500 truncate mt-1">{session?.user?.email}</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <Link href="/admin" className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${pathname === '/admin' ? 'bg-zinc-100 text-zinc-900' : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'}`}>
            <Database className="w-4 h-4" />
            Repository
          </Link>
        </nav>
        <div className="p-4 border-t border-zinc-200">
          <button onClick={() => signOut({ callbackUrl: '/' })} className="flex items-center gap-3 px-3 py-2 w-full text-left rounded-md text-sm font-medium text-zinc-600 hover:bg-red-50 hover:text-red-600 transition-colors">
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create Repository View (Main Admin Page)**
Implement the data table and indexing button. *Note: We bypass Next.js API routes for the heavy lifting and hit our Flask API directly from the client using the hardcoded token for simplicity right now.*

```tsx
// frontend/src/app/admin/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { Trash2, RefreshCw, Upload, FileText } from 'lucide-react';

const ADMIN_TOKEN = "super-secret-admin-token-123";

interface Thesis {
  id: number;
  title: string;
  filename: string;
  upload_date: string;
  is_indexed: boolean;
}

export default function RepositoryPage() {
  const [theses, setTheses] = useState<Thesis[]>([]);
  const [loading, setLoading] = useState(true);
  const [indexing, setIndexing] = useState(false);

  const fetchTheses = async () => {
    try {
      const res = await fetch('/api/admin/repository', {
        headers: { 'X-Admin-Token': ADMIN_TOKEN } // Next.js rewrites this to :5000
      });
      if (res.ok) setTheses(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTheses();
  }, []);

  const handleIndex = async () => {
    if (!confirm('This will parse all documents and rebuild the search index. This may take several minutes. Continue?')) return;
    setIndexing(true);
    try {
      const res = await fetch('/api/admin/index', {
        method: 'POST',
        headers: { 'X-Admin-Token': ADMIN_TOKEN }
      });
      if (res.ok) {
        alert('Index rebuilt successfully!');
        fetchTheses();
      } else {
        alert('Failed to rebuild index.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIndexing(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      const res = await fetch(`/api/admin/delete/${id}`, {
        method: 'DELETE',
        headers: { 'X-Admin-Token': ADMIN_TOKEN }
      });
      if (res.ok) fetchTheses();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div className="p-8 text-zinc-500">Loading repository data...</div>;

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Thesis Repository</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage documents in the search engine index.</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={handleIndex}
            disabled={indexing}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-zinc-200 text-zinc-700 text-sm font-medium rounded-md hover:bg-zinc-50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${indexing ? 'animate-spin' : ''}`} />
            {indexing ? 'Rebuilding Index...' : 'Rebuild Search Index'}
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-zinc-950 text-white text-sm font-medium rounded-md hover:bg-zinc-800 transition-colors">
            <Upload className="w-4 h-4" />
            Upload Document
          </button>
        </div>
      </div>

      <div className="bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-medium">
            <tr>
              <th className="px-6 py-3">Document</th>
              <th className="px-6 py-3">Upload Date</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {theses.map(t => (
              <tr key={t.id} className="hover:bg-zinc-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-zinc-400" />
                    <div>
                      <p className="font-medium text-zinc-900 line-clamp-1">{t.title}</p>
                      <p className="text-xs text-zinc-500">{t.filename}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {new Date(t.upload_date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${t.is_indexed ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                    {t.is_indexed ? 'Indexed' : 'Pending Reindex'}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button onClick={() => handleDelete(t.id)} className="text-zinc-400 hover:text-red-600 transition-colors p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {theses.length === 0 && (
              <tr><td colSpan={4} className="px-6 py-8 text-center text-zinc-500">No documents found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**
```bash
cd frontend && git add src/app/admin
git commit -m "feat: build admin dashboard layout and repository view"
```