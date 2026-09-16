#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from axm_character_design.connected_shoulder_diagonal_repair import (
    build_diagonal_repair_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_diagonal_repair_evidence(Path(args.out))
    comparison = receipt["sampled_intersection_comparison"]
    print(receipt["status"])
    print(
        "sampled pairs:",
        comparison["baseline_total_pairs"],
        "->",
        comparison["candidate_total_pairs"],
    )


if __name__ == "__main__":
    main()
