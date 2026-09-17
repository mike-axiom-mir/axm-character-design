"""Geometry-owned bounded third-flip extension of the current Character shoulder stitch.

This observer stacks exactly on Geometry PR #13's exhausted face-disjoint two-flip
family and the exact Rigging PR #12 pose field. Geometry #13 proved that no other
face-disjoint two-flip combination improves the current Geometry #11 topology
under the retained no-worse-per-sample gate. The smallest genuinely new family
is therefore not another two-flip shuffle: keep the exact current two-flip
control and test one additional legal face-disjoint stitch edge flip.

The search changes no Character source, vertex position, seam/arm sample, rig,
weighting profile, pose, Animation, Materials, Runtime, Universal Creation, or
axm-create-me product code. Every candidate changes exactly two additional face
records (six relative to the PR #9 base), retains the exact 93v / 180t budget,
face-group identity and closed/oriented/single-component local preflight, and is
challenged first at L/R x -40/0/+40 degrees before any survivor reaches the full
exact Rigging PR #12 one-degree pose field.

A strict dense reduction may create one new rollbackable same-position topology
candidate. If no strict reduction survives, the useful result is a truthful HOLD
for only this current-pair-plus-one-third-flip family. Arbitrary three-flip
combinations that do not contain the current pair, four-plus-edge remeshing,
vertex movement, continuous deformation safety, adjacent-face fold/contact,
anatomy and visual quality remain outside this observer.
"""
from __future__ import annotations

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
from .connected_shoulder_two_flip_search import (
    EXPECTED_CURRENT_DENSE_PAIR_SUM,
    EXPECTED_CURRENT_STRICTLY_REDUCED_SAMPLES,
    EXPECTED_TRIANGLE_COUNT,
    EXPECTED_VERTEX_COUNT,
    _counts_for_specimen,
    _flatten_counts,
    _intersection_count,
    _pose_field,
)
from .organic_form import canonical_digest
from .shoulder_connected_topology import _inspect_indexed_surface

SCHEMA = "axm.character-connected-shoulder-current-pair-third-flip-search/v0.1"
PASS_STATUS = (
    "PASS_CHARACTER_CONNECTED_SHOULDER_CURRENT_PAIR_PLUS_THIRD_FLIP_DENSE_REDUCTION"
    "__HOLD_NONZERO_INTERSECTIONS"
)
HOLD_STATUS = (
    "HOLD_CHARACTER_CONNECTED_SHOULDER_CURRENT_PAIR_PLUS_THIRD_FLIP_FAMILY_"
    "NO_STRICT_IMPROVEMENT__NONZERO_INTERSECTIONS_REMAIN"
)

TWO_FLIP_SEARCH_HEAD = "c3735e8785348c1d23b4de048c82f505b6acf4f0"
GEOMETRY_STITCH_HEAD = "b65d73e514c23670204915bde8ce935a3b417574"
RIGGING_STITCH_REBIND_HEAD = "329c485f567faeeb79198c7b1ebc2974b3c3db60"


def _canonical_face_pair(pair):
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        raise ValueError("third flip must contain exactly two face indexes")
    values = tuple(sorted(int(value) for value in pair))
    if values[0] == values[1]:
        raise ValueError("third flip face indexes must be distinct")
    return values


def _current_face_pairs():
    return tuple(sorted(_canonical_face_pair(pair) for pair in TARGET_FACE_PAIRS))


def _current_face_indexes():
    return {value for pair in _current_face_pairs() for value in pair}


def legal_third_flip_face_pairs(side: str = "L"):
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    singles = sorted(
        {_canonical_face_pair(row["face_pair"]) for row in _single_flip_candidates(base)}
    )
    occupied = _current_face_indexes()
    candidates = [pair for pair in singles if set(pair).isdisjoint(occupied)]
    if not candidates:
        raise ValueError("no legal face-disjoint third-flip extension remains")
    if any(pair in _current_face_pairs() for pair in candidates):
        raise ValueError("current two-flip face pair leaked into third-flip family")
    return candidates


