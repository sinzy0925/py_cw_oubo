from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from playwright.async_api import Browser, Page, async_playwright

from config import PAGE_WAIT_MS, REQUEST_INTERVAL_SEC

JOB_URL_PATTERN = re.compile(r"/public/jobs/(\d+)$")

EXTRACT_NEW_JOBS_JS = """
() => {
  const results = [];
  const cards = document.querySelectorAll('[class*="_root_"]');
  for (const card of cards) {
    const ribbon = card.querySelector('[class*="_ribbon_"]');
    const badge = ribbon?.textContent?.trim() || '';
    if (badge !== '新着') continue;

    const links = [...card.querySelectorAll('a[href*="/public/jobs/"]')];
    const jobLink = links.find(a => /\\/public\\/jobs\\/\\d+$/.test(a.pathname));
    if (!jobLink) continue;

    results.push({
      url: jobLink.href,
      title: jobLink.textContent.trim(),
    });
  }
  return results;
}
"""

EXTRACT_JOB_DETAIL_JS = """
() => {
  const header = document.querySelector('.job_offer_detail_header');
  const title = header?.innerText?.split('\\n')[0]?.trim() || document.title.split('|')[0].trim();

  const h2s = [...document.querySelectorAll('h2')];
  const summaryH2 = h2s.find(h => h.textContent.trim() === '仕事の概要');
  const detailH2 = h2s.find(h => h.textContent.trim() === '仕事の詳細');

  const summarySection = summaryH2?.closest('.cw-section') || summaryH2?.parentElement;
  const summary = summarySection?.innerText?.trim() || '';

  const detailTable = detailH2?.nextElementSibling;
  const description = detailTable?.innerText?.trim() || '';

  return { title, summary, description };
}
"""


@dataclass
class JobListing:
    url: str
    title: str


@dataclass
class JobDetail:
    url: str
    job_id: str
    title: str
    summary: str
    description: str

    @property
    def full_content(self) -> str:
        parts = [f"【タイトル】\n{self.title}"]
        if self.summary:
            parts.append(f"【仕事の概要】\n{self.summary}")
        if self.description:
            parts.append(f"【仕事の詳細（募集内容）】\n{self.description}")
        return "\n\n".join(parts)


class CrowdWorksScraper:
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self._browser: Browser | None = None
        self._playwright = None

    async def __aenter__(self) -> CrowdWorksScraper:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _wait_for_render(self, page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(PAGE_WAIT_MS)

    async def _new_page(self) -> Page:
        if not self._browser:
            raise RuntimeError("ブラウザが起動していません。")
        page = await self._browser.new_page()
        return page

    async def collect_new_jobs_from_listing(self, listing_url: str) -> list[JobListing]:
        page = await self._new_page()
        try:
            print(f"一覧ページを取得: {listing_url}")
            await page.goto(listing_url, wait_until="domcontentloaded")
            await self._wait_for_render(page)
            raw_jobs = await page.evaluate(EXTRACT_NEW_JOBS_JS)
            jobs = [JobListing(url=j["url"], title=j["title"]) for j in raw_jobs]
            print(f"  → 新着 {len(jobs)} 件")
            return jobs
        finally:
            await page.close()
            await asyncio.sleep(REQUEST_INTERVAL_SEC)

    async def collect_all_new_jobs(self, listing_urls: list[str]) -> list[JobListing]:
        seen: set[str] = set()
        all_jobs: list[JobListing] = []
        for url in listing_urls:
            jobs = await self.collect_new_jobs_from_listing(url)
            for job in jobs:
                if job.url not in seen:
                    seen.add(job.url)
                    all_jobs.append(job)
        return all_jobs

    async def fetch_job_detail(self, job_url: str) -> JobDetail:
        match = JOB_URL_PATTERN.search(job_url)
        if not match:
            raise ValueError(f"無効な求人URL: {job_url}")

        page = await self._new_page()
        try:
            print(f"詳細ページを取得: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._wait_for_render(page)
            data = await page.evaluate(EXTRACT_JOB_DETAIL_JS)
            return JobDetail(
                url=job_url,
                job_id=match.group(1),
                title=data.get("title", ""),
                summary=data.get("summary", ""),
                description=data.get("description", ""),
            )
        finally:
            await page.close()
            await asyncio.sleep(REQUEST_INTERVAL_SEC)
