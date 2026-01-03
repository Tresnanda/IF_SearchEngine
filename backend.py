from flask import Flask, jsonify, request, send_from_directory
import os
import pickle
from main import HybridSearchEngine, InvertedIndex, PDFCorpusIndexer, SpellingCorrector, IndonesianPreprocessor

app = Flask(__name__)

# Configuration
CONTENT_INDEX_PATH = "content_index.pkl"
TITLE_INDEX_PATH = "title_index.pkl"
DOWNLOADS_DIR = "downloads"  # Directory containing PDF files

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
        content_scores = {doc_id: score for doc_id, score, _ in content_results}

        # Get title-based scores
        title_results = engine.title_model.search(final_query, top_k=20)
        title_scores = {doc_id: score for doc_id, score, _ in title_results}

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
                
                combined_scores.append({
                    "title": title,
                    "filename": filename,
                    "score": final_score,
                    "content_score": content_score,
                    "title_score": title_score
                })

        # Sort by final score
        combined_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top 10
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

if __name__ == '__main__':
    if load_engine():
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Failed to start application due to missing indices.")
