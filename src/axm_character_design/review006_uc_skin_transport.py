"""Bounded Character review-006 -> UC rigged-animation transport.

This module is owned by Technical Art.  It does not redefine Character source,
topology, rigging, animation, or material semantics.  It binds the exact current
review-006 Animation/Rigging receiver to ordinary glTF 2.0 skin/TRS machinery so
current Universal Creation can independently execute the transported positions.

One Character-specific complication is explicit rather than hidden: the current
Rigging lane drives the proximal-ring child weight as a function of shoulder
angle. glTF skin weights are static.  For this exact bounded diagnostic clip we
factor that dynamic blend into a static 1/8 skin weight plus an animated helper
joint whose Y-axis-equivalent rotation and XZ scale exactly represent the same
linear map.  The factorization is mathematical transport plumbing, not a new rig
policy and not a UC feature.

Current UC pose execution evaluates positions, not deformed normals/tangents.
Neutral smooth normals are retained for a valid GLB, while a separate exact
reference packet keeps pose-recomputed direction-frame evidence visible.  A
position PASS therefore cannot silently become a direction-frame PASS.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from typing import Any

from .organic_form import canonical_digest
from .review006_connected_geometry import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    build_opening_repair,
)
from .review006_shoulder_animation_diagnostic import (
    AUTHORED_HZ,
    CLIP_ID,
    DENSE_HZ,
    DENSE_SAMPLE_COUNT,
    DURATION_S,
    RIGGING_HEAD,
    _phase_angle,
    animation_contract,
    clip_digest,
)
from .review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    _pose,
    _reindexed_layout,
    _weights,
    rebind_contract,
    release_weight,
)
from .shoulder_pose_clearance_refinement import shoulder_pose_clearance_refinement_candidate

SCHEMA = "axm.character-review006-uc-skin-transport/v0.1"
POSITION_STATUS = "PASS_CHARACTER_REVIEW006_DYNAMIC_RELEASE_TO_STATIC_GLTF_TRS_SKIN_DENSE_KEYS"
DIRECTION_STATUS = "HOLD_CHARACTER_REVIEW006_DEFORMED_DIRECTION_FRAME_NOT_EVALUATED_BY_CURRENT_UC_POSE_RUNTIME"

ANIMATION_HEAD = "9519be55581c009fd800d175677d9b50ee6926e6"
UC_HEAD = "7edbc9544d52207a6f09cb85889d1587e22d4442"
UC_GAME_POSE_RUNTIME_BLOB = "dee5db003a56a0a5f55092c1b3db50f56a22de7e"
MATERIALS_HEAD = "e450684b398f8e5b0e23c4cbf717e3475dd4d5ee"
MATERIALS_NORMAL_TOOL_BLOB = "843c0e1866172dd8b6c5ab0f23d69d1e469562f7"

# Exact binary fractions.  Current release_weight never exceeds 0.10, so 1/8
# leaves headroom while keeping both stored weights exactly representable.
STATIC_CORRECTION_WEIGHT = 0.125
STATIC_ROOT_WEIGHT = 0.875
POSITION_TOLERANCE_M = 5e-6

JOINTS = {
    "root": 0,
    "L_distal": 1,
    "L_release": 2,
    "R_distal": 3,
    "R_release": 4,
}


@dataclass(frozen=True)
class PackedCharacterGlb:
    bytes: bytes
    document: dict[str, Any]
    times: list[float]
    angles: list[float]
    source_vertex_counts: dict[str, int]
    source_triangle_counts: dict[str, int]


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def source_to_gltf(value) -> list[float]:
    """Rotate Character Z-up coordinates to glTF Y-up without reflection.

    This is R_x(-90deg): (x, y, z) -> (x, z, -y).  Determinant is +1, so
    triangle winding and axial-vector handedness are preserved.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("Character vector must contain exactly three components")
    row = [float(item) for item in value]
    if not all(math.isfinite(item) for item in row):
        raise ValueError("Character vector must be finite")
    return [row[0], row[2], -row[1]]


def _sub(a, b):
    return [float(a[i]) - float(b[i]) for i in range(3)]


def _cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _dot(a, b):
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _unit(value, label="vector"):
    size = math.sqrt(_dot(value, value))
    if not math.isfinite(size) or size <= 1e-15:
        raise ValueError(f"{label} must have non-zero finite length")
    return [float(item) / size for item in value]


