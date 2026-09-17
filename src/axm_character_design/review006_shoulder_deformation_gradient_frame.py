"""Rigging-owned deformation-gradient frame reference for review-006 shoulders.

This module derives the exact local linear deformation map already implied by the
current Rigging owner implementation:

    D(theta, w) = (1 - w) I + w R(theta)

where ``w`` is the existing angle-conditioned child weight and ``R`` is the
existing shoulder rotation.  It exposes an owner-consistent tangent/normal frame
reference without changing source geometry, topology, joints, weights or the
historical profile.

The reference is intentionally narrower than a production shading policy.  It
proves the rig-local deformation gradient remains invertible and handedness
preserving over the historical -40..+40 degree verification envelope, and that
its affine prediction reproduces the actual owner pose implementation at
representative poses.  It does NOT prove collision freedom, choose final vertex
normals/tangents, grant Animation/Technical-Art/Runtime acceptance, or override
the retained +36.55 clear / +36.60 failing structural boundary.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .review006_connected_geometry import build_opening_repair
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    HISTORICAL_RIGGING_HEAD,
    MAX_RELEASE_WEIGHT,
    PROFILE_SOURCE_HEAD,
    RELEASE_POWER,
    _pose,
    _reindexed_layout,
    _weights,
    rebind_contract,
    release_weight,
)
from .review006_shoulder_subdegree_boundary import (
    STATUS as SUBDEGREE_STATUS,
    audit_review006_positive_subdegree_boundary,
)
from .shoulder_pose_clearance_refinement import shoulder_pose_clearance_refinement_candidate

SCHEMA = "axm.character-review006-rig-deformation-gradient-frame/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_RIG_DEFORMATION_GRADIENT_FRAME_REFERENCE__STRUCTURAL_BOUNDARY_UNCHANGED"
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_RIG_DEFORMATION_GRADIENT_FRAME_REFERENCE"
REPRESENTATIVE_ANGLES_DEG = (-40.0, -30.0, 0.0, 30.0, 36.55, 36.60, 40.0)
OWNER_RESIDUAL_TOLERANCE_M = 1e-11
ORTHOGONALITY_TOLERANCE = 1e-11
HANDEDNESS_TOLERANCE = 1e-10
DETERMINANT_TOLERANCE = 1e-12
NEGATIVE_CONTROL_ANGLE_DEG = 30.0
NEGATIVE_CONTROL_MIN_ANGULAR_ERROR_DEG = 1.0


def _dot(a, b):
    return sum(float(a[index]) * float(b[index]) for index in range(3))


def _cross(a, b):
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _length(value):
    return math.sqrt(_dot(value, value))


def _unit(value):
    magnitude = _length(value)
    if magnitude <= 1e-15:
        raise ValueError("direction must be non-zero")
    return tuple(float(component) / magnitude for component in value)


def _matrix_vector(matrix, vector):
    return tuple(
        sum(float(matrix[row][column]) * float(vector[column]) for column in range(3))
        for row in range(3)
    )


def _matrix_scale(matrix, scalar):
    return tuple(
        tuple(float(value) * float(scalar) for value in row)
        for row in matrix
    )


def _matrix_add(first, second):
    return tuple(
        tuple(float(first[row][column]) + float(second[row][column]) for column in range(3))
        for row in range(3)
    )


def _transpose(matrix):
    return tuple(tuple(float(matrix[column][row]) for column in range(3)) for row in range(3))


def _determinant(matrix):
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    return (
        a * (e * i - f * h)
        - b * (d * i - f * g)
        + c * (d * h - e * g)
    )


def _inverse(matrix):
    determinant = _determinant(matrix)
    if abs(determinant) <= DETERMINANT_TOLERANCE:
        raise ValueError("deformation gradient is singular")
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    cofactor = (
        (e * i - f * h, -(d * i - f * g), d * h - e * g),
        (-(b * i - c * h), a * i - c * g, -(a * h - b * g)),
        (b * f - c * e, -(a * f - c * d), a * e - b * d),
    )
    return _matrix_scale(cofactor, 1.0 / determinant)


def _identity():
    return (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def _rotation_matrix(axis, angle_deg):
    x, y, z = _unit(axis)
    angle = math.radians(float(angle_deg))
    c = math.cos(angle)
    s = math.sin(angle)
    one_minus_c = 1.0 - c
    return (
        (
            c + x * x * one_minus_c,
            x * y * one_minus_c - z * s,
            x * z * one_minus_c + y * s,
        ),
        (
            y * x * one_minus_c + z * s,
            c + y * y * one_minus_c,
            y * z * one_minus_c - x * s,
        ),
        (
            z * x * one_minus_c - y * s,
            z * y * one_minus_c + x * s,
            c + z * z * one_minus_c,
        ),
    )


def deformation_gradient(axis, angle_deg, child_weight):
    weight = float(child_weight)
    if not 0.0 <= weight <= 1.0:
        raise ValueError("child weight must stay inside [0, 1]")
    rotation = _rotation_matrix(axis, angle_deg)
    return _matrix_add(
        _matrix_scale(_identity(), 1.0 - weight),
        _matrix_scale(rotation, weight),
    )


def normal_matrix(axis, angle_deg, child_weight):
    return _transpose(_inverse(deformation_gradient(axis, angle_deg, child_weight)))


def _distance(first, second):
    return math.sqrt(sum((float(first[index]) - float(second[index])) ** 2 for index in range(3)))


def _angle_between_deg(first, second):
    a = _unit(first)
    b = _unit(second)
    cosine = max(-1.0, min(1.0, _dot(a, b)))
    return math.degrees(math.acos(cosine))


def _frame_basis(axis):
    bitangent = _unit(axis)
    tangent = (1.0, 0.0, 0.0)
    if abs(_dot(tangent, bitangent)) > 1e-12:
        tangent = (0.0, 0.0, 1.0)
    tangent = _unit(tangent)
    normal = _unit(_cross(tangent, bitangent))
    if _dot(_cross(tangent, bitangent), normal) <= 0.0:
        raise ValueError("neutral reference frame must be right handed")
    return tangent, bitangent, normal


def _frame_metrics(axis, angle_deg, child_weight):
    gradient = deformation_gradient(axis, angle_deg, child_weight)
    normal_xform = normal_matrix(axis, angle_deg, child_weight)
    tangent0, bitangent0, normal0 = _frame_basis(axis)
    tangent = _unit(_matrix_vector(gradient, tangent0))
    bitangent = _unit(_matrix_vector(gradient, bitangent0))
    normal = _unit(_matrix_vector(normal_xform, normal0))
    orthogonality = max(
        abs(_dot(tangent, bitangent)),
        abs(_dot(tangent, normal)),
        abs(_dot(bitangent, normal)),
    )
    handedness = _dot(_cross(tangent, bitangent), normal)
    return {
        "gradient": gradient,
        "normal_matrix": normal_xform,
        "determinant": _determinant(gradient),
        "orthogonality_max_abs_dot": orthogonality,
        "handedness_triple_product": handedness,
        "tangent": tangent,
        "bitangent": bitangent,
        "normal": normal,
    }


def _proximal_continuous_determinant_lower_bound():
    # For D=(1-w)I+wR around one axis, det(D) is
    # 1 - 2*w*(1-w)*(1-cos(theta)).  Over |theta|<=40 deg and
    # 0<=w<=MAX_RELEASE_WEIGHT<=0.1, both factors are bounded above by
    # their interval endpoints, yielding a conservative continuous lower bound.
    theta_bound = math.radians(40.0)
    return 1.0 - (
        2.0
        * MAX_RELEASE_WEIGHT
        * (1.0 - MAX_RELEASE_WEIGHT)
        * (1.0 - math.cos(theta_bound))
    )


def deformation_gradient_contract():
    return {
        "schema": SCHEMA,
        "reference_id": "character-review006-rig-local-deformation-gradient-frame-001",
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
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "release_power": RELEASE_POWER,
            "max_release_weight": MAX_RELEASE_WEIGHT,
            "owner_map": "D=(1-w)I+wR(theta)",
            "normal_map": "inverse_transpose(D)",
            "profile_reauthored": False,
            "weights_reauthored": False,
            "joint_semantics_reauthored": False,
        },
        "verification": {
            "representative_angles_deg": list(REPRESENTATIVE_ANGLES_DEG),
            "continuous_local_gradient_envelope_deg": [-40.0, 40.0],
            "owner_residual_tolerance_m": OWNER_RESIDUAL_TOLERANCE_M,
        },
        "truth_boundary": {
            "rig_local_deformation_gradient_reference": True,
            "continuous_local_gradient_invertibility_proven": True,
            "continuous_collision_freedom_proven": False,
            "final_vertex_normal_or_tangent_policy": False,
            "animation_acceptance": False,
            "technical_art_transport_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_exact_identity():
    if rebind_contract()["rig_method"]["profile_digest"] != EXPECTED_PROFILE_DIGEST:
        raise ValueError("review-006 Rigging profile identity drift")
    boundary = audit_review006_positive_subdegree_boundary()
    if boundary["status"] != SUBDEGREE_STATUS:
        raise ValueError("review-006 subdegree structural prerequisite is not green")
    source = shoulder_pose_clearance_refinement_candidate()
    return source, boundary


def _group_weight(group_name, angle_deg):
    if group_name in ("ribcage", "seam"):
        return 0.0
    if group_name == "proximal":
        return release_weight(angle_deg)
    if group_name in ("distal", "distal_cap"):
        return 1.0
    raise ValueError(f"unknown Rigging group: {group_name}")


def audit_review006_deformation_gradient_frame(contract=None):
    contract = contract or deformation_gradient_contract()
    if contract != deformation_gradient_contract():
        raise ValueError("review-006 deformation-gradient frame contract identity drift")

    source, boundary = _validate_exact_identity()
    rows = []
    max_owner_residual = 0.0
    max_orthogonality = 0.0
    min_handedness = 1.0
    min_observed_determinant = 1.0

    rig_contract = rebind_contract()
    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        layout = _reindexed_layout(side, specimen)
        joint = rig_contract["rig_method"]["joint_semantics"][side]
        origin = tuple(float(value) for value in source["landmarks"][joint["landmark"]])
        axis = tuple(float(value) for value in joint["axis"])

        for angle_deg in REPRESENTATIVE_ANGLES_DEG:
            owner_weights = _weights(
                layout,
                release_weight(angle_deg),
                len(specimen["positions"]),
            )
            posed = _pose(specimen, origin, axis, angle_deg, owner_weights)

            for group_name, indexes in layout["groups"].items():
                weight = _group_weight(group_name, angle_deg)
                frame = _frame_metrics(axis, angle_deg, weight)
                gradient = frame["gradient"]
                group_residual = 0.0
                for index in indexes:
                    source_relative = tuple(
                        float(specimen["positions"][index][component]) - origin[component]
                        for component in range(3)
                    )
                    predicted_relative = _matrix_vector(gradient, source_relative)
                    predicted = tuple(
                        origin[component] + predicted_relative[component]
                        for component in range(3)
                    )
                    group_residual = max(
                        group_residual,
                        _distance(predicted, posed["positions"][index]),
                    )

                max_owner_residual = max(max_owner_residual, group_residual)
                max_orthogonality = max(
                    max_orthogonality,
                    frame["orthogonality_max_abs_dot"],
                )
                min_handedness = min(min_handedness, frame["handedness_triple_product"])
                min_observed_determinant = min(min_observed_determinant, frame["determinant"])
                rows.append({
                    "side": side,
                    "angle_deg": float(angle_deg),
                    "group": group_name,
                    "child_weight": float(weight),
                    "determinant": frame["determinant"],
                    "owner_affine_position_max_residual_m": group_residual,
                    "orthogonality_max_abs_dot": frame["orthogonality_max_abs_dot"],
                    "handedness_triple_product": frame["handedness_triple_product"],
                    "gradient": frame["gradient"],
                    "normal_matrix": frame["normal_matrix"],
                })

    continuous_det_lower_bound = _proximal_continuous_determinant_lower_bound()

    negative_rows = []
    for side in ("L", "R"):
        joint = rig_contract["rig_method"]["joint_semantics"][side]
        axis = tuple(float(value) for value in joint["axis"])
        weight = release_weight(NEGATIVE_CONTROL_ANGLE_DEG)
        owner_frame = _frame_metrics(axis, NEGATIVE_CONTROL_ANGLE_DEG, weight)
        _, _, neutral_normal = _frame_basis(axis)
        owner_normal = _unit(_matrix_vector(owner_frame["normal_matrix"], neutral_normal))
        naive_rigid_normal = _unit(
            _matrix_vector(_rotation_matrix(axis, NEGATIVE_CONTROL_ANGLE_DEG), neutral_normal)
        )
        angular_error = _angle_between_deg(owner_normal, naive_rigid_normal)
        negative_rows.append({
            "side": side,
            "angle_deg": NEGATIVE_CONTROL_ANGLE_DEG,
            "proximal_child_weight": weight,
            "naive_full_child_rotation_normal_error_deg": angular_error,
        })

    negative_control_rejected = all(
        row["naive_full_child_rotation_normal_error_deg"]
        >= NEGATIVE_CONTROL_MIN_ANGULAR_ERROR_DEG
        for row in negative_rows
    )

    last_clear = boundary["sampled_guard"]["refined_positive_sampled_guard_max_deg"]
    first_failure = boundary["sampled_guard"]["first_sampled_positive_failure_deg"]
    structural_boundary_preserved = last_clear == 36.55 and first_failure == 36.60

    pass_gate = (
        max_owner_residual <= OWNER_RESIDUAL_TOLERANCE_M
        and max_orthogonality <= ORTHOGONALITY_TOLERANCE
        and min_handedness >= 1.0 - HANDEDNESS_TOLERANCE
        and min_observed_determinant > DETERMINANT_TOLERANCE
        and continuous_det_lower_bound > DETERMINANT_TOLERANCE
        and negative_control_rejected
        and structural_boundary_preserved
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if pass_gate else FAIL_STATUS,
        "contract": contract,
        "exact_identity": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "geometry_head": GEOMETRY_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
        },
        "structural_boundary": {
            "prerequisite_status": boundary["status"],
            "last_sampled_clear_positive_deg": last_clear,
            "first_sampled_failing_positive_deg": first_failure,
            "unchanged": structural_boundary_preserved,
        },
        "deformation_gradient_reference": {
            "owner_map": "D=(1-w)I+wR(theta)",
            "normal_map": "inverse_transpose(D)",
            "representative_angles_deg": list(REPRESENTATIVE_ANGLES_DEG),
            "row_count": len(rows),
            "max_owner_affine_position_residual_m": max_owner_residual,
            "max_frame_orthogonality_abs_dot": max_orthogonality,
            "min_frame_handedness_triple_product": min_handedness,
            "min_observed_group_determinant": min_observed_determinant,
            "continuous_proximal_determinant_lower_bound_minus40_plus40": continuous_det_lower_bound,
            "continuous_local_gradient_invertible": continuous_det_lower_bound > DETERMINANT_TOLERANCE,
            "rows": rows,
        },
        "negative_control": {
            "mutation": "treat the partially weighted proximal ring direction frame as a fully rigid child rotation",
            "minimum_required_angular_error_deg": NEGATIVE_CONTROL_MIN_ANGULAR_ERROR_DEG,
            "rows": negative_rows,
            "rejected": negative_control_rejected,
        },
        "gates": {
            "exact_source_geometry_rig_profile_identity": "PASS",
            "owner_affine_prediction": "PASS" if max_owner_residual <= OWNER_RESIDUAL_TOLERANCE_M else "FAIL",
            "frame_orthogonality": "PASS" if max_orthogonality <= ORTHOGONALITY_TOLERANCE else "FAIL",
            "frame_handedness": "PASS" if min_handedness >= 1.0 - HANDEDNESS_TOLERANCE else "FAIL",
            "continuous_local_gradient_invertibility": "PASS" if continuous_det_lower_bound > DETERMINANT_TOLERANCE else "FAIL",
            "naive_rigid_proximal_frame_negative": "PASS_EXPECTED_REJECTION" if negative_control_rejected else "FAIL",
            "structural_contact_boundary_unchanged": "PASS" if structural_boundary_preserved else "FAIL",
            "continuous_collision_freedom": "NOT_PROVEN",
            "animation_acceptance": "NOT_EVALUATED",
            "technical_art_transport_acceptance": "NOT_EVALUATED",
            "runtime_acceptance": "NOT_EVALUATED",
            "visual_acceptance": "NOT_EVALUATED",
        },
        "handoffs": {
            "technical_art": (
                "This is a Rigging-owned local deformation-gradient reference only. A receiver may compare or transport it, "
                "but Technical Art must independently prove representation/export/import behavior and must not infer Art acceptance."
            ),
            "materials_art_qa": (
                "This reference does not replace the Materials pose-recomputed smooth-normal visual comparator. Any future "
                "direction-frame representation still requires direct shaded comparison and independent QA/Art review."
            ),
            "animation": (
                "The direction-frame reference does not widen or redefine the existing diagnostic clip or anatomical range."
            ),
            "runtime": (
                "No controller, target-engine interpolation, renderer, device or performance acceptance is implied."
            ),
        },
        "truth_boundary": [
            "Source geometry, Geometry topology, joint semantics, weight formula and Rigging profile are unchanged.",
            "The continuous proof is only local deformation-gradient invertibility/handedness over -40..+40 degrees; it is not continuous mesh collision freedom.",
            "The retained +36.55 sampled-clear / +36.60 sampled-failing structural boundary remains unchanged even though the local frame stays invertible there.",
            "The inverse-transpose local frame is a Rigging reference, not a final per-vertex shading-normal/tangent policy and not a claim of equivalence to Materials' pose-recomputed smooth normals.",
            "No Animation, Technical Art, Runtime, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_deformation_gradient_frame_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_deformation_gradient_frame()
    (out / "review006-rig-deformation-gradient-frame.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return audit