def build_third_flip_specimen(side: str, third_pair) -> dict:
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    third_pair = _canonical_face_pair(third_pair)
    if not set(third_pair).isdisjoint(_current_face_indexes()):
        raise ValueError("third flip must be face-disjoint from the current two-flip control")
    if third_pair not in legal_third_flip_face_pairs(side):
        raise ValueError("third flip is outside the exact legal stitch family")

    current = build_stitch_edge_repair_specimen(side)
    faces, change = _flip_face_pair([list(face) for face in current["faces"]], third_pair)
    positions = [list(point) for point in current["positions"]]
    groups = list(current["groups"])
    local = _inspect_indexed_surface(positions, faces)
    if local["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
        raise ValueError("third-flip specimen failed Character-local topology preflight")
    if len(positions) != EXPECTED_VERTEX_COUNT or len(faces) != EXPECTED_TRIANGLE_COUNT:
        raise ValueError("third-flip specimen changed exact vertex/triangle budget")
    if groups != list(current["groups"]):
        raise ValueError("third-flip specimen changed face-group identity")

    changed_from_current = [
        index
        for index, (before, after) in enumerate(zip(current["faces"], faces))
        if list(before) != list(after)
    ]
    if changed_from_current != list(third_pair):
        raise ValueError("third-flip specimen changed unexpected current face records")

    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    changed_from_base = [
        index
        for index, (before, after) in enumerate(zip(base["faces"], faces))
        if list(before) != list(after)
    ]
    expected_from_base = sorted(_current_face_indexes() | set(third_pair))
    if changed_from_base != expected_from_base:
        raise ValueError("third-flip specimen changed unexpected PR #9 base face records")

    return {
        "schema": SCHEMA,
        "id": f"character-connected-shoulder-{side.lower()}-third-flip-extension-001",
        "side": side,
        "current_face_pairs": [list(pair) for pair in _current_face_pairs()],
        "third_pair": list(third_pair),
        "positions": positions,
        "faces": faces,
        "indices": [index for face in faces for index in face],
        "groups": groups,
        "change": change,
        "changed_face_indexes_from_current": changed_from_current,
        "changed_face_indexes_from_pr9_base": changed_from_base,
        "local_preflight": local,
        "topology_digest": canonical_digest({"positions": positions, "faces": faces}),
    }


def _dense_candidate_row(third_pair, pose_field, current_by_key):
    specimens = {side: build_third_flip_specimen(side, third_pair) for side in ("L", "R")}
    total = 0
    maximum = 0
    improved = 0
    equal = 0
    worse = 0
    rows = []
    aborted = False
    for side in ("L", "R"):
        for angle in SWEEP_ANGLES_DEG:
            angle = float(angle)
            observed = _intersection_count(pose_field[side][angle], specimens[side])
            control = int(current_by_key[(side, angle)])
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
    return {
        "third_pair": list(third_pair),
        "no_worse_every_dense_sample": not aborted,
        "aborted_on_first_worse_sample": aborted,
        "evaluated_sample_count": len(rows),
        "candidate_pair_sum": total if not aborted else None,
        "maximum_pair_count": maximum if not aborted else None,
        "strictly_better_samples": improved if not aborted else None,
        "equal_samples": equal if not aborted else None,
        "worse_samples": worse,
        "all_evaluated_samples_nonzero": all(row["candidate_pair_count"] > 0 for row in rows),
        "sample_rows": rows if not aborted else rows[-1:],
    }


def audit_current_pair_third_flip_search() -> dict:
    rigging = audit_stitch_edge_rigging_rebind()
    if rigging["status"] != RIGGING_STITCH_STATUS:
        raise ValueError("exact Rigging PR #12 prerequisite is not green")
    if int(rigging["dependencies"]["geometry_stitch_dense_pair_sum"]) != EXPECTED_CURRENT_DENSE_PAIR_SUM:
        raise ValueError("current Geometry PR #11 dense pair total drift")
    if int(rigging["dependencies"]["geometry_stitch_strictly_reduced_samples"]) != EXPECTED_CURRENT_STRICTLY_REDUCED_SAMPLES:
        raise ValueError("current Geometry PR #11 dense relation distribution drift")

    pose_field = _pose_field(rigging)
    current = {side: build_stitch_edge_repair_specimen(side) for side in ("L", "R")}
    current_counts = _counts_for_specimen(current, pose_field, SWEEP_ANGLES_DEG)
    current_flat = _flatten_counts(current_counts, SWEEP_ANGLES_DEG)
    current_total = sum(current_flat)
    if current_total != EXPECTED_CURRENT_DENSE_PAIR_SUM:
        raise ValueError("independent current-control dense pair sum drift")
    if any(value <= 0 for value in current_flat):
        raise ValueError("current control unexpectedly contains an intersection-free sampled pose")

    left_pairs = legal_third_flip_face_pairs("L")
    right_pairs = legal_third_flip_face_pairs("R")
    if left_pairs != right_pairs:
        raise ValueError("left/right legal third-flip extension family drift")

    anchor_angles = tuple(float(value) for value in ANCHOR_ANGLES_DEG)
    current_anchor = {
        side: {angle: current_counts[side][angle] for angle in anchor_angles}
        for side in ("L", "R")
    }
    anchor_rows = []
    anchor_survivors = []
    for third_pair in left_pairs:
        specimens = {side: build_third_flip_specimen(side, third_pair) for side in ("L", "R")}
        counts = _counts_for_specimen(specimens, pose_field, anchor_angles)
        deltas = [
            counts[side][angle] - current_anchor[side][angle]
            for side in ("L", "R")
            for angle in anchor_angles
        ]
        flat = _flatten_counts(counts, anchor_angles)
        row = {
            "third_pair": list(third_pair),
            "anchor_counts": counts,
            "anchor_pair_sum": sum(flat),
            "maximum_anchor_pair_count": max(flat),
            "no_worse_every_anchor": max(deltas) <= 0,
            "strictly_better_anchor_samples": sum(delta < 0 for delta in deltas),
            "equal_anchor_samples": sum(delta == 0 for delta in deltas),
            "worse_anchor_samples": sum(delta > 0 for delta in deltas),
        }
        anchor_rows.append(row)
        if row["no_worse_every_anchor"]:
            anchor_survivors.append(third_pair)

    current_by_key = {
        (side, float(angle)): current_counts[side][float(angle)]
        for side in ("L", "R")
        for angle in SWEEP_ANGLES_DEG
    }
    dense_rows = [
        _dense_candidate_row(third_pair, pose_field, current_by_key)
        for third_pair in anchor_survivors
    ]
    dense_survivors = [row for row in dense_rows if row["no_worse_every_dense_sample"]]
    dense_survivors.sort(
        key=lambda row: (
            int(row["candidate_pair_sum"]),
            int(row["maximum_pair_count"]),
            tuple(row["third_pair"]),
        )
    )
    strict_rows = [
        row for row in dense_survivors if int(row["candidate_pair_sum"]) < current_total
    ]

    selection = None
    status = HOLD_STATUS
    if strict_rows:
        selection = dict(strict_rows[0])
        third_pair = _canonical_face_pair(selection["third_pair"])
        selected = {side: build_third_flip_specimen(side, third_pair) for side in ("L", "R")}
        for side in ("L", "R"):
            if selected[side]["positions"] != current[side]["positions"]:
                raise ValueError("selected third-flip candidate moved vertex positions")
            if selected[side]["groups"] != current[side]["groups"]:
                raise ValueError("selected third-flip candidate changed face-group identity")
        selection["strict_improvement"] = True
        selection["topology_digests"] = {
            side: selected[side]["topology_digest"] for side in ("L", "R")
        }
        selection["all_sampled_poses_nonzero"] = all(
            row["candidate_pair_count"] > 0 for row in selection["sample_rows"]
        )
        status = PASS_STATUS

    best_dense_observed = dict(dense_survivors[0]) if dense_survivors else None
    return {
        "schema": SCHEMA,
        "status": status,
        "dependencies": {
            "two_flip_search_head": TWO_FLIP_SEARCH_HEAD,
            "geometry_stitch_head": GEOMETRY_STITCH_HEAD,
            "rigging_stitch_rebind_head": RIGGING_STITCH_REBIND_HEAD,
            "rigging_status": rigging["status"],
        },
        "search_scope": {
            "current_face_pairs": [list(pair) for pair in _current_face_pairs()],
            "legal_single_flip_count": 22,
            "legal_face_disjoint_third_flip_extension_count": len(left_pairs),
            "anchor_angles_deg": list(anchor_angles),
            "dense_angles_deg": [float(value) for value in SWEEP_ANGLES_DEG],
            "dense_sample_count": len(current_flat),
            "anchor_no_worse_survivor_count": len(anchor_survivors),
            "dense_no_worse_survivor_count": len(dense_survivors),
            "strict_dense_total_improvement_count": len(strict_rows),
            "arbitrary_three_flip_combinations_exhausted": False,
            "four_plus_edge_remeshing_exhausted": False,
            "vertex_movement_exhausted": False,
        },
        "current_control": {
            "dense_pair_sum": current_total,
            "minimum_pair_count": min(current_flat),
            "maximum_pair_count": max(current_flat),
            "all_sampled_poses_nonzero": all(value > 0 for value in current_flat),
        },
        "anchor_search": anchor_rows,
        "dense_search": dense_rows,
        "best_dense_observed": best_dense_observed,
        "selection": selection,
        "decision": (
            "SELECT_STRICTLY_IMPROVED_SAME_POSITION_THIRD_FLIP_CANDIDATE__RIGGING_REBIND_REQUIRED"
            if selection is not None
            else "HOLD_NO_NEW_TOPOLOGY_IDENTITY__CURRENT_TWO_FLIP_CONTROL_REMAINS"
        ),
        "limitations": [
            "Search covers only one additional legal face-disjoint flip on top of the exact current two-flip topology.",
            "Arbitrary three-flip combinations that do not contain the current pair are not exhausted.",
            "Four-plus-edge retessellation and vertex/source-form movement are not tested.",
            "The exact pose field is finite one-degree sampling, not mathematical continuous-motion proof.",
            "Adjacent indexed-neighbour fold-over/contact, anatomy, visual seam quality, normals/UVs, Animation, Runtime, collision and gameplay remain outside this observer.",
        ],
    }


def _write_obj(path: Path, specimen: dict):
    lines = [f"# {specimen['id']}", f"# topology_digest {specimen['topology_digest']}"]
    for x, y, z in specimen["positions"]:
        lines.append(f"v {x:.12f} {y:.12f} {z:.12f}")
    for a, b, c in specimen["faces"]:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_current_pair_third_flip_search_evidence(out_dir) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_current_pair_third_flip_search()
    (out / "summary.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if receipt["selection"] is not None:
        third_pair = receipt["selection"]["third_pair"]
        label = "selected-third-flip"
        specimens = {side: build_third_flip_specimen(side, third_pair) for side in ("L", "R")}
    else:
        label = "current-control"
        specimens = {side: build_stitch_edge_repair_specimen(side) for side in ("L", "R")}

    for side, specimen in specimens.items():
        if "id" not in specimen:
            specimen = dict(specimen)
            specimen["id"] = f"character-connected-shoulder-{side.lower()}-{label}"
        if "topology_digest" not in specimen:
            specimen = dict(specimen)
            specimen["topology_digest"] = canonical_digest(
                {"positions": specimen["positions"], "faces": specimen["faces"]}
            )
        _write_obj(out / f"{label}-{side.lower()}.obj", specimen)
    return receipt
