from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import pickle
import json
from pathlib import Path
import docx
import PyPDF2
from datetime import datetime
# from main import HybridSearchEngine, InvertedIndex, PDFCorpusIndexer, SpellingCorrector, IndonesianPreprocessor
from vsm import HybridSearchEngine
from invertedindex import InvertedIndex
from indexer import DocumentCorpusIndexer
from spellcorrector import SpellingCorrector
from preprocessor import IndonesianPreprocessor
from index_runtime import ActiveManifest, IndexRuntime
from reindex_service import ReindexService
from incremental_indexer import IncrementalIndexBuilder
from incremental_indexer import build_indices_from_records

app = Flask(__name__)
CORS(app) # Enable CORS for Next.js frontend

# Configuration
CONTENT_INDEX_PATH = "content_index.pkl"
TITLE_INDEX_PATH = "title_index.pkl"
DOWNLOADS_DIR = "new_dataset"  # Directory containing docx files
FEEDBACK_LOG_PATH = "search_feedback_log.json"
INDEX_STORE_DIR = os.getenv("INDEX_STORE_DIR", "data/index")
DOCUMENT_CACHE_PATH = os.getenv("DOCUMENT_CACHE_PATH", os.path.join(INDEX_STORE_DIR, "document_cache.json"))
REINDEX_MODE = os.getenv("REINDEX_MODE", "incremental").lower()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///repository.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

index_runtime = IndexRuntime(base_dir=INDEX_STORE_DIR)
index_runtime.bootstrap_if_missing(
    seed_content_index_path=CONTENT_INDEX_PATH,
    seed_title_index_path=TITLE_INDEX_PATH,
)
# Task 2 wiring only; admin endpoint integration follows in later tasks.
reindex_service = ReindexService(runtime=index_runtime)

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

# Global engine variable
engine = None
engine_manifest_version = None


def _load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def _build_engine_from_manifest(manifest):
    content_index = _load_pickle(manifest.content_index_path)
    title_index = _load_pickle(manifest.title_index_path)
    return HybridSearchEngine(content_index, title_index)

def load_engine():
    global engine, engine_manifest_version
    try:
        manifest = index_runtime.recover_active_manifest()
        next_engine = _build_engine_from_manifest(manifest)
        engine = next_engine
        engine_manifest_version = manifest.version
        return True
    except Exception as e:
        print(f"Error loading engine: {e}")
        return False


def _reload_engine_or_raise(_manifest):
    if not load_engine():
        raise RuntimeError("engine reload failed")


def _mark_all_theses_indexed() -> None:
    with app.app_context():
        Thesis.query.update({Thesis.is_indexed: True})
        db.session.commit()


def _on_reindex_success(manifest) -> None:
    _reload_engine_or_raise(manifest)
    _mark_all_theses_indexed()


def initialize_engine_for_startup() -> bool:
    if load_engine():
        return True

    print("Failed to start application due to missing indices.")
    indexer = DocumentCorpusIndexer(DOWNLOADS_DIR)
    indexer.build_index(filter_sections=True, max_docs=150)
    indexer.save_index(CONTENT_INDEX_PATH, TITLE_INDEX_PATH)

    index_runtime.set_active_manifest(
        ActiveManifest(
            version=f"legacy-root-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            doc_count=indexer.content_index.num_docs,
            built_at=datetime.utcnow().isoformat() + "Z",
            content_index_path=Path(CONTENT_INDEX_PATH).resolve(),
            title_index_path=Path(TITLE_INDEX_PATH).resolve(),
        )
    )
    return load_engine()
    
