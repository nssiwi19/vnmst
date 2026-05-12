#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import random
import re
from pathlib import Path


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


def main() -> None:
    p = argparse.ArgumentParser(description="Split MST file into N batch files")
    p.add_argument("input", type=Path)
    p.add_argument("--batch-count", type=int, default=10)
    p.add_argument("--output-dir", type=Path, default=Path("."))
    p.add_argument("--prefix", type=str, default="mst_real_batch")
    p.add_argument("--shuffle", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    lines = args.input.read_text(encoding="utf-8", errors="ignore").splitlines()
    msts = sorted({m for m in (normalize_mst(x) for x in lines) if m})
    if not msts:
        raise SystemExit("Khong co MST hop le de chia batch.")

    if args.shuffle:
        rng = random.Random(args.seed)
        rng.shuffle(msts)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_batch = math.ceil(len(msts) / args.batch_count)
    created = 0
    for i in range(args.batch_count):
        chunk = msts[i * per_batch : (i + 1) * per_batch]
        if not chunk:
            break
        out = args.output_dir / f"{args.prefix}_{i+1:02d}.txt"
        out.write_text("\n".join(chunk) + "\n", encoding="utf-8")
        created += 1

    print(
        {
            "input_unique": len(msts),
            "batch_count_requested": args.batch_count,
            "batch_count_created": created,
            "per_batch_target": per_batch,
            "output_dir": str(args.output_dir),
            "prefix": args.prefix,
        }
    )


if __name__ == "__main__":
    main()
