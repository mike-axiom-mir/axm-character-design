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

CONTRACT_PATH = Path("lookdev/character_review006_neutral_target_host_isolation_001.json")
SCHEMA = "axm.character-review006-neutral-target-host-isolation-payload/v0.1"
RESULT = "PASS_CHARACTER_REVIEW006_NEUTRAL_TARGET_HOST_ISOLATION_PAYLOAD"

CURRENT_TECHNICAL_ART_HEAD = "c007c327f2613989581192602338435b67b748d7"
CURRENT_TECHNICAL_ART_PRODUCER_BLOB = "831fd7522ec2a8783862da653d6f12465252a3b2"
TARGET_GLB_SHA256 = "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
TARGET_GLB_BYTES = 44032
CURRENT_RIGGING_ORACLE_HEAD = "a218b2cf2727482a78db8ab21afcf1bb72637bcc"
STATIC_MATERIALS_HEAD = "e450684b398f8e5b0e23c4cbf717e3475dd4d5ee"
CURRENT_MOTION_MATERIALS_HEAD = "c2ae66c75abac064b679f1597b7544d058dc3ad1"
EXPECTED_ANIMATION_HEAD = "9519be55581c009fd800d175677d9b50ee6926e6"
EXPECTED_MATERIALS_NORMAL_TOOL_BLOB = "843c0e1866172dd8b6c5ab0f23d69d1e469562f7"


