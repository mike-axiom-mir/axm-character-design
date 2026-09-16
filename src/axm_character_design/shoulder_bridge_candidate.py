from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .organic_form import (
    _segment_mesh,
    build_mesh,
    canonical_digest,
    mesh_checks,
    neutral_character_study,
    svg_wire,
    validate_study,
    write_obj,
)

SCHEMA = "axm.character-shoulder-bridge-candidate/v0.1"
STATUS = "PASS_BOUNDED_SHOULDER_BRIDGE_FORM_CANDIDATE"
CANDIDATE_STUDY_ID = "character-neutral-a-shoulder-bridge-001"
BASELINE_STUDY_ID = "character-neutral-a-001"
BRIDGE_IDS = ("shoulder_bridge_L", "shoulder_bridge_R")
MIN_ROOT_RING_SAMPLES_IN_BRIDGE = 6


def _bridge_mass(side: str):
    sign = -1.0 if side == "L" else 1.0
    return {
        "id": f"shoulder_bridge_{side}",
        "center": [sign * 0.19, 0.0, 1.46],
        "radii": [0.10, 0.11, 0.10],
        "role": "STYLIZED_SHOULDER_TRANSITION_MASS_NOT_ANATOMY_CLAIM",
    }


def shoulder_bridge_candidate(study=None):
    baseline = study or neutral_character_study()
    validate_study(baseline)
    candidate = deepcopy(baseline)
    candidate["study_id"] = CANDIDATE_STUDY_ID
    candidate["intent"] = (
        "stylized_human_like_biped_form_study_with_bilateral_shoulder_transition_masses"
    )
    candidate["masses"].extend([_bridge_mass("L"), _bridge_mass("R")])
    candidate["candidate_provenance"] = {
        "baseline_study_id": baseline["study_id"],
        "baseline_source_digest": canonical_digest(baseline),
        "delta": "add_two_bilateral_shoulder_transition_masses_only",
        "status": "DERIVED_ORGANIC_FORM_CANDIDATE_NOT_ACCEPTED_SOURCE",
    }
    validate_study(candidate)
    return candidate


def _ellipsoid_implicit(point, mass):
    return sum(
        ((point[i] - mass["center"][i]) / mass["radii"][i]) ** 2
        for i in range(3)
    )


def _rounded(value):
    return round(float(value), 12)


