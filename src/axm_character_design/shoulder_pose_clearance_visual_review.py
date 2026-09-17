from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .organic_form import canonical_digest, mesh_checks
from .shoulder_pose_clearance_candidate import (
    EXPECTED_CANDIDATE_MESH_DIGEST,
    EXPECTED_CANDIDATE_SOURCE_DIGEST,
    EXPECTED_PARENT_MESH_DIGEST,
    EXPECTED_PARENT_SOURCE_DIGEST,
    VARIANT_ID,
    shoulder_pose_clearance_candidate,
)
from .shoulder_pose_elbow_chain_context import audit_shoulder_pose_elbow_chain_context
from .shoulder_source_lineage import adopted_character_source, build_adopted_character_mesh
from .shoulder_transition_profile import _filled_comparison_svg

SCHEMA = "axm.character-shoulder-pose-clearance-neutral-filled-review/v0.2"
STATUS = "PASS_EXACT_NEUTRAL_FILLED_AND_LANDMARK_CHAIN_REVIEW_PACKET_RETAINED"
VIEWS = ("front", "top", "three-quarter")
LANDMARK_CHAIN_VIEW = "shoulder-pose-clearance-elbow-chain-front.svg"


def _neutral_mesh(mesh):
    neutral = deepcopy(mesh)
    for region in neutral["regions"]:
        region["id"] = f"neutral_{region['id']}"
    return neutral


def _project_front(point, panel_x):
    x = float(point[0])
    z = float(point[2])
    return panel_x + 200.0 + (x * 280.0), 240.0 - ((z - 1.30) * 360.0)


def _landmark_chain_panel(source, panel_x, title, flexion_deg):
    lines = [
        f'<rect x="{panel_x}" y="0" width="400" height="360" fill="white" stroke="#777"/>',
        f'<text x="{panel_x + 20}" y="28" font-family="monospace" font-size="16">{title}</text>',
        f'<text x="{panel_x + 20}" y="50" font-family="monospace" font-size="13">neutral elbow-chain bend: {flexion_deg:.12f} deg from straight</text>',
    ]
    landmarks = source["landmarks"]
    for side in ("L", "R"):
        names = (f"shoulder_{side}", f"elbow_{side}", f"wrist_{side}")
        projected = [_project_front(landmarks[name], panel_x) for name in names]
        path = " ".join(
            f"{command}{x:.3f},{y:.3f}"
            for command, (x, y) in zip(("M", "L", "L"), projected)
        )
        lines.append(f'<path d="{path}" fill="none" stroke="#111" stroke-width="3"/>')
        for name, (x, y) in zip(names, projected):
            lines.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="5" fill="white" stroke="#111" stroke-width="2"/>')
            label = name.replace(f"_{side}", "")
            dx = -68 if side == "L" else 10
            lines.append(
                f'<text x="{x + dx:.3f}" y="{y - 8:.3f}" font-family="monospace" font-size="12">{side} {label}</text>'
            )
    return "\n".join(lines)


def _elbow_chain_comparison_svg(parent, candidate, elbow_context):
    parent_flex = elbow_context["parent_elbow_chain_context"]["landmark_flexion_from_straight_deg"]
    candidate_flex = elbow_context["candidate_elbow_chain_context"]["landmark_flexion_from_straight_deg"]
    increase = elbow_context["candidate_minus_parent_flexion_from_straight_deg"]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="820" height="410" viewBox="0 0 820 410">\n'
        '<rect width="820" height="410" fill="white"/>\n'
        + _landmark_chain_panel(parent, 0.0, "Parent accepted E", parent_flex)
        + "\n"
        + _landmark_chain_panel(candidate, 420.0, "Review candidate 005", candidate_flex)
        + "\n"
        + f'<text x="20" y="392" font-family="monospace" font-size="14">review-005 minus parent neutral bend: +{increase:.12f} deg; source-form context only, not rig/anatomy acceptance</text>\n'
        + '</svg>\n'
    )


