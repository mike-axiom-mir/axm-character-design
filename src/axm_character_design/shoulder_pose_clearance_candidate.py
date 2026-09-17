from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path

from .organic_form import canonical_digest, mesh_checks, svg_wire, validate_study, write_obj
from .shoulder_source_lineage import (
    SOURCE_ID as PARENT_SOURCE_ID,
    adopted_character_source,
    build_adopted_character_mesh,
)

SCHEMA = "axm.character-shoulder-pose-clearance-review/v0.1"
VARIANT_ID = "character-neutral-a-shoulder-pose-clearance-review-005"
STATUS = "PASS_BOUNDED_CHARACTER_SHOULDER_POSE_CLEARANCE_REVIEW_CANDIDATE"

EXPECTED_PARENT_SOURCE_DIGEST = "dbb20e6e7dc1874b3b22553d0407791f05699f23ebb42c4e249a259f56613f1d"
EXPECTED_PARENT_MESH_DIGEST = "30a4612212f2e8252b6f813912ce76c655763e6d3abb4650c04ad1af72baea7f"
EXPECTED_CANDIDATE_SOURCE_DIGEST = "a5f9bd6ef8b783261bdbf2debac46eafc7dc972b2e6ad02e26eafc74f73092b1"
EXPECTED_CANDIDATE_MESH_DIGEST = "59ea0a3d53825af372056593f41d602082cf83ba577f2393ccb4ca8d26f40ea9"

SHOULDER_X_M = 0.23275
ELBOW_X_M = 0.51000
ELBOW_Z_M = 1.35750
SHOULDER_WIDTH_M = SHOULDER_X_M * 2.0
MAX_SEGMENT_LENGTH_DELTA_RATIO = 0.01


def _distance(a, b):
    return math.dist(tuple(float(value) for value in a), tuple(float(value) for value in b))


def shoulder_pose_clearance_candidate():
    parent = adopted_character_source()
    if parent.get("study_id") != PARENT_SOURCE_ID:
        raise ValueError("parent Character source ID drift")
    if canonical_digest(parent) != EXPECTED_PARENT_SOURCE_DIGEST:
        raise ValueError("parent Character source digest drift")
    parent_mesh = build_adopted_character_mesh(parent)
    if canonical_digest(parent_mesh) != EXPECTED_PARENT_MESH_DIGEST:
        raise ValueError("parent Character proof-mesh digest drift")

    candidate = deepcopy(parent)
    candidate["study_id"] = VARIANT_ID
    candidate["intent"] = (
        "stylized_biped_form_study_with_adopted_feathered_shoulder_transition_"
        "and_review_only_shoulder_pose_clearance"
    )

    candidate["landmarks"]["shoulder_L"][0] = -SHOULDER_X_M
    candidate["landmarks"]["shoulder_R"][0] = SHOULDER_X_M
    candidate["landmarks"]["elbow_L"][0] = -ELBOW_X_M
    candidate["landmarks"]["elbow_R"][0] = ELBOW_X_M
    candidate["landmarks"]["elbow_L"][2] = ELBOW_Z_M
    candidate["landmarks"]["elbow_R"][2] = ELBOW_Z_M
    candidate["design_constraints"]["shoulder_width_m"] = SHOULDER_WIDTH_M

    candidate["shoulder_pose_clearance_review"] = {
        "schema": SCHEMA,
        "variant_id": VARIANT_ID,
        "status": "DERIVED_REVIEW_VARIANT_NOT_ADOPTED_SOURCE",
        "parent_source_id": PARENT_SOURCE_ID,
        "parent_source_digest": EXPECTED_PARENT_SOURCE_DIGEST,
        "parent_mesh_digest": EXPECTED_PARENT_MESH_DIGEST,
        "bounded_source_delta": {
            "shoulder_lateral_magnitude_m": [0.22, SHOULDER_X_M],
            "elbow_lateral_magnitude_m": [0.48, ELBOW_X_M],
            "elbow_height_m": [1.32, ELBOW_Z_M],
            "shoulder_width_constraint_m": [0.44, SHOULDER_WIDTH_M],
            "wrists_and_hands_changed": False,
            "accepted_E_transition_semantics_changed": False,
        },
        "purpose": (
            "review whether a small bilateral shoulder/elbow pose-form rebalance can create "
            "more deformation clearance without changing the accepted feathered E transition"
        ),
        "downstream_state": "GEOMETRY_RIGGING_VISUAL_REBIND_REQUIRED",
    }
    validate_study(candidate)
    return candidate


