import os

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

from backend import _detect_domain_from_title, _extract_year_from_title


def test_extract_year_from_title():
    assert _extract_year_from_title("Analisis Sentimen 2024 pada Twitter") == "2024"
    assert _extract_year_from_title("Judul Tanpa Tahun") is None


def test_detect_domain_from_title_security():
    assert _detect_domain_from_title("Implementasi RSA untuk Keamanan Data") == "security"


def test_detect_domain_from_title_default_other():
    assert _detect_domain_from_title("Studi Sistem Informasi Akademik") == "other"