def audit_shoulder_pose_clearance_visual_review():
    parent = adopted_character_source()
    candidate = shoulder_pose_clearance_candidate()
    parent_mesh = build_adopted_character_mesh(parent)
    candidate_mesh = build_adopted_character_mesh(candidate)
    elbow_context = audit_shoulder_pose_elbow_chain_context()

    parent_source_digest = canonical_digest(parent)
    parent_mesh_digest = canonical_digest(parent_mesh)
    candidate_source_digest = canonical_digest(candidate)
    candidate_mesh_digest = canonical_digest(candidate_mesh)

    if parent_source_digest != EXPECTED_PARENT_SOURCE_DIGEST:
        raise ValueError("parent Character source digest drift")
    if parent_mesh_digest != EXPECTED_PARENT_MESH_DIGEST:
        raise ValueError("parent Character proof-mesh digest drift")
    if candidate_source_digest != EXPECTED_CANDIDATE_SOURCE_DIGEST:
        raise ValueError("review candidate source digest drift")
    if candidate_mesh_digest != EXPECTED_CANDIDATE_MESH_DIGEST:
        raise ValueError("review candidate proof-mesh digest drift")
    if candidate.get("study_id") != VARIANT_ID:
        raise ValueError("review candidate ID drift")
    if elbow_context["parent_source_digest"] != parent_source_digest:
        raise ValueError("elbow-chain parent identity drift")
    if elbow_context["candidate_source_digest"] != candidate_source_digest:
        raise ValueError("elbow-chain candidate identity drift")

    parent_checks = mesh_checks(parent_mesh)
    candidate_checks = mesh_checks(candidate_mesh)
    if parent_checks["vertex_count"] != candidate_checks["vertex_count"]:
        raise ValueError("review packet source mesh vertex-count drift")
    if parent_checks["triangle_count"] != candidate_checks["triangle_count"]:
        raise ValueError("review packet source mesh triangle-count drift")
    if parent_checks["bounds_min"] != candidate_checks["bounds_min"]:
        raise ValueError("review packet changed whole-body minimum bounds")
    if parent_checks["bounds_max"] != candidate_checks["bounds_max"]:
        raise ValueError("review packet changed whole-body maximum bounds")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "review_candidate": VARIANT_ID,
        "parent_source_digest": parent_source_digest,
        "parent_mesh_digest": parent_mesh_digest,
        "candidate_source_digest": candidate_source_digest,
        "candidate_mesh_digest": candidate_mesh_digest,
        "neutral_filled_views": [
            f"shoulder-pose-clearance-filled-{view}.svg" for view in VIEWS
        ],
        "landmark_chain_view": LANDMARK_CHAIN_VIEW,
        "landmark_chain_context": {
            "parent_flexion_from_straight_deg": elbow_context["parent_elbow_chain_context"]["landmark_flexion_from_straight_deg"],
            "candidate_flexion_from_straight_deg": elbow_context["candidate_elbow_chain_context"]["landmark_flexion_from_straight_deg"],
            "candidate_minus_parent_flexion_from_straight_deg": elbow_context["candidate_minus_parent_flexion_from_straight_deg"],
        },
        "comparison_labels": [
            "Parent accepted E",
            "Review candidate 005",
        ],
        "render_scope": "STATIC_NEUTRAL_RENDERER_NEUTRAL_FILLED_PLUS_SOURCE_LANDMARK_CHAIN_EVIDENCE_ONLY",
        "gates": {
            "exact_parent_identity": "PASS",
            "exact_review_identity": "PASS",
            "same_proof_mesh_counts": "PASS",
            "same_whole_body_bounds": "PASS",
            "exact_elbow_chain_context_bound": "PASS",
            "visual_acceptance": "NOT_EVALUATED",
            "connected_topology_rebind": "NOT_EVALUATED",
            "rigging_or_deformation_rebind": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoff": (
            "Art Direction / Visual QA can compare the exact accepted-E parent and review-005 "
            "through matched neutral filled front, top and true three-quarter projections plus "
            "an exact front source-landmark-chain overlay. The overlay makes the already-measured "
            "+18.679036523327 deg neutral elbow-chain bend visible without changing either form. "
            "Judge shoulder width, upper-arm direction, elbow-chain read, mass hierarchy, silhouette "
            "and any return of pinch, collar, ruff, bulb or epaulet reads. These projections are "
            "evidence only and do not transfer Geometry or Rigging acceptance."
        ),
        "truth_boundary": [
            "This packet adds review evidence only; it changes no Character source, mesh, topology, weights or poses.",
            "The filled projections are renderer-neutral review aids, not target-engine shading evidence.",
            "The landmark-chain overlay projects exact source shoulder/elbow/wrist coordinates in front view and binds the existing elbow-chain context; it is not a skeletal rig drawing or anatomy claim.",
            "Exact source and proof-mesh digests are pinned so the visual packet cannot silently drift away from review-005.",
            "No anatomy or biology correctness, visual acceptance, connected topology, self-intersection freedom, rigging, weighting, continuous deformation, Animation, runtime, gameplay, CANON, production readiness or Organic Form mastery is claimed.",
        ],
    }


def build_shoulder_pose_clearance_visual_review_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    parent = adopted_character_source()
    candidate = shoulder_pose_clearance_candidate()
    parent_mesh = build_adopted_character_mesh(parent)
    candidate_mesh = build_adopted_character_mesh(candidate)
    elbow_context = audit_shoulder_pose_elbow_chain_context()
    receipt = audit_shoulder_pose_clearance_visual_review()

    neutral_meshes = {
        "Parent accepted E": _neutral_mesh(parent_mesh),
        "Review candidate 005": _neutral_mesh(candidate_mesh),
    }
    for view in VIEWS:
        (out / f"shoulder-pose-clearance-filled-{view}.svg").write_text(
            _filled_comparison_svg(neutral_meshes, view), encoding="utf-8"
        )
    (out / LANDMARK_CHAIN_VIEW).write_text(
        _elbow_chain_comparison_svg(parent, candidate, elbow_context), encoding="utf-8"
    )
    (out / "shoulder-pose-clearance-visual-review.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
