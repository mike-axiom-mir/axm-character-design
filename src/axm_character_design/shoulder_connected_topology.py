from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
import math
from pathlib import Path

from .organic_form import _ellipsoid_mesh, _segment_mesh, canonical_digest, write_obj
from .shoulder_source_lineage import (
    SOURCE_ID,
    adopted_character_source,
    build_adopted_character_mesh,
)
from .shoulder_transition_feathered import (
    BLEND_WEIGHTS,
    ROOT_RING_INDICES,
    TARGET_AXIS_SCALE,
)

SCHEMA = "axm.character-connected-shoulder-topology/v0.1"
STATUS = "PASS_CHARACTER_E_CLIPPED_CONNECTED_SHOULDER_TOPOLOGY_WITH_PHASE_REPAIR"

EXPECTED_SOURCE_ID = "character-neutral-a-shoulder-source-004"
EXPECTED_ADOPTED_SOURCE_DIGEST = "dbb20e6e7dc1874b3b22553d0407791f05699f23ebb42c4e249a259f56613f1d"
EXPECTED_ADOPTED_MESH_DIGEST = "30a4612212f2e8252b6f813912ce76c655763e6d3abb4650c04ad1af72baea7f"

UC_DONOR = {
    "repository": "mike-axiom-mir/axm-universal-creation",
    "commit": "dde8d952161788f8bf21118f91edd3163e51277d",
    "path": "src/axm_uc/mesh_topology.py",
    "license": "Apache-2.0",
    "use": "generic seam-welded edge-topology observer only",
}
ANIMAL_METHOD_PRECEDENT = {
    "repository": "mike-axiom-mir/axm-animal-design",
    "pr": 4,
    "head": "feb4b24cd36bcc879173138d240754f71db34834",
    "use": "shared-ring / phase-aware connected-chain evidence precedent only; no geometry or PASS inherited",
}

# Accepted E leaves root-ring samples 2/3 deliberately open/inferior. Geometry
# keeps that semantic distinction: the other eight seam samples are clipped from
# exact accepted-E trajectories at the ribcage shell; 2/3 receive explicit
# topology-only closure derived from the exact source root ring.
_SELECTED = tuple(ROOT_RING_INDICES)
_SELECTED_WEIGHT = dict(zip(_SELECTED, BLEND_WEIGHTS))
_INFERIOR_CLOSURE = tuple(index for index in range(10) if index not in _SELECTED)

# Exact current low-resolution ribcage proof tessellation only. Four adjacent
# quads / eight triangles are removed per side, yielding one ten-vertex hole.
# This is Character-local proof topology, not a reusable ellipsoid convention.
_RIBCAGE_HOLE_FACE_IDS = {
    "L": (20, 21, 22, 23, 24, 25, 26, 27),
    "R": (32, 33, 34, 35, 12, 13, 14, 15),
}

# Mirrored phase choice from direct same-position comparison. Phase zero remains
# the retained control: it is closed too, but makes a much sharper/skinnier seam.
_RIBCAGE_HOLE_PHASE = {"L": 5, "R": 3}
_PROXIMAL_SAMPLE_T = 0.06


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


def _face_normal(positions, face):
    a, b, c = (positions[index] for index in face)
    return _unit(_cross(_sub(b, a), _sub(c, a)), "triangle normal")


def _ellipsoid_implicit(point, mass):
    return sum(
        ((float(point[i]) - float(mass["center"][i])) / float(mass["radii"][i])) ** 2
        for i in range(3)
    )


