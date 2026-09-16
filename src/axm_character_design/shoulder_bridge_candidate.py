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

SCHEMA = "axm.character-shoulder-bridge-candidate/v0.2"
STATUS = "PASS_BOUNDED_SHOULDER_TRANSITION_BRIDGE_CANDIDATE"
CANDIDATE_STUDY_ID = "character-neutral-a-shoulder-bridge-001"
BASELINE_STUDY_ID = "character-neutral-a-001"
BRIDGE_IDS = ("shoulder_bridge_L", "shoulder_bridge_R")
MIN_PROXIMAL_RING_SAMPLES_IN_RIBCAGE = 6


def _bridge_region(side: str):
    sign = -1.0 if side == "L" else 1.0
    return {
        "id": f"shoulder_bridge_{side}",
        "anchor": [sign * 0.16, 0.0, 1.43],
        "shoulder_landmark": f"shoulder_{side}",
        "radius_anchor_m": 0.10,
        "radius_shoulder_m": 0.075,
        "role": "STYLIZED_SHOULDER_TRANSITION_BRIDGE_NOT_ANATOMY_CLAIM",
        "status": "FORM_CANDIDATE_NOT_CONNECTED_TOPOLOGY",
    }


def shoulder_bridge_candidate(study=None):
    baseline = study or neutral_character_study()
    validate_study(baseline)
    candidate = deepcopy(baseline)
    candidate["study_id"] = CANDIDATE_STUDY_ID
    candidate["intent"] = (
        "stylized_human_like_biped_form_study_with_bilateral_tapered_shoulder_transition_bridges"
    )
    candidate["shoulder_transition_regions"] = [
        _bridge_region("L"),
        _bridge_region("R"),
    ]
    candidate["candidate_provenance"] = {
        "baseline_study_id": baseline["study_id"],
        "baseline_source_digest": canonical_digest(baseline),
        "delta": "add_two_bilateral_tapered_shoulder_transition_regions_only",
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


def build_shoulder_bridge_mesh(candidate=None):
    candidate = candidate or shoulder_bridge_candidate()
    validate_study(candidate)
    mesh = build_mesh(candidate)
    vertices = list(mesh["vertices"])
    faces = list(mesh["faces"])
    regions = list(mesh["regions"])
    landmarks = candidate["landmarks"]
    for bridge in candidate["shoulder_transition_regions"]:
        shoulder = landmarks[bridge["shoulder_landmark"]]
        bridge_vertices, bridge_faces = _segment_mesh(
            bridge["anchor"],
            shoulder,
            float(bridge["radius_anchor_m"]),
            float(bridge["radius_shoulder_m"]),
            sides=10,
        )
        vertex_start = len(vertices)
        face_start = len(faces)
        vertices.extend(bridge_vertices)
        faces.extend([[index + vertex_start for index in face] for face in bridge_faces])
        regions.append(
            {
                "id": bridge["id"],
                "vertex_start": vertex_start,
                "vertex_count": len(bridge_vertices),
                "face_start": face_start,
                "face_count": len(bridge_faces),
            }
        )
    return {"vertices": vertices, "faces": faces, "regions": regions}


def audit_shoulder_bridge(candidate=None):
    baseline = neutral_character_study()
    candidate = candidate or shoulder_bridge_candidate(baseline)
    baseline_metrics = validate_study(baseline)
    candidate_metrics = validate_study(candidate)

    if candidate["landmarks"] != baseline["landmarks"]:
        raise ValueError("candidate landmark drift")
    if candidate["segments"] != baseline["segments"]:
        raise ValueError("candidate segment drift")
    if candidate["masses"] != baseline["masses"]:
        raise ValueError("candidate primary-mass drift")
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

    bridges = {item["id"]: item for item in candidate.get("shoulder_transition_regions", [])}
    if set(bridges) != set(BRIDGE_IDS):
        raise ValueError("candidate bridge-region coverage drift")
    left = bridges["shoulder_bridge_L"]
    right = bridges["shoulder_bridge_R"]
    tol = baseline["design_constraints"]["bilateral_tolerance_m"]
    if abs(left["anchor"][0] + right["anchor"][0]) > tol:
        raise ValueError("bridge anchor bilateral x drift")
    if any(abs(left["anchor"][i] - right["anchor"][i]) > tol for i in (1, 2)):
        raise ValueError("bridge anchor bilateral yz drift")
    for key in ("radius_anchor_m", "radius_shoulder_m"):
        if abs(float(left[key]) - float(right[key])) > tol:
            raise ValueError(f"bridge bilateral radius drift: {key}")
    if left["shoulder_landmark"] != "shoulder_L" or right["shoulder_landmark"] != "shoulder_R":
        raise ValueError("bridge shoulder landmark binding drift")

    segments = {segment["id"]: segment for segment in baseline["segments"]}
    masses = {mass["id"]: mass for mass in baseline["masses"]}
    ribcage = masses["ribcage"]
    lm = baseline["landmarks"]
    shoulder_results = []
    for side in ("L", "R"):
        bridge = bridges[f"shoulder_bridge_{side}"]
        upper_arm = segments[f"upper_arm_{side}"]
        shoulder = lm[bridge["shoulder_landmark"]]
        if upper_arm["a"] != bridge["shoulder_landmark"]:
            raise ValueError(f"upper-arm shoulder binding drift: {side}")
        if abs(float(bridge["radius_shoulder_m"]) - float(upper_arm["radius_a"])) > tol:
            raise ValueError(f"bridge-to-upper-arm radius mismatch: {side}")

        bridge_mesh, _ = _segment_mesh(
            bridge["anchor"],
            shoulder,
            float(bridge["radius_anchor_m"]),
            float(bridge["radius_shoulder_m"]),
            sides=10,
        )
        proximal_ring = bridge_mesh[:10]
        proximal_values = [_ellipsoid_implicit(point, ribcage) for point in proximal_ring]
        proximal_inside = sum(value <= 1.0 + tol for value in proximal_values)
        anchor_implicit = _ellipsoid_implicit(bridge["anchor"], ribcage)
        if anchor_implicit > 1.0 + tol:
            raise ValueError(f"shoulder bridge anchor detached from ribcage: {side}")
        if proximal_inside < MIN_PROXIMAL_RING_SAMPLES_IN_RIBCAGE:
            raise ValueError(f"insufficient bridge proximal-ring ribcage overlap: {side}")

        original_root_ring, _ = _segment_mesh(
            shoulder,
            lm[upper_arm["b"]],
            float(upper_arm["radius_a"]),
            float(upper_arm["radius_b"]),
            sides=10,
        )
        original_root_ring = original_root_ring[:10]
        original_inside = sum(
            _ellipsoid_implicit(point, ribcage) <= 1.0 + tol
            for point in original_root_ring
        )
        shoulder_results.append(
            {
                "side": side,
                "bridge_region": bridge["id"],
                "bridge_anchor": bridge["anchor"],
                "bridge_anchor_ribcage_implicit": _rounded(anchor_implicit),
                "bridge_proximal_ring_sample_count": 10,
                "bridge_proximal_ring_samples_inside_or_on_ribcage": proximal_inside,
                "bridge_distal_radius_m": float(bridge["radius_shoulder_m"]),
                "upper_arm_root_radius_m": float(upper_arm["radius_a"]),
                "original_upper_arm_root_ring_samples_inside_or_on_ribcage": original_inside,
                "observation": "LOCAL_FORM_TRANSITION_PROXY_NOT_DEFORMATION_GATE",
            }
        )

    if shoulder_results[0]["bridge_proximal_ring_samples_inside_or_on_ribcage"] != shoulder_results[1]["bridge_proximal_ring_samples_inside_or_on_ribcage"]:
        raise ValueError("candidate proximal overlap bilateral drift")
    if shoulder_results[0]["original_upper_arm_root_ring_samples_inside_or_on_ribcage"] != shoulder_results[1]["original_upper_arm_root_ring_samples_inside_or_on_ribcage"]:
        raise ValueError("baseline shoulder overlap bilateral drift")

    baseline_mesh = build_mesh(baseline)
    candidate_mesh = build_shoulder_bridge_mesh(candidate)
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
            "baseline_primary_masses_preserved_exactly": True,
            "baseline_flex_zones_preserved_exactly": True,
            "added_region_ids": list(BRIDGE_IDS),
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
            "bridge-anchor-overlaps-ribcage": "PASS",
            "majority-bridge-proximal-ring-overlaps-ribcage": "PASS",
            "bridge-distal-radius-matches-upper-arm-root": "PASS",
            "whole-body-bounds-preserved": "PASS",
            "a-rest-angle-preserved": "PASS",
            "finite-nondegenerate-candidate-mesh": "PASS",
            "art-direction-acceptance": "NOT_CLAIMED",
            "connected-topology-acceptance": "NOT_CLAIMED",
            "rigging-or-deformation-acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "stylized local shoulder-transition form candidate only; not anatomical, medical, or biological validation",
            "the two added tapered bridge regions are disconnected proof geometry, not production skin topology",
            "proximal ring overlap and exact distal radius match are local form-continuity proxies, not skinning or deformation quality metrics",
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
    candidate_mesh = build_shoulder_bridge_mesh(candidate)
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