def smooth_normals(positions, faces):
    """Exact Materials-review method: area-weighted indexed smooth normals."""
    accum = [[0.0, 0.0, 0.0] for _ in positions]
    for face in faces:
        if len(face) != 3:
            raise ValueError("normal receiver requires triangle faces")
        a, b, c = (int(index) for index in face)
        normal = _cross(_sub(positions[b], positions[a]), _sub(positions[c], positions[a]))
        if math.sqrt(_dot(normal, normal)) <= 1e-15:
            raise ValueError("normal receiver contains a degenerate face")
        for index in (a, b, c):
            for dim in range(3):
                accum[index][dim] += normal[dim]
    return [_unit(row, "accumulated smooth normal") for row in accum]


def _quat(axis, angle_deg):
    direction = _unit(axis, "joint axis")
    half = math.radians(float(angle_deg)) * 0.5
    sine = math.sin(half)
    return [
        _f32(direction[0] * sine),
        _f32(direction[1] * sine),
        _f32(direction[2] * sine),
        _f32(math.cos(half)),
    ]


def correction_transform(angle_deg: float) -> dict[str, Any]:
    """Factor Rigging's dynamic proximal blend into static LBS + TRS.

    Desired proximal map around the shoulder is
        D = (1-w) I + w R(theta).
    With a static skin weight alpha=1/8, choose helper map
        C = (1-k) I + k R(theta), k=w/alpha,
    so (1-alpha)I + alpha*C == D exactly in real arithmetic.

    Because current shoulder axes map to glTF +/-Z, the plane orthogonal to the
    axis is XY.  C is a uniform contraction in that plane plus a rotation about
    the same axis, hence it is ordinary glTF rotation + scale.
    """
    theta = math.radians(float(angle_deg))
    weight = float(release_weight(angle_deg))
    k = weight / STATIC_CORRECTION_WEIGHT
    if not (0.0 <= k <= 1.0 + 1e-12):
        raise ValueError("dynamic release exceeds bounded static correction weight")
    a = 1.0 - k + k * math.cos(theta)
    b = k * math.sin(theta)
    planar_scale = math.hypot(a, b)
    helper_angle_deg = math.degrees(math.atan2(b, a))
    return {
        "release_weight": weight,
        "static_correction_weight": STATIC_CORRECTION_WEIGHT,
        "k": k,
        "planar_scale": planar_scale,
        "helper_angle_deg": helper_angle_deg,
    }


def transport_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": POSITION_STATUS,
        "source": {
            "review006_source_sha256": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_sha256": EXPECTED_REVIEW006_MESH_DIGEST,
            "geometry_head": GEOMETRY_HEAD,
            "topology_digests": dict(EXPECTED_TOPOLOGY_DIGESTS),
        },
        "rigging": {
            "head": RIGGING_HEAD,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
            "dynamic_release_function_reauthored": False,
            "static_transport_correction_weight": STATIC_CORRECTION_WEIGHT,
            "static_transport_root_weight": STATIC_ROOT_WEIGHT,
        },
        "animation": {
            "head": ANIMATION_HEAD,
            "clip_id": CLIP_ID,
            "clip_digest": clip_digest(),
            "duration_s": DURATION_S,
            "authored_hz": AUTHORED_HZ,
            "transport_key_hz": DENSE_HZ,
            "transport_key_count": DENSE_SAMPLE_COUNT,
            "source_curve_reauthored": False,
        },
        "uc_receiver": {
            "head": UC_HEAD,
            "game_pose_runtime_blob": UC_GAME_POSE_RUNTIME_BLOB,
            "position_api": "GamePoseAsset.sample(..., vertices=True)",
            "deformed_direction_frame_api": "NOT_AVAILABLE_IN_BOUND_RECEIVER",
        },
        "materials_reference": {
            "head": MATERIALS_HEAD,
            "normal_evidence_tool_blob": MATERIALS_NORMAL_TOOL_BLOB,
            "normal_method": "AREA_WEIGHTED_INDEXED_VERTEX_SMOOTH_NORMAL",
            "semantics_copied_into_uc": False,
        },
        "coordinate_adapter": {
            "source": "Character source frame: Z-up",
            "target": "glTF Y-up",
            "map": "(x,y,z)->(x,z,-y)",
            "determinant": 1,
            "winding_reversed": False,
        },
        "truth_boundary": {
            "position_transport_at_321_exact_dense_keys": "EVALUATED",
            "between_transport_key_interpolation": "NOT_CLAIMED",
            "deformed_normals_or_tangents": DIRECTION_STATUS,
            "target_engine_rendering": "NOT_EVALUATED",
            "runtime_controller_or_gameplay": "NOT_EVALUATED",
            "source_adoption_or_canon": False,
            "production_readiness": False,
        },
    }


