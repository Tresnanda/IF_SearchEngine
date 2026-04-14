import os

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

from backend import _detect_domain_from_title, _extract_year_from_title, _resolve_result_year


def test_extract_year_from_title():
    assert _extract_year_from_title("Analisis Sentimen 2024 pada Twitter") == "2024"
    assert _extract_year_from_title("Judul Tanpa Tahun") is None


def test_detect_domain_from_title_security():
    assert _detect_domain_from_title("Implementasi RSA untuk Keamanan Data") == "security"


def test_detect_domain_from_title_default_other():
    assert _detect_domain_from_title("Studi Sistem Informasi Akademik") == "other"


def test_resolve_result_year_prefers_metadata_year():
    assert _resolve_result_year("Judul Tanpa Tahun", {"year": "2022"}) == "2022"


def test_resolve_result_year_falls_back_to_title_year():
    assert _resolve_result_year("Analisis Data 2021", {}) == "2021"


def test_resolve_result_year_uses_document_path_when_title_missing(monkeypatch):
    monkeypatch.setattr("backend._extract_year_from_document", lambda _path: "2020")
    assert _resolve_result_year("Judul Tanpa Tahun", {"path": "new_dataset/sample.docx"}) == "2020"
