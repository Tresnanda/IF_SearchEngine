import os

os.environ.setdefault("ADMIN_INTERNAL_TOKEN", "dev-admin-token")

from backend import _extract_gdrive_file_id, _normalize_gdrive_url


def test_extract_gdrive_file_id_from_file_path_url():
    url = "https://drive.google.com/file/d/1AbCdEfGhIjKlMn/view?usp=sharing"
    assert _extract_gdrive_file_id(url) == "1AbCdEfGhIjKlMn"


def test_extract_gdrive_file_id_from_query_url():
    url = "https://drive.google.com/open?id=1ZXCVbnm12345"
    assert _extract_gdrive_file_id(url) == "1ZXCVbnm12345"


def test_normalize_gdrive_url():
    url = "https://drive.google.com/file/d/1AbCdEfGhIjKlMn/view?usp=sharing"
    assert _normalize_gdrive_url(url) == "https://drive.google.com/file/d/1AbCdEfGhIjKlMn/view"