def _validate_dependencies():
    source = shoulder_pose_clearance_refinement_candidate()
    if canonical_digest(source) != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review-006 source identity drift")
    rig = rebind_contract()
    if rig["geometry"]["head"] != GEOMETRY_HEAD:
        raise ValueError("Geometry dependency drift")
    if rig["rig_method"]["profile_digest"] != EXPECTED_PROFILE_DIGEST:
        raise ValueError("Rigging profile drift")
    anim = animation_contract()
    if anim["rigging"]["exact_parent_head"] != RIGGING_HEAD:
        raise ValueError("Animation/Rigging lineage drift")
    if anim["clip"]["digest"] != clip_digest():
        raise ValueError("Animation clip identity drift")
    return source, rig


def _side_context(side: str, source, rig):
    specimen = build_opening_repair(side)
    if canonical_digest({"positions": specimen["positions"], "faces": specimen["faces"]}) != EXPECTED_TOPOLOGY_DIGESTS[side]:
        raise ValueError(f"{side} topology identity drift")
    layout = _reindexed_layout(side, specimen)
    joint = rig["rig_method"]["joint_semantics"][side]
    origin = [float(value) for value in source["landmarks"][joint["landmark"]]]
    axis = [float(value) for value in joint["axis"]]
    return {"specimen": specimen, "layout": layout, "origin": origin, "axis": axis}


def side_contexts():
    source, rig = _validate_dependencies()
    return {side: _side_context(side, source, rig) for side in ("L", "R")}


def owner_pose(side: str, angle_deg: float, contexts=None):
    contexts = contexts or side_contexts()
    context = contexts[side]
    specimen = context["specimen"]
    row = _pose(
        specimen,
        context["origin"],
        context["axis"],
        float(angle_deg),
        _weights(context["layout"], release_weight(angle_deg), len(specimen["positions"])),
    )
    return row["positions"]


def _static_skin_rows(side: str, context):
    vertex_count = len(context["specimen"]["positions"])
    group_for = {}
    for group, indexes in context["layout"]["groups"].items():
        for index in indexes:
            group_for[index] = group
    if sorted(group_for) != list(range(vertex_count)):
        raise ValueError(f"{side} static skin grouping does not cover all vertices")
    distal = JOINTS[f"{side}_distal"]
    helper = JOINTS[f"{side}_release"]
    joints, weights = [], []
    for index in range(vertex_count):
        group = group_for[index]
        if group in ("ribcage", "seam"):
            joints.append([JOINTS["root"], 0, 0, 0])
            weights.append([1.0, 0.0, 0.0, 0.0])
        elif group == "proximal":
            joints.append([JOINTS["root"], helper, 0, 0])
            weights.append([STATIC_ROOT_WEIGHT, STATIC_CORRECTION_WEIGHT, 0.0, 0.0])
        elif group in ("distal", "distal_cap"):
            joints.append([distal, 0, 0, 0])
            weights.append([1.0, 0.0, 0.0, 0.0])
        else:
            raise ValueError(f"unexpected Rigging group: {group}")
    return joints, weights


def _rotate_about_axis(point, origin, axis, angle_deg, scale_plane=1.0):
    direction = _unit(axis, "transport axis")
    local = _sub(point, origin)
    # All bound axes map to +/-Z.  Scale the orthogonal XY plane before rotation.
    if abs(abs(direction[2]) - 1.0) > 1e-12 or abs(direction[0]) > 1e-12 or abs(direction[1]) > 1e-12:
        raise ValueError("bounded Character transport expects mapped +/-Z shoulder axes")
    scaled = [local[0] * scale_plane, local[1] * scale_plane, local[2]]
    angle = math.radians(float(angle_deg))
    c, s = math.cos(angle), math.sin(angle) * (1.0 if direction[2] > 0 else -1.0)
    rotated = [c * scaled[0] - s * scaled[1], s * scaled[0] + c * scaled[1], scaled[2]]
    return [origin[i] + rotated[i] for i in range(3)]


