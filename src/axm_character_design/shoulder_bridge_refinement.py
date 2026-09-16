from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .organic_form import canonical_digest, neutral_character_study, svg_wire, write_obj
from .shoulder_bridge_candidate import (
    audit_shoulder_bridge,
    build_shoulder_bridge_mesh,
    shoulder_bridge_candidate,
)

SCHEMA = "axm.character-shoulder-bridge-refinement/v0.1"
STATUS = "PASS_RESTRAINED_SHOULDER_BRIDGE_REVIEW_VARIANT"
VARIANT_ID = "character-neutral-a-shoulder-bridge-001-r0p085"
PREVIOUS_ANCHOR_RADIUS_M = 0.10
REFINED_ANCHOR_RADIUS_M = 0.085
EXPECTED_PREVIOUS_SOURCE_DIGEST = "efa9b7d93cb6101a7f1c59d30e88f88ceeb124c37b44140b21771420c4365a61"
EXPECTED_PREVIOUS_MESH_DIGEST = "6a1792607906a1d72822d96e72f86b0b6e0b108d2e242c42fcd40c5811f004e7"
EXPECTED_REFINED_SOURCE_DIGEST = "ca3f117b23ec41c6571cadbfe5f798a6982f228d12663aa07860d3e83fd9f236"
EXPECTED_REFINED_MESH_DIGEST = "160698abaeeca8323e1b12c237f023dbc1c8a46fb4b5d0493336ad0789fd6798"


def _rounded(value):
    return round(float(value), 12)


def _bridge_bounds(mesh):
    result = {}
    for region in mesh["regions"]:
        if not region["id"].startswith("shoulder_bridge_"):
            continue
        start = region["vertex_start"]
        end = start + region["vertex_count"]
        vertices = mesh["vertices"][start:end]
        result[region["id"]] = {
            "min": [_rounded(min(vertex[i] for vertex in vertices)) for i in range(3)],
            "max": [_rounded(max(vertex[i] for vertex in vertices)) for i in range(3)],
        }
    return result


def refined_shoulder_bridge_candidate(study=None):
    baseline = study or neutral_character_study()
    previous = shoulder_bridge_candidate(baseline)
    previous_mesh = build_shoulder_bridge_mesh(previous)
    if canonical_digest(previous) != EXPECTED_PREVIOUS_SOURCE_DIGEST:
        raise ValueError("previous shoulder candidate source identity drift")
    if canonical_digest(previous_mesh) != EXPECTED_PREVIOUS_MESH_DIGEST:
        raise ValueError("previous shoulder candidate mesh identity drift")

    refined = deepcopy(previous)
    for bridge in refined["shoulder_transition_regions"]:
        if float(bridge["radius_anchor_m"]) != PREVIOUS_ANCHOR_RADIUS_M:
            raise ValueError("unexpected previous bridge anchor radius")
        bridge["radius_anchor_m"] = REFINED_ANCHOR_RADIUS_M
    refined["shoulder_bridge_refinement"] = {
        "variant_id": VARIANT_ID,
        "prior_candidate_study_id": previous["study_id"],
        "prior_candidate_source_digest": EXPECTED_PREVIOUS_SOURCE_DIGEST,
        "prior_candidate_mesh_digest": EXPECTED_PREVIOUS_MESH_DIGEST,
        "changed_field": "shoulder_transition_regions[*].radius_anchor_m",
        "previous_value_m": PREVIOUS_ANCHOR_RADIUS_M,
        "refined_value_m": REFINED_ANCHOR_RADIUS_M,
        "status": "DERIVED_REVIEW_VARIANT_NOT_ACCEPTED_SOURCE",
    }
    return refined


