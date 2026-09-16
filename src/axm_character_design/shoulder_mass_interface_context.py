from __future__ import annotations

import json
from pathlib import Path

from .flex_transition_audit import audit_flex_transitions
from .organic_form import canonical_digest
from .shoulder_pose_clearance_candidate import (
    EXPECTED_CANDIDATE_SOURCE_DIGEST,
    EXPECTED_PARENT_SOURCE_DIGEST,
    VARIANT_ID,
    shoulder_pose_clearance_candidate,
)
from .shoulder_source_lineage import SOURCE_ID as PARENT_SOURCE_ID, adopted_character_source

SCHEMA = "axm.character-shoulder-neutral-mass-interface-context/v0.1"
STATUS = "PASS_REVIEW_CANDIDATE_NEUTRAL_SHOULDER_INTERFACE_CONTEXT_RECORDED"

EXPECTED_PARENT = {
    "landmark_mass_implicit": 1.225533425816,
    "root_ring_samples_inside_or_on_mass": 2,
    "root_ring_min_mass_implicit": 0.775473643443,
    "root_ring_max_mass_implicit": 1.866689192265,
}
EXPECTED_CANDIDATE = {
    "landmark_mass_implicit": 1.325751524774,
    "root_ring_samples_inside_or_on_mass": 2,
    "root_ring_min_mass_implicit": 0.905941415897,
    "root_ring_max_mass_implicit": 1.930459580385,
}


def _shoulder_entries(audit):
    entries = {
        item["flex_zone"]: item
        for item in audit["mass_interfaces"]
        if item["flex_zone"] in {"shoulder_L", "shoulder_R"}
    }
    if set(entries) != {"shoulder_L", "shoulder_R"}:
        raise ValueError("shoulder mass-interface coverage drift")
    return entries


def _metric_subset(entry):
    return {
        "landmark_mass_implicit": entry["landmark_mass_implicit"],
        "root_ring_samples_inside_or_on_mass": entry[
            "root_ring_samples_inside_or_on_mass"
        ],
        "root_ring_min_mass_implicit": entry["root_ring_min_mass_implicit"],
        "root_ring_max_mass_implicit": entry["root_ring_max_mass_implicit"],
    }


def _assert_bilateral(entries, label):
    left = _metric_subset(entries["shoulder_L"])
    right = _metric_subset(entries["shoulder_R"])
    if left != right:
        raise ValueError(f"{label} shoulder mass-interface bilateral drift")
    return left


def audit_shoulder_mass_interface_context():
    parent = adopted_character_source()
    candidate = shoulder_pose_clearance_candidate()

    parent_digest = canonical_digest(parent)
    candidate_digest = canonical_digest(candidate)
    if parent_digest != EXPECTED_PARENT_SOURCE_DIGEST:
        raise ValueError("parent Character source identity drift")
    if candidate_digest != EXPECTED_CANDIDATE_SOURCE_DIGEST:
        raise ValueError("review candidate source identity drift")

    parent_audit = audit_flex_transitions(parent)
    candidate_audit = audit_flex_transitions(candidate)
    parent_metrics = _assert_bilateral(_shoulder_entries(parent_audit), "parent")
    candidate_metrics = _assert_bilateral(
        _shoulder_entries(candidate_audit), "candidate"
    )

    if parent_metrics != EXPECTED_PARENT:
        raise ValueError("parent neutral shoulder mass-interface context drift")
    if candidate_metrics != EXPECTED_CANDIDATE:
        raise ValueError("candidate neutral shoulder mass-interface context drift")

    if (
        candidate_metrics["root_ring_samples_inside_or_on_mass"]
        != parent_metrics["root_ring_samples_inside_or_on_mass"]
    ):
        raise ValueError("review candidate changed sampled shoulder root-ring overlap count")

    delta = {
        "landmark_mass_implicit": round(
            candidate_metrics["landmark_mass_implicit"]
            - parent_metrics["landmark_mass_implicit"],
            12,
        ),
        "root_ring_min_mass_implicit": round(
            candidate_metrics["root_ring_min_mass_implicit"]
            - parent_metrics["root_ring_min_mass_implicit"],
            12,
        ),
        "root_ring_max_mass_implicit": round(
            candidate_metrics["root_ring_max_mass_implicit"]
            - parent_metrics["root_ring_max_mass_implicit"],
            12,
        ),
    }

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "parent_source_id": PARENT_SOURCE_ID,
        "parent_source_digest": parent_digest,
        "candidate_variant_id": VARIANT_ID,
        "candidate_source_digest": candidate_digest,
        "measurement_space": "SOURCE_NEUTRAL_RIBCAGE_ELLIPSOID_CONTEXT",
        "root_ring_sample_count_per_shoulder": 10,
        "parent_shoulder_context": parent_metrics,
        "candidate_shoulder_context": candidate_metrics,
        "candidate_minus_parent": delta,
        "observation": (
            "SAME_2_OF_10_ROOT_RING_SAMPLES_INSIDE_OR_ON_RIBCAGE_WITH_MORE_"
            "EXTERIOR_ELLIPSOID_SPACE_VALUES_RECORDED_FOR_REVIEW_ONLY"
        ),
        "gates": {
            "exact_parent_source_identity": "PASS",
            "exact_candidate_source_identity": "PASS",
            "parent_flex_context_replayed": "PASS",
            "candidate_flex_context_replayed": "PASS",
            "bilateral_mass_interface_context": "PASS",
            "sampled_root_ring_inside_count_preserved": "PASS_2_OF_10_BOTH",
            "exterior_shift_interpretation": "RECORDED_NOT_AUTOMATIC_DEFECT_OR_ACCEPTANCE",
            "visual_acceptance": "NOT_EVALUATED",
            "connected_topology_rebind": "NOT_EVALUATED",
            "rigging_or_deformation_rebind": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoffs": {
            "art_direction_visual_qa": (
                "Use this only as neutral source-form context while reviewing candidate 005. "
                "The shoulder root-ring overlap sample count remains 2/10, while the root and "
                "ring sit farther outward in the source ribcage ellipsoid metric. Judge whether "
                "the resulting silhouette and accepted-E mass transition still read coherently."
            ),
            "geometry": (
                "Do not convert this neutral ellipsoid context into topology acceptance. If the "
                "form is visually accepted, rebuild and observe the connected shoulder from the "
                "exact candidate identity independently."
            ),
            "rigging": (
                "Do not infer skin reserve, volume preservation or weighting quality from these "
                "neutral root-ring samples. Rebind only after a receiving Geometry identity exists."
            ),
        },
        "truth_boundary": [
            "This reuses the existing source-form flex audit to record neutral shoulder-to-ribcage context for the already-authored review candidate; it changes no Character geometry or source semantics.",
            "Ellipsoid implicit values and ten root-ring samples are a low-resolution geometric context measure, not anatomy, tissue, joint-space, skinning-reserve or collision truth.",
            "The unchanged 2/10 inside-or-on count does not prove continuity, and the more exterior implicit values are neither automatically good nor automatically bad.",
            "No connected-topology, self-intersection, rigging, weighting, deformation, visual, animation, runtime, gameplay, CANON, production-readiness or Organic Form mastery claim is made.",
        ],
    }


def build_shoulder_mass_interface_context_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_shoulder_mass_interface_context()
    (out / "shoulder-neutral-mass-interface-context.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
