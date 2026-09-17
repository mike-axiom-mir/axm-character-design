"""Rigging-owned neutral bind-frame closure proof for Character review-006.

The current downstream blocker is a large target-host shaded mismatch at the exact
neutral pose even though source-side POSITION/NORMAL payloads and unshaded
coverage are nearly coincident. This module adds the smallest Rigging-owned
constraint useful to that diagnosis: at the owner rig's exact 0 degree pose,
every review-006 receiver vertex must close to its source position and every
local deformation-gradient / inverse-transpose normal map must close to the
identity transform.

This is deliberately a source-owner constraint only. It does not explain a
target-engine importer/render mismatch, choose production normals/tangents,
retime Animation, alter the rig profile, or grant Runtime/visual acceptance.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .review006_connected_geometry import build_opening_repair
from .review006_shoulder_deformation_gradient_frame import (
    STATUS as FRAME_STATUS,
    audit_review006_deformation_gradient_frame,
    deformation_gradient,
    normal_matrix,
)
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    HISTORICAL_RIGGING_HEAD,
    PROFILE_SOURCE_HEAD,
    _pose,
    _reindexed_layout,
    _weights,
    rebind_contract,
    release_weight,
)
from .shoulder_pose_clearance_refinement import shoulder_pose_clearance_refinement_candidate

SCHEMA = "axm.character-review006-rig-neutral-bind-frame-closure/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_NEUTRAL_BIND_FRAME_CLOSURE__STRUCTURAL_BOUNDARY_UNCHANGED"
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_NEUTRAL_BIND_FRAME_CLOSURE"
OWNER_FRAME_PARENT_HEAD = "a218b2cf2727482a78db8ab21afcf1bb72637bcc"
NEUTRAL_ANGLE_DEG = 0.0
NEUTRAL_TOLERANCE = 1e-12
NEGATIVE_CONTROL_HIDDEN_ANGLE_DEG = 0.25
NEGATIVE_CONTROL_MIN_VERTEX_DRIFT_M = 1e-5
NEGATIVE_CONTROL_MIN_MATRIX_DELTA = 1e-4


def _identity():
    return (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def _matrix_component_max_delta(first, second):
    return max(
        abs(float(first[row][column]) - float(second[row][column]))
        for row in range(3)
        for column in range(3)
    )


def neutral_bind_frame_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-owner-neutral-bind-frame-closure-001",
        "source": {
            "source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
        },
        "geometry": {
            "head": GEOMETRY_HEAD,
            "selected_stage": "opening_repair",
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
        },
        "rig": {
            "owner_frame_parent_head": OWNER_FRAME_PARENT_HEAD,
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "neutral_angle_deg": NEUTRAL_ANGLE_DEG,
            "neutral_proximal_release_weight": release_weight(NEUTRAL_ANGLE_DEG),
            "profile_reauthored": False,
            "weights_reauthored": False,
            "joint_semantics_reauthored": False,
        },
        "verification": {
            "neutral_tolerance": NEUTRAL_TOLERANCE,
            "negative_control_hidden_angle_deg": NEGATIVE_CONTROL_HIDDEN_ANGLE_DEG,
        },
        "truth_boundary": {
            "owner_neutral_position_closure": True,
            "owner_neutral_gradient_identity": True,
            "owner_neutral_normal_matrix_identity": True,
            "target_engine_bind_or_inverse_bind_evaluated": False,
            "target_engine_direction_frame_evaluated": False,
            "neutral_shaded_mismatch_explained": False,
            "animation_acceptance": False,
            "technical_art_target_host_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_exact_identity():
    if rebind_contract()["rig_method"]["profile_digest"] != EXPECTED_PROFILE_DIGEST:
        raise ValueError("review-006 Rigging profile identity drift")
    if release_weight(NEUTRAL_ANGLE_DEG) != 0.0:
        raise ValueError("review-006 neutral proximal release weight must remain exactly zero")
    frame = audit_review006_deformation_gradient_frame()
    if frame["status"] != FRAME_STATUS:
        raise ValueError("review-006 owner deformation-gradient prerequisite is not green")
    return shoulder_pose_clearance_refinement_candidate(), frame


def audit_review006_neutral_bind_frame(contract=None):
    contract = contract or neutral_bind_frame_contract()
    if contract != neutral_bind_frame_contract():
        raise ValueError("review-006 neutral bind-frame contract identity drift")

    source, frame = _validate_exact_identity()
    rig = rebind_contract()
    identity = _identity()
    group_rows = []
    side_rows = []
    total_vertices = 0
    max_vertex_drift = 0.0
    max_gradient_identity_delta = 0.0
    max_normal_identity_delta = 0.0

    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        layout = _reindexed_layout(side, specimen)
        joint = rig["rig_method"]["joint_semantics"][side]
        origin = tuple(float(value) for value in source["landmarks"][joint["landmark"]])
        axis = tuple(float(value) for value in joint["axis"])
        weights = _weights(layout, release_weight(NEUTRAL_ANGLE_DEG), len(specimen["positions"]))
        posed = _pose(specimen, origin, axis, NEUTRAL_ANGLE_DEG, weights)

        side_max_vertex_drift = max(
            math.dist(tuple(float(v) for v in before), tuple(float(v) for v in after))
            for before, after in zip(specimen["positions"], posed["positions"])
        )
        total_vertices += len(specimen["positions"])
        max_vertex_drift = max(max_vertex_drift, side_max_vertex_drift)

        for group_name, indexes in layout["groups"].items():
            group_weights = {float(weights[index]) for index in indexes}
            if len(group_weights) != 1:
                raise ValueError(f"neutral group {group_name} has mixed child weights")
            child_weight = next(iter(group_weights))
            gradient = deformation_gradient(axis, NEUTRAL_ANGLE_DEG, child_weight)
            normal = normal_matrix(axis, NEUTRAL_ANGLE_DEG, child_weight)
            gradient_delta = _matrix_component_max_delta(gradient, identity)
            normal_delta = _matrix_component_max_delta(normal, identity)
            group_vertex_drift = max(
                math.dist(
                    tuple(float(v) for v in specimen["positions"][index]),
                    tuple(float(v) for v in posed["positions"][index]),
                )
                for index in indexes
            )
            max_gradient_identity_delta = max(max_gradient_identity_delta, gradient_delta)
            max_normal_identity_delta = max(max_normal_identity_delta, normal_delta)
            group_rows.append({
                "side": side,
                "group": group_name,
                "vertex_count": len(indexes),
                "child_weight": child_weight,
                "max_vertex_drift_m": group_vertex_drift,
                "gradient_identity_max_component_delta": gradient_delta,
                "normal_matrix_identity_max_component_delta": normal_delta,
            })

        side_rows.append({
            "side": side,
            "vertex_count": len(specimen["positions"]),
            "max_vertex_drift_m": side_max_vertex_drift,
            "pose_reported_neutral_max_vertex_drift_m": posed["neutral_max_vertex_drift_m"],
        })

    negative_rows = []
    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        layout = _reindexed_layout(side, specimen)
        joint = rig["rig_method"]["joint_semantics"][side]
        origin = tuple(float(value) for value in source["landmarks"][joint["landmark"]])
        axis = tuple(float(value) for value in joint["axis"])
        neutral_weights = _weights(layout, 0.0, len(specimen["positions"]))
        hidden = _pose(
            specimen,
            origin,
            axis,
            NEGATIVE_CONTROL_HIDDEN_ANGLE_DEG,
            neutral_weights,
        )
        vertex_drift = max(
            math.dist(tuple(float(v) for v in before), tuple(float(v) for v in after))
            for before, after in zip(specimen["positions"], hidden["positions"])
        )
        distal_gradient = deformation_gradient(axis, NEGATIVE_CONTROL_HIDDEN_ANGLE_DEG, 1.0)
        matrix_delta = _matrix_component_max_delta(distal_gradient, identity)
        negative_rows.append({
            "side": side,
            "hidden_angle_deg": NEGATIVE_CONTROL_HIDDEN_ANGLE_DEG,
            "max_vertex_drift_m": vertex_drift,
            "distal_gradient_identity_max_component_delta": matrix_delta,
            "rejected": (
                vertex_drift >= NEGATIVE_CONTROL_MIN_VERTEX_DRIFT_M
                and matrix_delta >= NEGATIVE_CONTROL_MIN_MATRIX_DELTA
            ),
        })

    neutral_pass = (
        total_vertices == 184
        and max_vertex_drift <= NEUTRAL_TOLERANCE
        and max_gradient_identity_delta <= NEUTRAL_TOLERANCE
        and max_normal_identity_delta <= NEUTRAL_TOLERANCE
        and all(row["pose_reported_neutral_max_vertex_drift_m"] <= NEUTRAL_TOLERANCE for row in side_rows)
    )
    negative_rejected = all(row["rejected"] for row in negative_rows)
    boundary = frame["structural_boundary"]
    status = STATUS if neutral_pass and negative_rejected else FAIL_STATUS

    return {
        "status": status,
        "contract": contract,
        "neutral_closure": {
            "neutral_angle_deg": NEUTRAL_ANGLE_DEG,
            "neutral_proximal_release_weight": release_weight(NEUTRAL_ANGLE_DEG),
            "total_receiver_vertices": total_vertices,
            "max_owner_vertex_drift_m": max_vertex_drift,
            "max_gradient_identity_component_delta": max_gradient_identity_delta,
            "max_normal_matrix_identity_component_delta": max_normal_identity_delta,
            "all_receiver_vertices_close_to_source": neutral_pass,
            "side_rows": side_rows,
            "group_rows": group_rows,
        },
        "representative_motion_boundary": {
            "owner_frame_parent_status": frame["status"],
            "representative_non_neutral_angles_deg": [-30.0, 30.0],
            "last_sampled_clear_positive_deg": boundary["last_sampled_clear_positive_deg"],
            "first_sampled_failing_positive_deg": boundary["first_sampled_failing_positive_deg"],
            "structural_boundary_unchanged": boundary["unchanged"],
        },
        "negative_control": {
            "kind": "hidden_non_neutral_joint_offset_while_testing_neutral_closure",
            "rows": negative_rows,
            "rejected": negative_rejected,
        },
        "gates": {
            "target_engine_bind_or_inverse_bind": "NOT_EVALUATED",
            "target_engine_direction_frame": "NOT_EVALUATED",
            "neutral_shaded_mismatch_explanation": "NOT_ESTABLISHED",
            "animation_acceptance": "NOT_EVALUATED",
            "technical_art_target_host_acceptance": "NOT_EVALUATED",
            "runtime_acceptance": "NOT_EVALUATED",
            "visual_acceptance": "NOT_EVALUATED",
            "canon_or_production_readiness": "NOT_CLAIMED",
        },
    }


def build_review006_neutral_bind_frame_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_neutral_bind_frame()
    if audit["status"] != STATUS:
        raise ValueError("review-006 neutral bind-frame closure audit failed")
    path = out / "review006-rig-neutral-bind-frame-closure.json"
    path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit
