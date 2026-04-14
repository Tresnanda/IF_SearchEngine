from pathlib import Path
import zipfile

from indexer import DocumentCorpusIndexer


def test_extract_core_sections_clamps_when_end_marker_missing():
    indexer = DocumentCorpusIndexer("new_dataset")
    long_tail = " noise" * 50000
    text = (
        "ABSTRAK ini ringkasan penelitian kata kunci: sentimen "
        "BAB III METODOLOGI PENELITIAN langkah langkah eksperimen "
        "BAB V KESIMPULAN hasil penelitian "
        + long_tail
    )

    combined = indexer._extract_core_sections_from_text(text)

    assert len(combined) < 20000
    assert "ABSTRAK" not in combined.upper()


def test_extract_text_from_docx_uses_zip_fallback_for_broken_docx(tmp_path: Path):
    broken_docx = tmp_path / "broken.docx"
    with zipfile.ZipFile(broken_docx, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<?xml version='1.0' encoding='UTF-8'?><w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>Abstrak penelitian sistem informasi</w:t></w:r></w:p></w:body></w:document>",
        )

    indexer = DocumentCorpusIndexer("new_dataset")
    extracted = indexer.extract_text_from_docx(str(broken_docx))

    assert "Abstrak penelitian sistem informasi" in extracted
