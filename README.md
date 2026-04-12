# Information Retrieval System

A high-performance Information Retrieval Engine designed specifically for indexing and searching academic thesis documents (both PDF and DOCX). Built with a traditional IR stack using the Okapi BM25 algorithm for highly accurate ranking, and a sleek, hyper-minimalist Next.js frontend following Swiss Modernism design principles.

## Features
- **BM25 Search Algorithm:** Replaces traditional TF-IDF with the industry-standard Okapi BM25 for superior search relevance.
- **Dual Format Support:** Automatically extracts text and metadata from both `.pdf` and `.docx` documents.
- **Contextual Snippets:** Generates concise 200-character snippets around the matched search terms to give users immediate context.
- **Swiss Modernism UI:** A blazing fast, "Command Palette" style interface built with Next.js and Tailwind CSS (Zinc monochrome palette).
- **Automated Scraping:** Includes a robust scraper to reliably download restricted and public Google Drive thesis links.

## Tech Stack
### Backend
- **Python 3.12**
- **Flask** (API Server + CORS)
- **PyPDF2 & python-docx** (Document text extraction)
- **NLTK / Sastrawi** (Indonesian stemming & NLP preprocessing)
- **Scikit-learn / NumPy** (Vector space computations for BM25)
- **gdown / requests** (Drive scraping)

### Frontend
- **Next.js (App Router)**
- **React 18**
- **Tailwind CSS** (Zinc theme, glassmorphism removed)
- **Framer Motion**
- **Lucide React**

## Setup & Running
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd Kelompok1_InformationRetrieval
   ```

2. **Backend Setup:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gdown python-docx
   ```

3. **Index the Dataset:**
   Place your PDF and DOCX files inside the `new_dataset/` directory.
   ```bash
   python3 test_docx_indexer.py
   ```
   This will generate `content_index.pkl` and `title_index.pkl`.

4. **Start the Backend Server:**
   ```bash
   python3 backend.py
   ```
   The Flask API will run on `http://localhost:5000`.

5. **Start the Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Access the search engine at `http://localhost:3000`.

## Architecture Note
The system purposely avoids AI embeddings or vector databases to remain cost-effective and lightweight, proving that a well-tuned BM25 implementation on a local corpus can yield excellent, instantaneous results.