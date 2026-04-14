from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple
from tempfile import NamedTemporaryFile

import requests

from preprocessor import IndonesianPreprocessor
from indexer import DocumentCorpusIndexer
from invertedindex import InvertedIndex
from collections import Counter, defaultdict


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}
CACHE_EXTRACTOR_VERSION = 2


@dataclass
class CacheEntry:
    file_hash: str
    mtime: float
    size: int
    title: str
    content_tokens: List[str]
    title_tokens: List[str]
    updated_at: str
    source_type: str = "local"
    source_url: str | None = None
    extractor_version: int = 1
    year: str | None = None


class IncrementalIndexBuilder:
    def __init__(self, dataset_dir: str, cache_path: str, sources: List[dict] | None = None):
        self.dataset_dir = Path(dataset_dir)
        self.cache_path = Path(cache_path)
        self.preprocessor = IndonesianPreprocessor()
        self.indexer = DocumentCorpusIndexer(str(self.dataset_dir))
        self.sources = sources or []

    def load_cache(self) -> Dict[str, CacheEntry]:
        if not self.cache_path.exists():
            return {}
        payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        return {name: CacheEntry(**entry) for name, entry in payload.items()}

    def save_cache(self, cache: Dict[str, CacheEntry]) -> None:
        payload = {name: entry.__dict__ for name, entry in cache.items()}
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def collect_records(self) -> Tuple[List[dict], dict, Dict[str, CacheEntry]]:
        existing_cache = self.load_cache()
        updated_cache: Dict[str, CacheEntry] = {}
        stats = {"created": 0, "updated": 0, "reused": 0, "deleted": 0}
        records: List[dict] = []

        source_items = self._collect_sources()

        for source in source_items:
            filename = source["filename"]
            source_type = source["source_type"]
            source_url = source.get("source_url")
            source_title = source.get("title") or self.indexer.extract_title(filename)
            cache_entry = existing_cache.get(filename)

            if source_type == "local":
                file_path = Path(source["path"])
                file_hash = self._hash_file(file_path)
                stat = file_path.stat()
            else:
                file_hash = hashlib.sha256((source_url or "").encode("utf-8")).hexdigest()
                stat = type("Stat", (), {"st_size": len(source_url or ""), "st_mtime": 0.0})()

            if (
                cache_entry
                and cache_entry.file_hash == file_hash
                and cache_entry.size == stat.st_size
                and cache_entry.source_type == source_type
                and cache_entry.source_url == source_url
                and cache_entry.extractor_version == CACHE_EXTRACTOR_VERSION
            ):
                entry = cache_entry
                stats["reused"] += 1
            else:
                resolved_title, resolved_year, content_tokens, title_tokens = self._extract_record_payload(
                    source,
                    source_title,
                )
                now = datetime.now(timezone.utc).isoformat()
                entry = CacheEntry(
                    file_hash=file_hash,
                    mtime=stat.st_mtime,
                    size=stat.st_size,
                    title=resolved_title,
                    content_tokens=content_tokens,
                    title_tokens=title_tokens,
                    updated_at=now,
                    source_type=source_type,
                    source_url=source_url,
                    extractor_version=CACHE_EXTRACTOR_VERSION,
                    year=resolved_year,
                )
                if cache_entry is None:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

            updated_cache[filename] = entry
            records.append(
                {
                    "filename": filename,
                    "path": source.get("path", ""),
                    "title": entry.title,
                    "year": entry.year,
                    "content_tokens": entry.content_tokens,
                    "title_tokens": entry.title_tokens,
                    "source_type": source_type,
                    "source_url": source_url,
                }
            )

        previous_files = set(existing_cache.keys())
        current_files = set(updated_cache.keys())
        stats["deleted"] = len(previous_files - current_files)

        return records, stats, updated_cache

    def _extract_record_payload(self, source: dict, source_title: str) -> Tuple[str, str | None, List[str], List[str]]:
        extracted = self._extract_tokens_for_source(source)
        if len(extracted) == 4:
            resolved_title, resolved_year, content_tokens, title_tokens = extracted
            if not resolved_title:
                resolved_title = source_title
            return resolved_title, resolved_year, content_tokens, title_tokens

        if len(extracted) == 3:
            resolved_title, content_tokens, title_tokens = extracted
            if not resolved_title:
                resolved_title = source_title
            return resolved_title, None, content_tokens, title_tokens

        content_tokens, title_tokens = extracted
        return source_title, None, content_tokens, title_tokens

    def _extract_tokens_for_document(self, file_path: Path, filename: str) -> Tuple[str, str | None, List[str], List[str]]:
        lower_suffix = file_path.suffix.lower()
        if lower_suffix == ".pdf":
            first_page_text = self.indexer.extract_first_page_text_from_pdf(str(file_path))
            title = self.indexer._derive_title_from_text(first_page_text, self.indexer.extract_title(filename))
            year = self.indexer._derive_year_from_text(first_page_text)
            content_text = self.indexer.extract_core_sections(str(file_path))
        elif lower_suffix == ".docx":
            full_text = self.indexer.extract_text_from_docx(str(file_path))
            title = self.indexer._derive_title_from_text(full_text, self.indexer.extract_title(filename))
            year = self.indexer._derive_year_from_text(full_text)
            abstract = self.indexer._extract_abstract_section(full_text)
            content_text = abstract if abstract else full_text[:5000]
        else:
            title = self.indexer.extract_title(filename)
            year = None
            full_text = self.indexer.extract_text_from_docx(str(file_path))
            abstract = self.indexer._extract_abstract_section(full_text)
            content_text = abstract if abstract else full_text[:5000]

        content_tokens = self.preprocessor.preprocess(content_text)
        title_tokens = self.preprocessor.preprocess(title)
        return title, year, content_tokens, title_tokens

    def _extract_tokens_for_source(self, source: dict) -> Tuple[List[str], List[str]]:
        source_type = source["source_type"]
        filename = source["filename"]
        if source_type == "local":
            return self._extract_tokens_for_document(Path(source["path"]), filename)

        source_url = source.get("source_url") or ""
        with NamedTemporaryFile(delete=True, suffix=Path(filename).suffix.lower() or ".pdf") as handle:
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()
            handle.write(response.content)
            handle.flush()
            return self._extract_tokens_for_document(Path(handle.name), filename)

    def _collect_sources(self) -> List[dict]:
        if self.sources:
            return sorted(self.sources, key=lambda item: item["filename"])

        return [
            {
                "filename": p.name,
                "path": str(p),
                "title": self.indexer.extract_title(p.name),
                "source_type": "local",
                "source_url": None,
            }
            for p in sorted(self.dataset_dir.iterdir())
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

    def _hash_file(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()


def build_indices_from_records(records: List[dict], content_index_path: str, title_index_path: str) -> None:
    content_index = InvertedIndex()
    title_index = InvertedIndex()
    temp_content = defaultdict(list)
    temp_title = defaultdict(list)

    for doc_id, record in enumerate(records):
        filename = record["filename"]
        title = record["title"]
        file_path = record.get("path", "")
        content_tokens = record.get("content_tokens", [])
        title_tokens = record.get("title_tokens", [])

        metadata = {
            "filename": filename,
            "title": title,
            "path": file_path,
            "year": record.get("year"),
            "source_type": record.get("source_type", "local"),
            "source_url": record.get("source_url"),
        }
        content_index.doc_metadata[doc_id] = metadata
        title_index.doc_metadata[doc_id] = metadata

        if content_tokens:
            content_freqs = Counter(content_tokens)
            content_index.doc_lengths[doc_id] = len(content_tokens)
            for term, freq in content_freqs.items():
                temp_content[term].append((doc_id, freq))

        if title_tokens:
            title_freqs = Counter(title_tokens)
            title_index.doc_lengths[doc_id] = len(title_tokens)
            for term, freq in title_freqs.items():
                temp_title[term].append((doc_id, freq))

    content_index.num_docs = len(records)
    title_index.num_docs = len(records)

    for term, postings in temp_content.items():
        content_index.index[term] = postings
        content_index.df[term] = len(postings)

    for term, postings in temp_title.items():
        title_index.index[term] = postings
        title_index.df[term] = len(postings)

    if content_index.doc_lengths:
        content_index.avg_doc_length = sum(content_index.doc_lengths.values()) / len(content_index.doc_lengths)
    if title_index.doc_lengths:
        title_index.avg_doc_length = sum(title_index.doc_lengths.values()) / len(title_index.doc_lengths)

    content_index.build_tfidf_doc_vectors()
    title_index.build_tfidf_doc_vectors()
    content_index.compress_index()
    title_index.compress_index()

    Path(content_index_path).write_bytes(b"")
    Path(title_index_path).write_bytes(b"")

    import pickle

    with open(content_index_path, "wb") as content_file:
        pickle.dump(content_index, content_file)

    with open(title_index_path, "wb") as title_file:
        pickle.dump(title_index, title_file)