def _normalized_back_to_parent(candidate):
    normalized = deepcopy(candidate)
    normalized.pop("shoulder_pose_clearance_review")
    parent = adopted_character_source()
    normalized["study_id"] = parent["study_id"]
    normalized["intent"] = parent["intent"]
    for name in ("shoulder_L", "shoulder_R", "elbow_L", "elbow_R"):
        normalized["landmarks"][name] = deepcopy(parent["landmarks"][name])
    normalized["design_constraints"]["shoulder_width_m"] = parent["design_constraints"]["shoulder_width_m"]
    return normalized


def audit_shoulder_pose_clearance_candidate(candidate=None):
    parent = adopted_character_source()
    parent_digest = canonical_digest(parent)
    if parent_digest != EXPECTED_PARENT_SOURCE_DIGEST:
        raise ValueError("parent Character source digest drift")
    parent_mesh = build_adopted_character_mesh(parent)
    if canonical_digest(parent_mesh) != EXPECTED_PARENT_MESH_DIGEST:
        raise ValueError("parent Character proof-mesh digest drift")

    candidate = candidate or shoulder_pose_clearance_candidate()
    validate_study(candidate)
    if candidate.get("study_id") != VARIANT_ID:
        raise ValueError("review candidate ID drift")
    if canonical_digest(_normalized_back_to_parent(candidate)) != parent_digest:
        raise ValueError("review candidate changed fields outside bounded shoulder/elbow delta")

    expected_landmarks = {
        "shoulder_L": (-SHOULDER_X_M, 0.0, 1.48),
        "shoulder_R": (SHOULDER_X_M, 0.0, 1.48),
        "elbow_L": (-ELBOW_X_M, 0.0, ELBOW_Z_M),
        "elbow_R": (ELBOW_X_M, 0.0, ELBOW_Z_M),
    }
    for name, expected in expected_landmarks.items():
        observed = tuple(float(value) for value in candidate["landmarks"][name])
        if observed != expected:
            raise ValueError(f"unexpected bounded landmark drift: {name}")
    if float(candidate["design_constraints"]["shoulder_width_m"]) != SHOULDER_WIDTH_M:
        raise ValueError("shoulder-width constraint drift")

    parent_transition = parent["shoulder_transition_repair"]
    candidate_transition = candidate["shoulder_transition_repair"]
    if candidate_transition != parent_transition:
        raise ValueError("accepted E shoulder transition semantics changed")
    if candidate["shoulder_transition_regions"] != parent["shoulder_transition_regions"]:
        raise ValueError("accepted E shoulder transition regions changed")

    candidate_mesh = build_adopted_character_mesh(candidate)
    candidate_source_digest = canonical_digest(candidate)
    candidate_mesh_digest = canonical_digest(candidate_mesh)

    parent_checks = mesh_checks(parent_mesh)
    candidate_checks = mesh_checks(candidate_mesh)
    if candidate_checks["vertex_count"] != parent_checks["vertex_count"]:
        raise ValueError("review candidate changed proof-mesh vertex count")
    if candidate_checks["triangle_count"] != parent_checks["triangle_count"]:
        raise ValueError("review candidate changed proof-mesh triangle count")
    if candidate_checks["degenerate_triangles"] != 0:
        raise ValueError("review candidate introduced degenerate proof triangles")
    if candidate_checks["bounds_min"] != parent_checks["bounds_min"]:
        raise ValueError("review candidate changed whole-body minimum bounds")
    if candidate_checks["bounds_max"] != parent_checks["bounds_max"]:
        raise ValueError("review candidate changed whole-body maximum bounds")

    parent_valid = validate_study(parent)
    candidate_valid = validate_study(candidate)

    parent_lengths = {
        "upper_arm": _distance(parent["landmarks"]["shoulder_R"], parent["landmarks"]["elbow_R"]),
        "lower_arm": _distance(parent["landmarks"]["elbow_R"], parent["landmarks"]["wrist_R"]),
    }
    candidate_lengths = {
        "upper_arm": _distance(candidate["landmarks"]["shoulder_R"], candidate["landmarks"]["elbow_R"]),
        "lower_arm": _distance(candidate["landmarks"]["elbow_R"], candidate["landmarks"]["wrist_R"]),
    }
    length_delta_ratios = {
        name: (candidate_lengths[name] / parent_lengths[name]) - 1.0
        for name in parent_lengths
    }
    if any(abs(value) > MAX_SEGMENT_LENGTH_DELTA_RATIO for value in length_delta_ratios.values()):
        raise ValueError("review candidate exceeds bounded arm-segment length delta")

    review = candidate["shoulder_pose_clearance_review"]
    if review["parent_source_digest"] != EXPECTED_PARENT_SOURCE_DIGEST:
        raise ValueError("review parent source provenance drift")
    if review["parent_mesh_digest"] != EXPECTED_PARENT_MESH_DIGEST:
        raise ValueError("review parent mesh provenance drift")
    if review["status"] != "DERIVED_REVIEW_VARIANT_NOT_ADOPTED_SOURCE":
        raise ValueError("review candidate truth-state drift")
    if review["downstream_state"] != "GEOMETRY_RIGGING_VISUAL_REBIND_REQUIRED":
        raise ValueError("review candidate downstream-state drift")
    if candidate_source_digest != EXPECTED_CANDIDATE_SOURCE_DIGEST:
        raise ValueError("review candidate source identity drift")
    if candidate_mesh_digest != EXPECTED_CANDIDATE_MESH_DIGEST:
        raise ValueError("review candidate mesh identity drift")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "variant_id": VARIANT_ID,
        "parent_source_id": PARENT_SOURCE_ID,
        "parent_source_digest": parent_digest,
        "parent_mesh_digest": EXPECTED_PARENT_MESH_DIGEST,
        "candidate_source_digest": candidate_source_digest,
        "candidate_mesh_digest": candidate_mesh_digest,
        "bounded_delta": review["bounded_source_delta"],
        "form_metrics": {
            "parent_a_rest_down_angle_deg": parent_valid["a_pose_down_angle_deg"],
            "candidate_a_rest_down_angle_deg": candidate_valid["a_pose_down_angle_deg"],
            "parent_segment_lengths_m": parent_lengths,
            "candidate_segment_lengths_m": candidate_lengths,
            "segment_length_delta_ratios": length_delta_ratios,
            "vertex_count": candidate_checks["vertex_count"],
            "triangle_count": candidate_checks["triangle_count"],
            "degenerate_triangles": candidate_checks["degenerate_triangles"],
            "bounds_min": candidate_checks["bounds_min"],
            "bounds_max": candidate_checks["bounds_max"],
        },
        "gates": {
            "exact_parent_source_identity": "PASS",
            "exact_parent_mesh_identity": "PASS",
            "bounded_landmark_delta_only": "PASS",
            "bilateral_symmetry": "PASS",
            "accepted_E_transition_semantics_preserved": "PASS",
            "exact_candidate_source_identity": "PASS",
            "exact_candidate_mesh_identity": "PASS",
            "whole_body_bounds_preserved": "PASS",
            "arm_segment_length_delta_below_1_percent": "PASS",
            "existing_A_rest_angle_gate": "PASS",
            "visual_acceptance": "NOT_EVALUATED",
            "connected_topology_rebind": "NOT_EVALUATED",
            "rigging_or_deformation_rebind": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoffs": {
            "art_direction_visual_qa": (
                "Compare the exact parent and review-candidate views. Judge shoulder width, "
                "upper-arm direction, mass hierarchy, silhouette, pinch/collar regression, "
                "and whether the rebalance still belongs to the accepted E form language."
            ),
            "geometry": (
                "Do not inherit any downstream intersection or topology claim. If the form is "
                "visually accepted, explicitly rebind the connected shoulder topology to this "
                "exact candidate source/mesh identity and rerun Geometry evidence."
            ),
            "rigging": (
                "No deformation PASS transfers. Rebind only after Geometry owns a receiving "
                "topology for this exact review candidate."
            ),
        },
        "truth_boundary": [
            "This is a derived Character Organic review candidate, not an adopted source successor.",
            "Only bilateral shoulder/elbow landmarks plus the corresponding shoulder-width metadata change; wrists, hands, masses, segment radii, flex-zone truth states and accepted E transition semantics are preserved.",
            "The exact candidate source and proof-mesh identities are pinned for retained review evidence only; pinning them is not source adoption.",
            "The existing A-rest angle gate and proof-mesh structural checks are source-form checks, not anatomy or deformation acceptance.",
            "No connected-topology, self-intersection, rigging, weighting, animation, material, target-host, runtime, gameplay, CANON, production-readiness or Organic Form mastery claim is made.",
        ],
    }


def build_shoulder_pose_clearance_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    parent = adopted_character_source()
    candidate = shoulder_pose_clearance_candidate()
    parent_mesh = build_adopted_character_mesh(parent)
    candidate_mesh = build_adopted_character_mesh(candidate)
    receipt = audit_shoulder_pose_clearance_candidate(candidate)

    (out / "shoulder-pose-clearance-review.source.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-pose-clearance-review.mesh.json").write_text(
        json.dumps(candidate_mesh, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "shoulder-pose-clearance-review-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_obj(candidate_mesh, out / "shoulder-pose-clearance-review.obj")
    for view in ("front", "side", "top"):
        (out / f"shoulder-pose-clearance-parent-{view}.svg").write_text(
            svg_wire(parent_mesh, view, f"Parent accepted E — {view}"), encoding="utf-8"
        )
        (out / f"shoulder-pose-clearance-review-{view}.svg").write_text(
            svg_wire(candidate_mesh, view, f"Review candidate 005 — {view}"), encoding="utf-8"
        )
    return receipt
