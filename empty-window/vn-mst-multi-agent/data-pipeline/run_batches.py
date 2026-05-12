#!/usr/bin/env python3
"""
Chay nhieu batch category URL cho crawler compliant.

Input:
- Thu muc chua cac file danh muc, VD:
  category_batch_01.txt
  category_batch_02.txt
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run batch cho crawl_trangvang_compliant.py")
    p.add_argument("--base-url", required=True)
    p.add_argument("--batch-dir", type=Path, required=True)
    p.add_argument("--batch-glob", default="category_batch_*.txt")
    p.add_argument("--output-dir", type=Path, default=Path("out/batches"))
    p.add_argument("--checkpoint-dir", type=Path, default=Path("out/checkpoints"))
    p.add_argument("--concurrency", type=int, default=15)
    p.add_argument("--delay-ms", type=int, default=120)
    p.add_argument("--max-pages-per-category", type=int, default=500)
    p.add_argument("--pg-dsn", default="")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    batch_files = sorted(args.batch_dir.glob(args.batch_glob))
    if not batch_files:
        print("Khong tim thay file batch nao.", file=sys.stderr)
        raise SystemExit(2)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []

    for batch in batch_files:
        stem = batch.stem
        out_file = args.output_dir / f"{stem}.jsonl"
        ck_file = args.checkpoint_dir / f"{stem}.checkpoint.json"

        cmd = [
            sys.executable,
            "crawl_trangvang_compliant.py",
            "--base-url",
            args.base_url,
            "--category-urls",
            str(batch),
            "--output",
            str(out_file),
            "--checkpoint",
            str(ck_file),
            "--concurrency",
            str(args.concurrency),
            "--request-delay-ms",
            str(args.delay_ms),
            "--max-pages-per-category",
            str(args.max_pages_per_category),
        ]
        if args.pg_dsn:
            cmd += ["--pg-dsn", args.pg_dsn]

        print(f"Running {batch.name} ...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr or result.stdout, file=sys.stderr)
            raise SystemExit(result.returncode)

        parsed = json.loads(result.stdout)
        summary.append(
            {
                "batch": batch.name,
                "output_file": parsed.get("output_file"),
                "stats": parsed.get("stats"),
                "seen_detail_urls": parsed.get("seen_detail_urls"),
            }
        )
        print(f"Done {batch.name}")

    print(json.dumps({"batches": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
