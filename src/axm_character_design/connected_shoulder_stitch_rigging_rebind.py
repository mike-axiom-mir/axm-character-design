"""Rigging rebind of the exact angle-conditioned shoulder release to Geometry PR #11.

This module changes no Character source, vertex positions, joint definitions,
weighting profile, Animation, runtime/controller logic, or gameplay. Geometry
PR #11 changes exactly four face records in the existing ribcage-to-seam stitch,
so the previous Rigging PR #10 deformation PASS cannot transfer by equivalence.
The bounded job here is to rerun that exact rig/profile against the new topology,
prove the complete retained one-degree pose field stays identical in position,
and keep Geometry's remaining nonadjacent-intersection HOLD explicit.
"""
from __future__ import annotations

import json
from pathlib import Path

from .connected_shoulder_deformation import (
    CONTROL_PROXIMAL_WEIGHT,
    METRIC_TOLERANCE,
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
    rig_plan,
)
from .connected_shoulder_diagonal_rigging_rebind import (
    ANCHOR_ANGLES_DEG,
    EXPECTED_DONOR_RIG_PLAN_DIGEST,
    EXPECTED_PROFILE_DIGEST,
    REPRESENTATIVE_ANGLES_DEG,
    RIGGING_PROFILE_SOURCE_HEAD,
    STATUS as PREVIOUS_RIGGING_STATUS,
    SUCCESSOR_RIG_ID,
    SWEEP_ANGLES_DEG,
    audit_diagonal_repair_rigging_rebind,
    release_weight,
    successor_rig_profile,
)
from .connected_shoulder_stitch_edge_repair import (
    STATUS as GEOMETRY_STITCH_STATUS,
    TARGET_FACE_PAIRS,
    audit_stitch_edge_repair,
    build_stitch_edge_repair_specimen,
)
from .organic_form import canonical_digest, write_obj
from .self_intersection import inspect_triangle_self_intersections
from .shoulder_source_lineage import adopted_character_source

SCHEMA = "axm.character-stitch-edge-rigging-rebind/v0.1"
STATUS = (
    "PASS_CHARACTER_ANGLE_CONDITIONED_RELEASE_REBOUND_TO_STITCH_EDGE_REPAIR"
    "__HOLD_NONZERO_INTERSECTIONS"
)
FAIL_STATUS = "FAIL_CHARACTER_ANGLE_CONDITIONED_RELEASE_STITCH_EDGE_REBIND"

GEOMETRY_STITCH_REPAIR_HEAD = "b65d73e514c23670204915bde8ce935a3b417574"
PREVIOUS_RIGGING_REBIND_HEAD = "e5b129ba936f252946f48921be5a3096d8c2f801"
EXPECTED_GEOMETRY_DENSE_PAIR_SUM = 1020
EXPECTED_REPRESENTATIVE_INTERSECTION_COUNTS = {
    "L": {-40.0: 6, -20.0: 6, 0.0: 6, 20.0: 6, 40.0: 10},
    "R": {-40.0: 6, -20.0: 6, 0.0: 6, 20.0: 6, 40.0: 10},
}


