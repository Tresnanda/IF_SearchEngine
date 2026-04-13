import os

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

from backend import _select_snippet_terms


def test_select_snippet_terms_prefers_corrected_query_terms():
    original = "machien lerning"
    corrected = "machine learning"

    terms = _select_snippet_terms(original_query=original, corrected_query=corrected)

    assert "machine" in terms
    assert "learning" in terms


def test_select_snippet_terms_falls_back_to_original_when_no_correction():
    terms = _select_snippet_terms(original_query="sistem informasi", corrected_query=None)

    assert "sistem" in terms
    assert "informasi" in terms
