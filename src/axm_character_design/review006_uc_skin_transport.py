"""Bounded Character review-006 -> Universal Creation skin transport.

Technical Art owns only the transport. Character source/topology/Rigging/
Animation/Materials remain in their owner lanes. The current Rigging profile has
an angle-dependent proximal child weight, while glTF skin weights are static.
For the exact bounded diagnostic clip this module factors that dynamic blend
into a static 1/8 skin weight plus an animated helper-joint TRS. Current UC
GamePoseAsset is then used as an independent position receiver.

UC does not currently evaluate deformed normals/tangents. Neutral normals are
packed only to keep the GLB valid; pose-recomputed Materials-method normals are
retained as a separate reference and remain an explicit HOLD.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .organic_form import canonical_digest
from .review006_connected_geometry import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
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
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
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
STATIC_CORRECTION_WEIGHT = 0.125
STATIC_ROOT_WEIGHT = 0.875
POSITION_TOLERANCE_M = 5e-6
JOINTS = {"root": 0, "L_distal": 1, "L_release": 2, "R_distal": 3, "R_release": 4}


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
    """Proper R_x(-90deg): Character Z-up -> glTF Y-up, no reflection."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("Character vector must contain exactly three components")
    x, y, z = (float(item) for item in value)
    if not all(math.isfinite(item) for item in (x, y, z)):
        raise ValueError("Character vector must be finite")
    return [x, z, -y]


