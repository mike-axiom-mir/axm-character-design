"""Rigging rebind of the exact angle-conditioned shoulder release to Geometry PR #9.

This module does not change Character source, Geometry positions/topology, the
existing donor rig, Animation, runtime/controller logic, or gameplay. It only
re-runs the already-authored angle-conditioned Rigging profile against the exact
single-quad diagonal Geometry successor and keeps the remaining Geometry
intersection HOLD explicit.
"""
from __future__ import annotations

import json
from pathlib import Path

from .connected_shoulder_deformation import (
    CANDIDATE_PROXIMAL_WEIGHT,
    CONTROL_PROXIMAL_WEIGHT,
    METRIC_TOLERANCE,
    RIG_ID as DONOR_RIG_ID,
    SOURCE_DIGEST,
    SOURCE_ID,
    SOURCE_MESH_DIGEST,
    _improves_control,
    _mirror_position_set,
    _pose,
    _pose_status,
    _position_set,
    _specimen_layout,
    _weights,
    audit_connected_shoulder_deformation,
    rig_plan,
)
from .connected_shoulder_diagonal_repair import (
    SELECTED_MASK,
    STATUS as GEOMETRY_REPAIR_STATUS,
    audit_selected_diagonal_repair,
    build_diagonal_mask_specimen,
)
from .organic_form import canonical_digest, write_obj
from .self_intersection import inspect_triangle_self_intersections
from .shoulder_source_lineage import adopted_character_source

SCHEMA = "axm.character-diagonal-repair-rigging-rebind/v0.1"
STATUS = "PASS_CHARACTER_ANGLE_CONDITIONED_RELEASE_REBOUND_TO_DIAGONAL_REPAIR__HOLD_NONZERO_INTERSECTIONS"
FAIL_STATUS = "FAIL_CHARACTER_ANGLE_CONDITIONED_RELEASE_DIAGONAL_REPAIR_REBIND"

GEOMETRY_REPAIR_HEAD = "fa69eea233a56dc7e09b22c62a9e37bfa97bc994"
PREVIOUS_RIGGING_REBIND_HEAD = "ef73f87e0ebe4ce101b2fe25a92441ada7837b83"
RIGGING_PROFILE_SOURCE_HEAD = "62a60ee6b930d13898203d37b0cc9dab6b13d99d"
DONOR_RIGGING_HEAD = "b0a03cbcb61e0f8deec37172d22ff1a7fff306c9"
EXPECTED_DONOR_RIG_PLAN_DIGEST = "e1011be035f122cdbe86a8c8cf8846499ec0148d7b4adf05605d86bfac3e1f99"
SUCCESSOR_RIG_ID = "character-connected-shoulder-socket-rig-002-angle-conditioned-release"
RELEASE_PROFILE_ID = "angle-conditioned-proximal-release-power12-v1"
EXPECTED_PROFILE_DIGEST = "49e59bfd7596619a2a19454ca395276097102047af673fc4219694e777a5a719"
RELEASE_POWER = 12.0
MAX_RELEASE_WEIGHT = CANDIDATE_PROXIMAL_WEIGHT
SWEEP_ANGLES_DEG = tuple(float(value) for value in range(-40, 41))
REPRESENTATIVE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 40.0)
ANCHOR_ANGLES_DEG = (-40.0, 0.0, 40.0)
EXPECTED_ANCHOR_INTERSECTION_COUNTS = {
    "L": {-40.0: 8, 0.0: 8, 40.0: 10},
    "R": {-40.0: 8, 0.0: 8, 40.0: 10},
}


def release_weight(angle_deg: float) -> float:
    magnitude = min(abs(float(angle_deg)), 40.0)
    if magnitude == 0.0:
        return 0.0
    return MAX_RELEASE_WEIGHT * ((magnitude / 40.0) ** RELEASE_POWER)


