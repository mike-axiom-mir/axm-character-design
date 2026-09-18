"""Animation-owned dense shoulder diagnostic for Character review-006.

This module creates one deliberately conservative bilateral shoulder articulation
loop on top of the exact current review-006 Rigging receiver.  It does not
change source form, topology, joints, weights, the Rigging release profile, or
any runtime/controller implementation.

The useful question is temporal rather than anatomical: can a deterministic
clip remain inside a clearly interior motion envelope while dense in-between
sampling exercises the real Rigging deformation path and catches a hidden
subframe overshoot that authored-key-only checks would miss?

All results are finite sampled source/deformation evidence.  They are not
mathematical continuous-motion proof, anatomy/range-of-motion guidance,
target-engine interpolation, runtime-controller, gameplay, or production
acceptance.
"""
from __future__ import annotations

import copy
import math

from .organic_form import canonical_digest
from .review006_connected_geometry import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    build_opening_repair,
)
from .review006_self_intersection import inspect_triangle_self_intersections
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    _mirror_position_set,
    _pose,
    _pose_pass,
    _position_set,
    _reindexed_layout,
    _weights,
    rebind_contract,
    release_weight,
)
from .review006_shoulder_subdegree_boundary import (
    STATUS as SUBDEGREE_STATUS,
    audit_review006_positive_subdegree_boundary,
)
from .shoulder_pose_clearance_refinement import (
    VARIANT_ID as REVIEW006_ID,
    shoulder_pose_clearance_refinement_candidate,
)

SCHEMA = "axm.character-review006-shoulder-animation-diagnostic/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_DENSE_SHOULDER_DIAGNOSTIC_LOOP"
FAIL_STATUS = "HOLD_CHARACTER_REVIEW006_DENSE_SHOULDER_DIAGNOSTIC_LOOP"

RIGGING_HEAD = "fa16c44b1a488d43842470fc9f30c5fb5e98cab6"
CLIP_ID = "character-review006-bilateral-shoulder-articulation-review-loop-001"
TRUTH_LABEL = "DIAGNOSTIC_BILATERAL_SHOULDER_ARTICULATION_NOT_GESTURE_OR_LOCOMOTION"

DURATION_S = 2.0
AUTHORED_HZ = 40
AUTHORED_INTERVALS = int(DURATION_S * AUTHORED_HZ)
AUTHORED_SAMPLE_COUNT = AUTHORED_INTERVALS + 1
DENSE_FACTOR = 4
DENSE_HZ = AUTHORED_HZ * DENSE_FACTOR
DENSE_INTERVALS = AUTHORED_INTERVALS * DENSE_FACTOR
DENSE_SAMPLE_COUNT = DENSE_INTERVALS + 1
PHASE_DURATION_S = 0.5
AMPLITUDE_DEG = 30.0

# The current exact Rigging observer brackets the first positive nonadjacent
# intersection between these finite samples.  Animation stays well inside it.
EXPECTED_LAST_CLEAR_POSITIVE_DEG = 36.55
EXPECTED_FIRST_FAILING_POSITIVE_DEG = 36.60
POSITIVE_SAMPLE_MARGIN_DEG = EXPECTED_LAST_CLEAR_POSITIVE_DEG - AMPLITUDE_DEG

# Negative control: inject a verifier-only bump strictly between two authored
# keys.  The bump is zero at both authored endpoints and reaches the first
# measured failing Rigging sample at the midpoint, so a 40 Hz key-only check
# cannot see it while the 160 Hz diagnostic can.
NEGATIVE_INTERVAL_START_S = 1.25
NEGATIVE_INTERVAL_END_S = NEGATIVE_INTERVAL_START_S + (1.0 / AUTHORED_HZ)
NEGATIVE_INTERVAL_MID_S = 0.5 * (NEGATIVE_INTERVAL_START_S + NEGATIVE_INTERVAL_END_S)
NEGATIVE_TARGET_ANGLE_DEG = EXPECTED_FIRST_FAILING_POSITIVE_DEG


def _smootherstep(value: float) -> float:
    u = min(1.0, max(0.0, float(value)))
    return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)


