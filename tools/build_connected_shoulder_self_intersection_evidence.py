from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_character_design.connected_shoulder_self_intersection import (
    build_connected_shoulder_self_intersection_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_connected_shoulder_self_intersection_evidence(args.out)
    pair_total = sum(
        sample["inspection"]["self_intersection_pair_count"]
        for sample in receipt["samples"]
    )
    print(receipt["status"])
    print(f"samples={receipt['sample_scope']['sample_count']}")
    print(f"nonadjacent_self_intersection_pairs={pair_total}")


if __name__ == "__main__":
    main()