def extract_snippet(file_path, query_terms, context_words=15):
    """Extract a small text snippet around the matched query terms."""
    if not os.path.exists(file_path):
        return ""
        
    text = ""
    try:
        if file_path.lower().endswith('.docx'):
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + " "
        elif file_path.lower().endswith('.pdf'):
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages[:10]: # Only search first 10 pages for snippet to be fast
                    text += page.extract_text() + " "
    except Exception:
        return ""

    text_lower = text.lower()
    best_idx = -1
    
    # Find the first occurrence of any query term
    for term in query_terms:
        idx = text_lower.find(term.lower())
        if idx != -1:
            best_idx = idx
            break
            
    if best_idx == -1:
        return text[:200] + "..." # Fallback
        
    # Extract surrounding text
    start_idx = max(0, best_idx - 100)
    end_idx = min(len(text), best_idx + 100)
    
    snippet = text[start_idx:end_idx].strip()
    if start_idx > 0: snippet = "..." + snippet
    if end_idx < len(text): snippet = snippet + "..."
    
    return snippet


def _select_snippet_terms(original_query: str, corrected_query: str | None) -> list[str]:
    preferred_query = corrected_query if corrected_query else original_query
    terms = IndonesianPreprocessor().preprocess(preferred_query)
    if terms:
        return terms
    return IndonesianPreprocessor().preprocess(original_query)


def _extract_year_from_title(title: str) -> str | None:
    import re

    match = re.search(r"\b(19|20)\d{2}\b", title)
    return match.group(0) if match else None


def _detect_domain_from_title(title: str) -> str:
    lowered = title.lower()
    domain_rules = [
        ("sentiment", ["sentimen", "sentiment", "review", "opini"]),
        ("security", ["enkripsi", "kriptografi", "rsa", "aes", "cipher", "keamanan"]),
        ("computer vision", ["cnn", "resnet", "inception", "gambar", "vision"]),
        ("nlp", ["text mining", "ontology", "token", "bahasa"]),
        ("recommender", ["rekomendasi", "collaborative", "slope one"]),
    ]

    for label, keywords in domain_rules:
        if any(keyword in lowered for keyword in keywords):
            return label
    return "other"