def successor_rig_profile():
    return {
        "rig_id": SUCCESSOR_RIG_ID,
        "donor_rig_id": DONOR_RIG_ID,
        "donor_rigging_head": DONOR_RIGGING_HEAD,
        "donor_rig_plan_digest": canonical_digest(rig_plan()),
        "release_profile_id": RELEASE_PROFILE_ID,
        "release_power": RELEASE_POWER,
        "max_release_weight": MAX_RELEASE_WEIGHT,
        "control_proximal_weight": CONTROL_PROXIMAL_WEIGHT,
        "driver": "absolute_local_shoulder_angle_deg",
        "verification_envelope_deg": [-40.0, 40.0],
        "formula": "max_release_weight * (abs(angle_deg) / 40.0) ** release_power",
        "endpoint_contract": {
            "zero_deg_weight": 0.0,
            "minus_40_deg_weight": MAX_RELEASE_WEIGHT,
            "plus_40_deg_weight": MAX_RELEASE_WEIGHT,
        },
    }


def rebind_contract():
    return {
        "schema": SCHEMA,
        "source_id": SOURCE_ID,
        "source_digest": SOURCE_DIGEST,
        "source_mesh_digest": SOURCE_MESH_DIGEST,
        "geometry_repair_head": GEOMETRY_REPAIR_HEAD,
        "geometry_repair_expected_status": GEOMETRY_REPAIR_STATUS,
        "geometry_selected_mask": SELECTED_MASK,
        "previous_rigging_rebind_head": PREVIOUS_RIGGING_REBIND_HEAD,
        "rigging_profile_source_head": RIGGING_PROFILE_SOURCE_HEAD,
        "donor_rigging_head": DONOR_RIGGING_HEAD,
        "donor_rig_plan_digest": EXPECTED_DONOR_RIG_PLAN_DIGEST,
        "successor_rig_id": SUCCESSOR_RIG_ID,
        "successor_rig_profile_digest": EXPECTED_PROFILE_DIGEST,
        "sweep_angles_deg": list(SWEEP_ANGLES_DEG),
        "representative_angles_deg": list(REPRESENTATIVE_ANGLES_DEG),
        "truth_boundary": {
            "geometry_positions_unchanged": True,
            "geometry_topology_identity_changed": True,
            "rig_profile_reauthored": False,
            "remaining_intersections_are_held": True,
            "continuous_interpolation_proven": False,
            "visual_acceptance": False,
            "animation_acceptance": False,
            "runtime_acceptance": False,
        },
    }


def _validate_contract(contract):
    if contract != rebind_contract():
        raise ValueError("diagonal-repair Rigging rebind contract identity drift")
    if canonical_digest(rig_plan()) != EXPECTED_DONOR_RIG_PLAN_DIGEST:
        raise ValueError("donor rig-plan digest drift")
    if canonical_digest(successor_rig_profile()) != EXPECTED_PROFILE_DIGEST:
        raise ValueError("angle-conditioned successor profile digest drift")


def _nonworse(candidate, control):
    return (
        candidate["minimum_triangle_area_ratio"] + METRIC_TOLERANCE >= control["minimum_triangle_area_ratio"]
        and candidate["maximum_triangle_area_ratio"] <= control["maximum_triangle_area_ratio"] + METRIC_TOLERANCE
        and candidate["minimum_edge_length_ratio"] + METRIC_TOLERANCE >= control["minimum_edge_length_ratio"]
        and candidate["maximum_edge_length_ratio"] <= control["maximum_edge_length_ratio"] + METRIC_TOLERANCE
    )


def _rounded_positions(positions):
    return [[round(float(value), 9) for value in point] for point in positions]


def _representative_intersection_report(side, angle, positions, faces):
    report = inspect_triangle_self_intersections(positions, [index for face in faces for index in face])
    count = int(report["self_intersection_pair_count"])
    if angle in EXPECTED_ANCHOR_INTERSECTION_COUNTS[side]:
        expected = EXPECTED_ANCHOR_INTERSECTION_COUNTS[side][angle]
        if count != expected:
            raise ValueError(f"diagonal-repair anchor intersection count drift for {side} {angle}: {count} != {expected}")
    return {
        "side": side,
        "angle_deg": float(angle),
        "pair_count": count,
        "status": report["status"],
        "examples": report["examples"],
        "intersection_free": count == 0,
    }


