from __future__ import annotations

from .organic_form import (
    _segment_mesh,
    canonical_digest,
    neutral_character_study,
    validate_study,
)

SCHEMA = "axm.character-flex-transition-audit/v0.1"
STATUS = "PASS_EXPLICIT_NEUTRAL_FLEX_CONTEXT"

# These are declared flex zones that already have two source-owned segment
# endpoints meeting at the flex zone's landmark. The audit records any radius
# step; it does not average or silently repair source values.
INTERNAL_TRANSITIONS = (
    ("elbow_L", "upper_arm_L", "lower_arm_L"),
    ("wrist_L", "lower_arm_L", "hand_L"),
    ("elbow_R", "upper_arm_R", "lower_arm_R"),
    ("wrist_R", "lower_arm_R", "hand_R"),
    ("knee_L", "thigh_L", "shin_L"),
    ("ankle_L", "shin_L", "foot_L"),
    ("knee_R", "thigh_R", "shin_R"),
    ("ankle_R", "shin_R", "foot_R"),
)

# These flex zones meet a source-owned ellipsoid mass rather than a second
# segment. We therefore record neutral overlap context only. No connected
# topology, skinning reserve, or deformation quality is inferred from it.
MASS_INTERFACES = (
    ("neck", "neck", "ribcage"),
    ("shoulder_L", "upper_arm_L", "ribcage"),
    ("shoulder_R", "upper_arm_R", "ribcage"),
    ("hip_L", "thigh_L", "pelvis"),
    ("hip_R", "thigh_R", "pelvis"),
)


def _ellipsoid_implicit(point, mass):
    return sum(
        ((point[i] - mass["center"][i]) / mass["radii"][i]) ** 2
        for i in range(3)
    )


def _rounded(value):
    return round(float(value), 12)


