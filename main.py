from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from config import FAILED_URLS_FILE, PROCESSED_IDS_FILE, Settings, job_id_from_url
from gemini_client import GeminiClient
from processed_store import append_processed_id, sync_processed_ids_from_output
from scraper import CrowdWorksScraper, JobDetail, JobListing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="クラウドワークスの新着求人から応募文を生成します。",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        metavar="URL",
        help="処理する求人詳細URLを直接指定（一覧ページは使わない）",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help=f"前回失敗したURL（{FAILED_URLS_FILE}）のみ再実行",
    )
    return parser.parse_args()


def ensure_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


RISK_LABELS = ("[正常]", "[注意]", "[危険]")


def risk_label_from_application_text(application_text: str | None) -> str | None:
    if not application_text:
        return None
    first_line = application_text.splitlines()[0].strip()
    for label in RISK_LABELS:
        if first_line == label or first_line.startswith(label):
            return label
    return None


def output_path(
    output_dir: Path,
    job_id: str,
    application_text: str | None = None,
) -> Path:
    label = risk_label_from_application_text(application_text)
    if label:
        return output_dir / f"{label}{job_id}.json"
    return output_dir / f"{job_id}.json"


def save_result(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_failed_urls(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_failed_urls(path: Path, urls: list[str]) -> None:
    path.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")


def build_success_payload(job: JobDetail, application_text: str) -> dict:
    return {
        "job_id": job.job_id,
        "url": job.url,
        "title": job.title,
        "status": "success",
        "application_text": application_text,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }


def build_failure_payload(
    job_url: str,
    error: str,
    title: str = "",
    job_id: str | None = None,
) -> dict:
    resolved_id = job_id or job_id_from_url(job_url)
    return {
        "job_id": resolved_id,
        "url": job_url,
        "title": title,
        "status": "failed",
        "application_text": None,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }


async def resolve_target_jobs(
    scraper: CrowdWorksScraper,
    settings: Settings,
    args: argparse.Namespace,
) -> list[JobListing]:
    if args.urls:
        return [JobListing(url=url, title="") for url in args.urls]

    if args.retry_failed:
        failed_urls = load_failed_urls(FAILED_URLS_FILE)
        if not failed_urls:
            print("再実行対象の失敗URLがありません。")
            return []
        return [JobListing(url=url, title="") for url in failed_urls]

    return await scraper.collect_all_new_jobs(settings.listing_urls)


async def process_job(
    scraper: CrowdWorksScraper,
    gemini: GeminiClient,
    settings: Settings,
    listing: JobListing,
    processed_ids: set[str],
) -> tuple[bool, str]:
    job_id = job_id_from_url(listing.url)
    job: JobDetail | None = None

    try:
        job = await scraper.fetch_job_detail(listing.url)
        if not job.description and not job.summary:
            raise ValueError("募集内容を取得できませんでした。")

        application_text = gemini.generate_application(job)
        out_path = output_path(settings.output_dir, job_id, application_text)
        save_result(out_path, build_success_payload(job, application_text))
        append_processed_id(PROCESSED_IDS_FILE, job_id, processed_ids)
        print(f"成功: {listing.url}")
        return True, listing.url
    except Exception as exc:
        error_message = str(exc)
        title = job.title if job else listing.title
        out_path = output_path(settings.output_dir, job_id)
        save_result(
            out_path,
            build_failure_payload(listing.url, error_message, title=title, job_id=job_id),
        )
        print(f"失敗: {listing.url} ({error_message})")
        return False, listing.url


async def run() -> None:
    args = parse_args()
    settings = Settings.from_env()
    ensure_output_dir(settings.output_dir)
    processed_ids = sync_processed_ids_from_output(settings.output_dir, PROCESSED_IDS_FILE)
    print(f"作業済みID: {len(processed_ids)} 件（{PROCESSED_IDS_FILE}）")

    gemini = GeminiClient(
        api_key=settings.google_api_key,
        model=settings.gemini_model,
        applicant=settings.applicant,
    )

    success_count = 0
    failure_count = 0
    skipped_count = 0
    failed_urls: list[str] = []

    async with CrowdWorksScraper(headless=False) as scraper:
        targets = await resolve_target_jobs(scraper, settings, args)
        if not targets:
            return

        print(f"\n処理対象: {len(targets)} 件\n")

        for listing in targets:
            job_id = job_id_from_url(listing.url)

            if job_id in processed_ids:
                skipped_count += 1
                print(f"スキップ（作業済み）: {listing.url}")
                continue

            ok, url = await process_job(
                scraper, gemini, settings, listing, processed_ids
            )
            if ok:
                success_count += 1
            else:
                failure_count += 1
                failed_urls.append(url)

    save_failed_urls(FAILED_URLS_FILE, failed_urls)

    print("\n" + "=" * 50)
    print("処理結果サマリー")
    print("=" * 50)
    print(f"成功: {success_count} 件")
    print(f"失敗: {failure_count} 件")
    print(f"スキップ（処理済み）: {skipped_count} 件")
    if failed_urls:
        print("\n失敗したURL:")
        for url in failed_urls:
            print(f"  - {url}")
        print(f"\n再実行コマンド:")
        print("  python main.py --retry-failed")
        print("  または")
        print(f"  python main.py --urls {' '.join(failed_urls)}")
    else:
        print("\n失敗したURLはありません。")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
