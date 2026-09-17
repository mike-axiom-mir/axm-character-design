from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from axm_character_design.review006_uc_skin_transport import (
    ANIMATION_HEAD,
    MATERIALS_HEAD,
    MATERIALS_NORMAL_TOOL_BLOB,
    owner_pose,
    pack_character_glb,
    side_contexts,
    smooth_normals,
    source_to_gltf,
    transport_contract,
)

CONTRACT_PATH = Path("lookdev/character_review006_current_motion_host_equivalent_direction_frame_review_002.json")
SCHEMA = "axm.character-review006-current-motion-host-equivalent-direction-frame-payload/v0.2"
RESULT = "READY_CHARACTER_REVIEW006_CURRENT_MOTION_HOST_EQUIVALENT_DIRECTION_FRAME_RECEIVER"
TECHNICAL_ART_BRIDGE_HEAD = "a61f96d2cf8c33b153d17810ad18ca48074b81d2"
TECHNICAL_ART_BRIDGE_HELPER_BLOB = "c66d09f74cb6ff81c864e60dfbe6159c6f0c1455"
TECHNICAL_ART_PRODUCER_BLOB = "831fd7522ec2a8783862da653d6f12465252a3b2"
EXPECTED_TARGET_GLB_SHA256 = "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
EXPECTED_TARGET_GLB_BYTES = 44032
RIGGING_MOTION_SOURCE_HEAD = "fa16c44b1a488d43842470fc9f30c5fb5e98cab6"
RIGGING_NEUTRAL_ORACLE_HEAD = "675a6800271f9be563763026e3b196607a0a1cd3"
STATIC_REFERENCE_HEAD = "e450684b398f8e5b0e23c4cbf717e3475dd4d5ee"
SAMPLE_TOLERANCE = 1e-4


def canonical_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def reverse_faces(faces: list[list[int]]) -> list[list[int]]:
    return [[int(face[0]), int(face[2]), int(face[1])] for face in faces]