def _phase_angle(time_s: float) -> float:
    """Return the exact source curve angle for the four-phase diagnostic loop."""
    t = min(DURATION_S, max(0.0, float(time_s)))
    if t <= 0.5:
        return -AMPLITUDE_DEG * _smootherstep(t / PHASE_DURATION_S)
    if t <= 1.0:
        return -AMPLITUDE_DEG * (1.0 - _smootherstep((t - 0.5) / PHASE_DURATION_S))
    if t <= 1.5:
        return AMPLITUDE_DEG * _smootherstep((t - 1.0) / PHASE_DURATION_S)
    return AMPLITUDE_DEG * (1.0 - _smootherstep((t - 1.5) / PHASE_DURATION_S))


def _source_curve_boundary_kinematics():
    # smootherstep has exactly zero first and second derivative at u=0 and u=1.
    # Scaling by amplitude and phase duration therefore leaves every phase join
    # with zero analytic source-curve velocity and acceleration.
    return {
        "times_s": [0.0, 0.5, 1.0, 1.5, 2.0],
        "angle_deg": [_phase_angle(value) for value in (0.0, 0.5, 1.0, 1.5, 2.0)],
        "analytic_velocity_deg_s": [0.0] * 5,
        "analytic_acceleration_deg_s2": [0.0] * 5,
        "meaning": "source-curve C2 phase joins only; no target-engine interpolation claim",
    }


def authored_clip_payload():
    samples = []
    for index in range(AUTHORED_SAMPLE_COUNT):
        time_s = index / AUTHORED_HZ
        samples.append({
            "sample_index": index,
            "time_s": time_s,
            "shoulder_angle_deg": _phase_angle(time_s),
        })
    return {
        "clip_id": CLIP_ID,
        "truth_label": TRUTH_LABEL,
        "duration_s": DURATION_S,
        "authored_hz": AUTHORED_HZ,
        "endpoint_inclusive_sample_count": AUTHORED_SAMPLE_COUNT,
        "curve": "four_phase_quintic_smootherstep",
        "phase_targets_deg": [0.0, -AMPLITUDE_DEG, 0.0, AMPLITUDE_DEG, 0.0],
        "bilateral_local_angle_policy": "same_local_angle_both_shoulders_mirrored_axes_from_rig",
        "samples": samples,
    }


def clip_digest() -> str:
    return canonical_digest(authored_clip_payload())


def animation_contract():
    return {
        "schema": SCHEMA,
        "clip": {
            "id": CLIP_ID,
            "digest": clip_digest(),
            "truth_label": TRUTH_LABEL,
            "duration_s": DURATION_S,
            "authored_hz": AUTHORED_HZ,
            "authored_sample_count": AUTHORED_SAMPLE_COUNT,
            "dense_diagnostic_hz": DENSE_HZ,
            "dense_sample_count": DENSE_SAMPLE_COUNT,
            "amplitude_deg": AMPLITUDE_DEG,
            "phase_duration_s": PHASE_DURATION_S,
            "source_curve": "quintic_smootherstep",
        },
        "source": {
            "review006_id": REVIEW006_ID,
            "source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
        },
        "geometry": {
            "head": GEOMETRY_HEAD,
            "selected_stage": "opening_repair",
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
        },
        "rigging": {
            "exact_parent_head": RIGGING_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "source_or_rig_reauthored": False,
            "release_weight_function_reused": True,
            "current_subdegree_boundary_required": SUBDEGREE_STATUS,
            "expected_last_sampled_clear_positive_deg": EXPECTED_LAST_CLEAR_POSITIVE_DEG,
            "expected_first_sampled_failure_positive_deg": EXPECTED_FIRST_FAILING_POSITIVE_DEG,
        },
        "animation_scope": {
            "motion_variable_changed_from_rigging": "new Animation-owned diagnostic curve only",
            "source_form_changed": False,
            "topology_changed": False,
            "joint_semantics_changed": False,
            "weight_profile_changed": False,
            "runtime_controller_added": False,
            "gameplay_logic_added": False,
        },
        "truth_boundary": {
            "finite_dense_sampling_only": True,
            "mathematical_continuity_proven": False,
            "anatomical_range_of_motion": False,
            "target_engine_interpolation_proven": False,
            "target_engine_playback_proven": False,
            "technical_art_transport_acceptance": False,
            "runtime_controller_acceptance": False,
            "gameplay_acceptance": False,
            "final_visual_acceptance": False,
            "source_adoption_or_canon": False,
            "production_readiness": False,
        },
    }


