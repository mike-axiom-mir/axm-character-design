"""Continuous nonadjacent-clearance certificate for the exact review-006 shoulder rig.

The retained 0.05-degree observer brackets the first measured positive shoulder
self-intersection between +36.55 and +36.60 degrees. This module closes one
narrow Rigging-owned gap: it proves that the unchanged owner deformation map is
nonadjacent-triangle-intersection-free for every real-valued shoulder angle in
[-40, +36.55] degrees, not merely at sampled keys.

The proof is conservative. Each angular interval is evaluated at its midpoint;
a closed-form per-vertex speed bound for the exact owner pose map bounds how far
each triangle can move anywhere inside that interval. Exact midpoint
triangle-triangle distance must exceed the two triangles' possible motion by a
strict numerical margin. Intervals that cannot be certified are subdivided.

This says nothing about indexed-neighbour fold/contact, anatomy, Animation
range/timing, target-host transport, Runtime/controller behaviour, gameplay, or
visual acceptance.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .organic_form import canonical_digest
from .review006_connected_geometry import build_opening_repair
from .review006_self_intersection import (
    _triangles_intersect,
    inspect_triangle_self_intersections,
)
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
    _mirror_position_set,
    _pose,
    _pose_pass,
    _position_set,
    _reindexed_layout,
    _weights,
    historical_successor_profile,
    rebind_contract,
    release_weight,
)
from .review006_shoulder_subdegree_boundary import (
    STATUS as SUBDEGREE_STATUS,
    audit_review006_positive_subdegree_boundary,
)
from .shoulder_pose_clearance_refinement import (
    VARIANT_ID as REVIEW006_ID,
    shoulder_pose_clearance_refinement_candidate,
)

SCHEMA = "axm.character-review006-continuous-nonadjacent-clearance/v0.1"
STATUS = (
    "PASS_CHARACTER_REVIEW006_CONTINUOUS_NONADJACENT_CLEARANCE_"
    "MINUS40_TO_PLUS3655__CONTACT_BRACKET_RETAINED"
)
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_CONTINUOUS_NONADJACENT_CLEARANCE"
CURRENT_GEOMETRY_EVIDENCE_HEAD = "7126a1a167c8a6249e4120349e096c606a9371b9"
SAFE_START_DEG = -40.0
SAFE_END_DEG = 36.55
FIRST_SAMPLED_FAILURE_DEG = 36.60
BASE_INTERVAL_DEG = 0.5
MIN_INTERVAL_DEG = 0.00005
MAX_SUBDIVISION_DEPTH = 16
INTERSECTION_EPSILON_M = 1e-9
CERTIFICATE_MARGIN_M = 2e-10
REPRESENTATIVE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 30.0, 36.55, 36.60)


def _sub(a, b):
    return tuple(float(a[i]) - float(b[i]) for i in range(3))


def _add(a, b):
    return tuple(float(a[i]) + float(b[i]) for i in range(3))


def _mul(a, scalar):
    return tuple(float(a[i]) * float(scalar) for i in range(3))


def _dot(a, b):
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _length_sq(value):
    return _dot(value, value)


def _clamp(value, lo=0.0, hi=1.0):
    return min(max(float(value), float(lo)), float(hi))


def _point_segment_distance_sq(point, a, b):
    ab = _sub(b, a)
    denom = _length_sq(ab)
    if denom <= 1e-30:
        return _length_sq(_sub(point, a))
    t = _clamp(_dot(_sub(point, a), ab) / denom)
    closest = _add(a, _mul(ab, t))
    return _length_sq(_sub(point, closest))


def _point_triangle_distance_sq(point, triangle):
    """Squared Euclidean point/triangle distance (Ericson region tests)."""
    a, b, c = triangle
    ab = _sub(b, a)
    ac = _sub(c, a)
    ap = _sub(point, a)
    d1 = _dot(ab, ap)
    d2 = _dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return _length_sq(ap)

    bp = _sub(point, b)
    d3 = _dot(ab, bp)
    d4 = _dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return _length_sq(bp)

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        closest = _add(a, _mul(ab, v))
        return _length_sq(_sub(point, closest))

    cp = _sub(point, c)
    d5 = _dot(ab, cp)
    d6 = _dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return _length_sq(cp)

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        closest = _add(a, _mul(ac, w))
        return _length_sq(_sub(point, closest))

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        edge = _sub(c, b)
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        closest = _add(b, _mul(edge, w))
        return _length_sq(_sub(point, closest))

    denom = va + vb + vc
    if abs(denom) <= 1e-30:
        return min(
            _point_segment_distance_sq(point, a, b),
            _point_segment_distance_sq(point, b, c),
            _point_segment_distance_sq(point, c, a),
        )
    inv = 1.0 / denom
    v = vb * inv
    w = vc * inv
    closest = _add(a, _add(_mul(ab, v), _mul(ac, w)))
    return _length_sq(_sub(point, closest))


def _segment_segment_distance_sq(p1, q1, p2, q2):
    d1 = _sub(q1, p1)
    d2 = _sub(q2, p2)
    r = _sub(p1, p2)
    a = _dot(d1, d1)
    e = _dot(d2, d2)
    f = _dot(d2, r)
    tiny = 1e-30

    if a <= tiny and e <= tiny:
        return _length_sq(r)
    if a <= tiny:
        s = 0.0
        t = _clamp(f / e)
    else:
        c = _dot(d1, r)
        if e <= tiny:
            t = 0.0
            s = _clamp(-c / a)
        else:
            b = _dot(d1, d2)
            denom = a * e - b * b
            s = _clamp((b * f - c * e) / denom) if abs(denom) > tiny else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t = 0.0
                s = _clamp(-c / a)
            elif t > 1.0:
                t = 1.0
                s = _clamp((b - c) / a)

    c1 = _add(p1, _mul(d1, s))
    c2 = _add(p2, _mul(d2, t))
    return _length_sq(_sub(c1, c2))


def _triangle_distance(first, second):
    if _triangles_intersect(first, second, INTERSECTION_EPSILON_M):
        return 0.0
    best = min(
        *(_point_triangle_distance_sq(point, second) for point in first),
        *(_point_triangle_distance_sq(point, first) for point in second),
    )
    first_edges = ((first[0], first[1]), (first[1], first[2]), (first[2], first[0]))
    second_edges = ((second[0], second[1]), (second[1], second[2]), (second[2], second[0]))
    for a0, a1 in first_edges:
        for b0, b1 in second_edges:
            best = min(best, _segment_segment_distance_sq(a0, a1, b0, b1))
    return math.sqrt(max(0.0, best))


def _aabb_gap(first, second):
    gap_sq = 0.0
    for axis in range(3):
        amin = min(point[axis] for point in first)
        amax = max(point[axis] for point in first)
        bmin = min(point[axis] for point in second)
        bmax = max(point[axis] for point in second)
        if amax < bmin:
            gap = bmin - amax
        elif bmax < amin:
            gap = amin - bmax
        else:
            gap = 0.0
        gap_sq += gap * gap
    return math.sqrt(gap_sq)


def _triangle_index_data(indices):
    faces = [tuple(indices[offset: offset + 3]) for offset in range(0, len(indices), 3)]
    pairs = []
    for left in range(len(faces)):
        left_vertices = set(faces[left])
        for right in range(left + 1, len(faces)):
            if left_vertices.intersection(faces[right]):
                continue
            pairs.append((left, right))
    return faces, tuple(pairs)


def continuous_clearance_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-continuous-nonadjacent-clearance-001",
        "source": {
            "review006_id": REVIEW006_ID,
            "source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
        },
        "geometry": {
            "selected_geometry_head": GEOMETRY_HEAD,
            "current_evidence_head": CURRENT_GEOMETRY_EVIDENCE_HEAD,
            "selected_stage": "opening_repair",
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "current_evidence_head_changes_selected_topology": False,
        },
        "rig": {
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "profile_reauthored": False,
            "weights_reauthored": False,
            "joint_semantics_reauthored": False,
        },
        "continuous_certificate": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "base_interval_deg": BASE_INTERVAL_DEG,
            "minimum_interval_deg": MIN_INTERVAL_DEG,
            "max_subdivision_depth": MAX_SUBDIVISION_DEPTH,
            "intersection_epsilon_m": INTERSECTION_EPSILON_M,
            "strict_certificate_margin_m": CERTIFICATE_MARGIN_M,
            "method": "MIDPOINT_TRIANGLE_DISTANCE_MINUS_CLOSED_FORM_VERTEX_MOTION_BOUND",
        },
        "contact_boundary": {
            "last_continuously_certified_clear_deg": SAFE_END_DEG,
            "first_retained_sampled_failure_deg": FIRST_SAMPLED_FAILURE_DEG,
            "exact_contact_angle_solved": False,
        },
        "truth_boundary": {
            "nonadjacent_triangle_continuity_only": True,
            "indexed_neighbor_fold_contact_proven": False,
            "anatomical_range_of_motion": False,
            "animation_acceptance": False,
            "technical_art_transport_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_contract(contract):
    if contract != continuous_clearance_contract():
        raise ValueError("review-006 continuous-clearance contract identity drift")


def _exact_inputs(side):
    source = shoulder_pose_clearance_refinement_candidate()
    if source.get("study_id") != REVIEW006_ID:
        raise ValueError("review-006 source ID drift")
    if canonical_digest(source) != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 source digest drift")
    profile = historical_successor_profile()
    if canonical_digest(profile) != EXPECTED_PROFILE_DIGEST:
        raise ValueError("review-006 Rigging profile digest drift")
    specimen = build_opening_repair(side)
    observed_topology = canonical_digest({
        "positions": specimen["positions"],
        "faces": specimen["faces"],
    })
    if observed_topology != EXPECTED_TOPOLOGY_DIGESTS[side]:
        raise ValueError(f"review-006 selected Geometry topology identity drift for {side}")
    layout = _reindexed_layout(side, specimen)
    joint = rebind_contract()["rig_method"]["joint_semantics"][side]
    origin = tuple(float(value) for value in source["landmarks"][joint["landmark"]])
    axis = tuple(float(value) for value in joint["axis"])
    faces, pairs = _triangle_index_data(specimen["indices"])
    return source, specimen, layout, origin, axis, faces, pairs


def _pose_at(specimen, layout, origin, axis, angle_deg):
    return _pose(
        specimen,
        origin,
        axis,
        float(angle_deg),
        _weights(layout, release_weight(angle_deg), len(specimen["positions"])),
    )


def _release_derivative_bound_per_radian(max_abs_deg):
    magnitude = min(abs(float(max_abs_deg)), 40.0)
    if magnitude <= 0.0:
        return 0.0
    derivative_per_degree = (
        MAX_RELEASE_WEIGHT
        * RELEASE_POWER
        / 40.0
        * ((magnitude / 40.0) ** (RELEASE_POWER - 1.0))
    )
    return derivative_per_degree * (180.0 / math.pi)


def _vertex_speed_bounds(specimen, layout, origin, interval_start_deg, interval_end_deg):
    max_abs = max(abs(float(interval_start_deg)), abs(float(interval_end_deg)))
    w_max = release_weight(max_abs)
    dw_max = _release_derivative_bound_per_radian(max_abs)
    fixed = set(layout["groups"]["ribcage"]) | set(layout["groups"]["seam"])
    proximal = set(layout["groups"]["proximal"])
    rigid = set(layout["groups"]["distal"]) | set(layout["groups"]["distal_cap"])
    bounds = []
    for index, point in enumerate(specimen["positions"]):
        radius = math.dist(tuple(float(value) for value in point), origin)
        if index in fixed:
            speed = 0.0
        elif index in rigid:
            speed = radius
        elif index in proximal:
            speed = radius * (2.0 * dw_max + w_max)
        else:
            raise ValueError("review-006 continuous certificate found uncovered Rigging vertex")
        bounds.append(speed)
    return tuple(bounds)


def _certify_interval(specimen, layout, origin, axis, faces, pairs, start_deg, end_deg):
    midpoint = 0.5 * (float(start_deg) + float(end_deg))
    posed = _pose_at(specimen, layout, origin, axis, midpoint)
    if not _pose_pass(posed):
        return {"certified": False, "reason": "MIDPOINT_STRUCTURAL_FAILURE", "angle_deg": midpoint}
    positions = posed["positions"]
    triangles = [tuple(positions[index] for index in face) for face in faces]
    speeds = _vertex_speed_bounds(specimen, layout, origin, start_deg, end_deg)
    half_width_rad = math.radians(0.5 * (float(end_deg) - float(start_deg)))
    vertex_motion = tuple(speed * half_width_rad for speed in speeds)
    triangle_motion = tuple(max(vertex_motion[index] for index in face) for face in faces)

    minimum_slack = math.inf
    closest_pair = None
    exact_distance_evaluations = 0
    for left, right in pairs:
        motion_bound = triangle_motion[left] + triangle_motion[right]
        first = triangles[left]
        second = triangles[right]
        lower_bound = _aabb_gap(first, second)
        if lower_bound <= motion_bound + CERTIFICATE_MARGIN_M:
            exact_distance_evaluations += 1
            lower_bound = _triangle_distance(first, second)
        slack = lower_bound - motion_bound
        if slack < minimum_slack:
            minimum_slack = slack
            closest_pair = [left, right]
        if slack <= CERTIFICATE_MARGIN_M:
            return {
                "certified": False,
                "reason": "INSUFFICIENT_CONTINUOUS_SEPARATION_MARGIN",
                "interval_deg": [float(start_deg), float(end_deg)],
                "midpoint_deg": midpoint,
                "triangle_pair": [left, right],
                "midpoint_distance_lower_bound_m": lower_bound,
                "triangle_motion_bound_m": motion_bound,
                "certificate_slack_m": slack,
                "exact_distance_evaluations": exact_distance_evaluations,
            }

    return {
        "certified": True,
        "interval_deg": [float(start_deg), float(end_deg)],
        "midpoint_deg": midpoint,
        "minimum_certificate_slack_m": minimum_slack,
        "closest_pair": closest_pair,
        "exact_distance_evaluations": exact_distance_evaluations,
        "max_vertex_motion_bound_m": max(vertex_motion),
    }


def _endpoint_intersections(specimen, layout, origin, axis, angle_deg):
    posed = _pose_at(specimen, layout, origin, axis, angle_deg)
    report = inspect_triangle_self_intersections(
        posed["positions"], specimen["indices"], epsilon=INTERSECTION_EPSILON_M, max_examples=12
    )
    return posed, report


def _continuous_certificate_for_side(side, end_deg=SAFE_END_DEG):
    _, specimen, layout, origin, axis, faces, pairs = _exact_inputs(side)
    start_pose, start_report = _endpoint_intersections(
        specimen, layout, origin, axis, SAFE_START_DEG
    )
    end_pose, end_report = _endpoint_intersections(specimen, layout, origin, axis, end_deg)
    if not _pose_pass(start_pose) or start_report["self_intersection_pair_count"]:
        return {
            "side": side,
            "certified": False,
            "reason": "START_ENDPOINT_NOT_CLEAR",
            "end_deg": float(end_deg),
            "endpoint_report": start_report,
        }
    if not _pose_pass(end_pose) or end_report["self_intersection_pair_count"]:
        return {
            "side": side,
            "certified": False,
            "reason": "END_ENDPOINT_NOT_CLEAR",
            "end_deg": float(end_deg),
            "endpoint_report": end_report,
        }

    intervals = []
    current = SAFE_START_DEG
    while current < float(end_deg) - 1e-12:
        next_end = min(current + BASE_INTERVAL_DEG, float(end_deg))
        intervals.append((current, next_end, 0))
        current = next_end

    certified_rows = []
    subdivisions = 0
    max_depth = 0
    total_exact_distance_evaluations = 0
    minimum_slack = math.inf
    closest_witness = None

    while intervals:
        start, finish, depth = intervals.pop()
        result = _certify_interval(
            specimen, layout, origin, axis, faces, pairs, start, finish
        )
        total_exact_distance_evaluations += int(result.get("exact_distance_evaluations", 0))
        max_depth = max(max_depth, depth)
        if result["certified"]:
            certified_rows.append(result)
            slack = float(result["minimum_certificate_slack_m"])
            if slack < minimum_slack:
                minimum_slack = slack
                closest_witness = {
                    "interval_deg": result["interval_deg"],
                    "triangle_pair": result["closest_pair"],
                    "certificate_slack_m": slack,
                }
            continue

        width = finish - start
        if depth >= MAX_SUBDIVISION_DEPTH or width <= MIN_INTERVAL_DEG:
            return {
                "side": side,
                "certified": False,
                "reason": "SUBDIVISION_LIMIT_WITHOUT_CERTIFICATE",
                "end_deg": float(end_deg),
                "failed_interval": result,
                "certified_interval_count": len(certified_rows),
                "subdivision_count": subdivisions,
                "max_depth": max_depth,
                "triangle_pair_count": len(pairs),
                "exact_distance_evaluations": total_exact_distance_evaluations,
            }
        midpoint = 0.5 * (start + finish)
        intervals.append((midpoint, finish, depth + 1))
        intervals.append((start, midpoint, depth + 1))
        subdivisions += 1

    return {
        "side": side,
        "certified": True,
        "range_deg": [SAFE_START_DEG, float(end_deg)],
        "triangle_pair_count": len(pairs),
        "certified_interval_count": len(certified_rows),
        "subdivision_count": subdivisions,
        "max_depth": max_depth,
        "exact_distance_evaluations": total_exact_distance_evaluations,
        "minimum_certificate_slack_m": minimum_slack,
        "closest_certificate_witness": closest_witness,
        "start_endpoint_intersections": start_report["self_intersection_pair_count"],
        "end_endpoint_intersections": end_report["self_intersection_pair_count"],
    }


def _representative_rows(side):
    _, specimen, layout, origin, axis, _, _ = _exact_inputs(side)
    rows = []
    positions = {}
    for angle in REPRESENTATIVE_ANGLES_DEG:
        posed, report = _endpoint_intersections(specimen, layout, origin, axis, angle)
        positions[float(angle)] = posed["positions"]
        rows.append({
            "side": side,
            "angle_deg": float(angle),
            "release_weight": release_weight(angle),
            "structural_status": "PASS" if _pose_pass(posed) else "FAIL",
            "nonadjacent_intersection_pair_count": int(report["self_intersection_pair_count"]),
            "intersection_examples": report["examples"],
            "minimum_triangle_area_ratio": posed["minimum_triangle_area_ratio"],
            "maximum_triangle_area_ratio": posed["maximum_triangle_area_ratio"],
            "minimum_edge_length_ratio": posed["minimum_edge_length_ratio"],
            "maximum_edge_length_ratio": posed["maximum_edge_length_ratio"],
        })
    return rows, positions


def audit_review006_continuous_nonadjacent_clearance(contract=None):
    contract = contract or continuous_clearance_contract()
    _validate_contract(contract)

    subdegree = audit_review006_positive_subdegree_boundary()
    if subdegree["status"] != SUBDEGREE_STATUS:
        raise ValueError("review-006 subdegree boundary prerequisite is not green")
    for side in ("L", "R"):
        boundary = subdegree["subdegree_probe"]["boundaries"][side]
        if boundary["last_sampled_clear_deg"] != SAFE_END_DEG:
            raise ValueError("review-006 retained last-clear boundary drift")
        if boundary["first_sampled_failure_deg"] != FIRST_SAMPLED_FAILURE_DEG:
            raise ValueError("review-006 retained first-failure boundary drift")

    side_results = {
        side: _continuous_certificate_for_side(side, SAFE_END_DEG)
        for side in ("L", "R")
    }
    continuous_pass = all(result["certified"] for result in side_results.values())

    representatives = {}
    representative_positions = {}
    for side in ("L", "R"):
        rows, positions = _representative_rows(side)
        representatives[side] = rows
        representative_positions[side] = positions

    bilateral_mirror = True
    for angle in REPRESENTATIVE_ANGLES_DEG:
        bilateral_mirror &= (
            _mirror_position_set(representative_positions["L"][float(angle)])
            == _position_set(representative_positions["R"][float(angle)])
        )

    failure_rows = {
        side: next(
            row for row in representatives[side]
            if row["angle_deg"] == FIRST_SAMPLED_FAILURE_DEG
        )
        for side in ("L", "R")
    }
    sampled_failure_retained = all(
        row["nonadjacent_intersection_pair_count"] > 0
        for row in failure_rows.values()
    )
    bilateral_failure_match = (
        failure_rows["L"]["nonadjacent_intersection_pair_count"]
        == failure_rows["R"]["nonadjacent_intersection_pair_count"]
        and failure_rows["L"]["intersection_examples"]
        == failure_rows["R"]["intersection_examples"]
    )

    false_extension = {
        side: _continuous_certificate_for_side(side, FIRST_SAMPLED_FAILURE_DEG)
        for side in ("L", "R")
    }
    false_extension_rejected = all(
        not result["certified"]
        and result["reason"] == "END_ENDPOINT_NOT_CLEAR"
        for result in false_extension.values()
    )

    pass_gate = (
        continuous_pass
        and bilateral_mirror
        and sampled_failure_retained
        and bilateral_failure_match
        and false_extension_rejected
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if pass_gate else FAIL_STATUS,
        "contract": contract,
        "exact_identity": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "selected_geometry_head": GEOMETRY_HEAD,
            "current_geometry_evidence_head": CURRENT_GEOMETRY_EVIDENCE_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
        },
        "continuous_clearance": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "nonadjacent_triangle_clearance_proven_for_all_real_angles": continuous_pass,
            "sides": side_results,
            "bilateral_representative_pose_mirror": bilateral_mirror,
        },
        "contact_transition": {
            "last_continuously_certified_clear_deg": SAFE_END_DEG,
            "first_retained_sampled_failure_deg": FIRST_SAMPLED_FAILURE_DEG,
            "transition_bracket_deg": [SAFE_END_DEG, FIRST_SAMPLED_FAILURE_DEG],
            "transition_bracket_width_deg": FIRST_SAMPLED_FAILURE_DEG - SAFE_END_DEG,
            "first_failure_rows": failure_rows,
            "exact_contact_angle_solved": False,
        },
        "representative_poses": representatives,
        "negative_control": {
            "mutation": "extend continuously certified guard through retained +36.60 failing pose",
            "rejected": false_extension_rejected,
            "side_results": false_extension,
            "expected": "REJECT_CONTINUOUS_GUARD_WITH_INTERSECTING_ENDPOINT",
        },
        "gates": {
            "exact_source_topology_profile_identity": "PASS",
            "retained_subdegree_boundary": "PASS",
            "continuous_nonadjacent_clearance_minus40_to_plus3655": "PASS" if continuous_pass else "FAIL",
            "bilateral_representative_pose_mirror": "PASS" if bilateral_mirror else "FAIL",
            "retained_first_sampled_failure": "PASS" if sampled_failure_retained else "FAIL",
            "false_guard_extension_control": "PASS_EXPECTED_REJECTION" if false_extension_rejected else "FAIL",
            "indexed_neighbor_fold_contact": "NOT_PROVEN",
            "anatomical_range_of_motion": "NOT_CLAIMED",
            "animation_acceptance": "NOT_EVALUATED",
            "technical_art_transport_acceptance": "NOT_EVALUATED",
            "runtime_acceptance": "NOT_EVALUATED",
            "visual_acceptance": "NOT_EVALUATED",
        },
        "handoffs": {
            "geometry": (
                "Current Geometry evidence head is recorded separately from the unchanged selected opening_repair topology. "
                "No topology change or Geometry acceptance is requested."
            ),
            "animation": (
                "The continuously certified structural guard is not anatomy and is not an authored clip/range. "
                "Animation keeps timing, interpolation, amplitude and playback authority."
            ),
            "technical_art_runtime": (
                "No target-host skin transport, controller enforcement, device behaviour or performance acceptance transfers."
            ),
            "visual_qa_art": (
                "The contact bracket is structural nonadjacent-triangle evidence only. Final deformation appearance remains independent."
            ),
        },
        "truth_boundary": [
            "Source geometry, selected opening_repair topology, joint semantics and the historical angle-conditioned weight profile are unchanged.",
            "The continuous certificate is valid only for nonadjacent triangle intersection under the exact owner pose map over [-40,+36.55] degrees.",
            "Indexed-neighbour fold/contact remains excluded by the inherited observer and is not proven here.",
            "The exact first contact angle is not solved; the retained transition remains bounded only inside (36.55,36.60] degrees.",
            "No anatomy, Animation, Technical Art, Runtime, gameplay, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_continuous_nonadjacent_clearance_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_continuous_nonadjacent_clearance()
    with (out / "review006-continuous-nonadjacent-clearance.json").open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if audit["status"] != STATUS:
        raise ValueError("review-006 continuous nonadjacent-clearance evidence did not pass")
    return audit
