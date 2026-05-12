#!/usr/bin/env python3
"""
Batch async lookup against VietQR public business API.

LEGAL / USAGE — BẮT BUỘC ĐỌC:
- Chỉ dùng khi bạn có quyền hợp pháp (điều khoản dịch vụ, hợp đồng API, hoặc nguồn dữ liệu được phép).
- Không dùng script này để vượt giới hạn truy cập, né cơ chế chặn, hoặc thu thập trái phép.
- Quy mô 100k+ bản ghi: cần thỏa thuận thương mại / nguồn dữ liệu bản quyền; API công khai thường có rate limit (429).

HẠN CHẾ DỮ LIỆU: VietQR /v2/business/{taxCode} cung cấp chủ yếu MST, tên, địa chỉ (và tên quốc tế).
  Năm thành lập, SĐT, email, ngành VSIC đầy đủ cần nguồn bổ sung hợp pháp (đăng ký doanh nghiệp, nhà cung cấp dữ liệu).

Lọc Hà Nội / TP.HCM: heuristic trên chuỗi địa chỉ (xem REGION_KEYWORDS).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

import aiohttp

REGION_FILTERS = {
    "hn": ("HÀ NỘI", "HA NOI", "HANOI"),
    "hcm": ("HỒ CHÍ MINH", "HO CHI MINH", "TP. HỒ CHÍ MINH", "THỦ ĐỨC", "BINH THANH"),
}


def normalize_mst(line: str) -> str | None:
    digits = re.sub(r"\D", "", line.strip())
    return digits or None


def address_matches_region(address: str, regions: frozenset[str]) -> bool:
    u = address.upper()
    for key in regions:
        for kw in REGION_FILTERS[key]:
            if kw in u:
                return True
    return False


def map_to_target_schema(vietqr_data: dict[str, Any] | None, raw_response: dict[str, Any]) -> dict[str, Any]:
    """Chuẩn hóa về trường mục tiêu; trường không có từ VietQR để null."""
    if not vietqr_data:
        return {
            "mst": None,
            "ten_cong_ty": None,
            "nam_thanh_lap": None,
            "sdt": None,
            "email": None,
            "dia_chi": None,
            "nganh_nghe_kinh_doanh": None,
            "api_code": raw_response.get("code"),
            "api_desc": raw_response.get("desc"),
        }
    return {
        "mst": vietqr_data.get("id"),
        "ten_cong_ty": vietqr_data.get("name"),
        "nam_thanh_lap": None,
        "sdt": None,
        "email": None,
        "dia_chi": vietqr_data.get("address"),
        "nganh_nghe_kinh_doanh": None,
        "ten_quoc_te": vietqr_data.get("internationalName"),
        "ten_ngan": vietqr_data.get("shortName"),
        "api_code": raw_response.get("code"),
        "api_desc": raw_response.get("desc"),
    }


async def fetch_one(
    session: aiohttp.ClientSession,
    base_url: str,
    mst: str,
    timeout: aiohttp.ClientTimeout,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/v2/business/{mst}"
    async with session.get(url, timeout=timeout) as resp:
        text = await resp.text()
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            return {"code": "parse_error", "desc": text[:500], "data": None}
        return body


_STOP = object()


async def worker(
    queue: asyncio.Queue[str | object],
    session: aiohttp.ClientSession,
    base_url: str,
    out_lines: list[str],
    lock: asyncio.Lock,
    stats: dict[str, int],
    regions: frozenset[str] | None,
    max_retries: int,
    base_backoff: float,
) -> None:
    timeout = aiohttp.ClientTimeout(total=30)
    while True:
        item = await queue.get()
        if item is _STOP:
            queue.task_done()
            return
        mst = item
        try:
            attempt = 0
            raw: dict[str, Any] = {}
            while attempt <= max_retries:
                raw = await fetch_one(session, base_url, mst, timeout)
                code = str(raw.get("code", ""))
                if code == "429" or "429" in str(raw.get("desc", "")).lower():
                    delay = base_backoff * (2**attempt) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    attempt += 1
                    continue
                break

            data = raw.get("data") if isinstance(raw.get("data"), dict) else None
            row = map_to_target_schema(data, raw)

            if regions and data and data.get("address"):
                if not address_matches_region(data["address"], regions):
                    async with lock:
                        stats["filtered_region"] = stats.get("filtered_region", 0) + 1
                    continue

            line = json.dumps(row, ensure_ascii=False)
            async with lock:
                out_lines.append(line)
                if raw.get("code") == "00" and data:
                    stats["ok"] = stats.get("ok", 0) + 1
                else:
                    stats["miss"] = stats.get("miss", 0) + 1
        finally:
            queue.task_done()


async def run(args: argparse.Namespace) -> None:
    base_url = os.environ.get("VIETQR_API_BASE", "https://api.vietqr.io")
    mst_path: Path = args.input

    msts: list[str] = []
    for line in mst_path.read_text(encoding="utf-8").splitlines():
        n = normalize_mst(line)
        if n:
            msts.append(n)

    regions: frozenset[str] | None = None
    if args.only_hn_hcmc:
        regions = frozenset(["hn", "hcm"])

    queue: asyncio.Queue[str | object] = asyncio.Queue()
    for m in msts:
        await queue.put(m)
    for _ in range(args.workers):
        await queue.put(_STOP)

    out_lines: list[str] = []
    lock = asyncio.Lock()
    stats: dict[str, int] = {}

    connector = aiohttp.TCPConnector(limit=args.workers * 2)
    headers = {"Accept": "application/json", "User-Agent": "vn-mst-pipeline/1.0 (compliant batch)"}

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [
            asyncio.create_task(
                worker(
                    queue,
                    session,
                    base_url,
                    out_lines,
                    lock,
                    stats,
                    regions,
                    args.max_retries,
                    args.backoff,
                )
            )
            for _ in range(args.workers)
        ]
        await asyncio.gather(*tasks)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")

    print(json.dumps({"stats": stats, "written": len(out_lines)}, ensure_ascii=False), file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description="Async VietQR batch fetch (compliant use only).")
    p.add_argument("input", type=Path, help="File MST, một dòng một mã")
    p.add_argument("-o", "--output", type=Path, default=Path("out/vietqr_batch.jsonl"))
    p.add_argument("-w", "--workers", type=int, default=8, help="Số coroutine song song (giữ thấp để tránh 429)")
    p.add_argument("--max-retries", type=int, default=4)
    p.add_argument("--backoff", type=float, default=1.5, help="Backoff cơ sở khi 429 (giây)")
    p.add_argument(
        "--only-hn-hcmc",
        action="store_true",
        help="Chỉ giữ bản ghi có địa chỉ khớp Hà Nội hoặc TP.HCM (heuristic)",
    )
    args = p.parse_args()
    if args.workers < 1 or args.workers > 50:
        print("workers nên trong [1, 50] khi dùng API công khai.", file=sys.stderr)
        sys.exit(2)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
