from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from axm_character_design.review006_uc_skin_transport import (
    owner_pose,
    pack_character_glb,
    side_contexts,
    source_to_gltf,
    transport_contract,
)

CONTRACT_PATH = Path("lookdev/character_review006_current_target_shaded_motion_reference_003.json")
SCHEMA = "axm.character-review006-current-target-shaded-motion-reference-payload/v0.3"
RESULT = "READY_CHARACTER_REVIEW006_CURRENT_TARGET_SHADED_MOTION_REFERENCE_RECEIVER"
TECHNICAL_ART_HEAD = "36744749a592e067a119f3349a499d65f25af134"
TECHNICAL_ART_ARTIFACT_ID = 10500419469
TECHNICAL_ART_ARTIFACT_SHA256 = "2c8741ceb1e7bdb0866ad3505dc1ec37ea26f59c420980f480a4a48011e7374a"
TECHNICAL_ART_EXPECTED_RESULT = "PASS_CHARACTER_REVIEW006_GODOT_TARGET_NORMAL_BUFFER_CONSISTENTLY_NEARER_RIGGING_LINEAR_GRADIENT_REFERENCE__INVERSE_TRANSPOSE_SEPARATION_SUB_LSB"
RIGGING_HEAD = "4efa5772ee63f62d7a7e5b4ef6688550034b4659"
UC_HEAD = "41b4d9134e4d2e5f4fadaada2a1d6a56eed92ab0"
EXPECTED_TARGET_GLB_SHA256 = "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
EXPECTED_TARGET_GLB_BYTES = 44032
SAMPLE_TOLERANCE = 1e-4