def load_contract(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "axm.character-review006-current-motion-host-equivalent-direction-frame-lookdev/v0.2":
        raise ValueError("host-equivalent direction-frame contract schema drift")
    if data.get("technical_art_bridge_head") != TECHNICAL_ART_BRIDGE_HEAD:
        raise ValueError("Technical Art bridge head drift")
    if data.get("technical_art_bridge_helper_blob") != TECHNICAL_ART_BRIDGE_HELPER_BLOB:
        raise ValueError("Technical Art bridge helper blob drift")
    if data.get("technical_art_producer_blob") != TECHNICAL_ART_PRODUCER_BLOB:
        raise ValueError("Technical Art producer blob drift")
    if data.get("technical_art_target_glb_sha256") != EXPECTED_TARGET_GLB_SHA256:
        raise ValueError("Technical Art target GLB digest drift")
    if int(data.get("technical_art_target_glb_bytes", -1)) != EXPECTED_TARGET_GLB_BYTES:
        raise ValueError("Technical Art target GLB byte-size drift")
    if data.get("animation_head") != ANIMATION_HEAD:
        raise ValueError("Animation head drift")
    if data.get("rigging_motion_source_head") != RIGGING_MOTION_SOURCE_HEAD:
        raise ValueError("Rigging motion-source head drift")
    if data.get("rigging_neutral_oracle_head") != RIGGING_NEUTRAL_ORACLE_HEAD:
        raise ValueError("Rigging neutral-oracle head drift")
    if data.get("materials_static_reference_head") != STATIC_REFERENCE_HEAD or MATERIALS_HEAD != STATIC_REFERENCE_HEAD:
        raise ValueError("Materials static-reference head drift")
    if data.get("materials_normal_tool_blob") != MATERIALS_NORMAL_TOOL_BLOB:
        raise ValueError("Materials normal-method blob drift")
    receiver = data.get("receiver", {})
    if receiver.get("host_equivalent_relation") != "per triangle [a,b,c] -> [a,c,b] for this exact pinned Godot receiver only":
        raise ValueError("host-equivalent receiver relation drift")
    if receiver.get("universal_godot_rule") is not False:
        raise ValueError("receiver relation must remain receiver-local")
    for key in (
        "source_geometry_changed",
        "source_topology_membership_changed",
        "source_normals_changed",
        "rigging_changed",
        "animation_changed",
        "technical_art_transport_changed",
        "material_scalars_changed",
        "uc_product_modified",
    ):
        if receiver.get(key) is not False:
            raise ValueError(f"Materials receiver must keep {key}=false")
    material = data.get("material", {})
    if material.get("semantic") != "neutral_skin_response_review_only":
        raise ValueError("review material semantic drift")
    if list(material.get("albedo_srgb", [])) != [0.56, 0.43, 0.36]:
        raise ValueError("review albedo drift")
    if float(material.get("metallic", -1.0)) != 0.0 or abs(float(material.get("roughness", -1.0)) - 0.62) > 1e-12:
        raise ValueError("review material scalar drift")
    classification = data.get("classification", {})
    if abs(float(classification.get("neutral_adapted_max_mean_abs_rgb_channel_delta", -1.0)) - 0.002) > 1e-12:
        raise ValueError("neutral host-equivalent comparison bound drift")
    if abs(float(classification.get("position_control_max_frame_xor_fraction", -1.0)) - 0.0005) > 1e-12:
        raise ValueError("position-control bound drift")
    return data


def _combined_reference(angle_deg: float, contexts, neutral_normals_by_side) -> dict:
    positions: list[list[float]] = []
    pose_normals: list[list[float]] = []
    frozen_normals: list[list[float]] = []
    owner_faces: list[list[int]] = []
    offset = 0
    side_counts = {}
    for side in ("L", "R"):
        context = contexts[side]
        specimen = context["specimen"]
        source_positions = owner_pose(side, angle_deg, contexts)
        source_pose_normals = smooth_normals(source_positions, specimen["faces"])
        side_counts[side] = {
            "vertices": len(source_positions),
            "triangles": len(specimen["faces"]),
        }
        positions.extend(source_to_gltf(v) for v in source_positions)
        pose_normals.extend(source_to_gltf(n) for n in source_pose_normals)
        frozen_normals.extend(source_to_gltf(n) for n in neutral_normals_by_side[side])
        for face in specimen["faces"]:
            owner_faces.append([int(face[0]) + offset, int(face[1]) + offset, int(face[2]) + offset])
        offset += len(source_positions)
    return {
        "positions": positions,
        "pose_recomputed_normals": pose_normals,
        "frozen_neutral_normals": frozen_normals,
        "owner_faces": owner_faces,
        "receiver_winding_faces": reverse_faces(owner_faces),
        "counts": {
            "vertices": len(positions),
            "triangles": len(owner_faces),
            "indices": len(owner_faces) * 3,
            "by_side": side_counts,
        },
    }


def build_payload(contract_path: Path, out_dir: Path) -> dict:
    contract = load_contract(contract_path)
    donor_contract = transport_contract()
    if donor_contract.get("animation", {}).get("exact_parent_head") not in (None, ANIMATION_HEAD):
        raise ValueError("Technical Art animation lineage drift")
    if donor_contract.get("materials_reference", {}).get("head") not in (None, STATIC_REFERENCE_HEAD):
        raise ValueError("Technical Art Materials-reference lineage drift")

    packed = pack_character_glb()
    if len(packed.times) != len(packed.angles):
        raise ValueError("transport time/angle sample-count mismatch")
    target_digest = sha256_bytes(packed.bytes)
    if target_digest != EXPECTED_TARGET_GLB_SHA256:
        raise ValueError(f"target GLB digest drift: {target_digest}")
    if len(packed.bytes) != EXPECTED_TARGET_GLB_BYTES:
        raise ValueError(f"target GLB byte-size drift: {len(packed.bytes)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    glb_path = out_dir / "character-review006-current-motion-host-equivalent-target.glb"
    glb_path.write_bytes(packed.bytes)

    contexts = side_contexts()
    neutral_normals_by_side = {}
    for side in ("L", "R"):
        neutral_positions = owner_pose(side, 0.0, contexts)
        neutral_normals_by_side[side] = smooth_normals(neutral_positions, contexts[side]["specimen"]["faces"])

    samples = {}
    for spec in contract["samples"]:
        index = int(spec["sample_index"])
        if index < 0 or index >= len(packed.times):
            raise ValueError(f"sample index out of bounds: {index}")
        time_s = float(packed.times[index])
        angle_deg = float(packed.angles[index])
        expected_time = float(spec["expected_time_s"])
        expected_angle = float(spec["expected_angle_deg"])
        if abs(time_s - expected_time) > SAMPLE_TOLERANCE:
            raise ValueError(f"sample {index} time drift: {time_s} != {expected_time}")
        if abs(angle_deg - expected_angle) > SAMPLE_TOLERANCE:
            raise ValueError(f"sample {index} angle drift: {angle_deg} != {expected_angle}")
        samples[str(index)] = {
            "sample_index": index,
            "time_s": time_s,
            "angle_deg": angle_deg,
            "reference": _combined_reference(angle_deg, contexts, neutral_normals_by_side),
        }

    neutral = samples["160"]["reference"]
    max_neutral_delta = 0.0
    for a, b in zip(neutral["pose_recomputed_normals"], neutral["frozen_neutral_normals"]):
        max_neutral_delta = max(max_neutral_delta, max(abs(float(a[i]) - float(b[i])) for i in range(3)))
    if max_neutral_delta != 0.0:
        raise ValueError("neutral recomputed/frozen normal identity is not exact")
    if neutral["counts"] != {"vertices": 184, "triangles": 360, "indices": 1080, "by_side": {"L": {"vertices": 92, "triangles": 180}, "R": {"vertices": 92, "triangles": 180}}}:
        raise ValueError(f"receiver count drift: {neutral['counts']}")

    changed_counts = {}
    for key in ("80", "240"):
        row = samples[key]["reference"]
        changed = 0
        max_component = 0.0
        for frozen, posed in zip(row["frozen_neutral_normals"], row["pose_recomputed_normals"]):
            delta = max(abs(float(frozen[i]) - float(posed[i])) for i in range(3))
            max_component = max(max_component, delta)
            if delta > 1e-12:
                changed += 1
        if changed <= 0:
            raise ValueError(f"deformed sample {key} does not change pose-following normals")
        changed_counts[key] = {"changed_vertices": changed, "maximum_component_delta": max_component}

    payload = {
        "schema": SCHEMA,
        "result": RESULT,
        "contract": contract,
        "exact_identity": {
            "technical_art_bridge_head": TECHNICAL_ART_BRIDGE_HEAD,
            "technical_art_bridge_helper_blob": TECHNICAL_ART_BRIDGE_HELPER_BLOB,
            "technical_art_producer_blob": TECHNICAL_ART_PRODUCER_BLOB,
            "animation_head": ANIMATION_HEAD,
            "rigging_motion_source_head": RIGGING_MOTION_SOURCE_HEAD,
            "rigging_neutral_oracle_head": RIGGING_NEUTRAL_ORACLE_HEAD,
            "materials_static_reference_head": STATIC_REFERENCE_HEAD,
            "materials_normal_tool_blob": MATERIALS_NORMAL_TOOL_BLOB,
            "target_glb_sha256": target_digest,
            "target_glb_bytes": len(packed.bytes),
        },
        "target": {
            "glb_path": "generated/character-review006-current-motion-host-equivalent-target.glb",
            "clip_id": donor_contract["animation"]["clip_id"],
            "transport_key_count": len(packed.times),
        },
        "samples": samples,
        "normal_change_audit": changed_counts,
        "truth_boundary": contract["truth_boundary"],
    }
    payload["payload_sha256"] = canonical_digest(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(CONTRACT_PATH))
    parser.add_argument("--out-dir", default="lookdev-proof/generated")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    payload = build_payload(Path(args.contract), out_dir)
    out = out_dir / "character_review006_current_motion_host_equivalent_direction_frame_payload.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": payload["result"],
        "payload_sha256": payload["payload_sha256"],
        "target_glb_sha256": payload["exact_identity"]["target_glb_sha256"],
        "target_glb_bytes": payload["exact_identity"]["target_glb_bytes"],
        "normal_change_audit": payload["normal_change_audit"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
