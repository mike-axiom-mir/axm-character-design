from __future__ import annotations

import argparse
import hashlib
import json
import math
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

CONTRACT_PATH = Path("lookdev/character_review006_current_motion_direction_frame_review_001.json")
SCHEMA = "axm.character-review006-current-motion-direction-frame-payload/v0.1"
RESULT = "PASS_CHARACTER_REVIEW006_CURRENT_MOTION_DIRECTION_FRAME_EVIDENCE_PAYLOAD"
TECHNICAL_ART_HEAD = "1c021d40d7d606f6fb2a29e69f9353640aa33f60"
RIGGING_HEAD = "fa16c44b1a488d43842470fc9f30c5fb5e98cab6"
STATIC_REFERENCE_HEAD = "e450684b398f8e5b0e23c4cbf717e3475dd4d5ee"
SAMPLE_TOLERANCE = 1e-4


def canonical_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_contract(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "axm.character-review006-current-motion-direction-frame-lookdev/v0.1":
        raise ValueError("current-motion direction-frame contract schema drift")
    if data.get("technical_art_head") != TECHNICAL_ART_HEAD:
        raise ValueError("Technical Art head drift")
    if data.get("animation_head") != ANIMATION_HEAD:
        raise ValueError("Animation head drift")
    if data.get("rigging_head") != RIGGING_HEAD:
        raise ValueError("Rigging head drift")
    if data.get("materials_static_reference_head") != STATIC_REFERENCE_HEAD or MATERIALS_HEAD != STATIC_REFERENCE_HEAD:
        raise ValueError("Materials static-reference head drift")
    if data.get("materials_normal_tool_blob") != MATERIALS_NORMAL_TOOL_BLOB:
        raise ValueError("Materials normal-method blob drift")
    material = data.get("material", {})
    if material.get("semantic") != "neutral_skin_response_review_only":
        raise ValueError("review material semantic drift")
    if list(material.get("albedo_srgb", [])) != [0.56, 0.43, 0.36]:
        raise ValueError("review albedo drift")
    if float(material.get("metallic", -1.0)) != 0.0 or abs(float(material.get("roughness", -1.0)) - 0.62) > 1e-12:
        raise ValueError("review material scalar drift")
    if data.get("receiver", {}).get("source_geometry_changed") is not False:
        raise ValueError("Materials receiver must not rewrite source geometry")
    if data.get("receiver", {}).get("rigging_changed") is not False or data.get("receiver", {}).get("animation_changed") is not False:
        raise ValueError("Materials receiver must not rewrite Rigging or Animation")
    return data


def _combined_reference(angle_deg: float, contexts, neutral_normals_by_side) -> dict:
    positions: list[list[float]] = []
    pose_normals: list[list[float]] = []
    frozen_normals: list[list[float]] = []
    faces: list[list[int]] = []
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
            faces.append([int(face[0]) + offset, int(face[1]) + offset, int(face[2]) + offset])
        offset += len(source_positions)
    return {
        "positions": positions,
        "pose_recomputed_normals": pose_normals,
        "frozen_neutral_normals": frozen_normals,
        "faces": faces,
        "counts": {
            "vertices": len(positions),
            "triangles": len(faces),
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

    out_dir.mkdir(parents=True, exist_ok=True)
    glb_path = out_dir / "character-review006-current-motion-target.glb"
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
            "technical_art_head": TECHNICAL_ART_HEAD,
            "animation_head": ANIMATION_HEAD,
            "rigging_head": RIGGING_HEAD,
            "materials_static_reference_head": STATIC_REFERENCE_HEAD,
            "materials_normal_tool_blob": MATERIALS_NORMAL_TOOL_BLOB,
            "target_glb_sha256": sha256_bytes(packed.bytes),
            "target_glb_bytes": len(packed.bytes),
        },
        "target": {
            "glb_path": "generated/character-review006-current-motion-target.glb",
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
    out = out_dir / "character_review006_current_motion_direction_frame_payload.json"
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
