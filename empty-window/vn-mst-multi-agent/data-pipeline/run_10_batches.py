#!/usr/bin/env python3
"""
Chay tu dong nhieu batch MST va tong hop KPI chat luong cuoi.

Yeu cau:
- Thu muc batch chua file kieu: mst_batch_01.txt ... mst_batch_10.txt
- Script goi crawl_vn_enterprises.py cho tung batch
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run 10 batches + final quality summary")
    p.add_argument("--batch-dir", type=Path, default=Path("."))
    p.add_argument("--batch-glob", type=str, default="mst_batch_*.txt")
    p.add_argument("--output-dir", type=Path, default=Path("out/batches"))
    p.add_argument("--workers", type=int, default=15)
    p.add_argument("--pause-ms", type=int, default=150)
    p.add_argument("--source-retries", type=int, default=1)
    p.add_argument("--source-retry-backoff-ms", type=int, default=120)
    p.add_argument("--rescue-rounds", type=int, default=1)
    p.add_argument(
        "--source-profile",
        choices=["custom", "official3"],
        default="custom",
        help="official3 = dkkd -> gdt -> vietqr -> esgoo -> thongtindoanhnghiep -> xinvoice -> masothue",
    )
    p.add_argument("--source-order", type=str, default="vietqr,esgoo,thongtindoanhnghiep,xinvoice")
    p.add_argument("--vietqr-base-url", type=str, default="https://api.vietqr.io")
    p.add_argument("--esgoo-url-template", type=str, default="https://esgoo.net/api-mst/{mst}.htm")
    p.add_argument("--ttdn-url-template", type=str, default="https://thongtindoanhnghiep.co/api/company/{mst}")
    p.add_argument("--xinvoice-url-template", type=str, default="https://api.xinvoice.vn/gdt-api/tax-payer-records/{mst}")
    p.add_argument("--xinvoice-client-id", type=str, default="")
    p.add_argument("--xinvoice-api-key", type=str, default="")
    p.add_argument(
        "--dkkd-lookup-url",
        type=str,
        default="https://dangkykinhdoanh.gov.vn/bocaodientu/App_Services/NghiepVu/TienIch/TraCuu.asmx/LayDanhSachDoanhNghiepTheoTenNgan",
    )
    p.add_argument(
        "--masothue-url-template",
        type=str,
        default="https://masothue.com/Search/?q={mst}",
    )
    p.add_argument("--allow-all-regions", action="store_true")
    return p.parse_args()


def add_source_metrics(target: dict[str, dict[str, int]], source_metrics: dict[str, Any]) -> None:
    for source, values in source_metrics.items():
        if source not in target:
            target[source] = {"attempt": 0, "success": 0, "fail": 0}
        target[source]["attempt"] += int(values.get("attempt", 0))
        target[source]["success"] += int(values.get("success", 0))
        target[source]["fail"] += int(values.get("fail", 0))


def add_crawl_stats(target: dict[str, int], stats: dict[str, Any]) -> None:
    for key, value in stats.items():
        target[key] = target.get(key, 0) + int(value)


def run_one_batch(args: argparse.Namespace, batch_file: Path) -> dict[str, Any]:
    stem = batch_file.stem
    out_jsonl = args.output_dir / f"{stem}.jsonl"
    out_manual = args.output_dir / f"{stem}.manual_review.jsonl"
    out_quality = args.output_dir / f"{stem}.quality_report.json"

    cmd = [
        sys.executable,
        "crawl_vn_enterprises.py",
        str(batch_file),
        "--workers",
        str(args.workers),
        "--pause-ms",
        str(args.pause_ms),
        "--source-retries",
        str(args.source_retries),
        "--source-retry-backoff-ms",
        str(args.source_retry_backoff_ms),
        "--rescue-rounds",
        str(args.rescue_rounds),
        "--source-profile",
        args.source_profile,
        "--source-order",
        args.source_order,
        "--dkkd-lookup-url",
        args.dkkd_lookup_url,
        "--masothue-url-template",
        args.masothue_url_template,
        "--vietqr-base-url",
        args.vietqr_base_url,
        "--esgoo-url-template",
        args.esgoo_url_template,
        "--ttdn-url-template",
        args.ttdn_url_template,
        "--xinvoice-url-template",
        args.xinvoice_url_template,
        "--manual-review-file",
        str(out_manual),
        "--quality-report-file",
        str(out_quality),
        "--output",
        str(out_jsonl),
    ]
    if args.xinvoice_client_id:
        cmd += ["--xinvoice-client-id", args.xinvoice_client_id]
    if args.xinvoice_api_key:
        cmd += ["--xinvoice-api-key", args.xinvoice_api_key]
    if args.allow_all_regions:
        cmd.append("--allow-all-regions")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"Batch {batch_file.name} fail:\n{err}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Batch {batch_file.name} output khong phai JSON:\n{proc.stdout}") from exc


def main() -> None:
    args = parse_args()
    batch_files = sorted(args.batch_dir.glob(args.batch_glob))
    if not batch_files:
        print("Khong tim thay file batch nao.", file=sys.stderr)
        raise SystemExit(2)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    final = {
        "batch_count": len(batch_files),
        "batches": [],
        "totals": {
            "input_total": 0,
            "input_unique": 0,
            "output_records": 0,
            "dedup_records": 0,
            "duplicates_removed": 0,
            "manual_review_count": 0,
        },
        "crawl_stats_total": {},
        "quality_by_source_total": {},
    }

    for batch_file in batch_files:
        print(f"Running {batch_file.name} ...")
        result = run_one_batch(args, batch_file)
        final["batches"].append({"batch_file": batch_file.name, "result": result})
        final["totals"]["input_total"] += int(result.get("input_total", 0))
        final["totals"]["input_unique"] += int(result.get("input_unique", 0))
        final["totals"]["output_records"] += int(result.get("output_records", 0))
        final["totals"]["dedup_records"] += int(result.get("dedup_records", 0))
        final["totals"]["duplicates_removed"] += int(result.get("duplicates_removed", 0))
        final["totals"]["manual_review_count"] += int(result.get("manual_review_count", 0))
        add_crawl_stats(final["crawl_stats_total"], result.get("crawl_stats", {}))
        add_source_metrics(final["quality_by_source_total"], result.get("quality_by_source", {}))
        print(f"Done {batch_file.name}")

    summary_file = args.output_dir / "final_quality_summary.json"
    summary_file.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary_file": str(summary_file), "batch_count": len(batch_files)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
