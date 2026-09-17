from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path

from .organic_form import canonical_digest, mesh_checks, validate_study, write_obj
from .shoulder_pose_clearance_candidate import (
    EXPECTED_CANDIDATE_MESH_DIGEST as EXPECTED_REVIEW005_MESH_DIGEST,
    EXPECTED_CANDIDATE_SOURCE_DIGEST as EXPECTED_REVIEW005_SOURCE_DIGEST,
    VARIANT_ID as REVIEW005_ID,
    shoulder_pose_clearance_candidate,
)
from .shoulder_source_lineage import adopted_character_source, build_adopted_character_mesh
from .shoulder_transition_profile import _filled_comparison_svg

SCHEMA = "axm.character-shoulder-pose-clearance-refinement/v0.1"
VARIANT_ID = "character-neutral-a-shoulder-pose-clearance-review-006"
STATUS = "PASS_BOUNDED_CHARACTER_SHOULDER_POSE_CLEARANCE_REFINEMENT_CANDIDATE"

# Review-005 proved useful enough to retain, but its moved elbows also introduced a
# much more bent neutral source landmark chain. Review-006 changes only the elbow
# location relative to review-005, keeping the same shoulder and wrist positions.
ELBOW_X_M = 0.5045
ELBOW_Z_M = 1.3474
MAX_PARENT_SEGMENT_LENGTH_DELTA_RATIO = 0.01
MIN_REVIEW005_FLEX_REDUCTION_DEG = 4.0


def _distance(a, b):
    return math.dist(tuple(float(value) for value in a), tuple(float(value) for value in b))


def _elbow_flexion_from_straight_deg(source, side="R"):
    shoulder = source["landmarks"][f"shoulder_{side}"]
    elbow = source["landmarks"][f"elbow_{side}"]
    wrist = source["landmarks"][f"wrist_{side}"]
    a = [float(shoulder[i]) - float(elbow[i]) for i in range(3)]
    b = [float(wrist[i]) - float(elbow[i]) for i in range(3)]
    dot = sum(a[i] * b[i] for i in range(3))
    na = math.sqrt(sum(value * value for value in a))
    nb = math.sqrt(sum(value * value for value in b))
    cosine = max(-1.0, min(1.0, dot / (na * nb)))
    internal = math.degrees(math.acos(cosine))
    return 180.0 - internal


def shoulder_pose_clearance_refinement_candidate():
    review005 = shoulder_pose_clearance_candidate()
    if review005.get("study_id") != REVIEW005_ID:
        raise ValueError("review-005 Character source ID drift")
    if canonical_digest(review005) != EXPECTED_REVIEW005_SOURCE_DIGEST:
        raise ValueError("review-005 Character source digest drift")
    review005_mesh = build_adopted_character_mesh(review005)
    if canonical_digest(review005_mesh) != EXPECTED_REVIEW005_MESH_DIGEST:
        raise ValueError("review-005 Character proof-mesh digest drift")

    candidate = deepcopy(review005)
    candidate["study_id"] = VARIANT_ID
    candidate["intent"] = (
        "stylized_biped_form_study_with_adopted_feathered_shoulder_transition_"
        "and_review_only_shoulder_pose_clearance_refinement"
    )
    candidate["landmarks"]["elbow_L"][0] = -ELBOW_X_M
    candidate["landmarks"]["elbow_R"][0] = ELBOW_X_M
    candidate["landmarks"]["elbow_L"][2] = ELBOW_Z_M
    candidate["landmarks"]["elbow_R"][2] = ELBOW_Z_M
    candidate["shoulder_pose_clearance_refinement"] = {
        "schema": SCHEMA,
        "variant_id": VARIANT_ID,
        "status": "DERIVED_REVIEW_VARIANT_NOT_ADOPTED_SOURCE",
        "parent_review_id": REVIEW005_ID,
        "parent_review_source_digest": EXPECTED_REVIEW005_SOURCE_DIGEST,
        "parent_review_mesh_digest": EXPECTED_REVIEW005_MESH_DIGEST,
        "bounded_source_delta_from_review005": {
            "elbow_lateral_magnitude_m": [0.5100, ELBOW_X_M],
            "elbow_height_m": [1.3575, ELBOW_Z_M],
            "shoulders_changed": False,
            "wrists_and_hands_changed": False,
            "accepted_E_transition_semantics_changed": False,
        },
        "purpose": (
            "retain review-005 shoulder/wrist silhouette while reducing the neutral elbow-chain "
            "bend introduced by its clearance-oriented elbow placement"
        ),
        "downstream_state": "ART_QA_GEOMETRY_RIGGING_REBIND_REQUIRED",
    }
    validate_study(candidate)
    return candidate