def canonical_digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_contract(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "axm.character-review006-current-target-shaded-motion-reference-lookdev/v0.3":
        raise ValueError("current-target shaded-motion contract schema drift")
    if data.get("technical_art_direction_frame_head") != TECHNICAL_ART_HEAD:
        raise ValueError("Technical Art direction-frame head drift")
    if int(data.get("technical_art_direction_frame_artifact_id", -1)) != TECHNICAL_ART_ARTIFACT_ID:
        raise ValueError("Technical Art artifact id drift")
    if data.get("technical_art_direction_frame_artifact_sha256") != TECHNICAL_ART_ARTIFACT_SHA256:
        raise ValueError("Technical Art artifact digest drift")
    if data.get("technical_art_expected_result") != TECHNICAL_ART_EXPECTED_RESULT:
        raise ValueError("Technical Art expected-result drift")
    if data.get("technical_art_rigging_head") != RIGGING_HEAD:
        raise ValueError("Rigging head drift")
    if data.get("technical_art_uc_head") != UC_HEAD:
        raise ValueError("UC head drift")
    if data.get("target_glb_sha256") != EXPECTED_TARGET_GLB_SHA256:
        raise ValueError("target GLB digest drift")
    if int(data.get("target_glb_bytes", -1)) != EXPECTED_TARGET_GLB_BYTES:
        raise ValueError("target GLB byte-size drift")

    material = data.get("material", {})
    if material.get("semantic") != "neutral_skin_response_review_only":
        raise ValueError("review material semantic drift")
    if list(material.get("albedo_srgb", [])) != [0.56, 0.43, 0.36]:
        raise ValueError("review albedo drift")
    if float(material.get("metallic", -1.0)) != 0.0:
        raise ValueError("review metallic drift")
    if abs(float(material.get("roughness", -1.0)) - 0.62) > 1e-12:
        raise ValueError("review roughness drift")

    receiver = data.get("receiver", {})
    if receiver.get("actual_imported_target_is_visual_reference") is not True:
        raise ValueError("actual imported target must remain the visual reference")
    for key in (
        "pose_recomputed_is_desired_target",
        "frozen_neutral_is_desired_target",
        "linear_gradient_is_renderer_implementation_claim",
        "inverse_transpose_is_renderer_implementation_claim",
        "source_geometry_changed",
        "source_topology_membership_changed",
        "source_normals_changed",
        "rigging_changed",
        "animation_changed",
        "technical_art_transport_changed",
        "material_scalars_changed",
        "camera_policy_changed",
        "lighting_policy_changed",
        "uc_product_modified",
    ):
        if receiver.get(key) is not False:
            raise ValueError(f"bounded Materials receiver must keep {key}=false")

    truth = data.get("truth_boundary", {})
    if truth.get("lookdev_reference_pack_only") is not True:
        raise ValueError("lookdev reference-pack boundary drift")
    if truth.get("full_body_review_available") is not False:
        raise ValueError("bounded target must not be relabelled as a full-body review")
    for key in (
        "production_skin_material",
        "production_normals_or_tangents",
        "tangent_space_normal_map_correctness",
        "subsurface_or_transmission",
        "arbitrary_pose_or_camera_correctness",
        "runtime_or_target_device_acceptance",
        "final_art_direction_acceptance",
        "independent_visual_qa_acceptance",
        "source_adoption_or_canon",
        "production_readiness",
        "materials_mastery",
    ):
        if truth.get(key) is not False:
            raise ValueError(f"truth boundary must keep {key}=false")
    return data


def bounds_for_angle(angle_deg: float, contexts: dict) -> dict:
    positions = []
    for side in ("L", "R"):
        for value in owner_pose(side, angle_deg, contexts):
            positions.append(source_to_gltf(value))
    if not positions:
        raise ValueError("owner reference produced no positions")
    minimum = [min(float(p[i]) for p in positions) for i in range(3)]
    maximum = [max(float(p[i]) for p in positions) for i in range(3)]
    return {
        "minimum": minimum,
        "maximum": maximum,
        "center": [(minimum[i] + maximum[i]) * 0.5 for i in range(3)],
        "extent": [maximum[i] - minimum[i] for i in range(3)],
        "vertex_count": len(positions),
    }


def build_payload(contract_path: Path, out_dir: Path) -> dict:
    contract = load_contract(contract_path)
    packed = pack_character_glb()
    target_digest = sha256_bytes(packed.bytes)
    if target_digest != EXPECTED_TARGET_GLB_SHA256:
        raise ValueError(f"target GLB digest drift: {target_digest}")
    if len(packed.bytes) != EXPECTED_TARGET_GLB_BYTES:
        raise ValueError(f"target GLB byte-size drift: {len(packed.bytes)}")

    donor_contract = transport_contract()
    clip_id = donor_contract.get("animation", {}).get("clip_id")
    if not clip_id:
        raise ValueError("transport contract is missing animation clip id")

    out_dir.mkdir(parents=True, exist_ok=True)
    glb_path = out_dir / "character-review006-current-target-shaded-motion-reference-target.glb"
    glb_path.write_bytes(packed.bytes)

    contexts = side_contexts()
    samples = {}
    for spec in contract["samples"]:
        index = int(spec["sample_index"])
        if index < 0 or index >= len(packed.times):
            raise ValueError(f"sample index out of bounds: {index}")
        actual_time = float(packed.times[index])
        actual_angle = float(packed.angles[index])
        expected_time = float(spec["expected_time_s"])
        expected_angle = float(spec["expected_angle_deg"])
        if abs(actual_time - expected_time) > SAMPLE_TOLERANCE:
            raise ValueError(f"sample {index} time drift: {actual_time} != {expected_time}")
        if abs(actual_angle - expected_angle) > SAMPLE_TOLERANCE:
            raise ValueError(f"sample {index} angle drift: {actual_angle} != {expected_angle}")
        samples[str(index)] = {
            "sample_index": index,
            "time_s": actual_time,
            "angle_deg": actual_angle,
            "camera_bounds": bounds_for_angle(actual_angle, contexts),
        }

    expected_keys = {"80", "160", "240"}
    if set(samples) != expected_keys:
        raise ValueError(f"sample set drift: {sorted(samples)}")
    for key, row in samples.items():
        if int(row["camera_bounds"]["vertex_count"]) != 184:
            raise ValueError(f"camera-bound vertex count drift at {key}")

    payload = {
        "schema": SCHEMA,
        "result": RESULT,
        "contract": contract,
        "exact_identity": {
            "technical_art_direction_frame_head": TECHNICAL_ART_HEAD,
            "technical_art_direction_frame_artifact_id": TECHNICAL_ART_ARTIFACT_ID,
            "technical_art_direction_frame_artifact_sha256": TECHNICAL_ART_ARTIFACT_SHA256,
            "technical_art_expected_result": TECHNICAL_ART_EXPECTED_RESULT,
            "rigging_head": RIGGING_HEAD,
            "uc_head": UC_HEAD,
            "target_glb_sha256": target_digest,
            "target_glb_bytes": len(packed.bytes),
        },
        "target": {
            "glb_path": "generated/character-review006-current-target-shaded-motion-reference-target.glb",
            "clip_id": clip_id,
            "transport_key_count": len(packed.times),
        },
        "samples": samples,
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
    out = out_dir / "character_review006_current_target_shaded_motion_reference_payload.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": payload["result"],
        "payload_sha256": payload["payload_sha256"],
        "target_glb_sha256": payload["exact_identity"]["target_glb_sha256"],
        "target_glb_bytes": payload["exact_identity"]["target_glb_bytes"],
        "samples": {key: {"time_s": row["time_s"], "angle_deg": row["angle_deg"]} for key, row in payload["samples"].items()},
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
