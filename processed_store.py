from __future__ import annotations

import json
from pathlib import Path


def load_processed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def append_processed_id(path: Path, job_id: str, known_ids: set[str]) -> None:
    if job_id in known_ids:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(f"{job_id}\n")
    known_ids.add(job_id)


def sync_processed_ids_from_output(output_dir: Path, processed_file: Path) -> set[str]:
    """output/*.json の success 件から processed_ids.txt を補完する。"""
    processed_ids = load_processed_ids(processed_file)

    for json_file in output_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("status") != "success":
            continue
        job_id = str(data.get("job_id", "")).strip()
        if job_id:
            append_processed_id(processed_file, job_id, processed_ids)

    return processed_ids
