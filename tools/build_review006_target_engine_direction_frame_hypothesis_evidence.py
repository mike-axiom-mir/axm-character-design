from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from axm_character_design.review006_uc_skin_transport import (
    owner_pose,
    pack_character_glb,
    transport_contract,
    side_contexts,
    smooth_normals,
    source_to_gltf,
)
from axm_character_design.target_host_surface_bridge import reverse_triangle_winding

SCHEMA = "axm.character-review006-target-engine-direction-frame-hypothesis/v0.1"
READY = "READY_CHARACTER_REVIEW006_TARGET_ENGINE_DIRECTION_FRAME_HYPOTHESIS_RECEIVER"

TECHNICAL_ART_PARENT_HEAD = "a61f96d2cf8c33b153d17810ad18ca48074b81d2"
RIGGING_HEAD = "4efa5772ee63f62d7a7e5b4ef6688550034b4659"
RIGGING_GRADIENT_BLOB = "57c43aea818f293274a94457252bf87e20b98897"
MATERIALS_HEAD = "9978794604d31aff1f326a6a0dedd2d81dccf31f"
MATERIALS_OBSERVER_BLOB = "349b6b7374d1704907a00f90c9e8c5e6940cdb65"
UC_HEAD = "41b4d9134e4d2e5f4fadaada2a1d6a56eed92ab0"
EXPECTED_TARGET_GLB_SHA256 = "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
EXPECTED_TARGET_GLB_BYTES = 44032
SAMPLES = {80: -30.0, 160: 0.0, 240: 30.0}
ANGLE_TOLERANCE = 1e-4


def canonical_digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _dot(a, b):
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _unit(value):
    mag = math.sqrt(_dot(value, value))
    if not math.isfinite(mag) or mag <= 1e-15:
        raise ValueError("normal hypothesis produced a zero/non-finite vector")
    return [float(component) / mag for component in value]


def _matrix_vector(matrix, vector):
    return [
        sum(float(matrix[row][column]) * float(vector[column]) for column in range(3))
        for row in range(3)
    ]


def _oracle_key(side: str, angle_deg: float, group: str) -> tuple[str, float, str]:
    return side, round(float(angle_deg), 8), group


