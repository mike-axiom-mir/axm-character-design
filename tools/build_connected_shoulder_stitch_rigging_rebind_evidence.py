from __future__ import annotations

import argparse

from axm_character_design.connected_shoulder_stitch_rigging_rebind import (
    build_stitch_edge_rigging_rebind_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_stitch_edge_rigging_rebind_evidence(args.out)
    print(receipt["status"])
    print(receipt["gates"]["all_162_pose_positions_match_previous_rigging_field"])
    print(receipt["representative_intersections"]["pair_count_sum"])


if __name__ == "__main__":
    main()
