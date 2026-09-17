from __future__ import annotations

import json
import math
from pathlib import Path

from .organic_form import canonical_digest
from .shoulder_pose_clearance_candidate import (
    EXPECTED_CANDIDATE_MESH_DIGEST as EXPECTED_REVIEW005_MESH_DIGEST,
    EXPECTED_CANDIDATE_SOURCE_DIGEST as EXPECTED_REVIEW005_SOURCE_DIGEST,
    EXPECTED_PARENT_MESH_DIGEST,
    EXPECTED_PARENT_SOURCE_DIGEST,
    shoulder_pose_clearance_candidate,
)
from .shoulder_pose_clearance_refinement import (
    audit_shoulder_pose_clearance_refinement,
    shoulder_pose_clearance_refinement_candidate,
)
from .shoulder_pose_clearance_spatial_context import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    audit_shoulder_pose_clearance_spatial_context,
)
from .shoulder_source_lineage import adopted_character_source, build_adopted_character_mesh

SCHEMA = "axm.character-shoulder-review-decision-packet/v0.2"
STATUS = "PASS_EXACT_REVIEW006_ORGANIC_DECISION_PACKET_WITH_ART_DIRECTION_PREFERENCE_RETAINED"

# Geometry PR #15 is deliberately recorded only as a separate-lineage handoff.
# Its negative result applies to the accepted-E source, not to review-006.
GEOMETRY_PR15_HEAD = "31675939985aee37eaba7beea58c9443eb85b9ac"
GEOMETRY_PR15_SCOPE = (
    "accepted-E-only face-disjoint three-flip topology family exhausted; "
    "1122 candidates, 0 strict dense improvements, nonzero sampled intersections remain"
)

# External Art Direction return is pinned as coordination evidence only. Character CI
# does not impersonate or re-perform the Art review; it records the exact returned
# decision and keeps independent QA / Geometry / Rigging / source adoption separate.
ART_DIRECTION_DECISION = "PASS_ART_DIRECTION_CHARACTER_REVIEW006_NEUTRAL_FORM_PREFERENCE_023"
ART_DIRECTION_HOLD = (
    "HOLD_CHARACTER_REVIEW006_SOURCE_ADOPTION__INDEPENDENT_QA_EXACT_GEOMETRY_REBIND_AND_RIGGING_PENDING"
)
ART_DIRECTION_REVIEWED_ORGANIC_HEAD = "600fa8ee07fa31c7f9a4f237289c3d85e7a609c3"
ART_DIRECTION_COORDINATION_COMMIT = "ec9244d8d2cb75e55061060a4a737cd073df6866"
ART_DIRECTION_PACKET_BLOB = "413826284a3a80d36b514bc9ce4b54eb22edc810"
ART_DIRECTION_PR2_COMMENT_ID = 5711130272
ART_DIRECTION_RETAINED_ARTIFACT_ID = 10485067233
ART_DIRECTION_RETAINED_ARTIFACT_SHA256 = (
    "9ebee1454e2b3a76335310ed2bc151c089cc40bb4139098a9d23b892e04695e8"
)


def _distance(a, b):
    return math.dist(tuple(float(value) for value in a), tuple(float(value) for value in b))


def _changed_landmarks(parent, candidate):
    rows = []
    for name in sorted(parent["landmarks"]):
        before = parent["landmarks"][name]
        after = candidate["landmarks"][name]
        if before == after:
            continue
        rows.append(
            {
                "landmark": name,
                "parent": [float(value) for value in before],
                "review006": [float(value) for value in after],
                "delta_m": [float(after[i]) - float(before[i]) for i in range(3)],
                "distance_m": _distance(before, after),
            }
        )
    return rows