def audit_shoulder_bridge(candidate=None):
    baseline = neutral_character_study()
    candidate = candidate or shoulder_bridge_candidate(baseline)
    baseline_metrics = validate_study(baseline)
    candidate_metrics = validate_study(candidate)

    if candidate["landmarks"] != baseline["landmarks"]:
        raise ValueError("candidate landmark drift")
    if candidate["segments"] != baseline["segments"]:
        raise ValueError("candidate segment drift")
    if candidate["flex_zones"] != baseline["flex_zones"]:
        raise ValueError("candidate flex-zone drift")
    if candidate["design_constraints"] != baseline["design_constraints"]:
        raise ValueError("candidate design-constraint drift")
    if candidate["coordinate_system"] != baseline["coordinate_system"]:
        raise ValueError("candidate coordinate-system drift")
    if candidate["donor"] != baseline["donor"]:
        raise ValueError("candidate donor drift")
    if candidate["truth_state"] != baseline["truth_state"]:
        raise ValueError("candidate truth-state drift")
    if candidate["masses"][: len(baseline["masses"])] != baseline["masses"]:
        raise ValueError("candidate altered baseline masses")

    bridges = {mass["id"]: mass for mass in candidate["masses"] if mass["id"] in BRIDGE_IDS}
    if set(bridges) != set(BRIDGE_IDS):
        raise ValueError("candidate bridge-mass coverage drift")
    left = bridges["shoulder_bridge_L"]
    right = bridges["shoulder_bridge_R"]
    tol = baseline["design_constraints"]["bilateral_tolerance_m"]
    if abs(left["center"][0] + right["center"][0]) > tol:
        raise ValueError("bridge center bilateral x drift")
    if any(abs(left["center"][i] - right["center"][i]) > tol for i in (1, 2)):
        raise ValueError("bridge center bilateral yz drift")
    if any(abs(left["radii"][i] - right["radii"][i]) > tol for i in range(3)):
        raise ValueError("bridge radius bilateral drift")

    segments = {segment["id"]: segment for segment in baseline["segments"]}
    masses = {mass["id"]: mass for mass in baseline["masses"]}
    ribcage = masses["ribcage"]
    lm = baseline["landmarks"]
    shoulder_results = []
    for side in ("L", "R"):
        segment = segments[f"upper_arm_{side}"]
        bridge = bridges[f"shoulder_bridge_{side}"]
        root = lm[segment["a"]]
        tip = lm[segment["b"]]
        root_ring, _ = _segment_mesh(
            root,
            tip,
            float(segment["radius_a"]),
            float(segment["radius_b"]),
            sides=10,
        )
        root_ring = root_ring[:10]
        baseline_ribcage_values = [_ellipsoid_implicit(point, ribcage) for point in root_ring]
        bridge_values = [_ellipsoid_implicit(point, bridge) for point in root_ring]
        baseline_inside = sum(value <= 1.0 + tol for value in baseline_ribcage_values)
        bridge_inside = sum(value <= 1.0 + tol for value in bridge_values)
        bridge_center_ribcage = _ellipsoid_implicit(bridge["center"], ribcage)
        if bridge_center_ribcage > 1.0 + tol:
            raise ValueError(f"shoulder bridge center detached from ribcage: {side}")
        if bridge_inside < MIN_ROOT_RING_SAMPLES_IN_BRIDGE:
            raise ValueError(f"insufficient shoulder bridge root-ring coverage: {side}")
        shoulder_results.append(
            {
                "side": side,
                "upper_arm_segment": segment["id"],
                "baseline_receiving_mass": "ribcage",
                "candidate_transition_mass": bridge["id"],
                "root_ring_sample_count": 10,
                "baseline_root_ring_samples_inside_or_on_ribcage": baseline_inside,
                "candidate_root_ring_samples_inside_or_on_bridge_mass": bridge_inside,
                "candidate_bridge_center_ribcage_implicit": _rounded(bridge_center_ribcage),
                "observation": "LOCAL_FORM_CONTINUITY_PROXY_NOT_DEFORMATION_GATE",
            }
        )

    if shoulder_results[0]["baseline_root_ring_samples_inside_or_on_ribcage"] != shoulder_results[1]["baseline_root_ring_samples_inside_or_on_ribcage"]:
        raise ValueError("baseline shoulder overlap bilateral drift")
    if shoulder_results[0]["candidate_root_ring_samples_inside_or_on_bridge_mass"] != shoulder_results[1]["candidate_root_ring_samples_inside_or_on_bridge_mass"]:
        raise ValueError("candidate shoulder overlap bilateral drift")

    baseline_mesh = build_mesh(baseline)
    candidate_mesh = build_mesh(candidate)
    baseline_checks = mesh_checks(baseline_mesh)
    candidate_checks = mesh_checks(candidate_mesh)
    if baseline_checks["bounds_min"] != candidate_checks["bounds_min"] or baseline_checks["bounds_max"] != candidate_checks["bounds_max"]:
        raise ValueError("candidate changed whole-body bounds")
    if abs(baseline_metrics["a_pose_down_angle_deg"] - candidate_metrics["a_pose_down_angle_deg"]) > tol:
        raise ValueError("candidate changed A-rest arm angle")

    baseline_mesh_digest = canonical_digest(baseline_mesh)
    candidate_mesh_digest = canonical_digest(candidate_mesh)
    if baseline_mesh_digest == candidate_mesh_digest:
        raise ValueError("candidate mesh unexpectedly identical to baseline")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "baseline_study_id": BASELINE_STUDY_ID,
        "candidate_study_id": CANDIDATE_STUDY_ID,
        "baseline_source_digest": canonical_digest(baseline),
        "candidate_source_digest": canonical_digest(candidate),
        "baseline_mesh_digest": baseline_mesh_digest,
        "candidate_mesh_digest": candidate_mesh_digest,
        "source_identity": {
            "baseline_landmarks_preserved_exactly": True,
            "baseline_segments_preserved_exactly": True,
            "baseline_masses_preserved_exactly": True,
            "baseline_flex_zones_preserved_exactly": True,
            "added_mass_ids": list(BRIDGE_IDS),
        },
        "form_metrics": {
            "baseline_a_rest_down_angle_deg": _rounded(baseline_metrics["a_pose_down_angle_deg"]),
            "candidate_a_rest_down_angle_deg": _rounded(candidate_metrics["a_pose_down_angle_deg"]),
            "whole_body_bounds_unchanged": True,
            "baseline_vertices": baseline_checks["vertex_count"],
            "candidate_vertices": candidate_checks["vertex_count"],
            "baseline_triangles": baseline_checks["triangle_count"],
            "candidate_triangles": candidate_checks["triangle_count"],
            "added_vertices": candidate_checks["vertex_count"] - baseline_checks["vertex_count"],
            "added_triangles": candidate_checks["triangle_count"] - baseline_checks["triangle_count"],
        },
        "shoulder_transition_observations": shoulder_results,
        "gates": {
            "baseline-source-identity-preserved": "PASS",
            "bilateral-bridge-symmetry": "PASS",
            "bridge-center-overlaps-ribcage": "PASS",
            "majority-upper-arm-root-ring-covered-by-bridge": "PASS",
            "whole-body-bounds-preserved": "PASS",
            "a-rest-angle-preserved": "PASS",
            "finite-nondegenerate-candidate-mesh": "PASS",
            "art-direction-acceptance": "NOT_CLAIMED",
            "connected-topology-acceptance": "NOT_CLAIMED",
            "rigging-or-deformation-acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "stylized local shoulder-transition form candidate only; not anatomical, medical, or biological validation",
            "the two added ellipsoid masses are disconnected proof geometry, not production skin topology",
            "root-ring coverage is a neutral local form-continuity proxy, not a skinning or deformation quality metric",
            "baseline landmarks, limb segments, primary masses, flex-zone truth states, authored height, A-rest angle, and whole-body bounds remain unchanged",
            "no rigging, weights, animation, materials, engine/runtime, gameplay, Armor/Unit fit, Art Direction acceptance, CANON, or mastery claim",
        ],
    }


def build_shoulder_bridge_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    baseline = neutral_character_study()
    candidate = shoulder_bridge_candidate(baseline)
    baseline_mesh = build_mesh(baseline)
    candidate_mesh = build_mesh(candidate)
    receipt = audit_shoulder_bridge(candidate)

    (out / "shoulder-bridge-candidate.source.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-bridge-candidate.mesh.json").write_text(
        json.dumps(candidate_mesh, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_obj(candidate_mesh, out / "shoulder-bridge-candidate.obj")
    for view in ("front", "side", "top"):
        (out / f"shoulder-bridge-baseline-{view}.svg").write_text(
            svg_wire(baseline_mesh, view, BASELINE_STUDY_ID), encoding="utf-8"
        )
        (out / f"shoulder-bridge-candidate-{view}.svg").write_text(
            svg_wire(candidate_mesh, view, CANDIDATE_STUDY_ID), encoding="utf-8"
        )
    (out / "shoulder-bridge-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