def _line_to_ellipsoid_surface(inside, outside, mass):
    """Intersect one accepted-E inside->outside trajectory with the source shell."""
    if _ellipsoid_implicit(inside, mass) > 1.0 + 1e-8:
        raise ValueError("expected accepted-E proximal sample inside/on ribcage")
    if _ellipsoid_implicit(outside, mass) < 1.0 - 1e-8:
        raise ValueError("expected selected upper-arm root sample outside/on ribcage")
    center = tuple(float(value) for value in mass["center"])
    radii = tuple(float(value) for value in mass["radii"])
    direction = _sub(outside, inside)
    offset = _sub(inside, center)
    qa = sum((direction[i] / radii[i]) ** 2 for i in range(3))
    qb = 2.0 * sum(offset[i] * direction[i] / (radii[i] ** 2) for i in range(3))
    qc = sum((offset[i] / radii[i]) ** 2 for i in range(3)) - 1.0
    discriminant = qb * qb - 4.0 * qa * qc
    if discriminant < -1e-12:
        raise ValueError("accepted-E trajectory does not intersect ribcage")
    discriminant = max(0.0, discriminant)
    roots = (
        (-qb - math.sqrt(discriminant)) / (2.0 * qa),
        (-qb + math.sqrt(discriminant)) / (2.0 * qa),
    )
    candidates = [value for value in roots if -1e-9 <= value <= 1.0 + 1e-9]
    if not candidates:
        raise ValueError("accepted-E trajectory intersection lies outside segment")
    t = max(candidates)
    point = _add(inside, _mul(direction, t))
    if abs(_ellipsoid_implicit(point, mass) - 1.0) > 1e-8:
        raise ValueError("accepted-E clipped seam sample is not on ribcage")
    return point, t


def _radial_project_to_ellipsoid(point, mass):
    """Project an omitted inferior source-root sample to the shell for closure only."""
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
            raise ValueError("ribcage proof face must be one non-collapsed triangle")
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge = tuple(sorted((start, end)))
            counts[edge] += 1
            oriented[edge].append((start, end))
    boundary = [oriented[edge][0] for edge, count in counts.items() if count == 1]
    if not boundary:
        raise ValueError("expected one ribcage opening boundary")
    successor = {}
    predecessor_count = defaultdict(int)
    for start, end in boundary:
        if start in successor:
            raise ValueError("ribcage opening has branching boundary")
        successor[start] = end
        predecessor_count[end] += 1
    if any(predecessor_count[vertex] != 1 for vertex in successor):
        raise ValueError("ribcage opening boundary is not one oriented loop")
    start = min(successor)
    loop = [start]
    current = start
    while True:
        nxt = successor[current]
        if nxt == start:
            break
        if nxt in loop:
            raise ValueError("ribcage opening closes early")
        loop.append(nxt)
        current = nxt
        if len(loop) > len(boundary):
            raise ValueError("ribcage opening boundary walk overflow")
    if len(loop) != len(boundary):
        raise ValueError("ribcage opening contains more than one loop")
    return loop


def _stitch_loops(loop_a, loop_b):
    """Deterministically zip two oriented closed loops without moving vertices."""
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


def _inspect_indexed_surface(positions, faces):
    """Character-local preflight; retained generic authority comes from pinned UC."""
    edge_faces = defaultdict(list)
    collapsed = []
    for triangle_index, face in enumerate(faces):
        if len(face) != 3 or min(face) < 0 or max(face) >= len(positions):
            raise ValueError("invalid candidate face index")
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
    status = (
        "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT"
        if not collapsed and not boundary and not nonmanifold and not conflicts and components == 1
        else "FAIL_CHARACTER_LOCAL_SURFACE_PREFLIGHT"
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
    }


def _max_normal_turn(positions, faces, groups, group_a, group_b):
    edge_faces = defaultdict(list)
    for face_index, face in enumerate(faces):
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge_faces[tuple(sorted((start, end)))].append(face_index)
    turns = []
    for incidents in edge_faces.values():
        if len(incidents) != 2 or {groups[index] for index in incidents} != {group_a, group_b}:
            continue
        first = _face_normal(positions, faces[incidents[0]])
        second = _face_normal(positions, faces[incidents[1]])
        cosine = max(-1.0, min(1.0, _dot(first, second)))
        turns.append(math.degrees(math.acos(cosine)))
    if not turns:
        raise ValueError(f"no seam edges found for {group_a} / {group_b}")
    return max(turns)


