from __future__ import annotations

from copy import deepcopy
import json
import math
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

SCHEMA = "axm.character-shoulder-transition-profile/v0.1"
STATUS = "PASS_BOUNDED_DIRECTIONAL_SHOULDER_PROFILE_CANDIDATE"
VARIANT_ID = "character-neutral-a-shoulder-transition-profile-002"
DISTAL_ROOT_RING_INDICES = (5, 6, 7, 8, 9, 0)
PROXIMAL_AXIS_SCALE = (0.55, 0.55, 0.85)


def _rounded(value):
    return round(float(value), 12)


def _ellipsoid_implicit(point, mass):
    return sum(
        ((point[i] - mass["center"][i]) / mass["radii"][i]) ** 2
        for i in range(3)
    )


def directional_shoulder_profile_candidate(study=None):
    baseline = study or neutral_character_study()
    refined = refined_shoulder_bridge_candidate(baseline)
    if canonical_digest(refined) != EXPECTED_REFINED_SOURCE_DIGEST:
        raise ValueError("refined shoulder candidate source identity drift")
    if canonical_digest(build_shoulder_bridge_mesh(refined)) != EXPECTED_REFINED_MESH_DIGEST:
        raise ValueError("refined shoulder candidate mesh identity drift")

    candidate = deepcopy(refined)
    candidate["study_id"] = VARIANT_ID
    candidate["intent"] = (
        "stylized_human_like_biped_form_study_with_bilateral_directional_open_shoulder_saddles"
    )
    for bridge in candidate["shoulder_transition_regions"]:
        if float(bridge["radius_anchor_m"]) != REFINED_ANCHOR_RADIUS_M:
            raise ValueError("unexpected refined anchor radius")
        if float(bridge["radius_shoulder_m"]) != 0.075:
            raise ValueError("unexpected upper-arm root radius")
        bridge["profile_kind"] = "OPEN_SUPERIOR_SADDLE_NOT_ANNULAR_TUBE"
        bridge["distal_root_ring_indices"] = list(DISTAL_ROOT_RING_INDICES)
        bridge["proximal_world_axis_scale"] = list(PROXIMAL_AXIS_SCALE)
        bridge["open_underarm_sector"] = True

    candidate["shoulder_profile_repair"] = {
        "schema": SCHEMA,
        "variant_id": VARIANT_ID,
        "prior_refined_source_digest": EXPECTED_REFINED_SOURCE_DIGEST,
        "prior_refined_mesh_digest": EXPECTED_REFINED_MESH_DIGEST,
        "changed_form_language": (
            "replace_complete_circular_bridge_surface_with_open_superior_directional_saddle"
        ),
        "anchor_radius_reference_m": REFINED_ANCHOR_RADIUS_M,
        "upper_arm_root_radius_reference_m": 0.075,
        "distal_root_ring_indices": list(DISTAL_ROOT_RING_INDICES),
        "proximal_world_axis_scale": list(PROXIMAL_AXIS_SCALE),
        "status": "DERIVED_REVIEW_VARIANT_NOT_ACCEPTED_SOURCE",
    }
    validate_study(candidate)
    return candidate


def _patch_geometry(candidate, side):
    landmarks = candidate["landmarks"]
    segments = {segment["id"]: segment for segment in candidate["segments"]}
    bridges = {item["id"]: item for item in candidate["shoulder_transition_regions"]}
    bridge = bridges[f"shoulder_bridge_{side}"]
    upper_arm = segments[f"upper_arm_{side}"]
    shoulder = landmarks[bridge["shoulder_landmark"]]
    elbow = landmarks[upper_arm["b"]]

    root_vertices, _ = _segment_mesh(
        shoulder,
        elbow,
        float(upper_arm["radius_a"]),
        float(upper_arm["radius_b"]),
        sides=10,
    )
    root_ring = root_vertices[:10]
    distal = [list(root_ring[index]) for index in DISTAL_ROOT_RING_INDICES]
    anchor = bridge["anchor"]
    sx, sy, sz = PROXIMAL_AXIS_SCALE
    proximal = []
    for point in distal:
        radial = [point[i] - shoulder[i] for i in range(3)]
        proximal.append(
            [
                anchor[0] + radial[0] * sx,
                anchor[1] + radial[1] * sy,
                anchor[2] + radial[2] * sz,
            ]
        )

    vertices = proximal + distal
    count = len(distal)
    faces = []
    for index in range(count - 1):
        nxt = index + 1
        faces.append([index, nxt, count + nxt])
        faces.append([index, count + nxt, count + index])

    return {
        "vertices": vertices,
        "faces": faces,
        "proximal": proximal,
        "distal": distal,
        "full_upper_arm_root_ring": root_ring,
    }


