from invertedindex import InvertedIndex
from preprocessor import IndonesianPreprocessor
import math
from typing import List, Dict, Tuple, Set
from spellcorrector import SpellingCorrector
from collections import defaultdict, Counter

class BM25Model:
    """Vector Space Model with Okapi BM25 weighting"""
    
    def __init__(self, index: InvertedIndex, k1: float = 1.5, b: float = 0.75):
        self.index = index
        self.preprocessor = IndonesianPreprocessor()
        self.k1 = k1
        self.b = b
        self.avgdl = index.avg_doc_length if hasattr(index, 'avg_doc_length') and index.avg_doc_length else 1.0

    def compute_idf(self, term: str) -> float:
        """Compute BM25 inverse document frequency"""
        df = self.index.df.get(term, 0)
        N = self.index.num_docs
        # Standard BM25 IDF formula
        idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
        return max(0, idf) # Ensure IDF is not negative

    def score_document(self, query_terms: List[str], doc_id: int) -> float:
        """Calculate BM25 score for a single document given query terms"""
        score = 0.0
        doc_length = self.index.doc_lengths.get(doc_id, self.avgdl)
        
        for term in query_terms:
            if term not in self.index.index:
                continue
                
            # Find term frequency in this document
            tf = 0
            postings = self.index.get_postings(term) # Handle compressed index format
            for d_id, freq in postings:
                if d_id == doc_id:
                    tf = freq
                    break
                    
            if tf == 0:
                continue
                
            idf = self.compute_idf(term)
            
            # BM25 Term Frequency weighting
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avgdl))
            
            score += idf * (numerator / denominator)
            
        return score

    def search(self, query: str, top_k: int = 10):
        query_terms = self.preprocessor.preprocess(query)
        
        if not query_terms:
            return []

        # Find candidate documents (documents containing at least one query term)
        candidate_docs = set()
        for term in query_terms:
            if term in self.index.index:
                postings = self.index.get_postings(term) # Handle compressed index format
                candidate_docs.update(doc_id for doc_id, _ in postings)

        scores = []
        for doc_id in candidate_docs:
            score = self.score_document(query_terms, doc_id)
            if score > 0:
                title = self.index.doc_metadata.get(doc_id, {}).get("title", "Unknown")
                scores.append((doc_id, score, title))
                
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

class HybridSearchEngine:
    """Hybrid search engine combining content-based and title-based retrieval"""

    def __init__(self, content_index: InvertedIndex, title_index: InvertedIndex):
        self.content_index = content_index
        self.title_index = title_index
        self.preprocessor = IndonesianPreprocessor()

        # Create separate TF-IDF models for content and title
        self.content_model = BM25Model(content_index)
        self.title_model = BM25Model(title_index, k1=2.0, b=0.2) # Lower b for title to not penalize long titles too much

        # Weight parameters for hybrid scoring (tunable) - title gets higher weight
        self.content_weight = 0.3
        self.title_weight = 0.7

        # Initialize spelling corrector
        self.spelling_corrector = SpellingCorrector(set())
        self.spelling_corrector.build_vocabulary_from_indices(content_index, title_index)

    def set_weights(self, content_weight: float, title_weight: float):
        """Set weights for content and title components"""
        if content_weight + title_weight != 1.0:
            raise ValueError("Weights must sum to 1.0")
        self.content_weight = content_weight
        self.title_weight = title_weight

    def search(self, query: str, top_k: int = 10):
        """Perform hybrid search combining content and title scores with spelling correction"""
        # Check for spelling corrections
        corrected_query, was_corrected, corrections = self.spelling_corrector.correct_query_spelling(query)

        final_query = query

        # If spelling corrections were suggested, ask for user confirmation
        if was_corrected:
            print(f"\nSpelling corrections found:")

            # Show each correction clearly
            for original, suggestions in corrections.items():
                if suggestions:
                    print(f"  '{original}' -> '{suggestions[0]}'")

            print(f"\n  Original query: {query}")
            print(f"  Corrected query: {corrected_query}")

            response = input("\nApakah yang dimaksud (y/n)? ").strip().lower()

            if response == 'y' or response == 'yes':
                final_query = corrected_query
                print(f"✓ Menggunakan query yang dikoreksi: '{final_query}'")
            else:
                final_query = query
                print(f"✓ Menggunakan query asli: '{query}'")

        # Perform search with the final query
        query_terms = self.preprocessor.preprocess(final_query)
        print("Query terms (preprocesed):", query_terms)

        if not query_terms:
            return []

        # Get content-based scores
        content_results = self.content_model.search(final_query, top_k=top_k*2)  # Get more for better combination
        content_scores = {res[0]: res[1] for res in content_results}

        # Get title-based scores
        title_results = self.title_model.search(final_query, top_k=top_k*2)
        title_scores = {res[0]: res[1] for res in title_results}

        # Combine scores from both indices
        all_docs = set(content_scores.keys()) | set(title_scores.keys())
        combined_scores = []

        for doc_id in all_docs:
            content_score = content_scores.get(doc_id, 0.0)
            title_score = title_scores.get(doc_id, 0.0)

            # Weighted combination
            final_score = (self.content_weight * content_score +
                          self.title_weight * title_score)

            if final_score > 0:
                # Get title from content index metadata
                title = self.content_index.doc_metadata.get(doc_id, {}).get("title", "Unknown")
                filename = self.content_index.doc_metadata.get(doc_id, {}).get("filename", "Unknown")
                combined_scores.append((doc_id, final_score, title, filename,
                                      content_score, title_score))

        # Sort by combined score
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        return combined_scores[:top_k]