def _expand_query_terms_for_recall(query_terms: list[str]) -> list[str]:
    if not query_terms:
        return []

    synonym_map = {
        "sentimen": ["sentiment", "opini"],
        "sentiment": ["sentimen", "opini"],
        "kriptografi": ["enkripsi", "cipher", "security"],
        "enkripsi": ["kriptografi", "cipher", "security"],
        "keamanan": ["security", "kriptografi"],
        "sistem": ["system"],
        "rekomendasi": ["recommendation", "collaborative"],
        "collaborative": ["rekomendasi"],
    }

    expanded = list(query_terms)
    for term in query_terms:
        for synonym in synonym_map.get(term, []):
            if synonym not in expanded:
                expanded.append(synonym)
    return expanded

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.json
        
        # Data yang diharapkan dari frontend:
        # {
        #   "query": "string",
        #   "satisfied": boolean,
        #   "relevant_count": int,
        #   "total_results": int
        # }
        
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": data.get('query'),
            "satisfied": data.get('satisfied'),
            "relevant_count": data.get('relevant_count'),
            "total_displayed": data.get('total_results'),
            # Hitung precision sederhana: relevant / total
            "precision_score": data.get('relevant_count', 0) / max(data.get('total_results', 1), 1)
        }

        # Simpan ke file JSON (append mode)
        existing_data = []
        if os.path.exists(FEEDBACK_LOG_PATH):
            try:
                with open(FEEDBACK_LOG_PATH, 'r') as f:
                    existing_data = json.load(f)
            except:
                existing_data = []
        
        existing_data.append(feedback_entry)
        
        with open(FEEDBACK_LOG_PATH, 'w') as f:
            json.dump(existing_data, f, indent=4)

        return jsonify({"status": "success", "message": "Feedback saved"})

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    
    response = {
        "status": "success",
        "correction": None,
        "data": []
    }
    
    if not query:
        return jsonify(response)
        
    if engine is None and not load_engine():
        return jsonify({
            "status": "error",
            "message": "Search engine unavailable: failed to initialize index"
        }), 503

    try:
        # 1. Spelling Correction
        # We use the internal spelling corrector from the engine
        corrected_query, was_corrected, corrections = engine.spelling_corrector.correct_query_spelling(query)
        
        if was_corrected:
            response["correction"] = corrected_query
            
        # 2. Perform Search
        # We will search using the ORIGINAL query to be safe, 
        # or we could search the corrected one. 
        # Given the user wants a "correction" field, it implies the search might be on the original 
        # but suggests a fix. However, usually if there's a correction, 
        # users might want results for the corrected version if the original yields nothing.
        # But for this specific JSON structure, passing "correction" usually means "Did you mean?".
        # Let's search for the provided query.
        
        # If the query is very misspelled, results might be empty.
        # Let's search using the query provided by the user.
        final_query = query
        
        # NOTE: If you want to force search on corrected query when confidence is high, change here.
        # For now, sticking to user input for search, but providing suggestion.
        
        # Reuse logic from HybridSearchEngine.search but without print/input
        query_terms = engine.preprocessor.preprocess(final_query)
        expanded_terms = _expand_query_terms_for_recall(query_terms)
        search_query = " ".join(expanded_terms) if expanded_terms else final_query
        
        # Get content-based scores
        content_results = engine.content_model.search(search_query, top_k=30)
        content_scores = {res[0]: res[1] for res in content_results}

        # Get title-based scores
        title_results = engine.title_model.search(search_query, top_k=30)
        title_scores = {res[0]: res[1] for res in title_results}

        # Combine scores
        all_docs = set(content_scores.keys()) | set(title_scores.keys())
        combined_scores = []

        for doc_id in all_docs:
            content_score = content_scores.get(doc_id, 0.0)
            title_score = title_scores.get(doc_id, 0.0)

            # Weighted combination
            final_score = (engine.content_weight * content_score +
                          engine.title_weight * title_score)

            if final_score > 0:
                # Get metadata
                metadata = engine.content_index.doc_metadata.get(doc_id, {})
                title = metadata.get("title", "Unknown")
                filename = metadata.get("filename", "Unknown")
                file_path = metadata.get("path", "")
                
                # Fetch snippet context
                snippet_terms = _select_snippet_terms(
                    original_query=final_query,
                    corrected_query=response["correction"],
                )
                snippet = extract_snippet(file_path, snippet_terms) if file_path else ""
                
                combined_scores.append({
                    "title": title,
                    "filename": filename,
                    "score": final_score,
                    "content_score": content_score,
                    "title_score": title_score,
                    "snippet": snippet,
                    "year": _extract_year_from_title(title),
                    "domain": _detect_domain_from_title(title),
                })

        combined_scores.sort(key=lambda x: x['score'], reverse=True)

        response["data"] = combined_scores[:10]
        
        return jsonify(response)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/files/<path:filename>')
def serve_file(filename):
    try:
        return send_from_directory(DOWNLOADS_DIR, filename)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"File not found: {str(e)}"
        }), 404

import shutil

ADMIN_INTERNAL_TOKEN = os.getenv("ADMIN_INTERNAL_TOKEN")
if not ADMIN_INTERNAL_TOKEN:
    raise RuntimeError("ADMIN_INTERNAL_TOKEN must be set")
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _build_indices(content_path: str, title_path: str) -> int:
    indexer = DocumentCorpusIndexer(DOWNLOADS_DIR)
    indexer.build_index()
    indexer.save_index(content_path, title_path)
    return indexer.content_index.num_docs


def _build_indices_incremental(content_path: str, title_path: str) -> int:
    builder = IncrementalIndexBuilder(DOWNLOADS_DIR, DOCUMENT_CACHE_PATH)
    records, stats, cache = builder.collect_records()
    build_indices_from_records(records, content_path, title_path)
    builder.save_cache(cache)
    return len(records), stats


def _select_reindex_builder():
    if REINDEX_MODE == "full":
        return _build_indices, "full"
    return _build_indices_incremental, "incremental"


