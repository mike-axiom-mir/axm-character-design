"""Geometry-owned stitch-edge retessellation over the current Character shoulder.

This module consumes the exact Geometry PR #9 diagonal-repair topology and the
exact Rigging PR #10 rebound pose field. It changes no vertex position, source
form, seam sample, arm sample, rig weight, joint, or pose. The bounded question
is whether local edge choice inside the existing ribcage-to-seam stitch can
reduce the remaining sampled nonadjacent self-intersections.

The selection procedure is intentionally small and auditable:
1. exhaust every legal *single* internal edge flip in the exact 22-triangle
   ribcage-to-seam stitch at the retained -40/0/+40 anchors;
2. retain only the two mirrored face-pair locations that strictly improve that
   bounded single-flip search;
3. apply those two non-overlapping flips together and re-observe the exact
   162-pose Rigging PR #10 one-degree sweep.

This is not a generic remesher and it does not imply intersection freedom.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from .connected_shoulder_diagonal_repair import (
    SELECTED_MASK,
    STATUS as DIAGONAL_REPAIR_STATUS,
    audit_selected_diagonal_repair,
    build_diagonal_mask_specimen,
)
from .connected_shoulder_diagonal_rigging_rebind import (
    ANCHOR_ANGLES_DEG,
    REPRESENTATIVE_ANGLES_DEG,
    STATUS as RIGGING_REBIND_STATUS,
    audit_diagonal_repair_rigging_rebind,
)
from .organic_form import canonical_digest, write_obj
from .self_intersection import inspect_triangle_self_intersections
from .shoulder_connected_topology import _inspect_indexed_surface

SCHEMA = "axm.character-connected-shoulder-stitch-edge-repair/v0.1"
STATUS = (
    "PASS_CHARACTER_CONNECTED_SHOULDER_TWO_STITCH_EDGE_DENSE_SWEEP_REDUCTION"
    "__HOLD_NONZERO_INTERSECTIONS"
)

DIAGONAL_REPAIR_HEAD = "fa69eea233a56dc7e09b22c62a9e37bfa97bc994"
RIGGING_REBIND_HEAD = "e5b129ba936f252946f48921be5a3096d8c2f801"
TARGET_GROUP = "ribcage_to_seam"
TARGET_FACE_PAIRS = ((111, 112), (114, 115))
EXPECTED_SINGLE_SEARCH_DISTRIBUTION = {48: 2, 52: 17, 54: 2, 64: 1}
EXPECTED_ANCHOR_BASE_COUNTS = {
    "L": {-40.0: 8, 0.0: 8, 40.0: 10},
    "R": {-40.0: 8, 0.0: 8, 40.0: 10},
}
EXPECTED_ANCHOR_CANDIDATE_COUNTS = {
    "L": {-40.0: 6, 0.0: 6, 40.0: 10},
    "R": {-40.0: 6, 0.0: 6, 40.0: 10},
}


def _directed_edges(face):
    return tuple(zip(face, face[1:] + face[:1]))


def _edge_uses(faces):
    uses = {}
    for face_index, face in enumerate(faces):
        for start, end in _directed_edges(face):
            key = tuple(sorted((start, end)))
            uses.setdefault(key, []).append((face_index, (start, end)))
    return uses


def _flip_face_pair(faces, pair):
    """Flip the unique shared diagonal between one exact adjacent face pair."""
    if (
        not isinstance(pair, (tuple, list))
        or len(pair) != 2
        or any(type(value) is not int for value in pair)
        or pair[0] == pair[1]
    ):
        raise ValueError("pair must contain two distinct integer face indexes")
    first_index, second_index = sorted(pair)
    if first_index < 0 or second_index >= len(faces):
        raise ValueError("face pair is out of range")

    first = tuple(faces[first_index])
    second = tuple(faces[second_index])
    shared = set(first).intersection(second)
    if len(shared) != 2:
        raise ValueError("face pair must share exactly one indexed edge")

    shared_key = tuple(sorted(shared))
    uses = _edge_uses(faces)
    shared_uses = uses.get(shared_key, [])
    if {row[0] for row in shared_uses} != {first_index, second_index} or len(shared_uses) != 2:
        raise ValueError("shared edge must be used by exactly the selected two faces")

    oriented = None
    for start, end in _directed_edges(first):
        if {start, end} == shared:
            oriented = (start, end)
            break
    if oriented is None:
        raise ValueError("selected first face does not contain the shared edge")
    u, v = oriented
    if (v, u) not in _directed_edges(second):
        raise ValueError("selected pair does not have opposite shared-edge orientation")

    a = next(vertex for vertex in first if vertex not in shared)
    b = next(vertex for vertex in second if vertex not in shared)
    if len({a, b, u, v}) != 4:
        raise ValueError("edge flip requires four distinct quad vertices")

    replacement_key = tuple(sorted((a, b)))
    replacement_uses = uses.get(replacement_key, [])
    if replacement_uses:
        raise ValueError("replacement diagonal already exists in the mesh")

    output = [list(face) for face in faces]
    output[first_index] = [a, u, b]
    output[second_index] = [a, b, v]
    return output, {
        "face_pair": [first_index, second_index],
        "old_diagonal": list(shared_key),
        "new_diagonal": list(replacement_key),
    }


def _single_flip_candidates(base):
    target_indexes = [
        index for index, group in enumerate(base["groups"]) if group == TARGET_GROUP
    ]
    if target_indexes != list(range(108, 130)):
        raise ValueError("exact ribcage-to-seam face-group index range drift")

    candidates = []
    for edge, uses in sorted(_edge_uses(base["faces"]).items()):
        face_indexes = sorted(row[0] for row in uses)
        if len(face_indexes) != 2 or any(index not in target_indexes for index in face_indexes):
            continue
        try:
            _faces, change = _flip_face_pair(base["faces"], face_indexes)
        except ValueError:
            continue
        candidates.append(
            {
                "face_pair": tuple(change["face_pair"]),
                "old_diagonal": tuple(change["old_diagonal"]),
                "new_diagonal": tuple(change["new_diagonal"]),
            }
        )
    if len(candidates) != 22:
        raise ValueError("exact stitch must expose twenty-two legal internal single-edge flips")
    return candidates


def build_single_stitch_edge_specimen(side: str, pair) -> dict:
    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    if any(base["groups"][index] != TARGET_GROUP for index in pair):
        raise ValueError("selected face pair must stay inside ribcage_to_seam")
    faces, change = _flip_face_pair(base["faces"], pair)
    positions = [list(point) for point in base["positions"]]
    local = _inspect_indexed_surface(positions, faces)
    if local["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
        raise ValueError("single stitch-edge flip failed Character-local topology preflight")
    return {
        "schema": SCHEMA,
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [index for face in faces for index in face],
        "groups": list(base["groups"]),
        "local_preflight": local,
        "change": change,
    }


def build_stitch_edge_repair_specimen(side: str) -> dict:
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    faces = [list(face) for face in base["faces"]]
    changes = []
    for pair in TARGET_FACE_PAIRS:
        if any(base["groups"][index] != TARGET_GROUP for index in pair):
            raise ValueError("selected face pair left the exact ribcage_to_seam group")
        faces, change = _flip_face_pair(faces, pair)
        changes.append(change)

    positions = [list(point) for point in base["positions"]]
    local = _inspect_indexed_surface(positions, faces)
    if local["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
        raise ValueError("two-edge stitch repair failed Character-local topology preflight")
    if len(positions) != 93 or len(faces) != 180:
        raise ValueError("two-edge stitch repair changed exact vertex/triangle budget")

    changed_face_indexes = [
        index for index, (before, after) in enumerate(zip(base["faces"], faces))
        if list(before) != list(after)
    ]
    if changed_face_indexes != [111, 112, 114, 115]:
        raise ValueError("two-edge stitch repair changed unexpected face records")

    return {
        "schema": SCHEMA,
        "id": f"character-connected-shoulder-{side.lower()}-stitch-edge-repair-001",
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [index for face in faces for index in face],
        "groups": list(base["groups"]),
        "local_preflight": local,
        "construction": {
            "diagonal_repair_head": DIAGONAL_REPAIR_HEAD,
            "rigging_rebind_head": RIGGING_REBIND_HEAD,
            "target_group": TARGET_GROUP,
            "target_face_pairs": [list(pair) for pair in TARGET_FACE_PAIRS],
            "changed_face_indexes": changed_face_indexes,
            "changes": changes,
            "positions_moved": False,
            "vertex_count": len(positions),
            "triangle_count": len(faces),
        },
        "topology_digest": canonical_digest({"positions": positions, "faces": faces}),
    }


def _intersection_count(positions, specimen):
    return int(
        inspect_triangle_self_intersections(positions, specimen["indices"], max_examples=64)[
            "self_intersection_pair_count"
        ]
    )


def search_single_stitch_edge_flips() -> dict:
    """Exhaust the exact twenty-two legal single flips at the three retained anchors."""
    rigging = audit_diagonal_repair_rigging_rebind()
    if rigging["status"] != RIGGING_REBIND_STATUS:
        raise ValueError("exact Rigging PR #10 prerequisite is not green")

    bases = {side: build_diagonal_mask_specimen(side, SELECTED_MASK) for side in ("L", "R")}
    candidates = _single_flip_candidates(bases["L"])
    right_pairs = {row["face_pair"] for row in _single_flip_candidates(bases["R"])}
    if {row["face_pair"] for row in candidates} != right_pairs:
        raise ValueError("left/right legal stitch-edge face-pair family drift")

    poses = {
        side: {
            float(row["angle_deg"]): row["positions"]
            for row in rigging["results"][side]["candidate"]
            if float(row["angle_deg"]) in ANCHOR_ANGLES_DEG
        }
        for side in ("L", "R")
    }

    rows = []
    distribution = Counter()
    for candidate in candidates:
        pair = candidate["face_pair"]
        counts = []
        for side in ("L", "R"):
            specimen = build_single_stitch_edge_specimen(side, pair)
            for angle in ANCHOR_ANGLES_DEG:
                counts.append(_intersection_count(poses[side][float(angle)], specimen))
        row = {
            "face_pair": list(pair),
            "counts_L_m40_0_p40_R_m40_0_p40": counts,
            "maximum_pair_count": max(counts),
            "total_pair_count": sum(counts),
        }
        rows.append(row)
        distribution[row["total_pair_count"]] += 1

    rows.sort(key=lambda row: (row["total_pair_count"], row["maximum_pair_count"], row["face_pair"]))
    expected_distribution = {int(key): int(value) for key, value in EXPECTED_SINGLE_SEARCH_DISTRIBUTION.items()}
    if dict(sorted(distribution.items())) != expected_distribution:
        raise ValueError("single stitch-edge search distribution drift")

    winners = [row for row in rows if row["total_pair_count"] == rows[0]["total_pair_count"]]
    if [tuple(row["face_pair"]) for row in winners] != list(TARGET_FACE_PAIRS):
        raise ValueError("single stitch-edge minimum pair set drift")

    return {
        "schema": SCHEMA,
        "searched_group": TARGET_GROUP,
        "legal_single_flip_count": len(rows),
        "anchor_angles_deg": list(ANCHOR_ANGLES_DEG),
        "distribution_by_total_pair_count": dict(sorted(distribution.items())),
        "minimum_total_pair_count": rows[0]["total_pair_count"],
        "winning_face_pairs": [row["face_pair"] for row in winners],
        "rows": rows,
        "selection_boundary": (
            "Only the exact legal single-edge stitch family is exhausted here. "
            "The two non-overlapping single-flip winners are then combined and "
            "validated separately; arbitrary multi-edge remeshing is not exhausted."
        ),
    }


def audit_stitch_edge_repair() -> dict:
    geometry = audit_selected_diagonal_repair()
    if geometry["status"] != DIAGONAL_REPAIR_STATUS:
        raise ValueError("exact Geometry PR #9 prerequisite is not green")
    if geometry["sampled_intersection_comparison"]["candidate_total_pairs"] != 52:
        raise ValueError("Geometry PR #9 anchor total drift")

    rigging = audit_diagonal_repair_rigging_rebind()
    if rigging["status"] != RIGGING_REBIND_STATUS:
        raise ValueError("exact Rigging PR #10 prerequisite is not green")
    if rigging["contract"]["geometry_repair_head"] != DIAGONAL_REPAIR_HEAD:
        raise ValueError("Rigging rebind is not bound to the exact Geometry PR #9 head")

    single_search = search_single_stitch_edge_flips()
    baseline = {side: build_diagonal_mask_specimen(side, SELECTED_MASK) for side in ("L", "R")}
    candidate = {side: build_stitch_edge_repair_specimen(side) for side in ("L", "R")}

    for side in ("L", "R"):
        if candidate[side]["positions"] != baseline[side]["positions"]:
            raise ValueError("stitch-edge repair moved vertex positions")
        if candidate[side]["groups"] != baseline[side]["groups"]:
            raise ValueError("stitch-edge repair changed face-group identity")

    rows = []
    baseline_total = 0
    candidate_total = 0
    improved_samples = 0
    equal_samples = 0
    worse_samples = 0
    representative = []
    for side in ("L", "R"):
        for pose in rigging["results"][side]["candidate"]:
            angle = float(pose["angle_deg"])
            positions = pose["positions"]
            before_report = inspect_triangle_self_intersections(
                positions, baseline[side]["indices"], max_examples=64
            )
            after_report = inspect_triangle_self_intersections(
                positions, candidate[side]["indices"], max_examples=64
            )
            before = int(before_report["self_intersection_pair_count"])
            after = int(after_report["self_intersection_pair_count"])
            baseline_total += before
            candidate_total += after
            if after < before:
                improved_samples += 1
                relation = "STRICT_REDUCTION"
            elif after == before:
                equal_samples += 1
                relation = "EQUAL"
            else:
                worse_samples += 1
                relation = "WORSE"

            if angle in EXPECTED_ANCHOR_BASE_COUNTS[side]:
                if before != EXPECTED_ANCHOR_BASE_COUNTS[side][angle]:
                    raise ValueError(f"baseline anchor count drift for {side} {angle}")
                if after != EXPECTED_ANCHOR_CANDIDATE_COUNTS[side][angle]:
                    raise ValueError(f"candidate anchor count drift for {side} {angle}")

            row = {
                "side": side,
                "angle_deg": angle,
                "baseline_pair_count": before,
                "candidate_pair_count": after,
                "relation": relation,
            }
            rows.append(row)
            if angle in REPRESENTATIVE_ANGLES_DEG:
                representative.append(
                    {
                        **row,
                        "candidate_examples": after_report["examples"],
                        "candidate_status": after_report["status"],
                    }
                )

    if baseline_total != 1320 or candidate_total != 1020:
        raise ValueError("dense-sweep aggregate intersection count drift")
    if improved_samples != 150 or equal_samples != 12 or worse_samples != 0:
        raise ValueError("dense-sweep per-sample relation distribution drift")
    if any(row["candidate_pair_count"] == 0 for row in rows):
        raise ValueError("truth-boundary guard expected nonzero intersections in every dense sample")

    anchor_candidate = [
        row["candidate_pair_count"]
        for row in rows
        if row["angle_deg"] in ANCHOR_ANGLES_DEG
    ]
    if anchor_candidate != [6, 6, 10, 6, 6, 10]:
        raise ValueError("two-edge anchor count ordering drift")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "producer_dependencies": {
            "diagonal_repair_head": DIAGONAL_REPAIR_HEAD,
            "diagonal_repair_status": geometry["status"],
            "rigging_rebind_head": RIGGING_REBIND_HEAD,
            "rigging_rebind_status": rigging["status"],
            "rigging_profile_digest": canonical_digest(rigging["successor_rig_profile"]),
        },
        "selection": {
            "single_edge_search": {
                "legal_single_flip_count": single_search["legal_single_flip_count"],
                "distribution_by_total_pair_count": single_search["distribution_by_total_pair_count"],
                "minimum_total_pair_count": single_search["minimum_total_pair_count"],
                "winning_face_pairs": single_search["winning_face_pairs"],
            },
            "combined_face_pairs": [list(pair) for pair in TARGET_FACE_PAIRS],
            "changed_face_indexes": [111, 112, 114, 115],
            "positions_moved": False,
            "vertex_count_per_side": 93,
            "triangle_count_per_side": 180,
            "left_topology_digest": candidate["L"]["topology_digest"],
            "right_topology_digest": candidate["R"]["topology_digest"],
            "left_local_preflight": candidate["L"]["local_preflight"],
            "right_local_preflight": candidate["R"]["local_preflight"],
        },
        "dense_sweep": {
            "angle_range_deg": [-40.0, 40.0],
            "step_deg": 1.0,
            "samples_per_side": 81,
            "total_samples": 162,
            "baseline_pair_count_sum": baseline_total,
            "candidate_pair_count_sum": candidate_total,
            "reduction_pair_count": baseline_total - candidate_total,
            "reduction_fraction": (baseline_total - candidate_total) / baseline_total,
            "strictly_reduced_samples": improved_samples,
            "equal_samples": equal_samples,
            "worse_samples": worse_samples,
            "baseline_min_pair_count": min(row["baseline_pair_count"] for row in rows),
            "baseline_max_pair_count": max(row["baseline_pair_count"] for row in rows),
            "candidate_min_pair_count": min(row["candidate_pair_count"] for row in rows),
            "candidate_max_pair_count": max(row["candidate_pair_count"] for row in rows),
            "all_candidate_samples_still_nonzero": True,
            "rows": rows,
        },
        "representative_samples": representative,
        "gates": {
            "exact_geometry_pr9_identity": "PASS",
            "exact_rigging_pr10_identity": "PASS",
            "single_stitch_edge_family_exhausted_at_anchors": "PASS",
            "two_selected_edges_non_overlapping": "PASS",
            "same_position_topology_only": "PASS",
            "same_vertex_triangle_budget": "PASS",
            "closed_oriented_single_component_local_preflight": "PASS",
            "dense_sweep_nonworse_all_162_samples": "PASS",
            "dense_sweep_strict_reduction_150_samples": "PASS",
            "intersection_free": "HOLD_NONZERO_INTERSECTIONS_REMAIN",
            "rigging_rebind_for_this_topology": "NOT_PERFORMED",
            "visual_acceptance": "NOT_CLAIMED",
            "runtime_or_gameplay": "NOT_CLAIMED",
        },
        "handoffs": {
            "geometry": (
                "Retain this exact two-edge stitch candidate as a rollbackable successor. "
                "Every tested dense pose still has nonzero intersections, so any further "
                "repair must use a new explicit topology family rather than relabel this PASS."
            ),
            "rigging": (
                "Rigging PR #10 remains truthful for Geometry PR #9 only. This successor changes "
                "four face records and therefore needs an explicit rebind/rerun before any "
                "deformation PASS transfers."
            ),
            "visual_observer_art_direction": (
                "The structural reduction is not visual seam or silhouette acceptance. "
                "Review retained successor poses directly only if the topology advances."
            ),
            "organic_form": (
                "No source/seam/arm position moved. Return to Organic Form only if a later "
                "repair requires source-form motion rather than another derived topology change."
            ),
        },
        "truth_boundary": [
            "This result changes exactly two non-overlapping internal diagonals in the existing ribcage-to-seam stitch and moves no vertex.",
            "The exact one-degree -40..+40 Rigging PR #10 pose field is finite sampled evidence, not mathematical continuous-motion proof.",
            "The 22 legal single-edge stitch family is exhausted only at the retained -40/0/+40 anchors; arbitrary multi-edge remeshing is not exhausted.",
            "All 162 tested candidate poses still contain nonadjacent triangle intersections, so no intersection-free or collision-safe claim is made.",
            "No adjacent-face fold-over/contact freedom, anatomy, final normals/tangents/UVs, Rigging acceptance for this successor, visual quality, Animation, runtime, gameplay, CANON, production readiness, game readiness or Geometry mastery is established.",
        ],
    }


def build_stitch_edge_repair_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_stitch_edge_repair()
    search = search_single_stitch_edge_flips()
    (out / "connected-shoulder-stitch-edge-repair-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "connected-shoulder-stitch-edge-single-search.json").write_text(
        json.dumps(search, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rigging = audit_diagonal_repair_rigging_rebind()
    for side in ("L", "R"):
        specimen = build_stitch_edge_repair_specimen(side)
        (out / f"connected-shoulder-{side.lower()}-stitch-edge-repair.mesh.json").write_text(
            json.dumps(
                {"positions": specimen["positions"], "faces": specimen["faces"]},
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        rows = {
            float(row["angle_deg"]): row
            for row in rigging["results"][side]["candidate"]
        }
        for angle in REPRESENTATIVE_ANGLES_DEG:
            label = f"p{int(angle)}" if angle >= 0 else f"m{abs(int(angle))}"
            write_obj(
                {
                    "vertices": rows[float(angle)]["positions"],
                    "faces": specimen["faces"],
                    "regions": [],
                },
                out / f"connected-shoulder-{side.lower()}-{label}-stitch-edge-repair.obj",
            )
    return receipt
