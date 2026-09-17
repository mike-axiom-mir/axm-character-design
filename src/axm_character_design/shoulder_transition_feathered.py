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
    validate_study,
    write_obj,
)
from .shoulder_bridge_candidate import build_shoulder_bridge_mesh
from .shoulder_bridge_refinement import (
    EXPECTED_REFINED_MESH_DIGEST,
    EXPECTED_REFINED_SOURCE_DIGEST,
    REFINED_ANCHOR_RADIUS_M,
    refined_shoulder_bridge_candidate,
)
from .shoulder_transition_profile import _filled_comparison_svg

SCHEMA = "axm.character-shoulder-transition-feathered/v0.1"
STATUS = "PASS_BOUNDED_FEATHERED_SHOULDER_TRANSITION_CANDIDATE"
VARIANT_ID = "character-neutral-a-shoulder-transition-feathered-003"
ROOT_RING_INDICES = (4, 5, 6, 7, 8, 9, 0, 1)
BLEND_WEIGHTS = (0.40, 0.65, 0.90, 1.0, 1.0, 0.90, 0.65, 0.40)
TARGET_AXIS_SCALE = (0.55, 0.55, 0.85)


def _rounded(value):
    return round(float(value), 12)


def _ellipsoid_implicit(point, mass):
    return sum(
        ((point[i] - mass["center"][i]) / mass["radii"][i]) ** 2
        for i in range(3)
    )


def feathered_shoulder_candidate(study=None):
    baseline = study or neutral_character_study()
    refined = refined_shoulder_bridge_candidate(baseline)
    if canonical_digest(refined) != EXPECTED_REFINED_SOURCE_DIGEST:
        raise ValueError("refined shoulder source identity drift")
    if canonical_digest(build_shoulder_bridge_mesh(refined)) != EXPECTED_REFINED_MESH_DIGEST:
        raise ValueError("refined shoulder mesh identity drift")

    candidate = deepcopy(refined)
    candidate["study_id"] = VARIANT_ID
    candidate["intent"] = "stylized_biped_form_study_with_feathered_open_shoulder_transitions"
    for bridge in candidate["shoulder_transition_regions"]:
        if float(bridge["radius_anchor_m"]) != REFINED_ANCHOR_RADIUS_M:
            raise ValueError("unexpected retained anchor radius")
        if float(bridge["radius_shoulder_m"]) != 0.075:
            raise ValueError("unexpected retained upper-arm root radius")
        bridge["profile_kind"] = "FEATHERED_OPEN_SADDLE_NOT_ANNULAR_TUBE"
        bridge["root_ring_indices"] = list(ROOT_RING_INDICES)
        bridge["blend_weights"] = list(BLEND_WEIGHTS)
        bridge["target_axis_scale"] = list(TARGET_AXIS_SCALE)
        bridge["open_inferior_sector"] = True

    candidate["shoulder_transition_repair"] = {
        "schema": SCHEMA,
        "variant_id": VARIANT_ID,
        "prior_refined_source_digest": EXPECTED_REFINED_SOURCE_DIGEST,
        "prior_refined_mesh_digest": EXPECTED_REFINED_MESH_DIGEST,
        "anchor_radius_reference_m": REFINED_ANCHOR_RADIUS_M,
        "upper_arm_root_radius_reference_m": 0.075,
        "root_ring_indices": list(ROOT_RING_INDICES),
        "blend_weights": list(BLEND_WEIGHTS),
        "target_axis_scale": list(TARGET_AXIS_SCALE),
        "status": "DERIVED_REVIEW_VARIANT_NOT_ACCEPTED_SOURCE",
    }
    validate_study(candidate)
    return candidate


def _patch(candidate, side):
    landmarks = candidate["landmarks"]
    segments = {item["id"]: item for item in candidate["segments"]}
    bridges = {item["id"]: item for item in candidate["shoulder_transition_regions"]}
    bridge = bridges[f"shoulder_bridge_{side}"]
    upper_arm = segments[f"upper_arm_{side}"]
    shoulder = landmarks[bridge["shoulder_landmark"]]
    elbow = landmarks[upper_arm["b"]]
    ring, _ = _segment_mesh(
        shoulder,
        elbow,
        float(upper_arm["radius_a"]),
        float(upper_arm["radius_b"]),
        sides=10,
    )
    root_ring = ring[:10]
    distal = [list(root_ring[index]) for index in ROOT_RING_INDICES]
    anchor = bridge["anchor"]
    sx, sy, sz = TARGET_AXIS_SCALE
    proximal = []
    for point, weight in zip(distal, BLEND_WEIGHTS):
        radial = [point[i] - shoulder[i] for i in range(3)]
        target = [
            anchor[0] + radial[0] * sx,
            anchor[1] + radial[1] * sy,
            anchor[2] + radial[2] * sz,
        ]
        proximal.append(
            [point[i] + float(weight) * (target[i] - point[i]) for i in range(3)]
        )

    count = len(distal)
    faces = []
    for index in range(count - 1):
        nxt = index + 1
        faces.append([index, nxt, count + nxt])
        faces.append([index, count + nxt, count + index])
    return {
        "vertices": proximal + distal,
        "faces": faces,
        "proximal": proximal,
        "distal": distal,
        "root_ring": root_ring,
    }


