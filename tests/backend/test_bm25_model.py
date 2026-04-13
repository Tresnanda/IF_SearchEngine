from collections import defaultdict

from vsm import BM25Model


class FakeIndex:
    def __init__(self):
        self.index = {"machine": True, "learning": True}
        self.df = {"machine": 2, "learning": 1}
        self.num_docs = 2
        self.doc_lengths = {1: 5, 2: 8}
        self.avg_doc_length = 6.5
        self.doc_metadata = {
            1: {"title": "Machine Learning Basics"},
            2: {"title": "Machine Systems"},
        }
        self._postings = {
            "machine": [(1, 3), (2, 2)],
            "learning": [(1, 2)],
        }

    def get_postings(self, term):
        return self._postings.get(term, [])


def test_bm25_search_returns_ranked_results():
    model = BM25Model(FakeIndex())

    results = model.search("machine learning", top_k=5)

    assert len(results) == 2
    assert results[0][0] == 1
    assert results[0][1] > results[1][1]


def test_bm25_repeated_term_increases_score_weight():
    model = BM25Model(FakeIndex())

    once_score = model.search("machine", top_k=1)[0][1]
    repeated_score = model.search("machine machine", top_k=1)[0][1]

    assert repeated_score > once_score
