"""Sampled vertex-only neighbour contact evidence for review-006 shoulders.

The existing review-006 Rigging chain already proves continuous nonadjacent
triangle clearance and continuous same-ray edge-adjacent fold clearance through
+36.55 degrees. Those observers intentionally leave face pairs that share only
one indexed vertex outside their claims.

For two triangles sharing exactly one vertex, any second common point would
produce a ray from that shared vertex that lies in both triangles' positive
angular cones. Each triangle cone is represented by the minor spherical arc
between its two outgoing edge directions. A strictly positive angular
separation between those two arcs is therefore a conservative sufficient
certificate that the triangles meet only at their intended shared vertex at the
sampled pose.

This module checks that predicate on the exact unchanged owner rig at the same
0.05-degree sampling used by the retained upper-bound contact probe. It does
not prove continuity between those samples and does not grant Animation,
Technical-Art, Runtime or visual acceptance.
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
from .review006_shoulder_continuous_edge_adjacent_fold import (
    STATUS as CONTINUOUS_EDGE_STATUS,
    audit_review006_continuous_edge_adjacent_fold_margin,
)
from .review006_shoulder_edge_adjacent_fold_margin import (
    SAMPLE_SCALE,
    SAMPLE_STEP_DEG,
    _adjacency_rows,
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

SCHEMA = "axm.character-review006-sampled-vertex-only-neighbor-cone-margin/v0.1"
STATUS = (
    "PASS_CHARACTER_REVIEW006_SAMPLED_VERTEX_ONLY_NEIGHBOR_CONE_MARGIN_"
    "MINUS40_TO_PLUS3655__CONTINUOUS_VERTEX_ONLY_HELD"
)
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_SAMPLED_VERTEX_ONLY_NEIGHBOR_CONE_MARGIN"
GEOMETRY_EVIDENCE_HEAD = "3519289f99c15ee3b7298b7bd625cf81e32b3c98"
VERTEX_CONTACT_EPSILON_RAD = 1e-9
ARC_MEMBERSHIP_TOLERANCE_RAD = 1e-9
DIRECTION_EPSILON = 1e-14
REPRESENTATIVE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 30.0, 36.55, 36.60)


def _sub(a, b):
    return tuple(float(a[index]) - float(b[index]) for index in range(3))


def _add(a, b):
    return tuple(float(a[index]) + float(b[index]) for index in range(3))


def _mul(a, scalar):
    return tuple(float(a[index]) * float(scalar) for index in range(3))


def _dot(a, b):
    return sum(float(a[index]) * float(b[index]) for index in range(3))


def _cross(a, b):
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _length(value):
    return math.sqrt(max(0.0, _dot(value, value)))


def _unit(value):
    magnitude = _length(value)
    if magnitude <= DIRECTION_EPSILON:
        raise ValueError("review-006 vertex-only observer found degenerate direction")
    return _mul(value, 1.0 / magnitude)


def _angle(a, b):
    a_u = _unit(a)
    b_u = _unit(b)
    return math.atan2(_length(_cross(a_u, b_u)), max(-1.0, min(1.0, _dot(a_u, b_u))))


def _sample_angles():
    start_tick = int(round(SAFE_START_DEG * SAMPLE_SCALE))
    end_tick = int(round(SAFE_END_DEG * SAMPLE_SCALE))
    return tuple(tick / SAMPLE_SCALE for tick in range(start_tick, end_tick + 1))


def _vertex_only_rows(faces):
    rows = []
    for left in range(len(faces)):
        left_face = tuple(int(value) for value in faces[left])
        left_set = set(left_face)
        for right in range(left + 1, len(faces)):
            right_face = tuple(int(value) for value in faces[right])
            shared = sorted(left_set.intersection(right_face))
            if len(shared) != 1:
                continue
            shared_vertex = int(shared[0])
            left_other = [value for value in left_face if value != shared_vertex]
            right_other = [value for value in right_face if value != shared_vertex]
            if len(left_other) != 2 or len(right_other) != 2:
                raise ValueError("review-006 vertex-only neighbour identity is malformed")
            rows.append({
                "triangle_pair": [left, right],
                "shared_vertex": shared_vertex,
                "left_other_vertices": left_other,
                "right_other_vertices": right_other,
            })
    rows.sort(key=lambda row: (row["triangle_pair"][0], row["triangle_pair"][1]))
    return tuple(rows)


def _on_minor_arc(point, start, end):
    total = _angle(start, end)
    split = _angle(start, point) + _angle(point, end)
    return split <= total + ARC_MEMBERSHIP_TOLERANCE_RAD


def _point_to_minor_arc_distance(point, start, end):
    point = _unit(point)
    start = _unit(start)
    end = _unit(end)
    normal = _cross(start, end)
    normal_length = _length(normal)
    if normal_length <= DIRECTION_EPSILON:
        raise ValueError("review-006 vertex-only triangle cone is angularly degenerate")
    normal = _mul(normal, 1.0 / normal_length)
    projected = _sub(point, _mul(normal, _dot(point, normal)))
    projected_length = _length(projected)
    candidates = []
    if projected_length > DIRECTION_EPSILON:
        nearest = _mul(projected, 1.0 / projected_length)
        for candidate in (nearest, _mul(nearest, -1.0)):
            if _on_minor_arc(candidate, start, end):
                candidates.append(_angle(point, candidate))
    candidates.extend((_angle(point, start), _angle(point, end)))
    return min(candidates)


def _minor_arc_separation(a, b, c, d):
    a = _unit(a)
    b = _unit(b)
    c = _unit(c)
    d = _unit(d)
    n1 = _cross(a, b)
    n2 = _cross(c, d)
    if _length(n1) <= DIRECTION_EPSILON or _length(n2) <= DIRECTION_EPSILON:
        raise ValueError("review-006 vertex-only cone contains degenerate spherical arc")

    # If either arc endpoint lies on the other minor arc, the two positive
    # angular cones already share a ray.
    for point, start, end in ((a, c, d), (b, c, d), (c, a, b), (d, a, b)):
        if _on_minor_arc(point, start, end):
            return 0.0

    intersections = _cross(n1, n2)
    if _length(intersections) > DIRECTION_EPSILON:
        intersection = _unit(intersections)
        for candidate in (intersection, _mul(intersection, -1.0)):
            if _on_minor_arc(candidate, a, b) and _on_minor_arc(candidate, c, d):
                return 0.0

    return min(
        _point_to_minor_arc_distance(a, c, d),
        _point_to_minor_arc_distance(b, c, d),
        _point_to_minor_arc_distance(c, a, b),
        _point_to_minor_arc_distance(d, a, b),
    )


def _pair_cone_separation(positions, row):
    shared = int(row["shared_vertex"])
    origin = positions[shared]
    left_a, left_b = row["left_other_vertices"]
    right_a, right_b = row["right_other_vertices"]
    return _minor_arc_separation(
        _sub(positions[left_a], origin),
        _sub(positions[left_b], origin),
        _sub(positions[right_a], origin),
        _sub(positions[right_b], origin),
    )


def _inspect_positions(positions, rows):
    minimum = math.inf
    closest = None
    uncertified_count = 0
    for row in rows:
        separation = _pair_cone_separation(positions, row)
        if separation < minimum:
            minimum = separation
            closest = {
                "triangle_pair": list(row["triangle_pair"]),
                "shared_vertex": int(row["shared_vertex"]),
                "left_other_vertices": list(row["left_other_vertices"]),
                "right_other_vertices": list(row["right_other_vertices"]),
                "cone_separation_rad": separation,
                "cone_separation_deg": math.degrees(separation),
            }
        if separation <= VERTEX_CONTACT_EPSILON_RAD:
            uncertified_count += 1
    return {
        "vertex_only_neighbor_pair_count": len(rows),
        "uncertified_pair_count": uncertified_count,
        "minimum_cone_separation_rad": minimum,
        "minimum_cone_separation_deg": math.degrees(minimum),
        "closest_cone_witness": closest,
    }


def sampled_vertex_only_neighbor_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-sampled-vertex-only-neighbor-cone-margin-001",
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
        "sampled_vertex_only_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "step_deg": SAMPLE_STEP_DEG,
            "contact_epsilon_rad": VERTEX_CONTACT_EPSILON_RAD,
            "predicate": (
                "POSITIVE_SPHERICAL_TRIANGLE_CONES_AROUND_SHARED_VERTEX_"
                "MUST_HAVE_STRICT_ANGULAR_SEPARATION"
            ),
        },
        "truth_boundary": {
            "sampled_vertex_only_neighbor_contact_proven": True,
            "continuous_vertex_only_neighbor_contact_proven": False,
            "edge_adjacent_or_nonadjacent_claim_replaced": False,
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
    if contract != sampled_vertex_only_neighbor_contract():
        raise ValueError("review-006 sampled vertex-only contract identity drift")


def _sample_side(side):
    _, specimen, layout, origin, axis, faces, _ = _exact_inputs(side)
    rows = _vertex_only_rows(faces)
    edge_rows, expected_vertex_only_count = _adjacency_rows(faces)
    if len(rows) != expected_vertex_only_count:
        raise ValueError("review-006 vertex-only pair count drift from adjacency observer")
    if not edge_rows or not rows:
        raise ValueError("review-006 vertex-only observer requires both adjacency classes")

    minimum = math.inf
    closest_sample = None
    failing_samples = []
    representative_positions = {}
    representative_rows = []
    representative_set = set(float(value) for value in REPRESENTATIVE_ANGLES_DEG)
    sample_count = 0

    for angle in _sample_angles():
        posed = _pose_at(specimen, layout, origin, axis, angle)
        if not _pose_pass(posed):
            raise ValueError(f"review-006 vertex-only pose structural failure at {angle} degrees")
        report = _inspect_positions(posed["positions"], rows)
        sample_count += 1
        if report["uncertified_pair_count"]:
            failing_samples.append({"angle_deg": float(angle), "report": report})
        if report["minimum_cone_separation_rad"] < minimum:
            minimum = report["minimum_cone_separation_rad"]
            closest_sample = {
                "angle_deg": float(angle),
                "release_weight": release_weight(angle),
                **report,
            }
        if float(angle) in representative_set:
            representative_positions[float(angle)] = posed["positions"]
            representative_rows.append({
                "angle_deg": float(angle),
                "release_weight": release_weight(angle),
                "structural_status": "PASS",
                **report,
            })

    outside = _pose_at(specimen, layout, origin, axis, FIRST_SAMPLED_FAILURE_DEG)
    outside_report = _inspect_positions(outside["positions"], rows)
    representative_positions[float(FIRST_SAMPLED_FAILURE_DEG)] = outside["positions"]
    representative_rows.append({
        "angle_deg": float(FIRST_SAMPLED_FAILURE_DEG),
        "release_weight": release_weight(FIRST_SAMPLED_FAILURE_DEG),
        "structural_status": "PASS" if _pose_pass(outside) else "FAIL",
        "outside_sampled_vertex_only_guard": True,
        "known_nonadjacent_contact_witness": True,
        **outside_report,
    })
    representative_rows.sort(key=lambda row: row["angle_deg"])

    return {
        "side": side,
        "sample_range_deg": [SAFE_START_DEG, SAFE_END_DEG],
        "sample_step_deg": SAMPLE_STEP_DEG,
        "sample_count": sample_count,
        "vertex_only_neighbor_pair_count": len(rows),
        "uncertified_sample_count": len(failing_samples),
        "uncertified_samples": failing_samples[:12],
        "minimum_sampled_cone_separation_rad": minimum,
        "minimum_sampled_cone_separation_deg": math.degrees(minimum),
        "closest_sampled_cone_witness": closest_sample,
        "representative_rows": representative_rows,
        "representative_positions": representative_positions,
        "rows": rows,
        "specimen": specimen,
        "layout": layout,
        "origin": origin,
        "axis": axis,
    }


def _negative_control(side_result):
    posed = _pose_at(
        side_result["specimen"],
        side_result["layout"],
        side_result["origin"],
        side_result["axis"],
        0.0,
    )
    positions = [tuple(float(value) for value in point) for point in posed["positions"]]
    row = side_result["rows"][0]
    shared = int(row["shared_vertex"])
    left_vertex = int(row["left_other_vertices"][0])
    right_vertex = int(row["right_other_vertices"][0])
    origin = positions[shared]
    target_direction = _unit(_sub(positions[left_vertex], origin))
    original_radius = _length(_sub(positions[right_vertex], origin))
    positions[right_vertex] = _add(origin, _mul(target_direction, original_radius))
    observed = _pair_cone_separation(positions, row)
    rejected = observed <= VERTEX_CONTACT_EPSILON_RAD
    return {
        "side": side_result["side"],
        "mutation": "align one vertex-only neighbour edge ray with the paired triangle cone endpoint",
        "triangle_pair": list(row["triangle_pair"]),
        "shared_vertex": shared,
        "mutated_vertex": right_vertex,
        "observed_cone_separation_rad": observed,
        "observed_cone_separation_deg": math.degrees(observed),
        "rejected": rejected,
        "expected": "REJECT_OVERLAPPING_VERTEX_ONLY_ANGULAR_CONES",
    }


def audit_review006_sampled_vertex_only_neighbor_cone_margin(contract=None):
    contract = contract or sampled_vertex_only_neighbor_contract()
    _validate_contract(contract)

    continuous_edge = audit_review006_continuous_edge_adjacent_fold_margin()
    if continuous_edge["status"] != CONTINUOUS_EDGE_STATUS:
        raise ValueError("continuous edge-adjacent prerequisite is not green")

    raw = {side: _sample_side(side) for side in ("L", "R")}
    sides = {
        side: {
            key: value for key, value in result.items()
            if key not in {"representative_positions", "rows", "specimen", "layout", "origin", "axis"}
        }
        for side, result in raw.items()
    }
    pair_count_match = (
        sides["L"]["vertex_only_neighbor_pair_count"]
        == sides["R"]["vertex_only_neighbor_pair_count"]
    )
    minimum_residual = abs(
        sides["L"]["minimum_sampled_cone_separation_rad"]
        - sides["R"]["minimum_sampled_cone_separation_rad"]
    )
    representative_mirror = True
    for angle in REPRESENTATIVE_ANGLES_DEG:
        left_positions = raw["L"]["representative_positions"][float(angle)]
        right_positions = raw["R"]["representative_positions"][float(angle)]
        if _mirror_position_set(left_positions) != _position_set(right_positions):
            representative_mirror = False
            break

    sampled_pass = (
        pair_count_match
        and representative_mirror
        and minimum_residual <= 1e-12
        and all(result["uncertified_sample_count"] == 0 for result in sides.values())
        and all(
            result["minimum_sampled_cone_separation_rad"] > VERTEX_CONTACT_EPSILON_RAD
            for result in sides.values()
        )
    )
    negatives = {side: _negative_control(raw[side]) for side in ("L", "R")}
    negative_rejected = all(row["rejected"] for row in negatives.values())
    status = STATUS if sampled_pass and negative_rejected else FAIL_STATUS

    return {
        "schema": SCHEMA,
        "status": status,
        "sampled_vertex_only_neighbor_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "step_deg": SAMPLE_STEP_DEG,
            "sample_count_per_side": len(_sample_angles()),
            "all_sampled_vertex_only_pairs_cone_separated": sampled_pass,
            "bilateral_pair_count_match": pair_count_match,
            "bilateral_minimum_cone_separation_residual_rad": minimum_residual,
            "bilateral_representative_pose_mirror": representative_mirror,
            "sides": sides,
        },
        "negative_control": {
            "rejected": negative_rejected,
            "sides": negatives,
        },
        "truth_boundary": [
            "Positive cone separation is a sufficient sampled-pose certificate that a vertex-only neighbour pair shares only its intended indexed vertex.",
            "The certificate is evaluated only at the retained 0.05-degree owner samples from -40 through +36.55 degrees.",
            "Continuous between-sample vertex-only neighbour freedom remains unproven and is not inherited from the edge-adjacent certificate.",
            "The +36.60 retained nonadjacent contact remains a separate failure class and is not erased by vertex-only results.",
            "No anatomy, Animation, Technical Art, Runtime, gameplay, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_sampled_vertex_only_neighbor_cone_margin_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_sampled_vertex_only_neighbor_cone_margin()
    with (out / "review006-sampled-vertex-only-neighbor-cone-margin.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(audit, handle, indent=2, sort_keys=True)
    with (out / "review006-sampled-vertex-only-neighbor-contract.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(sampled_vertex_only_neighbor_contract(), handle, indent=2, sort_keys=True)
    return audit
