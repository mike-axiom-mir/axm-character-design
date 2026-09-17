from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path

from .organic_form import canonical_digest
from .shoulder_pose_clearance_candidate import (
    EXPECTED_CANDIDATE_MESH_DIGEST as EXPECTED_REVIEW005_MESH_DIGEST,
    EXPECTED_CANDIDATE_SOURCE_DIGEST as EXPECTED_REVIEW005_SOURCE_DIGEST,
    EXPECTED_PARENT_MESH_DIGEST,
    EXPECTED_PARENT_SOURCE_DIGEST,
    shoulder_pose_clearance_candidate,
)
from .shoulder_pose_clearance_refinement import shoulder_pose_clearance_refinement_candidate
from .shoulder_source_lineage import adopted_character_source, build_adopted_character_mesh

SCHEMA = "axm.character-shoulder-pose-clearance-spatial-context/v0.1"
STATUS = "PASS_REVIEW006_SOURCE_LANDMARK_SPATIAL_CONTEXT_RETAINED"
EXPECTED_REVIEW006_SOURCE_DIGEST = "8e9252ede4d257509e4eacb595f1c234aa100a42dc46a54b7b45550f2619c5e1"
EXPECTED_REVIEW006_MESH_DIGEST = "f173b2af9b7bf69ca78bce2ec2daa07a083748590d9ae9e99443962a6d1aa8e7"
MIN_REVIEW005_OFFSET_REDUCTION_M = 0.010


def _sub(a, b):
    return [float(a[i]) - float(b[i]) for i in range(3)]


def _add(a, b):
    return [float(a[i]) + float(b[i]) for i in range(3)]


def _mul(v, scalar):
    return [float(value) * float(scalar) for value in v]


def _dot(a, b):
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _norm(v):
    return math.sqrt(_dot(v, v))


def _distance(a, b):
    return math.dist(tuple(float(value) for value in a), tuple(float(value) for value in b))


def landmark_chain_spatial_context(source, side="R"):
    landmarks = source["landmarks"]
    shoulder = landmarks[f"shoulder_{side}"]
    elbow = landmarks[f"elbow_{side}"]
    wrist = landmarks[f"wrist_{side}"]
    chord = _sub(wrist, shoulder)
    chord_sq = _dot(chord, chord)
    if chord_sq <= 0.0:
        raise ValueError("zero-length shoulder-to-wrist chord")
    shoulder_to_elbow = _sub(elbow, shoulder)
    projection_t = _dot(shoulder_to_elbow, chord) / chord_sq
    projected = _add(shoulder, _mul(chord, projection_t))
    elbow_offset = _distance(elbow, projected)
    chord_length = math.sqrt(chord_sq)
    upper = _distance(shoulder, elbow)
    lower = _distance(elbow, wrist)
    path_excess = upper + lower - chord_length
    if path_excess < -1e-12:
        raise ValueError("arm landmark chain violates triangle inequality")
    return {
        "side": side,
        "shoulder": [float(value) for value in shoulder],
        "elbow": [float(value) for value in elbow],
        "wrist": [float(value) for value in wrist],
        "shoulder_to_wrist_chord_m": chord_length,
        "elbow_projection_fraction_along_chord": projection_t,
        "elbow_projection_point": projected,
        "elbow_perpendicular_offset_from_chord_m": elbow_offset,
        "landmark_chain_length_m": upper + lower,
        "landmark_chain_excess_over_chord_m": max(0.0, path_excess),
        "upper_arm_landmark_length_m": upper,
        "lower_arm_landmark_length_m": lower,
    }


def _require_bilateral_context(source, label):
    left = landmark_chain_spatial_context(source, "L")
    right = landmark_chain_spatial_context(source, "R")
    scalar_keys = (
        "shoulder_to_wrist_chord_m",
        "elbow_projection_fraction_along_chord",
        "elbow_perpendicular_offset_from_chord_m",
        "landmark_chain_length_m",
        "landmark_chain_excess_over_chord_m",
        "upper_arm_landmark_length_m",
        "lower_arm_landmark_length_m",
    )
    for key in scalar_keys:
        if abs(float(left[key]) - float(right[key])) > 1e-12:
            raise ValueError(f"{label} bilateral spatial-context drift: {key}")
    return {"left": left, "right": right}


