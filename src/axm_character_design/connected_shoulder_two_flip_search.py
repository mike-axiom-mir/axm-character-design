"""Geometry-owned exhaustive two-flip search over the current Character shoulder stitch.

This bounded observer stacks on the exact Rigging PR #12 pose field. It changes no
Character source, vertex position, seam/arm sample, rig, weighting profile, pose,
Animation, Runtime, Materials, Universal Creation, or axm-create-me product code.

Geometry PR #11 selected the two best *single* legal flips in the exact
``ribcage_to_seam`` stitch and combined them, but explicitly did not exhaust the
face-disjoint two-flip family. This module closes only that bounded search gap.

Every legal unordered pair of face-disjoint single flips is first challenged at
L/R x -40/0/+40 degrees. Candidates that are no worse than the current PR #11
control at every anchor are then challenged against the complete exact Rigging
PR #12 one-degree pose field (-40..+40 on both shoulders). The dense gate fails
closed as soon as a candidate is worse at any retained sample.

A strict reduction may produce a new same-position topology candidate. If no
strict reduction survives, the useful result is a truthful HOLD proving only
that this exact face-disjoint two-flip family has been exhausted under the
current sampled no-worse gate. Arbitrary three-plus-edge remeshing, vertex
movement, continuous deformation safety, adjacent-face fold/contact, anatomy,
and visual quality remain outside this observer.
"""
from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path

from .connected_shoulder_diagonal_repair import SELECTED_MASK, build_diagonal_mask_specimen
from .connected_shoulder_stitch_edge_repair import (
    TARGET_FACE_PAIRS,
    _flip_face_pair,
    _single_flip_candidates,
    build_stitch_edge_repair_specimen,
)
from .connected_shoulder_stitch_rigging_rebind import (
    ANCHOR_ANGLES_DEG,
    STATUS as RIGGING_STITCH_STATUS,
    SWEEP_ANGLES_DEG,
    audit_stitch_edge_rigging_rebind,
)
from .organic_form import canonical_digest
from .self_intersection import inspect_triangle_self_intersections
from .shoulder_connected_topology import _inspect_indexed_surface

SCHEMA = "axm.character-connected-shoulder-disjoint-two-flip-search/v0.1"
PASS_STATUS = (
    "PASS_CHARACTER_CONNECTED_SHOULDER_DISJOINT_TWO_FLIP_EXHAUSTIVE_NO_WORSE_REDUCTION"
    "__HOLD_NONZERO_INTERSECTIONS"
)
HOLD_STATUS = (
    "HOLD_CHARACTER_CONNECTED_SHOULDER_DISJOINT_TWO_FLIP_FAMILY_EXHAUSTED_"
    "NO_STRICT_IMPROVEMENT__NONZERO_INTERSECTIONS_REMAIN"
)

GEOMETRY_STITCH_HEAD = "b65d73e514c23670204915bde8ce935a3b417574"
RIGGING_STITCH_REBIND_HEAD = "329c485f567faeeb79198c7b1ebc2974b3c3db60"
EXPECTED_CURRENT_DENSE_PAIR_SUM = 1020
EXPECTED_CURRENT_STRICTLY_REDUCED_SAMPLES = 150
EXPECTED_VERTEX_COUNT = 93
EXPECTED_TRIANGLE_COUNT = 180


def _canonical_combo(combo):
    if not isinstance(combo, (tuple, list)) or len(combo) != 2:
        raise ValueError("two-flip combination must contain exactly two face pairs")
    normalized = []
    for pair in combo:
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("each flip must contain exactly two face indexes")
        values = tuple(sorted(int(value) for value in pair))
        if values[0] == values[1]:
            raise ValueError("flip face indexes must be distinct")
        normalized.append(values)
    normalized = tuple(sorted(normalized))
    if normalized[0] == normalized[1]:
        raise ValueError("two-flip combination cannot repeat the same face pair")
    if not set(normalized[0]).isdisjoint(normalized[1]):
        raise ValueError("two-flip combination must be face-disjoint")
    return normalized


