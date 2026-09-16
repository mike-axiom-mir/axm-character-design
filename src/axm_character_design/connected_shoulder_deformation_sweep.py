"""Rigging-owned angle-conditioned corrective release for the connected shoulder.

The previous Character Rigging proof uses one fixed 10% proximal release weight
at -40/0/+40 degrees. A dense one-degree probe showed that silently extending
that fixed weight through the full envelope is not safe: at least the -3 degree
sample is measurably worse than the anchored 0% control. This successor keeps
the exact source, connected Geometry and donor rig identity explicit, then adds
a new bounded pose-conditioned corrective profile rather than rewriting the
existing rig.

Geometry PR #5's sampled self-intersection result is also preserved exactly as
a FAIL with 374 detected nonadjacent triangle-pair intersections. This module
cannot promote that Geometry finding, Animation acceptance or runtime support.
"""
from __future__ import annotations

import json
from pathlib import Path

from .connected_shoulder_deformation import (
    CANDIDATE_DIGESTS,
    CANDIDATE_PROXIMAL_WEIGHT,
    CONTROL_PROXIMAL_WEIGHT,
    GEOMETRY_HEAD,
    METRIC_TOLERANCE,
    POSE_ANGLES_DEG,
    RIG_ID as DONOR_RIG_ID,
    SOURCE_DIGEST,
    SOURCE_ID,
    SOURCE_MESH_DIGEST,
    STATUS as RIGGING_STATUS,
    _improves_control,
    _mirror_position_set,
    _pose,
    _pose_status,
    _position_set,
    _specimen_layout,
    _weights,
    audit_connected_shoulder_deformation,
    rig_plan,
)
from .connected_shoulder_self_intersection import (
    FAIL_STATUS as SELF_INTERSECTION_FAIL_STATUS,
    audit_connected_shoulder_self_intersection,
)
from .organic_form import canonical_digest
from .shoulder_connected_topology import build_connected_shoulder_specimen
from .shoulder_source_lineage import adopted_character_source

SCHEMA = "axm.character-connected-shoulder-angle-conditioned-release-evidence/v0.1"
STATUS = "PASS_CHARACTER_CONNECTED_SHOULDER_ANGLE_CONDITIONED_RELEASE_STRUCTURAL_SWEEP_WITH_HELD_INTERSECTION_FAIL"
FAIL_STATUS = "FAIL_CHARACTER_CONNECTED_SHOULDER_ANGLE_CONDITIONED_RELEASE_STRUCTURAL_SWEEP"
SELF_INTERSECTION_HEAD = "eae6d296867ecaa40e8f5c3f1fe37d8e3019541e"
SELF_INTERSECTION_PAIR_COUNT = 374
DONOR_RIGGING_HEAD = "b0a03cbcb61e0f8deec37172d22ff1a7fff306c9"
SUCCESSOR_RIG_ID = "character-connected-shoulder-socket-rig-002-angle-conditioned-release"
RELEASE_PROFILE_ID = "angle-conditioned-proximal-release-power12-v1"
RELEASE_POWER = 12.0
MAX_RELEASE_WEIGHT = CANDIDATE_PROXIMAL_WEIGHT
SWEEP_START_DEG = -40.0
SWEEP_END_DEG = 40.0
SWEEP_STEP_DEG = 1.0
SWEEP_ANGLES_DEG = tuple(float(value) for value in range(-40, 41))
REPRESENTATIVE_ANGLES_DEG = (-40.0, -20.0, 0.0, 20.0, 40.0)


def release_weight(angle_deg: float) -> float:
    magnitude = min(abs(float(angle_deg)), abs(SWEEP_END_DEG))
    if magnitude == 0.0:
        return 0.0
    normalized = magnitude / abs(SWEEP_END_DEG)
    return MAX_RELEASE_WEIGHT * (normalized ** RELEASE_POWER)


