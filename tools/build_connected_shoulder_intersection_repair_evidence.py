#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from axm_character_design.connected_shoulder_intersection_repair import (
    build_opening_repair_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_opening_repair_evidence(Path(args.out))
    print(receipt["status"])
    print(
        "sampled pairs:",
        receipt["sampled_intersection_comparison"]["base_total_pairs"],
        "->",
        receipt["sampled_intersection_comparison"]["candidate_total_pairs"],
    )


if __name__ == "__main__":
    main()
