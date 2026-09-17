#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from axm_character_design.review006_shoulder_rigging_rebind import (
    build_review006_rigging_rebind_evidence,
)


def main():
    parser = argparse.ArgumentParser(
        description="Build exact review-006 opening-repair Rigging rebind evidence."
    )
    parser.add_argument("out_dir")
    args = parser.parse_args()
    audit = build_review006_rigging_rebind_evidence(args.out_dir)
    print(json.dumps({
        "status": audit["status"],
        "candidate_pose_count": audit["sample_scope"]["candidate_pose_count"],
        "intersection_acceptance": audit["nonadjacent_self_intersection"]["acceptance"],
        "intersection_pair_sum": audit["nonadjacent_self_intersection"]["sample_pair_count_sum"],
        "nonzero_intersection_samples": audit["nonadjacent_self_intersection"]["nonzero_sample_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