def direct_transport_pose(side: str, angle_deg: float, contexts=None, *, disable_helper=False):
    """Independent real-arithmetic reference for the emitted static skin/TRS map."""
    contexts = contexts or side_contexts()
    context = contexts[side]
    positions = [source_to_gltf(row) for row in context["specimen"]["positions"]]
    origin = source_to_gltf(context["origin"])
    axis = source_to_gltf(context["axis"])
    joints, weights = _static_skin_rows(side, context)
    correction = correction_transform(angle_deg)
    output = []
    for point, joint_row, weight_row in zip(positions, joints, weights):
        if joint_row[0] == JOINTS[f"{side}_distal"] and weight_row[0] == 1.0:
            output.append(_rotate_about_axis(point, origin, axis, angle_deg))
            continue
        if len([w for w in weight_row if w > 0.0]) == 2:
            helper = point if disable_helper else _rotate_about_axis(
                point, origin, axis, correction["helper_angle_deg"], correction["planar_scale"]
            )
            output.append([
                STATIC_ROOT_WEIGHT * point[i] + STATIC_CORRECTION_WEIGHT * helper[i]
                for i in range(3)
            ])
            continue
        output.append(list(point))
    return output


def direct_decomposition_audit() -> dict[str, Any]:
    contexts = side_contexts()
    maximum = 0.0
    worst = None
    mutation_maximum = 0.0
    for sample_index in range(DENSE_SAMPLE_COUNT):
        time_s = sample_index / DENSE_HZ
        angle = _phase_angle(time_s)
        for side in ("L", "R"):
            expected = [source_to_gltf(row) for row in owner_pose(side, angle, contexts)]
            candidate = direct_transport_pose(side, angle, contexts)
            residual = max(math.dist(a, b) for a, b in zip(expected, candidate))
            if residual > maximum:
                maximum = residual
                worst = {"sample_index": sample_index, "time_s": time_s, "angle_deg": angle, "side": side}
            mutated = direct_transport_pose(side, angle, contexts, disable_helper=True)
            mutation_maximum = max(mutation_maximum, max(math.dist(a, b) for a, b in zip(expected, mutated)))
    return {
        "status": POSITION_STATUS if maximum <= 1e-10 and mutation_maximum > 1e-6 else "HOLD_CHARACTER_REVIEW006_STATIC_SKIN_FACTORIZATION",
        "sample_count": DENSE_SAMPLE_COUNT,
        "side_count": 2,
        "maximum_real_arithmetic_position_residual_m": maximum,
        "worst_sample": worst,
        "disabled_helper_maximum_residual_m": mutation_maximum,
        "disabled_helper_rejected": mutation_maximum > 1e-6,
    }


def direction_frame_reference() -> dict[str, Any]:
    contexts = side_contexts()
    samples = {}
    for sample_index in (0, 80, 240, 320):
        time_s = sample_index / DENSE_HZ
        angle = _phase_angle(time_s)
        key = f"{sample_index:03d}"
        sides = {}
        for side in ("L", "R"):
            context = contexts[side]
            faces = context["specimen"]["faces"]
            neutral = smooth_normals(context["specimen"]["positions"], faces)
            posed_positions = owner_pose(side, angle, contexts)
            posed = smooth_normals(posed_positions, faces)
            maximum_angle = 0.0
            changed = 0
            for first, second in zip(neutral, posed):
                delta = max(abs(first[i] - second[i]) for i in range(3))
                if delta > 1e-12:
                    changed += 1
                maximum_angle = max(maximum_angle, math.degrees(math.acos(max(-1.0, min(1.0, _dot(first, second))))))
            mapped = [[_f32(v) for v in source_to_gltf(row)] for row in posed]
            sides[side] = {
                "vertex_count": len(posed),
                "changed_vertex_count_gt_1e_12_component": changed,
                "maximum_angle_from_neutral_deg": maximum_angle,
                "pose_recomputed_gltf_normal_sha256": canonical_digest(mapped),
                "pose_recomputed_gltf_normals": mapped,
            }
        samples[key] = {"sample_index": sample_index, "time_s": time_s, "angle_deg": angle, "sides": sides}
    return {
        "schema": "axm.character-review006-direction-frame-reference/v0.1",
        "status": DIRECTION_STATUS,
        "method": "AREA_WEIGHTED_INDEXED_VERTEX_SMOOTH_NORMAL",
        "materials_head": MATERIALS_HEAD,
        "materials_tool_blob": MATERIALS_NORMAL_TOOL_BLOB,
        "samples": samples,
        "meaning": "Reference-only owner normals. Current bound UC pose runtime does not evaluate deformed normals/tangents; no direction-frame equivalence is claimed.",
    }


