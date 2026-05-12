#!/usr/bin/env python3
"""
Crawler tuan thu (compliant) cho website danh ba doanh nghiep.

Muc tieu:
- Crawl 3 tang: danh muc -> phan trang -> trang chi tiet
- Su dung aiohttp + BeautifulSoup(lxml) de tang toc do parse
- Retry/backoff, timeout, checkpoint/resume
- Chuan hoa du lieu va upsert PostgreSQL theo MST

Luu y:
- Chi su dung khi website cho phep va ban co quyen truy cap du lieu.
- Khong duoc dung de ne CAPTCHA/chan bot/vi pham dieu khoan.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15",
]

DEFAULT_DETAIL_LINK_SELECTORS = [
    "a.company_name",
    "h2 a[href]",
    "a[href*='ma-so-thue']",
    "a[href*='cong-ty']",
]

DEFAULT_FIELD_SELECTORS: dict[str, list[str]] = {
    "ten_cong_ty": ["h1", "h2.company_name", ".company_name", ".title-company"],
    "dia_chi": [".info_contact .address", ".address", "[itemprop='address']", ".contact-address"],
    "nganh_nghe_kinh_doanh": [
        ".breadcrumb li:last-child",
        ".company-category a",
        ".business-field",
        ".industry",
    ],
    "sdt": [".info_contact .phone", ".phone", "[href^='tel:']"],
    "email": [".info_contact .email", ".email", "[href^='mailto:']"],
}

MST_REGEX = re.compile(r"\b\d{10}(?:-\d{3})?\b")
YEAR_REGEX = re.compile(r"\b(19|20)\d{2}\b")
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass
class CrawlConfig:
    max_pages_per_category: int
    concurrency: int
    request_delay_ms: int
    timeout_seconds: int
    max_retries: int
    backoff_seconds: float


def normalize_mst(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    m = MST_REGEX.search(v)
    if m:
        return m.group(0)
    digits = re.sub(r"\D", "", v)
    if len(digits) in {10, 13}:
        return digits if len(digits) == 10 else f"{digits[:10]}-{digits[10:]}"
    return None


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    if digits.startswith("84"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+84{digits[1:]}"
    return f"+{digits}"


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    m = EMAIL_REGEX.search(value)
    return m.group(0).lower() if m else None


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" ,:\n\t")
    return cleaned or None


def normalize_address(value: str | None) -> str | None:
    return normalize_text(value)


def read_non_empty_lines(path: Path | None) -> list[str]:
    if not path:
        return []
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_page_url(category_url: str, page_number: int) -> str:
    if "{page}" in category_url:
        return category_url.replace("{page}", str(page_number))
    parsed = urlparse(category_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_number)
    new_query = urlencode(query)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def is_same_host(base_url: str, target_url: str) -> bool:
    a = urlparse(base_url).netloc.lower()
    b = urlparse(target_url).netloc.lower()
    return a == b


def extract_text_by_selectors(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        if node.name == "a" and node.get("href", "").startswith("mailto:"):
            return node.get("href", "").replace("mailto:", "").strip()
        if node.name == "a" and node.get("href", "").startswith("tel:"):
            return node.get("href", "").replace("tel:", "").strip()
        txt = node.get_text(" ", strip=True)
        if txt:
            return txt
    return None


def extract_mst_from_page_text(soup: BeautifulSoup) -> str | None:
    text = soup.get_text(" ", strip=True)
    return normalize_mst(text)


def extract_year_from_page_text(soup: BeautifulSoup) -> int | None:
    text = soup.get_text(" ", strip=True)
    m = YEAR_REGEX.search(text)
    if not m:
        return None
    year = int(m.group(0))
    if 1900 <= year <= datetime.now().year:
        return year
    return None


def parse_detail_page(
    html: str,
    url: str,
    field_selectors: dict[str, list[str]],
) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    company_name = normalize_text(extract_text_by_selectors(soup, field_selectors["ten_cong_ty"]))
    address = normalize_address(extract_text_by_selectors(soup, field_selectors["dia_chi"]))
    industry = normalize_text(extract_text_by_selectors(soup, field_selectors["nganh_nghe_kinh_doanh"]))
    phone = normalize_phone(extract_text_by_selectors(soup, field_selectors["sdt"]))
    email = normalize_email(extract_text_by_selectors(soup, field_selectors["email"]))
    mst = extract_mst_from_page_text(soup)
    established_year = extract_year_from_page_text(soup)
    return {
        "mst": mst,
        "ten_cong_ty": company_name,
        "nam_thanh_lap": established_year,
        "sdt": phone,
        "email": email,
        "dia_chi": address,
        "nganh_nghe_kinh_doanh": industry,
        "nguon_url": url,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_detail_links(
    html: str,
    listing_url: str,
    base_url: str,
    selectors: list[str],
) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: set[str] = set()
    for selector in selectors:
        for node in soup.select(selector):
            href = node.get("href")
            if not href:
                continue
            full = urljoin(listing_url, href)
            if is_same_host(base_url, full):
                links.add(full)
    return sorted(links)


class PgWriter:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._conn = None

    def __enter__(self) -> "PgWriter":
        import psycopg2

        self._conn = psycopg2.connect(self.dsn)
        self._conn.autocommit = False
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if not self._conn:
            return
        if exc_type:
            self._conn.rollback()
        self._conn.close()
        self._conn = None

    def upsert_many(self, rows: list[dict[str, Any]]) -> int:
        if not rows or not self._conn:
            return 0
        from psycopg2.extras import execute_values

        sql = """
        INSERT INTO dim_company (
          mst, ten_cong_ty, nam_thanh_lap, sdt, email, dia_chi,
          nganh_nghe_kinh_doanh, nguon_url, updated_at
        )
        VALUES %s
        ON CONFLICT (mst) DO UPDATE SET
          ten_cong_ty = EXCLUDED.ten_cong_ty,
          nam_thanh_lap = COALESCE(EXCLUDED.nam_thanh_lap, dim_company.nam_thanh_lap),
          sdt = COALESCE(EXCLUDED.sdt, dim_company.sdt),
          email = COALESCE(EXCLUDED.email, dim_company.email),
          dia_chi = COALESCE(EXCLUDED.dia_chi, dim_company.dia_chi),
          nganh_nghe_kinh_doanh = COALESCE(EXCLUDED.nganh_nghe_kinh_doanh, dim_company.nganh_nghe_kinh_doanh),
          nguon_url = EXCLUDED.nguon_url,
          updated_at = EXCLUDED.updated_at;
        """
        values = [
            (
                r.get("mst"),
                r.get("ten_cong_ty"),
                r.get("nam_thanh_lap"),
                r.get("sdt"),
                r.get("email"),
                r.get("dia_chi"),
                r.get("nganh_nghe_kinh_doanh"),
                r.get("nguon_url"),
                r.get("updated_at"),
            )
            for r in rows
            if r.get("mst")
        ]
        if not values:
            return 0
        with self._conn.cursor() as cur:
            execute_values(cur, sql, values, page_size=500)
        self._conn.commit()
        return len(values)


class JsonlWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fp = self.path.open("a", encoding="utf-8")

    def close(self) -> None:
        self.fp.close()

    def write_many(self, rows: list[dict[str, Any]]) -> None:
        for r in rows:
            self.fp.write(json.dumps(r, ensure_ascii=False) + "\n")
        self.fp.flush()


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"category_next_page": {}, "seen_detail_urls": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    cfg: CrawlConfig,
    semaphore: asyncio.Semaphore,
    user_agents: list[str],
) -> tuple[int, str]:
    attempt = 0
    while True:
        try:
            async with semaphore:
                await asyncio.sleep(cfg.request_delay_ms / 1000.0)
                headers = {"User-Agent": random.choice(user_agents), "Accept": "text/html,*/*;q=0.8"}
                timeout = aiohttp.ClientTimeout(total=cfg.timeout_seconds)
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    text = await resp.text(errors="ignore")
                    if resp.status in {429, 500, 502, 503, 504} and attempt < cfg.max_retries:
                        await asyncio.sleep(cfg.backoff_seconds * (2**attempt) + random.random() * 0.5)
                        attempt += 1
                        continue
                    return resp.status, text
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt >= cfg.max_retries:
                return 0, ""
            await asyncio.sleep(cfg.backoff_seconds * (2**attempt) + random.random() * 0.5)
            attempt += 1


async def process_detail_url(
    session: aiohttp.ClientSession,
    url: str,
    cfg: CrawlConfig,
    semaphore: asyncio.Semaphore,
    user_agents: list[str],
    selectors: dict[str, list[str]],
) -> tuple[str, dict[str, Any] | None]:
    status, html = await fetch_text(session, url, cfg, semaphore, user_agents)
    if status != 200 or not html:
        return url, None
    try:
        row = parse_detail_page(html, url, selectors)
        if not row.get("mst"):
            return url, None
        return url, row
    except Exception:
        return url, None


async def run_crawl(args: argparse.Namespace) -> dict[str, Any]:
    category_urls = read_non_empty_lines(args.category_urls)
    if not category_urls:
        raise RuntimeError("File category_urls rong. Hay dien danh sach URL danh muc.")

    user_agents = read_non_empty_lines(args.user_agent_file) or DEFAULT_USER_AGENTS
    detail_selectors = (
        json.loads(args.detail_link_selectors) if args.detail_link_selectors else DEFAULT_DETAIL_LINK_SELECTORS
    )
    field_selectors = DEFAULT_FIELD_SELECTORS.copy()
    if args.field_selectors_json:
        override = json.loads(args.field_selectors_json)
        for key, value in override.items():
            if isinstance(value, list) and value:
                field_selectors[key] = value

    cfg = CrawlConfig(
        max_pages_per_category=args.max_pages_per_category,
        concurrency=args.concurrency,
        request_delay_ms=args.request_delay_ms,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        backoff_seconds=args.backoff_seconds,
    )

    checkpoint = load_checkpoint(args.checkpoint)
    seen_detail_urls = set(checkpoint.get("seen_detail_urls", []))
    category_next_page = dict(checkpoint.get("category_next_page", {}))
    stats: dict[str, int] = {"listing_ok": 0, "detail_ok": 0, "detail_fail": 0}

    writer = JsonlWriter(args.output)
    pg_dsn = args.pg_dsn or os.environ.get("PG_DSN", "")
    pg_writer = PgWriter(pg_dsn) if pg_dsn else None
    if pg_writer:
        pg_writer.__enter__()

    semaphore = asyncio.Semaphore(cfg.concurrency)
    connector = aiohttp.TCPConnector(limit=max(cfg.concurrency * 2, 20))

    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            for category_url in category_urls:
                start_page = int(category_next_page.get(category_url, 1))
                empty_streak = 0
                for page in range(start_page, cfg.max_pages_per_category + 1):
                    listing_url = build_page_url(category_url, page)
                    status, listing_html = await fetch_text(session, listing_url, cfg, semaphore, user_agents)
                    if status != 200 or not listing_html:
                        empty_streak += 1
                        if empty_streak >= 2:
                            break
                        continue

                    stats["listing_ok"] += 1
                    detail_urls = parse_detail_links(
                        html=listing_html,
                        listing_url=listing_url,
                        base_url=args.base_url,
                        selectors=detail_selectors,
                    )
                    new_urls = [u for u in detail_urls if u not in seen_detail_urls]

                    if not new_urls:
                        empty_streak += 1
                        if empty_streak >= 2:
                            break
                    else:
                        empty_streak = 0

                    tasks = [
                        process_detail_url(
                            session=session,
                            url=u,
                            cfg=cfg,
                            semaphore=semaphore,
                            user_agents=user_agents,
                            selectors=field_selectors,
                        )
                        for u in new_urls
                    ]
                    results = await asyncio.gather(*tasks)
                    rows: list[dict[str, Any]] = []
                    for url, row in results:
                        seen_detail_urls.add(url)
                        if row is None:
                            stats["detail_fail"] += 1
                        else:
                            stats["detail_ok"] += 1
                            rows.append(row)

                    if rows:
                        writer.write_many(rows)
                        if pg_writer:
                            pg_writer.upsert_many(rows)

                    category_next_page[category_url] = page + 1
                    checkpoint["category_next_page"] = category_next_page
                    checkpoint["seen_detail_urls"] = sorted(seen_detail_urls)
                    save_checkpoint(args.checkpoint, checkpoint)
    finally:
        writer.close()
        if pg_writer:
            pg_writer.__exit__(None, None, None)

    return {
        "output_file": str(args.output),
        "checkpoint": str(args.checkpoint),
        "categories": len(category_urls),
        "stats": stats,
        "seen_detail_urls": len(seen_detail_urls),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compliant crawler danh ba doanh nghiep.")
    p.add_argument("--base-url", type=str, required=True, help="VD: https://trangvangvietnam.com")
    p.add_argument(
        "--category-urls",
        type=Path,
        required=True,
        help="File txt chua URL danh muc. Co the dung mau {page} trong URL.",
    )
    p.add_argument("--output", type=Path, default=Path("out/trangvang_companies.jsonl"))
    p.add_argument("--checkpoint", type=Path, default=Path("out/checkpoints/trangvang_checkpoint.json"))
    p.add_argument("--max-pages-per-category", type=int, default=500)
    p.add_argument("--concurrency", type=int, default=15)
    p.add_argument("--request-delay-ms", type=int, default=120)
    p.add_argument("--timeout-seconds", type=int, default=25)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--backoff-seconds", type=float, default=1.5)
    p.add_argument("--user-agent-file", type=Path, default=None)
    p.add_argument("--detail-link-selectors", type=str, default="")
    p.add_argument("--field-selectors-json", type=str, default="")
    p.add_argument("--pg-dsn", type=str, default="")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.concurrency < 1 or args.concurrency > 100:
        print("concurrency nen trong [1, 100]", file=sys.stderr)
        raise SystemExit(2)
    result = asyncio.run(run_crawl(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
