"""Geometry-owned shoulder opening repair over the exact diagnosed Character mesh.

This module does not move Character source, accepted-E seam samples, arm samples,
Rigging weights, joints, or pose semantics.  It changes only the local ribcage
opening / ribcage-to-seam triangulation that Geometry PR #5 diagnosed as the
main neutral self-intersection source.

The candidate is deliberately a *reduction* experiment, not an
intersection-free claim.  Remaining intersections are retained as HOLD evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

from .connected_shoulder_deformation import (
    CANDIDATE_DIGESTS,
    GEOMETRY_HEAD,
    STATUS as RIGGING_STATUS,
    audit_connected_shoulder_deformation,
)
from .organic_form import canonical_digest, write_obj
from .self_intersection import inspect_triangle_self_intersections
from .shoulder_connected_topology import (
    _boundary_loop,
    _inspect_indexed_surface,
    _stitch_loops,
    build_connected_shoulder_specimen,
)

SCHEMA = "axm.character-connected-shoulder-intersection-repair/v0.1"
STATUS = (
    "PASS_CHARACTER_CONNECTED_SHOULDER_TOPOLOGY_ONLY_INTERSECTION_REDUCTION"
    "__HOLD_NONZERO_INTERSECTIONS"
)
DIAGNOSIS_HEAD = "eae6d296867ecaa40e8f5c3f1fe37d8e3019541e"
RIGGING_HEAD = "b0a03cbcb61e0f8deec37172d22ff1a7fff306c9"
GEOMETRY_PRODUCER_HEAD = "dcb2185a42072540ef2be37329735357561e01b5"

# Indices are local to the exact 112-face retained ribcage group produced by
# GEOMETRY_PRODUCER_HEAD, not source-owned face IDs.  They are therefore pinned
# to that exact producer identity and are not a generic ellipsoid policy.
_EXTRA_RIBCAGE_FACE_INDICES = {
    "L": (38, 39, 40, 41),
    "R": (28, 29, 50, 51),
}

# The expanded opening has 12 boundary vertices.  Phase is selected only among
# same-position retessellations to minimize the worst sampled retained
# intersection count across -40 / 0 / +40 degrees.  Seam phase remains zero.
_EXPANDED_HOLE_PHASE = {"L": 0, "R": 10}
_SEAM_PHASE = {"L": 0, "R": 0}

_EXPECTED_BASE_COUNTS = {
    "L": {-40.0: 61, 0.0: 61, 40.0: 65},
    "R": {-40.0: 61, 0.0: 61, 40.0: 65},
}
_EXPECTED_CANDIDATE_COUNTS = {
    "L": {-40.0: 9, 0.0: 9, 40.0: 11},
    "R": {-40.0: 9, 0.0: 9, 40.0: 11},
}


def _group_faces(specimen, group_name):
    return [
        list(face)
        for face, group in zip(specimen["faces"], specimen["groups"])
        if group == group_name
    ]


def _rotate(values, phase):
    values = list(values)
    if not values:
        raise ValueError("cannot rotate empty loop")
    phase = int(phase) % len(values)
    return values[phase:] + values[:phase]


def build_opening_repair_specimen(side):
    """Retessellate only the diagnosed ribcage opening / outer stitch."""
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")

    base = build_connected_shoulder_specimen(side)
    if canonical_digest({"positions": base["positions"], "faces": base["faces"]}) != CANDIDATE_DIGESTS[side]:
        raise ValueError(f"connected shoulder {side} producer identity drift")

    rib_faces = _group_faces(base, "ribcage")
    old_outer = _group_faces(base, "ribcage_to_seam")
    if len(rib_faces) != 112 or len(old_outer) != 20:
        raise ValueError("exact diagnosed ribcage/outer-stitch topology drift")

    extra = set(_EXTRA_RIBCAGE_FACE_INDICES[side])
    if len(extra) != 4 or max(extra) >= len(rib_faces):
        raise ValueError("expanded opening face-selection contract drift")
    remaining_rib = [face for index, face in enumerate(rib_faces) if index not in extra]

    hole = _boundary_loop(remaining_rib)
    if len(hole) != 12:
        raise ValueError("expanded Character shoulder opening must expose exactly twelve boundary vertices")
    hole = _rotate(hole, _EXPANDED_HOLE_PHASE[side])

    base_rib_vertices = {vertex for face in rib_faces for vertex in face}
    outer_vertices = {vertex for face in old_outer for vertex in face}
    seam = sorted(outer_vertices - base_rib_vertices)
    if len(seam) != 10:
        raise ValueError("exact diagnosed outer stitch must expose ten seam vertices")
    seam = _rotate(seam, _SEAM_PHASE[side])

    repaired_outer = _stitch_loops(list(reversed(hole)), seam)
    if len(repaired_outer) != 22:
        raise ValueError("12-to-10 expanded shoulder stitch must contain twenty-two triangles")

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

    positions = [list(point) for point in base["positions"]]
    local = _inspect_indexed_surface(positions, faces)
    if local["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
        raise ValueError("opening repair failed Character-local closed/oriented/single-component preflight")
    if len(positions) != 93 or len(faces) != 180:
        raise ValueError("opening repair vertex/triangle budget drift")

    return {
        "schema": SCHEMA,
        "id": f"character-connected-shoulder-{side.lower()}-opening-repair-001",
        "side": side,
        "positions": positions,
        "faces": faces,
        "indices": [index for face in faces for index in face],
        "groups": groups,
        "local_preflight": local,
        "construction": {
            "diagnosed_geometry_head": GEOMETRY_PRODUCER_HEAD,
            "diagnosis_head": DIAGNOSIS_HEAD,
            "extra_removed_ribcage_group_face_indices": list(_EXTRA_RIBCAGE_FACE_INDICES[side]),
            "expanded_hole_vertex_count": len(hole),
            "expanded_hole_phase": _EXPANDED_HOLE_PHASE[side],
            "seam_phase": _SEAM_PHASE[side],
            "positions_moved": False,
            "old_triangle_count": len(base["faces"]),
            "candidate_triangle_count": len(faces),
            "policy": "EXPAND_ONLY_DIAGNOSED_RIBCAGE_OPENING__RESTITCH_TO_EXACT_EXISTING_SEAM__NO_VERTEX_OR_SOURCE_EDIT",
        },
        "truth_boundary": {
            "source_rewritten": False,
            "accepted_E_seam_positions_moved": False,
            "arm_positions_moved": False,
            "rigging_rewritten": False,
            "closed_oriented_single_component_preflight": True,
            "sampled_nonadjacent_self_intersection_reduction_checked": False,
            "intersection_free": False,
            "visual_acceptance": False,
            "runtime_or_gameplay_acceptance": False,
        },
    }


def audit_opening_repair():
    rigging = audit_connected_shoulder_deformation()
    if rigging["status"] != RIGGING_STATUS:
        raise ValueError("exact retained Rigging prerequisite is not green")
    if rigging["geometry_head"] != GEOMETRY_HEAD or GEOMETRY_HEAD != GEOMETRY_PRODUCER_HEAD:
        raise ValueError("Rigging / Geometry producer lineage drift")

    samples = []
    base_total = 0
    candidate_total = 0
    for side in ("L", "R"):
        base = build_connected_shoulder_specimen(side)
        candidate = build_opening_repair_specimen(side)
        if candidate["positions"] != base["positions"]:
            raise ValueError("topology-only repair moved vertex positions")
        for pose in rigging["results"][side]["candidate"]:
            angle = float(pose["angle_deg"])
            base_report = inspect_triangle_self_intersections(pose["positions"], base["indices"])
            candidate_report = inspect_triangle_self_intersections(pose["positions"], candidate["indices"])
            base_count = int(base_report["self_intersection_pair_count"])
            candidate_count = int(candidate_report["self_intersection_pair_count"])
            if base_count != _EXPECTED_BASE_COUNTS[side][angle]:
                raise ValueError(f"historical diagnosed count drift for {side} {angle}")
            if candidate_count != _EXPECTED_CANDIDATE_COUNTS[side][angle]:
                raise ValueError(f"opening-repair count drift for {side} {angle}")
            if candidate_count >= base_count:
                raise ValueError(f"opening repair did not reduce intersections for {side} {angle}")
            base_total += base_count
            candidate_total += candidate_count
            samples.append({
                "side": side,
                "angle_deg": angle,
                "base_intersection_pair_count": base_count,
                "candidate_intersection_pair_count": candidate_count,
                "reduction_pair_count": base_count - candidate_count,
                "reduction_fraction": (base_count - candidate_count) / base_count,
                "candidate_status": candidate_report["status"],
                "candidate_examples": candidate_report["examples"],
            })

    if base_total != 374 or candidate_total != 58:
        raise ValueError("aggregate diagnosed/candidate count drift")
    if any(row["candidate_intersection_pair_count"] == 0 for row in samples):
        raise ValueError("truth-boundary guard expected remaining sampled intersections")

    left = build_opening_repair_specimen("L")
    right = build_opening_repair_specimen("R")
    if {
        (round(-float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in left["positions"]
    } != {
        (round(float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in right["positions"]
    }:
        raise ValueError("topology-only opening repair lost bilateral mirrored position sets")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "producer_dependencies": {
            "geometry_producer_head": GEOMETRY_PRODUCER_HEAD,
            "diagnosis_head": DIAGNOSIS_HEAD,
            "rigging_head": RIGGING_HEAD,
            "rigging_status": rigging["status"],
            "rig_plan_digest": rigging["rig_plan_digest"],
            "left_base_geometry_digest": CANDIDATE_DIGESTS["L"],
            "right_base_geometry_digest": CANDIDATE_DIGESTS["R"],
        },
        "candidate": {
            "vertex_count_per_side": 93,
            "triangle_count_per_side": 180,
            "positions_identical_to_diagnosed_geometry": True,
            "left_topology_digest": canonical_digest({"positions": left["positions"], "faces": left["faces"]}),
            "right_topology_digest": canonical_digest({"positions": right["positions"], "faces": right["faces"]}),
            "left_local_preflight": left["local_preflight"],
            "right_local_preflight": right["local_preflight"],
            "construction": {
                "L": left["construction"],
                "R": right["construction"],
            },
        },
        "sampled_intersection_comparison": {
            "samples": samples,
            "base_total_pairs": base_total,
            "candidate_total_pairs": candidate_total,
            "reduction_pair_count": base_total - candidate_total,
            "reduction_fraction": (base_total - candidate_total) / base_total,
            "neutral_base_pairs_per_side": 61,
            "neutral_candidate_pairs_per_side": 9,
            "all_candidate_samples_still_nonzero": True,
        },
        "gates": {
            "exact_historical_geometry_identity": "PASS",
            "exact_retained_rigging_pose_identity": "PASS",
            "topology_only_no_vertex_motion": "PASS",
            "closed_oriented_single_component_local_preflight": "PASS",
            "sampled_nonadjacent_intersection_count_strictly_reduced_all_six": "PASS",
            "intersection_free": "HOLD_NONZERO_INTERSECTIONS_REMAIN",
            "rigging_rebind": "NOT_PERFORMED",
            "visual_acceptance": "NOT_CLAIMED",
            "runtime_or_gameplay": "NOT_CLAIMED",
        },
        "handoffs": {
            "geometry": "Further repair is still required before any intersection-free claim; retain this candidate as a rollbackable reduction baseline.",
            "rigging": "Do not inherit prior deformation PASS onto this topology identity; rebind/rerun only if Geometry selects this or a later successor.",
            "visual_observer_art_direction": "No visual improvement is inferred from lower intersection counts; inspect any selected successor directly.",
            "organic_form": "No source mass/landmark intent changed. Return to Organic Form only if a later repair requires source-form edits rather than derived topology edits.",
        },
        "truth_boundary": [
            "This is a Character-local topology-only reduction candidate over the exact previously diagnosed connected shoulder and exact retained Rigging pose positions.",
            "No vertex, source, accepted-E seam, proximal/distal arm sample, Rigging weight, joint or pose angle is moved or rewritten.",
            "The candidate remains structurally failing for sampled nonadjacent self-intersection: 58 detected pairs remain across six samples, including 9 per side at neutral.",
            "The retained -40/0/+40 degree samples do not prove continuous deformation safety; indexed-neighbour fold-over/contact is outside the observer.",
            "Character-local edge preflight does not establish final vertex-manifoldness, authored normals/tangents/UVs, visual seam quality, anatomy, volume preservation, runtime/collision/gameplay suitability, CANON, production readiness, game readiness, or Geometry mastery.",
        ],
    }


def build_opening_repair_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_opening_repair()
    (out / "connected-shoulder-opening-repair-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rigging = audit_connected_shoulder_deformation()
    for side in ("L", "R"):
        candidate = build_opening_repair_specimen(side)
        (out / f"connected-shoulder-{side.lower()}-opening-repair.mesh.json").write_text(
            json.dumps({"positions": candidate["positions"], "faces": candidate["faces"]}, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for row in rigging["results"][side]["candidate"]:
            angle = int(row["angle_deg"])
            label = f"p{angle}" if angle >= 0 else f"m{abs(angle)}"
            write_obj(
                {"vertices": row["positions"], "faces": candidate["faces"], "regions": []},
                out / f"connected-shoulder-{side.lower()}-{label}-opening-repair.obj",
            )
    return receipt
