#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from axm_character_design.review006_shoulder_continuous_clearance import (
    build_review006_continuous_nonadjacent_clearance_evidence,
)
from axm_character_design.review006_shoulder_continuous_edge_adjacent_fold import (
    build_review006_continuous_edge_adjacent_fold_evidence,
)
from axm_character_design.review006_shoulder_deformation_gradient_frame import (
    build_review006_deformation_gradient_frame_evidence,
)
from axm_character_design.review006_shoulder_edge_adjacent_fold_margin import (
    build_review006_sampled_edge_adjacent_fold_margin_evidence,
)
from axm_character_design.review006_shoulder_neutral_bind_frame import (
    build_review006_neutral_bind_frame_evidence,
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
            "Build exact review-006 Rigging structural, sub-degree boundary, "
            "deformation-gradient frame, neutral bind-frame, continuous "
            "nonadjacent-clearance, sampled edge-adjacent fold and continuous "
            "edge-adjacent fold evidence."
        )
    )
    parser.add_argument("out_dir")
    args = parser.parse_args()

    safe = build_review006_structural_safe_envelope_evidence(args.out_dir)
    subdegree = build_review006_positive_subdegree_boundary_evidence(args.out_dir)
    frame = build_review006_deformation_gradient_frame_evidence(args.out_dir)
    neutral = build_review006_neutral_bind_frame_evidence(args.out_dir)
    continuous = build_review006_continuous_nonadjacent_clearance_evidence(args.out_dir)
    adjacent = build_review006_sampled_edge_adjacent_fold_margin_evidence(args.out_dir)
    continuous_edge = build_review006_continuous_edge_adjacent_fold_evidence(args.out_dir)
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
        "neutral_bind_frame_status": neutral["status"],
        "neutral_receiver_vertices": neutral["neutral_closure"]["total_receiver_vertices"],
        "neutral_owner_vertex_drift_m": neutral["neutral_closure"]["max_owner_vertex_drift_m"],
        "neutral_gradient_identity_delta": neutral["neutral_closure"]["max_gradient_identity_component_delta"],
        "neutral_normal_matrix_identity_delta": neutral["neutral_closure"]["max_normal_matrix_identity_component_delta"],
        "neutral_negative_control_rejected": neutral["negative_control"]["rejected"],
        "continuous_clearance_status": continuous["status"],
        "continuous_clearance_range_deg": continuous["continuous_clearance"]["range_deg"],
        "continuous_nonadjacent_clearance_proven_for_all_real_angles": continuous["continuous_clearance"]["nonadjacent_triangle_clearance_proven_for_all_real_angles"],
        "continuous_clearance_left_min_slack_m": continuous["continuous_clearance"]["sides"]["L"]["minimum_certificate_slack_m"],
        "continuous_clearance_right_min_slack_m": continuous["continuous_clearance"]["sides"]["R"]["minimum_certificate_slack_m"],
        "continuous_contact_bracket_deg": continuous["contact_transition"]["transition_bracket_deg"],
        "continuous_negative_control_rejected": continuous["negative_control"]["rejected"],
        "edge_adjacent_fold_status": adjacent["status"],
        "edge_adjacent_fold_range_deg": adjacent["sampled_edge_adjacent_fold_guard"]["range_deg"],
        "edge_adjacent_fold_step_deg": adjacent["sampled_edge_adjacent_fold_guard"]["step_deg"],
        "edge_adjacent_fold_sample_count_per_side": adjacent["sampled_edge_adjacent_fold_guard"]["sample_count_per_side"],
        "edge_adjacent_left_pair_count": adjacent["sampled_edge_adjacent_fold_guard"]["sides"]["L"]["edge_adjacent_pair_count"],
        "edge_adjacent_right_pair_count": adjacent["sampled_edge_adjacent_fold_guard"]["sides"]["R"]["edge_adjacent_pair_count"],
        "edge_adjacent_left_min_fold_angle_deg": adjacent["sampled_edge_adjacent_fold_guard"]["sides"]["L"]["minimum_sampled_fold_angle_deg"],
        "edge_adjacent_right_min_fold_angle_deg": adjacent["sampled_edge_adjacent_fold_guard"]["sides"]["R"]["minimum_sampled_fold_angle_deg"],
        "edge_adjacent_negative_control_rejected": adjacent["negative_control"]["rejected"],
        "continuous_edge_adjacent_fold_status": continuous_edge["status"],
        "continuous_edge_adjacent_range_deg": continuous_edge["continuous_edge_adjacent_fold_guard"]["range_deg"],
        "continuous_edge_adjacent_all_real_owner_angles_certified": continuous_edge["continuous_edge_adjacent_fold_guard"]["all_real_owner_angles_certified"],
        "continuous_edge_adjacent_left_min_slack_rad": continuous_edge["continuous_edge_adjacent_fold_guard"]["sides"]["L"]["minimum_certificate_slack_rad"],
        "continuous_edge_adjacent_right_min_slack_rad": continuous_edge["continuous_edge_adjacent_fold_guard"]["sides"]["R"]["minimum_certificate_slack_rad"],
        "continuous_edge_adjacent_left_subdivisions": continuous_edge["continuous_edge_adjacent_fold_guard"]["sides"]["L"]["adaptive_subdivision_count"],
        "continuous_edge_adjacent_right_subdivisions": continuous_edge["continuous_edge_adjacent_fold_guard"]["sides"]["R"]["adaptive_subdivision_count"],
        "continuous_edge_adjacent_negative_control_rejected": continuous_edge["negative_control"]["rejected"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