def _validate_contract(contract):
    if contract != animation_contract():
        raise ValueError("review-006 Animation diagnostic contract identity drift")


def _validate_exact_dependencies():
    source = shoulder_pose_clearance_refinement_candidate()
    if source.get("study_id") != REVIEW006_ID:
        raise ValueError("review-006 Animation source ID drift")
    if canonical_digest(source) != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 Animation source digest drift")

    rig_contract = rebind_contract()
    if rig_contract["geometry"]["head"] != GEOMETRY_HEAD:
        raise ValueError("review-006 Animation Geometry dependency drift")
    if rig_contract["rig_method"]["profile_digest"] != EXPECTED_PROFILE_DIGEST:
        raise ValueError("review-006 Animation Rigging profile drift")

    boundary = audit_review006_positive_subdegree_boundary()
    if boundary["status"] != SUBDEGREE_STATUS:
        raise ValueError("review-006 Animation subdegree prerequisite is not green")
    measured = boundary["subdegree_probe"]["boundaries"]
    if measured["L"] != measured["R"]:
        raise ValueError("review-006 Animation requires bilateral subdegree boundary agreement")
    if abs(float(measured["L"]["last_sampled_clear_deg"]) - EXPECTED_LAST_CLEAR_POSITIVE_DEG) > 1e-12:
        raise ValueError("review-006 Animation last-clear boundary identity drift")
    if abs(float(measured["L"]["first_sampled_failure_deg"]) - EXPECTED_FIRST_FAILING_POSITIVE_DEG) > 1e-12:
        raise ValueError("review-006 Animation first-failing boundary identity drift")
    if AMPLITUDE_DEG >= EXPECTED_LAST_CLEAR_POSITIVE_DEG:
        raise ValueError("review-006 Animation diagnostic amplitude is not interior to the measured positive guard")
    return source, rig_contract, boundary


def _build_side_context(side: str, source, rig_contract):
    specimen = build_opening_repair(side)
    observed_topology = canonical_digest({
        "positions": specimen["positions"],
        "faces": specimen["faces"],
    })
    if observed_topology != EXPECTED_TOPOLOGY_DIGESTS[side]:
        raise ValueError(f"review-006 Animation topology identity drift for {side}")
    layout = _reindexed_layout(side, specimen)
    joint = rig_contract["rig_method"]["joint_semantics"][side]
    origin = tuple(float(value) for value in source["landmarks"][joint["landmark"]])
    axis = tuple(float(value) for value in joint["axis"])
    return {
        "specimen": specimen,
        "layout": layout,
        "origin": origin,
        "axis": axis,
    }


def _evaluate_pose(context, angle_deg: float):
    specimen = context["specimen"]
    weight = release_weight(angle_deg)
    posed = _pose(
        specimen,
        context["origin"],
        context["axis"],
        angle_deg,
        _weights(context["layout"], weight, len(specimen["positions"])),
    )
    intersections = inspect_triangle_self_intersections(
        posed["positions"], specimen["indices"], max_examples=4
    )
    return posed, intersections, weight


def _max_position_delta(first, second) -> float:
    return max(math.dist(a, b) for a, b in zip(first, second)) if first else 0.0


def _monotonic_phase_gate(angles):
    boundaries = [0, 80, 160, 240, 320]  # 0.5 s phases at 160 Hz.
    directions = (-1, 1, 1, -1)
    for start, end, direction in zip(boundaries[:-1], boundaries[1:], directions):
        values = angles[start : end + 1]
        for first, second in zip(values, values[1:]):
            delta = second - first
            if direction < 0 and delta > 1e-12:
                return False
            if direction > 0 and delta < -1e-12:
                return False
    return True