def build_directional_shoulder_profile_mesh(candidate=None):
    candidate = candidate or directional_shoulder_profile_candidate()
    validate_study(candidate)
    mesh = build_mesh(candidate)
    vertices = list(mesh["vertices"])
    faces = list(mesh["faces"])
    regions = list(mesh["regions"])

    for side in ("L", "R"):
        patch = _patch_geometry(candidate, side)
        vertex_start = len(vertices)
        face_start = len(faces)
        vertices.extend(patch["vertices"])
        faces.extend([[index + vertex_start for index in face] for face in patch["faces"]])
        regions.append(
            {
                "id": f"shoulder_profile_{side}",
                "vertex_start": vertex_start,
                "vertex_count": len(patch["vertices"]),
                "face_start": face_start,
                "face_count": len(patch["faces"]),
            }
        )

    return {"vertices": vertices, "faces": faces, "regions": regions}


def _normalized_back_to_refined(candidate):
    normalized = deepcopy(candidate)
    normalized.pop("shoulder_profile_repair")
    refined = refined_shoulder_bridge_candidate(neutral_character_study())
    normalized["study_id"] = refined["study_id"]
    normalized["intent"] = refined["intent"]
    for bridge in normalized["shoulder_transition_regions"]:
        bridge.pop("profile_kind")
        bridge.pop("distal_root_ring_indices")
        bridge.pop("proximal_world_axis_scale")
        bridge.pop("open_underarm_sector")
    return normalized