def _area_summary(positions, faces):
    values = sorted(_triangle_area(positions, face) for face in faces)
    if not values or values[0] <= 1e-12:
        raise ValueError("stitch contains collapsed triangle")
    midpoint = len(values) // 2
    median = values[midpoint] if len(values) % 2 else (values[midpoint - 1] + values[midpoint]) * 0.5
    return {
        "minimum_m2": values[0],
        "median_m2": median,
        "minimum_over_median": values[0] / median,
    }


def _source_context():
    source = adopted_character_source()
    if SOURCE_ID != EXPECTED_SOURCE_ID or source.get("study_id") != EXPECTED_SOURCE_ID:
        raise ValueError("adopted Character source ID drift")
    if canonical_digest(source) != EXPECTED_ADOPTED_SOURCE_DIGEST:
        raise ValueError("adopted Character source digest drift")
    adopted_mesh = build_adopted_character_mesh(source)
    if canonical_digest(adopted_mesh) != EXPECTED_ADOPTED_MESH_DIGEST:
        raise ValueError("adopted Character proof-mesh digest drift")
    masses = {item["id"]: item for item in source["masses"]}
    segments = {item["id"]: item for item in source["segments"]}
    bridges = {item["id"]: item for item in source["shoulder_transition_regions"]}
    if "ribcage" not in masses:
        raise ValueError("adopted Character ribcage missing")
    repair = source["shoulder_transition_repair"]
    if repair["root_ring_indices"] != list(ROOT_RING_INDICES):
        raise ValueError("accepted E root-ring selection drift")
    if repair["blend_weights"] != list(BLEND_WEIGHTS):
        raise ValueError("accepted E blend-weight drift")
    if repair["target_axis_scale"] != list(TARGET_AXIS_SCALE):
        raise ValueError("accepted E target-axis-scale drift")
    return source, masses["ribcage"], segments, bridges


def _accepted_e_samples(side, source, segments, bridges):
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
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
            seam.append(point)
            provenance.append({
                "root_ring_index": index,
                "kind": "ACCEPTED_E_TRAJECTORY_CLIPPED_AT_RIBCAGE",
                "segment_t_from_E_proximal_to_root": t,
                "accepted_E_proximal": list(proximal),
                "source_root_sample": list(root),
                "ribcage_implicit": _ellipsoid_implicit(point, ribcage),
            })
        else:
            point = _radial_project_to_ellipsoid(root, ribcage)
            seam.append(point)
            provenance.append({
                "root_ring_index": index,
                "kind": "TOPOLOGY_ONLY_INFERIOR_CLOSURE_FROM_SOURCE_ROOT_RADIAL_PROJECTION",
                "source_root_sample": list(root),
                "ribcage_implicit": _ellipsoid_implicit(point, ribcage),
            })
    accepted_indices = {
        item["root_ring_index"] for item in provenance if item["kind"].startswith("ACCEPTED_E")
    }
    inferior_indices = tuple(
        item["root_ring_index"] for item in provenance if "INFERIOR" in item["kind"]
    )
    if accepted_indices != set(_SELECTED):
        raise ValueError("accepted E seam coverage drift")
    if inferior_indices != _INFERIOR_CLOSURE:
        raise ValueError("inferior closure coverage drift")
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


