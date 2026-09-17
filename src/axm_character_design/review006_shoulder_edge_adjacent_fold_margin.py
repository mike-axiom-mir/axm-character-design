"""Sampled edge-adjacent fold-margin evidence for the exact review-006 shoulder rig.

The existing continuous certificate intentionally excludes triangle pairs that
share a source vertex index. This module closes one smaller Rigging-owned part
of that truth boundary without changing source geometry, selected topology,
joints, weights, motion, or downstream acceptance policy: it inspects every
*edge-adjacent* face pair at the same 0.05-degree resolution used by the
retained positive contact bracket.

For two triangles sharing an indexed edge, expected contact along that shared
edge is topological adjacency and must not be mislabelled as self-intersection.
A local fold-over/contact occurs when their two opposite vertices become
coplanar on the same ray around the shared edge. We therefore measure the
angular separation between the two opposite-vertex radial directions in the
plane perpendicular to the posed shared edge. Zero radians is the fold-over
boundary; pi radians is a flat, non-overlapping continuation across the edge.

This is finite sampled edge-adjacent evidence only. Vertex-only neighbours and
continuous between-sample edge-adjacent fold freedom remain explicitly held.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .review006_shoulder_continuous_clearance import (
    FIRST_SAMPLED_FAILURE_DEG,
    SAFE_END_DEG,
    SAFE_START_DEG,
    STATUS as CONTINUOUS_STATUS,
    _exact_inputs,
    _pose_at,
    audit_review006_continuous_nonadjacent_clearance,
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

SCHEMA = "axm.character-review006-edge-adjacent-fold-margin/v0.1"
STATUS = (
    "PASS_CHARACTER_REVIEW006_SAMPLED_EDGE_ADJACENT_FOLD_MARGIN_"
    "MINUS40_TO_PLUS3655__VERTEX_ONLY_AND_CONTINUOUS_HELD"
)
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_SAMPLED_EDGE_ADJACENT_FOLD_MARGIN"
SAMPLE_STEP_DEG = 0.05
SAMPLE_SCALE = 20
FOLD_CONTACT_EPSILON_RAD = 1e-9
GEOMETRY_EVIDENCE_HEAD = "7126a1a167c8a6249e4120349e096c606a9371b9"
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
    if magnitude <= 1e-15:
        raise ValueError("review-006 edge-adjacent observer found degenerate direction")
    return tuple(float(component) / magnitude for component in value)


def _sample_angles():
    start_tick = int(round(SAFE_START_DEG * SAMPLE_SCALE))
    end_tick = int(round(SAFE_END_DEG * SAMPLE_SCALE))
    return tuple(tick / SAMPLE_SCALE for tick in range(start_tick, end_tick + 1))


def _adjacency_rows(faces):
    edge_rows = []
    vertex_only_count = 0
    for left in range(len(faces)):
        left_set = set(faces[left])
        for right in range(left + 1, len(faces)):
            shared = sorted(left_set.intersection(faces[right]))
            if len(shared) == 1:
                vertex_only_count += 1
                continue
            if len(shared) != 2:
                continue
            left_opposite = next(index for index in faces[left] if index not in shared)
            right_opposite = next(index for index in faces[right] if index not in shared)
            edge_rows.append({
                "triangle_pair": [left, right],
                "shared_edge": shared,
                "opposite_vertices": [left_opposite, right_opposite],
            })
    edge_rows.sort(key=lambda row: (row["triangle_pair"][0], row["triangle_pair"][1]))
    return tuple(edge_rows), int(vertex_only_count)


def _edge_fold_angle(positions, adjacency):
    edge_a, edge_b = adjacency["shared_edge"]
    opposite_a, opposite_b = adjacency["opposite_vertices"]
    origin = tuple(float(value) for value in positions[edge_a])
    edge = _sub(positions[edge_b], origin)
    edge_unit = _unit(edge)

    def radial(vertex_index):
        offset = _sub(positions[vertex_index], origin)
        axial = _mul(edge_unit, _dot(offset, edge_unit))
        return _sub(offset, axial)

    radial_a = radial(opposite_a)
    radial_b = radial(opposite_b)
    radial_a_unit = _unit(radial_a)
    radial_b_unit = _unit(radial_b)
    sine = _length(_cross(radial_a_unit, radial_b_unit))
    cosine = max(-1.0, min(1.0, _dot(radial_a_unit, radial_b_unit)))
    return math.atan2(sine, cosine), _length(edge), _length(radial_a), _length(radial_b)


def _inspect_positions(positions, adjacency_rows):
    minimum_angle = math.inf
    closest = None
    fold_contact_count = 0
    minimum_edge_length = math.inf
    minimum_radial_length = math.inf
    for adjacency in adjacency_rows:
        angle, edge_length, radial_a, radial_b = _edge_fold_angle(positions, adjacency)
        minimum_edge_length = min(minimum_edge_length, edge_length)
        minimum_radial_length = min(minimum_radial_length, radial_a, radial_b)
        if angle < minimum_angle:
            minimum_angle = angle
            closest = {
                "triangle_pair": list(adjacency["triangle_pair"]),
                "shared_edge": list(adjacency["shared_edge"]),
                "opposite_vertices": list(adjacency["opposite_vertices"]),
                "fold_angle_rad": angle,
                "fold_angle_deg": math.degrees(angle),
            }
        if angle <= FOLD_CONTACT_EPSILON_RAD:
            fold_contact_count += 1
    return {
        "edge_adjacent_pair_count": len(adjacency_rows),
        "fold_contact_pair_count": fold_contact_count,
        "minimum_fold_angle_rad": minimum_angle,
        "minimum_fold_angle_deg": math.degrees(minimum_angle),
        "closest_fold_witness": closest,
        "minimum_shared_edge_length_m": minimum_edge_length,
        "minimum_opposite_radial_length_m": minimum_radial_length,
    }


def edge_adjacent_fold_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-sampled-edge-adjacent-fold-margin-001",
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
        "sampled_fold_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "step_deg": SAMPLE_STEP_DEG,
            "fold_contact_epsilon_rad": FOLD_CONTACT_EPSILON_RAD,
            "predicate": "EDGE_ADJACENT_OPPOSITE_RADIAL_SAME_RAY_IS_FOLD_CONTACT",
        },
        "truth_boundary": {
            "edge_adjacent_sampled_fold_contact_only": True,
            "continuous_edge_adjacent_fold_contact_proven": False,
            "vertex_only_neighbor_contact_proven": False,
            "nonadjacent_contact_replaced": False,
            "anatomical_range_of_motion": False,
            "animation_acceptance": False,
            "technical_art_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_contract(contract):
    if contract != edge_adjacent_fold_contract():
        raise ValueError("review-006 edge-adjacent fold contract identity drift")


def _sample_side(side):
    _, specimen, layout, origin, axis, faces, _ = _exact_inputs(side)
    adjacency_rows, vertex_only_count = _adjacency_rows(faces)
    if not adjacency_rows:
        raise ValueError("review-006 edge-adjacent observer found no indexed shared edges")

    minimum_angle = math.inf
    closest_sample = None
    fold_contact_samples = []
    sample_count = 0
    representative_positions = {}
    representative_rows = []
    representative_set = set(float(value) for value in REPRESENTATIVE_ANGLES_DEG)

    for angle in _sample_angles():
        posed = _pose_at(specimen, layout, origin, axis, angle)
        if not _pose_pass(posed):
            raise ValueError(f"review-006 sampled edge-adjacent pose structural failure at {angle} degrees")
        report = _inspect_positions(posed["positions"], adjacency_rows)
        sample_count += 1
        if report["fold_contact_pair_count"]:
            fold_contact_samples.append({"angle_deg": angle, "report": report})
        if report["minimum_fold_angle_rad"] < minimum_angle:
            minimum_angle = report["minimum_fold_angle_rad"]
            closest_sample = {
                "angle_deg": angle,
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

    # +36.60 is deliberately outside the certified/sampled guard but is retained
    # as the known first nonadjacent-contact witness. Observe edge adjacency there
    # to keep the two contact classes separate rather than transferring failure.
    outside_pose = _pose_at(specimen, layout, origin, axis, FIRST_SAMPLED_FAILURE_DEG)
    outside_report = _inspect_positions(outside_pose["positions"], adjacency_rows)
    representative_positions[float(FIRST_SAMPLED_FAILURE_DEG)] = outside_pose["positions"]
    representative_rows.append({
        "angle_deg": float(FIRST_SAMPLED_FAILURE_DEG),
        "release_weight": release_weight(FIRST_SAMPLED_FAILURE_DEG),
        "structural_status": "PASS" if _pose_pass(outside_pose) else "FAIL",
        "outside_sampled_edge_guard": True,
        "known_nonadjacent_contact_witness": True,
        **outside_report,
    })
    representative_rows.sort(key=lambda row: row["angle_deg"])

    return {
        "side": side,
        "sample_range_deg": [SAFE_START_DEG, SAFE_END_DEG],
        "sample_step_deg": SAMPLE_STEP_DEG,
        "sample_count": sample_count,
        "edge_adjacent_pair_count": len(adjacency_rows),
        "vertex_only_neighbor_pair_count": vertex_only_count,
        "fold_contact_sample_count": len(fold_contact_samples),
        "fold_contact_samples": fold_contact_samples[:12],
        "minimum_sampled_fold_angle_rad": minimum_angle,
        "minimum_sampled_fold_angle_deg": math.degrees(minimum_angle),
        "closest_sampled_fold_witness": closest_sample,
        "representative_rows": representative_rows,
        "representative_positions": representative_positions,
        "adjacency_rows": adjacency_rows,
        "specimen": specimen,
        "layout": layout,
        "origin": origin,
        "axis": axis,
    }


def _negative_control(side_result):
    specimen = side_result["specimen"]
    layout = side_result["layout"]
    origin = side_result["origin"]
    axis = side_result["axis"]
    adjacency = side_result["adjacency_rows"][0]
    posed = _pose_at(specimen, layout, origin, axis, 0.0)
    positions = [tuple(float(value) for value in point) for point in posed["positions"]]

    edge_a, edge_b = adjacency["shared_edge"]
    opposite_a, opposite_b = adjacency["opposite_vertices"]
    edge_origin = positions[edge_a]
    edge_unit = _unit(_sub(positions[edge_b], edge_origin))

    first_offset = _sub(positions[opposite_a], edge_origin)
    first_radial = _sub(first_offset, _mul(edge_unit, _dot(first_offset, edge_unit)))
    first_radial_unit = _unit(first_radial)

    second_offset = _sub(positions[opposite_b], edge_origin)
    second_axial = _dot(second_offset, edge_unit)
    second_radial = _sub(second_offset, _mul(edge_unit, second_axial))
    second_radial_length = _length(second_radial)
    positions[opposite_b] = _add(
        edge_origin,
        _add(
            _mul(edge_unit, second_axial),
            _mul(first_radial_unit, second_radial_length),
        ),
    )

    mutated_angle, _, _, _ = _edge_fold_angle(positions, adjacency)
    rejected = mutated_angle <= FOLD_CONTACT_EPSILON_RAD
    return {
        "side": side_result["side"],
        "mutation": "rotate one edge-adjacent opposite vertex onto the same radial ray around the shared edge",
        "triangle_pair": list(adjacency["triangle_pair"]),
        "shared_edge": list(adjacency["shared_edge"]),
        "mutated_opposite_vertex": int(opposite_b),
        "observed_fold_angle_rad": mutated_angle,
        "observed_fold_angle_deg": math.degrees(mutated_angle),
        "rejected": rejected,
        "expected": "REJECT_SAME_RAY_EDGE_ADJACENT_FOLD_CONTACT",
    }


def audit_review006_sampled_edge_adjacent_fold_margin(contract=None):
    contract = contract or edge_adjacent_fold_contract()
    _validate_contract(contract)

    continuous = audit_review006_continuous_nonadjacent_clearance()
    if continuous["status"] != CONTINUOUS_STATUS:
        raise ValueError("review-006 continuous nonadjacent-clearance prerequisite is not green")

    side_raw = {side: _sample_side(side) for side in ("L", "R")}
    side_results = {}
    for side, raw in side_raw.items():
        side_results[side] = {
            key: value for key, value in raw.items()
            if key not in {"representative_positions", "adjacency_rows", "specimen", "layout", "origin", "axis"}
        }

    sampled_pass = all(
        row["fold_contact_sample_count"] == 0
        and row["minimum_sampled_fold_angle_rad"] > FOLD_CONTACT_EPSILON_RAD
        for row in side_results.values()
    )
    bilateral_pair_count_match = (
        side_results["L"]["edge_adjacent_pair_count"]
        == side_results["R"]["edge_adjacent_pair_count"]
    )
    bilateral_minimum_residual = abs(
        side_results["L"]["minimum_sampled_fold_angle_rad"]
        - side_results["R"]["minimum_sampled_fold_angle_rad"]
    )
    bilateral_minimum_match = bilateral_minimum_residual <= 1e-12

    bilateral_representative_pose_mirror = True
    for angle in REPRESENTATIVE_ANGLES_DEG:
        bilateral_representative_pose_mirror &= (
            _mirror_position_set(side_raw["L"]["representative_positions"][float(angle)])
            == _position_set(side_raw["R"]["representative_positions"][float(angle)])
        )

    negatives = {side: _negative_control(side_raw[side]) for side in ("L", "R")}
    negative_control_rejected = all(row["rejected"] for row in negatives.values())

    pass_gate = (
        sampled_pass
        and bilateral_pair_count_match
        and bilateral_minimum_match
        and bilateral_representative_pose_mirror
        and negative_control_rejected
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if pass_gate else FAIL_STATUS,
        "contract": contract,
        "exact_identity": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "selected_geometry_head": GEOMETRY_HEAD,
            "current_geometry_evidence_head": GEOMETRY_EVIDENCE_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
        },
        "sampled_edge_adjacent_fold_guard": {
            "range_deg": [SAFE_START_DEG, SAFE_END_DEG],
            "step_deg": SAMPLE_STEP_DEG,
            "sample_count_per_side": len(_sample_angles()),
            "all_sampled_edge_adjacent_pairs_clear_of_same_ray_fold_contact": sampled_pass,
            "sides": side_results,
            "bilateral_pair_count_match": bilateral_pair_count_match,
            "bilateral_minimum_fold_angle_residual_rad": bilateral_minimum_residual,
            "bilateral_minimum_fold_angle_match": bilateral_minimum_match,
            "bilateral_representative_pose_mirror": bilateral_representative_pose_mirror,
        },
        "negative_control": {
            "rejected": negative_control_rejected,
            "sides": negatives,
        },
        "gates": {
            "exact_source_topology_profile_identity": "PASS",
            "continuous_nonadjacent_prerequisite": "PASS",
            "sampled_edge_adjacent_fold_margin": "PASS" if sampled_pass else "FAIL",
            "negative_same_ray_fold_control": "PASS_EXPECTED_REJECTION" if negative_control_rejected else "FAIL",
            "continuous_edge_adjacent_fold_contact": "NOT_PROVEN",
            "vertex_only_neighbor_contact": "NOT_PROVEN",
            "animation_acceptance": "NOT_EVALUATED",
            "technical_art_acceptance": "NOT_EVALUATED",
            "runtime_acceptance": "NOT_EVALUATED",
            "visual_acceptance": "NOT_EVALUATED",
        },
        "handoffs": {
            "geometry": (
                "No selected opening_repair index, face, vertex or topology digest changes. "
                "Edge adjacency is observed from exact existing indices only."
            ),
            "animation": (
                "The sampled structural fold margin is not anatomy, a clip range, timing, interpolation or playback acceptance."
            ),
            "technical_art_runtime": (
                "No target-host transport, controller enforcement, renderer, device or performance acceptance transfers."
            ),
            "visual_qa_art": (
                "This is owner-mesh structural evidence, not shaded deformation or aesthetic acceptance."
            ),
        },
        "truth_boundary": [
            "Source geometry, selected opening_repair topology, joint semantics and historical angle-conditioned weights are unchanged.",
            "Every edge-adjacent face pair is observed only at 0.05-degree samples from -40 through +36.55 degrees; continuous between-sample edge-fold freedom is not claimed.",
            "Pairs sharing only one indexed vertex remain outside this observer and are not claimed contact-free.",
            "The +36.60 retained nonadjacent contact remains a separate failure class and is not waived by any edge-adjacent result.",
            "No anatomy, Animation, Technical Art, Runtime, gameplay, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_sampled_edge_adjacent_fold_margin_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_sampled_edge_adjacent_fold_margin()
    with (out / "review006-sampled-edge-adjacent-fold-margin.json").open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if audit["status"] != STATUS:
        raise ValueError("review-006 sampled edge-adjacent fold-margin evidence did not pass")
    return audit