def audit_directional_shoulder_profile(candidate=None):
    baseline = neutral_character_study()
    refined = refined_shoulder_bridge_candidate(baseline)
    candidate = candidate or directional_shoulder_profile_candidate(baseline)
    validate_study(candidate)

    if canonical_digest(refined) != EXPECTED_REFINED_SOURCE_DIGEST:
        raise ValueError("refined shoulder candidate source identity drift")
    if canonical_digest(build_shoulder_bridge_mesh(refined)) != EXPECTED_REFINED_MESH_DIGEST:
        raise ValueError("refined shoulder candidate mesh identity drift")
    if canonical_digest(_normalized_back_to_refined(candidate)) != canonical_digest(refined):
        raise ValueError("profile candidate changed fields outside the bounded local profile delta")

    refined_mesh = build_shoulder_bridge_mesh(refined)
    candidate_mesh = build_directional_shoulder_profile_mesh(candidate)
    baseline_mesh = build_mesh(baseline)
    refined_checks = mesh_checks(refined_mesh)
    candidate_checks = mesh_checks(candidate_mesh)
    baseline_checks = mesh_checks(baseline_mesh)

    if candidate_checks["bounds_min"] != baseline_checks["bounds_min"]:
        raise ValueError("profile candidate changed whole-body minimum bounds")
    if candidate_checks["bounds_max"] != baseline_checks["bounds_max"]:
        raise ValueError("profile candidate changed whole-body maximum bounds")
    if canonical_digest(candidate_mesh) == canonical_digest(refined_mesh):
        raise ValueError("profile candidate mesh unexpectedly identical to circular refinement")

    masses = {mass["id"]: mass for mass in baseline["masses"]}
    ribcage = masses["ribcage"]
    side_results = []
    vertex_sets = {}
    for side in ("L", "R"):
        patch = _patch_geometry(candidate, side)
        proximal_values = [_ellipsoid_implicit(point, ribcage) for point in patch["proximal"]]
        proximal_inside = sum(value <= 1.0 + 1e-9 for value in proximal_values)
        if proximal_inside != len(patch["proximal"]):
            raise ValueError(f"profile proximal saddle escaped ribcage envelope: {side}")

        expected_distal = [
            patch["full_upper_arm_root_ring"][index] for index in DISTAL_ROOT_RING_INDICES
        ]
        if patch["distal"] != expected_distal:
            raise ValueError(f"profile distal saddle lost exact upper-arm root binding: {side}")

        count = len(DISTAL_ROOT_RING_INDICES)
        if any(
            (0 in face and count - 1 in face)
            or (count in face and (2 * count) - 1 in face)
            for face in patch["faces"]
        ):
            raise ValueError(f"profile patch wrapped its open arc: {side}")

        vertex_sets[side] = {
            tuple(_rounded(value) for value in vertex) for vertex in patch["vertices"]
        }
        side_results.append(
            {
                "side": side,
                "proximal_samples_inside_or_on_ribcage": proximal_inside,
                "proximal_sample_count": len(patch["proximal"]),
                "distal_samples_exactly_on_upper_arm_root_ring": len(expected_distal),
                "distal_root_ring_sample_count": len(DISTAL_ROOT_RING_INDICES),
                "upper_arm_root_ring_total_samples": 10,
                "open_root_sector_samples_not_covered": 10 - len(DISTAL_ROOT_RING_INDICES),
                "patch_vertices": len(patch["vertices"]),
                "patch_triangles": len(patch["faces"]),
                "observation": "STRUCTURAL_OPEN_SADDLE_PROXY_NOT_VISUAL_ACCEPTANCE",
            }
        )

    mirrored_left = {
        (_rounded(-vertex[0]), _rounded(vertex[1]), _rounded(vertex[2]))
        for vertex in vertex_sets["L"]
    }
    if mirrored_left != vertex_sets["R"]:
        raise ValueError("profile patch bilateral geometry drift")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "variant_id": VARIANT_ID,
        "baseline_source_digest": canonical_digest(baseline),
        "refined_source_digest": canonical_digest(refined),
        "refined_mesh_digest": canonical_digest(refined_mesh),
        "profile_candidate_source_digest": canonical_digest(candidate),
        "profile_candidate_mesh_digest": canonical_digest(candidate_mesh),
        "bounded_delta": {
            "prior_refined_candidate_preserved": True,
            "anchor_radius_reference_m": REFINED_ANCHOR_RADIUS_M,
            "upper_arm_root_radius_reference_m": 0.075,
            "distal_root_ring_indices": list(DISTAL_ROOT_RING_INDICES),
            "proximal_world_axis_scale": list(PROXIMAL_AXIS_SCALE),
            "profile_surface": "OPEN_SUPERIOR_SADDLE_NOT_ANNULAR_TUBE",
            "whole_body_bounds_unchanged": True,
        },
        "side_results": side_results,
        "form_metrics": {
            "baseline_vertices": baseline_checks["vertex_count"],
            "baseline_triangles": baseline_checks["triangle_count"],
            "refined_vertices": refined_checks["vertex_count"],
            "refined_triangles": refined_checks["triangle_count"],
            "profile_candidate_vertices": candidate_checks["vertex_count"],
            "profile_candidate_triangles": candidate_checks["triangle_count"],
            "profile_added_vertices": candidate_checks["vertex_count"] - baseline_checks["vertex_count"],
            "profile_added_triangles": candidate_checks["triangle_count"] - baseline_checks["triangle_count"],
        },
        "gates": {
            "prior-refined-source-and-mesh-identity-preserved": "PASS",
            "bounded-profile-only-source-delta": "PASS",
            "bilateral-profile-symmetry": "PASS",
            "all-proximal-saddle-samples-inside-ribcage": "PASS",
            "distal-saddle-exactly-reuses-upper-arm-root-samples": "PASS",
            "transition-surface-does-not-wrap-full-root-ring": "PASS",
            "whole-body-bounds-preserved": "PASS",
            "finite-nondegenerate-proof-mesh": "PASS",
            "art-direction-acceptance": "NOT_CLAIMED",
            "visual-qa-acceptance": "NOT_CLAIMED",
            "connected-topology-acceptance": "NOT_CLAIMED",
            "rigging-or-deformation-acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "this is one Character-local review candidate responding to the named mechanical-collar visual defect; it is not accepted source migration",
            "the 0.085 m anchor-radius and 0.075 m upper-arm-root references are preserved; the modeled change is the transition surface profile, not another scalar radius reduction",
            "the proof patch covers only six exact upper-arm root samples and remains open on the underarm sector; this structural fact does not by itself prove the collar read is gone",
            "the patch uses disconnected duplicate vertices at the distal root for proof continuity and is not connected production topology",
            "no anatomical or biological correctness, rigging, deformation, materials, target-engine look, Armor/Unit fit, runtime, gameplay, CANON, production readiness, or Organic Form mastery claim",
        ],
    }


def _v_sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _v_dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _v_cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _v_norm(v):
    length = math.sqrt(_v_dot(v, v))
    if length == 0:
        raise ValueError("zero-length camera vector")
    return [value / length for value in v]