def _sub(a, b):
    return [float(a[i]) - float(b[i]) for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _unit(value, label="vector"):
    size = math.sqrt(_dot(value, value))
    if not math.isfinite(size) or size <= 1e-15:
        raise ValueError(f"{label} must have non-zero finite length")
    return [float(item) / size for item in value]


def smooth_normals(positions, faces):
    """Materials PR #18 method: area-weighted indexed vertex smooth normals."""
    accum = [[0.0, 0.0, 0.0] for _ in positions]
    for face in faces:
        a, b, c = (int(index) for index in face)
        normal = _cross(_sub(positions[b], positions[a]), _sub(positions[c], positions[a]))
        if math.sqrt(_dot(normal, normal)) <= 1e-15:
            raise ValueError("normal receiver contains a degenerate face")
        for index in (a, b, c):
            for dim in range(3):
                accum[index][dim] += normal[dim]
    return [_unit(row, "accumulated smooth normal") for row in accum]


def _quat(axis, angle_deg):
    axis = _unit(axis, "joint axis")
    half = math.radians(float(angle_deg)) / 2.0
    sine = math.sin(half)
    return [_f32(axis[0] * sine), _f32(axis[1] * sine), _f32(axis[2] * sine), _f32(math.cos(half))]


def correction_transform(angle_deg: float) -> dict[str, Any]:
    """Return C where .875*I + .125*C == (1-w)*I + w*R(angle)."""
    theta = math.radians(float(angle_deg))
    weight = float(release_weight(angle_deg))
    k = weight / STATIC_CORRECTION_WEIGHT
    if not 0.0 <= k <= 1.0 + 1e-12:
        raise ValueError("dynamic release exceeds bounded static correction weight")
    a = 1.0 - k + k * math.cos(theta)
    b = k * math.sin(theta)
    return {
        "release_weight": weight,
        "static_correction_weight": STATIC_CORRECTION_WEIGHT,
        "k": k,
        "planar_scale": math.hypot(a, b),
        "helper_angle_deg": math.degrees(math.atan2(b, a)),
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
            "source": "Character Z-up",
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
    if rig["geometry"]["head"] != GEOMETRY_HEAD or rig["rig_method"]["profile_digest"] != EXPECTED_PROFILE_DIGEST:
        raise ValueError("Geometry/Rigging dependency drift")
    anim = animation_contract()
    if anim["rigging"]["exact_parent_head"] != RIGGING_HEAD or anim["clip"]["digest"] != clip_digest():
        raise ValueError("Animation dependency drift")
    return source, rig


@lru_cache(maxsize=1)
def side_contexts():
    source, rig = _validate_dependencies()
    result = {}
    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        digest = canonical_digest({"positions": specimen["positions"], "faces": specimen["faces"]})
        if digest != EXPECTED_TOPOLOGY_DIGESTS[side]:
            raise ValueError(f"{side} topology identity drift")
        joint = rig["rig_method"]["joint_semantics"][side]
        result[side] = {
            "specimen": specimen,
            "layout": _reindexed_layout(side, specimen),
            "origin": [float(v) for v in source["landmarks"][joint["landmark"]]],
            "axis": [float(v) for v in joint["axis"]],
        }
    return result


def owner_pose(side: str, angle_deg: float, contexts=None):
    context = (contexts or side_contexts())[side]
    specimen = context["specimen"]
    return _pose(
        specimen,
        context["origin"],
        context["axis"],
        float(angle_deg),
        _weights(context["layout"], release_weight(angle_deg), len(specimen["positions"])),
    )["positions"]


def _static_skin_rows(side: str, context):
    vertex_count = len(context["specimen"]["positions"])
    groups = {}
    for name, indexes in context["layout"]["groups"].items():
        for index in indexes:
            groups[index] = name
    if sorted(groups) != list(range(vertex_count)):
        raise ValueError(f"{side} static skin grouping does not cover all vertices")
    distal, helper = JOINTS[f"{side}_distal"], JOINTS[f"{side}_release"]
    joints, weights = [], []
    for index in range(vertex_count):
        name = groups[index]
        if name in ("ribcage", "seam"):
            joints.append([0, 0, 0, 0]); weights.append([1.0, 0.0, 0.0, 0.0])
        elif name == "proximal":
            joints.append([0, helper, 0, 0]); weights.append([STATIC_ROOT_WEIGHT, STATIC_CORRECTION_WEIGHT, 0.0, 0.0])
        elif name in ("distal", "distal_cap"):
            joints.append([distal, 0, 0, 0]); weights.append([1.0, 0.0, 0.0, 0.0])
        else:
            raise ValueError(f"unexpected Rigging group {name}")
    return joints, weights


def _transform_about_axis(point, origin, axis, angle_deg, planar_scale=1.0):
    axis = _unit(axis, "transport axis")
    if abs(axis[0]) > 1e-12 or abs(axis[1]) > 1e-12 or abs(abs(axis[2]) - 1.0) > 1e-12:
        raise ValueError("bounded mapped shoulder axis must be +/-Z")
    local = _sub(point, origin)
    x, y, z = local[0] * planar_scale, local[1] * planar_scale, local[2]
    angle = math.radians(float(angle_deg)) * (1.0 if axis[2] > 0 else -1.0)
    c, s = math.cos(angle), math.sin(angle)
    return [origin[0] + c * x - s * y, origin[1] + s * x + c * y, origin[2] + z]


def direct_transport_pose(side: str, angle_deg: float, contexts=None, *, disable_helper=False):
    contexts = contexts or side_contexts()
    context = contexts[side]
    positions = [source_to_gltf(row) for row in context["specimen"]["positions"]]
    origin, axis = source_to_gltf(context["origin"]), source_to_gltf(context["axis"])
    joints, weights = _static_skin_rows(side, context)
    correction = correction_transform(angle_deg)
    result = []
    for point, joint_row, weight_row in zip(positions, joints, weights):
        if joint_row[0] == JOINTS[f"{side}_distal"] and weight_row[0] == 1.0:
            result.append(_transform_about_axis(point, origin, axis, angle_deg)); continue
        if sum(w > 0.0 for w in weight_row) == 2:
            helper = point if disable_helper else _transform_about_axis(
                point, origin, axis, correction["helper_angle_deg"], correction["planar_scale"]
            )
            result.append([STATIC_ROOT_WEIGHT * point[i] + STATIC_CORRECTION_WEIGHT * helper[i] for i in range(3)]); continue
        result.append(list(point))
    return result


def direct_decomposition_audit() -> dict[str, Any]:
    contexts = side_contexts()
    maximum, mutation_maximum, worst = 0.0, 0.0, None
    for index in range(DENSE_SAMPLE_COUNT):
        time_s, angle = index / DENSE_HZ, _phase_angle(index / DENSE_HZ)
        for side in ("L", "R"):
            expected = [source_to_gltf(row) for row in owner_pose(side, angle, contexts)]
            actual = direct_transport_pose(side, angle, contexts)
            residual = max(math.dist(a, b) for a, b in zip(expected, actual))
            if residual > maximum:
                maximum, worst = residual, {"sample_index": index, "time_s": time_s, "angle_deg": angle, "side": side}
            mutated = direct_transport_pose(side, angle, contexts, disable_helper=True)
            mutation_maximum = max(mutation_maximum, max(math.dist(a, b) for a, b in zip(expected, mutated)))
    status = POSITION_STATUS if maximum <= 1e-10 and mutation_maximum > 1e-6 else "HOLD_CHARACTER_REVIEW006_STATIC_SKIN_FACTORIZATION"
    return {
        "status": status,
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
    for index in (0, 80, 240, 320):
        time_s, angle = index / DENSE_HZ, _phase_angle(index / DENSE_HZ)
        side_rows = {}
        for side in ("L", "R"):
            context = contexts[side]; faces = context["specimen"]["faces"]
            neutral = smooth_normals(context["specimen"]["positions"], faces)
            posed = smooth_normals(owner_pose(side, angle, contexts), faces)
            changed, maximum_angle = 0, 0.0
            for first, second in zip(neutral, posed):
                if max(abs(first[d] - second[d]) for d in range(3)) > 1e-12:
                    changed += 1
                maximum_angle = max(maximum_angle, math.degrees(math.acos(max(-1.0, min(1.0, _dot(first, second))))))
            mapped = [[_f32(v) for v in source_to_gltf(row)] for row in posed]
            side_rows[side] = {
                "vertex_count": len(posed),
                "changed_vertex_count_gt_1e_12_component": changed,
                "maximum_angle_from_neutral_deg": maximum_angle,
                "pose_recomputed_gltf_normal_sha256": canonical_digest(mapped),
                "pose_recomputed_gltf_normals": mapped,
            }
        samples[f"{index:03d}"] = {"sample_index": index, "time_s": time_s, "angle_deg": angle, "sides": side_rows}
    return {
        "schema": "axm.character-review006-direction-frame-reference/v0.1",
        "status": DIRECTION_STATUS,
        "method": "AREA_WEIGHTED_INDEXED_VERTEX_SMOOTH_NORMAL",
        "materials_head": MATERIALS_HEAD,
        "materials_tool_blob": MATERIALS_NORMAL_TOOL_BLOB,
        "samples": samples,
        "meaning": "Reference only: current bound UC pose runtime does not evaluate deformed normals/tangents.",
    }


def _pad4(data: bytes, fill=b"\x00") -> bytes:
    return data + fill * ((-len(data)) % 4)


def _translation_matrix(x, y, z):
    return [1.0,0.0,0.0,0.0, 0.0,1.0,0.0,0.0, 0.0,0.0,1.0,0.0, float(x),float(y),float(z),1.0]


def pack_character_glb() -> PackedCharacterGlb:
    contexts = side_contexts()
    positions, normals, joint_rows, weight_rows, indices = [], [], [], [], []
    vertex_counts, triangle_counts, offset = {}, {}, 0
    for side in ("L", "R"):
        context = contexts[side]; specimen = context["specimen"]; faces = specimen["faces"]
        positions.extend([[_f32(v) for v in source_to_gltf(row)] for row in specimen["positions"]])
        normals.extend([[_f32(v) for v in source_to_gltf(row)] for row in smooth_normals(specimen["positions"], faces)])
        sj, sw = _static_skin_rows(side, context); joint_rows.extend(sj); weight_rows.extend([[_f32(v) for v in row] for row in sw])
        for face in faces: indices.extend(offset + int(i) for i in face)
        vertex_counts[side], triangle_counts[side] = len(specimen["positions"]), len(faces); offset += len(specimen["positions"])
    if len(positions) != 184 or len(indices) != 1080:
        raise ValueError("bounded Character transport expected 184 vertices / 360 triangles")

    times = [_f32(index / DENSE_HZ) for index in range(DENSE_SAMPLE_COUNT)]
    angles = [float(_phase_angle(index / DENSE_HZ)) for index in range(DENSE_SAMPLE_COUNT)]
    if any(times[i] <= times[i-1] for i in range(1, len(times))):
        raise ValueError("float32 transport times must be strictly increasing")
    source, rig = _validate_dependencies()
    origins = {}; axes = {}
    for side in ("L", "R"):
        joint = rig["rig_method"]["joint_semantics"][side]
        origins[side] = source_to_gltf(source["landmarks"][joint["landmark"]]); axes[side] = source_to_gltf(joint["axis"])

    rotations, scales = {}, {}
    for side in ("L", "R"):
        rotations[f"{side}_distal"] = [_quat(axes[side], angle) for angle in angles]
        rotations[f"{side}_release"] = [] ; scales[f"{side}_release"] = []
        for angle in angles:
            correction = correction_transform(angle)
            rotations[f"{side}_release"].append(_quat(axes[side], correction["helper_angle_deg"]))
            scale = _f32(correction["planar_scale"]); scales[f"{side}_release"].append([scale, scale, 1.0])

    chunks, views, accessors = [], [], []
    def view(data, target=None):
        index, offset_bytes = len(views), sum(len(chunk) for chunk in chunks); chunks.append(_pad4(data))
        row = {"buffer": 0, "byteOffset": offset_bytes, "byteLength": len(data)}
        if target is not None: row["target"] = target
        views.append(row); return index
    def accessor(data, component, count, kind, target=None, minimum=None, maximum=None):
        row = {"bufferView": view(data, target), "componentType": component, "count": count, "type": kind}
        if minimum is not None: row["min"] = minimum
        if maximum is not None: row["max"] = maximum
        accessors.append(row); return len(accessors)-1
    def floats(rows):
        flat = [float(v) for row in rows for v in (row if isinstance(row,(list,tuple)) else [row])]
        return struct.pack("<" + "f"*len(flat), *flat)
    def ubytes(rows):
        flat = [int(v) for row in rows for v in (row if isinstance(row,(list,tuple)) else [row])]
        return struct.pack("<" + "B"*len(flat), *flat)
    def ushorts(rows):
        flat = [int(v) for row in rows for v in (row if isinstance(row,(list,tuple)) else [row])]
        return struct.pack("<" + "H"*len(flat), *flat)

    pmin = [min(row[d] for row in positions) for d in range(3)]; pmax = [max(row[d] for row in positions) for d in range(3)]
    a_pos = accessor(floats(positions),5126,184,"VEC3",34962,pmin,pmax); a_nrm = accessor(floats(normals),5126,184,"VEC3",34962)
    a_jnt = accessor(ubytes(joint_rows),5121,184,"VEC4",34962); a_wgt = accessor(floats(weight_rows),5126,184,"VEC4",34962)
    a_idx = accessor(ushorts(indices),5123,len(indices),"SCALAR",34963,[min(indices)],[max(indices)])
    inverse = [_translation_matrix(0,0,0)] + [_translation_matrix(*[-v for v in origins[side]]) for side in ("L","L","R","R")]
    a_inv = accessor(floats(inverse),5126,5,"MAT4"); a_time = accessor(floats(times),5126,len(times),"SCALAR",minimum=[times[0]],maximum=[times[-1]])
    outputs = {}
    for key in ("L_distal","L_release","R_distal","R_release"): outputs[f"rotation:{key}"] = accessor(floats(rotations[key]),5126,len(times),"VEC4")
    for key in ("L_release","R_release"): outputs[f"scale:{key}"] = accessor(floats(scales[key]),5126,len(times),"VEC3")
    binary = b"".join(chunks)

    nodes = [
        {"name":"CharacterReview006Shoulders","mesh":0,"skin":0},
        {"name":"CharacterReview006SkinRoot","children":[2,3,4,5]},
        {"name":"shoulder-L-distal","translation":origins["L"]}, {"name":"shoulder-L-release-transport","translation":origins["L"]},
        {"name":"shoulder-R-distal","translation":origins["R"]}, {"name":"shoulder-R-release-transport","translation":origins["R"]},
    ]
    samplers, channels = [], []
    def add_channel(node, path, output):
        index = len(samplers); samplers.append({"input":a_time,"output":output,"interpolation":"LINEAR"}); channels.append({"sampler":index,"target":{"node":node,"path":path}})
    add_channel(2,"rotation",outputs["rotation:L_distal"]); add_channel(3,"rotation",outputs["rotation:L_release"]); add_channel(3,"scale",outputs["scale:L_release"])
    add_channel(4,"rotation",outputs["rotation:R_distal"]); add_channel(5,"rotation",outputs["rotation:R_release"]); add_channel(5,"scale",outputs["scale:R_release"])
    document = {
        "asset":{"version":"2.0","generator":"AXM Character Technical Art review006 transport v0.1"},
        "scene":0,"scenes":[{"name":"Character review006 bounded transport","nodes":[0,1]}],"nodes":nodes,
        "meshes":[{"name":"review006_opening_repair_LR","primitives":[{"attributes":{"POSITION":a_pos,"NORMAL":a_nrm,"JOINTS_0":a_jnt,"WEIGHTS_0":a_wgt},"indices":a_idx,"mode":4,"material":0}]}],
        "materials":[{"name":"neutral_transport_only","pbrMetallicRoughness":{"baseColorFactor":[0.56,0.43,0.36,1.0],"metallicFactor":0.0,"roughnessFactor":0.62}}],
        "skins":[{"name":"review006-static-weight-transport","inverseBindMatrices":a_inv,"skeleton":1,"joints":[1,2,3,4,5]}],
        "animations":[{"name":CLIP_ID,"samplers":samplers,"channels":channels}],"buffers":[{"byteLength":len(binary)}],"bufferViews":views,"accessors":accessors,
        "extras":{"axmTechnicalArt":{"schema":SCHEMA,"sourceClipDigest":clip_digest(),"dynamicReleaseTransport":"STATIC_1_OVER_8_WEIGHT_PLUS_ANIMATED_HELPER_TRS","directionFrameStatus":DIRECTION_STATUS}},
    }
    json_chunk = _pad4(json.dumps(document,sort_keys=True,separators=(",",":")).encode(),b" "); bin_chunk = _pad4(binary)
    total = 12+8+len(json_chunk)+8+len(bin_chunk)
    glb = struct.pack("<4sII",b"glTF",2,total)+struct.pack("<I4s",len(json_chunk),b"JSON")+json_chunk+struct.pack("<I4s",len(bin_chunk),b"BIN\x00")+bin_chunk
    return PackedCharacterGlb(glb,document,times,angles,vertex_counts,triangle_counts)


def glb_sha256() -> str:
    return hashlib.sha256(pack_character_glb().bytes).hexdigest()