def _negative_control(contexts):
    midpoint_base = _phase_angle(NEGATIVE_INTERVAL_MID_S)
    bump_amplitude = NEGATIVE_TARGET_ANGLE_DEG - midpoint_base
    if bump_amplitude <= 0.0:
        raise ValueError("negative-control bump must raise the hidden subframe above the base curve")

    def mutated_angle(time_s):
        base = _phase_angle(time_s)
        if time_s <= NEGATIVE_INTERVAL_START_S or time_s >= NEGATIVE_INTERVAL_END_S:
            return base
        phase = (time_s - NEGATIVE_INTERVAL_START_S) / (
            NEGATIVE_INTERVAL_END_S - NEGATIVE_INTERVAL_START_S
        )
        return base + bump_amplitude * (math.sin(math.pi * phase) ** 2)

    authored_residual = 0.0
    for index in range(AUTHORED_SAMPLE_COUNT):
        time_s = index / AUTHORED_HZ
        authored_residual = max(
            authored_residual,
            abs(mutated_angle(time_s) - _phase_angle(time_s)),
        )

    failures = []
    max_mutated_angle = -float("inf")
    for index in range(DENSE_SAMPLE_COUNT):
        time_s = index / DENSE_HZ
        if time_s < NEGATIVE_INTERVAL_START_S - 1e-12 or time_s > NEGATIVE_INTERVAL_END_S + 1e-12:
            continue
        angle = mutated_angle(time_s)
        max_mutated_angle = max(max_mutated_angle, angle)
        side_rows = {}
        for side in ("L", "R"):
            posed, intersections, _ = _evaluate_pose(contexts[side], angle)
            side_rows[side] = {
                "structural_pass": _pose_pass(posed),
                "intersection_pairs": int(intersections["self_intersection_pair_count"]),
            }
        if any(row["intersection_pairs"] > 0 for row in side_rows.values()):
            failures.append({
                "dense_sample_index": index,
                "time_s": time_s,
                "mutated_angle_deg": angle,
                "sides": side_rows,
            })

    rejected = (
        authored_residual <= 1e-12
        and max_mutated_angle >= NEGATIVE_TARGET_ANGLE_DEG - 1e-12
        and bool(failures)
    )
    return {
        "mutation": "hidden sin^2 shoulder-angle bump strictly between authored 40 Hz keys",
        "interval_s": [NEGATIVE_INTERVAL_START_S, NEGATIVE_INTERVAL_END_S],
        "midpoint_s": NEGATIVE_INTERVAL_MID_S,
        "base_midpoint_angle_deg": midpoint_base,
        "bump_amplitude_deg": bump_amplitude,
        "target_midpoint_angle_deg": NEGATIVE_TARGET_ANGLE_DEG,
        "authored_key_max_angle_residual_deg": authored_residual,
        "max_mutated_dense_angle_deg": max_mutated_angle,
        "dense_failure_count": len(failures),
        "first_dense_failure": failures[0] if failures else None,
        "rejected": rejected,
        "expected": "HOLD_HIDDEN_SUBFRAME_OVERSHOOT",
        "meaning": (
            "All authored 40 Hz keys remain unchanged. The denser Animation observer must still reject "
            "an in-between overshoot that enters the exact Rigging-measured failing shoulder state."
        ),
    }