def _normalized_back_to_review005(candidate):
    normalized = deepcopy(candidate)
    normalized.pop("shoulder_pose_clearance_refinement")
    review005 = shoulder_pose_clearance_candidate()
    normalized["study_id"] = review005["study_id"]
    normalized["intent"] = review005["intent"]
    normalized["landmarks"]["elbow_L"] = deepcopy(review005["landmarks"]["elbow_L"])
    normalized["landmarks"]["elbow_R"] = deepcopy(review005["landmarks"]["elbow_R"])
    return normalized


def audit_shoulder_pose_clearance_refinement(candidate=None):
    parent = adopted_character_source()
    review005 = shoulder_pose_clearance_candidate()
    candidate = candidate or shoulder_pose_clearance_refinement_candidate()
    validate_study(candidate)

    if canonical_digest(review005) != EXPECTED_REVIEW005_SOURCE_DIGEST:
        raise ValueError("review-005 source identity drift")
    review005_mesh = build_adopted_character_mesh(review005)
    if canonical_digest(review005_mesh) != EXPECTED_REVIEW005_MESH_DIGEST:
        raise ValueError("review-005 mesh identity drift")
    if candidate.get("study_id") != VARIANT_ID:
        raise ValueError("review-006 candidate ID drift")
    if canonical_digest(_normalized_back_to_review005(candidate)) != EXPECTED_REVIEW005_SOURCE_DIGEST:
        raise ValueError("review-006 changed fields outside bounded elbow refinement")

    expected = {
        "elbow_L": (-ELBOW_X_M, 0.0, ELBOW_Z_M),
        "elbow_R": (ELBOW_X_M, 0.0, ELBOW_Z_M),
    }
    for name, xyz in expected.items():
        if tuple(float(value) for value in candidate["landmarks"][name]) != xyz:
            raise ValueError(f"unexpected review-006 elbow drift: {name}")

    for name in ("shoulder_L", "shoulder_R", "wrist_L", "wrist_R", "hand_tip_L", "hand_tip_R"):
        if candidate["landmarks"][name] != review005["landmarks"][name]:
            raise ValueError(f"review-006 changed protected landmark: {name}")
    if candidate["shoulder_transition_repair"] != review005["shoulder_transition_repair"]:
        raise ValueError("accepted E shoulder transition semantics changed")
    if candidate["shoulder_transition_regions"] != review005["shoulder_transition_regions"]:
        raise ValueError("accepted E shoulder transition regions changed")

    candidate_mesh = build_adopted_character_mesh(candidate)
    candidate_checks = mesh_checks(candidate_mesh)
    review005_checks = mesh_checks(review005_mesh)
    if candidate_checks != review005_checks:
        raise ValueError("review-006 changed proof-mesh structural budget or whole-body bounds")

    parent_lengths = {
        "upper_arm": _distance(parent["landmarks"]["shoulder_R"], parent["landmarks"]["elbow_R"]),
        "lower_arm": _distance(parent["landmarks"]["elbow_R"], parent["landmarks"]["wrist_R"]),
    }
    review005_lengths = {
        "upper_arm": _distance(review005["landmarks"]["shoulder_R"], review005["landmarks"]["elbow_R"]),
        "lower_arm": _distance(review005["landmarks"]["elbow_R"], review005["landmarks"]["wrist_R"]),
    }
    candidate_lengths = {
        "upper_arm": _distance(candidate["landmarks"]["shoulder_R"], candidate["landmarks"]["elbow_R"]),
        "lower_arm": _distance(candidate["landmarks"]["elbow_R"], candidate["landmarks"]["wrist_R"]),
    }
    parent_length_delta_ratios = {
        key: candidate_lengths[key] / parent_lengths[key] - 1.0 for key in parent_lengths
    }
    if any(abs(value) > MAX_PARENT_SEGMENT_LENGTH_DELTA_RATIO for value in parent_length_delta_ratios.values()):
        raise ValueError("review-006 exceeds parent-relative arm-segment length delta")

    review005_flex = _elbow_flexion_from_straight_deg(review005)
    candidate_flex = _elbow_flexion_from_straight_deg(candidate)
    flex_reduction = review005_flex - candidate_flex
    if flex_reduction < MIN_REVIEW005_FLEX_REDUCTION_DEG:
        raise ValueError("review-006 elbow refinement does not materially reduce review-005 neutral bend")

    review005_valid = validate_study(review005)
    candidate_valid = validate_study(candidate)
    if candidate_valid["a_pose_down_angle_deg"] != review005_valid["a_pose_down_angle_deg"]:
        raise ValueError("review-006 changed shoulder-to-wrist A-rest line")

    refinement = candidate["shoulder_pose_clearance_refinement"]
    if refinement["status"] != "DERIVED_REVIEW_VARIANT_NOT_ADOPTED_SOURCE":
        raise ValueError("review-006 truth-state drift")
    if refinement["downstream_state"] != "ART_QA_GEOMETRY_RIGGING_REBIND_REQUIRED":
        raise ValueError("review-006 downstream-state drift")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "variant_id": VARIANT_ID,
        "parent_review_id": REVIEW005_ID,
        "parent_review_source_digest": EXPECTED_REVIEW005_SOURCE_DIGEST,
        "parent_review_mesh_digest": EXPECTED_REVIEW005_MESH_DIGEST,
        "candidate_source_digest": canonical_digest(candidate),
        "candidate_mesh_digest": canonical_digest(candidate_mesh),
        "bounded_delta_from_review005": refinement["bounded_source_delta_from_review005"],
        "form_metrics": {
            "parent_segment_lengths_m": parent_lengths,
            "review005_segment_lengths_m": review005_lengths,
            "candidate_segment_lengths_m": candidate_lengths,
            "candidate_vs_parent_segment_length_delta_ratios": parent_length_delta_ratios,
            "review005_flexion_from_straight_deg": review005_flex,
            "candidate_flexion_from_straight_deg": candidate_flex,
            "review005_minus_candidate_flexion_deg": flex_reduction,
            "review005_a_rest_down_angle_deg": review005_valid["a_pose_down_angle_deg"],
            "candidate_a_rest_down_angle_deg": candidate_valid["a_pose_down_angle_deg"],
            "vertex_count": candidate_checks["vertex_count"],
            "triangle_count": candidate_checks["triangle_count"],
            "degenerate_triangles": candidate_checks["degenerate_triangles"],
            "bounds_min": candidate_checks["bounds_min"],
            "bounds_max": candidate_checks["bounds_max"],
        },
        "gates": {
            "exact_review005_identity": "PASS",
            "elbows_only_relative_to_review005": "PASS",
            "shoulder_wrist_hand_positions_preserved": "PASS",
            "accepted_E_transition_semantics_preserved": "PASS",
            "same_proof_mesh_counts_and_bounds": "PASS",
            "parent_relative_arm_segment_length_delta_below_1_percent": "PASS",
            "review005_neutral_elbow_bend_reduced_by_at_least_4_deg": "PASS",
            "same_shoulder_to_wrist_A_rest_line_as_review005": "PASS",
            "visual_acceptance": "NOT_EVALUATED",
            "connected_topology_or_intersection_rebind": "NOT_EVALUATED",
            "rigging_or_deformation_rebind": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoffs": {
            "art_direction_visual_qa": (
                "Compare parent, review-005 and review-006. Review-006 keeps review-005 shoulder/wrist "
                "silhouette but reduces its neutral elbow-chain bend; judge whether that is a cleaner "
                "form compromise without reintroducing the accepted-E shoulder problem."
            ),
            "geometry": (
                "Topology-only two-flip and current-pair-plus-third-flip families did not remove the "
                "current parent intersections. If this review form is chosen, bind its exact source/mesh "
                "identity and independently rerun connected topology/intersection evidence; do not inherit "
                "any historical Organic exploratory result."
            ),
            "rigging": (
                "No rigging or deformation PASS transfers. Rebind only after Geometry owns an exact "
                "receiver for the selected source-form identity."
            ),
        },
        "truth_boundary": [
            "Review-006 is a derived Organic review candidate, not an adopted source successor.",
            "Relative to review-005 only the bilateral elbow landmarks change; shoulder, wrist, hand, masses, segment radii, flex-zone truth states and accepted E transition semantics are preserved.",
            "The reduced source-landmark elbow-chain bend is a geometric review fact, not an anatomy, skeletal rest-angle or range-of-motion claim.",
            "No connected-topology, self-intersection, rigging, weighting, continuous-deformation, Animation, materials, runtime, gameplay, CANON, production-readiness or Organic mastery claim is made.",
        ],
    }


def build_shoulder_pose_clearance_refinement_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    parent = adopted_character_source()
    review005 = shoulder_pose_clearance_candidate()
    candidate = shoulder_pose_clearance_refinement_candidate()
    candidate_mesh = build_adopted_character_mesh(candidate)
    receipt = audit_shoulder_pose_clearance_refinement(candidate)

    (out / "shoulder-pose-clearance-review-006.source.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-pose-clearance-review-006.mesh.json").write_text(
        json.dumps(candidate_mesh, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-pose-clearance-review-006-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_obj(candidate_mesh, out / "shoulder-pose-clearance-review-006.obj")

    neutral_meshes = {
        "Parent accepted E": build_adopted_character_mesh(parent),
        "Review candidate 005": build_adopted_character_mesh(review005),
        "Review candidate 006": candidate_mesh,
    }
    for view in ("front", "top", "three-quarter"):
        (out / f"shoulder-pose-clearance-review-006-filled-{view}.svg").write_text(
            _filled_comparison_svg(neutral_meshes, view), encoding="utf-8"
        )
    return receipt
