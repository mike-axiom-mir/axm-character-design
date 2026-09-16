from __future__ import annotations

import argparse
from pathlib import Path

from axm_character_design.connected_shoulder_stitch_edge_repair import (
    build_stitch_edge_repair_evidence,
)


def main():
    parser = argparse.ArgumentParser(
        description="Build retained Geometry evidence for the Character shoulder stitch-edge repair."
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_stitch_edge_repair_evidence(Path(args.out))
    print(receipt["status"])
    dense = receipt["dense_sweep"]
    print(
        "dense-pairs",
        dense["baseline_pair_count_sum"],
        "->",
        dense["candidate_pair_count_sum"],
        "improved",
        dense["strictly_reduced_samples"],
        "equal",
        dense["equal_samples"],
        "worse",
        dense["worse_samples"],
    )


if __name__ == "__main__":
    main()