def audit_shoulder_pose_clearance_spatial_context(review006=None):
    parent = adopted_character_source()
    review005 = shoulder_pose_clearance_candidate()
    review006 = review006 or shoulder_pose_clearance_refinement_candidate()

    if canonical_digest(parent) != EXPECTED_PARENT_SOURCE_DIGEST:
        raise ValueError("accepted-E parent source identity drift")
    if canonical_digest(build_adopted_character_mesh(parent)) != EXPECTED_PARENT_MESH_DIGEST:
        raise ValueError("accepted-E parent proof-mesh identity drift")
    if canonical_digest(review005) != EXPECTED_REVIEW005_SOURCE_DIGEST:
        raise ValueError("review-005 source identity drift")
    if canonical_digest(build_adopted_character_mesh(review005)) != EXPECTED_REVIEW005_MESH_DIGEST:
        raise ValueError("review-005 proof-mesh identity drift")
    if canonical_digest(review006) != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 source identity drift")
    if canonical_digest(build_adopted_character_mesh(review006)) != EXPECTED_REVIEW006_MESH_DIGEST:
        raise ValueError("review-006 proof-mesh identity drift")

    for side in ("L", "R"):
        for landmark in ("shoulder", "wrist"):
            key = f"{landmark}_{side}"
            if review006["landmarks"][key] != review005["landmarks"][key]:
                raise ValueError(f"review-006 changed protected chord endpoint: {key}")

    parent_context = _require_bilateral_context(parent, "accepted-E")
    review005_context = _require_bilateral_context(review005, "review-005")
    review006_context = _require_bilateral_context(review006, "review-006")

    r5 = review005_context["right"]
    r6 = review006_context["right"]
    chord_residual = abs(r6["shoulder_to_wrist_chord_m"] - r5["shoulder_to_wrist_chord_m"])
    if chord_residual > 1e-12:
        raise ValueError("review-006 changed review-005 shoulder-to-wrist chord")

    offset_reduction = (
        r5["elbow_perpendicular_offset_from_chord_m"]
        - r6["elbow_perpendicular_offset_from_chord_m"]
    )
    if offset_reduction < MIN_REVIEW005_OFFSET_REDUCTION_M:
        raise ValueError("review-006 does not materially reduce review-005 elbow chord offset")
    path_excess_reduction = (
        r5["landmark_chain_excess_over_chord_m"]
        - r6["landmark_chain_excess_over_chord_m"]
    )
    if path_excess_reduction <= 0.0:
        raise ValueError("review-006 does not reduce review-005 landmark-chain excess")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "identities": {
            "accepted_E_parent_source_digest": EXPECTED_PARENT_SOURCE_DIGEST,
            "accepted_E_parent_mesh_digest": EXPECTED_PARENT_MESH_DIGEST,
            "review005_source_digest": EXPECTED_REVIEW005_SOURCE_DIGEST,
            "review005_mesh_digest": EXPECTED_REVIEW005_MESH_DIGEST,
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
        },
        "accepted_E_parent": parent_context,
        "review005": review005_context,
        "review006": review006_context,
        "review006_vs_review005": {
            "shoulder_to_wrist_chord_residual_m": chord_residual,
            "elbow_perpendicular_offset_reduction_m": offset_reduction,
            "elbow_perpendicular_offset_reduction_ratio": (
                offset_reduction / r5["elbow_perpendicular_offset_from_chord_m"]
            ),
            "landmark_chain_excess_reduction_m": path_excess_reduction,
            "shoulder_and_wrist_endpoints_identical": True,
        },
        "gates": {
            "exact_parent_identity": "PASS",
            "exact_review005_identity": "PASS",
            "exact_review006_identity": "PASS",
            "bilateral_source_landmark_context": "PASS",
            "review006_preserves_review005_shoulder_wrist_chord": "PASS",
            "review006_reduces_review005_elbow_chord_offset_by_at_least_10mm": "PASS",
            "review006_reduces_review005_chain_excess": "PASS",
            "visual_acceptance": "NOT_EVALUATED",
            "connected_topology_or_intersection_rebind": "NOT_EVALUATED",
            "rigging_or_deformation_rebind": "NOT_EVALUATED",
            "source_adoption": "NOT_CLAIMED",
        },
        "handoff": (
            "Art Direction / Visual QA can use the retained front landmark context beside the existing "
            "filled accepted-E / review-005 / review-006 views. The metric states only how far the "
            "source elbow landmark sits away from the straight shoulder-to-wrist chord while review-005 "
            "and review-006 keep the same chord endpoints. Geometry and Rigging must not inherit this as "
            "a topology, collision, skeleton-rest-angle or deformation PASS."
        ),
        "truth_boundary": [
            "This is source-landmark spatial context for an already-retained Organic review candidate; no Character form is changed by this evidence contract.",
            "Elbow-to-chord offset and landmark-chain excess are geometric review measurements, not anatomical targets, skeletal rest angles, range-of-motion rules or biological claims.",
            "A smaller offset is not automatically visually better; Art Direction / Visual QA retain perceptual acceptance authority.",
            "No connected-topology, self-intersection, weighting, skinning, continuous deformation, Animation, Materials, runtime, gameplay, CANON, production-readiness or Organic mastery claim is made.",
        ],
    }


