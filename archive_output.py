from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR

KEEP_FILES = {"processed_ids.txt", "failed_urls.txt"}


def archive_json_files(output_dir: Path, timestamp: datetime | None = None) -> Path | None:
    json_files = sorted(output_dir.glob("*.json"))
    if not json_files:
        return None

    when = timestamp or datetime.now()
    archive_dir = output_dir / when.strftime("%Y%m%d_%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=False)

    for json_file in json_files:
        target = archive_dir / json_file.name
        json_file.rename(target)

    return archive_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="output/*.json を実行日時フォルダへ移動します。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"対象ディレクトリ（既定: {OUTPUT_DIR}）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_dir = archive_json_files(output_dir)
    if archive_dir is None:
        print(f"{output_dir} に移動対象の JSON ファイルがないためスキップしました。")
        return

    moved_count = len(list(archive_dir.glob("*.json")))
    print(f"{moved_count} 件を移動しました: {archive_dir}")


if __name__ == "__main__":
    main()
