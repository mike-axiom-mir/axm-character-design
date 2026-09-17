#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from axm_character_design.review006_shoulder_deformation_gradient_frame import (
    build_review006_deformation_gradient_frame_evidence,
)
from axm_character_design.review006_shoulder_safe_envelope import (
    build_review006_structural_safe_envelope_evidence,
)
from axm_character_design.review006_shoulder_subdegree_boundary import (
    build_review006_positive_subdegree_boundary_evidence,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build exact review-006 Rigging structural, sub-degree boundary and "
            "deformation-gradient frame evidence."
        )
    )
    parser.add_argument("out_dir")
    args = parser.parse_args()

    safe = build_review006_structural_safe_envelope_evidence(args.out_dir)
    subdegree = build_review006_positive_subdegree_boundary_evidence(args.out_dir)
    frame = build_review006_deformation_gradient_frame_evidence(args.out_dir)
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
        "subdegree_negative_control_rejected": subdegree["negative_control"]["rejected"],
        "deformation_gradient_frame_status": frame["status"],
        "continuous_local_gradient_invertible": frame["deformation_gradient_reference"]["continuous_local_gradient_invertible"],
        "continuous_proximal_determinant_lower_bound": frame["deformation_gradient_reference"]["continuous_proximal_determinant_lower_bound_minus40_plus40"],
        "max_owner_affine_position_residual_m": frame["deformation_gradient_reference"]["max_owner_affine_position_residual_m"],
        "frame_negative_control_rejected": frame["negative_control"]["rejected"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
