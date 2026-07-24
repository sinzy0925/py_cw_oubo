from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("output")
FAILED_URLS_FILE = OUTPUT_DIR / "failed_urls.txt"
PROCESSED_IDS_FILE = OUTPUT_DIR / "processed_ids.txt"
PAGE_WAIT_MS = 1000
REQUEST_INTERVAL_SEC = 2


@dataclass(frozen=True)
class ApplicantProfile:
    name: str
    job: str
    age: str
    gender: str
    address: str
    pc_skill: str

    def to_prompt_block(self) -> str:
        return (
            f"名前：{self.name}\n"
            f"仕事：{self.job}\n"
            f"年齢：{self.age}\n"
            f"性別：{self.gender}\n"
            f"住所：{self.address}\n"
            f"パソコン作業：{self.pc_skill}"
        )


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    gemini_model: str
    applicant: ApplicantProfile
    listing_urls: list[str]
    output_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY が .env に設定されていません。")

        listing_raw = os.getenv("LISTING_URLS", "").strip()
        listing_urls = [u.strip() for u in listing_raw.split(",") if u.strip()]
        if not listing_urls:
            raise ValueError("LISTING_URLS が .env に設定されていません。")

        applicant = ApplicantProfile(
            name=os.getenv("APPLICANT_NAME", "").strip(),
            job=os.getenv("APPLICANT_JOB", "").strip(),
            age=os.getenv("APPLICANT_AGE", "").strip(),
            gender=os.getenv("APPLICANT_GENDER", "").strip(),
            address=os.getenv("APPLICANT_ADDRESS", "").strip(),
            pc_skill=os.getenv("APPLICANT_PC_SKILL", "").strip(),
        )

        return cls(
            google_api_key=api_key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
            applicant=applicant,
            listing_urls=listing_urls,
            output_dir=OUTPUT_DIR,
        )


def job_id_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]
