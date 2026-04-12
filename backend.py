from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import pickle
import json
import docx
import PyPDF2
from datetime import datetime
# from main import HybridSearchEngine, InvertedIndex, PDFCorpusIndexer, SpellingCorrector, IndonesianPreprocessor
from vsm import HybridSearchEngine
from invertedindex import InvertedIndex
from indexer import DocumentCorpusIndexer
from spellcorrector import SpellingCorrector
from preprocessor import IndonesianPreprocessor

app = Flask(__name__)
CORS(app) # Enable CORS for Next.js frontend

# Configuration
CONTENT_INDEX_PATH = "content_index.pkl"
TITLE_INDEX_PATH = "title_index.pkl"
DOWNLOADS_DIR = "new_dataset"  # Directory containing docx files
FEEDBACK_LOG_PATH = "search_feedback_log.json"

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

# Global engine variable
engine = None

def load_engine():
    global engine
    
    # Check if indices exist
    if not os.path.exists(CONTENT_INDEX_PATH) or not os.path.exists(TITLE_INDEX_PATH):
        print("Error: Index files not found. Please run main.py first to build indices.")
        return False

    try:
        print("Loading content index...")
        with open(CONTENT_INDEX_PATH, 'rb') as f:
            content_index = pickle.load(f)
            
        print("Loading title index...")
        with open(TITLE_INDEX_PATH, 'rb') as f:
            title_index = pickle.load(f)
            
        print("Initializing Hybrid Search Engine...")
        engine = HybridSearchEngine(content_index, title_index)
        return True
    except Exception as e:
        print(f"Error loading engine: {e}")
        return False
    
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
        
    if engine is None:
        return jsonify({
            "status": "error",
            "message": "Search engine not initialized"
        }), 500

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
        
        # Get content-based scores
        content_results = engine.content_model.search(final_query, top_k=20)
        content_scores = {res[0]: res[1] for res in content_results}

        # Get title-based scores
        title_results = engine.title_model.search(final_query, top_k=20)
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
                query_terms = engine.preprocessor.preprocess(final_query)
                snippet = extract_snippet(file_path, query_terms) if file_path else ""
                
                combined_scores.append({
                    "title": title,
                    "filename": filename,
                    "score": final_score,
                    "content_score": content_score,
                    "title_score": title_score,
                    "snippet": snippet
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

if __name__ == '__main__':
    if load_engine():
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Failed to start application due to missing indices.")
        CORPUS_PATH = "new_dataset"
        indexer = DocumentCorpusIndexer(CORPUS_PATH)
        indexer.build_index(filter_sections=True, max_docs=150)
        indexer.save_index(CONTENT_INDEX_PATH, TITLE_INDEX_PATH)
        app.run(debug=True, host='0.0.0.0', port=5000)
