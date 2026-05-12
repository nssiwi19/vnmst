#!/usr/bin/env python3
"""
Build real MST seed list from public company pages on masothue.com.

Approach:
- Start from homepage (or provided URLs)
- Crawl company detail links with bounded BFS
- Extract MST from URLs and page text
- Merge optional local seed files
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urljoin, urlparse

import requests

MST_RE = re.compile(r"\b(\d{10}(?:-\d{3})?)\b")
COMPANY_LINK_RE = re.compile(r'href=["\'](/(\d{10}(?:-\d{3})?)-[^"\']+)["\']', re.IGNORECASE)
DEFAULT_START_URLS = ["https://masothue.com/"]
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15",
]


def normalize_mst(text: str) -> str | None:
    raw = text.strip()
    if re.fullmatch(r"\d{10}", raw):
        return raw
    if re.fullmatch(r"\d{10}-\d{3}", raw):
        return raw
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return digits
    if len(digits) == 13:
        return f"{digits[:10]}-{digits[10:]}"
    return None


def extract_msts_from_text(text: str) -> set[str]:
    out: set[str] = set()
    for match in MST_RE.findall(text):
        norm = normalize_mst(match)
        if norm:
            out.add(norm)
    return out


def should_follow_listing(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"masothue.com", "www.masothue.com"}:
        return False
    path = parsed.path.lower()
    query = parsed.query.lower()
    if path.startswith("/search/"):
        return True
    if "tra-cuu-ma-so-thue" in path:
        return True
    if "page=" in query:
        return True
    return False


def extract_company_links(base_url: str, html: str) -> tuple[set[str], set[str], set[str]]:
    company_links: set[str] = set()
    listing_links: set[str] = set()
    msts: set[str] = set()
    for href, mst_raw in COMPANY_LINK_RE.findall(html):
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        company_links.add(clean)
        norm = normalize_mst(mst_raw)
        if norm:
            msts.add(norm)

    for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
        if href.startswith(("mailto:", "javascript:", "#")):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean += f"?{parsed.query}"
        if should_follow_listing(clean):
            listing_links.add(clean)
    return company_links, listing_links, msts


def fetch_html_sync(url: str, min_delay_ms: int, max_delay_ms: int) -> tuple[str, str | None, int]:
    try:
        delay = random.uniform(min_delay_ms / 1000.0, max_delay_ms / 1000.0)
        if delay > 0:
            import time

            time.sleep(delay)
        headers = {"User-Agent": random.choice(DEFAULT_USER_AGENTS), "Accept": "text/html,*/*;q=0.8"}
        resp = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
        if resp.status_code != 200:
            return url, None, resp.status_code
        resp.encoding = resp.apparent_encoding or resp.encoding
        return url, resp.text, resp.status_code
    except (requests.RequestException, ValueError):
        return url, None, 0


async def fetch_html(url: str, min_delay_ms: int, max_delay_ms: int) -> tuple[str, str | None, int]:
    return await asyncio.to_thread(fetch_html_sync, url, min_delay_ms, max_delay_ms)


def load_seed_files(paths: Iterable[Path]) -> set[str]:
    out: set[str] = set()
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            norm = normalize_mst(line)
            if norm:
                out.add(norm)
    return out


async def run(args: argparse.Namespace) -> dict[str, int]:
    start_urls = [u.strip() for u in args.start_urls.split(",") if u.strip()] or list(DEFAULT_START_URLS)
    queries = [q.strip() for q in args.query_seeds.split(",") if q.strip()]
    start_urls.extend([f"https://masothue.com/Search/?q={quote(q)}" for q in queries])
    queue: list[str] = list(dict.fromkeys(start_urls))
    visited: set[str] = set()
    discovered_company_urls: set[str] = set()
    all_msts: set[str] = set()
    ok_pages = 0
    fail_pages = 0
    status_counts: dict[int, int] = {}

    merge_files = [Path(p.strip()) for p in args.merge_files.split(",") if p.strip()]
    all_msts.update(load_seed_files(merge_files))

    while queue and len(visited) < args.max_pages:
        batch: list[str] = []
        while queue and len(batch) < args.concurrency and len(visited) + len(batch) < args.max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            batch.append(url)
        if not batch:
            break

        results = await asyncio.gather(*[fetch_html(url, args.min_delay_ms, args.max_delay_ms) for url in batch])
        for url, html, status in results:
            status_counts[status] = status_counts.get(status, 0) + 1
            if not html:
                fail_pages += 1
                continue
            ok_pages += 1
            all_msts.update(extract_msts_from_text(html))
            links, listing_links, link_msts = extract_company_links(url, html)
            all_msts.update(link_msts)
            candidate_links = links | listing_links
            fresh_links = [u for u in candidate_links if u not in visited and u not in discovered_company_urls]
            discovered_company_urls.update(fresh_links)
            queue.extend(fresh_links)

    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.unique_output.parent.mkdir(parents=True, exist_ok=True)
    raw_sorted = sorted(all_msts)
    args.raw_output.write_text("\n".join(raw_sorted) + ("\n" if raw_sorted else ""), encoding="utf-8")

    # Keep only enterprise-like MSTs (10 or 10-3)
    unique_sorted = sorted({x for x in all_msts if re.fullmatch(r"\d{10}(?:-\d{3})?", x)})
    args.unique_output.write_text("\n".join(unique_sorted) + ("\n" if unique_sorted else ""), encoding="utf-8")

    stats = {
        "pages_visited": len(visited),
        "pages_ok": ok_pages,
        "pages_failed": fail_pages,
        "queue_remaining": len(queue),
        "company_links_discovered": len(discovered_company_urls),
        "mst_total_raw": len(raw_sorted),
        "mst_total_unique": len(unique_sorted),
        "status_counts": {str(k): v for k, v in sorted(status_counts.items(), key=lambda kv: kv[0])},
    }
    args.stats_output.parent.mkdir(parents=True, exist_ok=True)
    args.stats_output.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build real MST seed list from public pages")
    p.add_argument("--start-urls", type=str, default="https://masothue.com/")
    p.add_argument(
        "--query-seeds",
        type=str,
        default="ha-noi,tp-ho-chi-minh,cong-ty,doanh-nghiep,xay-dung,thuong-mai,logistics,san-xuat",
    )
    p.add_argument("--merge-files", type=str, default="../seed_mst.txt,mst_input.txt,mst_input_1k_real.txt")
    p.add_argument("--max-pages", type=int, default=800)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--min-delay-ms", type=int, default=40)
    p.add_argument("--max-delay-ms", type=int, default=120)
    p.add_argument("--raw-output", type=Path, default=Path("out/seed/seed_mst_raw.txt"))
    p.add_argument("--unique-output", type=Path, default=Path("out/seed/seed_mst_unique.txt"))
    p.add_argument("--stats-output", type=Path, default=Path("out/seed/seed_stats.json"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    stats = asyncio.run(run(args))
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
