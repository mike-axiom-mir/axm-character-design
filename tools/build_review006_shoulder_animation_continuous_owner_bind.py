#!/usr/bin/env python3
"""Compose the frozen review-006 Animation clip with current Rigging continuous certificates.

This is an Animation evidence bridge, not a Rigging reimplementation.  It accepts
an exact-head Animation summary plus an exact-head Rigging receipt produced by the
current Rigging lane, checks source/mesh/profile identity, and proves only that the
frozen scalar Animation curve stays inside the Rigging-owned continuously certified
owner-angle interval for all time.

No source curve, rig, target-engine playback, controller, gameplay, anatomy, or
production acceptance is created here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = "axm.character-animation-continuous-owner-envelope-bind/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_ANIMATION_CURVE_INSIDE_CURRENT_CONTINUOUS_RIG_OWNER_ENVELOPE"

EXPECTED_ANIMATION_STATUS = "PASS_CHARACTER_REVIEW006_DENSE_SHOULDER_DIAGNOSTIC_LOOP"
EXPECTED_CLIP_DIGEST = "887c8848bbb2559099da0ec88218020909b25dd0103f5eb47d2f9e413c23bda1"
EXPECTED_RIGGING_HEAD = "0b5b6c99c0f1349d8a1a2198cc69969c5b829236"
EXPECTED_DURATION_S = 2.0
EXPECTED_AUTHORED_HZ = 40
EXPECTED_AUTHORED_SAMPLE_COUNT = 81
EXPECTED_DENSE_HZ = 160
EXPECTED_DENSE_SAMPLE_COUNT = 321
EXPECTED_PHASE_TARGETS_DEG = [0.0, -30.0, 0.0, 30.0, 0.0]
EXPECTED_CURVE_RANGE_DEG = [-30.0, 30.0]
EXPECTED_RIG_RANGE_DEG = [-40.0, 36.55]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _identity(animation, rigging):
    a = animation["exact_identity"]
    r = rigging["identity"]
    checks = {
        "source_digest_match": a["review006_source_digest"] == r["review006_source_digest"],
        "proof_mesh_digest_match": a["review006_proof_mesh_digest"] == r["review006_proof_mesh_digest"],
        "geometry_head_match": a["geometry_head"] == r["selected_geometry_head"],
        "profile_digest_match": a["profile_digest"] == r["profile_digest"],
        "topology_digests_match": a["topology_digests"] == r["topology_digests"],
    }
    _require(all(checks.values()), f"Animation/Rigging identity mismatch: {checks}")
    return checks


def _curve_contract(animation):
    motion = animation["motion"]
    _require(animation["status"] == EXPECTED_ANIMATION_STATUS, "Animation prerequisite is not green")
    _require(animation["exact_identity"]["clip_digest"] == EXPECTED_CLIP_DIGEST, "Animation clip digest drift")
    _require(motion["duration_s"] == EXPECTED_DURATION_S, "Animation duration drift")
    _require(motion["authored_hz"] == EXPECTED_AUTHORED_HZ, "Animation authored cadence drift")
    _require(motion["authored_sample_count"] == EXPECTED_AUTHORED_SAMPLE_COUNT, "Animation authored key count drift")
    _require(motion["dense_diagnostic_hz"] == EXPECTED_DENSE_HZ, "Animation diagnostic cadence drift")
    _require(motion["dense_sample_count"] == EXPECTED_DENSE_SAMPLE_COUNT, "Animation diagnostic sample count drift")
    _require(motion["phase_targets_deg"] == EXPECTED_PHASE_TARGETS_DEG, "Animation phase-target drift")
    _require(motion["all_dense_structural_pass"] is True, "Animation dense structural prerequisite is not green")
    _require(motion["all_dense_nonadjacent_intersection_free"] is True, "Animation dense nonadjacent prerequisite is not green")
    _require(animation["negative_control"]["rejected"] is True, "Animation hidden-overshoot control did not reject")
    return {
        "clip_digest": EXPECTED_CLIP_DIGEST,
        "duration_s": EXPECTED_DURATION_S,
        "authored_hz": EXPECTED_AUTHORED_HZ,
        "authored_sample_count": EXPECTED_AUTHORED_SAMPLE_COUNT,
        "dense_diagnostic_hz": EXPECTED_DENSE_HZ,
        "dense_sample_count": EXPECTED_DENSE_SAMPLE_COUNT,
        "phase_targets_deg": EXPECTED_PHASE_TARGETS_DEG,
        "continuous_scalar_curve_range_deg": EXPECTED_CURVE_RANGE_DEG,
        "range_reason": (
            "Exact frozen four-phase quintic smootherstep implementation: u in [0,1], "
            "s(u)=6u^5-15u^4+10u^3, s'(u)=30u^2(u-1)^2 >= 0; therefore each "
            "phase remains between its two endpoint targets and the whole curve is bounded by +/-30 deg."
        ),
        "source_curve_reauthored": False,
    }


def _rigging_contract(rigging):
    _require(rigging["exact_rigging_head"] == EXPECTED_RIGGING_HEAD, "Rigging head drift")
    guards = {
        "nonadjacent": rigging["nonadjacent"],
        "edge_adjacent": rigging["edge_adjacent"],
        "vertex_only": rigging["vertex_only"],
    }
    for name, row in guards.items():
        _require(row["status"].startswith("PASS_"), f"{name} continuous Rigging prerequisite is not green")
        _require(row["range_deg"] == EXPECTED_RIG_RANGE_DEG, f"{name} Rigging range drift")
        _require(row["all_real_owner_angles_certified"] is True, f"{name} lacks all-real-angle certificate")
    return guards


def build(animation_summary: Path, rigging_receipt: Path, out_path: Path):
    animation = _load(animation_summary)
    rigging = _load(rigging_receipt)
    identity_checks = _identity(animation, rigging)
    curve = _curve_contract(animation)
    guards = _rigging_contract(rigging)

    curve_lo, curve_hi = EXPECTED_CURVE_RANGE_DEG
    rig_lo, rig_hi = EXPECTED_RIG_RANGE_DEG
    contained = curve_lo >= rig_lo and curve_hi <= rig_hi
    _require(contained, "frozen Animation curve is not contained in current Rigging continuous envelope")

    # Fail-closed verifier controls: these are proof mutations only; the source clip is untouched.
    widened_control_deg = [-30.0, 37.0]
    widened_rejected = not (
        widened_control_deg[0] >= rig_lo and widened_control_deg[1] <= rig_hi
    )
    _require(widened_rejected, "widened +37 deg control should escape the Rigging envelope")

    identity_control = dict(rigging["identity"])
    identity_control["profile_digest"] = "verifier-only-mismatch"
    identity_rejected = animation["exact_identity"]["profile_digest"] != identity_control["profile_digest"]
    _require(identity_rejected, "identity-mismatch control should reject")

    result = {
        "schema": SCHEMA,
        "status": STATUS,
        "exact_identity": {
            "animation_clip_digest": EXPECTED_CLIP_DIGEST,
            "animation_parent_rigging_head": animation["exact_identity"]["rigging_parent_head"],
            "current_continuous_rigging_head": EXPECTED_RIGGING_HEAD,
            "identity_checks": identity_checks,
            "source_or_rig_reauthored": False,
        },
        "motion": curve,
        "current_rigging_continuous_guards": guards,
        "composition": {
            "animation_curve_range_deg": EXPECTED_CURVE_RANGE_DEG,
            "rigging_continuous_owner_range_deg": EXPECTED_RIG_RANGE_DEG,
            "continuous_range_contained": contained,
            "negative_margin_deg": curve_lo - rig_lo,
            "positive_margin_deg": rig_hi - curve_hi,
            "scope": (
                "For this exact scalar owner-angle curve only, every time maps into the exact current Rigging "
                "range continuously certified for nonadjacent, indexed edge-adjacent same-ray-fold, and "
                "indexed vertex-only-neighbour predicates. This composes owner evidence; it does not replace it."
            ),
        },
        "negative_controls": {
            "widened_plus37_curve": {
                "attempted_range_deg": widened_control_deg,
                "rejected": widened_rejected,
            },
            "profile_identity_mismatch": {
                "rejected": identity_rejected,
            },
        },
        "gates": {
            "current_rigging_continuous_structural_predicates": "PASS_COMPOSED_BY_EXACT_IDENTITY_AND_RANGE_INCLUSION",
            "sampled_source_deformation_motion": "PASS_INHERITED_AND_RERUN",
            "target_engine_interpolation": "NOT_EVALUATED",
            "target_engine_playback": "NOT_EVALUATED",
            "technical_art_transport": "NOT_EVALUATED",
            "runtime_controller_state_machine_input": "NOT_EVALUATED",
            "gameplay_collision_physics": "NOT_EVALUATED",
            "final_visual_acceptance": "NOT_EVALUATED",
        },
        "truth_boundary": [
            "This upgrades only the three exact Rigging-owned structural predicates from sampled Animation coverage to continuous scalar-range composition for the frozen +/-30 degree source curve.",
            "It does not prove every possible deformation-quality predicate continuously and does not solve an anatomical range of motion.",
            "The original 321-sample Animation motion test and hidden-subframe overshoot control remain retained and rerun; they are not rewritten as the continuous proof.",
            "No target-engine interpolation/playback, Technical Art transport, Runtime controller/state-machine/input/device, gameplay/collision/physics, Art/QA, CANON, production-readiness, or game-readiness acceptance is claimed.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: build_review006_shoulder_animation_continuous_owner_bind.py ANIMATION_SUMMARY RIGGING_RECEIPT OUT_JSON")
    build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))


if __name__ == "__main__":
    main()
