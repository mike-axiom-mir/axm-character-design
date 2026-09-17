#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from axm_character_design.review006_shoulder_safe_envelope import (
    build_review006_structural_safe_envelope_evidence,
)
from axm_character_design.review006_shoulder_subdegree_boundary import (
    build_review006_positive_subdegree_boundary_evidence,
)


def main():
    parser = argparse.ArgumentParser(
        description="Build exact review-006 Rigging structural and sub-degree boundary evidence."
    )
    parser.add_argument("out_dir")
    args = parser.parse_args()

    safe = build_review006_structural_safe_envelope_evidence(args.out_dir)
    subdegree = build_review006_positive_subdegree_boundary_evidence(args.out_dir)
    print(json.dumps({
        "status": safe["status"],
        "safe_envelope_deg": safe["safe_envelope"]["range_deg"],
        "safe_sampled_pose_count": safe["safe_envelope"]["sampled_pose_count"],
        "safe_intersection_free": safe["safe_envelope"]["all_nonadjacent_intersection_free"],
        "integer_first_unsafe_positive_deg": safe["outside_envelope_witness"]["first_positive_sample_deg"],
        "subdegree_status": subdegree["status"],
        "subdegree_step_deg": subdegree["subdegree_probe"]["step_deg"],
        "subdegree_pose_count": subdegree["subdegree_probe"]["posed_sample_count"],
        "refined_positive_sampled_guard_max_deg": subdegree["sampled_guard"]["refined_positive_sampled_guard_max_deg"],
        "first_sampled_positive_failure_deg": subdegree["sampled_guard"]["first_sampled_positive_failure_deg"],
        "negative_control_rejected": subdegree["negative_control"]["rejected"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