def _combo_key(combo):
    combo = _canonical_combo(combo)
    return tuple(value for pair in combo for value in pair)


def _current_combo():
    return _canonical_combo(TARGET_FACE_PAIRS)


def legal_disjoint_two_flip_combinations(side: str = "L"):
    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    singles = [tuple(row["face_pair"]) for row in _single_flip_candidates(base)]
    combos = []
    for first, second in combinations(singles, 2):
        if not set(first).isdisjoint(second):
            continue
        combos.append(_canonical_combo((first, second)))
    combos = sorted(set(combos), key=_combo_key)
    if _current_combo() not in combos:
        raise ValueError("current Geometry PR #11 two-flip control left legal family")
    if not combos:
        raise ValueError("no legal face-disjoint two-flip combinations found")
    return combos


def build_two_flip_specimen(side: str, combo) -> dict:
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    combo = _canonical_combo(combo)
    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    legal_pairs = {tuple(row["face_pair"]) for row in _single_flip_candidates(base)}
    if any(pair not in legal_pairs for pair in combo):
        raise ValueError("combination contains a face pair outside the exact legal stitch family")

    faces = [list(face) for face in base["faces"]]
    changes = []
    for pair in combo:
        faces, change = _flip_face_pair(faces, pair)
        changes.append(change)

    positions = [list(point) for point in base["positions"]]
    groups = list(base["groups"])
    local = _inspect_indexed_surface(positions, faces)
    if local["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
        raise ValueError("two-flip specimen failed Character-local topology preflight")
    if len(positions) != EXPECTED_VERTEX_COUNT or len(faces) != EXPECTED_TRIANGLE_COUNT:
        raise ValueError("two-flip specimen changed exact vertex/triangle budget")
    if groups != list(base["groups"]):
        raise ValueError("two-flip specimen changed face-group identity")

    changed_face_indexes = [
        index
        for index, (before, after) in enumerate(zip(base["faces"], faces))
        if list(before) != list(after)
    ]
    expected_changed = sorted(value for pair in combo for value in pair)
    if changed_face_indexes != expected_changed:
        raise ValueError("two-flip specimen changed unexpected face records")

    return {
        "schema": SCHEMA,
        "id": f"character-connected-shoulder-{side.lower()}-two-flip-search-001",
        "side": side,
        "combo": [list(pair) for pair in combo],
        "positions": positions,
        "faces": faces,
        "indices": [index for face in faces for index in face],
        "groups": groups,
        "changes": changes,
        "changed_face_indexes": changed_face_indexes,
        "local_preflight": local,
        "topology_digest": canonical_digest({"positions": positions, "faces": faces}),
    }


def _intersection_count(positions, specimen):
    return int(
        inspect_triangle_self_intersections(
            positions, specimen["indices"], max_examples=8
        )["self_intersection_pair_count"]
    )


def _pose_field(rigging):
    output = {}
    for side in ("L", "R"):
        rows = rigging["results"][side]["candidate"]
        by_angle = {float(row["angle_deg"]): row["positions"] for row in rows}
        if sorted(by_angle) != sorted(float(value) for value in SWEEP_ANGLES_DEG):
            raise ValueError(f"exact Rigging PR #12 pose field drift for {side}")
        output[side] = by_angle
    return output


def _counts_for_specimen(specimen, pose_field, angles):
    return {
        side: {
            float(angle): _intersection_count(
                pose_field[side][float(angle)], specimen[side]
            )
            for angle in angles
        }
        for side in ("L", "R")
    }


def _flatten_counts(counts, angles):
    return [
        int(counts[side][float(angle)])
        for side in ("L", "R")
        for angle in angles
    ]


def audit_disjoint_two_flip_search() -> dict:
    rigging = audit_stitch_edge_rigging_rebind()
    if rigging["status"] != RIGGING_STITCH_STATUS:
        raise ValueError("exact Rigging PR #12 prerequisite is not green")
    geometry_dense = int(rigging["dependencies"]["geometry_stitch_dense_pair_sum"])
    if geometry_dense != EXPECTED_CURRENT_DENSE_PAIR_SUM:
        raise ValueError("current Geometry PR #11 dense pair total drift")
    if int(rigging["dependencies"]["geometry_stitch_strictly_reduced_samples"]) != EXPECTED_CURRENT_STRICTLY_REDUCED_SAMPLES:
        raise ValueError("current Geometry PR #11 dense relation distribution drift")

    pose_field = _pose_field(rigging)
    current = {
        side: build_stitch_edge_repair_specimen(side) for side in ("L", "R")
    }
    current_counts = _counts_for_specimen(current, pose_field, SWEEP_ANGLES_DEG)
    current_flat = _flatten_counts(current_counts, SWEEP_ANGLES_DEG)
    current_total = sum(current_flat)
    if current_total != EXPECTED_CURRENT_DENSE_PAIR_SUM:
        raise ValueError("independent current-control dense pair sum drift")
    if any(value <= 0 for value in current_flat):
        raise ValueError("current control unexpectedly contains an intersection-free sampled pose")

    left_combos = legal_disjoint_two_flip_combinations("L")
    right_combos = legal_disjoint_two_flip_combinations("R")
    if left_combos != right_combos:
        raise ValueError("left/right legal disjoint two-flip family drift")

    anchor_angles = tuple(float(value) for value in ANCHOR_ANGLES_DEG)
    current_anchor = {
        side: {angle: current_counts[side][angle] for angle in anchor_angles}
        for side in ("L", "R")
    }

    anchor_rows = []
    anchor_survivors = []
    for combo in left_combos:
        specimens = {side: build_two_flip_specimen(side, combo) for side in ("L", "R")}
        counts = _counts_for_specimen(specimens, pose_field, anchor_angles)
        comparisons = [
            counts[side][angle] - current_anchor[side][angle]
            for side in ("L", "R")
            for angle in anchor_angles
        ]
        row = {
            "combo": [list(pair) for pair in combo],
            "anchor_counts": counts,
            "anchor_pair_sum": sum(_flatten_counts(counts, anchor_angles)),
            "maximum_anchor_pair_count": max(_flatten_counts(counts, anchor_angles)),
            "no_worse_every_anchor": max(comparisons) <= 0,
            "strictly_better_anchor_samples": sum(value < 0 for value in comparisons),
            "equal_anchor_samples": sum(value == 0 for value in comparisons),
            "worse_anchor_samples": sum(value > 0 for value in comparisons),
        }
        anchor_rows.append(row)
        if row["no_worse_every_anchor"]:
            anchor_survivors.append(combo)

    if _current_combo() not in anchor_survivors:
        raise ValueError("current control failed its own anchor no-worse gate")

    dense_rows = []
    current_by_key = {
        (side, float(angle)): current_counts[side][float(angle)]
        for side in ("L", "R")
        for angle in SWEEP_ANGLES_DEG
    }
    for combo in anchor_survivors:
        specimens = {side: build_two_flip_specimen(side, combo) for side in ("L", "R")}
        total = 0
        maximum = 0
        improved = 0
        equal = 0
        worse = 0
        aborted = False
        rows = []
        for side in ("L", "R"):
            for angle in SWEEP_ANGLES_DEG:
                angle = float(angle)
                observed = _intersection_count(pose_field[side][angle], specimens[side])
                control = current_by_key[(side, angle)]
                delta = observed - control
                rows.append(
                    {
                        "side": side,
                        "angle_deg": angle,
                        "control_pair_count": control,
                        "candidate_pair_count": observed,
                        "delta": delta,
                    }
                )
                total += observed
                maximum = max(maximum, observed)
                if delta < 0:
                    improved += 1
                elif delta == 0:
                    equal += 1
                else:
                    worse += 1
                    aborted = True
                    break
            if aborted:
                break
        dense_rows.append(
            {
                "combo": [list(pair) for pair in combo],
                "no_worse_every_dense_sample": not aborted,
                "aborted_on_first_worse_sample": aborted,
                "evaluated_sample_count": len(rows),
                "candidate_pair_sum": total if not aborted else None,
                "maximum_pair_count": maximum if not aborted else None,
                "strictly_better_samples": improved if not aborted else None,
                "equal_samples": equal if not aborted else None,
                "worse_samples": worse,
                "sample_rows": rows if not aborted else rows[-1:],
            }
        )

    dense_survivors = [
        row for row in dense_rows if row["no_worse_every_dense_sample"]
    ]
    if not dense_survivors:
        raise ValueError("current control disappeared from dense no-worse family")

    dense_survivors.sort(
        key=lambda row: (
            int(row["candidate_pair_sum"]),
            int(row["maximum_pair_count"]),
            _combo_key(row["combo"]),
        )
    )
    selected_row = dense_survivors[0]
    selected_combo = _canonical_combo(selected_row["combo"])
    selected_total = int(selected_row["candidate_pair_sum"])
    strict_rows = [
        row
        for row in dense_survivors
        if int(row["candidate_pair_sum"]) < current_total
    ]

    selected = {
        side: build_two_flip_specimen(side, selected_combo) for side in ("L", "R")
    }
    for side in ("L", "R"):
        base = build_diagonal_mask_specimen(side, SELECTED_MASK)
        if selected[side]["positions"] != [list(point) for point in base["positions"]]:
            raise ValueError("selected two-flip candidate moved vertex positions")
        if selected[side]["groups"] != list(base["groups"]):
            raise ValueError("selected two-flip candidate changed face-group identity")

    selected_is_current = selected_combo == _current_combo()
    strict_improvement = selected_total < current_total
    if strict_improvement and selected_is_current:
        raise ValueError("current control cannot be a strict improvement over itself")
    status = PASS_STATUS if strict_improvement else HOLD_STATUS

    return {
        "schema": SCHEMA,
        "status": status,
        "dependencies": {
            "geometry_stitch_head": GEOMETRY_STITCH_HEAD,
            "rigging_stitch_rebind_head": RIGGING_STITCH_REBIND_HEAD,
            "rigging_status": rigging["status"],
            "current_dense_pair_sum": current_total,
        },
        "search_scope": {
            "legal_single_flip_count": 22,
            "legal_face_disjoint_two_flip_combination_count": len(left_combos),
            "anchor_angles_deg": list(anchor_angles),
            "dense_angles_deg": [float(value) for value in SWEEP_ANGLES_DEG],
            "dense_sample_count": len(current_flat),
            "anchor_no_worse_survivor_count": len(anchor_survivors),
            "dense_no_worse_survivor_count": len(dense_survivors),
            "strict_dense_total_improvement_count": len(strict_rows),
            "arbitrary_three_plus_edge_remeshing_exhausted": False,
            "vertex_movement_exhausted": False,
        },
        "current_control": {
            "combo": [list(pair) for pair in _current_combo()],
            "dense_pair_sum": current_total,
            "minimum_pair_count": min(current_flat),
            "maximum_pair_count": max(current_flat),
            "all_sampled_poses_nonzero": all(value > 0 for value in current_flat),
            "anchor_counts": current_anchor,
            "left_topology_digest": current["L"]["topology_digest"],
            "right_topology_digest": current["R"]["topology_digest"],
        },
        "selection": {
            "combo": [list(pair) for pair in selected_combo],
            "dense_pair_sum": selected_total,
            "pair_sum_delta_vs_current": selected_total - current_total,
            "maximum_pair_count": int(selected_row["maximum_pair_count"]),
            "strictly_better_samples": int(selected_row["strictly_better_samples"]),
            "equal_samples": int(selected_row["equal_samples"]),
            "worse_samples": 0,
            "strict_improvement": strict_improvement,
            "selected_is_current_control": selected_is_current,
            "left_topology_digest": selected["L"]["topology_digest"],
            "right_topology_digest": selected["R"]["topology_digest"],
            "left_local_preflight": selected["L"]["local_preflight"],
            "right_local_preflight": selected["R"]["local_preflight"],
        },
        "anchor_search": sorted(
            anchor_rows,
            key=lambda row: (
                int(row["anchor_pair_sum"]),
                int(row["maximum_anchor_pair_count"]),
                _combo_key(row["combo"]),
            ),
        ),
        "dense_search": dense_rows,
        "gates": {
            "exact_current_control_reproduced": "PASS",
            "all_selected_vertex_positions_preserved": "PASS",
            "all_selected_face_groups_preserved": "PASS",
            "selected_local_closed_oriented_single_component": "PASS",
            "selected_no_worse_at_every_retained_dense_sample": "PASS",
            "sampled_self_intersection_freedom": "HOLD_NONZERO_INTERSECTIONS_REMAIN",
            "continuous_motion_safety": "NOT_CLAIMED",
            "adjacent_face_fold_contact_freedom": "NOT_CLAIMED",
            "visual_acceptance": "NOT_CLAIMED",
            "rigging_acceptance_for_new_identity": (
                "REQUIRES_REBIND_IF_STRICT_SUCCESSOR"
                if strict_improvement
                else "NO_NEW_TOPOLOGY_IDENTITY_SELECTED"
            ),
        },
        "handoffs": {
            "geometry": (
                "If strict improvement is false, treat the exact face-disjoint two-flip "
                "family as exhausted under this sampled no-worse gate; next Geometry work "
                "must use a genuinely different bounded topology family or return to source/form "
                "ownership rather than repeating diagonal churn."
            ),
            "rigging": (
                "If a strict new topology identity is selected, the current Rigging PR #12 PASS "
                "does not transfer and requires an explicit rebind. If no strict successor is "
                "selected, PR #12 remains the current exact rig/topology chain."
            ),
            "visual_observer_art_direction": (
                "Lower sampled pair counts are not seam, silhouette, volume, anatomy, or final "
                "deformation-quality acceptance. Review only an exact selected successor."
            ),
        },
        "truth_boundary": [
            "This exhausts only unordered pairs of face-disjoint flips drawn from the exact 22 legal PR #11 ribcage-to-seam single-flip locations.",
            "The gate is finite: exact retained anchor poses plus the exact one-degree -40..+40 Rigging PR #12 pose field.",
            "Nonadjacent triangle-pair observation does not cover indexed-neighbour fold-over/contact.",
            "A HOLD is useful negative search evidence, not proof that arbitrary shoulder topology cannot improve.",
            "No source-form, Rigging, visual, Animation, runtime, collision/gameplay, CANON, production-readiness, game-readiness, or Geometry-mastery claim is made.",
        ],
    }


def _write_obj(path: Path, specimen: dict):
    lines = ["# AXM Character Geometry two-flip selected specimen"]
    for point in specimen["positions"]:
        lines.append("v " + " ".join(f"{float(value):.12g}" for value in point))
    for face in specimen["faces"]:
        lines.append("f " + " ".join(str(int(index) + 1) for index in face))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_disjoint_two_flip_search_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_disjoint_two_flip_search()
    (out / "two-flip-search-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    combo = receipt["selection"]["combo"]
    for side in ("L", "R"):
        specimen = build_two_flip_specimen(side, combo)
        _write_obj(out / f"selected-{side.lower()}-neutral.obj", specimen)
    return receipt