def build_feathered_shoulder_mesh(candidate=None):
    candidate = candidate or feathered_shoulder_candidate()
    mesh = build_mesh(candidate)
    vertices = list(mesh["vertices"])
    faces = list(mesh["faces"])
    regions = list(mesh["regions"])
    for side in ("L", "R"):
        patch = _patch(candidate, side)
        vertex_start = len(vertices)
        face_start = len(faces)
        vertices.extend(patch["vertices"])
        faces.extend([[value + vertex_start for value in face] for face in patch["faces"]])
        regions.append(
            {
                "id": f"shoulder_feathered_{side}",
                "vertex_start": vertex_start,
                "vertex_count": len(patch["vertices"]),
                "face_start": face_start,
                "face_count": len(patch["faces"]),
            }
        )
    return {"vertices": vertices, "faces": faces, "regions": regions}


def _normalized_back_to_refined(candidate):
    normalized = deepcopy(candidate)
    normalized.pop("shoulder_transition_repair")
    refined = refined_shoulder_bridge_candidate(neutral_character_study())
    normalized["study_id"] = refined["study_id"]
    normalized["intent"] = refined["intent"]
    for bridge in normalized["shoulder_transition_regions"]:
        bridge.pop("profile_kind")
        bridge.pop("root_ring_indices")
        bridge.pop("blend_weights")
        bridge.pop("target_axis_scale")
        bridge.pop("open_inferior_sector")
    return normalized


