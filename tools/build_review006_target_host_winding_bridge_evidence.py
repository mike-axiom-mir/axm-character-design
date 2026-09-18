from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from axm_character_design.review006_uc_skin_transport import (
    MATERIALS_NORMAL_TOOL_BLOB,
    owner_pose,
    pack_character_glb,
    side_contexts,
    smooth_normals,
    source_to_gltf,
    transport_contract,
)
from axm_character_design.target_host_surface_bridge import reverse_triangle_winding

SCHEMA = "axm.character-review006-target-host-winding-bridge-payload/v0.1"
RESULT = "READY_CHARACTER_REVIEW006_TARGET_HOST_WINDING_BRIDGE_RECEIVER"
TARGET_GLB_SHA256 = "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
TARGET_GLB_BYTES = 44032
MATERIALS_HEAD = "23609806af791330f5cd511fab55dd56a633fe21"
MATERIALS_STATIC_HEAD = "e450684b398f8e5b0e23c4cbf717e3475dd4d5ee"
MATERIALS_NORMAL_BLOB = "843c0e1866172dd8b6c5ab0f23d69d1e469562f7"
RIGGING_NEUTRAL_HEAD = "675a6800271f9be563763026e3b196607a0a1cd3"
RIGGING_NEUTRAL_STATUS = "PASS_CHARACTER_REVIEW006_NEUTRAL_BIND_FRAME_CLOSURE__STRUCTURAL_BOUNDARY_UNCHANGED"
UC_POSE_RUNTIME_BLOB = "dee5db003a56a0a5f55092c1b3db50f56a22de7e"


def canonical_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_materials_contract(path: Path) -> dict:
    row = json.loads(path.read_text(encoding="utf-8"))
    if row.get("schema") != "axm.character-review006-neutral-target-host-isolation-lookdev/v0.1":
        raise ValueError("Materials neutral receiver contract schema drift")
    if row.get("technical_art_target_glb_sha256") != TARGET_GLB_SHA256:
        raise ValueError("Materials target GLB identity drift")
    material = row.get("material", {})
    if list(material.get("albedo_srgb", [])) != [0.56, 0.43, 0.36]:
        raise ValueError("Materials review albedo drift")
    if float(material.get("metallic", -1)) != 0.0 or float(material.get("roughness", -1)) != 0.62:
        raise ValueError("Materials review scalar drift")
    if list(row.get("contexts", [])) != ["front", "three_quarter", "grazing"]:
        raise ValueError("Materials camera context drift")
    return row


def _load_rigging_neutral(path: Path) -> dict:
    row = json.loads(path.read_text(encoding="utf-8"))
    if row.get("status") != RIGGING_NEUTRAL_STATUS:
        raise ValueError("Rigging neutral closure prerequisite is not green")
    neutral = row.get("neutral_closure", {})
    if int(neutral.get("total_receiver_vertices", -1)) != 184:
        raise ValueError("Rigging neutral receiver vertex count drift")
    if float(neutral.get("max_owner_vertex_drift_m", -1)) != 0.0:
        raise ValueError("Rigging neutral owner positions are not exact")
    if float(neutral.get("max_gradient_identity_component_delta", -1)) != 0.0:
        raise ValueError("Rigging neutral gradient is not identity")
    if float(neutral.get("max_normal_matrix_identity_component_delta", -1)) != 0.0:
        raise ValueError("Rigging neutral normal matrix is not identity")
    if row.get("negative_control", {}).get("rejected") is not True:
        raise ValueError("Rigging neutral negative control did not reject")
    return row


def combined_neutral_reference() -> dict:
    contexts = side_contexts()
    positions: list[list[float]] = []
    normals: list[list[float]] = []
    faces: list[list[int]] = []
    offset = 0
    by_side = {}
    for side in ("L", "R"):
        context = contexts[side]
        specimen = context["specimen"]
        source_positions = owner_pose(side, 0.0, contexts)
        source_normals = smooth_normals(source_positions, specimen["faces"])
        by_side[side] = {"vertices": len(source_positions), "triangles": len(specimen["faces"])}
        positions.extend(source_to_gltf(v) for v in source_positions)
        normals.extend(source_to_gltf(n) for n in source_normals)
        for face in specimen["faces"]:
            faces.append([int(face[0]) + offset, int(face[1]) + offset, int(face[2]) + offset])
        offset += len(source_positions)
    if len(positions) != 184 or len(faces) != 360:
        raise ValueError("combined neutral reference shape drift")
    return {
        "positions": positions,
        "normals": normals,
        "owner_faces": faces,
        "receiver_winding_candidate_faces": reverse_triangle_winding(faces),
        "counts": {"vertices": len(positions), "triangles": len(faces), "indices": len(faces) * 3, "by_side": by_side},
    }


