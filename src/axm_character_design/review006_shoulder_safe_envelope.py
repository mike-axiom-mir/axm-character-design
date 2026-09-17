"""Rigging-only structural motion envelope for the exact review-006 shoulder rebind.

The donor rebind proves the unchanged historical release profile structurally
survives all 162 sampled poses, but its nonadjacent-triangle observer finds the
first positive-side intersections at +37 degrees. This module does not rewrite
that evidence or retune the profile. It adds the smallest source/topology-bound
constraint: the structurally clear sampled envelope is -40 through +36 degrees.

This is not anatomy and it grants no Animation or Runtime range-of-motion
acceptance. +37 degrees is retained as an expected failing boundary witness.
"""
from __future__ import annotations

import json
from pathlib import Path

from .organic_form import write_obj
from .review006_connected_geometry import build_opening_repair
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    HISTORICAL_RIGGING_HEAD,
    PROFILE_SOURCE_HEAD,
    STATUS as DONOR_REBIND_STATUS,
    audit_review006_rigging_rebind,
)

SCHEMA = "axm.character-review006-rigging-structural-safe-envelope/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_MINUS40_PLUS36_STRUCTURAL_SAFE_ENVELOPE"
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_STRUCTURAL_SAFE_ENVELOPE"
DONOR_DISCOVERY_HEAD = "93e957eca152c45286924da44e4f085af2de69b2"
SAFE_MIN_DEG = -40.0
SAFE_MAX_DEG = 36.0
FIRST_UNSAFE_POSITIVE_DEG = 37.0
SAFE_ANGLES_DEG = tuple(float(value) for value in range(-40, 37))
REPRESENTATIVE_SAFE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 36.0)


