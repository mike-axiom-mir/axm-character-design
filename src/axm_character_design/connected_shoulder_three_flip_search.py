"""Geometry-owned exhaustive three-flip search over the Character shoulder stitch.

This bounded observer continues the exact Character shoulder line without moving source
form, seam samples, arm samples, rigging, weights, poses, Animation, Runtime,
Materials, Universal Creation, or axm-create-me product code.

Geometry PR #13 exhausted every unordered face-disjoint *two*-flip combination drawn
from the exact 22 legal ``ribcage_to_seam`` stitch-edge flips. Geometry PR #14 then
kept the current winning two-flip control fixed and proved that all 16 legal
face-disjoint one-third-flip extensions are observationally neutral under the exact
Rigging PR #12 pose field.

This module closes the next strictly bounded family: every unordered set of exactly
three pairwise face-disjoint flips drawn from those same exact 22 legal stitch-edge
locations, including triples that do *not* contain the current two-flip control.
It is therefore broader than PR #14, but it still does not exhaust arbitrary
three-edge remeshing, four-plus-edge remeshing, vertex movement, source-form repair,
continuous deformation safety, adjacent-face fold/contact, anatomy, or visual quality.
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
from .connected_shoulder_third_flip_search import legal_third_flip_face_pairs
from .connected_shoulder_two_flip_search import (
    EXPECTED_CURRENT_DENSE_PAIR_SUM,
    EXPECTED_CURRENT_STRICTLY_REDUCED_SAMPLES,
    EXPECTED_TRIANGLE_COUNT,
    EXPECTED_VERTEX_COUNT,
    _intersection_count,
    _pose_field,
)
from .organic_form import canonical_digest
from .shoulder_connected_topology import _inspect_indexed_surface

SCHEMA = "axm.character-connected-shoulder-disjoint-three-flip-search/v0.1"
PASS_STATUS = (
    "PASS_CHARACTER_CONNECTED_SHOULDER_DISJOINT_THREE_FLIP_EXHAUSTIVE_"
    "NO_WORSE_REDUCTION"
)
HOLD_STATUS = (
    "HOLD_CHARACTER_CONNECTED_SHOULDER_DISJOINT_THREE_FLIP_FAMILY_EXHAUSTED_"
    "NO_STRICT_IMPROVEMENT__NONZERO_INTERSECTIONS_REMAIN"
)

THIRD_FLIP_EXTENSION_HEAD = "d07da5f3702491e71a00e06bf46030b70a17d9ee"
TWO_FLIP_SEARCH_HEAD = "c3735e8785348c1d23b4de048c82f505b6acf4f0"
GEOMETRY_STITCH_HEAD = "b65d73e514c23670204915bde8ce935a3b417574"
RIGGING_STITCH_REBIND_HEAD = "329c485f567faeeb79198c7b1ebc2974b3c3db60"


def _canonical_face_pair(pair):
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        raise ValueError("flip face pair must contain exactly two face indexes")
    values = tuple(sorted(int(value) for value in pair))
    if values[0] == values[1]:
        raise ValueError("flip face indexes must be distinct")
    return values


def _canonical_combo(combo):
    if not isinstance(combo, (tuple, list)) or len(combo) != 3:
        raise ValueError("three-flip combination must contain exactly three face pairs")
    normalized = tuple(sorted(_canonical_face_pair(pair) for pair in combo))
    if len(set(normalized)) != 3:
        raise ValueError("three-flip combination cannot repeat a face pair")
    flattened = [value for pair in normalized for value in pair]
    if len(set(flattened)) != 6:
        raise ValueError("three-flip combination must be pairwise face-disjoint")
    return normalized


def _combo_key(combo):
    combo = _canonical_combo(combo)
    return tuple(value for pair in combo for value in pair)


def _current_pair_set():
    return frozenset(_canonical_face_pair(pair) for pair in TARGET_FACE_PAIRS)


def _contains_current_pair(combo):
    combo = _canonical_combo(combo)
    return _current_pair_set().issubset(frozenset(combo))


def legal_disjoint_three_flip_combinations(side: str = "L"):
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    singles = sorted(
        {_canonical_face_pair(row["face_pair"]) for row in _single_flip_candidates(base)}
    )
    combos = []
    for combo in combinations(singles, 3):
        flattened = [value for pair in combo for value in pair]
        if len(set(flattened)) != 6:
            continue
        combos.append(_canonical_combo(combo))
    combos = sorted(set(combos), key=_combo_key)
    if not combos:
        raise ValueError("no legal face-disjoint three-flip combinations found")
    return combos


def build_three_flip_specimen(side: str, combo) -> dict:
    if side not in ("L", "R"):
        raise ValueError("side must be L or R")
    combo = _canonical_combo(combo)
    base = build_diagonal_mask_specimen(side, SELECTED_MASK)
    legal_pairs = {
        _canonical_face_pair(row["face_pair"]) for row in _single_flip_candidates(base)
    }
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
        raise ValueError("three-flip specimen failed Character-local topology preflight")
    if len(positions) != EXPECTED_VERTEX_COUNT or len(faces) != EXPECTED_TRIANGLE_COUNT:
        raise ValueError("three-flip specimen changed exact vertex/triangle budget")
    if groups != list(base["groups"]):
        raise ValueError("three-flip specimen changed face-group identity")

    changed_face_indexes = [
        index
        for index, (before, after) in enumerate(zip(base["faces"], faces))
        if list(before) != list(after)
    ]
    expected_changed = sorted(value for pair in combo for value in pair)
    if changed_face_indexes != expected_changed:
        raise ValueError("three-flip specimen changed unexpected face records")

    return {
        "schema": SCHEMA,
        "id": f"character-connected-shoulder-{side.lower()}-three-flip-search-001",
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


def _counts_for_specimens(specimens, pose_field, angles):
    return {
        side: {
            float(angle): _intersection_count(
                pose_field[side][float(angle)], specimens[side]
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


def _dense_candidate_row(combo, specimens, pose_field, current_counts):
    rows = []
    total = 0
    maximum = 0
    improved = 0
    equal = 0
    worse = 0
    aborted = False
    for side in ("L", "R"):
        for angle in SWEEP_ANGLES_DEG:
            angle = float(angle)
            observed = _intersection_count(pose_field[side][angle], specimens[side])
            control = int(current_counts[side][angle])
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
        "combo": [list(pair) for pair in combo],
        "contains_current_two_flip_control": _contains_current_pair(combo),
        "no_worse_every_dense_sample": not aborted,
        "aborted_on_first_worse_sample": aborted,
        "evaluated_sample_count": len(rows),
        "candidate_pair_sum": total if not aborted else None,
        "maximum_pair_count": maximum if not aborted else None,
        "strictly_better_samples": improved if not aborted else None,
        "equal_samples": equal if not aborted else None,
        "worse_samples": worse,
        "zero_intersection_samples": (
            sum(row["candidate_pair_count"] == 0 for row in rows) if not aborted else None
        ),
        "sample_rows": rows if not aborted else rows[-1:],
    }


def audit_disjoint_three_flip_search() -> dict:
    rigging = audit_stitch_edge_rigging_rebind()
    if rigging["status"] != RIGGING_STITCH_STATUS:
        raise ValueError("exact Rigging PR #12 prerequisite is not green")
    if int(rigging["dependencies"]["geometry_stitch_dense_pair_sum"]) != EXPECTED_CURRENT_DENSE_PAIR_SUM:
        raise ValueError("current Geometry PR #11 dense pair total drift")
    if int(rigging["dependencies"]["geometry_stitch_strictly_reduced_samples"]) != EXPECTED_CURRENT_STRICTLY_REDUCED_SAMPLES:
        raise ValueError("current Geometry PR #11 dense relation distribution drift")

    pose_field = _pose_field(rigging)
    current = {
        side: build_stitch_edge_repair_specimen(side) for side in ("L", "R")
    }
    current_counts = _counts_for_specimens(current, pose_field, SWEEP_ANGLES_DEG)
    current_flat = _flatten_counts(current_counts, SWEEP_ANGLES_DEG)
    current_total = sum(current_flat)
    if current_total != EXPECTED_CURRENT_DENSE_PAIR_SUM:
        raise ValueError("independent current-control dense pair sum drift")
    if any(value <= 0 for value in current_flat):
        raise ValueError("current control unexpectedly contains an intersection-free sampled pose")

    left_combos = legal_disjoint_three_flip_combinations("L")
    right_combos = legal_disjoint_three_flip_combinations("R")
    if left_combos != right_combos:
        raise ValueError("left/right legal face-disjoint three-flip family drift")

    previous_extensions = {
        _canonical_combo(tuple(TARGET_FACE_PAIRS) + (third_pair,))
        for third_pair in legal_third_flip_face_pairs("L")
    }
    current_pair_extensions = {combo for combo in left_combos if _contains_current_pair(combo)}
    if current_pair_extensions != previous_extensions:
        raise ValueError("PR #14 current-pair-plus-third family is not an exact subset")

    anchor_angles = tuple(float(value) for value in ANCHOR_ANGLES_DEG)
    current_anchor = {
        side: {angle: current_counts[side][angle] for angle in anchor_angles}
        for side in ("L", "R")
    }

    anchor_rows = []
    anchor_survivors = []
    structural_digest_pairs = set()
    for combo in left_combos:
        specimens = {side: build_three_flip_specimen(side, combo) for side in ("L", "R")}
        structural_digest_pairs.add(
            (specimens["L"]["topology_digest"], specimens["R"]["topology_digest"])
        )
        counts = _counts_for_specimens(specimens, pose_field, anchor_angles)
        deltas = [
            counts[side][angle] - current_anchor[side][angle]
            for side in ("L", "R")
            for angle in anchor_angles
        ]
        flat = _flatten_counts(counts, anchor_angles)
        row = {
            "combo": [list(pair) for pair in combo],
            "contains_current_two_flip_control": _contains_current_pair(combo),
            "anchor_counts": counts,
            "anchor_pair_sum": sum(flat),
            "maximum_anchor_pair_count": max(flat),
            "no_worse_every_anchor": max(deltas) <= 0,
            "strictly_better_anchor_samples": sum(value < 0 for value in deltas),
            "equal_anchor_samples": sum(value == 0 for value in deltas),
            "worse_anchor_samples": sum(value > 0 for value in deltas),
        }
        anchor_rows.append(row)
        if row["no_worse_every_anchor"]:
            anchor_survivors.append(combo)

    if len(structural_digest_pairs) != len(left_combos):
        raise ValueError("three-flip family unexpectedly contains duplicate topology identities")
    if not current_pair_extensions.issubset(set(anchor_survivors)):
        raise ValueError("a previously neutral PR #14 extension failed the exact anchor gate")

    dense_rows = []
    for combo in anchor_survivors:
        specimens = {side: build_three_flip_specimen(side, combo) for side in ("L", "R")}
        dense_rows.append(
            _dense_candidate_row(combo, specimens, pose_field, current_counts)
        )

    dense_survivors = [row for row in dense_rows if row["no_worse_every_dense_sample"]]
    dense_survivors.sort(
        key=lambda row: (
            int(row["candidate_pair_sum"]),
            int(row["maximum_pair_count"]),
            _combo_key(row["combo"]),
        )
    )
    strict_rows = [
        row
        for row in dense_survivors
        if int(row["candidate_pair_sum"]) < current_total
    ]

    selection = None
    if strict_rows:
        selected_row = strict_rows[0]
        selected_combo = _canonical_combo(selected_row["combo"])
        selected = {
            side: build_three_flip_specimen(side, selected_combo) for side in ("L", "R")
        }
        for side in ("L", "R"):
            base = build_diagonal_mask_specimen(side, SELECTED_MASK)
            if selected[side]["positions"] != [list(point) for point in base["positions"]]:
                raise ValueError("selected three-flip candidate moved vertex positions")
            if selected[side]["groups"] != list(base["groups"]):
                raise ValueError("selected three-flip candidate changed face-group identity")
        selection = {
            **selected_row,
            "strict_improvement": True,
            "all_sampled_poses_nonzero": selected_row["zero_intersection_samples"] == 0,
            "left_topology_digest": selected["L"]["topology_digest"],
            "right_topology_digest": selected["R"]["topology_digest"],
        }
        status = PASS_STATUS
        decision = "SELECT_NEW_SAME_POSITION_THREE_FLIP_TOPOLOGY__RIGGING_REBIND_REQUIRED"
    else:
        status = HOLD_STATUS
        decision = "HOLD_NO_NEW_TOPOLOGY_IDENTITY__CURRENT_TWO_FLIP_CONTROL_REMAINS"

    return {
        "schema": SCHEMA,
        "status": status,
        "dependencies": {
            "third_flip_extension_head": THIRD_FLIP_EXTENSION_HEAD,
            "two_flip_search_head": TWO_FLIP_SEARCH_HEAD,
            "geometry_stitch_head": GEOMETRY_STITCH_HEAD,
            "rigging_stitch_rebind_head": RIGGING_STITCH_REBIND_HEAD,
            "rigging_status": rigging["status"],
        },
        "search_scope": {
            "legal_single_flip_count": 22,
            "legal_face_disjoint_three_flip_combination_count": len(left_combos),
            "prior_current_pair_plus_third_extension_count": len(previous_extensions),
            "new_triples_not_containing_current_pair_count": len(left_combos) - len(previous_extensions),
            "unique_bilateral_topology_identity_count": len(structural_digest_pairs),
            "anchor_angles_deg": list(anchor_angles),
            "dense_angles_deg": [float(value) for value in SWEEP_ANGLES_DEG],
            "dense_sample_count": len(current_flat),
            "anchor_no_worse_survivor_count": len(anchor_survivors),
            "dense_no_worse_survivor_count": len(dense_survivors),
            "strict_dense_total_improvement_count": len(strict_rows),
            "face_disjoint_three_flip_family_exhausted": True,
            "arbitrary_three_edge_remeshing_exhausted": False,
            "four_plus_edge_remeshing_exhausted": False,
            "vertex_movement_exhausted": False,
            "source_form_movement_exhausted": False,
        },
        "current_control": {
            "combo": [list(pair) for pair in sorted(_current_pair_set())],
            "dense_pair_sum": current_total,
            "maximum_pair_count": max(current_flat),
            "all_sampled_poses_nonzero": all(value > 0 for value in current_flat),
        },
        "selection": selection,
        "decision": decision,
        "anchor_rows": anchor_rows,
        "dense_rows": dense_rows,
        "limitations": [
            "Exhausts only pairwise face-disjoint triples drawn from the exact 22 legal stitch-edge flips.",
            "Does not exhaust overlapping three-edge retessellation or any topology introducing/removing vertices or faces.",
            "Dense evidence is finite at one-degree samples from -40 through +40 degrees on both shoulders.",
            "Indexed-neighbour fold/contact, anatomy, shading, UVs, materials, animation, runtime and gameplay remain outside this observer.",
        ],
    }


def _write_obj(path: Path, specimen: dict):
    lines = [f"# {specimen['id']}"]
    for x, y, z in specimen["positions"]:
        lines.append(f"v {x:.12g} {y:.12g} {z:.12g}")
    for a, b, c in specimen["faces"]:
        lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_disjoint_three_flip_search_evidence(out_dir) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_disjoint_three_flip_search()
    (out / "audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for side in ("L", "R"):
        control = build_stitch_edge_repair_specimen(side)
        _write_obj(out / f"current-control-{side.lower()}.obj", control)

    if audit["selection"] is not None:
        combo = audit["selection"]["combo"]
        for side in ("L", "R"):
            selected = build_three_flip_specimen(side, combo)
            _write_obj(out / f"selected-{side.lower()}.obj", selected)

    summary = {
        "schema": SCHEMA,
        "status": audit["status"],
        "decision": audit["decision"],
        "legal_face_disjoint_three_flip_combination_count": audit["search_scope"][
            "legal_face_disjoint_three_flip_combination_count"
        ],
        "prior_current_pair_plus_third_extension_count": audit["search_scope"][
            "prior_current_pair_plus_third_extension_count"
        ],
        "new_triples_not_containing_current_pair_count": audit["search_scope"][
            "new_triples_not_containing_current_pair_count"
        ],
        "anchor_no_worse_survivor_count": audit["search_scope"][
            "anchor_no_worse_survivor_count"
        ],
        "dense_no_worse_survivor_count": audit["search_scope"][
            "dense_no_worse_survivor_count"
        ],
        "strict_dense_total_improvement_count": audit["search_scope"][
            "strict_dense_total_improvement_count"
        ],
        "current_dense_pair_sum": audit["current_control"]["dense_pair_sum"],
        "selection": audit["selection"],
        "limitations": audit["limitations"],
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return audit