def build_payload(
    *,
    out_dir: Path,
    materials_contract_path: Path,
    rigging_neutral_path: Path,
    technical_art_head: str,
    uc_head: str,
) -> dict:
    if len(technical_art_head) != 40 or len(uc_head) != 40:
        raise ValueError("exact Technical Art and UC commit SHAs are required")
    materials = _load_materials_contract(materials_contract_path)
    rigging = _load_rigging_neutral(rigging_neutral_path)
    if MATERIALS_NORMAL_TOOL_BLOB != MATERIALS_NORMAL_BLOB:
        raise ValueError("Technical Art Materials normal-method identity drift")

    donor = transport_contract()
    packed = pack_character_glb()
    glb_sha = sha256_bytes(packed.bytes)
    if glb_sha != TARGET_GLB_SHA256 or len(packed.bytes) != TARGET_GLB_BYTES:
        raise ValueError(f"Technical Art target GLB drift: {glb_sha} / {len(packed.bytes)}")
    if abs(float(packed.times[160]) - 1.0) > 1e-12 or abs(float(packed.angles[160])) > 1e-12:
        raise ValueError("Technical Art neutral animation sample drift")

    reference = combined_neutral_reference()
    out_dir.mkdir(parents=True, exist_ok=True)
    glb_path = out_dir / "character-review006-target-host-winding-target.glb"
    glb_path.write_bytes(packed.bytes)

    payload = {
        "schema": SCHEMA,
        "result": RESULT,
        "exact_identity": {
            "technical_art_head": technical_art_head,
            "target_glb_sha256": glb_sha,
            "target_glb_bytes": len(packed.bytes),
            "materials_neutral_isolation_head": MATERIALS_HEAD,
            "materials_static_reference_head": MATERIALS_STATIC_HEAD,
            "materials_normal_method_blob": MATERIALS_NORMAL_BLOB,
            "rigging_neutral_head": RIGGING_NEUTRAL_HEAD,
            "uc_head": uc_head,
            "uc_pose_runtime_blob": UC_POSE_RUNTIME_BLOB,
        },
        "target": {
            "glb_path": "generated/character-review006-target-host-winding-target.glb",
            "clip_id": donor["animation"]["clip_id"],
            "neutral_sample_index": 160,
            "neutral_time_s": float(packed.times[160]),
        },
        "external_owner_receipts": {
            "rigging_neutral_status": rigging["status"],
            "rigging_neutral_max_owner_vertex_drift_m": rigging["neutral_closure"]["max_owner_vertex_drift_m"],
            "rigging_neutral_max_gradient_identity_delta": rigging["neutral_closure"]["max_gradient_identity_component_delta"],
            "rigging_neutral_max_normal_matrix_identity_delta": rigging["neutral_closure"]["max_normal_matrix_identity_component_delta"],
        },
        "materials_fixture": {
            "source_head": MATERIALS_HEAD,
            "albedo_srgb": list(materials["material"]["albedo_srgb"]),
            "metallic": float(materials["material"]["metallic"]),
            "roughness": float(materials["material"]["roughness"]),
            "contexts": list(materials["contexts"]),
            "semantics_copied_into_uc": False,
        },
        "neutral_reference": reference,
        "bridge_candidate": {
            "kind": "PER_TRIANGLE_RECEIVER_LOCAL_WINDING_PERMUTATION",
            "owner_order": "[a,b,c]",
            "candidate_order": "[a,c,b]",
            "source_positions_changed": False,
            "source_normals_changed": False,
            "source_topology_membership_changed": False,
            "uc_product_modified": False,
            "universal_receiver_rule_claimed": False,
        },
        "truth_boundary": {
            "neutral_receiver_winding_relation": "TO_BE_OBSERVED_IN_REAL_GODOT",
            "neutral_shaded_equivalence_after_adapter": "TO_BE_OBSERVED_IN_REAL_GODOT",
            "deformed_normal_or_tangent_equivalence": "NOT_CLAIMED",
            "materials_policy_changed": False,
            "rigging_policy_changed": False,
            "uc_product_modified": False,
            "art_or_qa_acceptance": False,
            "canon": False,
            "production_ready": False,
        },
    }
    payload["payload_sha256"] = canonical_digest(payload)
    (out_dir / "character_review006_target_host_winding_bridge_payload.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="lookdev-proof/generated")
    parser.add_argument("--materials-contract", required=True)
    parser.add_argument("--rigging-neutral", required=True)
    parser.add_argument("--technical-art-head", required=True)
    parser.add_argument("--uc-head", required=True)
    args = parser.parse_args()
    payload = build_payload(
        out_dir=Path(args.out_dir),
        materials_contract_path=Path(args.materials_contract),
        rigging_neutral_path=Path(args.rigging_neutral),
        technical_art_head=args.technical_art_head,
        uc_head=args.uc_head,
    )
    print(json.dumps({
        "result": payload["result"],
        "payload_sha256": payload["payload_sha256"],
        "target_glb_sha256": payload["exact_identity"]["target_glb_sha256"],
        "triangles": payload["neutral_reference"]["counts"]["triangles"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
