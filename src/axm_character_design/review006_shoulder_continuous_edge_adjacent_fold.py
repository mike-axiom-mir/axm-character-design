"""Continuous edge-adjacent fold certificate for the exact review-006 shoulder rig.

The previous Rigging observer proved a positive edge-adjacent fold margin only at
0.05-degree samples. This module closes only the between-sample part of that
same local contact class. It does not change source geometry, topology, joints,
weights, pose semantics or any downstream owner.

For each triangle pair sharing one indexed edge, the certificate evaluates the
two opposite-vertex radial directions around that moving edge at an interval
midpoint. Closed-form owner vertex-speed bounds provide conservative bounds for
shared-edge direction motion and for each opposite radial direction. The
geodesic separation of the two radial directions must remain strictly positive
for the whole interval. Intervals that cannot be certified are subdivided.

A positive result proves absence of the same-ray edge-fold/contact predicate for
all real-valued owner angles in the retained range. Vertex-only neighbours,
anatomy, Animation, target-host transport, Runtime and visual acceptance remain
outside this claim.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .review006_shoulder_continuous_clearance import (
    FIRST_SAMPLED_FAILURE_DEG,
    SAFE_END_DEG,
    SAFE_START_DEG,
    STATUS as CONTINUOUS_NONADJACENT_STATUS,
    _exact_inputs,
    _pose_at,
    _vertex_speed_bounds,
    audit_review006_continuous_nonadjacent_clearance,
)
from .review006_shoulder_edge_adjacent_fold_margin import (
    FOLD_CONTACT_EPSILON_RAD,
    SAMPLE_STEP_DEG,
    STATUS as SAMPLED_EDGE_STATUS,
    _adjacency_rows,
    _edge_fold_angle,
    audit_review006_sampled_edge_adjacent_fold_margin,
)
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    HISTORICAL_RIGGING_HEAD,
    PROFILE_SOURCE_HEAD,
)

SCHEMA = "axm.character-review006-continuous-edge-adjacent-fold/v0.1"
STATUS = (
    "PASS_CHARACTER_REVIEW006_CONTINUOUS_EDGE_ADJACENT_FOLD_MARGIN_"
    "MINUS40_TO_PLUS3655__VERTEX_ONLY_HELD"
)
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_CONTINUOUS_EDGE_ADJACENT_FOLD_MARGIN"
GEOMETRY_EVIDENCE_HEAD = "3519289f99c15ee3b7298b7bd625cf81e32b3c98"
BASE_INTERVAL_DEG = SAMPLE_STEP_DEG
MIN_INTERVAL_DEG = 0.00000075
MAX_SUBDIVISION_DEPTH = 17
MIN_LENGTH_M = 1e-12
CERTIFICATE_MARGIN_RAD = 1e-12


def _sub(a, b):
    return tuple(float(a[index]) - float(b[index]) for index in range(3))


def _length(value):
    return math.sqrt(sum(float(component) * float(component) for component in value))


def continuous_edge_adjacent_fold_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-continuous-edge-adjacent-fold-margin-001",
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
        "continuous_fold_certificate": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "base_interval_deg": BASE_INTERVAL_DEG,
            "minimum_interval_deg": MIN_INTERVAL_DEG,
            "max_subdivision_depth": MAX_SUBDIVISION_DEPTH,
            "fold_contact_epsilon_rad": FOLD_CONTACT_EPSILON_RAD,
            "strict_certificate_margin_rad": CERTIFICATE_MARGIN_RAD,
            "method": (
                "MIDPOINT_RADIAL_GEODESIC_SEPARATION_MINUS_"
                "OWNER_VERTEX_SPEED_DIRECTION_MOTION_BOUND"
            ),
        },
        "truth_boundary": {
            "continuous_edge_adjacent_same_ray_fold_contact_proven": True,
            "vertex_only_neighbor_contact_proven": False,
            "nonadjacent_contact_replaced": False,
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
    if contract != continuous_edge_adjacent_fold_contract():
        raise ValueError("review-006 continuous edge-adjacent contract identity drift")


def _radial_motion_bound(
    positions,
    speeds,
    edge_a,
    edge_b,
    opposite,
    radial_mid_length,
    half_width_rad,
):
    edge_mid = _sub(positions[edge_b], positions[edge_a])
    edge_mid_length = _length(edge_mid)
    edge_speed = float(speeds[edge_a]) + float(speeds[edge_b])
    edge_lower = edge_mid_length - edge_speed * half_width_rad
    if edge_lower <= MIN_LENGTH_M:
        return {
            "certified": False,
            "reason": "EDGE_LENGTH_LOWER_BOUND_NONPOSITIVE",
            "edge_mid_length_m": edge_mid_length,
            "edge_lower_bound_m": edge_lower,
        }

    # For u=e/|e|, ||u'|| <= ||e'|| / |e|.
    edge_direction_speed = edge_speed / edge_lower

    offset_mid = _sub(positions[opposite], positions[edge_a])
    offset_mid_length = _length(offset_mid)
    offset_speed = float(speeds[opposite]) + float(speeds[edge_a])
    offset_upper = offset_mid_length + offset_speed * half_width_rad

    # r=(I-u u^T)d.  ||r'|| <= ||d'|| + 2 ||u'|| ||d||.
    radial_speed = offset_speed + 2.0 * edge_direction_speed * offset_upper
    radial_lower = float(radial_mid_length) - radial_speed * half_width_rad
    if radial_lower <= MIN_LENGTH_M:
        return {
            "certified": False,
            "reason": "RADIAL_LENGTH_LOWER_BOUND_NONPOSITIVE",
            "radial_mid_length_m": float(radial_mid_length),
            "radial_lower_bound_m": radial_lower,
            "radial_speed_bound_m_per_rad": radial_speed,
        }

    angular_speed = radial_speed / radial_lower
    angular_deviation = angular_speed * half_width_rad
    return {
        "certified": True,
        "edge_mid_length_m": edge_mid_length,
        "edge_lower_bound_m": edge_lower,
        "radial_mid_length_m": float(radial_mid_length),
        "radial_lower_bound_m": radial_lower,
        "radial_speed_bound_m_per_rad": radial_speed,
        "angular_speed_bound_rad_per_rad": angular_speed,
        "half_interval_angular_deviation_rad": angular_deviation,
    }


def _certify_interval(specimen, layout, origin, axis, adjacency_rows, start_deg, end_deg):
    start_deg = float(start_deg)
    end_deg = float(end_deg)
    midpoint_deg = 0.5 * (start_deg + end_deg)
    half_width_rad = math.radians(0.5 * (end_deg - start_deg))
    posed = _pose_at(specimen, layout, origin, axis, midpoint_deg)
    positions = posed["positions"]
    speeds = _vertex_speed_bounds(specimen, layout, origin, start_deg, end_deg)

    minimum_slack = math.inf
    witness = None
    for adjacency in adjacency_rows:
        edge_a, edge_b = adjacency["shared_edge"]
        opposite_a, opposite_b = adjacency["opposite_vertices"]
        midpoint_angle, _, radial_a_mid, radial_b_mid = _edge_fold_angle(
            positions, adjacency
        )

        if midpoint_angle <= FOLD_CONTACT_EPSILON_RAD:
            return {
                "certified": False,
                "reason": "MIDPOINT_SAME_RAY_FOLD_CONTACT",
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(adjacency["triangle_pair"]),
                "shared_edge": list(adjacency["shared_edge"]),
                "midpoint_fold_angle_rad": midpoint_angle,
            }

        a_bound = _radial_motion_bound(
            positions,
            speeds,
            edge_a,
            edge_b,
            opposite_a,
            radial_a_mid,
            half_width_rad,
        )
        b_bound = _radial_motion_bound(
            positions,
            speeds,
            edge_a,
            edge_b,
            opposite_b,
            radial_b_mid,
            half_width_rad,
        )
        if not a_bound["certified"] or not b_bound["certified"]:
            return {
                "certified": False,
                "reason": "DIRECTION_MOTION_BOUND_NOT_CERTIFIED",
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(adjacency["triangle_pair"]),
                "shared_edge": list(adjacency["shared_edge"]),
                "a_bound": a_bound,
                "b_bound": b_bound,
            }

        slack = (
            midpoint_angle
            - a_bound["half_interval_angular_deviation_rad"]
            - b_bound["half_interval_angular_deviation_rad"]
            - FOLD_CONTACT_EPSILON_RAD
        )
        if slack < minimum_slack:
            minimum_slack = slack
            witness = {
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(adjacency["triangle_pair"]),
                "shared_edge": list(adjacency["shared_edge"]),
                "opposite_vertices": list(adjacency["opposite_vertices"]),
                "midpoint_fold_angle_rad": midpoint_angle,
                "midpoint_fold_angle_deg": math.degrees(midpoint_angle),
                "a_angular_deviation_bound_rad": a_bound[
                    "half_interval_angular_deviation_rad"
                ],
                "b_angular_deviation_bound_rad": b_bound[
                    "half_interval_angular_deviation_rad"
                ],
                "certificate_slack_rad": slack,
                "certificate_slack_deg": math.degrees(slack),
            }
        if slack <= CERTIFICATE_MARGIN_RAD:
            return {
                "certified": False,
                "reason": "ANGULAR_SEPARATION_BOUND_INSUFFICIENT",
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(adjacency["triangle_pair"]),
                "shared_edge": list(adjacency["shared_edge"]),
                "midpoint_fold_angle_rad": midpoint_angle,
                "certificate_slack_rad": slack,
            }

    return {
        "certified": True,
        "interval_deg": [start_deg, end_deg],
        "midpoint_deg": midpoint_deg,
        "minimum_certificate_slack_rad": minimum_slack,
        "minimum_certificate_slack_deg": math.degrees(minimum_slack),
        "closest_witness": witness,
    }


def _certify_recursive(
    specimen,
    layout,
    origin,
    axis,
    adjacency_rows,
    start_deg,
    end_deg,
    depth,
    accepted,
    counters,
):
    counters["attempted_intervals"] += 1
    result = _certify_interval(
        specimen,
        layout,
        origin,
        axis,
        adjacency_rows,
        start_deg,
        end_deg,
    )
    if result["certified"]:
        accepted.append({**result, "depth": int(depth)})
        counters["max_depth"] = max(counters["max_depth"], int(depth))
        return

    width = float(end_deg) - float(start_deg)
    if depth >= MAX_SUBDIVISION_DEPTH or width <= MIN_INTERVAL_DEG:
        raise ValueError(
            "review-006 continuous edge-adjacent certificate exhausted subdivision "
            f"at [{start_deg}, {end_deg}] because {result['reason']}"
        )
    midpoint = 0.5 * (float(start_deg) + float(end_deg))
    counters["subdivisions"] += 1
    _certify_recursive(
        specimen,
        layout,
        origin,
        axis,
        adjacency_rows,
        start_deg,
        midpoint,
        depth + 1,
        accepted,
        counters,
    )
    _certify_recursive(
        specimen,
        layout,
        origin,
        axis,
        adjacency_rows,
        midpoint,
        end_deg,
        depth + 1,
        accepted,
        counters,
    )


def _initial_intervals():
    scale = int(round(1.0 / BASE_INTERVAL_DEG))
    start_tick = int(round(SAFE_START_DEG * scale))
    end_tick = int(round(SAFE_END_DEG * scale))
    return tuple(
        (tick / scale, (tick + 1) / scale)
        for tick in range(start_tick, end_tick)
    )


def _certify_side(side):
    _, specimen, layout, origin, axis, faces, _ = _exact_inputs(side)
    adjacency_rows, vertex_only_count = _adjacency_rows(faces)
    if not adjacency_rows:
        raise ValueError("review-006 continuous edge-adjacent proof found no shared edges")

    accepted = []
    counters = {
        "attempted_intervals": 0,
        "subdivisions": 0,
        "max_depth": 0,
    }
    for start_deg, end_deg in _initial_intervals():
        _certify_recursive(
            specimen,
            layout,
            origin,
            axis,
            adjacency_rows,
            start_deg,
            end_deg,
            0,
            accepted,
            counters,
        )

    minimum = min(accepted, key=lambda row: row["minimum_certificate_slack_rad"])
    return {
        "side": side,
        "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
        "edge_adjacent_pair_count": len(adjacency_rows),
        "vertex_only_neighbor_pair_count": int(vertex_only_count),
        "base_interval_count": len(_initial_intervals()),
        "certified_interval_count": len(accepted),
        "attempted_interval_count": counters["attempted_intervals"],
        "adaptive_subdivision_count": counters["subdivisions"],
        "maximum_subdivision_depth": counters["max_depth"],
        "minimum_certificate_slack_rad": minimum["minimum_certificate_slack_rad"],
        "minimum_certificate_slack_deg": minimum["minimum_certificate_slack_deg"],
        "closest_certificate_witness": minimum["closest_witness"],
        "continuous_same_ray_fold_contact_free": True,
    }


def audit_review006_continuous_edge_adjacent_fold_margin(contract=None):
    contract = contract or continuous_edge_adjacent_fold_contract()
    _validate_contract(contract)

    nonadjacent = audit_review006_continuous_nonadjacent_clearance()
    if nonadjacent["status"] != CONTINUOUS_NONADJACENT_STATUS:
        raise ValueError("continuous nonadjacent prerequisite is not green")

    sampled = audit_review006_sampled_edge_adjacent_fold_margin()
    if sampled["status"] != SAMPLED_EDGE_STATUS:
        raise ValueError("sampled edge-adjacent prerequisite is not green")

    sides = {side: _certify_side(side) for side in ("L", "R")}
    pair_match = (
        sides["L"]["edge_adjacent_pair_count"]
        == sides["R"]["edge_adjacent_pair_count"]
    )
    slack_residual = abs(
        sides["L"]["minimum_certificate_slack_rad"]
        - sides["R"]["minimum_certificate_slack_rad"]
    )
    continuous_pass = (
        pair_match
        and all(row["continuous_same_ray_fold_contact_free"] for row in sides.values())
        and all(
            row["minimum_certificate_slack_rad"] > CERTIFICATE_MARGIN_RAD
            for row in sides.values()
        )
    )
    negative = sampled["negative_control"]
    if not negative["rejected"]:
        raise ValueError("inherited same-ray negative control did not reject")

    return {
        "schema": SCHEMA,
        "status": STATUS if continuous_pass else FAIL_STATUS,
        "contract": contract,
        "continuous_edge_adjacent_fold_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "base_interval_deg": BASE_INTERVAL_DEG,
            "all_real_owner_angles_certified": continuous_pass,
            "bilateral_pair_count_match": pair_match,
            "bilateral_minimum_slack_residual_rad": slack_residual,
            "sides": sides,
        },
        "retained_boundaries": {
            "continuous_nonadjacent_status": nonadjacent["status"],
            "sampled_edge_adjacent_status": sampled["status"],
            "first_retained_nonadjacent_failure_deg": FIRST_SAMPLED_FAILURE_DEG,
            "vertex_only_neighbor_contact_proven": False,
        },
        "negative_control": negative,
        "truth_boundary": [
            "This closes only continuous same-ray fold/contact freedom for indexed edge-adjacent face pairs on the exact unchanged owner rig.",
            "The 845 vertex-only neighbouring face pairs per shoulder remain outside this claim.",
            "The retained +36.60 nonadjacent 114/137 contact remains a separate failure class and is not waived.",
            "No anatomical ROM or exact first-contact angle is inferred.",
            "No Animation timing/interpolation/playback acceptance is inferred.",
            "No Technical-Art target-host transport or Runtime/controller/device acceptance is inferred.",
            "No final shaded visual acceptance, CANON, production readiness or Rigging mastery is inferred.",
        ],
    }


def build_review006_continuous_edge_adjacent_fold_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    contract = continuous_edge_adjacent_fold_contract()
    audit = audit_review006_continuous_edge_adjacent_fold_margin(contract)
    (out / "review006-continuous-edge-adjacent-fold-contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "review006-continuous-edge-adjacent-fold-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return audit