def audit_diagonal_repair_rigging_rebind(contract=None):
    contract = contract or rebind_contract()
    _validate_contract(contract)

    geometry = audit_selected_diagonal_repair()
    if geometry["status"] != GEOMETRY_REPAIR_STATUS:
        raise ValueError("exact Geometry diagonal-repair prerequisite is not green")
    if geometry["sampled_intersection_comparison"]["candidate_total_pairs"] != 52:
        raise ValueError("Geometry diagonal-repair sampled intersection total drift")
    if geometry["candidate"]["selected_mask"] != SELECTED_MASK:
        raise ValueError("Geometry selected diagonal mask drift")

    donor = audit_connected_shoulder_deformation()
    source = adopted_character_source()
    if source.get("study_id") != SOURCE_ID or canonical_digest(source) != SOURCE_DIGEST:
        raise ValueError("adopted Character source identity drift")

    donor_anchors = {
        side: {float(row["angle_deg"]): row for row in donor["results"][side]["candidate"]}
        for side in ("L", "R")
    }

    all_pass = True
    results = {}
    representative_intersections = []
    for side in ("L", "R"):
        specimen = build_diagonal_mask_specimen(side, SELECTED_MASK)
        topology_digest = canonical_digest({"positions": specimen["positions"], "faces": specimen["faces"]})
        expected_digest = geometry["candidate"][f"{'left' if side == 'L' else 'right'}_topology_digest"]
        if topology_digest != expected_digest:
            raise ValueError(f"diagonal-repair topology identity drift for {side}")

        layout = _specimen_layout(source, specimen)
        control_weights = _weights(layout, CONTROL_PROXIMAL_WEIGHT)
        joint = rig_plan()["joints"][side]
        origin = tuple(source["landmarks"][joint["landmark"]])
        axis = tuple(joint["axis"])
        candidate_rows = []
        control_rows = []

        for angle in SWEEP_ANGLES_DEG:
            weight = release_weight(angle)
            candidate = _pose(specimen, origin, axis, angle, _weights(layout, weight))
            control = _pose(specimen, origin, axis, angle, control_weights)
            candidate["proximal_release_weight"] = weight
            candidate["status"] = "PASS" if _pose_status(candidate) else "FAIL"
            control["status"] = "PASS" if _pose_status(control) else "FAIL"
            candidate["nonworse_than_anchored_proximal_control"] = _nonworse(candidate, control)
            candidate["strictly_improves_anchored_proximal_control"] = (
                False if angle == 0.0 else _improves_control(candidate, control)
            )
            candidate["position_digest"] = canonical_digest(candidate["positions"])
            candidate["matches_historical_anchor_positions"] = (
                _rounded_positions(candidate["positions"]) == donor_anchors[side][angle]["positions"]
                if angle in donor_anchors[side]
                else None
            )

            all_pass &= candidate["status"] == "PASS"
            all_pass &= control["status"] == "PASS"
            all_pass &= candidate["nonworse_than_anchored_proximal_control"]
            if candidate["matches_historical_anchor_positions"] is False:
                all_pass = False

            if angle in REPRESENTATIVE_ANGLES_DEG:
                representative_intersections.append(
                    _representative_intersection_report(side, angle, candidate["positions"], specimen["faces"])
                )
            candidate_rows.append(candidate)
            control_rows.append(control)

        results[side] = {
            "topology_digest": topology_digest,
            "candidate": candidate_rows,
            "anchored_proximal_control": control_rows,
        }

    bilateral_pass = True
    for index, _angle in enumerate(SWEEP_ANGLES_DEG):
        mirrored = _mirror_position_set(results["L"]["candidate"][index]["positions"])
        observed = _position_set(results["R"]["candidate"][index]["positions"])
        same = mirrored == observed
        bilateral_pass &= same
        all_pass &= same
        results["L"]["candidate"][index]["bilateral_mirrored_position_set"] = same
        results["R"]["candidate"][index]["bilateral_mirrored_position_set"] = same

    boundary_improvement_pass = all(
        row["strictly_improves_anchored_proximal_control"]
        for side in ("L", "R")
        for row in results[side]["candidate"]
        if row["angle_deg"] in (-40.0, 40.0)
    )
    all_pass &= boundary_improvement_pass

    anchor_position_pass = all(
        row["matches_historical_anchor_positions"] is True
        for side in ("L", "R")
        for row in results[side]["candidate"]
        if row["angle_deg"] in ANCHOR_ANGLES_DEG
    )
    all_pass &= anchor_position_pass

    remaining_pairs = sum(row["pair_count"] for row in representative_intersections)
    representative_intersection_free = all(row["intersection_free"] for row in representative_intersections)

    return {
        "schema": SCHEMA,
        "status": STATUS if all_pass else FAIL_STATUS,
        "contract": contract,
        "successor_rig_profile": successor_rig_profile(),
        "dependencies": {
            "geometry_repair_status": geometry["status"],
            "geometry_repair_sampled_total_pairs": geometry["sampled_intersection_comparison"]["candidate_total_pairs"],
            "geometry_selected_mask": geometry["candidate"]["selected_mask"],
            "previous_rigging_rebind_head": PREVIOUS_RIGGING_REBIND_HEAD,
            "donor_rig_status": donor["status"],
        },
        "sample_scope": {
            "samples_per_side": len(SWEEP_ANGLES_DEG),
            "total_candidate_samples": len(SWEEP_ANGLES_DEG) * 2,
            "representative_intersection_samples": len(representative_intersections),
            "continuous_interpolation_proven": False,
        },
        "results": results,
        "representative_intersections": {
            "samples": representative_intersections,
            "pair_count_sum": remaining_pairs,
            "all_intersection_free": representative_intersection_free,
            "acceptance": "HOLD_NONZERO_INTERSECTIONS_REMAIN" if not representative_intersection_free else "PASS_REPRESENTATIVE_ONLY",
        },
        "gates": {
            "exact_character_source_identity": "PASS",
            "exact_geometry_repair_identity": "PASS",
            "exact_rig_profile_identity": "PASS",
            "all_162_structural_samples": "PASS" if all_pass else "FAIL",
            "bilateral_mirror": "PASS" if bilateral_pass else "FAIL",
            "historical_anchor_positions": "PASS" if anchor_position_pass else "FAIL",
            "boundary_strict_improvement": "PASS" if boundary_improvement_pass else "FAIL",
            "sampled_self_intersection_freedom": "HOLD_NONZERO_INTERSECTIONS_REMAIN",
            "visual_acceptance": "NOT_CLAIMED",
            "animation_acceptance": "NOT_CLAIMED",
            "runtime_acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "This rebind proves structural deformation metrics for one exact Rigging profile on one exact Geometry diagonal-repair topology identity.",
            "The one-degree sweep is discrete evidence, not mathematical proof of all real-valued intermediate poses.",
            "Representative nonadjacent self-intersection checks remain a Geometry HOLD and are not converted into a Rigging PASS.",
            "No visual, animation, exported skeleton/skin, runtime/controller, gameplay, CANON, production-readiness or mastery claim is made.",
        ],
    }


def build_diagonal_repair_rigging_rebind_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_diagonal_repair_rigging_rebind()
    (out / "diagonal-repair-rigging-rebind-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "successor-rig-profile.json").write_text(
        json.dumps(successor_rig_profile(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for side in ("L", "R"):
        specimen = build_diagonal_mask_specimen(side, SELECTED_MASK)
        rows = {row["angle_deg"]: row for row in receipt["results"][side]["candidate"]}
        for angle in REPRESENTATIVE_ANGLES_DEG:
            label = f"p{int(angle)}" if angle >= 0 else f"m{abs(int(angle))}"
            write_obj(
                {"vertices": rows[angle]["positions"], "faces": specimen["faces"], "regions": []},
                out / f"connected-shoulder-{side.lower()}-{label}-diagonal-repair-rigging-rebind.obj",
            )
    return receipt
