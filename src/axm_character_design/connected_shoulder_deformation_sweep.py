"""Rigging-owned dense deformation sweep for the exact connected Character shoulder rig.

This successor consumes Geometry PR #5's sampled self-intersection PASS and the
unchanged Rigging PR #4 plan. It does not author new weights, joints, source
geometry, animation timing, controller limits, or runtime behavior. The only new
capability is a deterministic one-degree structural sweep across the already
bounded -40..+40 degree verification envelope.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .connected_shoulder_deformation import (
    CANDIDATE_DIGESTS,
    CANDIDATE_PROXIMAL_WEIGHT,
    CONTROL_PROXIMAL_WEIGHT,
    GEOMETRY_HEAD,
    POSE_ANGLES_DEG,
    RIG_ID,
    SOURCE_DIGEST,
    SOURCE_ID,
    SOURCE_MESH_DIGEST,
    STATUS as RIGGING_STATUS,
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
from .connected_shoulder_self_intersection import (
    STATUS as SELF_INTERSECTION_STATUS,
    audit_connected_shoulder_self_intersection,
)
from .organic_form import canonical_digest
from .shoulder_connected_topology import build_connected_shoulder_specimen
from .shoulder_source_lineage import adopted_character_source

SCHEMA = "axm.character-connected-shoulder-rigging-sweep-evidence/v0.1"
STATUS = "PASS_CHARACTER_CONNECTED_SHOULDER_DENSE_DEFORMATION_SWEEP"
FAIL_STATUS = "FAIL_CHARACTER_CONNECTED_SHOULDER_DENSE_DEFORMATION_SWEEP"
SELF_INTERSECTION_HEAD = "eae6d296867ecaa40e8f5c3f1fe37d8e3019541e"
RIGGING_HEAD = "b0a03cbcb61e0f8deec37172d22ff1a7fff306c9"
SWEEP_START_DEG = -40.0
SWEEP_END_DEG = 40.0
SWEEP_STEP_DEG = 1.0
SWEEP_ANGLES_DEG = tuple(float(value) for value in range(-40, 41))
REPRESENTATIVE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 40.0)


def sweep_contract():
    return {
        "schema": SCHEMA,
        "source_id": SOURCE_ID,
        "source_digest": SOURCE_DIGEST,
        "source_mesh_digest": SOURCE_MESH_DIGEST,
        "geometry_head": GEOMETRY_HEAD,
        "self_intersection_head": SELF_INTERSECTION_HEAD,
        "rigging_head": RIGGING_HEAD,
        "rig_id": RIG_ID,
        "rig_plan_digest": canonical_digest(rig_plan()),
        "candidate_geometry_digests": dict(CANDIDATE_DIGESTS),
        "candidate_proximal_weight": CANDIDATE_PROXIMAL_WEIGHT,
        "control_proximal_weight": CONTROL_PROXIMAL_WEIGHT,
        "sweep": {
            "start_deg": SWEEP_START_DEG,
            "end_deg": SWEEP_END_DEG,
            "step_deg": SWEEP_STEP_DEG,
            "sample_count_per_side": len(SWEEP_ANGLES_DEG),
            "angles_deg": list(SWEEP_ANGLES_DEG),
            "representative_angles_deg": list(REPRESENTATIVE_ANGLES_DEG),
        },
        "truth_boundary": {
            "verification_envelope_not_anatomical_joint_limits": True,
            "finite_dense_sampling_not_mathematical_continuous_proof": True,
            "interior_self_intersection_not_checked": True,
            "animation_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
        },
    }


def _validate_contract(contract):
    expected = sweep_contract()
    if contract != expected:
        raise ValueError("connected shoulder deformation sweep contract identity drift")
    return expected


def _metric_extrema(rows):
    return {
        "minimum_triangle_area_ratio": min(row["minimum_triangle_area_ratio"] for row in rows),
        "maximum_triangle_area_ratio": max(row["maximum_triangle_area_ratio"] for row in rows),
        "minimum_edge_length_ratio": min(row["minimum_edge_length_ratio"] for row in rows),
        "maximum_edge_length_ratio": max(row["maximum_edge_length_ratio"] for row in rows),
        "maximum_fixed_socket_drift_m": max(row["fixed_socket_max_drift_m"] for row in rows),
        "maximum_rigid_arm_radius_drift_m": max(row["rigid_arm_radius_max_drift_m"] for row in rows),
        "collapsed_triangle_total": sum(row["collapsed_triangles"] for row in rows),
    }


def _write_obj(path, positions, faces):
    lines = ["# AXM retained Character connected shoulder deformation sweep pose"]
    lines.extend("v {:.12f} {:.12f} {:.12f}".format(*point) for point in positions)
    lines.extend("f {} {} {}".format(face[0] + 1, face[1] + 1, face[2] + 1) for face in faces)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def audit_connected_shoulder_deformation_sweep(contract=None):
    contract = _validate_contract(contract or sweep_contract())

    rigging = audit_connected_shoulder_deformation()
    if rigging["status"] != RIGGING_STATUS:
        raise ValueError("exact Rigging prerequisite is not green")
    if canonical_digest(rig_plan()) != contract["rig_plan_digest"]:
        raise ValueError("exact Rigging plan digest drift")

    self_intersection = audit_connected_shoulder_self_intersection()
    if self_intersection["status"] != SELF_INTERSECTION_STATUS:
        raise ValueError("exact Geometry sampled self-intersection prerequisite is not green")
    if self_intersection["producer_dependencies"]["rigging_head"] != RIGGING_HEAD:
        raise ValueError("Geometry self-intersection Rigging dependency drift")

    source = adopted_character_source()
    if source.get("study_id") != SOURCE_ID or canonical_digest(source) != SOURCE_DIGEST:
        raise ValueError("adopted Character source identity drift")

    results = {}
    all_pass = True
    for side in ("L", "R"):
        specimen = build_connected_shoulder_specimen(side)
        observed_geometry_digest = canonical_digest({
            "positions": specimen["positions"],
            "faces": specimen["faces"],
        })
        if observed_geometry_digest != CANDIDATE_DIGESTS[side]:
            raise ValueError(f"connected shoulder {side} Geometry identity drift")

        layout = _specimen_layout(source, specimen)
        candidate_weights = _weights(layout, CANDIDATE_PROXIMAL_WEIGHT)
        control_weights = _weights(layout, CONTROL_PROXIMAL_WEIGHT)
        joint = rig_plan()["joints"][side]
        origin = tuple(source["landmarks"][joint["landmark"]])
        axis = tuple(joint["axis"])

        candidate_rows = []
        control_rows = []
        original_by_angle = {
            float(row["angle_deg"]): row
            for row in rigging["results"][side]["candidate"]
        }
        for angle in SWEEP_ANGLES_DEG:
            candidate = _pose(specimen, origin, axis, angle, candidate_weights)
            control = _pose(specimen, origin, axis, angle, control_weights)
            candidate["status"] = "PASS" if _pose_status(candidate) else "FAIL"
            control["status"] = "PASS" if _pose_status(control) else "FAIL"
            candidate["improves_anchored_proximal_control"] = (
                True if angle == 0.0 else _improves_control(candidate, control)
            )
            candidate["position_digest"] = canonical_digest(candidate["positions"])
            control["position_digest"] = canonical_digest(control["positions"])

            if angle in original_by_angle:
                candidate["matches_original_rigging_anchor"] = (
                    candidate["positions"] == original_by_angle[angle]["positions"]
                )
            else:
                candidate["matches_original_rigging_anchor"] = None

            all_pass &= candidate["status"] == "PASS"
            all_pass &= control["status"] == "PASS"
            all_pass &= candidate["improves_anchored_proximal_control"]
            if candidate["matches_original_rigging_anchor"] is False:
                all_pass = False

            candidate_rows.append(candidate)
            control_rows.append(control)

        results[side] = {
            "geometry_digest": observed_geometry_digest,
            "candidate": candidate_rows,
            "anchored_proximal_control": control_rows,
            "candidate_extrema": _metric_extrema(candidate_rows),
            "control_extrema": _metric_extrema(control_rows),
        }

    bilateral_mirror_pass = True
    for index, angle in enumerate(SWEEP_ANGLES_DEG):
        left = results["L"]["candidate"][index]["positions"]
        right = results["R"]["candidate"][index]["positions"]
        mirrored = _mirror_position_set(left) == _position_set(right)
        results["L"]["candidate"][index]["bilateral_mirrored_position_set"] = mirrored
        results["R"]["candidate"][index]["bilateral_mirrored_position_set"] = mirrored
        bilateral_mirror_pass &= mirrored
        all_pass &= mirrored

    anchor_pass = all(
        row["matches_original_rigging_anchor"] is True
        for side in ("L", "R")
        for row in results[side]["candidate"]
        if row["angle_deg"] in POSE_ANGLES_DEG
    )
    all_pass &= anchor_pass

    representative = {
        side: [
            {
                "angle_deg": row["angle_deg"],
                "position_digest": row["position_digest"],
                "minimum_triangle_area_ratio": row["minimum_triangle_area_ratio"],
                "maximum_triangle_area_ratio": row["maximum_triangle_area_ratio"],
                "minimum_edge_length_ratio": row["minimum_edge_length_ratio"],
                "maximum_edge_length_ratio": row["maximum_edge_length_ratio"],
                "fixed_socket_max_drift_m": row["fixed_socket_max_drift_m"],
                "rigid_arm_radius_max_drift_m": row["rigid_arm_radius_max_drift_m"],
            }
            for row in results[side]["candidate"]
            if row["angle_deg"] in REPRESENTATIVE_ANGLES_DEG
        ]
        for side in ("L", "R")
    }

    return {
        "schema": SCHEMA,
        "status": STATUS if all_pass else FAIL_STATUS,
        "contract": contract,
        "dependencies": {
            "rigging_status": rigging["status"],
            "sampled_self_intersection_status": self_intersection["status"],
            "sampled_self_intersection_scope_angles_deg": list(POSE_ANGLES_DEG),
        },
        "sample_scope": {
            "samples_per_side": len(SWEEP_ANGLES_DEG),
            "total_candidate_samples": len(SWEEP_ANGLES_DEG) * 2,
            "angles_deg": list(SWEEP_ANGLES_DEG),
            "finite_dense_sampling": True,
            "continuous_interpolation_proven": False,
            "interior_self_intersection_checked": False,
        },
        "results": results,
        "representative": representative,
        "gates": {
            "exact_source_identity": "PASS",
            "exact_connected_geometry_identity": "PASS",
            "exact_rig_plan_identity": "PASS",
            "exact_sampled_self_intersection_prerequisite": "PASS",
            "all_162_candidate_pose_samples_structurally_green": "PASS" if all_pass else "FAIL",
            "all_nonzero_samples_improve_anchored_control": "PASS" if all(
                row["improves_anchored_proximal_control"]
                for side in ("L", "R")
                for row in results[side]["candidate"]
            ) else "FAIL",
            "original_minus40_zero_plus40_anchors_unchanged": "PASS" if anchor_pass else "FAIL",
            "bilateral_mirror_all_samples": "PASS" if bilateral_mirror_pass else "FAIL",
            "continuous_interpolation": "NOT_PROVEN_BY_FINITE_SWEEP",
            "interior_self_intersection": "NOT_CHECKED",
            "visual_quality": "NOT_CLAIMED",
            "animation_or_runtime": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "The exact Character source, connected Geometry, Rigging plan, weights, joints, axes and original -40/0/+40 poses are unchanged.",
            "This is a deterministic one-degree structural sweep across the existing verification envelope, not a new joint limit or animation clip.",
            "Finite one-degree sampling materially narrows the unobserved deformation interval but does not mathematically prove every real-valued intermediate pose.",
            "Geometry PR #5 proves nonadjacent self-intersection only at -40/0/+40; no interior self-intersection freedom is inherited or claimed here.",
            "No anatomy, volume preservation, skin sliding, visual acceptance, Animation timing/interpolation, runtime/controller, gameplay, CANON, production readiness or Rigging mastery is claimed.",
        ],
    }


def build_connected_shoulder_deformation_sweep_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_connected_shoulder_deformation_sweep()
    (out / "connected-shoulder-deformation-sweep-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    source = adopted_character_source()
    plan = rig_plan()
    for side in ("L", "R"):
        specimen = build_connected_shoulder_specimen(side)
        joint = plan["joints"][side]
        origin = tuple(source["landmarks"][joint["landmark"]])
        axis = tuple(joint["axis"])
        layout = _specimen_layout(source, specimen)
        weights = _weights(layout, CANDIDATE_PROXIMAL_WEIGHT)
        for angle in REPRESENTATIVE_ANGLES_DEG:
            posed = _pose(specimen, origin, axis, angle, weights)
            label = f"m{abs(int(angle)):02d}" if angle < 0 else f"p{int(angle):02d}"
            if angle == 0:
                label = "zero"
            _write_obj(
                out / f"character-shoulder-{side.lower()}-{label}.obj",
                posed["positions"],
                specimen["faces"],
            )

    return receipt