def canonical_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_contract(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "axm.character-review006-neutral-target-host-isolation-lookdev/v0.1":
        raise ValueError("neutral target-host isolation contract schema drift")
    exact = (
        ("technical_art_current_head", CURRENT_TECHNICAL_ART_HEAD),
        ("technical_art_producer_blob", CURRENT_TECHNICAL_ART_PRODUCER_BLOB),
        ("technical_art_target_glb_sha256", TARGET_GLB_SHA256),
        ("rigging_owner_head", CURRENT_RIGGING_ORACLE_HEAD),
        ("materials_static_reference_head", STATIC_MATERIALS_HEAD),
        ("materials_current_motion_reference_head", CURRENT_MOTION_MATERIALS_HEAD),
    )
    for key, expected in exact:
        if data.get(key) != expected:
            raise ValueError(f"{key} drift")
    if int(data.get("technical_art_target_glb_bytes", -1)) != TARGET_GLB_BYTES:
        raise ValueError("technical_art_target_glb_bytes drift")
    neutral = data.get("neutral_sample", {})
    if int(neutral.get("sample_index", -1)) != 160:
        raise ValueError("neutral sample-index drift")
    if float(neutral.get("expected_time_s", -1.0)) != 1.0 or float(neutral.get("expected_angle_deg", 999.0)) != 0.0:
        raise ValueError("neutral sample value drift")
    material = data.get("material", {})
    if material.get("semantic") != "neutral_skin_response_review_only":
        raise ValueError("review material semantic drift")
    if list(material.get("albedo_srgb", [])) != [0.56, 0.43, 0.36]:
        raise ValueError("review albedo drift")
    if float(material.get("metallic", -1.0)) != 0.0 or float(material.get("roughness", -1.0)) != 0.62:
        raise ValueError("review material scalar drift")
    receiver = data.get("receiver", {})
    for key in (
        "source_geometry_changed",
        "rigging_changed",
        "animation_changed",
        "material_scalars_changed",
        "technical_art_transport_changed",
    ):
        if receiver.get(key) is not False:
            raise ValueError(f"receiver ownership drift: {key}")
    return data


def combined_neutral_reference() -> dict:
    contexts = side_contexts()
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    faces: list[list[int]] = []
    offset = 0
    side_counts = {}
    for side in ("L", "R"):
        context = contexts[side]
        specimen = context["specimen"]
        source_positions = owner_pose(side, 0.0, contexts)
        source_normals = smooth_normals(source_positions, specimen["faces"])
        side_counts[side] = {
            "vertices": len(source_positions),
            "triangles": len(specimen["faces"]),
        }
        positions.extend(source_to_gltf(v) for v in source_positions)
        normals.extend(source_to_gltf(n) for n in source_normals)
        for face in specimen["faces"]:
            faces.append([int(face[0]) + offset, int(face[1]) + offset, int(face[2]) + offset])
        offset += len(source_positions)
    return {
        "positions": positions,
        "pose_recomputed_normals": normals,
        "faces": faces,
        "counts": {
            "vertices": len(positions),
            "triangles": len(faces),
            "by_side": side_counts,
        },
    }


def build_payload(contract_path: Path, out_dir: Path) -> dict:
    contract = load_contract(contract_path)
    if ANIMATION_HEAD != EXPECTED_ANIMATION_HEAD:
        raise ValueError("current Technical Art producer Animation identity drift")
    if MATERIALS_HEAD != STATIC_MATERIALS_HEAD:
        raise ValueError("current Technical Art producer Materials reference drift")
    if MATERIALS_NORMAL_TOOL_BLOB != EXPECTED_MATERIALS_NORMAL_TOOL_BLOB:
        raise ValueError("current Technical Art producer Materials normal-method blob drift")

    donor_contract = transport_contract()
    if donor_contract.get("materials_reference", {}).get("head") not in (None, STATIC_MATERIALS_HEAD):
        raise ValueError("current Technical Art donor Materials lineage drift")

    packed = pack_character_glb()
    actual_sha = sha256_bytes(packed.bytes)
    if actual_sha != TARGET_GLB_SHA256:
        raise ValueError(f"current Technical Art target GLB digest drift: {actual_sha}")
    if len(packed.bytes) != TARGET_GLB_BYTES:
        raise ValueError(f"current Technical Art target GLB byte-size drift: {len(packed.bytes)}")
    sample_index = 160
    if sample_index >= len(packed.times):
        raise ValueError("neutral sample out of bounds")
    if abs(float(packed.times[sample_index]) - 1.0) > 1e-12:
        raise ValueError("neutral target time drift")
    if abs(float(packed.angles[sample_index])) > 1e-12:
        raise ValueError("neutral target angle drift")

    reference = combined_neutral_reference()
    if int(reference["counts"]["vertices"]) != 184:
        raise ValueError("neutral reference vertex-count drift")

    out_dir.mkdir(parents=True, exist_ok=True)
    glb_path = out_dir / "character-review006-neutral-target-host-target.glb"
    glb_path.write_bytes(packed.bytes)

    payload = {
        "schema": SCHEMA,
        "result": RESULT,
        "contract": contract,
        "exact_identity": {
            "technical_art_current_head": CURRENT_TECHNICAL_ART_HEAD,
            "technical_art_producer_blob": CURRENT_TECHNICAL_ART_PRODUCER_BLOB,
            "target_glb_sha256": actual_sha,
            "target_glb_bytes": len(packed.bytes),
            "rigging_owner_oracle_head": CURRENT_RIGGING_ORACLE_HEAD,
            "animation_head": ANIMATION_HEAD,
            "materials_static_reference_head": STATIC_MATERIALS_HEAD,
            "materials_normal_tool_blob": MATERIALS_NORMAL_TOOL_BLOB,
            "materials_current_motion_reference_head": CURRENT_MOTION_MATERIALS_HEAD,
        },
        "target": {
            "glb_path": "generated/character-review006-neutral-target-host-target.glb",
            "clip_id": donor_contract["animation"]["clip_id"],
        },
        "neutral_sample": {
            "sample_index": 160,
            "time_s": float(packed.times[sample_index]),
            "angle_deg": float(packed.angles[sample_index]),
            "reference": reference,
        },
        "truth_boundary": contract["truth_boundary"],
    }
    payload["payload_sha256"] = canonical_digest(payload)
    out = out_dir / "character_review006_neutral_target_host_isolation_payload.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(CONTRACT_PATH))
    parser.add_argument("--out-dir", default="lookdev-proof/generated")
    args = parser.parse_args()
    payload = build_payload(Path(args.contract), Path(args.out_dir))
    print(json.dumps({
        "result": payload["result"],
        "payload_sha256": payload["payload_sha256"],
        "target_glb_sha256": payload["exact_identity"]["target_glb_sha256"],
        "neutral_vertices": payload["neutral_sample"]["reference"]["counts"]["vertices"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