def audit_shoulder_bridge_refinement(study=None):
    baseline = study or neutral_character_study()
    previous = shoulder_bridge_candidate(baseline)
    refined = refined_shoulder_bridge_candidate(baseline)
    previous_mesh = build_shoulder_bridge_mesh(previous)
    refined_mesh = build_shoulder_bridge_mesh(refined)
    previous_receipt = audit_shoulder_bridge(previous)
    refined_receipt = audit_shoulder_bridge(refined)

    if canonical_digest(previous) != EXPECTED_PREVIOUS_SOURCE_DIGEST:
        raise ValueError("previous shoulder candidate source identity drift")
    if canonical_digest(previous_mesh) != EXPECTED_PREVIOUS_MESH_DIGEST:
        raise ValueError("previous shoulder candidate mesh identity drift")
    if canonical_digest(refined) != EXPECTED_REFINED_SOURCE_DIGEST:
        raise ValueError("refined shoulder candidate source identity drift")
    if canonical_digest(refined_mesh) != EXPECTED_REFINED_MESH_DIGEST:
        raise ValueError("refined shoulder candidate mesh identity drift")

    normalized = deepcopy(refined)
    normalized.pop("shoulder_bridge_refinement")
    for bridge in normalized["shoulder_transition_regions"]:
        bridge["radius_anchor_m"] = PREVIOUS_ANCHOR_RADIUS_M
    if canonical_digest(normalized) != canonical_digest(previous):
        raise ValueError("refinement changed fields outside anchor radius")

    previous_by_side = {
        item["side"]: item for item in previous_receipt["shoulder_transition_observations"]
    }
    refined_by_side = {
        item["side"]: item for item in refined_receipt["shoulder_transition_observations"]
    }
    side_comparison = []
    for side in ("L", "R"):
        before = previous_by_side[side]
        after = refined_by_side[side]
        if after["bridge_proximal_ring_samples_inside_or_on_ribcage"] <= before[
            "bridge_proximal_ring_samples_inside_or_on_ribcage"
        ]:
            raise ValueError(f"refinement did not improve proximal overlap proxy: {side}")
        if after["bridge_distal_radius_m"] != before["bridge_distal_radius_m"]:
            raise ValueError(f"refinement changed distal bridge radius: {side}")
        if after["upper_arm_root_radius_m"] != before["upper_arm_root_radius_m"]:
            raise ValueError(f"refinement changed upper-arm root radius: {side}")
        side_comparison.append(
            {
                "side": side,
                "previous_proximal_ring_inside_or_on_ribcage": before[
                    "bridge_proximal_ring_samples_inside_or_on_ribcage"
                ],
                "refined_proximal_ring_inside_or_on_ribcage": after[
                    "bridge_proximal_ring_samples_inside_or_on_ribcage"
                ],
                "distal_radius_m": after["bridge_distal_radius_m"],
                "upper_arm_root_radius_m": after["upper_arm_root_radius_m"],
                "observation": "LOCAL_FORM_CONTINUITY_PROXY_NOT_DEFORMATION_GATE",
            }
        )

    previous_bounds = _bridge_bounds(previous_mesh)
    refined_bounds = _bridge_bounds(refined_mesh)
    for side in ("L", "R"):
        region_id = f"shoulder_bridge_{side}"
        before = previous_bounds[region_id]
        after = refined_bounds[region_id]
        previous_depth = before["max"][1] - before["min"][1]
        refined_depth = after["max"][1] - after["min"][1]
        if not refined_depth < previous_depth:
            raise ValueError(f"refinement did not reduce bridge depth envelope: {side}")

    if previous_receipt["form_metrics"] != refined_receipt["form_metrics"]:
        raise ValueError("refinement changed global count/bounds/A-rest metrics")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "variant_id": VARIANT_ID,
        "baseline_source_digest": previous_receipt["baseline_source_digest"],
        "baseline_mesh_digest": previous_receipt["baseline_mesh_digest"],
        "previous_candidate_source_digest": canonical_digest(previous),
        "previous_candidate_mesh_digest": canonical_digest(previous_mesh),
        "refined_candidate_source_digest": canonical_digest(refined),
        "refined_candidate_mesh_digest": canonical_digest(refined_mesh),
        "bounded_delta": {
            "changed_field": "shoulder_transition_regions[*].radius_anchor_m",
            "previous_anchor_radius_m": PREVIOUS_ANCHOR_RADIUS_M,
            "refined_anchor_radius_m": REFINED_ANCHOR_RADIUS_M,
            "absolute_reduction_m": _rounded(PREVIOUS_ANCHOR_RADIUS_M - REFINED_ANCHOR_RADIUS_M),
            "relative_reduction": _rounded(
                (PREVIOUS_ANCHOR_RADIUS_M - REFINED_ANCHOR_RADIUS_M)
                / PREVIOUS_ANCHOR_RADIUS_M
            ),
            "other_candidate_fields_preserved": True,
        },
        "side_comparison": side_comparison,
        "previous_bridge_bounds_m": previous_bounds,
        "refined_bridge_bounds_m": refined_bounds,
        "global_form_metrics": refined_receipt["form_metrics"],
        "gates": {
            "previous-candidate-identity-preserved": "PASS",
            "single-field-radius-refinement": "PASS",
            "proximal-overlap-proxy-improved-bilaterally": "PASS",
            "local-depth-envelope-reduced-bilaterally": "PASS",
            "distal-radius-and-upper-arm-root-match-preserved": "PASS",
            "whole-body-bounds-and-a-rest-preserved": "PASS",
            "art-direction-acceptance": "NOT_CLAIMED",
            "visual-qa-acceptance": "NOT_CLAIMED",
            "connected-topology-acceptance": "NOT_CLAIMED",
            "rigging-or-deformation-acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "this is a derived review variant of the existing tapered shoulder candidate, not an accepted Character source migration",
            "the only modeled parameter change is bilateral bridge anchor radius 0.10 m -> 0.085 m",
            "increased proximal ring overlap is a local source-form continuity proxy, not anatomy, skinning, or deformation acceptance",
            "reduced local bridge depth/envelope is geometric evidence only; Art Direction and Visual QA still own perceptual acceptance",
            "no connected production topology, rigging, weights, animation, materials, target runtime, gameplay, CANON, or mastery claim",
        ],
    }


def build_shoulder_bridge_refinement_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    baseline = neutral_character_study()
    previous = shoulder_bridge_candidate(baseline)
    refined = refined_shoulder_bridge_candidate(baseline)
    previous_mesh = build_shoulder_bridge_mesh(previous)
    refined_mesh = build_shoulder_bridge_mesh(refined)
    receipt = audit_shoulder_bridge_refinement(baseline)

    (out / "shoulder-bridge-refinement.source.json").write_text(
        json.dumps(refined, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-bridge-refinement.mesh.json").write_text(
        json.dumps(refined_mesh, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_obj(refined_mesh, out / "shoulder-bridge-refinement.obj")
    for view in ("front", "side", "top"):
        (out / f"shoulder-bridge-v0.2-{view}.svg").write_text(
            svg_wire(previous_mesh, view, previous["study_id"]), encoding="utf-8"
        )
        (out / f"shoulder-bridge-refined-{view}.svg").write_text(
            svg_wire(refined_mesh, view, VARIANT_ID), encoding="utf-8"
        )
    (out / "shoulder-bridge-refinement-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt
