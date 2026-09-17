from __future__ import annotations

import json
import math
from pathlib import Path

from .organic_form import canonical_digest
from .shoulder_pose_clearance_candidate import (
    EXPECTED_CANDIDATE_SOURCE_DIGEST,
    EXPECTED_PARENT_SOURCE_DIGEST,
    VARIANT_ID,
    shoulder_pose_clearance_candidate,
)
from .shoulder_source_lineage import SOURCE_ID as PARENT_SOURCE_ID, adopted_character_source

SCHEMA = "axm.character-shoulder-pose-elbow-chain-context/v0.1"
STATUS = "PASS_REVIEW005_NEUTRAL_ELBOW_CHAIN_CONTEXT_RECORDED"

EXPECTED_PARENT = {
    "landmark_internal_angle_deg": 177.917434720269,
    "landmark_flexion_from_straight_deg": 2.082565279731,
}
EXPECTED_CANDIDATE = {
    "landmark_internal_angle_deg": 159.238398196942,
    "landmark_flexion_from_straight_deg": 20.761601803058,
}
EXPECTED_FLEXION_INCREASE_DEG = 18.679036523327


def _angle_deg(a, b, c):
    ba = tuple(float(a[i]) - float(b[i]) for i in range(3))
    bc = tuple(float(c[i]) - float(b[i]) for i in range(3))
    ba_len = math.sqrt(sum(value * value for value in ba))
    bc_len = math.sqrt(sum(value * value for value in bc))
    if ba_len <= 0.0 or bc_len <= 0.0:
        raise ValueError("zero-length landmark chain segment")
    cosine = sum(ba[i] * bc[i] for i in range(3)) / (ba_len * bc_len)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def _bilateral_elbow_context(source, label):
    metrics = {}
    for side in ("L", "R"):
        landmarks = source["landmarks"]
        internal = _angle_deg(
            landmarks[f"shoulder_{side}"],
            landmarks[f"elbow_{side}"],
            landmarks[f"wrist_{side}"],
        )
        metrics[side] = {
            "landmark_internal_angle_deg": round(internal, 12),
            "landmark_flexion_from_straight_deg": round(180.0 - internal, 12),
        }
    if metrics["L"] != metrics["R"]:
        raise ValueError(f"{label} elbow landmark-chain bilateral drift")
    return metrics["L"]


def audit_shoulder_pose_elbow_chain_context():
    parent = adopted_character_source()
    candidate = shoulder_pose_clearance_candidate()

    parent_digest = canonical_digest(parent)
    candidate_digest = canonical_digest(candidate)
    if parent_digest != EXPECTED_PARENT_SOURCE_DIGEST:
        raise ValueError("parent Character source identity drift")
    if candidate_digest != EXPECTED_CANDIDATE_SOURCE_DIGEST:
        raise ValueError("review candidate source identity drift")

    parent_metrics = _bilateral_elbow_context(parent, "parent")
    candidate_metrics = _bilateral_elbow_context(candidate, "candidate")
    if parent_metrics != EXPECTED_PARENT:
        raise ValueError("parent neutral elbow landmark-chain context drift")
    if candidate_metrics != EXPECTED_CANDIDATE:
        raise ValueError("candidate neutral elbow landmark-chain context drift")

    flexion_increase = round(
        candidate_metrics["landmark_flexion_from_straight_deg"]
        - parent_metrics["landmark_flexion_from_straight_deg"],
        12,
    )
    if flexion_increase != EXPECTED_FLEXION_INCREASE_DEG:
        raise ValueError("review candidate elbow landmark-chain delta drift")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "parent_source_id": PARENT_SOURCE_ID,
        "parent_source_digest": parent_digest,
        "candidate_variant_id": VARIANT_ID,
        "candidate_source_digest": candidate_digest,
        "measurement_space": "SOURCE_NEUTRAL_SHOULDER_ELBOW_WRIST_LANDMARK_CHAIN",
        "bilateral_source_context": True,
        "parent_elbow_chain_context": parent_metrics,
        "candidate_elbow_chain_context": candidate_metrics,
        "candidate_minus_parent_flexion_from_straight_deg": flexion_increase,
        "observation": (
            "REVIEW005_RECORDS_18P679_DEG_MORE_NEUTRAL_ELBOW_LANDMARK_CHAIN_BEND_"
            "THAN_ACCEPTED_E_PARENT"
        ),
        "gates": {
            "exact_parent_source_identity": "PASS",
            "exact_candidate_source_identity": "PASS",
            "bilateral_elbow_chain_context": "PASS",
            "landmark_chain_change_interpretation": (
                "RECORDED_NOT_AUTOMATIC_DEFECT_OR_ACCEPTANCE"
            ),
            "visual_acceptance": "NOT_EVALUATED",
            "connected_topology_rebind": "NOT_EVALUATED",
            "rigging_or_joint_rest_acceptance": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoffs": {
            "art_direction_visual_qa": (
                "Review candidate 005 with the exact filled A/B packet knowing that its source "
                "landmark chain changes from 2.082565 deg to 20.761602 deg flexion from straight "
                "at each elbow. Judge whether that neutral A-rest bend still belongs to the "
                "accepted E form language; do not treat this metric as an automatic defect."
            ),
            "geometry": (
                "Do not infer intersection freedom or connected-topology acceptance from the "
                "landmark-chain angle. If candidate 005 is visually accepted, bind its exact "
                "source identity and rerun Geometry independently."
            ),
            "rigging": (
                "This is source landmark-chain context, not a skeleton joint-rest-angle PASS or "
                "range-of-motion prescription. If candidate 005 advances, explicitly rebind "
                "rest-pose/deformation evidence rather than inheriting the parent result."
            ),
        },
        "truth_boundary": [
            "This activation records a neutral shoulder-elbow-wrist landmark-chain angle for the already-authored review candidate and changes no Character source or proof geometry.",
            "The measured angle is a source-form landmark relationship, not anatomical validation, a skeletal joint-rest angle, muscle/tendon behavior, range of motion, or a deformation-quality verdict.",
            "The larger neutral bend can help reviewers understand what changed visually, but it is neither automatically good nor automatically bad.",
            "No connected-topology, self-intersection, rigging, weighting, animation, runtime, gameplay, CANON, production-readiness or Organic Form mastery claim is made.",
        ],
    }


def build_shoulder_pose_elbow_chain_context_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_shoulder_pose_elbow_chain_context()
    (out / "shoulder-pose-elbow-chain-context.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