def successor_rig_profile():
    return {
        "rig_id": SUCCESSOR_RIG_ID,
        "donor_rig_id": DONOR_RIG_ID,
        "donor_rigging_head": DONOR_RIGGING_HEAD,
        "donor_rig_plan_digest": canonical_digest(rig_plan()),
        "release_profile_id": RELEASE_PROFILE_ID,
        "release_power": RELEASE_POWER,
        "max_release_weight": MAX_RELEASE_WEIGHT,
        "control_proximal_weight": CONTROL_PROXIMAL_WEIGHT,
        "driver": "absolute_local_shoulder_angle_deg",
        "verification_envelope_deg": [SWEEP_START_DEG, SWEEP_END_DEG],
        "formula": "max_release_weight * (abs(angle_deg) / 40.0) ** release_power",
        "endpoint_contract": {
            "zero_deg_weight": 0.0,
            "minus_40_deg_weight": MAX_RELEASE_WEIGHT,
            "plus_40_deg_weight": MAX_RELEASE_WEIGHT,
        },
    }


def sweep_contract():
    profile = successor_rig_profile()
    return {
        "schema": SCHEMA,
        "source_id": SOURCE_ID,
        "source_digest": SOURCE_DIGEST,
        "source_mesh_digest": SOURCE_MESH_DIGEST,
        "geometry_head": GEOMETRY_HEAD,
        "self_intersection_head": SELF_INTERSECTION_HEAD,
        "self_intersection_expected_status": SELF_INTERSECTION_FAIL_STATUS,
        "self_intersection_expected_pair_count": SELF_INTERSECTION_PAIR_COUNT,
        "donor_rigging_head": DONOR_RIGGING_HEAD,
        "donor_rig_id": DONOR_RIG_ID,
        "donor_rig_plan_digest": canonical_digest(rig_plan()),
        "successor_rig_id": SUCCESSOR_RIG_ID,
        "successor_rig_profile_digest": canonical_digest(profile),
        "candidate_geometry_digests": dict(CANDIDATE_DIGESTS),
        "sweep": {
            "start_deg": SWEEP_START_DEG,
            "end_deg": SWEEP_END_DEG,
            "step_deg": SWEEP_STEP_DEG,
            "sample_count_per_side": len(SWEEP_ANGLES_DEG),
            "angles_deg": list(SWEEP_ANGLES_DEG),
            "representative_angles_deg": list(REPRESENTATIVE_ANGLES_DEG),
        },
        "truth_boundary": {
            "verification_envelope_not_anatomical_joint_limits": True,
            "finite_dense_sampling_not_mathematical_continuous_proof": True,
            "sampled_geometry_self_intersection_fail_is_preserved": True,
            "interior_self_intersection_not_checked": True,
            "animation_acceptance": False,
            "runtime_acceptance": False,
            "visual_acceptance": False,
        },
    }


def _validate_contract(contract):
    expected = sweep_contract()
    if contract != expected:
        raise ValueError("connected shoulder angle-conditioned release contract identity drift")
    return expected


def _metric_extrema(rows):
    return {
        "minimum_triangle_area_ratio": min(row["minimum_triangle_area_ratio"] for row in rows),
        "maximum_triangle_area_ratio": max(row["maximum_triangle_area_ratio"] for row in rows),
        "minimum_edge_length_ratio": min(row["minimum_edge_length_ratio"] for row in rows),
        "maximum_edge_length_ratio": max(row["maximum_edge_length_ratio"] for row in rows),
        "maximum_fixed_socket_drift_m": max(row["fixed_socket_max_drift_m"] for row in rows),
        "maximum_rigid_arm_radius_drift_m": max(row["rigid_arm_radius_max_drift_m"] for row in rows),
        "collapsed_triangle_total": sum(row["collapsed_triangles"] for row in rows),
        "minimum_release_weight": min(row["proximal_release_weight"] for row in rows),
        "maximum_release_weight": max(row["proximal_release_weight"] for row in rows),
    }


