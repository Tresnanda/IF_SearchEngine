from pathlib import Path
import random

from incremental_indexer import IncrementalIndexBuilder


def test_incremental_pipeline_stats_on_real_dataset_snapshot():
    dataset = Path("new_dataset")
    if not dataset.exists():
        return

    files = [p for p in dataset.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".doc"}]
    files = sorted(files)
    if len(files) > 40:
        random.seed(42)
        selected = random.sample(files, 40)
        subset_dir = Path("data/index/test_subset_dataset")
        if subset_dir.exists():
            for child in subset_dir.iterdir():
                child.unlink()
        else:
            subset_dir.mkdir(parents=True, exist_ok=True)

        for source in selected:
            target = subset_dir / source.name
            target.write_bytes(source.read_bytes())
        dataset = subset_dir

    cache_path = Path("data/index/test_document_cache.json")
    if cache_path.exists():
        cache_path.unlink()

    builder = IncrementalIndexBuilder(str(dataset), str(cache_path))
    records, stats, cache = builder.collect_records()

    assert len(records) == len(cache)
    assert stats["updated"] == 0
    assert stats["reused"] == 0
    assert stats["created"] == len(records)