def _project_front(point, panel_x):
    x = float(point[0])
    z = float(point[2])
    return panel_x + 170.0 + (x * 250.0), 245.0 - ((z - 1.28) * 390.0)


def _panel(source, context, panel_x, title):
    shoulder = source["landmarks"]["shoulder_R"]
    elbow = source["landmarks"]["elbow_R"]
    wrist = source["landmarks"]["wrist_R"]
    projected = context["right"]["elbow_projection_point"]
    s = _project_front(shoulder, panel_x)
    e = _project_front(elbow, panel_x)
    w = _project_front(wrist, panel_x)
    p = _project_front(projected, panel_x)
    offset_mm = context["right"]["elbow_perpendicular_offset_from_chord_m"] * 1000.0
    t = context["right"]["elbow_projection_fraction_along_chord"]
    excess_mm = context["right"]["landmark_chain_excess_over_chord_m"] * 1000.0
    lines = [
        f'<rect x="{panel_x:.1f}" y="0" width="350" height="350" fill="white" stroke="#777"/>',
        f'<text x="{panel_x + 16:.1f}" y="26" font-family="monospace" font-size="14">{title}</text>',
        f'<line x1="{s[0]:.3f}" y1="{s[1]:.3f}" x2="{w[0]:.3f}" y2="{w[1]:.3f}" stroke="#777" stroke-width="2" stroke-dasharray="7 5"/>',
        f'<polyline points="{s[0]:.3f},{s[1]:.3f} {e[0]:.3f},{e[1]:.3f} {w[0]:.3f},{w[1]:.3f}" fill="none" stroke="#111" stroke-width="3"/>',
        f'<line x1="{e[0]:.3f}" y1="{e[1]:.3f}" x2="{p[0]:.3f}" y2="{p[1]:.3f}" stroke="#444" stroke-width="2"/>',
        f'<circle cx="{s[0]:.3f}" cy="{s[1]:.3f}" r="4" fill="white" stroke="#111"/>',
        f'<circle cx="{e[0]:.3f}" cy="{e[1]:.3f}" r="5" fill="white" stroke="#111"/>',
        f'<circle cx="{w[0]:.3f}" cy="{w[1]:.3f}" r="4" fill="white" stroke="#111"/>',
        f'<circle cx="{p[0]:.3f}" cy="{p[1]:.3f}" r="3" fill="white" stroke="#444"/>',
        f'<text x="{panel_x + 16:.1f}" y="305" font-family="monospace" font-size="12">elbow chord offset: {offset_mm:.3f} mm</text>',
        f'<text x="{panel_x + 16:.1f}" y="324" font-family="monospace" font-size="12">projection t: {t:.6f}</text>',
        f'<text x="{panel_x + 16:.1f}" y="343" font-family="monospace" font-size="12">chain excess: {excess_mm:.3f} mm</text>',
    ]
    return "\n".join(lines)


def _comparison_svg(parent, review005, review006, receipt):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1090" height="395" viewBox="0 0 1090 395">\n'
        '<rect width="1090" height="395" fill="white"/>\n'
        + _panel(parent, receipt["accepted_E_parent"], 0.0, "Accepted E parent")
        + "\n"
        + _panel(review005, receipt["review005"], 370.0, "Review 005")
        + "\n"
        + _panel(review006, receipt["review006"], 740.0, "Review 006")
        + "\n"
        + '<text x="14" y="382" font-family="monospace" font-size="12">source-landmark context only; dashed line = shoulder-to-wrist chord; perpendicular marker is not rig/anatomy acceptance</text>\n'
        + '</svg>\n'
    )


def build_shoulder_pose_clearance_spatial_context_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    parent = adopted_character_source()
    review005 = shoulder_pose_clearance_candidate()
    review006 = shoulder_pose_clearance_refinement_candidate()
    receipt = audit_shoulder_pose_clearance_spatial_context(review006)
    (out / "shoulder-pose-clearance-review-006-spatial-context.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "shoulder-pose-clearance-review-006-spatial-context.svg").write_text(
        _comparison_svg(parent, review005, review006, receipt), encoding="utf-8"
    )
    return receipt
