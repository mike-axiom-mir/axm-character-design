"""Exact Rigging rebind for the review-006 Character opening-repair receiver.

This module preserves the historical angle-conditioned shoulder release profile
as a method identity, but binds it from scratch to the exact review-006 source
and Geometry PR #16 selected receiver. Historical accepted-E pose scores and
PASS states do not transfer.

The bounded observer evaluates every integer shoulder delta from -40 to +40
degrees on both sides and reports nonadjacent-triangle intersections at every
sample. Finite sampling is not mathematical continuous-motion proof and does
not grant Animation or Runtime acceptance.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .organic_form import canonical_digest, write_obj
from .review006_connected_geometry import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    STATUS as GEOMETRY_STATUS,
    audit_review006_geometry_rebind,
    build_connected_baseline,
    build_opening_repair,
)
from .review006_self_intersection import inspect_triangle_self_intersections
from .shoulder_pose_clearance_refinement import (
    VARIANT_ID as REVIEW006_ID,
    shoulder_pose_clearance_refinement_candidate,
)

SCHEMA = "axm.character-review006-opening-repair-rigging-rebind/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_ANGLE_CONDITIONED_RELEASE_REBOUND_TO_OPENING_REPAIR"
FAIL_STATUS = "FAIL_CHARACTER_REVIEW006_RIGGING_REBIND"

GEOMETRY_HEAD = "8ad006f91ebb9934d5df98702e4410c74a1e68ea"
GEOMETRY_PR = 16
SELECTED_STAGE = "opening_repair"
EXPECTED_TOPOLOGY_DIGESTS = {
    "L": "ea00241192b2af9113a28c4b723e871b440d4d37d32ebe5457c64f94b7650d5d",
    "R": "aeca6971c25e9786bcdea4f28103f69db642d3c360226b0705752229050b850a",
}

HISTORICAL_RIGGING_HEAD = "329c485f567faeeb79198c7b1ebc2974b3c3db60"
PROFILE_SOURCE_HEAD = "62a60ee6b930d13898203d37b0cc9dab6b13d99d"
DONOR_RIGGING_HEAD = "b0a03cbcb61e0f8deec37172d22ff1a7fff306c9"
DONOR_RIG_ID = "character-connected-shoulder-socket-rig-001"
SUCCESSOR_RIG_ID = "character-connected-shoulder-socket-rig-002-angle-conditioned-release"
RELEASE_PROFILE_ID = "angle-conditioned-proximal-release-power12-v1"
EXPECTED_DONOR_RIG_PLAN_DIGEST = "e1011be035f122cdbe86a8c8cf8846499ec0148d7b4adf05605d86bfac3e1f99"
EXPECTED_PROFILE_DIGEST = "49e59bfd7596619a2a19454ca395276097102047af673fc4219694e777a5a719"
RELEASE_POWER = 12.0
MAX_RELEASE_WEIGHT = 0.10
CONTROL_PROXIMAL_WEIGHT = 0.0
SWEEP_ANGLES_DEG = tuple(float(value) for value in range(-40, 41))
REPRESENTATIVE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 40.0)
DRIFT_TOLERANCE = 1e-9
METRIC_TOLERANCE = 1e-9


def _add(a, b):
    return tuple(float(a[i]) + float(b[i]) for i in range(3))


def _sub(a, b):
    return tuple(float(a[i]) - float(b[i]) for i in range(3))


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


def _rotate_about_axis(point, origin, axis, angle_deg):
    value = _sub(point, origin)
    direction = _unit(axis, "shoulder axis")
    angle = math.radians(float(angle_deg))
    c, s = math.cos(angle), math.sin(angle)
    rotated = _add(
        _add(_mul(value, c), _mul(_cross(direction, value), s)),
        _mul(direction, _dot(direction, value) * (1.0 - c)),
    )
    return _add(origin, rotated)


def _triangle_area(positions, face):
    a, b, c = (positions[index] for index in face)
    return 0.5 * _length(_cross(_sub(b, a), _sub(c, a)))


def _edge_ratios(before, after, faces):
    edges = set()
    for face in faces:
        for first, second in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edges.add(tuple(sorted((first, second))))
    ratios = []
    for first, second in edges:
        base = math.dist(before[first], before[second])
        posed = math.dist(after[first], after[second])
        if base > 1e-12:
            ratios.append(posed / base)
    if not ratios:
        raise ValueError("review-006 connected shoulder must contain measurable edges")
    return min(ratios), max(ratios)


def _mirror_position_set(positions):
    return {
        (round(-float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in positions
    }


def _position_set(positions):
    return {
        (round(float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in positions
    }


def release_weight(angle_deg: float) -> float:
    magnitude = min(abs(float(angle_deg)), 40.0)
    if magnitude == 0.0:
        return 0.0
    return MAX_RELEASE_WEIGHT * ((magnitude / 40.0) ** RELEASE_POWER)


def historical_successor_profile():
    """Return the exact historical weight-driver profile, not a reauthored variant."""
    return {
        "rig_id": SUCCESSOR_RIG_ID,
        "donor_rig_id": DONOR_RIG_ID,
        "donor_rigging_head": DONOR_RIGGING_HEAD,
        "donor_rig_plan_digest": EXPECTED_DONOR_RIG_PLAN_DIGEST,
        "release_profile_id": RELEASE_PROFILE_ID,
        "release_power": RELEASE_POWER,
        "max_release_weight": MAX_RELEASE_WEIGHT,
        "control_proximal_weight": CONTROL_PROXIMAL_WEIGHT,
        "driver": "absolute_local_shoulder_angle_deg",
        "verification_envelope_deg": [-40.0, 40.0],
        "formula": "max_release_weight * (abs(angle_deg) / 40.0) ** release_power",
        "endpoint_contract": {
            "zero_deg_weight": 0.0,
            "minus_40_deg_weight": MAX_RELEASE_WEIGHT,
            "plus_40_deg_weight": MAX_RELEASE_WEIGHT,
        },
    }


def rebind_contract():
    return {
        "schema": SCHEMA,
        "binding_id": "character-review006-opening-repair-rig-bind-001",
        "source": {
            "review006_id": REVIEW006_ID,
            "source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "adoption_state": "SELECTED_REVIEW_INPUT_NOT_CANON_SOURCE",
        },
        "geometry": {
            "head": GEOMETRY_HEAD,
            "pr": GEOMETRY_PR,
            "selected_stage": SELECTED_STAGE,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
        },
        "rig_method": {
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "successor_rig_id": SUCCESSOR_RIG_ID,
            "profile_id": RELEASE_PROFILE_ID,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "profile_reauthored": False,
            "joint_semantics": {
                "L": {"id": "shoulder-L", "landmark": "shoulder_L", "axis": [0.0, -1.0, 0.0]},
                "R": {"id": "shoulder-R", "landmark": "shoulder_R", "axis": [0.0, 1.0, 0.0]},
            },
            "weight_semantics": {
                "ribcage_and_seam_child_weight": 0.0,
                "proximal_ring_child_weight": "ANGLE_CONDITIONED_PROFILE",
                "distal_ring_and_cap_child_weight": 1.0,
                "control_proximal_ring_child_weight": CONTROL_PROXIMAL_WEIGHT,
            },
        },
        "verification": {
            "sweep_angles_deg": list(SWEEP_ANGLES_DEG),
            "representative_angles_deg": list(REPRESENTATIVE_ANGLES_DEG),
        },
        "truth_boundary": {
            "historical_pass_transfer": False,
            "source_or_geometry_rewritten": False,
            "rig_profile_reauthored": False,
            "finite_sampled_deformation_only": True,
            "continuous_motion_proven": False,
            "animation_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
        },
    }


def _validate_profile(profile):
    if canonical_digest(profile) != EXPECTED_PROFILE_DIGEST:
        raise ValueError("historical angle-conditioned Rigging profile identity drift")


def _validate_contract(contract):
    if contract != rebind_contract():
        raise ValueError("review-006 Rigging rebind contract identity drift")
    _validate_profile(historical_successor_profile())


def _reindexed_layout(side, opening):
    baseline = build_connected_baseline(side)
    removed = opening["construction"]["unused_vertex_prune"]["removed_original_vertex_indices"]
    if len(removed) != 1:
        raise ValueError("review-006 opening repair must retain exactly one unused-vertex prune")
    rib_count = len(baseline["positions"]) - 31
    if rib_count <= 0 or len(baseline["positions"]) != rib_count + 31:
        raise ValueError("review-006 baseline layout budget drift")
    used = [index for index in range(len(baseline["positions"])) if index not in set(removed)]
    if [baseline["positions"][index] for index in used] != opening["positions"]:
        raise ValueError("opening repair compaction moved or reordered retained positions")
    mapping = {old: new for new, old in enumerate(used)}

    old_groups = {
        "ribcage": list(range(0, rib_count)),
        "seam": list(range(rib_count, rib_count + 10)),
        "proximal": list(range(rib_count + 10, rib_count + 20)),
        "distal": list(range(rib_count + 20, rib_count + 30)),
        "distal_cap": [rib_count + 30],
    }
    groups = {
        name: [mapping[index] for index in indexes if index in mapping]
        for name, indexes in old_groups.items()
    }
    expected_counts = {"ribcage": rib_count - 1, "seam": 10, "proximal": 10, "distal": 10, "distal_cap": 1}
    if {name: len(indexes) for name, indexes in groups.items()} != expected_counts:
        raise ValueError("review-006 opening repair Rigging layout count drift")
    if sorted(index for indexes in groups.values() for index in indexes) != list(range(len(opening["positions"]))):
        raise ValueError("review-006 opening repair Rigging layout coverage drift")
    return {"groups": groups, "removed_original_vertex_indices": removed, "ribcage_baseline_count": rib_count}


def _weights(layout, proximal_weight, vertex_count):
    values = [None] * vertex_count
    for name in ("ribcage", "seam"):
        for index in layout["groups"][name]:
            values[index] = 0.0
    for index in layout["groups"]["proximal"]:
        values[index] = float(proximal_weight)
    for name in ("distal", "distal_cap"):
        for index in layout["groups"][name]:
            values[index] = 1.0
    if any(value is None for value in values):
        raise ValueError("review-006 Rigging weights do not cover the selected receiver")
    return values


def _pose(specimen, origin, axis, angle_deg, child_weights):
    before = [tuple(float(value) for value in point) for point in specimen["positions"]]
    faces = specimen["faces"]
    source_areas = [_triangle_area(before, face) for face in faces]
    if min(source_areas) <= 1e-12:
        raise ValueError("review-006 selected receiver contains degenerate neutral triangle")

    after = []
    fixed_drift = 0.0
    rigid_radius_drift = 0.0
    for point, child_weight in zip(before, child_weights):
        rotated = _rotate_about_axis(point, origin, axis, angle_deg)
        current = _add(point, _mul(_sub(rotated, point), child_weight))
        after.append(current)
        if child_weight <= 1e-12:
            fixed_drift = max(fixed_drift, math.dist(point, current))
        if child_weight >= 1.0 - 1e-12:
            rigid_radius_drift = max(
                rigid_radius_drift,
                abs(math.dist(point, origin) - math.dist(current, origin)),
            )

    posed_areas = [_triangle_area(after, face) for face in faces]
    collapsed = sum(area <= 1e-12 for area in posed_areas)
    area_ratios = [posed / neutral for neutral, posed in zip(source_areas, posed_areas)]
    min_edge, max_edge = _edge_ratios(before, after, faces)
    neutral_drift = max(math.dist(a, b) for a, b in zip(before, after)) if angle_deg == 0 else None
    return {
        "angle_deg": float(angle_deg),
        "positions": after,
        "finite": all(math.isfinite(value) for point in after for value in point),
        "collapsed_triangles": collapsed,
        "minimum_triangle_area_ratio": min(area_ratios),
        "maximum_triangle_area_ratio": max(area_ratios),
        "minimum_edge_length_ratio": min_edge,
        "maximum_edge_length_ratio": max_edge,
        "fixed_socket_max_drift_m": fixed_drift,
        "rigid_arm_radius_max_drift_m": rigid_radius_drift,
        "neutral_max_vertex_drift_m": neutral_drift,
    }


def _pose_pass(row):
    return (
        row["finite"]
        and row["collapsed_triangles"] == 0
        and row["fixed_socket_max_drift_m"] <= DRIFT_TOLERANCE
        and row["rigid_arm_radius_max_drift_m"] <= DRIFT_TOLERANCE
        and (row["neutral_max_vertex_drift_m"] is None or row["neutral_max_vertex_drift_m"] <= DRIFT_TOLERANCE)
    )


def _nonworse(candidate, control):
    return (
        candidate["minimum_triangle_area_ratio"] + METRIC_TOLERANCE >= control["minimum_triangle_area_ratio"]
        and candidate["maximum_triangle_area_ratio"] <= control["maximum_triangle_area_ratio"] + METRIC_TOLERANCE
        and candidate["minimum_edge_length_ratio"] + METRIC_TOLERANCE >= control["minimum_edge_length_ratio"]
        and candidate["maximum_edge_length_ratio"] <= control["maximum_edge_length_ratio"] + METRIC_TOLERANCE
    )


def _strictly_improves(candidate, control):
    return _nonworse(candidate, control) and (
        candidate["minimum_triangle_area_ratio"] > control["minimum_triangle_area_ratio"] + METRIC_TOLERANCE
        or candidate["maximum_triangle_area_ratio"] + METRIC_TOLERANCE < control["maximum_triangle_area_ratio"]
        or candidate["minimum_edge_length_ratio"] > control["minimum_edge_length_ratio"] + METRIC_TOLERANCE
        or candidate["maximum_edge_length_ratio"] + METRIC_TOLERANCE < control["maximum_edge_length_ratio"]
    )


def _specimen_identity(side, specimen, geometry):
    observed = canonical_digest({"positions": specimen["positions"], "faces": specimen["faces"]})
    expected = EXPECTED_TOPOLOGY_DIGESTS[side]
    selected_expected = geometry["selection"][f"{'left' if side == 'L' else 'right'}_topology_digest"]
    if observed != expected or selected_expected != expected:
        raise ValueError(f"review-006 selected Geometry topology identity drift for {side}")
    if specimen["stage"] != SELECTED_STAGE:
        raise ValueError("review-006 Rigging bound wrong Geometry stage")
    if not specimen["local_preflight"]["status"].startswith("PASS_"):
        raise ValueError("review-006 selected Geometry preflight is not green")
    return observed


def audit_review006_rigging_rebind(contract=None):
    contract = contract or rebind_contract()
    _validate_contract(contract)
    geometry = audit_review006_geometry_rebind()
    if geometry["status"] != GEOMETRY_STATUS:
        raise ValueError("review-006 Geometry prerequisite status drift")
    if geometry["selection"]["selected_stage"] != SELECTED_STAGE:
        raise ValueError("review-006 Geometry selected receiver changed")
    if not geometry["selection"]["neutral_intersection_free"]:
        raise ValueError("review-006 selected neutral receiver lost its Geometry intersection gate")

    source = shoulder_pose_clearance_refinement_candidate()
    if source.get("study_id") != REVIEW006_ID:
        raise ValueError("review-006 source ID drift")
    if canonical_digest(source) != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 exact source digest drift")

    profile = historical_successor_profile()
    _validate_profile(profile)
    results = {}
    intersection_rows = []
    structural_pass = True
    bilateral_pass = True
    boundary_control_rows = []

    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        topology_digest = _specimen_identity(side, specimen, geometry)
        layout = _reindexed_layout(side, specimen)
        joint = contract["rig_method"]["joint_semantics"][side]
        origin = tuple(float(value) for value in source["landmarks"][joint["landmark"]])
        axis = tuple(float(value) for value in joint["axis"])
        control_weights = _weights(layout, CONTROL_PROXIMAL_WEIGHT, len(specimen["positions"]))
        candidate_rows = []
        control_rows = []

        for angle in SWEEP_ANGLES_DEG:
            weight = release_weight(angle)
            candidate = _pose(
                specimen,
                origin,
                axis,
                angle,
                _weights(layout, weight, len(specimen["positions"])),
            )
            control = _pose(specimen, origin, axis, angle, control_weights)
            candidate["proximal_release_weight"] = weight
            candidate["status"] = "PASS" if _pose_pass(candidate) else "FAIL"
            control["status"] = "PASS" if _pose_pass(control) else "FAIL"
            candidate["nonworse_than_anchored_control"] = _nonworse(candidate, control)
            candidate["strictly_improves_anchored_control"] = (
                False if angle == 0.0 else _strictly_improves(candidate, control)
            )
            report = inspect_triangle_self_intersections(
                candidate["positions"], specimen["indices"], max_examples=12
            )
            candidate["nonadjacent_intersection_pair_count"] = int(report["self_intersection_pair_count"])
            candidate["nonadjacent_intersection_status"] = report["status"]
            intersection_rows.append({
                "side": side,
                "angle_deg": float(angle),
                "pair_count": int(report["self_intersection_pair_count"]),
                "status": report["status"],
                "examples": report["examples"] if angle in REPRESENTATIVE_ANGLES_DEG else [],
            })
            structural_pass &= candidate["status"] == "PASS" and control["status"] == "PASS"
            if angle in (-40.0, 40.0):
                boundary_control_rows.append({
                    "side": side,
                    "angle_deg": float(angle),
                    "nonworse": candidate["nonworse_than_anchored_control"],
                    "strictly_improves": candidate["strictly_improves_anchored_control"],
                })
            candidate_rows.append(candidate)
            control_rows.append(control)

        results[side] = {
            "topology_digest": topology_digest,
            "layout": layout,
            "candidate": candidate_rows,
            "anchored_proximal_control": control_rows,
        }

    for index, angle in enumerate(SWEEP_ANGLES_DEG):
        same = _mirror_position_set(results["L"]["candidate"][index]["positions"]) == _position_set(
            results["R"]["candidate"][index]["positions"]
        )
        bilateral_pass &= same
        structural_pass &= same
        results["L"]["candidate"][index]["bilateral_mirrored_position_set"] = same
        results["R"]["candidate"][index]["bilateral_mirrored_position_set"] = same

    representative = [row for row in intersection_rows if row["angle_deg"] in REPRESENTATIVE_ANGLES_DEG]
    neutral_rows = [row for row in intersection_rows if row["angle_deg"] == 0.0]
    neutral_zero = all(row["pair_count"] == 0 for row in neutral_rows) and len(neutral_rows) == 2
    structural_pass &= neutral_zero

    pair_sum = sum(row["pair_count"] for row in intersection_rows)
    max_pairs = max(row["pair_count"] for row in intersection_rows)
    nonzero_samples = sum(row["pair_count"] > 0 for row in intersection_rows)
    all_sampled_intersection_free = nonzero_samples == 0
    boundary_nonworse = all(row["nonworse"] for row in boundary_control_rows)
    boundary_strict = all(row["strictly_improves"] for row in boundary_control_rows)

    all_candidates = [row for side in ("L", "R") for row in results[side]["candidate"]]
    metrics = {
        "minimum_triangle_area_ratio": min(row["minimum_triangle_area_ratio"] for row in all_candidates),
        "maximum_triangle_area_ratio": max(row["maximum_triangle_area_ratio"] for row in all_candidates),
        "minimum_edge_length_ratio": min(row["minimum_edge_length_ratio"] for row in all_candidates),
        "maximum_edge_length_ratio": max(row["maximum_edge_length_ratio"] for row in all_candidates),
        "maximum_fixed_socket_drift_m": max(row["fixed_socket_max_drift_m"] for row in all_candidates),
        "maximum_rigid_arm_radius_drift_m": max(row["rigid_arm_radius_max_drift_m"] for row in all_candidates),
    }

    return {
        "schema": SCHEMA,
        "status": STATUS if structural_pass else FAIL_STATUS,
        "contract": contract,
        "historical_successor_profile": profile,
        "exact_identity": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "geometry_head": GEOMETRY_HEAD,
            "selected_stage": SELECTED_STAGE,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "historical_rigging_head": HISTORICAL_RIGGING_HEAD,
            "profile_source_head": PROFILE_SOURCE_HEAD,
            "profile_digest": canonical_digest(profile),
        },
        "sample_scope": {
            "angles_per_side": len(SWEEP_ANGLES_DEG),
            "candidate_pose_count": len(SWEEP_ANGLES_DEG) * 2,
            "angle_range_deg": [-40.0, 40.0],
            "step_deg": 1.0,
            "representative_angles_deg": list(REPRESENTATIVE_ANGLES_DEG),
            "continuous_interpolation_proven": False,
        },
        "metrics": metrics,
        "boundary_control": {
            "rows": boundary_control_rows,
            "all_nonworse": boundary_nonworse,
            "all_strictly_improve": boundary_strict,
            "meaning": "measured comparison only; the historical profile was not tuned on review-006",
        },
        "nonadjacent_self_intersection": {
            "all_sampled_intersection_free": all_sampled_intersection_free,
            "sample_pair_count_sum": pair_sum,
            "maximum_pairs_in_one_sample": max_pairs,
            "nonzero_sample_count": nonzero_samples,
            "neutral_bilateral_zero": neutral_zero,
            "representative_rows": representative,
            "acceptance": (
                "PASS_FINITE_ONE_DEGREE_SAMPLED_NONADJACENT_INTERSECTION_FREE"
                if all_sampled_intersection_free
                else "HOLD_NONZERO_DEFORMED_NONADJACENT_INTERSECTIONS"
            ),
        },
        "results": results,
        "gates": {
            "exact_review006_source_identity": "PASS",
            "exact_geometry_head_and_selected_topology": "PASS",
            "historical_rig_profile_digest": "PASS",
            "all_162_structural_samples": "PASS" if structural_pass else "FAIL",
            "bilateral_mirror": "PASS" if bilateral_pass else "FAIL",
            "neutral_geometry_intersection_reproduction": "PASS" if neutral_zero else "FAIL",
            "boundary_vs_anchored_control": (
                "PASS_NONWORSE_AND_STRICT_IMPROVEMENT" if boundary_nonworse and boundary_strict
                else "MEASURED_NO_ACCEPTANCE_TRANSFER"
            ),
            "animation_acceptance": "NOT_EVALUATED",
            "runtime_acceptance": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoffs": {
            "geometry": (
                "Exact opening_repair receiver remained identity-stable through the Rigging rebind. "
                "Any nonzero deformed intersection sample remains a measured Geometry/Rigging boundary, not a silent topology rewrite."
            ),
            "organic_form": (
                "Review-006 source identity was not rewritten. Keep Organic frozen unless this exact rebind returns a source-owned defect."
            ),
            "animation": (
                "No clip, timing, interpolation or playback acceptance transfers. Animation must bind explicitly to this exact Rigging successor before use."
            ),
            "runtime_technical_art": (
                "No exported skeleton/skin, importer, controller, target-engine or performance acceptance is established."
            ),
        },
        "truth_boundary": [
            "This is a source/receiver Rigging rebind of the exact historical weighting profile, not a new weighting design.",
            "All 162 integer-degree poses are finite samples; they do not prove mathematical continuity between samples.",
            "The nonadjacent-triangle observer excludes indexed-neighbour fold/contact and is not a gameplay collision proof.",
            "Review-006 remains a selected review input rather than silently adopted CANON source.",
            "No Animation timing/interpolation/playback, Technical Art export, Runtime/controller/performance, final visual, CANON, production-readiness, game-readiness or Rigging-mastery claim is made.",
        ],
    }


def build_review006_rigging_rebind_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_rigging_rebind()
    (out / "review006-opening-repair-rigging-rebind-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "rebind-contract.json").write_text(
        json.dumps(rebind_contract(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "historical-rig-profile.json").write_text(
        json.dumps(historical_successor_profile(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    by_side_angle = {
        side: {row["angle_deg"]: row for row in audit["results"][side]["candidate"]}
        for side in ("L", "R")
    }
    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        for angle in REPRESENTATIVE_ANGLES_DEG:
            row = by_side_angle[side][angle]
            write_obj(
                {"vertices": row["positions"], "faces": specimen["faces"], "regions": []},
                out / f"review006-{side.lower()}-{int(angle):+03d}deg.obj",
            )
    return audit