def audit_review006_shoulder_animation(contract=None):
    contract = copy.deepcopy(contract or animation_contract())
    _validate_contract(contract)
    source, rig_contract, boundary = _validate_exact_dependencies()
    contexts = {
        side: _build_side_context(side, source, rig_contract)
        for side in ("L", "R")
    }

    dense_rows = []
    dense_angles = []
    previous_positions = {"L": None, "R": None}
    first_positions = {}
    max_adjacent_step_m = {"L": 0.0, "R": 0.0}
    max_intersection_pairs = {"L": 0, "R": 0}
    all_structural_pass = True
    all_intersection_free = True
    all_bilateral_mirror = True

    for index in range(DENSE_SAMPLE_COUNT):
        time_s = index / DENSE_HZ
        angle = _phase_angle(time_s)
        dense_angles.append(angle)
        posed_by_side = {}
        row = {
            "dense_sample_index": index,
            "time_s": time_s,
            "shoulder_angle_deg": angle,
            "sides": {},
        }
        for side in ("L", "R"):
            posed, intersections, weight = _evaluate_pose(contexts[side], angle)
            posed_by_side[side] = posed
            pair_count = int(intersections["self_intersection_pair_count"])
            max_intersection_pairs[side] = max(max_intersection_pairs[side], pair_count)
            structural_pass = _pose_pass(posed)
            all_structural_pass &= structural_pass
            all_intersection_free &= pair_count == 0
            if previous_positions[side] is not None:
                max_adjacent_step_m[side] = max(
                    max_adjacent_step_m[side],
                    _max_position_delta(previous_positions[side], posed["positions"]),
                )
            else:
                first_positions[side] = posed["positions"]
            previous_positions[side] = posed["positions"]
            row["sides"][side] = {
                "release_weight": weight,
                "structural_pass": structural_pass,
                "nonadjacent_intersection_pair_count": pair_count,
                "minimum_triangle_area_ratio": posed["minimum_triangle_area_ratio"],
                "maximum_triangle_area_ratio": posed["maximum_triangle_area_ratio"],
                "minimum_edge_length_ratio": posed["minimum_edge_length_ratio"],
                "maximum_edge_length_ratio": posed["maximum_edge_length_ratio"],
                "fixed_socket_max_drift_m": posed["fixed_socket_max_drift_m"],
                "rigid_arm_radius_max_drift_m": posed["rigid_arm_radius_max_drift_m"],
            }

        mirrored = (
            _mirror_position_set(posed_by_side["L"]["positions"])
            == _position_set(posed_by_side["R"]["positions"])
        )
        row["bilateral_mirrored_position_set"] = mirrored
        all_bilateral_mirror &= mirrored
        dense_rows.append(row)

    loop_residual_m = {
        side: _max_position_delta(first_positions[side], previous_positions[side])
        for side in ("L", "R")
    }

    authored_subset_max_angle_residual = 0.0
    for authored_index in range(AUTHORED_SAMPLE_COUNT):
        dense_index = authored_index * DENSE_FACTOR
        authored_angle = authored_clip_payload()["samples"][authored_index]["shoulder_angle_deg"]
        authored_subset_max_angle_residual = max(
            authored_subset_max_angle_residual,
            abs(authored_angle - dense_rows[dense_index]["shoulder_angle_deg"]),
        )

    extrema_exact = (
        abs(min(dense_angles) + AMPLITUDE_DEG) <= 1e-12
        and abs(max(dense_angles) - AMPLITUDE_DEG) <= 1e-12
        and abs(dense_angles[0]) <= 1e-12
        and abs(dense_angles[-1]) <= 1e-12
    )
    monotonic_phases = _monotonic_phase_gate(dense_angles)
    negative = _negative_control(contexts)
    kinematics = _source_curve_boundary_kinematics()

    positive_guard = (
        all_structural_pass
        and all_intersection_free
        and all_bilateral_mirror
        and max(abs(value) for value in dense_angles) <= AMPLITUDE_DEG + 1e-12
        and all(value <= 1e-12 for value in loop_residual_m.values())
        and authored_subset_max_angle_residual <= 1e-12
        and extrema_exact
        and monotonic_phases
    )
    pass_gate = positive_guard and negative["rejected"]

    serial_rows = dense_rows
    return {
        "schema": SCHEMA,
        "status": STATUS if pass_gate else FAIL_STATUS,
        "contract": contract,
        "exact_identity": {
            "rigging_parent_head": RIGGING_HEAD,
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "geometry_head": GEOMETRY_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "clip_digest": clip_digest(),
        },
        "rigging_boundary_prerequisite": {
            "status": boundary["status"],
            "last_sampled_clear_positive_deg": boundary["subdegree_probe"]["boundaries"]["L"]["last_sampled_clear_deg"],
            "first_sampled_failure_positive_deg": boundary["subdegree_probe"]["boundaries"]["L"]["first_sampled_failure_deg"],
            "animation_positive_amplitude_deg": AMPLITUDE_DEG,
            "margin_below_last_sampled_clear_positive_deg": POSITIVE_SAMPLE_MARGIN_DEG,
            "meaning": "Rigging finite boundary is a structural prerequisite, not anatomy or Animation ROM authority",
        },
        "motion": {
            "duration_s": DURATION_S,
            "authored_hz": AUTHORED_HZ,
            "authored_sample_count": AUTHORED_SAMPLE_COUNT,
            "dense_diagnostic_hz": DENSE_HZ,
            "dense_sample_count": DENSE_SAMPLE_COUNT,
            "phase_targets_deg": [0.0, -AMPLITUDE_DEG, 0.0, AMPLITUDE_DEG, 0.0],
            "all_dense_structural_pass": all_structural_pass,
            "all_dense_nonadjacent_intersection_free": all_intersection_free,
            "maximum_nonadjacent_intersection_pairs": max_intersection_pairs,
            "all_dense_bilateral_mirror": all_bilateral_mirror,
            "monotonic_within_each_phase": monotonic_phases,
            "exact_phase_extrema_and_neutral_endpoints": extrema_exact,
            "loop_max_vertex_residual_m": loop_residual_m,
            "maximum_adjacent_dense_vertex_step_m": max_adjacent_step_m,
            "authored_subset_max_angle_residual_deg": authored_subset_max_angle_residual,
            "source_curve_boundary_kinematics": kinematics,
            "rows": serial_rows,
        },
        "negative_control": negative,
        "gates": {
            "exact_source_geometry_rig_identity": "PASS",
            "current_rigging_subdegree_prerequisite": "PASS",
            "dense_source_deformation_motion": "PASS" if positive_guard else "FAIL",
            "all_dense_structural_samples": "PASS" if all_structural_pass else "FAIL",
            "all_dense_nonadjacent_intersection_samples": "PASS" if all_intersection_free else "FAIL",
            "bilateral_motion_mirror": "PASS" if all_bilateral_mirror else "FAIL",
            "exact_loop_closure": "PASS" if all(value <= 1e-12 for value in loop_residual_m.values()) else "FAIL",
            "authored_keys_are_dense_subset": "PASS" if authored_subset_max_angle_residual <= 1e-12 else "FAIL",
            "hidden_subframe_overshoot_control": "PASS_EXPECTED_REJECTION" if negative["rejected"] else "FAIL",
            "mathematical_continuity": "NOT_PROVEN",
            "target_engine_interpolation": "NOT_EVALUATED",
            "target_engine_playback": "NOT_EVALUATED",
            "technical_art_transport": "NOT_EVALUATED",
            "runtime_controller": "NOT_EVALUATED",
            "gameplay": "NOT_EVALUATED",
            "final_visual_acceptance": "NOT_EVALUATED",
        },
        "handoffs": {
            "rigging": (
                "Animation consumed exact current Rigging identity without changing source, topology, joints, release profile, "
                "or the measured +36.55/+36.60 boundary. The diagnostic clip stays at +/-30 degrees."
            ),
            "materials_visual_qa_art": (
                "This exact clip is now a bounded temporal review surface. A future shaded/full-body receiver may consume it, "
                "but no visual acceptance is transferred from source-deformation sampling."
            ),
            "technical_art_runtime": (
                "No skeleton/skin transport, target-engine interpolation/playback, controller/state-machine, device, or performance claim is made."
            ),
        },
        "truth_boundary": [
            "The Animation-owned curve is new, but Organic source, Geometry opening_repair topology, Rigging joints and the angle-conditioned release profile are unchanged.",
            "The +/-30 degree amplitude is a conservative diagnostic choice inside the current measured positive finite boundary; it is not anatomy or an Animation range-of-motion prescription.",
            "The 160 Hz dense observer is finite sampled source/deformation evidence and is not mathematical continuous-motion proof.",
            "The hidden-subframe negative control changes no authored 40 Hz key and exists only to prove the denser Animation observer can detect an in-between overshoot.",
            "No target-engine interpolation/playback, Technical Art transport, Runtime/controller, gameplay/collision/input, final Art/QA, CANON, production-readiness, game-readiness, or Animation-mastery claim is made.",
        ],
    }