def _pad4(data: bytes, fill=b"\x00") -> bytes:
    return data + fill * ((-len(data)) % 4)


def _translation_matrix(x, y, z):
    # glTF accessor MAT4 is column-major.
    return [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, float(x), float(y), float(z), 1.0]


def pack_character_glb() -> PackedCharacterGlb:
    contexts = side_contexts()
    positions, normals, joint_rows, weight_rows, indices = [], [], [], [], []
    source_vertex_counts, source_triangle_counts = {}, {}
    vertex_offset = 0
    for side in ("L", "R"):
        context = contexts[side]
        specimen = context["specimen"]
        source_positions = specimen["positions"]
        faces = specimen["faces"]
        source_normals = smooth_normals(source_positions, faces)
        side_positions = [[_f32(v) for v in source_to_gltf(row)] for row in source_positions]
        side_normals = [[_f32(v) for v in source_to_gltf(row)] for row in source_normals]
        side_joints, side_weights = _static_skin_rows(side, context)
        positions.extend(side_positions)
        normals.extend(side_normals)
        joint_rows.extend(side_joints)
        weight_rows.extend([[_f32(v) for v in row] for row in side_weights])
        for face in faces:
            indices.extend(vertex_offset + int(index) for index in face)
        source_vertex_counts[side] = len(source_positions)
        source_triangle_counts[side] = len(faces)
        vertex_offset += len(source_positions)

    if len(positions) != 184 or len(indices) != 1080:
        raise ValueError("bounded Character transport expected 184 vertices / 360 triangles")

    times = [_f32(index / DENSE_HZ) for index in range(DENSE_SAMPLE_COUNT)]
    angles = [float(_phase_angle(index / DENSE_HZ)) for index in range(DENSE_SAMPLE_COUNT)]
    if any(times[i] <= times[i - 1] for i in range(1, len(times))):
        raise ValueError("float32 transport times are not strictly increasing")

    source, rig = _validate_dependencies()
    origins = {side: source_to_gltf([float(v) for v in source["landmarks"][rig["rig_method"]["joint_semantics"][side]["landmark"]]]) for side in ("L", "R")}
    axes = {side: source_to_gltf(rig["rig_method"]["joint_semantics"][side]["axis"]) for side in ("L", "R")}

    rotations = {}
    scales = {}
    for side in ("L", "R"):
        rotations[f"{side}_distal"] = [_quat(axes[side], angle) for angle in angles]
        helper_rows, scale_rows = [], []
        for angle in angles:
            correction = correction_transform(angle)
            helper_rows.append(_quat(axes[side], correction["helper_angle_deg"]))
            scale_rows.append([_f32(correction["planar_scale"]), _f32(correction["planar_scale"]), 1.0])
        rotations[f"{side}_release"] = helper_rows
        scales[f"{side}_release"] = scale_rows

    chunks: list[bytes] = []
    views: list[dict[str, Any]] = []
    accessors: list[dict[str, Any]] = []

    def view(data: bytes, target=None):
        offset = sum(len(chunk) for chunk in chunks)
        index = len(views)
        chunks.append(_pad4(data))
        row = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
        if target is not None:
            row["target"] = target
        views.append(row)
        return index

    def accessor(data: bytes, component: int, count: int, kind: str, target=None, minimum=None, maximum=None):
        row = {"bufferView": view(data, target), "componentType": component, "count": count, "type": kind}
        if minimum is not None:
            row["min"] = minimum
        if maximum is not None:
            row["max"] = maximum
        accessors.append(row)
        return len(accessors) - 1

    def floats(rows):
        flat = [float(value) for row in rows for value in (row if isinstance(row, (list, tuple)) else [row])]
        return struct.pack("<" + "f" * len(flat), *flat)

    def ubytes(rows):
        flat = [int(value) for row in rows for value in (row if isinstance(row, (list, tuple)) else [row])]
        return struct.pack("<" + "B" * len(flat), *flat)

    def ushorts(rows):
        flat = [int(value) for row in rows for value in (row if isinstance(row, (list, tuple)) else [row])]
        return struct.pack("<" + "H" * len(flat), *flat)

    pos_min = [min(row[d] for row in positions) for d in range(3)]
    pos_max = [max(row[d] for row in positions) for d in range(3)]
    a_pos = accessor(floats(positions), 5126, len(positions), "VEC3", 34962, pos_min, pos_max)
    a_nrm = accessor(floats(normals), 5126, len(normals), "VEC3", 34962)
    a_jnt = accessor(ubytes(joint_rows), 5121, len(joint_rows), "VEC4", 34962)
    a_wgt = accessor(floats(weight_rows), 5126, len(weight_rows), "VEC4", 34962)
    a_idx = accessor(ushorts(indices), 5123, len(indices), "SCALAR", 34963, [min(indices)], [max(indices)])

    inverse = [_translation_matrix(0, 0, 0)]
    for side in ("L", "L", "R", "R"):
        origin = origins[side]
        inverse.append(_translation_matrix(-origin[0], -origin[1], -origin[2]))
    a_inv = accessor(floats(inverse), 5126, 5, "MAT4")
    a_time = accessor(floats(times), 5126, len(times), "SCALAR", minimum=[times[0]], maximum=[times[-1]])

    output_accessors = {}
    for key in ("L_distal", "L_release", "R_distal", "R_release"):
        output_accessors[f"rotation:{key}"] = accessor(floats(rotations[key]), 5126, len(times), "VEC4")
    for key in ("L_release", "R_release"):
        output_accessors[f"scale:{key}"] = accessor(floats(scales[key]), 5126, len(times), "VEC3")

    binary = b"".join(chunks)
    nodes = [
        {"name": "CharacterReview006Shoulders", "mesh": 0, "skin": 0},
        {"name": "CharacterReview006SkinRoot", "children": [2, 3, 4, 5]},
        {"name": "shoulder-L-distal", "translation": origins["L"]},
        {"name": "shoulder-L-release-transport", "translation": origins["L"]},
        {"name": "shoulder-R-distal", "translation": origins["R"]},
        {"name": "shoulder-R-release-transport", "translation": origins["R"]},
    ]
    samplers, channels = [], []

    def channel(node, path, output):
        sampler_index = len(samplers)
        samplers.append({"input": a_time, "output": output, "interpolation": "LINEAR"})
        channels.append({"sampler": sampler_index, "target": {"node": node, "path": path}})

    channel(2, "rotation", output_accessors["rotation:L_distal"])
    channel(3, "rotation", output_accessors["rotation:L_release"])
    channel(3, "scale", output_accessors["scale:L_release"])
    channel(4, "rotation", output_accessors["rotation:R_distal"])
    channel(5, "rotation", output_accessors["rotation:R_release"])
    channel(5, "scale", output_accessors["scale:R_release"])

    document = {
        "asset": {"version": "2.0", "generator": "AXM Character Technical Art review006 transport v0.1"},
        "scene": 0,
        "scenes": [{"name": "Character review006 bounded transport", "nodes": [0, 1]}],
        "nodes": nodes,
        "meshes": [{"name": "review006_opening_repair_LR", "primitives": [{"attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "JOINTS_0": a_jnt, "WEIGHTS_0": a_wgt}, "indices": a_idx, "mode": 4, "material": 0}]}],
        "materials": [{"name": "neutral_transport_only", "pbrMetallicRoughness": {"baseColorFactor": [0.56, 0.43, 0.36, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.62}}],
        "skins": [{"name": "review006-static-weight-transport", "inverseBindMatrices": a_inv, "skeleton": 1, "joints": [1, 2, 3, 4, 5]}],
        "animations": [{"name": CLIP_ID, "samplers": samplers, "channels": channels}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": views,
        "accessors": accessors,
        "extras": {
            "axmTechnicalArt": {
                "schema": SCHEMA,
                "sourceClipDigest": clip_digest(),
                "dynamicReleaseTransport": "STATIC_1_OVER_8_WEIGHT_PLUS_ANIMATED_HELPER_TRS",
                "directionFrameStatus": DIRECTION_STATUS,
            }
        },
    }
    json_chunk = _pad4(json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = _pad4(binary)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    glb = (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk
        + struct.pack("<I4s", len(bin_chunk), b"BIN\x00") + bin_chunk
    )
    return PackedCharacterGlb(
        bytes=glb,
        document=document,
        times=times,
        angles=angles,
        source_vertex_counts=source_vertex_counts,
        source_triangle_counts=source_triangle_counts,
    )


def glb_sha256() -> str:
    return hashlib.sha256(pack_character_glb().bytes).hexdigest()
