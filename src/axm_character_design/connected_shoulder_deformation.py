"""Bounded rigging/deformation probe for the exact connected Character shoulders.

This module consumes Geometry PR #3's exact connected shoulder specimens and the
adopted Character shoulder source. It authors one Rigging-only two-transform
socket/arm weighting candidate and compares it with an explicit conservative
anchored-proximal control across mirrored +/-40 degree front-plane poses.

It does not change source or Geometry identity, and it does not claim Animation,
runtime, gameplay, anatomy, or visual-quality acceptance.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path

from .organic_form import _ellipsoid_mesh, canonical_digest, write_obj
from .shoulder_connected_topology import build_connected_shoulder_specimen
from .shoulder_source_lineage import adopted_character_source

SCHEMA = "axm.character-connected-shoulder-rigging-evidence/v0.1"
RIG_SCHEMA = "axm.character-connected-shoulder-rig-plan/v0.1"
RIG_ID = "character-connected-shoulder-socket-rig-001"
STATUS = "PASS_CHARACTER_CONNECTED_SHOULDER_BOUNDED_SOCKET_DEFORMATION"

GEOMETRY_HEAD = "dcb2185a42072540ef2be37329735357561e01b5"
SOURCE_ID = "character-neutral-a-shoulder-source-004"
SOURCE_DIGEST = "dbb20e6e7dc1874b3b22553d0407791f05699f23ebb42c4e249a259f56613f1d"
SOURCE_MESH_DIGEST = "30a4612212f2e8252b6f813912ce76c655763e6d3abb4650c04ad1af72baea7f"
CANDIDATE_DIGESTS = {
    "L": "0f36b0df287581bc94cc88a000c09bda6f126f44be6a088fbb853f52a31fc19f",
    "R": "171a17bd20c0871736bc1ee229ce4c2f06d4e80405e996dcc2e184541996161d",
}
POSE_ANGLES_DEG = (-40.0, 0.0, 40.0)
CANDIDATE_PROXIMAL_WEIGHT = 0.10
CONTROL_PROXIMAL_WEIGHT = 0.0
DRIFT_TOLERANCE = 1e-9
METRIC_TOLERANCE = 1e-9


def _add(a, b):
    return tuple(float(a[i]) + float(b[i]) for i in range(3))


def _sub(a, b):
    return tuple(float(a[i]) - float(b[i]) for i in range(3))


def _mul(a, scalar):
    return tuple(float(a[i]) * float(scalar) for i in range(3))


def _dot(a, b):
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _cross(a, b):
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _length(value):
    return math.sqrt(_dot(value, value))


def _unit(value, label):
    size = _length(value)
    if size <= 1e-12:
        raise ValueError(f"{label} must have non-zero length")
    return _mul(value, 1.0 / size)


def _rotate_about_axis(point, origin, axis, angle_deg):
    value = _sub(point, origin)
    direction = _unit(axis, "shoulder axis")
    angle = math.radians(float(angle_deg))
    c, s = math.cos(angle), math.sin(angle)
    rotated = _add(
        _add(_mul(value, c), _mul(_cross(direction, value), s)),
        _mul(direction, _dot(direction, value) * (1.0 - c)),
    )
    return _add(origin, rotated)


def _triangle_area(positions, face):
    a, b, c = (positions[index] for index in face)
    return 0.5 * _length(_cross(_sub(b, a), _sub(c, a)))


def _edge_ratios(before, after, faces):
    edges = set()
    for face in faces:
        for first, second in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edges.add(tuple(sorted((first, second))))
    ratios = []
    for first, second in edges:
        base = math.dist(before[first], before[second])
        posed = math.dist(after[first], after[second])
        if base > 1e-12:
            ratios.append(posed / base)
    if not ratios:
        raise ValueError("connected shoulder must contain measurable edges")
    return min(ratios), max(ratios)


def rig_plan():
    return {
        "schema": RIG_SCHEMA,
        "rig_id": RIG_ID,
        "source": {
            "source_id": SOURCE_ID,
            "source_digest": SOURCE_DIGEST,
            "source_mesh_digest": SOURCE_MESH_DIGEST,
        },
        "geometry": {
            "repository": "mike-axiom-mir/axm-character-design",
            "head": GEOMETRY_HEAD,
            "left_candidate_digest": CANDIDATE_DIGESTS["L"],
            "right_candidate_digest": CANDIDATE_DIGESTS["R"],
        },
        "joints": {
            "L": {
                "id": "shoulder-L",
                "landmark": "shoulder_L",
                "axis": [0.0, -1.0, 0.0],
                "local_delta_pose_angles_deg": list(POSE_ANGLES_DEG),
            },
            "R": {
                "id": "shoulder-R",
                "landmark": "shoulder_R",
                "axis": [0.0, 1.0, 0.0],
                "local_delta_pose_angles_deg": list(POSE_ANGLES_DEG),
            },
        },
        "weights": {
            "torso_and_seam_child_weight": 0.0,
            "proximal_arm_ring_child_weight": CANDIDATE_PROXIMAL_WEIGHT,
            "distal_arm_ring_and_cap_child_weight": 1.0,
            "control_proximal_arm_ring_child_weight": CONTROL_PROXIMAL_WEIGHT,
            "method": "TWO_TRANSFORM_LINEAR_BLEND__TORSO_SOCKET_FIXED__TEN_PERCENT_PROXIMAL_RELEASE",
        },
        "truth_boundary": {
            "rigging_candidate_only": True,
            "source_or_geometry_rewritten": False,
            "pose_angles_are_bounded_test_deltas_not_anatomical_limits": True,
            "animation_acceptance": False,
            "runtime_acceptance": False,
            "gameplay_acceptance": False,
            "visual_acceptance": False,
        },
    }


def _validate_plan(plan):
    expected = rig_plan()
    if plan != expected:
        raise ValueError("connected shoulder rig plan identity drift")
    return expected


def _specimen_layout(source, specimen):
    masses = {row["id"]: row for row in source["masses"]}
    ribcage = masses.get("ribcage")
    if ribcage is None:
        raise ValueError("adopted Character source lost ribcage")
    rib_positions, _ = _ellipsoid_mesh(ribcage["center"], ribcage["radii"])
    rib_count = len(rib_positions)
    if len(specimen["positions"]) != rib_count + 31:
        raise ValueError("connected shoulder vertex layout drift")
    return {
        "ribcage": (0, rib_count),
        "seam": (rib_count, rib_count + 10),
        "proximal": (rib_count + 10, rib_count + 20),
        "distal": (rib_count + 20, rib_count + 30),
        "distal_cap": (rib_count + 30, rib_count + 31),
    }


def _weights(layout, proximal_weight):
    total = layout["distal_cap"][1]
    values = [None] * total
    for name in ("ribcage", "seam"):
        start, end = layout[name]
        values[start:end] = [0.0] * (end - start)
    start, end = layout["proximal"]
    values[start:end] = [float(proximal_weight)] * (end - start)
    for name in ("distal", "distal_cap"):
        start, end = layout[name]
        values[start:end] = [1.0] * (end - start)
    if any(value is None for value in values):
        raise ValueError("connected shoulder weight layout incomplete")
    return values


def _pose(specimen, origin, axis, angle_deg, child_weights):
    before = [tuple(float(value) for value in point) for point in specimen["positions"]]
    faces = specimen["faces"]
    source_areas = [_triangle_area(before, face) for face in faces]
    if min(source_areas) <= 1e-12:
        raise ValueError("connected shoulder contains degenerate neutral triangle")

    after = []
    fixed_drift = 0.0
    rigid_radius_drift = 0.0
    for point, child_weight in zip(before, child_weights):
        rotated = _rotate_about_axis(point, origin, axis, angle_deg)
        current = _add(point, _mul(_sub(rotated, point), child_weight))
        after.append(current)
        if child_weight <= 1e-12:
            fixed_drift = max(fixed_drift, math.dist(point, current))
        if child_weight >= 1.0 - 1e-12:
            rigid_radius_drift = max(
                rigid_radius_drift,
                abs(math.dist(point, origin) - math.dist(current, origin)),
            )

    posed_areas = [_triangle_area(after, face) for face in faces]
    collapsed = sum(area <= 1e-12 for area in posed_areas)
    area_ratios = [after_area / before_area for before_area, after_area in zip(source_areas, posed_areas)]
    min_edge, max_edge = _edge_ratios(before, after, faces)
    neutral_drift = max(math.dist(a, b) for a, b in zip(before, after)) if angle_deg == 0 else None
    finite = all(math.isfinite(value) for point in after for value in point)
    return {
        "angle_deg": float(angle_deg),
        "positions": after,
        "finite": finite,
        "collapsed_triangles": collapsed,
        "minimum_triangle_area_ratio": min(area_ratios),
        "maximum_triangle_area_ratio": max(area_ratios),
        "minimum_edge_length_ratio": min_edge,
        "maximum_edge_length_ratio": max_edge,
        "fixed_socket_max_drift_m": fixed_drift,
        "rigid_arm_radius_max_drift_m": rigid_radius_drift,
        "neutral_max_vertex_drift_m": neutral_drift,
    }


def _pose_status(row):
    return (
        row["finite"]
        and row["collapsed_triangles"] == 0
        and row["fixed_socket_max_drift_m"] <= DRIFT_TOLERANCE
        and row["rigid_arm_radius_max_drift_m"] <= DRIFT_TOLERANCE
        and (row["neutral_max_vertex_drift_m"] is None or row["neutral_max_vertex_drift_m"] <= DRIFT_TOLERANCE)
    )


def _improves_control(candidate, control):
    return (
        candidate["minimum_triangle_area_ratio"] + METRIC_TOLERANCE >= control["minimum_triangle_area_ratio"]
        and candidate["maximum_triangle_area_ratio"] <= control["maximum_triangle_area_ratio"] + METRIC_TOLERANCE
        and candidate["minimum_edge_length_ratio"] + METRIC_TOLERANCE >= control["minimum_edge_length_ratio"]
        and candidate["maximum_edge_length_ratio"] <= control["maximum_edge_length_ratio"] + METRIC_TOLERANCE
        and (
            candidate["minimum_triangle_area_ratio"] > control["minimum_triangle_area_ratio"] + METRIC_TOLERANCE
            or candidate["maximum_triangle_area_ratio"] + METRIC_TOLERANCE < control["maximum_triangle_area_ratio"]
            or candidate["minimum_edge_length_ratio"] > control["minimum_edge_length_ratio"] + METRIC_TOLERANCE
            or candidate["maximum_edge_length_ratio"] + METRIC_TOLERANCE < control["maximum_edge_length_ratio"]
        )
    )


def _mirror_position_set(positions):
    return {
        (round(-float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in positions
    }


def _position_set(positions):
    return {
        (round(float(point[0]), 9), round(float(point[1]), 9), round(float(point[2]), 9))
        for point in positions
    }


def audit_connected_shoulder_deformation(plan=None):
    plan = _validate_plan(plan or rig_plan())
    source = adopted_character_source()
    if source.get("study_id") != SOURCE_ID or canonical_digest(source) != SOURCE_DIGEST:
        raise ValueError("adopted Character source identity drift")

    specimens = {side: build_connected_shoulder_specimen(side) for side in ("L", "R")}
    results = {}
    all_pass = True
    for side in ("L", "R"):
        specimen = specimens[side]
        observed_digest = canonical_digest({"positions": specimen["positions"], "faces": specimen["faces"]})
        if observed_digest != CANDIDATE_DIGESTS[side]:
            raise ValueError(f"connected shoulder {side} Geometry identity drift: {observed_digest}")
        if specimen["local_preflight"]["status"] != "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT":
            raise ValueError(f"connected shoulder {side} Geometry prerequisite no longer passes")
        layout = _specimen_layout(source, specimen)
        candidate_weights = _weights(layout, CANDIDATE_PROXIMAL_WEIGHT)
        control_weights = _weights(layout, CONTROL_PROXIMAL_WEIGHT)
        joint = plan["joints"][side]
        origin = tuple(source["landmarks"][joint["landmark"]])
        axis = tuple(joint["axis"])

        candidate_rows = []
        control_rows = []
        for angle in POSE_ANGLES_DEG:
            candidate = _pose(specimen, origin, axis, angle, candidate_weights)
            control = _pose(specimen, origin, axis, angle, control_weights)
            candidate["status"] = "PASS" if _pose_status(candidate) else "FAIL"
            control["status"] = "PASS" if _pose_status(control) else "FAIL"
            candidate["improves_anchored_proximal_control"] = (
                True if angle == 0 else _improves_control(candidate, control)
            )
            all_pass &= candidate["status"] == "PASS"
            all_pass &= candidate["improves_anchored_proximal_control"]
            candidate_rows.append(candidate)
            control_rows.append(control)

        results[side] = {
            "geometry_digest": observed_digest,
            "layout": layout,
            "weight_counts": {
                "fixed": sum(value <= 1e-12 for value in candidate_weights),
                "blended": sum(1e-12 < value < 1.0 - 1e-12 for value in candidate_weights),
                "rigid": sum(value >= 1.0 - 1e-12 for value in candidate_weights),
            },
            "candidate": candidate_rows,
            "anchored_proximal_control": control_rows,
        }

    for index, angle in enumerate(POSE_ANGLES_DEG):
        mirrored = _mirror_position_set(results["L"]["candidate"][index]["positions"])
        observed = _position_set(results["R"]["candidate"][index]["positions"])
        if mirrored != observed:
            all_pass = False
            results["L"]["candidate"][index]["bilateral_mirrored_position_set"] = False
            results["R"]["candidate"][index]["bilateral_mirrored_position_set"] = False
        else:
            results["L"]["candidate"][index]["bilateral_mirrored_position_set"] = True
            results["R"]["candidate"][index]["bilateral_mirrored_position_set"] = True

    for side in ("L", "R"):
        for bucket in ("candidate", "anchored_proximal_control"):
            for row in results[side][bucket]:
                row["positions"] = [[round(value, 9) for value in point] for point in row["positions"]]
                for key in (
                    "minimum_triangle_area_ratio", "maximum_triangle_area_ratio",
                    "minimum_edge_length_ratio", "maximum_edge_length_ratio",
                    "fixed_socket_max_drift_m", "rigid_arm_radius_max_drift_m",
                ):
                    row[key] = round(float(row[key]), 12)
                if row["neutral_max_vertex_drift_m"] is not None:
                    row["neutral_max_vertex_drift_m"] = round(float(row["neutral_max_vertex_drift_m"]), 12)

    return {
        "schema": SCHEMA,
        "status": STATUS if all_pass else "FAIL_CHARACTER_CONNECTED_SHOULDER_BOUNDED_SOCKET_DEFORMATION",
        "rig_plan": plan,
        "rig_plan_digest": canonical_digest(plan),
        "source_id": SOURCE_ID,
        "source_digest": SOURCE_DIGEST,
        "source_mesh_digest": SOURCE_MESH_DIGEST,
        "geometry_head": GEOMETRY_HEAD,
        "pose_scope": {
            "angles_deg": list(POSE_ANGLES_DEG),
            "interpretation": "local front-plane deltas around the neutral A-rest shoulder; bounded structural samples, not anatomy or controller limits",
        },
        "results": results,
        "gates": {
            "exact_source_identity": "PASS",
            "exact_geometry_candidate_identity": "PASS",
            "fixed_torso_and_seam_socket": "PASS" if all_pass else "FAIL",
            "rigid_distal_arm_radius": "PASS" if all_pass else "FAIL",
            "neutral_return": "PASS" if all_pass else "FAIL",
            "bilateral_mirrored_pose_position_sets": "PASS" if all_pass else "FAIL",
            "ten_percent_proximal_release_nonworse_and_strictly_better_than_zero_release_at_nonzero_boundaries": "PASS" if all_pass else "FAIL",
            "animation": "NOT_CLAIMED",
            "runtime": "NOT_CLAIMED",
            "gameplay": "NOT_CLAIMED",
            "visual_deformation_quality": "NOT_CLAIMED",
            "self_intersection": "NOT_CHECKED",
        },
        "truth_boundary": [
            "Rigging-only two-transform weighting candidate over the exact Geometry PR #3 connected shoulder specimens; source and Geometry bytes are not rewritten",
            "the 10% proximal release is compared directly against a 0% anchored-proximal control on both mirrored shoulders at -40/0/+40 degree local deltas",
            "distortion metrics are structural diagnostics only and are not aesthetic, anatomical, or production thresholds",
            "self-intersection, continuous interpolation between sampled poses, volume preservation, authored normals/tangents, Animation, runtime/controller, gameplay, target-device behavior, CANON, production readiness, game readiness, and Rigging mastery remain unclaimed",
        ],
    }


def build_connected_shoulder_deformation_evidence(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = audit_connected_shoulder_deformation()
    if receipt["status"] != STATUS:
        raise ValueError(receipt["status"])

    (out / "rig-plan.json").write_text(
        json.dumps(rig_plan(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "connected-shoulder-rigging-audit.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for side in ("L", "R"):
        specimen = build_connected_shoulder_specimen(side)
        for row in receipt["results"][side]["candidate"]:
            angle = int(row["angle_deg"])
            label = f"p{angle}" if angle >= 0 else f"m{abs(angle)}"
            write_obj(
                {"vertices": row["positions"], "faces": specimen["faces"], "regions": []},
                out / f"connected-shoulder-{side.lower()}-{label}.obj",
            )
    return receipt
