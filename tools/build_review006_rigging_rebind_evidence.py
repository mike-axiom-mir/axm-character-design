#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from axm_character_design.review006_shoulder_safe_envelope import (
    build_review006_structural_safe_envelope_evidence,
)


def main():
    parser = argparse.ArgumentParser(
        description="Build exact review-006 Rigging structural safe-envelope evidence."
    )
    parser.add_argument("out_dir")
    args = parser.parse_args()
    audit = build_review006_structural_safe_envelope_evidence(args.out_dir)
    print(json.dumps({
        "status": audit["status"],
        "safe_envelope_deg": audit["safe_envelope"]["range_deg"],
        "safe_sampled_pose_count": audit["safe_envelope"]["sampled_pose_count"],
        "safe_intersection_free": audit["safe_envelope"]["all_nonadjacent_intersection_free"],
        "first_unsafe_positive_deg": audit["outside_envelope_witness"]["first_positive_sample_deg"],
        "first_unsafe_positive_rows": audit["outside_envelope_witness"]["rows"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
