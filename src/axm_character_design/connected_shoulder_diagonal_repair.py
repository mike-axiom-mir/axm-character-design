"""Geometry-owned same-position diagonal search over the repaired Character shoulder.

This module consumes the exact opening-repair topology from Geometry PR #7 and
asks one deliberately smaller question: can diagonal choice inside the existing
10-quad proximal-to-distal arm strip reduce the remaining sampled nonadjacent
self-intersections without moving a vertex, changing source form, or changing
mesh budget?

The search is bounded to the 2^10 legal per-quad diagonal choices in that one
strip.  It is not a generic remesher and it does not imply intersection freedom.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from .connected_shoulder_deformation import audit_connected_shoulder_deformation
from .connected_shoulder_intersection_repair import (
    STATUS as OPENING_REPAIR_STATUS,
    audit_opening_repair,
    build_opening_repair_specimen,
)
from .organic_form import canonical_digest, write_obj
from .self_intersection import (
    _aabb,
    _aabb_overlap,
    _triangles_intersect,
    inspect_triangle_self_intersections,
)
from .shoulder_connected_topology import _inspect_indexed_surface

SCHEMA = "axm.character-connected-shoulder-diagonal-repair/v0.1"
STATUS = (
    "PASS_CHARACTER_CONNECTED_SHOULDER_SINGLE_QUAD_DIAGONAL_REDUCTION"
    "__HOLD_NONZERO_INTERSECTIONS"
)
OPENING_REPAIR_HEAD = "8cc4a180cd1481d680841190b0038b4b330133ae"
RIGGING_REBIND_HEAD = "ef73f87e0ebe4ce101b2fe25a92441ada7837b83"
GROUP = "proximal_to_distal"
QUAD_COUNT = 10
MASK_COUNT = 1 << QUAD_COUNT
SELECTED_MASK = 1 << 1
EXPECTED_BASE_COUNTS = (-40.0, 9), (0.0, 9), (40.0, 11)
EXPECTED_SELECTED_COUNTS = (-40.0, 8), (0.0, 8), (40.0, 10)


def _group_face_indexes(specimen, group_name: str) -> list[int]:
    indexes = [index for index, group in enumerate(specimen["groups"]) if group == group_name]
    if not indexes:
        raise ValueError(f"missing face group: {group_name}")
    if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        raise ValueError(f"face group must remain contiguous: {group_name}")
    return indexes


def _retessellated_strip_faces(base, mask: int) -> tuple[list[list[int]], list[int]]:
    if type(mask) is not int or mask < 0 or mask >= MASK_COUNT:
        raise ValueError(f"mask must be an integer in [0,{MASK_COUNT - 1}]")
    strip_indexes = _group_face_indexes(base, GROUP)
    if len(strip_indexes) != QUAD_COUNT * 2:
        raise ValueError("exact repaired proximal-to-distal strip must contain twenty triangles")

    output: list[list[int]] = []
    for quad in range(QUAD_COUNT):
        first = list(base["faces"][strip_indexes[quad * 2]])
        second = list(base["faces"][strip_indexes[quad * 2 + 1]])
        if len(first) != 3 or len(second) != 3:
            raise ValueError("strip face must remain triangular")
        a, a_next, b = first
        if second[0] != a_next or second[2] != b:
            raise ValueError("proximal-to-distal strip pairing contract drift")
        b_next = second[1]
        if len({a, a_next, b, b_next}) != 4:
            raise ValueError("proximal-to-distal quad must contain four distinct vertices")
        if mask & (1 << quad):
            output.extend(([a, a_next, b_next], [a, b_next, b]))
        else:
            output.extend((first, second))
    return output, strip_indexes


def build_diagonal_mask_specimen(side: str, mask: int = SELECTED_MASK) -> dict:
    base = build_opening_repair_specimen(side)
    strip, strip_indexes = _retessellated_strip_faces(base, mask)
    faces = [list(face) for face in base["faces"]]
    faces[strip_indexes[0]: strip_indexes[-1] + 1] = strip
    positions = [list(point) for point in base["positions"]]
    local = _inspect_indexed_surface(positions, faces)
    if local["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
        raise ValueError("diagonal candidate failed Character-local topology preflight")
    if len(positions) != 93 or len(faces) != 180:
        raise ValueError("diagonal candidate changed exact vertex/triangle budget")

    return {
        "schema": SCHEMA,
        "id": f"character-connected-shoulder-{side.lower()}-diagonal-mask-{mask:03x}",
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [index for face in faces for index in face],
        "groups": list(base["groups"]),
        "local_preflight": local,
        "construction": {
            "opening_repair_head": OPENING_REPAIR_HEAD,
            "mask": mask,
            "flipped_quad_indices": [quad for quad in range(QUAD_COUNT) if mask & (1 << quad)],
            "searched_group": GROUP,
            "positions_moved": False,
            "vertex_count": len(positions),
            "triangle_count": len(faces),
        },
        "topology_digest": canonical_digest({"positions": positions, "faces": faces}),
    }


def _count_changed_group_intersections(positions, faces, changed_indexes: set[int]) -> int:
    """Count exact observer intersections when unchanged/unchanged is already proven zero.

    The geometric predicate is the same Character-local predicate used by the full
    self-intersection observer.  This helper only avoids re-testing pairs whose two
    triangles are byte-identical across every mask in the bounded search.
    """
    triangles = [tuple(tuple(float(value) for value in positions[index]) for index in face) for face in faces]
    boxes = [_aabb(triangle) for triangle in triangles]
    count = 0
    for left in range(len(triangles)):
        left_vertices = set(faces[left])
        for right in range(left + 1, len(triangles)):
            if left not in changed_indexes and right not in changed_indexes:
                continue
            if left_vertices.intersection(faces[right]):
                continue
            if not _aabb_overlap(boxes[left], boxes[right], 1e-9):
                continue
            if _triangles_intersect(triangles[left], triangles[right], 1e-9):
                count += 1
    return count


def _exact_anchor_poses():
    rigging = audit_connected_shoulder_deformation()
    poses = {}
    for side in ("L", "R"):
        rows = rigging["results"][side]["candidate"]
        poses[side] = {float(row["angle_deg"]): row["positions"] for row in rows}
        if sorted(poses[side]) != [-40.0, 0.0, 40.0]:
            raise ValueError("exact retained shoulder anchor pose set drift")
    return rigging, poses


def _full_counts(specimens, poses):
    rows = []
    total = 0
    for side in ("L", "R"):
        for angle in (-40.0, 0.0, 40.0):
            report = inspect_triangle_self_intersections(
                poses[side][angle], specimens[side]["indices"], max_examples=64
            )
            count = int(report["self_intersection_pair_count"])
            total += count
            rows.append({
                "side": side,
                "angle_deg": angle,
                "intersection_pair_count": count,
                "examples": report["examples"],
            })
    return total, rows


def audit_selected_diagonal_repair() -> dict:
    opening = audit_opening_repair()
    if opening["status"] != OPENING_REPAIR_STATUS:
        raise ValueError("exact opening-repair prerequisite is not green")
    if opening["sampled_intersection_comparison"]["candidate_total_pairs"] != 58:
        raise ValueError("opening-repair 58-pair baseline drift")

    rigging, poses = _exact_anchor_poses()
    baseline = {side: build_opening_repair_specimen(side) for side in ("L", "R")}
    candidate = {side: build_diagonal_mask_specimen(side, SELECTED_MASK) for side in ("L", "R")}
    for side in ("L", "R"):
        if candidate[side]["positions"] != baseline[side]["positions"]:
            raise ValueError("single-quad diagonal repair moved vertex positions")
        if candidate[side]["groups"] != baseline[side]["groups"]:
            raise ValueError("single-quad diagonal repair changed face-group identity")
        if len(candidate[side]["faces"]) != len(baseline[side]["faces"]):
            raise ValueError("single-quad diagonal repair changed triangle budget")
        if candidate[side]["construction"]["flipped_quad_indices"] != [1]:
            raise ValueError("selected repair must flip exactly proximal-to-distal quad 1")

    baseline_total, baseline_rows = _full_counts(baseline, poses)
    candidate_total, candidate_rows = _full_counts(candidate, poses)
    if baseline_total != 58 or candidate_total != 52:
        raise ValueError("selected diagonal repair aggregate intersection count drift")
    expected_base = dict(EXPECTED_BASE_COUNTS)
    expected_candidate = dict(EXPECTED_SELECTED_COUNTS)
    for row in baseline_rows:
        if row["intersection_pair_count"] != expected_base[row["angle_deg"]]:
            raise ValueError("baseline per-pose intersection count drift")
    for row in candidate_rows:
        if row["intersection_pair_count"] != expected_candidate[row["angle_deg"]]:
            raise ValueError("candidate per-pose intersection count drift")
    for before, after in zip(baseline_rows, candidate_rows):
        if before["side"] != after["side"] or before["angle_deg"] != after["angle_deg"]:
            raise ValueError("before/after pose ordering drift")
        if after["intersection_pair_count"] >= before["intersection_pair_count"]:
            raise ValueError("selected diagonal repair must strictly reduce every retained pose")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "producer_dependencies": {
            "opening_repair_head": OPENING_REPAIR_HEAD,
            "opening_repair_status": opening["status"],
            "rigging_anchor_head": opening["producer_dependencies"]["rigging_head"],
            "latest_known_explicit_rigging_rebind_head": RIGGING_REBIND_HEAD,
            "rig_plan_digest": rigging["rig_plan_digest"],
        },
        "candidate": {
            "selected_mask": SELECTED_MASK,
            "flipped_quad_indices": [1],
            "searched_group": GROUP,
            "positions_identical": True,
            "vertex_count_per_side": 93,
            "triangle_count_per_side": 180,
            "left_topology_digest": candidate["L"]["topology_digest"],
            "right_topology_digest": candidate["R"]["topology_digest"],
            "left_local_preflight": candidate["L"]["local_preflight"],
            "right_local_preflight": candidate["R"]["local_preflight"],
        },
        "sampled_intersection_comparison": {
            "baseline_total_pairs": baseline_total,
            "candidate_total_pairs": candidate_total,
            "reduction_pair_count": baseline_total - candidate_total,
            "reduction_fraction": (baseline_total - candidate_total) / baseline_total,
            "baseline_rows": baseline_rows,
            "candidate_rows": candidate_rows,
            "all_six_samples_strictly_reduced": True,
            "all_candidate_samples_still_nonzero": True,
        },
        "gates": {
            "exact_opening_repair_identity": "PASS",
            "same_position_topology_only": "PASS",
            "same_vertex_triangle_budget": "PASS",
            "closed_oriented_single_component_local_preflight": "PASS",
            "strict_reduction_all_six_anchor_poses": "PASS",
            "intersection_free": "HOLD_NONZERO_INTERSECTIONS_REMAIN",
            "rigging_rebind_for_this_topology": "NOT_PERFORMED",
            "visual_acceptance": "NOT_CLAIMED",
            "runtime_or_gameplay": "NOT_CLAIMED",
        },
        "handoffs": {
            "geometry": "Retain this one-quad candidate as the minimum-change winner of the bounded strip-diagonal family; 52 sampled pairs remain, so stronger topology work still needs a distinct rollbackable identity.",
            "rigging": "PR #8 is truthful for Geometry PR #7 only. Do not transfer it to this new topology identity; explicitly rebind/rerun if this candidate is selected.",
            "visual_observer_art_direction": "Lower sampled intersection count is not seam/silhouette/deformation acceptance. Compare the exact successor directly if it advances.",
            "organic_form": "No source/seam/arm positions moved. Return to Organic Form only if later evidence shows a stronger repair requires source-form movement rather than another derived topology candidate.",
        },
        "truth_boundary": [
            "This result changes exactly one diagonal in the existing proximal-to-distal 10-quad strip and moves no vertex.",
            "The retained -40/0/+40 anchor samples remain finite evidence only; continuous deformation and topological-neighbour fold-over/contact are outside this observer.",
            "Fifty-two sampled nonadjacent triangle-pair intersections remain across the six exact anchor poses, so no self-intersection-free or collision-safe claim is made.",
            "No anatomy, final normals/tangents/UVs, Rigging acceptance for this successor, visual quality, Animation, runtime, collision/gameplay, CANON, production readiness, game readiness or Geometry mastery is established.",
        ],
    }


def search_bounded_strip_diagonals() -> dict:
    """Exhaust all 1,024 same-position diagonal masks in the existing strip."""
    opening = audit_opening_repair()
    if opening["status"] != OPENING_REPAIR_STATUS:
        raise ValueError("opening-repair prerequisite is not green")
    _rigging, poses = _exact_anchor_poses()
    baseline = {side: build_opening_repair_specimen(side) for side in ("L", "R")}

    changed = {}
    for side in ("L", "R"):
        changed[side] = set(_group_face_indexes(baseline[side], GROUP))
        for angle in (-40.0, 0.0, 40.0):
            report = inspect_triangle_self_intersections(
                poses[side][angle], baseline[side]["indices"], max_examples=64
            )
            if len(report["examples"]) != report["self_intersection_pair_count"]:
                raise ValueError("baseline observer examples must retain every current pair")
            if any(
                row["triangle_a"] not in changed[side] and row["triangle_b"] not in changed[side]
                for row in report["examples"]
            ):
                raise ValueError("bounded diagonal search invalid: baseline has unchanged/unchanged intersections")

    rows = []
    distribution = Counter()
    for mask in range(MASK_COUNT):
        counts = []
        for side in ("L", "R"):
            specimen = build_diagonal_mask_specimen(side, mask)
            for angle in (-40.0, 0.0, 40.0):
                counts.append(_count_changed_group_intersections(
                    poses[side][angle], specimen["faces"], changed[side]
                ))
        row = {
            "mask": mask,
            "mask_bits_low_quad_first": [1 if mask & (1 << quad) else 0 for quad in range(QUAD_COUNT)],
            "flipped_quad_indices": [quad for quad in range(QUAD_COUNT) if mask & (1 << quad)],
            "counts_L_m40_0_p40_R_m40_0_p40": counts,
            "maximum_pair_count": max(counts),
            "total_pair_count": sum(counts),
            "flip_count": mask.bit_count(),
        }
        rows.append(row)
        distribution[(row["maximum_pair_count"], row["total_pair_count"])] += 1

    rows.sort(key=lambda row: (
        row["maximum_pair_count"],
        row["total_pair_count"],
        row["flip_count"],
        row["mask"],
    ))
    winner = rows[0]
    if winner["mask"] != SELECTED_MASK or winner["flipped_quad_indices"] != [1]:
        raise ValueError(f"bounded diagonal search winner drift: {winner}")
    expected_distribution = {(10, 52): 256, (11, 58): 512, (12, 64): 256}
    if dict(distribution) != expected_distribution:
        raise ValueError(f"bounded diagonal search distribution drift: {dict(distribution)}")

    selected = {side: build_diagonal_mask_specimen(side, SELECTED_MASK) for side in ("L", "R")}
    selected_total, selected_rows = _full_counts(selected, poses)
    if selected_total != winner["total_pair_count"]:
        raise ValueError("optimized search count does not reproduce full observer on selected mask")

    return {
        "schema": SCHEMA,
        "status": "PASS_EXHAUSTIVE_1024_MASK_SAME_POSITION_STRIP_DIAGONAL_SEARCH",
        "family": {
            "group": GROUP,
            "quad_count": QUAD_COUNT,
            "mask_count": MASK_COUNT,
            "positions_moved": False,
            "vertex_triangle_budget_changed": False,
        },
        "winner": winner,
        "full_observer_selected_rows": selected_rows,
        "score_distribution": [
            {"maximum_pair_count": key[0], "total_pair_count": key[1], "mask_count": count}
            for key, count in sorted(distribution.items())
        ],
        "all_masks_local_preflight_pass": True,
        "truth_boundary": "This exhausts only the ten independent diagonal choices of the existing proximal-to-distal strip. It does not exhaust arbitrary topology, vertex movement, source-form changes, or continuous deformation.",
    }


def build_diagonal_repair_evidence(out_dir: Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_selected_diagonal_repair()
    search = search_bounded_strip_diagonals()
    (out / "connected-shoulder-diagonal-repair-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "connected-shoulder-diagonal-search.json").write_text(
        json.dumps(search, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _rigging, poses = _exact_anchor_poses()
    for side in ("L", "R"):
        candidate = build_diagonal_mask_specimen(side, SELECTED_MASK)
        (out / f"connected-shoulder-{side.lower()}-diagonal-repair.mesh.json").write_text(
            json.dumps({"positions": candidate["positions"], "faces": candidate["faces"]}, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for angle in (-40.0, 0.0, 40.0):
            label = f"p{int(angle)}" if angle >= 0 else f"m{abs(int(angle))}"
            write_obj(
                {"vertices": poses[side][angle], "faces": candidate["faces"], "regions": []},
                out / f"connected-shoulder-{side.lower()}-{label}-diagonal-repair.obj",
            )
    return audit
