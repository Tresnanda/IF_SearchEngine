from indexer import DocumentCorpusIndexer
import os

CONTENT_INDEX_PATH = "content_index.pkl"
TITLE_INDEX_PATH = "title_index.pkl"

def test_indexer():
    print("Building full index on currently downloaded files...")
    indexer = DocumentCorpusIndexer('new_dataset')
    indexer.build_index()
    print("Saving index to disk...")
    indexer.save_index(CONTENT_INDEX_PATH, TITLE_INDEX_PATH)
    print("Done! The search engine is now ready to use.")
    
if __name__ == "__main__":
    test_indexer()