def _write_obj(path, positions, faces):
    lines = ["# AXM retained Character connected shoulder angle-conditioned release pose"]
    lines.extend("v {:.12f} {:.12f} {:.12f}".format(*point) for point in positions)
    lines.extend("f {} {} {}".format(face[0] + 1, face[1] + 1, face[2] + 1) for face in faces)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sampled_intersection_pair_count(report):
    return sum(
        int(row["inspection"]["self_intersection_pair_count"])
        for row in report["samples"]
    )


def _nonworse_control(candidate, control):
    return (
        candidate["minimum_triangle_area_ratio"] + METRIC_TOLERANCE >= control["minimum_triangle_area_ratio"]
        and candidate["maximum_triangle_area_ratio"] <= control["maximum_triangle_area_ratio"] + METRIC_TOLERANCE
        and candidate["minimum_edge_length_ratio"] + METRIC_TOLERANCE >= control["minimum_edge_length_ratio"]
        and candidate["maximum_edge_length_ratio"] <= control["maximum_edge_length_ratio"] + METRIC_TOLERANCE
    )


def _rounded_positions(positions):
    return [[round(float(value), 9) for value in point] for point in positions]


def audit_connected_shoulder_deformation_sweep(contract=None):
    contract = _validate_contract(contract or sweep_contract())

    donor = audit_connected_shoulder_deformation()
    if donor["status"] != RIGGING_STATUS:
        raise ValueError("exact donor Rigging proof is not green")
    if canonical_digest(rig_plan()) != contract["donor_rig_plan_digest"]:
        raise ValueError("exact donor Rigging plan digest drift")
    if canonical_digest(successor_rig_profile()) != contract["successor_rig_profile_digest"]:
        raise ValueError("successor Rigging profile digest drift")

    self_intersection = audit_connected_shoulder_self_intersection()
    observed_intersection_pairs = _sampled_intersection_pair_count(self_intersection)
    if self_intersection["status"] != SELF_INTERSECTION_FAIL_STATUS:
        raise ValueError("Geometry sampled self-intersection finding status drift")
    if observed_intersection_pairs != SELF_INTERSECTION_PAIR_COUNT:
        raise ValueError("Geometry sampled self-intersection finding count drift")
    if self_intersection["producer_dependencies"]["rigging_head"] != DONOR_RIGGING_HEAD:
        raise ValueError("Geometry self-intersection donor Rigging dependency drift")

    source = adopted_character_source()
    if source.get("study_id") != SOURCE_ID or canonical_digest(source) != SOURCE_DIGEST:
        raise ValueError("adopted Character source identity drift")

    results = {}
    all_structural_pass = True
    for side in ("L", "R"):
        specimen = build_connected_shoulder_specimen(side)
        observed_geometry_digest = canonical_digest({
            "positions": specimen["positions"],
            "faces": specimen["faces"],
        })
        if observed_geometry_digest != CANDIDATE_DIGESTS[side]:
            raise ValueError(f"connected shoulder {side} Geometry identity drift")

        layout = _specimen_layout(source, specimen)
        control_weights = _weights(layout, CONTROL_PROXIMAL_WEIGHT)
        joint = rig_plan()["joints"][side]
        origin = tuple(source["landmarks"][joint["landmark"]])
        axis = tuple(joint["axis"])
        original_by_angle = {
            float(row["angle_deg"]): row
            for row in donor["results"][side]["candidate"]
        }

        candidate_rows = []
        control_rows = []
        for angle in SWEEP_ANGLES_DEG:
            proximal_release = release_weight(angle)
            candidate_weights = _weights(layout, proximal_release)
            candidate = _pose(specimen, origin, axis, angle, candidate_weights)
            control = _pose(specimen, origin, axis, angle, control_weights)
            candidate["proximal_release_weight"] = proximal_release
            control["proximal_release_weight"] = CONTROL_PROXIMAL_WEIGHT
            candidate["status"] = "PASS" if _pose_status(candidate) else "FAIL"
            control["status"] = "PASS" if _pose_status(control) else "FAIL"
            candidate["nonworse_than_anchored_proximal_control"] = _nonworse_control(candidate, control)
            candidate["strictly_improves_anchored_proximal_control"] = (
                False if angle == 0.0 else _improves_control(candidate, control)
            )
            candidate["position_digest"] = canonical_digest(candidate["positions"])
            control["position_digest"] = canonical_digest(control["positions"])

            if angle in original_by_angle:
                candidate["matches_original_rigging_anchor"] = (
                    _rounded_positions(candidate["positions"]) == original_by_angle[angle]["positions"]
                )
            else:
                candidate["matches_original_rigging_anchor"] = None

            all_structural_pass &= candidate["status"] == "PASS"
            all_structural_pass &= control["status"] == "PASS"
            all_structural_pass &= candidate["nonworse_than_anchored_proximal_control"]
            if candidate["matches_original_rigging_anchor"] is False:
                all_structural_pass = False

            candidate_rows.append(candidate)
            control_rows.append(control)

        results[side] = {
            "geometry_digest": observed_geometry_digest,
            "candidate": candidate_rows,
            "anchored_proximal_control": control_rows,
            "candidate_extrema": _metric_extrema(candidate_rows),
            "control_extrema": _metric_extrema(control_rows),
        }

    bilateral_mirror_pass = True
    for index, _angle in enumerate(SWEEP_ANGLES_DEG):
        left = results["L"]["candidate"][index]["positions"]
        right = results["R"]["candidate"][index]["positions"]
        mirrored = _mirror_position_set(left) == _position_set(right)
        results["L"]["candidate"][index]["bilateral_mirrored_position_set"] = mirrored
        results["R"]["candidate"][index]["bilateral_mirrored_position_set"] = mirrored
        bilateral_mirror_pass &= mirrored
        all_structural_pass &= mirrored

    anchor_pass = all(
        row["matches_original_rigging_anchor"] is True
        for side in ("L", "R")
        for row in results[side]["candidate"]
        if row["angle_deg"] in POSE_ANGLES_DEG
    )
    all_structural_pass &= anchor_pass

    boundary_improvement_pass = all(
        row["strictly_improves_anchored_proximal_control"]
        for side in ("L", "R")
        for row in results[side]["candidate"]
        if row["angle_deg"] in (-40.0, 40.0)
    )
    all_structural_pass &= boundary_improvement_pass

    representative = {
        side: [
            {
                "angle_deg": row["angle_deg"],
                "proximal_release_weight": row["proximal_release_weight"],
                "position_digest": row["position_digest"],
                "minimum_triangle_area_ratio": row["minimum_triangle_area_ratio"],
                "maximum_triangle_area_ratio": row["maximum_triangle_area_ratio"],
                "minimum_edge_length_ratio": row["minimum_edge_length_ratio"],
                "maximum_edge_length_ratio": row["maximum_edge_length_ratio"],
                "fixed_socket_max_drift_m": row["fixed_socket_max_drift_m"],
                "rigid_arm_radius_max_drift_m": row["rigid_arm_radius_max_drift_m"],
                "nonworse_than_anchored_proximal_control": row["nonworse_than_anchored_proximal_control"],
                "strictly_improves_anchored_proximal_control": row["strictly_improves_anchored_proximal_control"],
            }
            for row in results[side]["candidate"]
            if row["angle_deg"] in REPRESENTATIVE_ANGLES_DEG
        ]
        for side in ("L", "R")
    }

    return {
        "schema": SCHEMA,
        "status": STATUS if all_structural_pass else FAIL_STATUS,
        "contract": contract,
        "successor_rig_profile": successor_rig_profile(),
        "dependencies": {
            "donor_rigging_status": donor["status"],
            "sampled_self_intersection_status": self_intersection["status"],
            "sampled_self_intersection_pair_count": observed_intersection_pairs,
            "sampled_self_intersection_scope_angles_deg": list(POSE_ANGLES_DEG),
            "sampled_self_intersection_acceptance": "HELD_FAIL__NOT_RELABELLED_BY_RIGGING",
        },
        "sample_scope": {
            "samples_per_side": len(SWEEP_ANGLES_DEG),
            "total_candidate_samples": len(SWEEP_ANGLES_DEG) * 2,
            "angles_deg": list(SWEEP_ANGLES_DEG),
            "finite_dense_sampling": True,
            "continuous_interpolation_proven": False,
            "interior_self_intersection_checked": False,
        },
        "results": results,
        "representative": representative,
        "gates": {
            "exact_source_identity": "PASS",
            "exact_connected_geometry_identity": "PASS",
            "exact_donor_rig_identity": "PASS",
            "explicit_successor_rig_profile_identity": "PASS",
            "exact_sampled_self_intersection_finding": "BOUND_FAIL_374_PAIRS",
            "all_162_successor_pose_samples_structurally_green_and_nonworse": "PASS" if all_structural_pass else "FAIL",
            "original_nonzero_boundary_samples_still_strictly_improve_control": "PASS" if boundary_improvement_pass else "FAIL",
            "original_minus40_zero_plus40_pose_anchors_unchanged": "PASS" if anchor_pass else "FAIL",
            "bilateral_mirror_all_samples": "PASS" if bilateral_mirror_pass else "FAIL",
            "sampled_self_intersection_acceptance": "FAIL_HELD",
            "continuous_interpolation": "NOT_PROVEN_BY_FINITE_SWEEP",
            "interior_self_intersection": "NOT_CHECKED",
            "visual_quality": "NOT_CLAIMED",
            "animation_or_runtime": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "The exact Character source, connected Geometry and donor Rigging PR #4 remain unchanged; this evidence gives the corrective profile a new successor rig identity instead of silently mutating the donor rig.",
            "The successor uses a smooth absolute-angle power-12 release: weight 0.0 at neutral and exactly the donor 0.10 release at both +/-40 degree boundaries.",
            "Geometry PR #5 reports FAIL_CHARACTER_CONNECTED_SHOULDER_SAMPLED_NONADJACENT_SELF_INTERSECTION_GATE with 374 detected nonadjacent triangle-pair intersections across its six retained samples; this Rigging successor pins and preserves that failure.",
            "The one-degree sweep checks structural distortion metrics and exact socket/radius invariants only. It does not establish collision freedom, continuous deformation quality or animation timing.",
            "The -40..+40 degree range is a verification envelope, not an anatomical joint limit or runtime/controller policy.",
            "Finite one-degree sampling materially narrows the unobserved structural interval but does not mathematically prove every real-valued intermediate pose.",
            "No anatomy, volume preservation, skin sliding, visual acceptance, Animation acceptance, exported skeleton/skin, runtime/controller, gameplay, CANON, production readiness or Rigging mastery is claimed.",
        ],
    }


def build_connected_shoulder_deformation_sweep_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_connected_shoulder_deformation_sweep()
    (out / "connected-shoulder-angle-conditioned-release-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "successor-rig-profile.json").write_text(
        json.dumps(successor_rig_profile(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    source = adopted_character_source()
    plan = rig_plan()
    for side in ("L", "R"):
        specimen = build_connected_shoulder_specimen(side)
        joint = plan["joints"][side]
        origin = tuple(source["landmarks"][joint["landmark"]])
        axis = tuple(joint["axis"])
        layout = _specimen_layout(source, specimen)
        for angle in REPRESENTATIVE_ANGLES_DEG:
            posed = _pose(specimen, origin, axis, angle, _weights(layout, release_weight(angle)))
            label = f"m{abs(int(angle)):02d}" if angle < 0 else f"p{int(angle):02d}"
            if angle == 0:
                label = "zero"
            _write_obj(
                out / f"character-shoulder-{side.lower()}-{label}.obj",
                posed["positions"],
                specimen["faces"],
            )

    return receipt