def _project_vertex(vertex, view):
    if view == "front":
        return (vertex[0], vertex[2], vertex[1])
    if view == "top":
        return (vertex[0], vertex[1], vertex[2])
    if view != "three-quarter":
        raise ValueError(view)

    eye = [2.35, 2.15, 1.95]
    target = [0.0, 0.0, 1.05]
    forward = _v_norm(_v_sub(target, eye))
    right = _v_norm(_v_cross(forward, [0.0, 0.0, 1.0]))
    up = _v_cross(right, forward)
    rel = _v_sub(vertex, eye)
    depth = _v_dot(rel, forward)
    if depth <= 0:
        raise ValueError("camera projection crossed near plane")
    focal = 1.35
    return (
        focal * _v_dot(rel, right) / depth,
        focal * _v_dot(rel, up) / depth,
        depth,
    )


def _highlight_face_indices(mesh):
    result = set()
    for region in mesh["regions"]:
        if not region["id"].startswith("shoulder_"):
            continue
        if "profile" not in region["id"] and "bridge" not in region["id"]:
            continue
        for index in range(region["face_start"], region["face_start"] + region["face_count"]):
            result.add(index)
    return result


def _filled_comparison_svg(meshes, view):
    projected = {
        label: [_project_vertex(vertex, view) for vertex in mesh["vertices"]]
        for label, mesh in meshes.items()
    }
    all_points = [point for points in projected.values() for point in points]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)

    panel_w = 430
    panel_h = 700
    margin = 34
    gap = 18
    width = len(meshes) * panel_w + (len(meshes) - 1) * gap
    height = panel_h
    scale = min((panel_w - 2 * margin) / span_x, (panel_h - 2 * margin - 34) / span_y)

    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f4f4f4"/>',
    ]
    for panel_index, (label, mesh) in enumerate(meshes.items()):
        offset_x = panel_index * (panel_w + gap)
        points = projected[label]
        face_order = []
        for face_index, face in enumerate(mesh["faces"]):
            depth = sum(points[index][2] for index in face) / 3.0
            face_order.append((depth, face_index, face))
        face_order.sort(reverse=True)
        highlight = _highlight_face_indices(mesh)
        chunks.append(
            f'<rect x="{offset_x}" y="0" width="{panel_w}" height="{panel_h}" fill="#ffffff" stroke="#b8b8b8"/>'
        )
        chunks.append(
            f'<text x="{offset_x + panel_w / 2:.1f}" y="24" text-anchor="middle" font-family="sans-serif" font-size="16">{label}</text>'
        )
        for _, face_index, face in face_order:
            coords = []
            for vertex_index in face:
                px, py, _ = points[vertex_index]
                sx = offset_x + margin + (px - min_x) * scale
                sy = panel_h - margin - (py - min_y) * scale
                coords.append(f"{sx:.2f},{sy:.2f}")
            if face_index in highlight:
                fill = "#8a8a8a"
                stroke = "#3f3f3f"
            else:
                fill = "#d5d5d5"
                stroke = "#8f8f8f"
            chunks.append(
                f'<polygon points="{" ".join(coords)}" fill="{fill}" stroke="{stroke}" stroke-width="0.45"/>'
            )
    chunks.append("</svg>")
    return "\n".join(chunks)


def build_directional_shoulder_profile_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    baseline = neutral_character_study()
    refined = refined_shoulder_bridge_candidate(baseline)
    candidate = directional_shoulder_profile_candidate(baseline)
    baseline_mesh = build_mesh(baseline)
    refined_mesh = build_shoulder_bridge_mesh(refined)
    candidate_mesh = build_directional_shoulder_profile_mesh(candidate)
    receipt = audit_directional_shoulder_profile(candidate)

    (out / "shoulder-transition-profile.source.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-transition-profile.mesh.json").write_text(
        json.dumps(candidate_mesh, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_obj(candidate_mesh, out / "shoulder-transition-profile.obj")
    (out / "shoulder-transition-profile-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    meshes = {
        "A — baseline detached": baseline_mesh,
        "C — retained 0.085 circular bridge": refined_mesh,
        "D — directional open saddle": candidate_mesh,
    }
    for view in ("front", "top", "three-quarter"):
        (out / f"shoulder-transition-profile-{view}.svg").write_text(
            _filled_comparison_svg(meshes, view), encoding="utf-8"
        )
    return receipt