def build_connected_shoulder_specimen(side, *, hole_phase=None):
    source, ribcage, segments, bridges = _source_context()
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    phase = _RIBCAGE_HOLE_PHASE[side] if hole_phase is None else int(hole_phase)

    rib_vertices, rib_faces = _ellipsoid_mesh(ribcage["center"], ribcage["radii"])
    removed = set(_RIBCAGE_HOLE_FACE_IDS[side])
    if max(removed) >= len(rib_faces):
        raise ValueError("Character ribcage tessellation drifted beyond pinned local face IDs")
    remaining_rib_faces = [list(face) for index, face in enumerate(rib_faces) if index not in removed]
    hole = _boundary_loop(remaining_rib_faces)
    if len(hole) != 10:
        raise ValueError("Character shoulder opening must expose exactly ten boundary vertices")
    phase %= len(hole)
    hole = hole[phase:] + hole[:phase]

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
    local = _inspect_indexed_surface(positions, faces)
    if local["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
        raise ValueError("connected shoulder candidate failed Character-local topology preflight")
    seam_turns = {
        "ribcage_to_seam_max_normal_turn_deg": _max_normal_turn(
            positions, faces, groups, "ribcage", "ribcage_to_seam"
        ),
        "seam_to_proximal_max_normal_turn_deg": _max_normal_turn(
            positions, faces, groups, "ribcage_to_seam", "seam_to_proximal"
        ),
        "proximal_to_distal_max_normal_turn_deg": _max_normal_turn(
            positions, faces, groups, "seam_to_proximal", "proximal_to_distal"
        ),
        "distal_cap_max_normal_turn_deg": _max_normal_turn(
            positions, faces, groups, "proximal_to_distal", "distal_cap"
        ),
    }
    area = {
        "ribcage_to_seam": _area_summary(positions, rib_to_seam),
        "seam_to_proximal": _area_summary(positions, seam_to_proximal),
        "proximal_to_distal": _area_summary(positions, proximal_to_distal),
    }
    return {
        "schema": SCHEMA,
        "id": f"character-connected-shoulder-{side.lower()}-001",
        "side": side,
        "positions": [[round(value, 12) for value in point] for point in positions],
        "faces": faces,
        "indices": [value for face in faces for value in face],
        "groups": groups,
        "source": {
            "source_id": source["study_id"],
            "source_digest": EXPECTED_ADOPTED_SOURCE_DIGEST,
            "source_mesh_digest": EXPECTED_ADOPTED_MESH_DIGEST,
            "upper_arm_region": segment["id"],
            "ribcage_region": ribcage["id"],
        },
        "construction": {
            "removed_ribcage_face_ids": list(_RIBCAGE_HOLE_FACE_IDS[side]),
            "ribcage_hole_phase": phase,
            "proximal_arm_sample_t": _PROXIMAL_SAMPLE_T,
            "accepted_E_selected_root_ring_indices": list(ROOT_RING_INDICES),
            "accepted_E_open_inferior_root_ring_indices": list(_INFERIOR_CLOSURE),
            "seam_provenance": seam_provenance,
            "policy": "CLIP_ACCEPTED_E_TRAJECTORIES_AT_SOURCE_RIBCAGE__CLOSE_ONLY_INFERIOR_OPEN_SECTOR__PHASE_REPAIR_TRIANGULATION_WITHOUT_SOURCE_EDIT",
        },
        "local_preflight": local,
        "local_shape_diagnostics": {
            "seam_normal_turns": seam_turns,
            "stitch_triangle_areas": area,
            "status": "MEASURED_NOT_VISUAL_OR_DEFORMATION_ACCEPTANCE",
        },
        "truth_boundary": {
            "source_rewritten": False,
            "accepted_E_source_identity_pinned": True,
            "selected_E_trajectory_samples_preserved_as_clipping_guides": True,
            "inferior_closure_is_topology_only": True,
            "connected_closed_indexed_surface_preflight": True,
            "generic_UC_topology_acceptance": False,
            "self_intersection_checked": False,
            "vertex_manifoldness_beyond_indexed_edge_preflight_checked": False,
            "normals_tangents_authored": False,
            "deformation_checked": False,
            "visual_acceptance": False,
            "runtime_acceptance": False,
            "gameplay_acceptance": False,
        },
    }


def _mirrored_position_set(specimen):
    return {
        (round(-float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in specimen["positions"]
    }


def _position_set(specimen):
    return {
        (round(float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in specimen["positions"]
    }


def audit_connected_shoulders(*, topology_inspector=None):
    source, _, _, _ = _source_context()
    left = build_connected_shoulder_specimen("L")
    right = build_connected_shoulder_specimen("R")
    if _mirrored_position_set(left) != _position_set(right):
        raise ValueError("connected shoulder position sets lost bilateral mirror symmetry")

    control_left = build_connected_shoulder_specimen("L", hole_phase=0)
    control_right = build_connected_shoulder_specimen("R", hole_phase=0)
    def outer_turn(specimen):
        return specimen["local_shape_diagnostics"]["seam_normal_turns"]["ribcage_to_seam_max_normal_turn_deg"]
    def outer_area(specimen):
        return specimen["local_shape_diagnostics"]["stitch_triangle_areas"]["ribcage_to_seam"]["minimum_over_median"]
    if not outer_turn(left) < outer_turn(control_left) or not outer_turn(right) < outer_turn(control_right):
        raise ValueError("selected ring phase did not reduce outer seam normal turn")
    if not outer_area(left) > outer_area(control_left) or not outer_area(right) > outer_area(control_right):
        raise ValueError("selected ring phase did not improve local stitch triangle area ratio")

    uc = {}
    if topology_inspector is not None:
        for side, specimen in (("L", left), ("R", right)):
            result = topology_inspector(specimen["positions"], specimen["indices"], weld_tolerance=1e-6)
            if result["status"] != "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE":
                raise ValueError(f"UC topology observer rejected connected shoulder {side}")
            required_zero = (
                "boundary_edge_count", "nonmanifold_edge_count",
                "orientation_conflict_edge_count", "collapsed_triangle_count",
            )
            if any(result[key] != 0 for key in required_zero):
                raise ValueError(f"UC topology observer found structural defect: {side}")
            if result["triangle_component_count"] != 1:
                raise ValueError(f"UC topology observer found disconnected surface: {side}")
            uc[side] = result
        corrupted = deepcopy(left)
        corrupted["faces"][0] = [
            corrupted["faces"][0][0], corrupted["faces"][0][2], corrupted["faces"][0][1]
        ]
        corrupted["indices"] = [value for face in corrupted["faces"] for value in face]
        negative = topology_inspector(corrupted["positions"], corrupted["indices"], weld_tolerance=1e-6)
        if negative["status"] == "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE":
            raise ValueError("UC topology negative control failed open")
        uc["negative_single_triangle_winding_flip"] = negative

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "source_id": source["study_id"],
        "adopted_source_digest": EXPECTED_ADOPTED_SOURCE_DIGEST,
        "adopted_mesh_digest": EXPECTED_ADOPTED_MESH_DIGEST,
        "uc_donor": UC_DONOR,
        "animal_method_precedent": ANIMAL_METHOD_PRECEDENT,
        "candidate": {
            "left_digest": canonical_digest({"positions": left["positions"], "faces": left["faces"]}),
            "right_digest": canonical_digest({"positions": right["positions"], "faces": right["faces"]}),
            "left": {
                "vertex_count": len(left["positions"]), "triangle_count": len(left["faces"]),
                "local_preflight": left["local_preflight"],
                "shape_diagnostics": left["local_shape_diagnostics"],
                "ribcage_hole_phase": left["construction"]["ribcage_hole_phase"],
            },
            "right": {
                "vertex_count": len(right["positions"]), "triangle_count": len(right["faces"]),
                "local_preflight": right["local_preflight"],
                "shape_diagnostics": right["local_shape_diagnostics"],
                "ribcage_hole_phase": right["construction"]["ribcage_hole_phase"],
            },
            "bilateral_mirrored_position_sets": True,
        },
        "phase_control": {
            "left": {
                "chosen_phase": left["construction"]["ribcage_hole_phase"], "control_phase": 0,
                "chosen_outer_seam_max_normal_turn_deg": outer_turn(left),
                "control_outer_seam_max_normal_turn_deg": outer_turn(control_left),
                "chosen_outer_stitch_min_over_median_area": outer_area(left),
                "control_outer_stitch_min_over_median_area": outer_area(control_left),
            },
            "right": {
                "chosen_phase": right["construction"]["ribcage_hole_phase"], "control_phase": 0,
                "chosen_outer_seam_max_normal_turn_deg": outer_turn(right),
                "control_outer_seam_max_normal_turn_deg": outer_turn(control_right),
                "chosen_outer_stitch_min_over_median_area": outer_area(right),
                "control_outer_stitch_min_over_median_area": outer_area(control_right),
            },
            "interpretation": "same exact seam/arm positions and closed topology; only loop correspondence changes, proving phase selection prevents a structurally legal but locally pinched stitch",
        },
        "uc_topology": uc or {
            "status": "NOT_RUN_IN_LOCAL_UNIT_PREFLIGHT",
            "retained_evidence_requires_pinned_donor": True,
        },
        "gates": {
            "adopted_character_source_identity_pinned": "PASS",
            "accepted_E_selected_trajectory_semantics_used": "PASS",
            "inferior_open_sector_closure_declared_topology_only": "PASS",
            "bilateral_position_mirror": "PASS",
            "left_character_local_closed_oriented_single_component": "PASS",
            "right_character_local_closed_oriented_single_component": "PASS",
            "phase_repair_reduces_outer_seam_normal_turn": "PASS",
            "phase_repair_improves_outer_stitch_area_ratio": "PASS",
            "pinned_UC_edge_topology": "PASS" if topology_inspector is not None else "NOT_RUN",
            "self_intersection": "NOT_CLAIMED",
            "deformation": "NOT_CLAIMED",
            "visual_tangent_or_pinch_acceptance": "NOT_CLAIMED",
            "rigging": "NOT_CLAIMED",
            "runtime": "NOT_CLAIMED",
            "gameplay": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "derived Character-local connected shoulder topology specimens only; adopted Organic source bytes and accepted E proof mesh are not rewritten",
            "eight seam samples are clipped from exact accepted-E proximal-to-root trajectories at the exact source ribcage ellipsoid; the two omitted inferior E samples receive explicit topology-only source-root radial closure points",
            "ring-phase repair is selected by direct same-position comparison against phase-zero control; topology PASS alone is not treated as proof of good local triangulation",
            "the measured seam normal-turn and triangle-area diagnostics are specimen-local evidence, not universal aesthetic or deformation thresholds",
            "pinned UC edge topology does not prove vertex manifoldness, self-intersection freedom, authored normals/tangents, deformation quality, visual quality, runtime behavior, collision/gameplay suitability, CANON, production readiness, game readiness, or Geometry mastery",
        ],
    }


def build_connected_shoulder_evidence(out_dir, *, topology_inspector):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    left = build_connected_shoulder_specimen("L")
    right = build_connected_shoulder_specimen("R")
    receipt = audit_connected_shoulders(topology_inspector=topology_inspector)
    for side, specimen in (("L", left), ("R", right)):
        prefix = f"connected-shoulder-{side.lower()}"
        (out / f"{prefix}.mesh.json").write_text(
            json.dumps({"positions": specimen["positions"], "faces": specimen["faces"]}, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_obj(
            {"vertices": specimen["positions"], "faces": specimen["faces"], "regions": []},
            out / f"{prefix}.obj",
        )
        (out / f"{prefix}.construction.json").write_text(
            json.dumps({
                "id": specimen["id"], "side": side, "source": specimen["source"],
                "construction": specimen["construction"], "local_preflight": specimen["local_preflight"],
                "local_shape_diagnostics": specimen["local_shape_diagnostics"],
                "truth_boundary": specimen["truth_boundary"],
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (out / "connected-shoulder-topology-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
