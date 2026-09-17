"""Geometry rebind for the Art/QA-selected Character review-006 source identity.

This module deliberately does not inherit the accepted-E Geometry PASS/HOLD results.
It reconstructs a small family of previously useful connected-shoulder topology
patterns from the exact review-006 source, validates each from scratch, and observes
neutral nonadjacent triangle intersections.

Historical topology patterns are method precedent only. Their old scores, Rigging
poses and acceptance states do not transfer to this source identity.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
import math
from pathlib import Path

from .organic_form import _ellipsoid_mesh, _segment_mesh, canonical_digest, write_obj
from .review006_self_intersection import inspect_triangle_self_intersections
from .shoulder_pose_clearance_refinement import (
    VARIANT_ID as REVIEW006_ID,
    shoulder_pose_clearance_refinement_candidate,
)
from .shoulder_source_lineage import build_adopted_character_mesh
from .shoulder_transition_feathered import BLEND_WEIGHTS, ROOT_RING_INDICES, TARGET_AXIS_SCALE

SCHEMA = "axm.character-review006-connected-geometry-rebind/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_EXACT_CONNECTED_GEOMETRY_REBIND__NEUTRAL_INTERSECTION_OBSERVED"

ORGANIC_HEAD = "e27067477922b13b14a2cfcc7f3659b97a10b8a7"
EXPECTED_REVIEW006_SOURCE_DIGEST = "8e9252ede4d257509e4eacb595f1c234aa100a42dc46a54b7b45550f2619c5e1"
EXPECTED_REVIEW006_MESH_DIGEST = "f173b2af9b7bf69ca78bce2ec2daa07a083748590d9ae9e99443962a6d1aa8e7"

ART_DIRECTION = {
    "repository": "mike-axiom-mir/axm-create-me",
    "status": "PASS_ART_DIRECTION_CHARACTER_REVIEW006_NEUTRAL_FORM_PREFERENCE_023",
    "meaning": "review-006 is the selected next Geometry review input; source adoption remains held",
}
VISUAL_QA = {
    "repository": "mike-axiom-mir/axm-create-me",
    "status": "PASS_CHARACTER_REVIEW006_INDEPENDENT_RETAINED_VISUAL_COHERENCE_GATE",
    "meaning": "independent source-form visual coherence passed; exact Geometry and Rigging remain pending",
}
HISTORICAL_GEOMETRY_PRECEDENT = {
    "repository": "mike-axiom-mir/axm-character-design",
    "accepted_E_geometry_head": "31675939985aee37eaba7beea58c9443eb85b9ac",
    "base_connected_topology_blob": "4614884e7e49a63712d48e7f24f0d92fbeb99488",
    "opening_repair_blob": "1e44ad922b857a6d1466d9b1007e9da1b03d48e1",
    "diagonal_repair_blob": "34c0ed2a503dd697fdf2b891afadf8ade26f8e1b",
    "stitch_repair_blob": "e97ece45aa52162b02e5159dbc3dccbc912e012a",
    "policy": "TOPOLOGY_PATTERN_PRECEDENT_ONLY__NO_OLD_SCORE_OR_PASS_TRANSFER",
}

_SELECTED = tuple(ROOT_RING_INDICES)
_SELECTED_WEIGHT = dict(zip(_SELECTED, BLEND_WEIGHTS))
_INFERIOR_CLOSURE = tuple(index for index in range(10) if index not in _SELECTED)

_RIBCAGE_HOLE_FACE_IDS = {
    "L": (20, 21, 22, 23, 24, 25, 26, 27),
    "R": (32, 33, 34, 35, 12, 13, 14, 15),
}
_RIBCAGE_HOLE_PHASE = {"L": 5, "R": 3}
_PROXIMAL_SAMPLE_T = 0.06

_EXTRA_RIBCAGE_FACE_INDICES = {
    "L": (38, 39, 40, 41),
    "R": (28, 29, 50, 51),
}
_EXPANDED_HOLE_PHASE = {"L": 0, "R": 10}
_SEAM_PHASE = {"L": 0, "R": 0}

DIAGONAL_QUAD_INDEX = 1
STITCH_FACE_PAIRS = ((111, 112), (114, 115))
STAGES = ("connected_baseline", "opening_repair", "diagonal_repair", "stitch_repair")


def _sub(a, b):
    return tuple(float(a[i]) - float(b[i]) for i in range(3))


def _add(a, b):
    return tuple(float(a[i]) + float(b[i]) for i in range(3))


def _mul(a, scalar):
    return tuple(float(a[i]) * float(scalar) for i in range(3))


def _dot(a, b):
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _cross(a, b):
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _length(value):
    return math.sqrt(_dot(value, value))


def _unit(value, label):
    magnitude = _length(value)
    if magnitude <= 1e-12:
        raise ValueError(f"{label} must have non-zero length")
    return _mul(value, 1.0 / magnitude)


def _triangle_area(positions, face):
    a, b, c = (positions[index] for index in face)
    return 0.5 * _length(_cross(_sub(b, a), _sub(c, a)))


def _ellipsoid_implicit(point, mass):
    return sum(
        ((float(point[i]) - float(mass["center"][i])) / float(mass["radii"][i])) ** 2
        for i in range(3)
    )


def _line_to_ellipsoid_surface(inside, outside, mass):
    if _ellipsoid_implicit(inside, mass) > 1.0 + 1e-8:
        raise ValueError("expected review-006 accepted-E proximal sample inside/on ribcage")
    if _ellipsoid_implicit(outside, mass) < 1.0 - 1e-8:
        raise ValueError("expected review-006 upper-arm root sample outside/on ribcage")
    center = tuple(float(value) for value in mass["center"])
    radii = tuple(float(value) for value in mass["radii"])
    direction = _sub(outside, inside)
    offset = _sub(inside, center)
    qa = sum((direction[i] / radii[i]) ** 2 for i in range(3))
    qb = 2.0 * sum(offset[i] * direction[i] / (radii[i] ** 2) for i in range(3))
    qc = sum((offset[i] / radii[i]) ** 2 for i in range(3)) - 1.0
    discriminant = qb * qb - 4.0 * qa * qc
    if discriminant < -1e-12:
        raise ValueError("review-006 accepted-E trajectory does not intersect ribcage")
    discriminant = max(0.0, discriminant)
    roots = (
        (-qb - math.sqrt(discriminant)) / (2.0 * qa),
        (-qb + math.sqrt(discriminant)) / (2.0 * qa),
    )
    candidates = [value for value in roots if -1e-9 <= value <= 1.0 + 1e-9]
    if not candidates:
        raise ValueError("review-006 trajectory intersection lies outside segment")
    t = max(candidates)
    point = _add(inside, _mul(direction, t))
    if abs(_ellipsoid_implicit(point, mass) - 1.0) > 1e-8:
        raise ValueError("clipped seam sample is not on ribcage")
    return point, t


def _radial_project_to_ellipsoid(point, mass):
    center = tuple(float(value) for value in mass["center"])
    radii = tuple(float(value) for value in mass["radii"])
    direction = _sub(point, center)
    denominator = sum((direction[i] / radii[i]) ** 2 for i in range(3))
    if denominator <= 1e-12:
        raise ValueError("cannot radially project ribcage center")
    projected = _add(center, _mul(direction, 1.0 / math.sqrt(denominator)))
    if abs(_ellipsoid_implicit(projected, mass) - 1.0) > 1e-8:
        raise ValueError("inferior closure projection is not on ribcage")
    return projected


def _boundary_loop(faces):
    oriented = defaultdict(list)
    counts = defaultdict(int)
    for face in faces:
        if len(face) != 3 or len(set(face)) != 3:
            raise ValueError("proof face must be one non-collapsed triangle")
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = tuple(sorted((start, end)))
            counts[edge] += 1
            oriented[edge].append((start, end))
    boundary = [oriented[edge][0] for edge, count in counts.items() if count == 1]
    if not boundary:
        raise ValueError("expected one opening boundary")
    successor = {}
    predecessor_count = defaultdict(int)
    for start, end in boundary:
        if start in successor:
            raise ValueError("opening has branching boundary")
        successor[start] = end
        predecessor_count[end] += 1
    if any(predecessor_count[vertex] != 1 for vertex in successor):
        raise ValueError("opening boundary is not one oriented loop")
    start = min(successor)
    loop = [start]
    current = start
    while True:
        nxt = successor[current]
        if nxt == start:
            break
        if nxt in loop:
            raise ValueError("opening closes early")
        loop.append(nxt)
        current = nxt
        if len(loop) > len(boundary):
            raise ValueError("opening boundary walk overflow")
    if len(loop) != len(boundary):
        raise ValueError("opening contains more than one loop")
    return loop


def _stitch_loops(loop_a, loop_b):
    if len(loop_a) < 3 or len(loop_b) < 3:
        raise ValueError("stitch loops must contain at least three vertices")
    faces = []
    i = j = 0
    count_a, count_b = len(loop_a), len(loop_b)
    while i < count_a or j < count_b:
        next_a = (i + 1) / count_a if i < count_a else math.inf
        next_b = (j + 1) / count_b if j < count_b else math.inf
        a, b = loop_a[i % count_a], loop_b[j % count_b]
        if abs(next_a - next_b) <= 1e-12:
            a_next = loop_a[(i + 1) % count_a]
            b_next = loop_b[(j + 1) % count_b]
            faces.extend(([a, a_next, b], [a_next, b_next, b]))
            i += 1
            j += 1
        elif next_a < next_b:
            a_next = loop_a[(i + 1) % count_a]
            faces.append([a, a_next, b])
            i += 1
        else:
            b_next = loop_b[(j + 1) % count_b]
            faces.append([a, b_next, b])
            j += 1
    return faces


def _compact_unused_vertices(positions, faces):
    """Prune topology-edit leftovers without moving any retained position."""
    used = sorted({vertex for face in faces for vertex in face})
    if not used:
        raise ValueError("cannot compact an empty surface")
    mapping = {old: new for new, old in enumerate(used)}
    compact_positions = [list(positions[old]) for old in used]
    compact_faces = [[mapping[vertex] for vertex in face] for face in faces]
    removed = sorted(set(range(len(positions))) - set(used))
    return compact_positions, compact_faces, removed


def _inspect_vertex_fans(faces):
    """Detect disconnected triangle fans around one indexed vertex (bow-ties)."""
    incident = defaultdict(list)
    for face_index, face in enumerate(faces):
        for vertex in face:
            incident[vertex].append(face_index)
    disconnected = []
    for vertex, members in incident.items():
        members = set(members)
        adjacency = {face_index: set() for face_index in members}
        edge_neighbors = defaultdict(list)
        for face_index in members:
            face = faces[face_index]
            local = [item for item in face if item != vertex]
            if len(local) != 2:
                raise ValueError("vertex fan inspection requires non-collapsed triangles")
            for other in local:
                edge_neighbors[tuple(sorted((vertex, other)))].append(face_index)
        for uses in edge_neighbors.values():
            for left in uses:
                for right in uses:
                    if left != right:
                        adjacency[left].add(right)
        remaining = set(members)
        components = 0
        while remaining:
            components += 1
            stack = [remaining.pop()]
            while stack:
                current = stack.pop()
                for neighbor in adjacency[current]:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        stack.append(neighbor)
        if components != 1:
            disconnected.append({"vertex": vertex, "fan_components": components})
    return disconnected


def _inspect_indexed_surface(positions, faces):
    edge_faces = defaultdict(list)
    collapsed = []
    used_vertices = set()
    for triangle_index, face in enumerate(faces):
        if len(face) != 3 or min(face) < 0 or max(face) >= len(positions):
            raise ValueError("invalid candidate face index")
        used_vertices.update(face)
        if len(set(face)) != 3 or _triangle_area(positions, face) <= 1e-12:
            collapsed.append(triangle_index)
            continue
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = tuple(sorted((start, end)))
            direction = 1 if (start, end) == edge else -1
            edge_faces[edge].append((triangle_index, direction))
    boundary = [edge for edge, incidents in edge_faces.items() if len(incidents) == 1]
    nonmanifold = [edge for edge, incidents in edge_faces.items() if len(incidents) > 2]
    conflicts = [
        edge for edge, incidents in edge_faces.items()
        if len(incidents) == 2 and incidents[0][1] == incidents[1][1]
    ]
    collapsed_set = set(collapsed)
    valid_faces = [index for index in range(len(faces)) if index not in collapsed_set]
    adjacency = {index: set() for index in valid_faces}
    for incidents in edge_faces.values():
        members = sorted({triangle for triangle, _direction in incidents})
        if len(members) > 1:
            anchor = members[0]
            for other in members[1:]:
                adjacency[anchor].add(other)
                adjacency[other].add(anchor)
    remaining = set(valid_faces)
    components = 0
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    disconnected_fans = _inspect_vertex_fans(faces) if not collapsed else []
    isolated = sorted(set(range(len(positions))) - used_vertices)
    status = (
        "PASS_CHARACTER_REVIEW006_CLOSED_ORIENTED_SINGLE_COMPONENT_VERTEX_MANIFOLD_CANDIDATE"
        if (
            not collapsed
            and not boundary
            and not nonmanifold
            and not conflicts
            and components == 1
            and not disconnected_fans
            and not isolated
        )
        else "FAIL_CHARACTER_REVIEW006_SURFACE_PREFLIGHT"
    )
    return {
        "status": status,
        "vertex_count": len(positions),
        "triangle_count": len(faces),
        "collapsed_triangle_count": len(collapsed),
        "boundary_edge_count": len(boundary),
        "nonmanifold_edge_count": len(nonmanifold),
        "orientation_conflict_edge_count": len(conflicts),
        "triangle_component_count": components,
        "disconnected_vertex_fan_count": len(disconnected_fans),
        "isolated_vertex_count": len(isolated),
        "disconnected_vertex_fan_examples": disconnected_fans[:8],
    }


def _source_context():
    source = shoulder_pose_clearance_refinement_candidate()
    if source.get("study_id") != REVIEW006_ID:
        raise ValueError("review-006 source ID drift")
    source_digest = canonical_digest(source)
    if source_digest != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 exact source digest drift")
    proof_mesh = build_adopted_character_mesh(source)
    mesh_digest = canonical_digest(proof_mesh)
    if mesh_digest != EXPECTED_REVIEW006_MESH_DIGEST:
        raise ValueError("review-006 exact proof-mesh digest drift")
    masses = {item["id"]: item for item in source["masses"]}
    segments = {item["id"]: item for item in source["segments"]}
    bridges = {item["id"]: item for item in source["shoulder_transition_regions"]}
    repair = source["shoulder_transition_repair"]
    if repair["root_ring_indices"] != list(ROOT_RING_INDICES):
        raise ValueError("accepted-E root-ring selection drift inside review-006")
    if repair["blend_weights"] != list(BLEND_WEIGHTS):
        raise ValueError("accepted-E blend-weight drift inside review-006")
    if repair["target_axis_scale"] != list(TARGET_AXIS_SCALE):
        raise ValueError("accepted-E target-axis-scale drift inside review-006")
    return source, masses["ribcage"], segments, bridges, proof_mesh


def _accepted_e_samples(side, source, segments, bridges):
    segment = segments[f"upper_arm_{side}"]
    bridge = bridges[f"shoulder_bridge_{side}"]
    shoulder = source["landmarks"][segment["a"]]
    elbow = source["landmarks"][segment["b"]]
    segment_vertices, _ = _segment_mesh(
        shoulder, elbow, float(segment["radius_a"]), float(segment["radius_b"]), sides=10
    )
    root_ring = [tuple(point) for point in segment_vertices[:10]]
    accepted_proximal = {}
    sx, sy, sz = (float(value) for value in TARGET_AXIS_SCALE)
    for index, weight in zip(ROOT_RING_INDICES, BLEND_WEIGHTS):
        point = root_ring[index]
        radial = _sub(point, shoulder)
        target = (
            float(bridge["anchor"][0]) + radial[0] * sx,
            float(bridge["anchor"][1]) + radial[1] * sy,
            float(bridge["anchor"][2]) + radial[2] * sz,
        )
        accepted_proximal[index] = tuple(
            point[axis] + float(weight) * (target[axis] - point[axis]) for axis in range(3)
        )
    return root_ring, accepted_proximal


def _seam_ring(side, source, ribcage, segments, bridges):
    root_ring, accepted_proximal = _accepted_e_samples(side, source, segments, bridges)
    seam, provenance = [], []
    for index, root in enumerate(root_ring):
        if index in _SELECTED_WEIGHT:
            proximal = accepted_proximal[index]
            point, t = _line_to_ellipsoid_surface(proximal, root, ribcage)
            provenance.append({
                "root_ring_index": index,
                "kind": "REVIEW006_ACCEPTED_E_TRAJECTORY_CLIPPED_AT_RIBCAGE",
                "segment_t_from_E_proximal_to_root": t,
                "review006_E_proximal": list(proximal),
                "review006_source_root_sample": list(root),
                "ribcage_implicit": _ellipsoid_implicit(point, ribcage),
            })
        else:
            point = _radial_project_to_ellipsoid(root, ribcage)
            provenance.append({
                "root_ring_index": index,
                "kind": "TOPOLOGY_ONLY_INFERIOR_CLOSURE_FROM_REVIEW006_SOURCE_ROOT",
                "review006_source_root_sample": list(root),
                "ribcage_implicit": _ellipsoid_implicit(point, ribcage),
            })
        seam.append(point)
    if {row["root_ring_index"] for row in provenance if "TRAJECTORY" in row["kind"]} != set(_SELECTED):
        raise ValueError("review-006 accepted-E seam coverage drift")
    inferior = tuple(row["root_ring_index"] for row in provenance if "INFERIOR" in row["kind"])
    if inferior != _INFERIOR_CLOSURE:
        raise ValueError("review-006 inferior closure coverage drift")
    return seam, provenance


def _source_arm_ring(side, source, segments, sample_t):
    segment = segments[f"upper_arm_{side}"]
    shoulder = tuple(float(value) for value in source["landmarks"][segment["a"]])
    elbow = tuple(float(value) for value in source["landmarks"][segment["b"]])
    source_vertices, _ = _segment_mesh(
        shoulder, elbow, float(segment["radius_a"]), float(segment["radius_b"]), sides=10
    )
    source_root = [tuple(point) for point in source_vertices[:10]]
    center = tuple(
        shoulder[axis] + float(sample_t) * (elbow[axis] - shoulder[axis]) for axis in range(3)
    )
    radius = float(segment["radius_a"]) + float(sample_t) * (
        float(segment["radius_b"]) - float(segment["radius_a"])
    )
    return [
        _add(center, _mul(_unit(_sub(point, shoulder), "upper-arm radial direction"), radius))
        for point in source_root
    ]


def _rotate(values, phase):
    values = list(values)
    if not values:
        raise ValueError("cannot rotate empty loop")
    phase = int(phase) % len(values)
    return values[phase:] + values[:phase]


def _group_faces(specimen, group_name):
    return [
        list(face)
        for face, group in zip(specimen["faces"], specimen["groups"])
        if group == group_name
    ]


def build_connected_baseline(side):
    source, ribcage, segments, bridges, _proof_mesh = _source_context()
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    rib_vertices, rib_faces = _ellipsoid_mesh(ribcage["center"], ribcage["radii"])
    removed = set(_RIBCAGE_HOLE_FACE_IDS[side])
    remaining_rib_faces = [list(face) for index, face in enumerate(rib_faces) if index not in removed]
    hole = _boundary_loop(remaining_rib_faces)
    if len(hole) != 10:
        raise ValueError("review-006 shoulder opening must expose exactly ten boundary vertices")
    hole = _rotate(hole, _RIBCAGE_HOLE_PHASE[side])

    seam_ring, seam_provenance = _seam_ring(side, source, ribcage, segments, bridges)
    proximal_ring = _source_arm_ring(side, source, segments, _PROXIMAL_SAMPLE_T)
    segment = segments[f"upper_arm_{side}"]
    shoulder, elbow = source["landmarks"][segment["a"]], source["landmarks"][segment["b"]]
    source_arm_vertices, _ = _segment_mesh(
        shoulder, elbow, float(segment["radius_a"]), float(segment["radius_b"]), sides=10
    )
    distal_ring = [tuple(point) for point in source_arm_vertices[10:20]]
    distal_center = tuple(source_arm_vertices[21])

    positions = [tuple(point) for point in rib_vertices]
    seam_start = len(positions)
    positions.extend(seam_ring)
    proximal_start = len(positions)
    positions.extend(proximal_ring)
    distal_start = len(positions)
    positions.extend(distal_ring)
    distal_center_index = len(positions)
    positions.append(distal_center)

    seam_indices = list(range(seam_start, seam_start + 10))
    proximal_indices = list(range(proximal_start, proximal_start + 10))
    distal_indices = list(range(distal_start, distal_start + 10))
    rib_to_seam = _stitch_loops(list(reversed(hole)), seam_indices)
    seam_to_proximal = _stitch_loops(seam_indices, proximal_indices)
    proximal_to_distal = _stitch_loops(proximal_indices, distal_indices)
    distal_cap = [
        [distal_center_index, distal_indices[index], distal_indices[(index + 1) % 10]]
        for index in range(10)
    ]
    faces = remaining_rib_faces + rib_to_seam + seam_to_proximal + proximal_to_distal + distal_cap
    groups = (
        ["ribcage"] * len(remaining_rib_faces)
        + ["ribcage_to_seam"] * len(rib_to_seam)
        + ["seam_to_proximal"] * len(seam_to_proximal)
        + ["proximal_to_distal"] * len(proximal_to_distal)
        + ["distal_cap"] * len(distal_cap)
    )
    positions = [[round(value, 12) for value in point] for point in positions]
    local = _inspect_indexed_surface(positions, faces)
    if not local["status"].startswith("PASS_"):
        raise ValueError("review-006 connected baseline failed structural preflight")
    if len(positions) != 93 or len(faces) != 182:
        raise ValueError("review-006 connected baseline budget drift")
    return {
        "stage": "connected_baseline",
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [value for face in faces for value in face],
        "groups": groups,
        "local_preflight": local,
        "construction": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "ribcage_hole_phase": _RIBCAGE_HOLE_PHASE[side],
            "proximal_arm_sample_t": _PROXIMAL_SAMPLE_T,
            "seam_provenance": seam_provenance,
            "positions_moved_from_review006_derivation": False,
        },
    }


def build_opening_repair(side):
    base = build_connected_baseline(side)
    rib_faces = _group_faces(base, "ribcage")
    old_outer = _group_faces(base, "ribcage_to_seam")
    if len(rib_faces) != 112 or len(old_outer) != 20:
        raise ValueError("review-006 connected baseline ribcage/stitch topology drift")
    extra = set(_EXTRA_RIBCAGE_FACE_INDICES[side])
    remaining_rib = [face for index, face in enumerate(rib_faces) if index not in extra]
    hole = _rotate(_boundary_loop(remaining_rib), _EXPANDED_HOLE_PHASE[side])
    if len(hole) != 12:
        raise ValueError("review-006 expanded opening must expose twelve boundary vertices")

    base_rib_vertices = {vertex for face in rib_faces for vertex in face}
    outer_vertices = {vertex for face in old_outer for vertex in face}
    seam = sorted(outer_vertices - base_rib_vertices)
    if len(seam) != 10:
        raise ValueError("review-006 outer stitch must expose ten seam vertices")
    seam = _rotate(seam, _SEAM_PHASE[side])
    repaired_outer = _stitch_loops(list(reversed(hole)), seam)
    if len(repaired_outer) != 22:
        raise ValueError("review-006 12-to-10 stitch must contain twenty-two triangles")

    downstream = [
        (list(face), group)
        for face, group in zip(base["faces"], base["groups"])
        if group not in ("ribcage", "ribcage_to_seam")
    ]
    faces = remaining_rib + repaired_outer + [face for face, _group in downstream]
    groups = (
        ["ribcage"] * len(remaining_rib)
        + ["ribcage_to_seam"] * len(repaired_outer)
        + [group for _face, group in downstream]
    )
    positions, faces, removed_unused_vertices = _compact_unused_vertices(base["positions"], faces)
    local = _inspect_indexed_surface(positions, faces)
    if not local["status"].startswith("PASS_"):
        raise ValueError(f"review-006 opening repair failed structural preflight: {local}")
    if len(positions) != 92 or len(faces) != 180 or len(removed_unused_vertices) != 1:
        raise ValueError("review-006 opening repair compacted budget drift")
    return {
        "stage": "opening_repair",
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [value for face in faces for value in face],
        "groups": groups,
        "local_preflight": local,
        "construction": {
            "historical_pattern": "EXPANDED_12_TO_10_OPENING_RESTITCH",
            "historical_scores_inherited": False,
            "extra_removed_ribcage_group_face_indices": list(_EXTRA_RIBCAGE_FACE_INDICES[side]),
            "expanded_hole_phase": _EXPANDED_HOLE_PHASE[side],
            "positions_moved": False,
            "unused_vertex_prune": {
                "removed_original_vertex_indices": removed_unused_vertices,
                "removed_count": len(removed_unused_vertices),
                "policy": "PRUNE_TOPOLOGY_EDIT_LEFTOVER_BEFORE_MANIFOLD_CLAIM",
            },
        },
    }


def _group_face_indexes(specimen, group_name):
    indexes = [index for index, group in enumerate(specimen["groups"]) if group == group_name]
    if not indexes or indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        raise ValueError(f"face group must remain nonempty and contiguous: {group_name}")
    return indexes


def _retessellate_quad(specimen, quad_index):
    indexes = _group_face_indexes(specimen, "proximal_to_distal")
    if len(indexes) != 20 or not (0 <= quad_index < 10):
        raise ValueError("review-006 proximal-to-distal strip contract drift")
    first_index = indexes[quad_index * 2]
    second_index = indexes[quad_index * 2 + 1]
    first = list(specimen["faces"][first_index])
    second = list(specimen["faces"][second_index])
    a, a_next, b = first
    if second[0] != a_next or second[2] != b:
        raise ValueError("review-006 strip pairing contract drift")
    b_next = second[1]
    if len({a, a_next, b, b_next}) != 4:
        raise ValueError("review-006 strip quad must contain four vertices")
    faces = [list(face) for face in specimen["faces"]]
    faces[first_index] = [a, a_next, b_next]
    faces[second_index] = [a, b_next, b]
    return faces


def build_diagonal_repair(side):
    base = build_opening_repair(side)
    faces = _retessellate_quad(base, DIAGONAL_QUAD_INDEX)
    positions = deepcopy(base["positions"])
    local = _inspect_indexed_surface(positions, faces)
    if not local["status"].startswith("PASS_"):
        raise ValueError("review-006 diagonal replay failed structural preflight")
    return {
        "stage": "diagonal_repair",
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [value for face in faces for value in face],
        "groups": list(base["groups"]),
        "local_preflight": local,
        "construction": {
            "historical_pattern": "PROXIMAL_TO_DISTAL_QUAD_1_DIAGONAL_FLIP",
            "historical_scores_inherited": False,
            "positions_moved": False,
        },
    }


def _directed_edges(face):
    return tuple(zip(face, face[1:] + face[:1]))


def _edge_uses(faces):
    uses = {}
    for face_index, face in enumerate(faces):
        for start, end in _directed_edges(face):
            uses.setdefault(tuple(sorted((start, end))), []).append((face_index, (start, end)))
    return uses


def _flip_face_pair(faces, pair):
    first_index, second_index = sorted(pair)
    first = tuple(faces[first_index])
    second = tuple(faces[second_index])
    shared = set(first).intersection(second)
    if len(shared) != 2:
        raise ValueError("stitch face pair must share exactly one edge")
    uses = _edge_uses(faces)
    shared_key = tuple(sorted(shared))
    shared_uses = uses.get(shared_key, [])
    if len(shared_uses) != 2 or {row[0] for row in shared_uses} != {first_index, second_index}:
        raise ValueError("stitch shared edge incidence drift")
    oriented = next(((a, b) for a, b in _directed_edges(first) if {a, b} == shared), None)
    if oriented is None:
        raise ValueError("first stitch face lost shared edge")
    u, v = oriented
    if (v, u) not in _directed_edges(second):
        raise ValueError("stitch faces lost opposite edge orientation")
    a = next(vertex for vertex in first if vertex not in shared)
    b = next(vertex for vertex in second if vertex not in shared)
    if len({a, b, u, v}) != 4:
        raise ValueError("stitch edge flip requires four distinct vertices")
    if uses.get(tuple(sorted((a, b)))):
        raise ValueError("replacement stitch diagonal already exists")
    output = [list(face) for face in faces]
    output[first_index] = [a, u, b]
    output[second_index] = [a, b, v]
    return output


def build_stitch_repair(side):
    base = build_diagonal_repair(side)
    faces = [list(face) for face in base["faces"]]
    for pair in STITCH_FACE_PAIRS:
        if any(base["groups"][index] != "ribcage_to_seam" for index in pair):
            raise ValueError("historical stitch pair left review-006 ribcage_to_seam group")
        faces = _flip_face_pair(faces, pair)
    positions = deepcopy(base["positions"])
    local = _inspect_indexed_surface(positions, faces)
    if not local["status"].startswith("PASS_"):
        raise ValueError("review-006 stitch replay failed structural preflight")
    changed = [
        index for index, (before, after) in enumerate(zip(base["faces"], faces))
        if list(before) != list(after)
    ]
    if changed != [111, 112, 114, 115]:
        raise ValueError("review-006 stitch replay changed unexpected face records")
    return {
        "stage": "stitch_repair",
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [value for face in faces for value in face],
        "groups": list(base["groups"]),
        "local_preflight": local,
        "construction": {
            "historical_pattern": "TWO_NONOVERLAPPING_RIBCAGE_TO_SEAM_EDGE_FLIPS",
            "historical_scores_inherited": False,
            "face_pairs": [list(pair) for pair in STITCH_FACE_PAIRS],
            "changed_face_indexes": changed,
            "positions_moved": False,
        },
    }


def build_stage(side, stage):
    builders = {
        "connected_baseline": build_connected_baseline,
        "opening_repair": build_opening_repair,
        "diagonal_repair": build_diagonal_repair,
        "stitch_repair": build_stitch_repair,
    }
    try:
        builder = builders[stage]
    except KeyError as exc:
        raise ValueError(f"unknown stage: {stage}") from exc
    return builder(side)


def _mirrored_position_set(specimen):
    return {
        (round(-float(p[0]), 9), round(float(p[1]), 9), round(float(p[2]), 9))
        for p in specimen["positions"]
    }


def _position_set(specimen):
    return {
        (round(float(p[0]), 9), round(float(p[1]), 9), round(float(p[2]), 9))
        for p in specimen["positions"]
    }


def audit_review006_geometry_rebind():
    source, _ribcage, _segments, _bridges, proof_mesh = _source_context()
    source_before = canonical_digest(source)
    mesh_before = canonical_digest(proof_mesh)

    stage_rows = []
    stage_specimens = {}
    for stage in STAGES:
        stage_specimens[stage] = {}
        for side in ("L", "R"):
            specimen = build_stage(side, stage)
            stage_specimens[stage][side] = specimen
            report = inspect_triangle_self_intersections(
                specimen["positions"], specimen["indices"], max_examples=32
            )
            stage_rows.append({
                "stage": stage,
                "side": side,
                "vertex_count": len(specimen["positions"]),
                "triangle_count": len(specimen["faces"]),
                "topology_digest": canonical_digest({
                    "positions": specimen["positions"], "faces": specimen["faces"]
                }),
                "local_preflight": specimen["local_preflight"],
                "neutral_nonadjacent_intersection": report,
            })
        left = stage_specimens[stage]["L"]
        right = stage_specimens[stage]["R"]
        if _mirrored_position_set(left) != _position_set(right):
            raise ValueError(f"review-006 {stage} lost bilateral mirrored position sets")

    summaries = []
    for stage in STAGES:
        rows = [row for row in stage_rows if row["stage"] == stage]
        counts = {
            row["side"]: int(row["neutral_nonadjacent_intersection"]["self_intersection_pair_count"])
            for row in rows
        }
        if counts["L"] != counts["R"]:
            raise ValueError(f"review-006 {stage} neutral intersection counts lost bilateral equality")
        summaries.append({
            "stage": stage,
            "vertex_count_per_side": rows[0]["vertex_count"],
            "triangle_count_per_side": rows[0]["triangle_count"],
            "neutral_pairs_L": counts["L"],
            "neutral_pairs_R": counts["R"],
            "neutral_pairs_total": counts["L"] + counts["R"],
        })

    rank = {stage: index for index, stage in enumerate(STAGES)}
    selected_summary = min(
        summaries,
        key=lambda row: (
            row["neutral_pairs_total"],
            row["triangle_count_per_side"],
            rank[row["stage"]],
        ),
    )
    selected_stage = selected_summary["stage"]
    selected = stage_specimens[selected_stage]

    if canonical_digest(source) != source_before or canonical_digest(proof_mesh) != mesh_before:
        raise ValueError("derived Geometry rebind mutated review-006 source/proof identity")

    selected_intersection_free = selected_summary["neutral_pairs_total"] == 0
    verdict = (
        "PASS_REVIEW006_NEUTRAL_CONNECTED_RECEIVER_NO_NONADJACENT_INTERSECTIONS"
        if selected_intersection_free
        else "HOLD_REVIEW006_NEUTRAL_CONNECTED_RECEIVER_NONZERO_INTERSECTIONS"
    )
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "verdict": verdict,
        "exact_identity": {
            "organic_head": ORGANIC_HEAD,
            "review006_id": REVIEW006_ID,
            "review006_source_digest": source_before,
            "review006_proof_mesh_digest": mesh_before,
            "review006_proof_vertex_count": len(proof_mesh["vertices"]),
            "review006_proof_triangle_count": len(proof_mesh["faces"]),
            "art_direction": ART_DIRECTION,
            "visual_qa": VISUAL_QA,
        },
        "historical_precedent": HISTORICAL_GEOMETRY_PRECEDENT,
        "rebind_policy": (
            "RECONSTRUCT_EACH_KNOWN_TOPOLOGY_PATTERN_FROM_EXACT_REVIEW006_SOURCE__"
            "RETEST_STRUCTURE_AND_NEUTRAL_INTERSECTIONS__NO_HISTORICAL_SCORE_TRANSFER"
        ),
        "stage_summaries": summaries,
        "stage_rows": stage_rows,
        "selection": {
            "selected_stage": selected_stage,
            "criterion": "MIN_NEUTRAL_NONADJACENT_INTERSECTIONS__THEN_FEWER_TRIANGLES__THEN_EARLIER_STAGE",
            "selected_summary": selected_summary,
            "left_topology_digest": canonical_digest({
                "positions": selected["L"]["positions"], "faces": selected["L"]["faces"]
            }),
            "right_topology_digest": canonical_digest({
                "positions": selected["R"]["positions"], "faces": selected["R"]["faces"]
            }),
            "neutral_intersection_free": selected_intersection_free,
        },
        "gates": {
            "exact_review006_source_identity": "PASS",
            "exact_review006_proof_mesh_identity": "PASS",
            "art_direction_selection_observed": "PASS",
            "independent_visual_QA_selection_observed": "PASS",
            "old_geometry_result_transfer": "FORBIDDEN_AND_NOT_PERFORMED",
            "all_four_patterns_reconstructed_from_review006": "PASS",
            "all_four_patterns_closed_oriented_single_component": "PASS",
            "all_four_patterns_vertex_fan_manifold_candidate": "PASS",
            "opening_and_successor_unused_vertex_prune": "PASS_ONE_DERIVED_LEFTOVER_PER_SIDE_REMOVED",
            "all_four_patterns_bilateral_position_mirror": "PASS",
            "neutral_nonadjacent_self_intersection_observed": "PASS",
            "continuous_deformation": "NOT_EVALUATED",
            "rigging_rebind": "PENDING_EXACT_SELECTED_GEOMETRY_RECEIVER",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoffs": {
            "rigging": (
                f"Bind only the exact selected review-006 Geometry receiver stage '{selected_stage}' and its "
                "retained topology digests; rebuild deformation evidence from scratch. No accepted-E Rigging PASS transfers."
            ),
            "organic_form": (
                "Review-006 source/proof identity was not rewritten. Keep the form frozen unless Geometry/Rigging "
                "returns a concrete source-owned defect."
            ),
            "art_direction_visual_QA": (
                "Geometry selected only by structural neutral evidence. No visual preference is inferred; inspect "
                "the exact selected receiver if downstream deformation exposes a visible issue."
            ),
            "geometry": (
                "Do not resume accepted-E edge-flip searches by cadence. Any further topology repair must bind "
                "the exact review-006 selected receiver and a new measured defect."
            ),
        },
        "truth_boundary": [
            "Review-006 is a selected review input, not an adopted CANON source successor.",
            "The four topology stages reuse historical Character-local construction patterns only; every stage is rebuilt from the exact review-006 source and remeasured.",
            "The expanded-opening topology leaves one now-unreferenced derived ribcage vertex per side; Geometry prunes that index-only leftover before claiming manifold-candidate structure, without moving any retained position.",
            "Neutral nonadjacent-triangle intersection evidence is static finite evidence; it is not continuous deformation, adjacent-face fold/contact, collision, or gameplay proof.",
            "The proof mesh remains separate source-form evidence; this connected receiver is derived Geometry evidence and does not silently replace Organic ownership.",
            "No anatomy, final normals/tangents/UVs, material quality, Rigging/Animation acceptance, runtime performance, CANON, production readiness, game readiness, or Geometry mastery is claimed.",
        ],
    }


def build_review006_geometry_rebind_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_geometry_rebind()
    (out / "review006-connected-geometry-rebind-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    selected_stage = audit["selection"]["selected_stage"]
    for side in ("L", "R"):
        specimen = build_stage(side, selected_stage)
        (out / f"review006-connected-{side.lower()}-{selected_stage}.mesh.json").write_text(
            json.dumps(
                {"positions": specimen["positions"], "faces": specimen["faces"]},
                separators=(",", ":"),
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        write_obj(
            {"vertices": specimen["positions"], "faces": specimen["faces"], "regions": []},
            out / f"review006-connected-{side.lower()}-{selected_stage}.obj",
        )
    return audit