def audit_feathered_shoulder(candidate=None):
    baseline = neutral_character_study()
    refined = refined_shoulder_bridge_candidate(baseline)
    candidate = candidate or feathered_shoulder_candidate(baseline)
    validate_study(candidate)
    if canonical_digest(_normalized_back_to_refined(candidate)) != canonical_digest(refined):
        raise ValueError("feathered candidate changed fields outside bounded transition delta")

    baseline_mesh = build_mesh(baseline)
    refined_mesh = build_shoulder_bridge_mesh(refined)
    candidate_mesh = build_feathered_shoulder_mesh(candidate)
    baseline_checks = mesh_checks(baseline_mesh)
    refined_checks = mesh_checks(refined_mesh)
    candidate_checks = mesh_checks(candidate_mesh)
    if candidate_checks["bounds_min"] != baseline_checks["bounds_min"]:
        raise ValueError("minimum whole-body bounds changed")
    if candidate_checks["bounds_max"] != baseline_checks["bounds_max"]:
        raise ValueError("maximum whole-body bounds changed")

    ribcage = {item["id"]: item for item in baseline["masses"]}["ribcage"]
    side_results = []
    vertex_sets = {}
    for side in ("L", "R"):
        patch = _patch(candidate, side)
        inside = sum(_ellipsoid_implicit(point, ribcage) <= 1.0 + 1e-9 for point in patch["proximal"])
        if inside != len(patch["proximal"]):
            raise ValueError(f"feathered proximal row escaped ribcage envelope: {side}")
        expected = [patch["root_ring"][index] for index in ROOT_RING_INDICES]
        if patch["distal"] != expected:
            raise ValueError(f"distal root sample identity drift: {side}")
        count = len(ROOT_RING_INDICES)
        if any(
            (0 in face and count - 1 in face)
            or (count in face and (2 * count) - 1 in face)
            for face in patch["faces"]
        ):
            raise ValueError(f"open transition arc wrapped closed: {side}")
        vertex_sets[side] = {
            tuple(_rounded(value) for value in vertex) for vertex in patch["vertices"]
        }
        side_results.append(
            {
                "side": side,
                "proximal_samples_inside_or_on_ribcage": inside,
                "proximal_sample_count": len(patch["proximal"]),
                "distal_samples_exactly_on_upper_arm_root_ring": len(expected),
                "root_ring_sample_count": len(ROOT_RING_INDICES),
                "root_ring_total_samples": 10,
                "open_inferior_samples_not_covered": 10 - len(ROOT_RING_INDICES),
                "patch_vertices": len(patch["vertices"]),
                "patch_triangles": len(patch["faces"]),
                "observation": "STRUCTURAL_FEATHERED_OPEN_SADDLE_NOT_VISUAL_ACCEPTANCE",
            }
        )

    mirrored_left = {
        (_rounded(-vertex[0]), _rounded(vertex[1]), _rounded(vertex[2]))
        for vertex in vertex_sets["L"]
    }
    if mirrored_left != vertex_sets["R"]:
        raise ValueError("bilateral feathered transition geometry drift")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "variant_id": VARIANT_ID,
        "baseline_source_digest": canonical_digest(baseline),
        "refined_source_digest": canonical_digest(refined),
        "refined_mesh_digest": canonical_digest(refined_mesh),
        "candidate_source_digest": canonical_digest(candidate),
        "candidate_mesh_digest": canonical_digest(candidate_mesh),
        "bounded_delta": {
            "anchor_radius_reference_m": REFINED_ANCHOR_RADIUS_M,
            "upper_arm_root_radius_reference_m": 0.075,
            "root_ring_indices": list(ROOT_RING_INDICES),
            "blend_weights": list(BLEND_WEIGHTS),
            "target_axis_scale": list(TARGET_AXIS_SCALE),
            "profile_surface": "FEATHERED_OPEN_SADDLE_NOT_ANNULAR_TUBE",
            "whole_body_bounds_unchanged": True,
        },
        "side_results": side_results,
        "form_metrics": {
            "baseline_vertices": baseline_checks["vertex_count"],
            "baseline_triangles": baseline_checks["triangle_count"],
            "refined_vertices": refined_checks["vertex_count"],
            "refined_triangles": refined_checks["triangle_count"],
            "candidate_vertices": candidate_checks["vertex_count"],
            "candidate_triangles": candidate_checks["triangle_count"],
            "added_vertices": candidate_checks["vertex_count"] - baseline_checks["vertex_count"],
            "added_triangles": candidate_checks["triangle_count"] - baseline_checks["triangle_count"],
        },
        "gates": {
            "prior-refined-identity-preserved": "PASS",
            "bounded-transition-only-source-delta": "PASS",
            "bilateral-symmetry": "PASS",
            "all-proximal-samples-inside-ribcage": "PASS",
            "distal-samples-exactly-reuse-upper-arm-root": "PASS",
            "transition-does-not-wrap-full-root-ring": "PASS",
            "whole-body-bounds-preserved": "PASS",
            "finite-nondegenerate-proof-mesh": "PASS",
            "art-direction-acceptance": "NOT_CLAIMED",
            "visual-qa-acceptance": "NOT_CLAIMED",
            "connected-topology-acceptance": "NOT_CLAIMED",
            "rigging-or-deformation-acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "derived Character-local review variant only; not accepted source migration",
            "0.085 m anchor-radius and 0.075 m upper-arm-root references are preserved; the change is transition profile, not another radius reduction",
            "eight exact root samples are feathered with reduced blend at both arc ends while the two most inferior root samples remain uncovered",
            "duplicate distal proof vertices are not connected production topology",
            "no anatomy/biology, rigging, deformation, materials, target-engine, Armor/Unit fit, runtime, gameplay, CANON, production readiness, or mastery claim",
        ],
    }


def _neutral_mesh(mesh):
    neutral = deepcopy(mesh)
    for region in neutral["regions"]:
        region["id"] = f"neutral_{region['id']}"
    return neutral


def build_feathered_shoulder_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    baseline = neutral_character_study()
    refined = refined_shoulder_bridge_candidate(baseline)
    candidate = feathered_shoulder_candidate(baseline)
    baseline_mesh = build_mesh(baseline)
    refined_mesh = build_shoulder_bridge_mesh(refined)
    candidate_mesh = build_feathered_shoulder_mesh(candidate)
    receipt = audit_feathered_shoulder(candidate)

    (out / "shoulder-transition-feathered.source.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-transition-feathered.mesh.json").write_text(
        json.dumps(candidate_mesh, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_obj(candidate_mesh, out / "shoulder-transition-feathered.obj")
    (out / "shoulder-transition-feathered-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    neutral_meshes = {
        "A — baseline detached": _neutral_mesh(baseline_mesh),
        "C — retained 0.085 circular bridge": _neutral_mesh(refined_mesh),
        "E — feathered open saddle": _neutral_mesh(candidate_mesh),
    }
    diagnostic_meshes = {
        "A — baseline detached": baseline_mesh,
        "C — retained 0.085 circular bridge": refined_mesh,
        "E — feathered open saddle": candidate_mesh,
    }
    for view in ("front", "top", "three-quarter"):
        (out / f"shoulder-transition-feathered-{view}.svg").write_text(
            _filled_comparison_svg(neutral_meshes, view), encoding="utf-8"
        )
        (out / f"shoulder-transition-feathered-{view}-diagnostic.svg").write_text(
            _filled_comparison_svg(diagnostic_meshes, view), encoding="utf-8"
        )
    return receipt
