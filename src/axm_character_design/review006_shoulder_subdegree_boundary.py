"""Rigging-only sub-degree boundary probe for the exact review-006 shoulder rebind.

The retained one-degree evidence proves the exact review-006 opening-repair receiver
is structurally clear from -40 through +36 degrees and first reports a nonadjacent
intersection at +37 degrees. This observer refines only that already-exposed
positive boundary with 0.05-degree samples. It does not retune weights, move
source geometry, change topology, or claim continuous-motion / Animation /
Runtime acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path

from .organic_form import canonical_digest, write_obj
from .review006_connected_geometry import build_opening_repair
from .review006_self_intersection import inspect_triangle_self_intersections
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    HISTORICAL_RIGGING_HEAD,
    PROFILE_SOURCE_HEAD,
    _mirror_position_set,
    _pose,
    _pose_pass,
    _position_set,
    _reindexed_layout,
    _weights,
    historical_successor_profile,
    rebind_contract,
    release_weight,
)
from .review006_shoulder_safe_envelope import (
    STATUS as INTEGER_SAFE_ENVELOPE_STATUS,
    audit_review006_structural_safe_envelope,
)
from .shoulder_pose_clearance_refinement import (
    VARIANT_ID as REVIEW006_ID,
    shoulder_pose_clearance_refinement_candidate,
)

SCHEMA = "axm.character-review006-positive-subdegree-boundary/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_POSITIVE_SUBDEGREE_BOUNDARY_CONSTRAINT_005_DEG"
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_POSITIVE_SUBDEGREE_BOUNDARY_CONSTRAINT"
START_DEG = 36.0
END_DEG = 37.0
STEP_DEG = 0.05
SAMPLE_COUNT_PER_SIDE = int(round((END_DEG - START_DEG) / STEP_DEG)) + 1
SUBDEGREE_ANGLES_DEG = tuple(
    round(START_DEG + index * STEP_DEG, 10)
    for index in range(SAMPLE_COUNT_PER_SIDE)
)


def boundary_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-positive-subdegree-boundary-005deg-001",
        "source": {
            "review006_id": REVIEW006_ID,
            "source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
        },
        "geometry": {
            "head": GEOMETRY_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "selected_stage": "opening_repair",
        },
        "rig": {
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "profile_reauthored": False,
            "weights_reauthored": False,
            "joint_semantics_reauthored": False,
        },
        "sampling": {
            "start_deg": START_DEG,
            "end_deg": END_DEG,
            "step_deg": STEP_DEG,
            "samples_per_side": SAMPLE_COUNT_PER_SIDE,
            "angles_deg": list(SUBDEGREE_ANGLES_DEG),
        },
        "truth_boundary": {
            "finite_subdegree_sampling_only": True,
            "mathematical_continuity_proven": False,
            "anatomical_range_of_motion": False,
            "animation_acceptance": False,
            "runtime_acceptance": False,
            "technical_art_transport_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_contract(contract):
    if contract != boundary_contract():
        raise ValueError("review-006 subdegree boundary contract identity drift")


def _validate_exact_identity():
    integer_audit = audit_review006_structural_safe_envelope()
    if integer_audit["status"] != INTEGER_SAFE_ENVELOPE_STATUS:
        raise ValueError("review-006 integer safe-envelope prerequisite is not green")

    source = shoulder_pose_clearance_refinement_candidate()
    if source.get("study_id") != REVIEW006_ID:
        raise ValueError("review-006 source ID drift")
    if canonical_digest(source) != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 source digest drift")

    profile = historical_successor_profile()
    if canonical_digest(profile) != EXPECTED_PROFILE_DIGEST:
        raise ValueError("review-006 Rigging profile digest drift")

    return integer_audit, source


def _sample_side(side, source):
    specimen = build_opening_repair(side)
    observed_topology = canonical_digest({
        "positions": specimen["positions"],
        "faces": specimen["faces"],
    })
    if observed_topology != EXPECTED_TOPOLOGY_DIGESTS[side]:
        raise ValueError(f"review-006 selected Geometry topology identity drift for {side}")

    layout = _reindexed_layout(side, specimen)
    rig_contract = rebind_contract()
    joint = rig_contract["rig_method"]["joint_semantics"][side]
    origin = tuple(float(value) for value in source["landmarks"][joint["landmark"]])
    axis = tuple(float(value) for value in joint["axis"])

    rows = []
    for angle in SUBDEGREE_ANGLES_DEG:
        weight = release_weight(angle)
        posed = _pose(
            specimen,
            origin,
            axis,
            angle,
            _weights(layout, weight, len(specimen["positions"])),
        )
        report = inspect_triangle_self_intersections(
            posed["positions"], specimen["indices"], max_examples=12
        )
        rows.append({
            "side": side,
            "angle_deg": float(angle),
            "proximal_release_weight": weight,
            "structural_status": "PASS" if _pose_pass(posed) else "FAIL",
            "nonadjacent_intersection_status": report["status"],
            "nonadjacent_intersection_pair_count": int(report["self_intersection_pair_count"]),
            "intersection_examples": report["examples"],
            "minimum_triangle_area_ratio": posed["minimum_triangle_area_ratio"],
            "maximum_triangle_area_ratio": posed["maximum_triangle_area_ratio"],
            "minimum_edge_length_ratio": posed["minimum_edge_length_ratio"],
            "maximum_edge_length_ratio": posed["maximum_edge_length_ratio"],
            "fixed_socket_max_drift_m": posed["fixed_socket_max_drift_m"],
            "rigid_arm_radius_max_drift_m": posed["rigid_arm_radius_max_drift_m"],
            "positions": posed["positions"],
        })
    return specimen, rows


def audit_review006_positive_subdegree_boundary(contract=None):
    contract = contract or boundary_contract()
    _validate_contract(contract)
    integer_audit, source = _validate_exact_identity()

    specimens = {}
    rows_by_side = {}
    for side in ("L", "R"):
        specimen, rows = _sample_side(side, source)
        specimens[side] = specimen
        rows_by_side[side] = rows

    all_rows = [row for side in ("L", "R") for row in rows_by_side[side]]
    all_structural = all(row["structural_status"] == "PASS" for row in all_rows)

    bilateral_pose_mirror = True
    for left, right in zip(rows_by_side["L"], rows_by_side["R"]):
        same = _mirror_position_set(left["positions"]) == _position_set(right["positions"])
        left["bilateral_mirrored_position_set"] = same
        right["bilateral_mirrored_position_set"] = same
        bilateral_pose_mirror &= same

    boundaries = {}
    for side in ("L", "R"):
        rows = rows_by_side[side]
        clear = [row for row in rows if row["nonadjacent_intersection_pair_count"] == 0]
        failing = [row for row in rows if row["nonadjacent_intersection_pair_count"] > 0]
        if not clear or not failing:
            boundaries[side] = {
                "last_sampled_clear_deg": None,
                "first_sampled_failure_deg": None,
                "transition_bracket_width_deg": None,
            }
            continue
        last_clear = max(row["angle_deg"] for row in clear)
        first_failure = min(row["angle_deg"] for row in failing)
        boundaries[side] = {
            "last_sampled_clear_deg": last_clear,
            "first_sampled_failure_deg": first_failure,
            "transition_bracket_width_deg": first_failure - last_clear,
            "last_clear_pair_count": next(
                row["nonadjacent_intersection_pair_count"] for row in rows
                if row["angle_deg"] == last_clear
            ),
            "first_failure_pair_count": next(
                row["nonadjacent_intersection_pair_count"] for row in rows
                if row["angle_deg"] == first_failure
            ),
        }

    endpoints_preserved = all(
        rows_by_side[side][0]["angle_deg"] == START_DEG
        and rows_by_side[side][0]["nonadjacent_intersection_pair_count"] == 0
        and rows_by_side[side][-1]["angle_deg"] == END_DEG
        and rows_by_side[side][-1]["nonadjacent_intersection_pair_count"] > 0
        for side in ("L", "R")
    )
    bilateral_boundary = (
        boundaries["L"]["last_sampled_clear_deg"] is not None
        and boundaries["L"] == boundaries["R"]
    )
    bracket_bounded = bilateral_boundary and (
        0.0 < boundaries["L"]["transition_bracket_width_deg"] <= STEP_DEG + 1e-12
    )

    last_clear = boundaries["L"]["last_sampled_clear_deg"] if bilateral_boundary else None
    first_failure = boundaries["L"]["first_sampled_failure_deg"] if bilateral_boundary else None

    false_guard_rejected = False
    if bilateral_boundary:
        false_guard_rejected = all(
            any(
                row["angle_deg"] <= first_failure
                and row["nonadjacent_intersection_pair_count"] > 0
                for row in rows_by_side[side]
            )
            for side in ("L", "R")
        )

    representative_angles = [START_DEG]
    if last_clear is not None and last_clear not in representative_angles:
        representative_angles.append(last_clear)
    if first_failure is not None and first_failure not in representative_angles:
        representative_angles.append(first_failure)
    if END_DEG not in representative_angles:
        representative_angles.append(END_DEG)
    representative_angles = sorted(representative_angles)

    representative_rows = [
        {
            key: value
            for key, value in row.items()
            if key != "positions"
        }
        for side in ("L", "R")
        for row in rows_by_side[side]
        if row["angle_deg"] in representative_angles
    ]

    pass_gate = (
        all_structural
        and bilateral_pose_mirror
        and endpoints_preserved
        and bilateral_boundary
        and bracket_bounded
        and false_guard_rejected
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if pass_gate else FAIL_STATUS,
        "contract": contract,
        "exact_identity": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "geometry_head": GEOMETRY_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
        },
        "integer_prerequisite": {
            "status": integer_audit["status"],
            "safe_range_deg": integer_audit["safe_envelope"]["range_deg"],
            "first_positive_failure_sample_deg": integer_audit["outside_envelope_witness"]["first_positive_sample_deg"],
        },
        "subdegree_probe": {
            "range_deg": [START_DEG, END_DEG],
            "step_deg": STEP_DEG,
            "samples_per_side": SAMPLE_COUNT_PER_SIDE,
            "posed_sample_count": len(all_rows),
            "all_structural_pass": all_structural,
            "bilateral_pose_mirror": bilateral_pose_mirror,
            "boundaries": boundaries,
            "representative_angles_deg": representative_angles,
            "representative_rows": representative_rows,
            "rows": {
                side: [
                    {key: value for key, value in row.items() if key != "positions"}
                    for row in rows_by_side[side]
                ]
                for side in ("L", "R")
            },
        },
        "sampled_guard": {
            "existing_integer_guard_deg": [-40.0, 36.0],
            "refined_positive_sampled_guard_max_deg": last_clear,
            "first_sampled_positive_failure_deg": first_failure,
            "meaning": (
                "Finite evidence only: integer samples remain proven through +36 and the positive boundary is refined "
                "with exact 0.05-degree samples. Unsampled real-valued angles are not claimed clear."
            ),
        },
        "negative_control": {
            "mutation": "extend sampled guard to the first measured failing sample",
            "rejected": false_guard_rejected,
            "expected": "REJECT_GUARD_CONTAINING_NONZERO_INTERSECTION_SAMPLE",
        },
        "gates": {
            "exact_source_topology_profile_identity": "PASS",
            "all_subdegree_structural_samples": "PASS" if all_structural else "FAIL",
            "bilateral_pose_mirror": "PASS" if bilateral_pose_mirror else "FAIL",
            "integer_endpoint_reproduction": "PASS" if endpoints_preserved else "FAIL",
            "bilateral_boundary_match": "PASS" if bilateral_boundary else "FAIL",
            "transition_bracket_at_most_005deg": "PASS" if bracket_bounded else "FAIL",
            "guard_negative_control": "PASS_EXPECTED_REJECTION" if false_guard_rejected else "FAIL",
            "continuous_motion": "NOT_PROVEN",
            "anatomical_range_of_motion": "NOT_CLAIMED",
            "animation_acceptance": "NOT_EVALUATED",
            "runtime_acceptance": "NOT_EVALUATED",
            "technical_art_transport_acceptance": "NOT_EVALUATED",
            "visual_acceptance": "NOT_EVALUATED",
        },
        "handoffs": {
            "geometry": (
                "No topology rewrite requested. The exact opening_repair receiver is preserved while Rigging only refines "
                "the measured positive deformation boundary."
            ),
            "visual_qa_art": (
                "Use the retained last-clear / first-failing subdegree witnesses for visual boundary review. "
                "Structural sampling does not grant appearance acceptance."
            ),
            "animation": (
                "The refined sampled guard is not anatomy or a motion range. Animation must independently choose and "
                "prove any clip/range while binding this exact Rigging identity."
            ),
            "runtime_technical_art": (
                "No skeleton/skin export, importer, controller enforcement, target-engine playback or performance acceptance is implied."
            ),
        },
        "truth_boundary": [
            "Source geometry, Geometry topology, joint semantics and the historical angle-conditioned weight profile are unchanged.",
            "The 0.05-degree probe is finite sampled evidence only and is not mathematical continuous-motion proof.",
            "The sampled guard must stop before the first measured failing sample; the negative control rejects silent over-extension.",
            "The nonadjacent observer excludes indexed-neighbour fold/contact and is not gameplay collision proof.",
            "No Animation, Technical Art, Runtime, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
        "_specimens": specimens,
        "_rows_with_positions": rows_by_side,
    }


def build_review006_positive_subdegree_boundary_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_positive_subdegree_boundary()

    serializable = {
        key: value for key, value in audit.items()
        if not key.startswith("_")
    }
    (out / "review006-positive-subdegree-boundary-audit.json").write_text(
        json.dumps(serializable, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "positive-subdegree-boundary-contract.json").write_text(
        json.dumps(boundary_contract(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    representative = audit["subdegree_probe"]["representative_angles_deg"]
    rows_by_side = audit["_rows_with_positions"]
    specimens = audit["_specimens"]
    for side in ("L", "R"):
        row_map = {row["angle_deg"]: row for row in rows_by_side[side]}
        for angle in representative:
            row = row_map[angle]
            token = f"{angle:+06.2f}".replace("+", "p").replace("-", "m").replace(".", "p")
            write_obj(
                {"vertices": row["positions"], "faces": specimens[side]["faces"], "regions": []},
                out / f"review006-{side.lower()}-{token}deg.obj",
            )
    return serializable