def require_internal_admin_token(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("X-Internal-Admin-Token")
        if not token or token != ADMIN_INTERNAL_TOKEN:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)

    return decorated_function


@app.route('/health/live', methods=['GET'])
def health_live():
    return jsonify({'status': 'ok'}), 200


@app.route('/health/ready', methods=['GET'])
def health_ready():
    global engine, engine_manifest_version
    try:
        manifest = index_runtime.read_active_manifest()
        if not manifest.content_index_path.exists() or not manifest.title_index_path.exists():
            raise RuntimeError("active index files are missing")

        _load_pickle(manifest.content_index_path)
        _load_pickle(manifest.title_index_path)

        if engine is None or engine_manifest_version != manifest.version:
            next_engine = _build_engine_from_manifest(manifest)
            engine = next_engine
            engine_manifest_version = manifest.version

        ready = engine is not None and engine_manifest_version == manifest.version
        state = reindex_service.status()
        return jsonify({
            'ready': ready,
            'active_version': manifest.version,
            'doc_count': manifest.doc_count,
            'reindex_status': state.status,
            'last_error': state.last_error,
        }), (200 if ready else 503)
    except Exception as exc:
        state = reindex_service.status()
        return jsonify({
            'ready': False,
            'active_version': None,
            'doc_count': 0,
            'reindex_status': state.status,
            'last_error': state.last_error or str(exc),
        }), 503

@app.route('/admin/repository', methods=['GET'])
@require_internal_admin_token
def get_repository():
    theses = Thesis.query.order_by(Thesis.upload_date.desc()).all()
    return jsonify([t.to_dict() for t in theses])

@app.route('/admin/upload', methods=['POST'])
@require_internal_admin_token
def upload_thesis():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No selected file'}), 400

    filename = os.path.basename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Invalid file type'}), 400

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_UPLOAD_SIZE_BYTES:
        return jsonify({'error': 'File exceeds size limit'}), 400

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOADS_DIR, filename)
    if os.path.exists(file_path):
        return jsonify({'error': 'File already exists'}), 409

    existing = Thesis.query.filter_by(filename=filename).first()
    if existing:
        return jsonify({'error': 'File already exists'}), 409

    file.save(file_path)

    title = os.path.splitext(filename)[0]
    new_thesis = Thesis(title=title, filename=filename, is_indexed=False)
    db.session.add(new_thesis)
    db.session.commit()

    return jsonify({'message': 'File uploaded successfully', 'thesis': new_thesis.to_dict()}), 201

@app.route('/admin/delete/<int:id>', methods=['DELETE'])
@require_internal_admin_token
def delete_thesis(id):
    thesis = Thesis.query.get_or_404(id)
    file_path = os.path.join(DOWNLOADS_DIR, thesis.filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    db.session.delete(thesis)
    db.session.commit()
    
    return jsonify({'message': 'Thesis deleted successfully'})

@app.route('/admin/index', methods=['POST'])
@app.route('/admin/reindex', methods=['POST'])
@require_internal_admin_token
def trigger_index():
    actor = request.headers.get('X-Admin-Actor', 'admin@informatika.unud.ac.id')
    build_fn, mode = _select_reindex_builder()
    started, message = reindex_service.start(
        actor=actor,
        build_fn=build_fn,
        on_success=_on_reindex_success,
        mode=mode,
    )
    if not started:
        return jsonify({'error': message}), 409
    return jsonify({'message': message}), 202


@app.route('/admin/reindex/status', methods=['GET'])
@require_internal_admin_token
def get_reindex_status():
    state = reindex_service.status()
    return jsonify({
        'status': state.status,
        'mode': state.mode,
        'stats': state.stats,
        'actor': state.actor,
        'started_at': state.started_at,
        'finished_at': state.finished_at,
        'last_error': state.last_error,
        'active_version': state.active_version,
        'last_doc_count': state.last_doc_count,
    }), 200

if __name__ == '__main__':
    if initialize_engine_for_startup():
        app.run(debug=True, host='0.0.0.0', port=5000)
