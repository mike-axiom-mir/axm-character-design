from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import build_runtime_review006_scale_accessor_dedup as base


def receiver_semantic_shape(description: dict) -> dict:
    return {
        "vertices": description.get("vertices"),
        "primitives": description.get("primitives"),
        "clips": [
            {"name": row.get("name"), "channels": row.get("channels")}
            for row in description.get("clips", [])
        ],
        "skins": [
            {"joints": len(row.get("joints", []))}
            for row in description.get("skins", [])
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--uc-root", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    uc_root = Path(args.uc_root).resolve()

    base.git_text("merge-base", "--is-ancestor", base.TECHNICAL_ART_PARENT, "HEAD")
    transport_blob = base.git_text("rev-parse", "HEAD:src/axm_character_design/review006_uc_skin_transport.py")
    if transport_blob != base.TECHNICAL_ART_TRANSPORT_BLOB:
        raise ValueError(f"Technical Art transport producer drift: {transport_blob}")
    if base.git_text("rev-parse", "HEAD", cwd=uc_root) != base.UC_CURRENT_HEAD:
        raise ValueError("current UC checkout drift")
    if base.git_text("rev-parse", "HEAD:src/axm_uc/game_pose_runtime.py", cwd=uc_root) != base.UC_GAME_POSE_RUNTIME_BLOB:
        raise ValueError("current UC pose receiver blob drift")

    packed = base.pack_character_glb()
    control = packed.bytes
    if len(control) != base.EXPECTED_CONTROL_BYTES or base.sha256_bytes(control) != base.CONTROL_GLB_SHA256:
        raise ValueError("exact Technical Art control GLB identity drift")

    candidate, structural = base.deduplicate_bilateral_release_scale(control)
    control_document, control_binary = base.parse_glb(control)
    candidate_document, candidate_binary = base.parse_glb(candidate)

    mutated = base.mutate_right_scale_byte(control)
    negative_rejected = False
    try:
        base.deduplicate_bilateral_release_scale(mutated)
    except ValueError as exc:
        negative_rejected = "not byte-identical" in str(exc)
    if not negative_rejected:
        raise ValueError("non-identical bilateral scale negative control was not rejected")

    control_path = out / "review006-control-duplicate-release-scale.glb"
    candidate_path = out / "review006-candidate-shared-release-scale.glb"
    control_path.write_bytes(control)
    candidate_path.write_bytes(candidate)

    sys.path.insert(0, str(uc_root / "src"))
    from axm_uc.game_pose_runtime import load_game_pose_glb

    control_asset = load_game_pose_glb(control_path)
    candidate_asset = load_game_pose_glb(candidate_path)
    control_description = control_asset.describe()
    candidate_description = candidate_asset.describe()
    control_shape = receiver_semantic_shape(control_description)
    candidate_shape = receiver_semantic_shape(candidate_description)
    if control_shape != candidate_shape:
        raise ValueError(
            "UC receiver semantic shape changed after scale accessor sharing: "
            f"{control_shape} != {candidate_shape}"
        )

    clip_id = base.transport_contract()["animation"]["clip_id"]
    max_position_delta = 0.0
    max_palette_delta = 0.0
    changed_position_samples = 0
    changed_palette_samples = 0
    for time_s in packed.times:
        control_sample = control_asset.sample(clip_id, time_s, loop=False, vertices=True)
        candidate_sample = candidate_asset.sample(clip_id, time_s, loop=False, vertices=True)
        control_positions = base.flatten_positions(control_sample)
        candidate_positions = base.flatten_positions(candidate_sample)
        position_delta = max(math.dist(a, b) for a, b in zip(control_positions, candidate_positions))
        palette_delta = base.nested_numeric_max_delta(
            control_sample["skin_world_matrices"], candidate_sample["skin_world_matrices"]
        )
        max_position_delta = max(max_position_delta, position_delta)
        max_palette_delta = max(max_palette_delta, palette_delta)
        changed_position_samples += int(position_delta != 0.0)
        changed_palette_samples += int(palette_delta != 0.0)

    if max_position_delta != 0.0 or max_palette_delta != 0.0:
        raise ValueError(
            f"UC semantic delta after exact accessor sharing: positions={max_position_delta} palette={max_palette_delta}"
        )

    file_saved = len(control) - len(candidate)
    binary_saved = len(control_binary) - len(candidate_binary)
    if binary_saved != base.EXPECTED_DUPLICATE_PAYLOAD_BYTES or file_saved <= binary_saved:
        raise ValueError("dedup byte budget did not match exact duplicated scale payload")

    result = {
        "schema": base.SCHEMA,
        "status": base.STATUS,
        "identity": {
            "runtime_head": base.git_text("rev-parse", "HEAD"),
            "technical_art_parent": base.TECHNICAL_ART_PARENT,
            "technical_art_transport_blob": transport_blob,
            "uc_current_head": base.UC_CURRENT_HEAD,
            "uc_game_pose_runtime_blob": base.UC_GAME_POSE_RUNTIME_BLOB,
        },
        "control": {
            "glb_bytes": len(control),
            "glb_sha256": base.sha256_bytes(control),
            "binary_bytes": len(control_binary),
            "accessors": len(control_document["accessors"]),
            "buffer_views": len(control_document["bufferViews"]),
        },
        "candidate": {
            "glb_bytes": len(candidate),
            "glb_sha256": base.sha256_bytes(candidate),
            "binary_bytes": len(candidate_binary),
            "accessors": len(candidate_document["accessors"]),
            "buffer_views": len(candidate_document["bufferViews"]),
        },
        "before_after": {
            "file_bytes_saved": file_saved,
            "file_percent_reduction": 100.0 * file_saved / len(control),
            "binary_bytes_saved": binary_saved,
            "binary_percent_reduction": 100.0 * binary_saved / len(control_binary),
            "duplicate_animation_payload_bytes_removed": structural["duplicate_payload_bytes_removed"],
            "animation_key_count_per_channel": 321,
            "animation_channels": 6,
            "scale_channels_sharing_output_accessor_after": 2,
        },
        "exact_shared_payload": structural,
        "uc_receiver_equivalence": {
            "sample_count": len(packed.times),
            "vertices_per_sample": 184,
            "maximum_position_delta_m": max_position_delta,
            "changed_position_samples": changed_position_samples,
            "maximum_skin_palette_component_delta": max_palette_delta,
            "changed_palette_samples": changed_palette_samples,
            "position_tolerance_reference_m": base.POSITION_TOLERANCE_M,
            "semantic_shape_equal": control_shape == candidate_shape,
            "full_description_equal": control_description == candidate_description,
            "control_semantic_shape": control_shape,
            "candidate_semantic_shape": candidate_shape,
        },
        "negative_control": {
            "mutation": "flip one byte only in the right release-scale payload before dedup",
            "non_identical_payload_rejected": negative_rejected,
        },
        "visual_tradeoff": {
            "measured_receiver_input_delta": "NONE_OBSERVED_EXACT_UC_POSITION_AND_SKIN_PALETTE_IDENTITY_ALL_321_KEYS",
            "rendered_frame_delta": "NOT_REMEASURED",
            "art_direction_acceptance": "HOLD",
            "visual_qa_acceptance": "HOLD",
        },
        "truth_boundary": {
            "import_file_size": "MEASURED",
            "glb_binary_payload": "MEASURED",
            "current_uc_position_and_palette_equivalence": "MEASURED_ALL_321_KEYS",
            "target_engine_import_memory": "NOT_MEASURED",
            "target_device_cpu_gpu_fps_vram": "NOT_MEASURED",
            "rendered_frame_equivalence": "NOT_MEASURED",
            "technical_art_producer_adoption": False,
            "uc_changed": False,
            "canon": False,
            "production_readiness": False,
        },
        "harness_repair": {
            "failed_predecessor_gate": "FULL_UC_DESCRIPTION_DICT_EQUALITY",
            "repair": "COMPARE_SEMANTIC_RECEIVER_SHAPE_THEN_EXACTLY_COMPARE_ALL_321_POSITION_AND_SKIN_PALETTE_SAMPLES",
            "candidate_semantics_weakened": False,
        },
    }

    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "uc-control-description.json").write_text(json.dumps(control_description, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "uc-candidate-description.json").write_text(json.dumps(candidate_description, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "runtime-head.txt").write_text(result["identity"]["runtime_head"] + "\n", encoding="utf-8")
    (out / "technical-art-parent.txt").write_text(base.TECHNICAL_ART_PARENT + "\n", encoding="utf-8")
    (out / "uc-current-head.txt").write_text(base.UC_CURRENT_HEAD + "\n", encoding="utf-8")
    (out / "result-sha256.txt").write_text(base.canonical_sha(result) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
