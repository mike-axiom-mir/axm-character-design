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
from .shoulder_source_lineage import adopted_character_source, build_adopted_character_mesh
from .shoulder_transition_profile import _filled_comparison_svg

SCHEMA = "axm.character-shoulder-pose-clearance-neutral-filled-review/v0.1"
STATUS = "PASS_EXACT_NEUTRAL_FILLED_REVIEW_PACKET_RETAINED"
VIEWS = ("front", "top", "three-quarter")


def _neutral_mesh(mesh):
    neutral = deepcopy(mesh)
    for region in neutral["regions"]:
        region["id"] = f"neutral_{region['id']}"
    return neutral


def audit_shoulder_pose_clearance_visual_review():
    parent = adopted_character_source()
    candidate = shoulder_pose_clearance_candidate()
    parent_mesh = build_adopted_character_mesh(parent)
    candidate_mesh = build_adopted_character_mesh(candidate)

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
        "comparison_labels": [
            "Parent accepted E",
            "Review candidate 005",
        ],
        "render_scope": "STATIC_NEUTRAL_RENDERER_NEUTRAL_FILLED_PROJECTION_EVIDENCE_ONLY",
        "gates": {
            "exact_parent_identity": "PASS",
            "exact_review_identity": "PASS",
            "same_proof_mesh_counts": "PASS",
            "same_whole_body_bounds": "PASS",
            "visual_acceptance": "NOT_EVALUATED",
            "connected_topology_rebind": "NOT_EVALUATED",
            "rigging_or_deformation_rebind": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoff": (
            "Art Direction / Visual QA can now compare the exact accepted-E parent and review-005 "
            "through matched neutral filled front, top and true three-quarter projections. Judge "
            "shoulder width, upper-arm direction, mass hierarchy, silhouette and any return of "
            "pinch, collar, ruff, bulb or epaulet reads. These projections are evidence only and "
            "do not transfer Geometry or Rigging acceptance."
        ),
        "truth_boundary": [
            "This packet adds review evidence only; it changes no Character source, mesh, topology, weights or poses.",
            "The filled projections are renderer-neutral review aids, not target-engine shading evidence.",
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
    receipt = audit_shoulder_pose_clearance_visual_review()

    neutral_meshes = {
        "Parent accepted E": _neutral_mesh(parent_mesh),
        "Review candidate 005": _neutral_mesh(candidate_mesh),
    }
    for view in VIEWS:
        (out / f"shoulder-pose-clearance-filled-{view}.svg").write_text(
            _filled_comparison_svg(neutral_meshes, view), encoding="utf-8"
        )
    (out / "shoulder-pose-clearance-visual-review.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