def rebind_contract():
    return {
        "schema": SCHEMA,
        "source_id": SOURCE_ID,
        "source_digest": SOURCE_DIGEST,
        "source_mesh_digest": SOURCE_MESH_DIGEST,
        "geometry_stitch_repair_head": GEOMETRY_STITCH_REPAIR_HEAD,
        "geometry_stitch_expected_status": GEOMETRY_STITCH_STATUS,
        "geometry_target_face_pairs": [list(pair) for pair in TARGET_FACE_PAIRS],
        "previous_rigging_rebind_head": PREVIOUS_RIGGING_REBIND_HEAD,
        "previous_rigging_expected_status": PREVIOUS_RIGGING_STATUS,
        "rigging_profile_source_head": RIGGING_PROFILE_SOURCE_HEAD,
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
        raise ValueError("stitch-edge Rigging rebind contract identity drift")
    if canonical_digest(rig_plan()) != EXPECTED_DONOR_RIG_PLAN_DIGEST:
        raise ValueError("donor rig-plan digest drift")
    if canonical_digest(successor_rig_profile()) != EXPECTED_PROFILE_DIGEST:
        raise ValueError("angle-conditioned successor profile digest drift")


def _nonworse(candidate, control):
    return (
        candidate["minimum_triangle_area_ratio"] + METRIC_TOLERANCE
        >= control["minimum_triangle_area_ratio"]
        and candidate["maximum_triangle_area_ratio"]
        <= control["maximum_triangle_area_ratio"] + METRIC_TOLERANCE
        and candidate["minimum_edge_length_ratio"] + METRIC_TOLERANCE
        >= control["minimum_edge_length_ratio"]
        and candidate["maximum_edge_length_ratio"]
        <= control["maximum_edge_length_ratio"] + METRIC_TOLERANCE
    )


def _rounded_positions(positions):
    return [[round(float(value), 9) for value in point] for point in positions]


def _representative_intersection_report(side, angle, positions, faces):
    report = inspect_triangle_self_intersections(
        positions, [index for face in faces for index in face], max_examples=64
    )
    count = int(report["self_intersection_pair_count"])
    expected = EXPECTED_REPRESENTATIVE_INTERSECTION_COUNTS[side][float(angle)]
    if count != expected:
        raise ValueError(
            f"stitch-edge representative intersection count drift for {side} {angle}: "
            f"{count} != {expected}"
        )
    return {
        "side": side,
        "angle_deg": float(angle),
        "pair_count": count,
        "status": report["status"],
        "examples": report["examples"],
        "intersection_free": count == 0,
    }


def audit_stitch_edge_rigging_rebind(contract=None):
    contract = contract or rebind_contract()
    _validate_contract(contract)

    geometry = audit_stitch_edge_repair()
    if geometry["status"] != GEOMETRY_STITCH_STATUS:
        raise ValueError("exact Geometry stitch-edge prerequisite is not green")
    dense = geometry["dense_sweep"]
    if dense["candidate_pair_count_sum"] != EXPECTED_GEOMETRY_DENSE_PAIR_SUM:
        raise ValueError("Geometry stitch-edge dense intersection total drift")
    if dense["worse_samples"] != 0 or dense["strictly_reduced_samples"] != 150:
        raise ValueError("Geometry stitch-edge dense relation distribution drift")

    previous = audit_diagonal_repair_rigging_rebind()
    if previous["status"] != PREVIOUS_RIGGING_STATUS:
        raise ValueError("exact previous Rigging rebind prerequisite is not green")

    source = adopted_character_source()
    if source.get("study_id") != SOURCE_ID or canonical_digest(source) != SOURCE_DIGEST:
        raise ValueError("adopted Character source identity drift")

    previous_rows = {
        side: {float(row["angle_deg"]): row for row in previous["results"][side]["candidate"]}
        for side in ("L", "R")
    }

    all_pass = True
    results = {}
    representative_intersections = []
    for side in ("L", "R"):
        specimen = build_stitch_edge_repair_specimen(side)
        geometry_digest = geometry["selection"][
            f"{'left' if side == 'L' else 'right'}_topology_digest"
        ]
        if specimen["topology_digest"] != geometry_digest:
            raise ValueError(f"stitch-edge topology identity drift for {side}")

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

            previous_row = previous_rows[side][float(angle)]
            candidate["matches_previous_rigging_pose_field"] = (
                candidate["position_digest"] == previous_row["position_digest"]
                and _rounded_positions(candidate["positions"])
                == _rounded_positions(previous_row["positions"])
            )
            candidate["matches_historical_anchor_positions"] = (
                previous_row.get("matches_historical_anchor_positions") is True
                if angle in ANCHOR_ANGLES_DEG
                else None
            )

            all_pass &= candidate["status"] == "PASS"
            all_pass &= control["status"] == "PASS"
            all_pass &= candidate["nonworse_than_anchored_proximal_control"]
            all_pass &= candidate["matches_previous_rigging_pose_field"]
            if candidate["matches_historical_anchor_positions"] is False:
                all_pass = False

            if angle in REPRESENTATIVE_ANGLES_DEG:
                representative_intersections.append(
                    _representative_intersection_report(
                        side, angle, candidate["positions"], specimen["faces"]
                    )
                )
            candidate_rows.append(candidate)
            control_rows.append(control)

        results[side] = {
            "topology_digest": specimen["topology_digest"],
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

    pose_field_identity_pass = all(
        row["matches_previous_rigging_pose_field"]
        for side in ("L", "R")
        for row in results[side]["candidate"]
    )
    all_pass &= pose_field_identity_pass

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
    representative_intersection_free = all(
        row["intersection_free"] for row in representative_intersections
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if all_pass else FAIL_STATUS,
        "contract": contract,
        "successor_rig_profile": successor_rig_profile(),
        "dependencies": {
            "geometry_stitch_status": geometry["status"],
            "geometry_stitch_dense_pair_sum": dense["candidate_pair_count_sum"],
            "geometry_stitch_strictly_reduced_samples": dense["strictly_reduced_samples"],
            "previous_rigging_status": previous["status"],
            "previous_rigging_rebind_head": PREVIOUS_RIGGING_REBIND_HEAD,
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
            "acceptance": (
                "HOLD_NONZERO_INTERSECTIONS_REMAIN"
                if not representative_intersection_free
                else "PASS_REPRESENTATIVE_ONLY"
            ),
        },
        "gates": {
            "exact_character_source_identity": "PASS",
            "exact_geometry_stitch_identity": "PASS",
            "exact_rig_profile_identity": "PASS",
            "all_162_structural_samples": "PASS" if all_pass else "FAIL",
            "all_162_pose_positions_match_previous_rigging_field": (
                "PASS" if pose_field_identity_pass else "FAIL"
            ),
            "bilateral_mirror": "PASS" if bilateral_pass else "FAIL",
            "historical_anchor_positions": "PASS" if anchor_position_pass else "FAIL",
            "boundary_strict_improvement": "PASS" if boundary_improvement_pass else "FAIL",
            "sampled_self_intersection_freedom": "HOLD_NONZERO_INTERSECTIONS_REMAIN",
            "visual_acceptance": "NOT_CLAIMED",
            "animation_acceptance": "NOT_CLAIMED",
            "runtime_acceptance": "NOT_CLAIMED",
        },
        "handoffs": {
            "geometry": (
                "The exact angle-conditioned Rigging profile survives this exact four-face "
                "retessellation, but all retained representative poses still contain "
                "nonadjacent intersections. Geometry owns any further topology repair."
            ),
            "animation": (
                "No Animation acceptance transfers. Animation may consume this chain only "
                "after explicitly rebinding its own clip/playback evidence to this exact head."
            ),
            "visual_observer_art_direction": (
                "Structural deformation and exact pose-field continuity are not visual seam, "
                "silhouette, volume, or anatomy acceptance. Inspect retained poses directly."
            ),
        },
        "truth_boundary": [
            "This rebind proves one exact Rigging profile on one exact Geometry stitch-edge topology identity.",
            "All 162 discrete posed vertex-position sets match the previous Rigging PR #10 field; changed face membership still required the deformation-metric rerun performed here.",
            "The one-degree sweep is finite sampled evidence, not mathematical proof of all real-valued intermediate poses.",
            "Representative nonadjacent self-intersections remain a Geometry HOLD and are not converted into a Rigging PASS.",
            "No visual, Animation, exported skeleton/skin, runtime/controller, gameplay, CANON, production-readiness or mastery claim is made.",
        ],
    }


def build_stitch_edge_rigging_rebind_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_stitch_edge_rigging_rebind()
    (out / "stitch-edge-rigging-rebind-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "successor-rig-profile.json").write_text(
        json.dumps(successor_rig_profile(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "rebind-contract.json").write_text(
        json.dumps(rebind_contract(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for side in ("L", "R"):
        specimen = build_stitch_edge_repair_specimen(side)
        rows = {
            float(row["angle_deg"]): row
            for row in receipt["results"][side]["candidate"]
        }
        for angle in REPRESENTATIVE_ANGLES_DEG:
            label = f"p{int(angle)}" if angle >= 0 else f"m{abs(int(angle))}"
            write_obj(
                {
                    "vertices": rows[float(angle)]["positions"],
                    "faces": specimen["faces"],
                    "regions": [],
                },
                out / f"connected-shoulder-{side.lower()}-{label}-stitch-rigging-rebind.obj",
            )
    return receipt