def envelope_contract():
    return {
        "schema": SCHEMA,
        "constraint_id": "character-review006-opening-repair-structural-envelope-001",
        "donor_rebind": {
            "head": DONOR_DISCOVERY_HEAD,
            "status": DONOR_REBIND_STATUS,
            "source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "geometry_head": GEOMETRY_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
        },
        "constraint": {
            "safe_sampled_local_delta_deg": [SAFE_MIN_DEG, SAFE_MAX_DEG],
            "first_expected_positive_failure_witness_deg": FIRST_UNSAFE_POSITIVE_DEG,
            "profile_reauthored": False,
            "weights_reauthored": False,
            "joint_semantics_reauthored": False,
            "source_or_topology_rewritten": False,
        },
        "truth_boundary": {
            "finite_one_degree_sampling_only": True,
            "mathematical_continuity_proven": False,
            "anatomical_range_of_motion": False,
            "animation_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_contract(contract):
    if contract != envelope_contract():
        raise ValueError("review-006 structural envelope contract identity drift")


def _candidate_rows(audit, side):
    return {float(row["angle_deg"]): row for row in audit["results"][side]["candidate"]}


def audit_review006_structural_safe_envelope(contract=None):
    contract = contract or envelope_contract()
    _validate_contract(contract)
    donor = audit_review006_rigging_rebind()
    if donor["status"] != DONOR_REBIND_STATUS:
        raise ValueError("review-006 donor Rigging rebind is not structurally green")
    identity = donor["exact_identity"]
    if identity["review006_source_digest"] != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 donor source identity drift")
    if identity["review006_proof_mesh_digest"] != EXPECTED_REVIEW006_MESH_DIGEST:
        raise ValueError("review-006 donor proof-mesh identity drift")
    if identity["geometry_head"] != GEOMETRY_HEAD:
        raise ValueError("review-006 donor Geometry head drift")
    if identity["topology_digests"] != EXPECTED_TOPOLOGY_DIGESTS:
        raise ValueError("review-006 donor topology identity drift")
    if identity["profile_digest"] != EXPECTED_PROFILE_DIGEST:
        raise ValueError("review-006 donor Rigging profile identity drift")

    safe_rows = []
    first_unsafe_rows = []
    representative_rows = []
    boundary_control = []
    all_structural = True
    all_safe_intersection_free = True
    first_unsafe_confirmed = True

    for side in ("L", "R"):
        rows = _candidate_rows(donor, side)
        for angle in SAFE_ANGLES_DEG:
            row = rows[angle]
            safe_rows.append({
                "side": side,
                "angle_deg": angle,
                "pair_count": int(row["nonadjacent_intersection_pair_count"]),
                "status": row["status"],
            })
            all_structural &= row["status"] == "PASS"
            all_safe_intersection_free &= row["nonadjacent_intersection_pair_count"] == 0
            if angle in REPRESENTATIVE_SAFE_ANGLES_DEG:
                representative_rows.append({
                    "side": side,
                    "angle_deg": angle,
                    "pair_count": int(row["nonadjacent_intersection_pair_count"]),
                    "minimum_triangle_area_ratio": row["minimum_triangle_area_ratio"],
                    "maximum_triangle_area_ratio": row["maximum_triangle_area_ratio"],
                    "minimum_edge_length_ratio": row["minimum_edge_length_ratio"],
                    "maximum_edge_length_ratio": row["maximum_edge_length_ratio"],
                    "proximal_release_weight": row["proximal_release_weight"],
                })
        unsafe = rows[FIRST_UNSAFE_POSITIVE_DEG]
        witness = {
            "side": side,
            "angle_deg": FIRST_UNSAFE_POSITIVE_DEG,
            "pair_count": int(unsafe["nonadjacent_intersection_pair_count"]),
            "status": unsafe["nonadjacent_intersection_status"],
        }
        first_unsafe_rows.append(witness)
        first_unsafe_confirmed &= witness["pair_count"] > 0

        for angle in (SAFE_MIN_DEG, SAFE_MAX_DEG):
            row = rows[angle]
            boundary_control.append({
                "side": side,
                "angle_deg": angle,
                "nonworse_than_anchored_control": bool(row["nonworse_than_anchored_control"]),
                "strictly_improves_anchored_control": bool(row["strictly_improves_anchored_control"]),
            })

    boundary_nonworse = all(row["nonworse_than_anchored_control"] for row in boundary_control)
    boundary_strict = all(row["strictly_improves_anchored_control"] for row in boundary_control)
    safe_candidate_rows = [
        _candidate_rows(donor, side)[angle]
        for side in ("L", "R")
        for angle in SAFE_ANGLES_DEG
    ]
    metrics = {
        "minimum_triangle_area_ratio": min(row["minimum_triangle_area_ratio"] for row in safe_candidate_rows),
        "maximum_triangle_area_ratio": max(row["maximum_triangle_area_ratio"] for row in safe_candidate_rows),
        "minimum_edge_length_ratio": min(row["minimum_edge_length_ratio"] for row in safe_candidate_rows),
        "maximum_edge_length_ratio": max(row["maximum_edge_length_ratio"] for row in safe_candidate_rows),
        "maximum_fixed_socket_drift_m": max(row["fixed_socket_max_drift_m"] for row in safe_candidate_rows),
        "maximum_rigid_arm_radius_drift_m": max(row["rigid_arm_radius_max_drift_m"] for row in safe_candidate_rows),
    }
    pass_gate = (
        all_structural
        and all_safe_intersection_free
        and first_unsafe_confirmed
        and boundary_nonworse
        and boundary_strict
    )

    return {
        "schema": SCHEMA,
        "status": STATUS if pass_gate else FAIL_STATUS,
        "contract": contract,
        "donor_discovery": {
            "status": donor["status"],
            "full_diagnostic_pose_count": donor["sample_scope"]["candidate_pose_count"],
            "full_diagnostic_intersection_pair_sum": donor["nonadjacent_self_intersection"]["sample_pair_count_sum"],
            "full_diagnostic_nonzero_sample_count": donor["nonadjacent_self_intersection"]["nonzero_sample_count"],
            "full_diagnostic_max_pairs_one_sample": donor["nonadjacent_self_intersection"]["maximum_pairs_in_one_sample"],
        },
        "safe_envelope": {
            "range_deg": [SAFE_MIN_DEG, SAFE_MAX_DEG],
            "sampled_pose_count": len(safe_rows),
            "all_structural_pass": all_structural,
            "all_nonadjacent_intersection_free": all_safe_intersection_free,
            "representative_rows": representative_rows,
            "metrics": metrics,
        },
        "outside_envelope_witness": {
            "first_positive_sample_deg": FIRST_UNSAFE_POSITIVE_DEG,
            "rows": first_unsafe_rows,
            "confirmed_nonzero_on_both_sides": first_unsafe_confirmed,
            "acceptance": "HOLD_OUTSIDE_STRUCTURAL_SAFE_ENVELOPE",
        },
        "boundary_control": {
            "rows": boundary_control,
            "all_nonworse": boundary_nonworse,
            "all_strictly_improve": boundary_strict,
        },
        "gates": {
            "exact_source_topology_profile_identity": "PASS",
            "safe_envelope_154_sample_structural_gate": "PASS" if all_structural else "FAIL",
            "safe_envelope_154_sample_nonadjacent_intersection_gate": "PASS" if all_safe_intersection_free else "FAIL",
            "first_outside_envelope_positive_witness": "PASS_EXPECTED_FAILURE" if first_unsafe_confirmed else "FAIL_WITNESS_MISSING",
            "safe_boundary_vs_anchored_control": "PASS" if boundary_nonworse and boundary_strict else "FAIL",
            "continuous_motion": "NOT_PROVEN",
            "anatomical_range_of_motion": "NOT_CLAIMED",
            "animation_acceptance": "NOT_EVALUATED",
            "runtime_acceptance": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoffs": {
            "geometry": (
                "The exact opening_repair receiver is sampled clear throughout the constrained -40..+36 Rigging envelope; "
                "+37 remains the first retained positive nonadjacent-intersection witness. No topology rewrite was made."
            ),
            "animation": (
                "Treat -40..+36 only as a Rigging structural guard for this exact source/topology/profile. "
                "Do not infer clip timing, interpolation, playback or anatomy acceptance."
            ),
            "runtime_technical_art": (
                "No export/import/controller enforcement exists yet. Any receiver that uses this guard must bind the exact identities explicitly."
            ),
        },
        "truth_boundary": [
            "The historical weighting formula and joint semantics are unchanged; this successor adds only a measured structural motion constraint.",
            "The -40..+36 result is one-degree finite sampling, not mathematical continuous-motion proof.",
            "+37 degrees is a retained expected-failure witness, not permission to infer behavior at unsampled fractional angles.",
            "The nonadjacent observer excludes indexed-neighbour fold/contact and is not collision/gameplay proof.",
            "This structural guard is not an anatomical or Animation range-of-motion limit.",
            "No Animation, Runtime, Technical Art transport, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_structural_safe_envelope_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_structural_safe_envelope()
    (out / "review006-rigging-structural-safe-envelope-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "structural-safe-envelope-contract.json").write_text(
        json.dumps(envelope_contract(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    donor = audit_review006_rigging_rebind()
    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        rows = _candidate_rows(donor, side)
        for angle in REPRESENTATIVE_SAFE_ANGLES_DEG + (FIRST_UNSAFE_POSITIVE_DEG,):
            write_obj(
                {"vertices": rows[angle]["positions"], "faces": specimen["faces"], "regions": []},
                out / f"review006-{side.lower()}-{int(angle):+03d}deg.obj",
            )
    return audit
