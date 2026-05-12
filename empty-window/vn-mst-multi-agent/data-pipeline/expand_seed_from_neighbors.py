#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import re
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Expand MST seeds by nearby numeric neighbors")
    p.add_argument("--input", type=Path, default=Path("out/seed/seed_mst_unique.txt"))
    p.add_argument("--output", type=Path, default=Path("out/seed/seed_mst_candidates.txt"))
    p.add_argument("--window", type=int, default=120)
    p.add_argument("--extra-sample", type=int, default=80)
    p.add_argument("--extra-step-max", type=int, default=1200)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    lines = args.input.read_text(encoding="utf-8", errors="ignore").splitlines()
    base = sorted({x.strip() for x in lines if re.fullmatch(r"\d{10}", x.strip())})
    if not base:
        raise SystemExit("Khong co MST 10 so trong file input.")

    rng = random.Random(args.seed)
    candidates = set(base)
    for m in base:
        n = int(m)
        for d in range(-args.window, args.window + 1):
            v = n + d
            if v >= 0:
                candidates.add(f"{v:010d}")

    sample = rng.sample(base, min(len(base), args.extra_sample))
    for m in sample:
        n = int(m)
        for d in range(args.window + 1, args.extra_step_max + 1, 11):
            candidates.add(f"{n + d:010d}")
            if n >= d:
                candidates.add(f"{n - d:010d}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(sorted(candidates)) + "\n", encoding="utf-8")
    print({"seed_count": len(base), "candidate_count": len(candidates), "output": str(args.output)})


if __name__ == "__main__":
    main()
