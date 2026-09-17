"""Dense sampled vertex-only neighbour cone evidence for review-006 shoulders.

This is a bounded successor to the 0.25-degree vertex-only observer. It keeps
source geometry, selected topology, joints, weights and pose semantics exact,
while tightening the sampled owner-angle spacing to 0.05 degrees through the
retained +36.55-degree safe endpoint. It does not claim continuous freedom
between samples, anatomical ROM, Animation acceptance, target-host transport,
Runtime acceptance or visual acceptance.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .review006_shoulder_continuous_clearance import (
    FIRST_SAMPLED_FAILURE_DEG,
    SAFE_END_DEG,
    SAFE_START_DEG,
    _exact_inputs,
    _pose_at,
)
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    HISTORICAL_RIGGING_HEAD,
    PROFILE_SOURCE_HEAD,
    _mirror_position_set,
    _pose_pass,
    _position_set,
    release_weight,
)
from .review006_shoulder_vertex_only_neighbor_cone_margin import (
    GEOMETRY_EVIDENCE_HEAD,
    STATUS as SAMPLED_VERTEX_STATUS,
    VERTEX_CONTACT_EPSILON_RAD,
    _inspect_positions,
    _vertex_only_rows,
    audit_review006_sampled_vertex_only_neighbor_cone_margin,
)

SCHEMA = "axm.character-review006-dense-vertex-only-neighbor-cone-margin/v0.1"
STATUS = (
    "PASS_CHARACTER_REVIEW006_SAMPLED_VERTEX_ONLY_NEIGHBOR_CONE_MARGIN_"
    "005_DEG_MINUS40_TO_PLUS3655__CONTINUOUS_VERTEX_ONLY_HELD"
)
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_DENSE_VERTEX_ONLY_NEIGHBOR_CONE_MARGIN"
DENSE_STEP_DEG = 0.05
DENSE_SCALE = 20
REPRESENTATIVE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 30.0, 36.55)


def _dense_angles():
    start_tick = int(round(SAFE_START_DEG * DENSE_SCALE))
    end_tick = int(round(SAFE_END_DEG * DENSE_SCALE))
    return tuple(tick / DENSE_SCALE for tick in range(start_tick, end_tick + 1))


def dense_vertex_only_neighbor_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-dense-vertex-only-neighbor-cone-margin-001",
        "source": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
        },
        "geometry": {
            "selected_geometry_head": GEOMETRY_HEAD,
            "current_geometry_evidence_head": GEOMETRY_EVIDENCE_HEAD,
            "selected_stage": "opening_repair",
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
        },
        "rig": {
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "source_geometry_reauthored": False,
            "selected_topology_reauthored": False,
            "joint_semantics_reauthored": False,
            "weights_reauthored": False,
        },
        "dense_sampled_vertex_only_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "step_deg": DENSE_STEP_DEG,
            "sample_count_per_side": len(_dense_angles()),
            "contact_epsilon_rad": VERTEX_CONTACT_EPSILON_RAD,
            "predicate": (
                "POSITIVE_SPHERICAL_TRIANGLE_CONES_AROUND_SHARED_VERTEX_"
                "MUST_HAVE_STRICT_ANGULAR_SEPARATION"
            ),
        },
        "truth_boundary": {
            "dense_sampled_vertex_only_neighbor_contact_proven": True,
            "continuous_vertex_only_neighbor_contact_proven": False,
            "exact_first_contact_angle_solved": False,
            "anatomical_range_of_motion": False,
            "animation_acceptance": False,
            "technical_art_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_contract(contract):
    if contract != dense_vertex_only_neighbor_contract():
        raise ValueError("review-006 dense vertex-only contract identity drift")


def _sample_side(side):
    _, specimen, layout, origin, axis, faces, _ = _exact_inputs(side)
    rows = _vertex_only_rows(faces)
    if len(rows) != 845:
        raise ValueError(f"review-006 dense vertex-only pair count drift: {len(rows)}")

    minimum = math.inf
    closest = None
    failing = []
    representative_positions = {}
    representative_rows = []
    representative = set(REPRESENTATIVE_ANGLES_DEG)

    for angle in _dense_angles():
        posed = _pose_at(specimen, layout, origin, axis, angle)
        if not _pose_pass(posed):
            raise ValueError(f"review-006 dense vertex-only structural failure at {angle}")
        report = _inspect_positions(posed["positions"], rows)
        if report["uncertified_pair_count"]:
            failing.append({"angle_deg": angle, "report": report})
        if report["minimum_cone_separation_rad"] < minimum:
            minimum = report["minimum_cone_separation_rad"]
            closest = {
                "angle_deg": angle,
                "release_weight": release_weight(angle),
                **report,
            }
        if angle in representative:
            representative_positions[angle] = posed["positions"]
            representative_rows.append({
                "angle_deg": angle,
                "release_weight": release_weight(angle),
                **report,
            })

    outside = _pose_at(specimen, layout, origin, axis, FIRST_SAMPLED_FAILURE_DEG)
    outside_report = _inspect_positions(outside["positions"], rows)

    return {
        "side": side,
        "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
        "step_deg": DENSE_STEP_DEG,
        "sample_count": len(_dense_angles()),
        "vertex_only_neighbor_pair_count": len(rows),
        "uncertified_sample_count": len(failing),
        "uncertified_samples": failing[:12],
        "minimum_sampled_cone_separation_rad": minimum,
        "minimum_sampled_cone_separation_deg": math.degrees(minimum),
        "closest_sampled_cone_witness": closest,
        "representative_rows": representative_rows,
        "representative_positions": representative_positions,
        "outside_boundary": {
            "angle_deg": FIRST_SAMPLED_FAILURE_DEG,
            "release_weight": release_weight(FIRST_SAMPLED_FAILURE_DEG),
            **outside_report,
        },
    }


def audit_review006_dense_vertex_only_neighbor_cone_margin(contract=None):
    contract = contract or dense_vertex_only_neighbor_contract()
    _validate_contract(contract)

    sampled = audit_review006_sampled_vertex_only_neighbor_cone_margin()
    if sampled["status"] != SAMPLED_VERTEX_STATUS:
        raise ValueError("sampled vertex-only prerequisite is not green")

    raw = {side: _sample_side(side) for side in ("L", "R")}
    sides = {
        side: {key: value for key, value in result.items() if key != "representative_positions"}
        for side, result in raw.items()
    }
    representative_mirror = all(
        _mirror_position_set(raw["L"]["representative_positions"][angle])
        == _position_set(raw["R"]["representative_positions"][angle])
        for angle in REPRESENTATIVE_ANGLES_DEG
    )
    pair_count_match = (
        sides["L"]["vertex_only_neighbor_pair_count"]
        == sides["R"]["vertex_only_neighbor_pair_count"]
    )
    minimum_residual = abs(
        sides["L"]["minimum_sampled_cone_separation_rad"]
        - sides["R"]["minimum_sampled_cone_separation_rad"]
    )
    dense_pass = (
        pair_count_match
        and representative_mirror
        and minimum_residual <= 1e-12
        and all(side["uncertified_sample_count"] == 0 for side in sides.values())
        and all(
            side["minimum_sampled_cone_separation_rad"] > VERTEX_CONTACT_EPSILON_RAD
            for side in sides.values()
        )
    )
    outside_uncertified = all(
        side["outside_boundary"]["uncertified_pair_count"] > 0
        for side in sides.values()
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if dense_pass else FAIL_STATUS,
        "contract": contract,
        "dense_sampled_vertex_only_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "step_deg": DENSE_STEP_DEG,
            "sample_count_per_side": len(_dense_angles()),
            "all_sampled_vertex_only_pairs_cone_separated": dense_pass,
            "bilateral_pair_count_match": pair_count_match,
            "bilateral_minimum_cone_separation_residual_rad": minimum_residual,
            "bilateral_representative_pose_mirror": representative_mirror,
            "sides": sides,
        },
        "retained_boundary": {
            "first_retained_nonadjacent_failure_deg": FIRST_SAMPLED_FAILURE_DEG,
            "vertex_only_cone_predicate_uncertified_at_failure_pose_both_sides": outside_uncertified,
        },
        "negative_control": sampled["negative_control"],
        "truth_boundary": [
            "All 845 vertex-only neighbouring face pairs per shoulder are cone-separated at every 0.05-degree owner sample from -40 through +36.55 degrees.",
            "This is denser sampled evidence only; continuity between samples is still held.",
            "The +36.60 retained nonadjacent contact remains a separate failure boundary and its vertex-only cone predicate is also uncertified on both sides.",
            "No anatomical ROM, Animation, Technical Art, Runtime, gameplay, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_dense_vertex_only_neighbor_cone_margin_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    contract = dense_vertex_only_neighbor_contract()
    audit = audit_review006_dense_vertex_only_neighbor_cone_margin(contract)
    (out / "review006-dense-vertex-only-neighbor-contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "review006-dense-vertex-only-neighbor-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return audit