def load_rigging_oracle(path: Path) -> tuple[dict, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "axm.character-review006-rig-deformation-gradient-frame/v0.1":
        raise ValueError("Rigging deformation-gradient oracle schema drift")
    if data.get("status") != "PASS_CHARACTER_REVIEW006_RIG_DEFORMATION_GRADIENT_FRAME_REFERENCE__STRUCTURAL_BOUNDARY_UNCHANGED":
        raise ValueError("Rigging deformation-gradient oracle is not green")
    rows = data.get("deformation_gradient_reference", {}).get("rows", [])
    index = {}
    for row in rows:
        key = _oracle_key(row["side"], row["angle_deg"], row["group"])
        if key in index:
            raise ValueError(f"duplicate Rigging oracle row {key}")
        index[key] = row
    for side in ("L", "R"):
        for angle in SAMPLES.values():
            for group in ("ribcage", "seam", "proximal", "distal", "distal_cap"):
                if _oracle_key(side, angle, group) not in index:
                    raise ValueError(f"missing Rigging oracle row {(side, angle, group)}")
    return data, index


def _group_by_vertex(context: dict) -> list[str]:
    count = len(context["specimen"]["positions"])
    result = [None] * count
    for group, indexes in context["layout"]["groups"].items():
        for index in indexes:
            index = int(index)
            if index < 0 or index >= count or result[index] is not None:
                raise ValueError("Rigging group coverage is invalid")
            result[index] = str(group)
    if any(value is None for value in result):
        raise ValueError("Rigging groups do not cover every vertex exactly once")
    return result


def _combined_reference(angle_deg: float, contexts: dict, neutral_normals_by_side: dict, oracle_rows: dict) -> dict:
    positions = []
    frozen = []
    pose_recomputed = []
    linear_gradient = []
    inverse_transpose = []
    owner_faces = []
    group_rows = []
    offset = 0

    for side in ("L", "R"):
        context = contexts[side]
        specimen = context["specimen"]
        groups = _group_by_vertex(context)
        source_positions = owner_pose(side, angle_deg, contexts)
        source_pose_normals = smooth_normals(source_positions, specimen["faces"])
        neutral_normals = neutral_normals_by_side[side]

        positions.extend(source_to_gltf(value) for value in source_positions)
        pose_recomputed.extend(source_to_gltf(value) for value in source_pose_normals)
        frozen.extend(source_to_gltf(value) for value in neutral_normals)

        for index, neutral in enumerate(neutral_normals):
            group = groups[index]
            row = oracle_rows[_oracle_key(side, angle_deg, group)]
            linear_source = _unit(_matrix_vector(row["gradient"], neutral))
            inverse_source = _unit(_matrix_vector(row["normal_matrix"], neutral))
            linear_gradient.append(source_to_gltf(linear_source))
            inverse_transpose.append(source_to_gltf(inverse_source))

        for group in sorted(set(groups)):
            row = oracle_rows[_oracle_key(side, angle_deg, group)]
            group_rows.append({
                "side": side,
                "group": group,
                "angle_deg": float(angle_deg),
                "child_weight": float(row["child_weight"]),
                "gradient": row["gradient"],
                "normal_matrix": row["normal_matrix"],
                "determinant": float(row["determinant"]),
            })

        for face in specimen["faces"]:
            owner_faces.append([
                int(face[0]) + offset,
                int(face[1]) + offset,
                int(face[2]) + offset,
            ])
        offset += len(source_positions)

    return {
        "positions": positions,
        "normals": {
            "frozen_neutral": frozen,
            "pose_recomputed": pose_recomputed,
            "linear_gradient": linear_gradient,
            "inverse_transpose": inverse_transpose,
        },
        "owner_faces": owner_faces,
        "receiver_winding_faces": reverse_triangle_winding(owner_faces),
        "rigging_group_frames": group_rows,
        "counts": {
            "vertices": len(positions),
            "triangles": len(owner_faces),
            "indices": len(owner_faces) * 3,
        },
    }


def _max_vector_delta(a, b) -> float:
    return max(
        max(abs(float(first[i]) - float(second[i])) for i in range(3))
        for first, second in zip(a, b)
    )


def build_payload(rigging_oracle_path: Path, out_dir: Path) -> dict:
    rigging_oracle, oracle_rows = load_rigging_oracle(rigging_oracle_path)
    packed = pack_character_glb()
    digest = sha256_bytes(packed.bytes)
    if digest != EXPECTED_TARGET_GLB_SHA256 or len(packed.bytes) != EXPECTED_TARGET_GLB_BYTES:
        raise ValueError(
            f"Technical Art target GLB identity drift: bytes={len(packed.bytes)} sha256={digest}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    glb_path = out_dir / "character-review006-target-engine-direction-frame-target.glb"
    glb_path.write_bytes(packed.bytes)

    contexts = side_contexts()
    neutral_normals_by_side = {}
    for side in ("L", "R"):
        neutral_positions = owner_pose(side, 0.0, contexts)
        neutral_normals_by_side[side] = smooth_normals(
            neutral_positions, contexts[side]["specimen"]["faces"]
        )

    samples = {}
    for sample_index, expected_angle in SAMPLES.items():
        actual_angle = float(packed.angles[sample_index])
        if abs(actual_angle - expected_angle) > ANGLE_TOLERANCE:
            raise ValueError(
                f"sample {sample_index} angle drift: {actual_angle} != {expected_angle}"
            )
        reference = _combined_reference(
            actual_angle, contexts, neutral_normals_by_side, oracle_rows
        )
        if reference["counts"] != {"vertices": 184, "triangles": 360, "indices": 1080}:
            raise ValueError(f"reference count drift: {reference['counts']}")
        samples[str(sample_index)] = {
            "sample_index": sample_index,
            "time_s": float(packed.times[sample_index]),
            "angle_deg": actual_angle,
            "reference": reference,
        }

    neutral = samples["160"]["reference"]["normals"]
    neutral_linear_vs_inverse = _max_vector_delta(
        neutral["linear_gradient"], neutral["inverse_transpose"]
    )
    neutral_linear_vs_frozen = _max_vector_delta(
        neutral["linear_gradient"], neutral["frozen_neutral"]
    )
    if neutral_linear_vs_inverse > 1e-12 or neutral_linear_vs_frozen > 1e-12:
        raise ValueError("neutral direction-frame hypotheses are not identical")

    deformed_separation = {}
    for key in ("80", "240"):
        normals = samples[key]["reference"]["normals"]
        linear_vs_inverse = _max_vector_delta(
            normals["linear_gradient"], normals["inverse_transpose"]
        )
        linear_vs_frozen = _max_vector_delta(
            normals["linear_gradient"], normals["frozen_neutral"]
        )
        inverse_vs_frozen = _max_vector_delta(
            normals["inverse_transpose"], normals["frozen_neutral"]
        )
        if linear_vs_inverse <= 1e-6:
            raise ValueError(f"deformed hypotheses are not distinguishable at sample {key}")
        deformed_separation[key] = {
            "linear_vs_inverse_max_component_delta": linear_vs_inverse,
            "linear_vs_frozen_max_component_delta": linear_vs_frozen,
            "inverse_vs_frozen_max_component_delta": inverse_vs_frozen,
        }

    payload = {
        "schema": SCHEMA,
        "result": READY,
        "exact_identity": {
            "technical_art_parent_head": TECHNICAL_ART_PARENT_HEAD,
            "rigging_head": RIGGING_HEAD,
            "rigging_gradient_blob": RIGGING_GRADIENT_BLOB,
            "materials_head": MATERIALS_HEAD,
            "materials_host_equivalent_observer_blob": MATERIALS_OBSERVER_BLOB,
            "uc_head": UC_HEAD,
            "target_glb_sha256": digest,
            "target_glb_bytes": len(packed.bytes),
            "rigging_oracle_sha256": canonical_digest(rigging_oracle),
        },
        "target": {
            "glb_path": "generated/character-review006-target-engine-direction-frame-target.glb",
            "clip_id": transport_contract()["animation"]["clip_id"],
        },
        "normal_hypotheses": {
            "linear_gradient": (
                "normalize(D * n0), where D is the exact Rigging owner local deformation gradient"
            ),
            "inverse_transpose": (
                "normalize(inverse_transpose(D) * n0), using the exact Rigging owner normal matrix"
            ),
            "pose_recomputed": (
                "Materials reference: area-weighted smooth normals recomputed from the posed owner surface"
            ),
            "frozen_neutral": "neutral owner smooth normals retained through deformation",
        },
        "samples": samples,
        "deformed_hypothesis_separation": deformed_separation,
        "truth_boundary": {
            "receiver": "Godot 4.7.2-stable / GL Compatibility in retained workflow",
            "normal_buffer_probe": "normal-as-color shaded diagnostic, not production material acceptance",
            "godot_skinning_implementation_claim": False,
            "universal_godot_rule_claim": False,
            "uc_product_modified": False,
            "source_geometry_changed": False,
            "source_topology_changed": False,
            "rigging_changed": False,
            "animation_changed": False,
            "materials_policy_changed": False,
            "production_normals_or_tangents": False,
            "runtime_or_target_device_acceptance": False,
            "visual_acceptance": False,
            "source_adoption_or_canon": False,
            "production_readiness": False,
        },
    }
    payload["payload_sha256"] = canonical_digest(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rigging-oracle",
        default="lookdev-proof/generated/exact-rigging-deformation-gradient-frame.json",
    )
    parser.add_argument("--out-dir", default="lookdev-proof/generated")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    payload = build_payload(Path(args.rigging_oracle), out_dir)
    path = out_dir / "character_review006_target_engine_direction_frame_hypothesis_payload.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": payload["result"],
        "payload_sha256": payload["payload_sha256"],
        "target_glb_sha256": payload["exact_identity"]["target_glb_sha256"],
        "deformed_hypothesis_separation": payload["deformed_hypothesis_separation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
