import os

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

from backend import _expand_query_terms_for_recall


def test_expand_query_terms_adds_synonyms_without_duplicates():
    expanded = _expand_query_terms_for_recall(["sentimen", "keamanan"])

    assert "sentiment" in expanded
    assert "opini" in expanded
    assert "security" in expanded
    assert len(expanded) == len(set(expanded))


def test_expand_query_terms_handles_empty_input():
    assert _expand_query_terms_for_recall([]) == []