def audit_shoulder_review_decision_packet():
    parent = adopted_character_source()
    review005 = shoulder_pose_clearance_candidate()
    review006 = shoulder_pose_clearance_refinement_candidate()

    identities = {
        "accepted_E_parent_source_digest": canonical_digest(parent),
        "accepted_E_parent_mesh_digest": canonical_digest(build_adopted_character_mesh(parent)),
        "review005_source_digest": canonical_digest(review005),
        "review005_mesh_digest": canonical_digest(build_adopted_character_mesh(review005)),
        "review006_source_digest": canonical_digest(review006),
        "review006_mesh_digest": canonical_digest(build_adopted_character_mesh(review006)),
    }
    expected = {
        "accepted_E_parent_source_digest": EXPECTED_PARENT_SOURCE_DIGEST,
        "accepted_E_parent_mesh_digest": EXPECTED_PARENT_MESH_DIGEST,
        "review005_source_digest": EXPECTED_REVIEW005_SOURCE_DIGEST,
        "review005_mesh_digest": EXPECTED_REVIEW005_MESH_DIGEST,
        "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
        "review006_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
    }
    if identities != expected:
        raise ValueError("shoulder review decision packet identity drift")

    refinement = audit_shoulder_pose_clearance_refinement(review006)
    spatial = audit_shoulder_pose_clearance_spatial_context(review006)
    if refinement["candidate_source_digest"] != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 refinement receipt identity drift")
    if spatial["identities"]["review006_source_digest"] != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 spatial receipt identity drift")

    changed = _changed_landmarks(parent, review006)
    changed_names = [row["landmark"] for row in changed]
    expected_changed = ["elbow_L", "elbow_R", "shoulder_L", "shoulder_R"]
    if changed_names != expected_changed:
        raise ValueError(f"unexpected review-006 landmark delta set: {changed_names}")

    form_metrics = refinement["form_metrics"]
    spatial_delta = spatial["review006_vs_review005"]
    review006_spatial = spatial["review006"]["right"]
    parent_spatial = spatial["accepted_E_parent"]["right"]

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "identities": identities,
        "form_is_frozen": True,
        "source_adoption": "NOT_CLAIMED",
        "changed_landmarks_from_accepted_E_parent": changed,
        "exact_form_context": {
            "accepted_E_parent_elbow_flexion_from_straight_deg": 2.082565279731,
            "review005_elbow_flexion_from_straight_deg": form_metrics[
                "review005_flexion_from_straight_deg"
            ],
            "review006_elbow_flexion_from_straight_deg": form_metrics[
                "candidate_flexion_from_straight_deg"
            ],
            "review005_minus_review006_flexion_deg": form_metrics[
                "review005_minus_candidate_flexion_deg"
            ],
            "accepted_E_parent_elbow_chord_offset_m": parent_spatial[
                "elbow_perpendicular_offset_from_chord_m"
            ],
            "review006_elbow_chord_offset_m": review006_spatial[
                "elbow_perpendicular_offset_from_chord_m"
            ],
            "review006_vs_review005_elbow_chord_offset_reduction_m": spatial_delta[
                "elbow_perpendicular_offset_reduction_m"
            ],
            "review006_vs_review005_elbow_chord_offset_reduction_ratio": spatial_delta[
                "elbow_perpendicular_offset_reduction_ratio"
            ],
            "review006_a_rest_down_angle_deg": form_metrics[
                "candidate_a_rest_down_angle_deg"
            ],
            "proof_vertex_count": form_metrics["vertex_count"],
            "proof_triangle_count": form_metrics["triangle_count"],
            "proof_degenerate_triangles": form_metrics["degenerate_triangles"],
        },
        "retained_visual_review_surfaces": [
            "shoulder-pose-clearance-review-006-filled-front.svg",
            "shoulder-pose-clearance-review-006-filled-top.svg",
            "shoulder-pose-clearance-review-006-filled-three-quarter.svg",
            "shoulder-pose-clearance-review-006-spatial-context.svg",
            "shoulder-pose-clearance-elbow-chain-front.svg",
        ],
        "art_direction_return": {
            "owner": "3D Art Director",
            "decision": ART_DIRECTION_DECISION,
            "companion_hold": ART_DIRECTION_HOLD,
            "reviewed_organic_head": ART_DIRECTION_REVIEWED_ORGANIC_HEAD,
            "reviewed_review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "reviewed_review006_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "coordination_commit": ART_DIRECTION_COORDINATION_COMMIT,
            "direction_packet_blob": ART_DIRECTION_PACKET_BLOB,
            "character_pr2_comment_id": ART_DIRECTION_PR2_COMMENT_ID,
            "retained_artifact_id": ART_DIRECTION_RETAINED_ARTIFACT_ID,
            "retained_artifact_sha256": ART_DIRECTION_RETAINED_ARTIFACT_SHA256,
            "scope": (
                "visual source-form preference only; review-006 preferred over accepted-E and review-005; "
                "no source adoption, topology/intersection, anatomy, deformation, runtime or mastery transfer"
            ),
            "required_order": [
                "independent_visual_qa",
                "exact_review006_geometry_rebind",
                "rigging_deformation_rebind_after_geometry",
                "source_adoption_decision",
            ],
        },
        "art_qa_decision_questions": [
            "Independent QA: does the exact retained review-006 packet reproduce the Art-reviewed form identity without corruption?",
            "Independent QA: does review-006 preserve the accepted-E shoulder mass language without an overbuilt upper-torso read?",
            "Independent QA: does the wider shoulder / revised elbow relationship remain coherent across front, top and three-quarter views?",
            "Independent QA: is any concrete Organic-owned defect visible that would justify reopening form mutation?",
        ],
        "separate_geometry_context": {
            "geometry_pr15_head": GEOMETRY_PR15_HEAD,
            "scope": GEOMETRY_PR15_SCOPE,
            "inheritance": "FORBIDDEN",
            "required_if_review006_selected": (
                "Geometry must bind exact review-006 source/mesh identities and rerun connected-topology "
                "and nonadjacent-intersection evidence from scratch before Rigging receives it."
            ),
        },
        "gates": {
            "exact_parent_review005_review006_identity": "PASS",
            "review006_form_changed_by_this_packet": "NO",
            "art_direction_form_preference": ART_DIRECTION_DECISION,
            "independent_visual_qa": "PENDING",
            "visual_acceptance": "NOT_EVALUATED",
            "combined_visual_acceptance": "NOT_CLAIMED",
            "connected_topology_or_self_intersection": "NOT_EVALUATED",
            "rigging_or_deformation": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "This packet aggregates exact Organic source-form evidence for review; it does not modify Character form, topology, weights, poses, materials or runtime state.",
            "The Art Direction return is an exact coordination reference to a visual source-form preference; Character CI records it but does not impersonate or re-perform Art review.",
            "Independent Visual QA remains pending; Art preference is not renamed combined visual acceptance or source adoption.",
            "Landmark angles, distances and offsets are geometric review facts, not anatomy, biology, skeletal-rest-angle or range-of-motion prescriptions.",
            "Geometry PR #15 remains negative evidence for the accepted-E lineage only and is not transferred to review-006.",
            "No source adoption, topology/intersection freedom, rigging, continuous deformation, Animation, runtime, gameplay, CANON, production readiness or Organic mastery is claimed.",
        ],
    }


def build_shoulder_review_decision_packet_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_shoulder_review_decision_packet()
    (out / "shoulder-review-decision-packet.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