def audit_flex_transitions(study=None):
    study = study or neutral_character_study()
    validate_study(study)

    landmarks = study["landmarks"]
    segments = {segment["id"]: segment for segment in study["segments"]}
    masses = {mass["id"]: mass for mass in study["masses"]}
    flex_landmarks = {zone["id"]: zone["landmark"] for zone in study["flex_zones"]}
    tolerance = study["design_constraints"]["bilateral_tolerance_m"]

    internal = []
    for flex_id, proximal_id, distal_id in INTERNAL_TRANSITIONS:
        landmark = flex_landmarks.get(flex_id)
        if landmark is None:
            raise ValueError(f"unknown declared flex zone: {flex_id}")
        proximal = segments[proximal_id]
        distal = segments[distal_id]
        if proximal["b"] != landmark or distal["a"] != landmark:
            raise ValueError(f"transition landmark binding drift: {flex_id}")
        proximal_radius = float(proximal["radius_b"])
        distal_radius = float(distal["radius_a"])
        signed_delta = distal_radius - proximal_radius
        internal.append(
            {
                "flex_zone": flex_id,
                "landmark": landmark,
                "proximal_segment": proximal_id,
                "distal_segment": distal_id,
                "proximal_radius_m": proximal_radius,
                "distal_radius_m": distal_radius,
                "signed_radius_delta_m": _rounded(signed_delta),
                "abs_radius_delta_m": _rounded(abs(signed_delta)),
                "abs_delta_ratio_to_proximal": _rounded(
                    abs(signed_delta) / proximal_radius
                ),
                "observation": (
                    "EXACT_RADIUS_MATCH"
                    if abs(signed_delta) <= tolerance
                    else "SOURCE_RADIUS_STEP_RECORDED_NOT_REPAIRED"
                ),
            }
        )

    internal_by_id = {entry["flex_zone"]: entry for entry in internal}
    for base in ("elbow", "wrist", "knee", "ankle"):
        left = internal_by_id[f"{base}_L"]["signed_radius_delta_m"]
        right = internal_by_id[f"{base}_R"]["signed_radius_delta_m"]
        if abs(left - right) > tolerance:
            raise ValueError(f"bilateral transition delta mismatch: {base}")

    mass_interfaces = []
    for flex_id, segment_id, mass_id in MASS_INTERFACES:
        landmark = flex_landmarks.get(flex_id)
        if landmark is None:
            raise ValueError(f"unknown declared flex zone: {flex_id}")
        segment = segments[segment_id]
        mass = masses[mass_id]
        if segment["a"] != landmark:
            raise ValueError(f"mass-interface landmark binding drift: {flex_id}")
        root = landmarks[landmark]
        tip = landmarks[segment["b"]]
        root_ring, _ = _segment_mesh(
            root,
            tip,
            float(segment["radius_a"]),
            float(segment["radius_b"]),
            sides=10,
        )
        root_ring = root_ring[:10]
        implicit_values = [_ellipsoid_implicit(point, mass) for point in root_ring]
        inside_count = sum(value <= 1.0 + tolerance for value in implicit_values)
        mass_interfaces.append(
            {
                "flex_zone": flex_id,
                "landmark": landmark,
                "segment": segment_id,
                "mass": mass_id,
                "segment_root_radius_m": float(segment["radius_a"]),
                "landmark_mass_implicit": _rounded(_ellipsoid_implicit(root, mass)),
                "root_ring_sample_count": len(root_ring),
                "root_ring_samples_inside_or_on_mass": inside_count,
                "root_ring_min_mass_implicit": _rounded(min(implicit_values)),
                "root_ring_max_mass_implicit": _rounded(max(implicit_values)),
                "observation": "NEUTRAL_OVERLAP_CONTEXT_ONLY_NOT_DEFORMATION_GATE",
            }
        )

    audited_ids = {entry["flex_zone"] for entry in internal} | {
        entry["flex_zone"] for entry in mass_interfaces
    }
    declared_ids = set(flex_landmarks)
    if audited_ids != declared_ids:
        missing = sorted(declared_ids - audited_ids)
        extra = sorted(audited_ids - declared_ids)
        raise ValueError(f"flex audit coverage drift: missing={missing} extra={extra}")

    exact_match_count = sum(
        entry["observation"] == "EXACT_RADIUS_MATCH" for entry in internal
    )
    radius_step_count = len(internal) - exact_match_count
    max_abs_delta = max(entry["abs_radius_delta_m"] for entry in internal)
    max_ratio = max(entry["abs_delta_ratio_to_proximal"] for entry in internal)
    least_inside = min(
        item["root_ring_samples_inside_or_on_mass"] for item in mass_interfaces
    )

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "study_id": study["study_id"],
        "source_digest": canonical_digest(study),
        "source_geometry_modified_by_audit": False,
        "coverage": {
            "declared_flex_zone_count": len(declared_ids),
            "audited_flex_zone_count": len(audited_ids),
            "internal_segment_transition_count": len(internal),
            "mass_interface_count": len(mass_interfaces),
        },
        "internal_segment_transitions": internal,
        "mass_interfaces": mass_interfaces,
        "summary": {
            "exact_radius_match_count": exact_match_count,
            "source_radius_step_count": radius_step_count,
            "max_abs_radius_delta_m": _rounded(max_abs_delta),
            "max_abs_delta_ratio_to_proximal": _rounded(max_ratio),
            "least_embedded_mass_interfaces_by_root_ring_samples": [
                entry["flex_zone"]
                for entry in mass_interfaces
                if entry["root_ring_samples_inside_or_on_mass"] == least_inside
            ],
        },
        "gates": {
            "declared-flex-zone-coverage": "PASS",
            "bilateral-transition-deltas": "PASS",
            "source-radius-steps-preserved": "PASS",
            "mass-interface-neutral-context": "RECORDED_NOT_DEFORMATION_GATE",
            "rigging-or-deformation-acceptance": "NOT_CLAIMED",
        },
        "truth_boundary": [
            "neutral source-form transition evidence only; no pose deformation was executed",
            "radius steps are recorded source truth, not automatically defects and not silently averaged",
            "mass-interface root-ring overlap is a neutral geometric observation, not connected-topology or skinning proof",
            "no biological/anatomical validation, rig acceptance, animation, runtime, gameplay, CANON, or mastery claim",
        ],
    }
