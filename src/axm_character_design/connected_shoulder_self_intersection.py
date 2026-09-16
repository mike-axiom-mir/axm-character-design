"""Geometry-owned sampled self-intersection gate over the exact Rigging successor.

This module consumes the exact connected shoulder Geometry identity through the
current Rigging evidence path, then checks only nonadjacent triangle
self-intersections at the retained -40 / 0 / +40 degree samples. It does not
rewrite Character source, Geometry, Rigging weights, or pose semantics.
"""
from __future__ import annotations

import json
from pathlib import Path

from .connected_shoulder_deformation import (
    CANDIDATE_DIGESTS,
    GEOMETRY_HEAD,
    STATUS as RIGGING_STATUS,
    audit_connected_shoulder_deformation,
)
from .organic_form import canonical_digest, write_obj
from .self_intersection import DONOR_PROVENANCE, inspect_triangle_self_intersections
from .shoulder_connected_topology import build_connected_shoulder_specimen

SCHEMA = "axm.character-connected-shoulder-self-intersection-evidence/v0.1"
STATUS = "PASS_CHARACTER_CONNECTED_SHOULDER_SAMPLED_NONADJACENT_SELF_INTERSECTION_GATE"
FAIL_STATUS = "FAIL_CHARACTER_CONNECTED_SHOULDER_SAMPLED_NONADJACENT_SELF_INTERSECTION_GATE"
RIGGING_HEAD = "b0a03cbcb61e0f8deec37172d22ff1a7fff306c9"
ANIMAL_DEFORMED_METHOD_PRECEDENT = {
    "repository": "mike-axiom-mir/axm-animal-design",
    "pr": 7,
    "head": "95b53572037ca3de98811db52beb4262a34b7d42",
    "use": "sampled deformed nonadjacent self-intersection gate precedent only; no Animal geometry or PASS inherited",
}


def _crossing_control():
    positions = [
        [0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0],
        [0.5, 0.5, -1.0], [0.5, 0.5, 1.0], [1.5, 0.5, 0.0],
    ]
    return inspect_triangle_self_intersections(positions, [0, 1, 2, 3, 4, 5])


def _coplanar_control():
    positions = [
        [0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0],
        [0.25, 0.25, 0.0], [1.25, 0.25, 0.0], [0.25, 1.25, 0.0],
    ]
    return inspect_triangle_self_intersections(positions, [0, 1, 2, 3, 4, 5])


def audit_connected_shoulder_self_intersection():
    rigging = audit_connected_shoulder_deformation()
    if rigging["status"] != RIGGING_STATUS:
        raise ValueError("exact Rigging prerequisite is not green")
    if rigging["geometry_head"] != GEOMETRY_HEAD:
        raise ValueError("Rigging Geometry dependency drift")

    samples = []
    samples_pass = True
    for side in ("L", "R"):
        specimen = build_connected_shoulder_specimen(side)
        observed_digest = canonical_digest({
            "positions": specimen["positions"],
            "faces": specimen["faces"],
        })
        if observed_digest != CANDIDATE_DIGESTS[side]:
            raise ValueError(f"connected shoulder {side} identity drift")
        for pose in rigging["results"][side]["candidate"]:
            report = inspect_triangle_self_intersections(pose["positions"], specimen["indices"])
            passed = (
                report["status"] == "PASS_NO_NONADJACENT_SELF_INTERSECTIONS"
                and report["self_intersection_pair_count"] == 0
            )
            samples_pass &= passed
            samples.append({
                "side": side,
                "angle_deg": pose["angle_deg"],
                "geometry_digest": observed_digest,
                "position_digest": canonical_digest(pose["positions"]),
                "status": "PASS" if passed else "FAIL",
                "inspection": report,
            })

    crossing = _crossing_control()
    coplanar = _coplanar_control()
    controls_pass = (
        crossing["status"] == "SELF_INTERSECTIONS_DETECTED"
        and crossing["self_intersection_pair_count"] == 1
        and coplanar["status"] == "SELF_INTERSECTIONS_DETECTED"
        and coplanar["self_intersection_pair_count"] == 1
    )
    all_pass = samples_pass and controls_pass and len(samples) == 6

    return {
        "schema": SCHEMA,
        "status": STATUS if all_pass else FAIL_STATUS,
        "producer_dependencies": {
            "geometry_head": GEOMETRY_HEAD,
            "rigging_head": RIGGING_HEAD,
            "rigging_status": rigging["status"],
            "rig_plan_digest": rigging["rig_plan_digest"],
            "left_geometry_digest": CANDIDATE_DIGESTS["L"],
            "right_geometry_digest": CANDIDATE_DIGESTS["R"],
        },
        "method_provenance": {
            "triangle_intersection_method": DONOR_PROVENANCE,
            "sampled_deformed_method_precedent": ANIMAL_DEFORMED_METHOD_PRECEDENT,
            "receiving_rule": "Character-local re-test; no donor PASS inherited and no UC extraction",
        },
        "sample_scope": {
            "sample_count": len(samples),
            "sides": ["L", "R"],
            "angles_deg": [-40.0, 0.0, 40.0],
            "continuous_interpolation_checked": False,
        },
        "samples": samples,
        "negative_controls": {
            "crossing_non_coplanar": crossing,
            "coplanar_overlap": coplanar,
            "status": "PASS_DETECTS_BOTH_CONTROL_INTERSECTIONS" if controls_pass else "FAIL_NEGATIVE_CONTROL",
        },
        "gates": {
            "exact_geometry_identity": "PASS",
            "exact_rigging_prerequisite": "PASS",
            "six_retained_samples_checked": "PASS" if len(samples) == 6 else "FAIL",
            "zero_nonadjacent_self_intersections_at_all_samples": "PASS" if samples_pass else "FAIL",
            "crossing_and_coplanar_negative_controls": "PASS" if controls_pass else "FAIL",
            "continuous_pose_range": "NOT_CHECKED",
            "topological_neighbor_foldover_or_contact": "NOT_CHECKED_BY_THIS_OBSERVER",
            "visual_seam_or_pinch_quality": "NOT_CLAIMED",
            "rigging_acceptance": "NOT_RELABELED",
            "runtime_or_gameplay": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "This is Geometry-owned nonadjacent-triangle self-intersection evidence over the exact retained Rigging candidate samples only.",
            "Triangle pairs sharing an indexed source vertex are deliberately excluded, so local adjacent fold-over/contact remains outside this gate.",
            "The three retained pose samples do not prove continuous interpolation between -40 and +40 degrees.",
            "No Character source, connected Geometry positions/faces, Rigging weights, joint axes, or pose angles are changed by this evidence layer.",
            "A detected intersection is retained as a scoped FAIL finding rather than being hidden by making evidence generation itself fail.",
            "No visual quality, anatomy, volume preservation, authored normals/tangents, Animation, runtime/controller, collision/gameplay, CANON, production readiness, game readiness, or Geometry mastery is claimed.",
        ],
    }


def build_connected_shoulder_self_intersection_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_connected_shoulder_self_intersection()

    (out / "connected-shoulder-self-intersection-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rigging = audit_connected_shoulder_deformation()
    for side in ("L", "R"):
        specimen = build_connected_shoulder_specimen(side)
        for row in rigging["results"][side]["candidate"]:
            angle = int(row["angle_deg"])
            label = f"p{angle}" if angle >= 0 else f"m{abs(angle)}"
            write_obj(
                {"vertices": row["positions"], "faces": specimen["faces"], "regions": []},
                out / f"connected-shoulder-{side.lower()}-{label}.obj",
            )
    return receipt
