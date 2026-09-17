"""Continuous vertex-only neighbour cone certificate for Character review-006.

The existing dense observer proves all 845 face pairs per shoulder that share
exactly one indexed vertex are separated at every 0.05-degree owner sample from
-40 through +36.55 degrees. This module closes only the between-sample gap for
that same local contact class without changing source geometry, selected
topology, joints, weights, or owner pose semantics.

For each interval, every outgoing edge direction from a shared vertex receives
a closed-form angular-motion bound derived from the exact owner per-vertex speed
bound. Each triangle's positive spherical cone is the minor arc traced by
normalized positive blends of its two outgoing unit directions. Endpoint motion
therefore gives a conservative Hausdorff bound for the whole moving cone arc.
The two midpoint cone arcs must remain separated by more than both cone-motion
bounds plus a strict numerical margin. Intervals that cannot be certified are
subdivided.

A positive result is structural owner-rig evidence only. It is not anatomy,
Animation acceptance, Technical-Art transport acceptance, Runtime/controller
acceptance, gameplay collision suitability, visual acceptance, CANON, or
production readiness.
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
    _vertex_speed_bounds,
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
from .review006_shoulder_vertex_only_dense_margin import (
    DENSE_STEP_DEG,
    STATUS as DENSE_STATUS,
)
from .review006_shoulder_vertex_only_neighbor_cone_margin import (
    GEOMETRY_EVIDENCE_HEAD,
    VERTEX_CONTACT_EPSILON_RAD,
    _angle_unit,
    _direction_cache,
    _pair_cone_separation,
    _vertex_only_rows,
)

SCHEMA = "axm.character-review006-continuous-vertex-only-neighbor-cone/v0.1"
STATUS = (
    "PASS_CHARACTER_REVIEW006_CONTINUOUS_VERTEX_ONLY_NEIGHBOR_CONE_MARGIN_"
    "MINUS40_TO_PLUS3655__ALL_INDEXED_NEIGHBOR_CLASSES_CLOSED"
)
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_CONTINUOUS_VERTEX_ONLY_NEIGHBOR_CONE_MARGIN"
BASE_INTERVAL_DEG = 0.5
MIN_INTERVAL_DEG = 1e-8
MAX_SUBDIVISION_DEPTH = 24
MIN_DIRECTION_LENGTH_M = 1e-12
CERTIFICATE_MARGIN_RAD = 1e-12


def _sub(a, b):
    return tuple(float(a[i]) - float(b[i]) for i in range(3))


def _length(value):
    return math.sqrt(sum(float(component) * float(component) for component in value))


def continuous_vertex_only_neighbor_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-continuous-vertex-only-neighbor-cone-margin-001",
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
        "predecessor": {
            "dense_sampled_schema_status": DENSE_STATUS,
            "dense_sample_step_deg": DENSE_STEP_DEG,
            "dense_sampled_result_rewritten": False,
        },
        "continuous_vertex_only_certificate": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "base_interval_deg": BASE_INTERVAL_DEG,
            "minimum_interval_deg": MIN_INTERVAL_DEG,
            "max_subdivision_depth": MAX_SUBDIVISION_DEPTH,
            "contact_epsilon_rad": VERTEX_CONTACT_EPSILON_RAD,
            "strict_certificate_margin_rad": CERTIFICATE_MARGIN_RAD,
            "method": (
                "MIDPOINT_SPHERICAL_CONE_SEPARATION_MINUS_"
                "OWNER_VERTEX_SPEED_POSITIVE_BLEND_CONE_MOTION_BOUND"
            ),
        },
        "truth_boundary": {
            "continuous_vertex_only_neighbor_contact_proven": True,
            "nonadjacent_or_edge_adjacent_claim_replaced": False,
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
    if contract != continuous_vertex_only_neighbor_contract():
        raise ValueError("review-006 continuous vertex-only contract identity drift")


def _initial_intervals():
    intervals = []
    current = float(SAFE_START_DEG)
    while current + BASE_INTERVAL_DEG < SAFE_END_DEG - 1e-12:
        nxt = current + BASE_INTERVAL_DEG
        intervals.append((current, nxt))
        current = nxt
    if current < SAFE_END_DEG - 1e-12:
        intervals.append((current, float(SAFE_END_DEG)))
    return tuple(intervals)


def _direction_motion_bounds(positions, speeds, rows, half_width_rad):
    required = set()
    for row in rows:
        shared = int(row["shared_vertex"])
        for vertex in row["left_other_vertices"] + row["right_other_vertices"]:
            required.add((shared, int(vertex)))

    result = {}
    for shared, other in required:
        vector = _sub(positions[other], positions[shared])
        midpoint_length = _length(vector)
        speed = float(speeds[shared]) + float(speeds[other])
        lower_length = midpoint_length - speed * half_width_rad
        if lower_length <= MIN_DIRECTION_LENGTH_M:
            result[(shared, other)] = {
                "certified": False,
                "reason": "OUTGOING_EDGE_LENGTH_LOWER_BOUND_NONPOSITIVE",
                "midpoint_length_m": midpoint_length,
                "lower_length_m": lower_length,
            }
            continue
        angular_speed = speed / lower_length
        angular_deviation = angular_speed * half_width_rad
        chord_deviation = 2.0 * math.sin(min(math.pi, angular_deviation) * 0.5)
        result[(shared, other)] = {
            "certified": True,
            "midpoint_length_m": midpoint_length,
            "lower_length_m": lower_length,
            "angular_speed_bound_rad_per_rad": angular_speed,
            "half_interval_angular_deviation_rad": angular_deviation,
            "half_interval_chord_deviation": chord_deviation,
        }
    return result


def _cone_arc_motion_bound(cache, motion, shared, first, second):
    first_key = (int(shared), int(first))
    second_key = (int(shared), int(second))
    first_bound = motion[first_key]
    second_bound = motion[second_key]
    if not first_bound["certified"] or not second_bound["certified"]:
        return {
            "certified": False,
            "reason": "ENDPOINT_DIRECTION_MOTION_NOT_CERTIFIED",
            "first_bound": first_bound,
            "second_bound": second_bound,
        }

    midpoint_arc_angle = _angle_unit(cache[first_key], cache[second_key])
    if midpoint_arc_angle >= math.pi - 1e-12:
        return {
            "certified": False,
            "reason": "MIDPOINT_CONE_ARC_NOT_STRICTLY_MINOR",
            "midpoint_arc_angle_rad": midpoint_arc_angle,
        }

    blend_norm_lower = math.cos(0.5 * midpoint_arc_angle)
    endpoint_chord = max(
        float(first_bound["half_interval_chord_deviation"]),
        float(second_bound["half_interval_chord_deviation"]),
    )
    if blend_norm_lower <= MIN_DIRECTION_LENGTH_M or endpoint_chord >= blend_norm_lower:
        return {
            "certified": False,
            "reason": "POSITIVE_BLEND_NORMALIZATION_BOUND_NOT_CERTIFIED",
            "midpoint_arc_angle_rad": midpoint_arc_angle,
            "midpoint_blend_norm_lower_bound": blend_norm_lower,
            "endpoint_chord_deviation_bound": endpoint_chord,
        }
    arc_angular_deviation = math.asin(endpoint_chord / blend_norm_lower)
    return {
        "certified": True,
        "midpoint_arc_angle_rad": midpoint_arc_angle,
        "midpoint_blend_norm_lower_bound": blend_norm_lower,
        "endpoint_chord_deviation_bound": endpoint_chord,
        "half_interval_cone_angular_deviation_rad": arc_angular_deviation,
    }


def _certify_interval(specimen, layout, origin, axis, rows, start_deg, end_deg):
    start_deg = float(start_deg)
    end_deg = float(end_deg)
    midpoint_deg = 0.5 * (start_deg + end_deg)
    half_width_rad = math.radians(0.5 * (end_deg - start_deg))
    posed = _pose_at(specimen, layout, origin, axis, midpoint_deg)
    positions = posed["positions"]
    speeds = _vertex_speed_bounds(specimen, layout, origin, start_deg, end_deg)
    cache = _direction_cache(positions, rows)
    motion = _direction_motion_bounds(positions, speeds, rows, half_width_rad)

    minimum_slack = math.inf
    witness = None
    for row in rows:
        shared = int(row["shared_vertex"])
        left_a, left_b = (int(v) for v in row["left_other_vertices"])
        right_a, right_b = (int(v) for v in row["right_other_vertices"])
        midpoint_separation = _pair_cone_separation(cache, row)
        if midpoint_separation <= VERTEX_CONTACT_EPSILON_RAD:
            return {
                "certified": False,
                "reason": "MIDPOINT_VERTEX_ONLY_CONE_CONTACT",
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(row["triangle_pair"]),
                "shared_vertex": shared,
                "midpoint_cone_separation_rad": midpoint_separation,
            }

        left_bound = _cone_arc_motion_bound(cache, motion, shared, left_a, left_b)
        right_bound = _cone_arc_motion_bound(cache, motion, shared, right_a, right_b)
        if not left_bound["certified"] or not right_bound["certified"]:
            return {
                "certified": False,
                "reason": "CONE_ARC_MOTION_BOUND_NOT_CERTIFIED",
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(row["triangle_pair"]),
                "shared_vertex": shared,
                "left_bound": left_bound,
                "right_bound": right_bound,
            }

        slack = (
            midpoint_separation
            - float(left_bound["half_interval_cone_angular_deviation_rad"])
            - float(right_bound["half_interval_cone_angular_deviation_rad"])
            - VERTEX_CONTACT_EPSILON_RAD
        )
        if slack < minimum_slack:
            minimum_slack = slack
            witness = {
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(row["triangle_pair"]),
                "shared_vertex": shared,
                "midpoint_cone_separation_rad": midpoint_separation,
                "midpoint_cone_separation_deg": math.degrees(midpoint_separation),
                "left_cone_motion_bound_rad": left_bound[
                    "half_interval_cone_angular_deviation_rad"
                ],
                "right_cone_motion_bound_rad": right_bound[
                    "half_interval_cone_angular_deviation_rad"
                ],
                "certificate_slack_rad": slack,
                "certificate_slack_deg": math.degrees(slack),
            }
        if slack <= CERTIFICATE_MARGIN_RAD:
            return {
                "certified": False,
                "reason": "CONE_SEPARATION_BOUND_INSUFFICIENT",
                "interval_deg": [start_deg, end_deg],
                "midpoint_deg": midpoint_deg,
                "triangle_pair": list(row["triangle_pair"]),
                "shared_vertex": shared,
                "midpoint_cone_separation_rad": midpoint_separation,
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
    specimen, layout, origin, axis, rows, start_deg, end_deg, depth, accepted, counters
):
    counters["attempted_intervals"] += 1
    result = _certify_interval(specimen, layout, origin, axis, rows, start_deg, end_deg)
    if result["certified"]:
        accepted.append({**result, "depth": int(depth)})
        counters["max_depth"] = max(counters["max_depth"], int(depth))
        return

    width = float(end_deg) - float(start_deg)
    if depth >= MAX_SUBDIVISION_DEPTH or width <= MIN_INTERVAL_DEG:
        raise ValueError(
            "review-006 continuous vertex-only certificate exhausted subdivision "
            f"at [{start_deg}, {end_deg}] because {result['reason']}"
        )
    midpoint = 0.5 * (float(start_deg) + float(end_deg))
    counters["subdivisions"] += 1
    _certify_recursive(
        specimen, layout, origin, axis, rows,
        start_deg, midpoint, depth + 1, accepted, counters,
    )
    _certify_recursive(
        specimen, layout, origin, axis, rows,
        midpoint, end_deg, depth + 1, accepted, counters,
    )


def _certify_side(side):
    _, specimen, layout, origin, axis, faces, _ = _exact_inputs(side)
    rows = _vertex_only_rows(faces)
    if len(rows) != 845:
        raise ValueError(f"review-006 continuous vertex-only pair count drift: {len(rows)}")

    accepted = []
    counters = {"attempted_intervals": 0, "subdivisions": 0, "max_depth": 0}
    for start_deg, end_deg in _initial_intervals():
        _certify_recursive(
            specimen, layout, origin, axis, rows,
            start_deg, end_deg, 0, accepted, counters,
        )
    minimum = min(accepted, key=lambda row: row["minimum_certificate_slack_rad"])
    return {
        "side": side,
        "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
        "vertex_only_neighbor_pair_count": len(rows),
        "base_interval_count": len(_initial_intervals()),
        "certified_interval_count": len(accepted),
        "attempted_interval_count": counters["attempted_intervals"],
        "adaptive_subdivision_count": counters["subdivisions"],
        "maximum_subdivision_depth": counters["max_depth"],
        "minimum_certificate_slack_rad": minimum["minimum_certificate_slack_rad"],
        "minimum_certificate_slack_deg": minimum["minimum_certificate_slack_deg"],
        "closest_certificate_witness": minimum["closest_witness"],
        "continuous_vertex_only_neighbor_contact_free": True,
    }


def _extension_negative_control(side):
    _, specimen, layout, origin, axis, faces, _ = _exact_inputs(side)
    rows = _vertex_only_rows(faces)
    result = _certify_interval(
        specimen, layout, origin, axis, rows,
        SAFE_END_DEG, FIRST_SAMPLED_FAILURE_DEG,
    )
    return {
        "attempted_extension_deg": [SAFE_END_DEG, FIRST_SAMPLED_FAILURE_DEG],
        "rejected": not bool(result["certified"]),
        "reason": result.get("reason"),
    }


def audit_review006_continuous_vertex_only_neighbor_cone(contract=None):
    contract = contract or continuous_vertex_only_neighbor_contract()
    _validate_contract(contract)

    sides = {side: _certify_side(side) for side in ("L", "R")}
    pair_match = (
        sides["L"]["vertex_only_neighbor_pair_count"]
        == sides["R"]["vertex_only_neighbor_pair_count"]
    )
    slack_residual = abs(
        sides["L"]["minimum_certificate_slack_rad"]
        - sides["R"]["minimum_certificate_slack_rad"]
    )
    negatives = {side: _extension_negative_control(side) for side in ("L", "R")}
    continuous_pass = (
        pair_match
        and slack_residual <= 1e-12
        and all(row["continuous_vertex_only_neighbor_contact_free"] for row in sides.values())
        and all(
            row["minimum_certificate_slack_rad"] > CERTIFICATE_MARGIN_RAD
            for row in sides.values()
        )
        and all(row["rejected"] for row in negatives.values())
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if continuous_pass else FAIL_STATUS,
        "continuous_vertex_only_neighbor_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "all_real_owner_angles_certified": continuous_pass,
            "bilateral_pair_count_match": pair_match,
            "bilateral_minimum_slack_residual_rad": slack_residual,
            "sides": sides,
        },
        "retained_boundary": {
            "last_continuously_certified_clear_deg": SAFE_END_DEG,
            "first_retained_sampled_nonadjacent_failure_deg": FIRST_SAMPLED_FAILURE_DEG,
            "exact_first_contact_angle_solved": False,
        },
        "negative_control": {
            "description": (
                "attempt to certify the retained +36.55 to +36.60 extension "
                "as one interval"
            ),
            "sides": negatives,
            "rejected": all(row["rejected"] for row in negatives.values()),
        },
        "truth_boundary": [
            "All 845 vertex-only neighbouring face pairs per shoulder are continuously cone-separated for every real-valued owner angle from -40 through +36.55 degrees.",
            "Together with the separately retained continuous nonadjacent and edge-adjacent results, this closes the three indexed face-pair contact classes only for their stated predicates.",
            "The +36.60 nonadjacent intersection remains outside the guard; no exact first-contact angle is claimed.",
            "No anatomical ROM, Animation, Technical Art, Runtime, gameplay, visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_continuous_vertex_only_neighbor_cone_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    contract = continuous_vertex_only_neighbor_contract()
    audit = audit_review006_continuous_vertex_only_neighbor_cone(contract)
    (out / "review006-continuous-vertex-only-neighbor-contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "review006-continuous-vertex-only-neighbor-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return audit
