from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from axm_character_design.review006_uc_skin_transport import (
    POSITION_TOLERANCE_M,
    UC_GAME_POSE_RUNTIME_BLOB,
    pack_character_glb,
    transport_contract,
)

SCHEMA = "axm.character-review006-runtime-scale-accessor-dedup/v0.1"
STATUS = "PASS_CHARACTER_REVIEW006_BILATERAL_RELEASE_SCALE_ACCESSOR_DEDUP_IMPORT_BUDGET__HOLD_TARGET_ENGINE_ART_QA_ADOPTION"
TECHNICAL_ART_PARENT = "c007c327f2613989581192602338435b67b748d7"
TECHNICAL_ART_TRANSPORT_BLOB = "831fd7522ec2a8783862da653d6f12465252a3b2"
CONTROL_GLB_SHA256 = "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
UC_CURRENT_HEAD = "fed35116c1aabe54789f1197b7b2423b3b516169"
EXPECTED_CONTROL_BYTES = 44032
EXPECTED_DUPLICATE_PAYLOAD_BYTES = 321 * 3 * 4


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def git_text(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd or ROOT, text=True).strip()


def _pad4(data: bytes, fill: bytes = b"\x00") -> bytes:
    return data + fill * ((-len(data)) % 4)


def parse_glb(body: bytes) -> tuple[dict, bytes]:
    if len(body) < 28:
        raise ValueError("GLB too short")
    magic, version, total = struct.unpack_from("<4sII", body, 0)
    if magic != b"glTF" or version != 2 or total != len(body):
        raise ValueError("unexpected GLB header")
    json_len, json_kind = struct.unpack_from("<I4s", body, 12)
    if json_kind != b"JSON":
        raise ValueError("first GLB chunk is not JSON")
    json_start = 20
    json_end = json_start + json_len
    document = json.loads(body[json_start:json_end].decode("utf-8").rstrip(" "))
    bin_len, bin_kind = struct.unpack_from("<I4s", body, json_end)
    if bin_kind != b"BIN\x00":
        raise ValueError("second GLB chunk is not BIN")
    bin_start = json_end + 8
    binary = body[bin_start:bin_start + bin_len]
    if bin_start + bin_len != len(body):
        raise ValueError("unexpected trailing GLB bytes")
    if int(document["buffers"][0]["byteLength"]) != len(binary):
        raise ValueError("GLB buffer length/document mismatch")
    return document, binary


def build_glb(document: dict, binary: bytes) -> bytes:
    document = copy.deepcopy(document)
    document["buffers"][0]["byteLength"] = len(binary)
    json_chunk = _pad4(json.dumps(document, sort_keys=True, separators=(",", ":")).encode(), b" ")
    bin_chunk = _pad4(binary)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(json_chunk), b"JSON")
        + json_chunk
        + struct.pack("<I4s", len(bin_chunk), b"BIN\x00")
        + bin_chunk
    )


def accessor_payload(document: dict, binary: bytes, accessor_index: int) -> bytes:
    accessor = document["accessors"][int(accessor_index)]
    if accessor.get("componentType") != 5126 or accessor.get("type") != "VEC3":
        raise ValueError("bounded release-scale accessor must be FLOAT VEC3")
    if int(accessor.get("count", -1)) != 321:
        raise ValueError("bounded release-scale accessor must retain 321 dense keys")
    view = document["bufferViews"][int(accessor["bufferView"])]
    offset = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    expected = int(accessor["count"]) * 3 * 4
    if int(view["byteLength"]) != expected:
        raise ValueError("bounded release-scale view is not tightly packed")
    return binary[offset:offset + expected]


def find_release_scale_accessors(document: dict) -> tuple[int, int, int, int]:
    nodes = document["nodes"]
    names = {row.get("name"): index for index, row in enumerate(nodes)}
    expected_nodes = {
        "L": names.get("shoulder-L-release-transport"),
        "R": names.get("shoulder-R-release-transport"),
    }
    if None in expected_nodes.values():
        raise ValueError("bounded release helper node identity drift")
    animation = document["animations"][0]
    found: dict[str, tuple[int, int]] = {}
    for channel_index, channel in enumerate(animation["channels"]):
        target = channel["target"]
        if target.get("path") != "scale":
            continue
        for side, node_index in expected_nodes.items():
            if int(target.get("node", -1)) == int(node_index):
                sampler_index = int(channel["sampler"])
                accessor_index = int(animation["samplers"][sampler_index]["output"])
                found[side] = (sampler_index, accessor_index)
    if set(found) != {"L", "R"}:
        raise ValueError(f"expected exactly two bilateral release scale channels, observed {found}")
    return found["L"][0], found["L"][1], found["R"][0], found["R"][1]


def deduplicate_bilateral_release_scale(control_glb: bytes) -> tuple[bytes, dict]:
    document, binary = parse_glb(control_glb)
    left_sampler, left_accessor, right_sampler, right_accessor = find_release_scale_accessors(document)
    if left_accessor == right_accessor:
        raise ValueError("control is already deduplicated")
    left = accessor_payload(document, binary, left_accessor)
    right = accessor_payload(document, binary, right_accessor)
    if left != right:
        raise ValueError("bilateral release scale payloads are not byte-identical; dedup rejected")
    if len(right) != EXPECTED_DUPLICATE_PAYLOAD_BYTES:
        raise ValueError("duplicate scale payload byte budget drift")

    right_row = document["accessors"][right_accessor]
    right_view_index = int(right_row["bufferView"])
    if right_accessor != len(document["accessors"]) - 1:
        raise ValueError("bounded proof only removes the final duplicate accessor")
    if right_view_index != len(document["bufferViews"]) - 1:
        raise ValueError("bounded proof only removes the final duplicate bufferView")
    right_view = document["bufferViews"][right_view_index]
    right_offset = int(right_view.get("byteOffset", 0))
    right_length = int(right_view["byteLength"])
    if right_offset + right_length != len(binary):
        raise ValueError("bounded duplicate bufferView is not the final binary payload")

    candidate = copy.deepcopy(document)
    candidate["animations"][0]["samplers"][right_sampler]["output"] = left_accessor
    candidate["accessors"].pop()
    candidate["bufferViews"].pop()
    candidate_binary = binary[:right_offset]
    candidate_glb = build_glb(candidate, candidate_binary)

    reparsed, rebinary = parse_glb(candidate_glb)
    _, left_after, _, right_after = find_release_scale_accessors(reparsed)
    if left_after != right_after or left_after != left_accessor:
        raise ValueError("candidate did not rebind both scale channels to one accessor")
    if accessor_payload(reparsed, rebinary, left_after) != left:
        raise ValueError("candidate retained scale payload changed")

    return candidate_glb, {
        "left_scale_sampler": left_sampler,
        "right_scale_sampler": right_sampler,
        "control_left_accessor": left_accessor,
        "control_right_accessor": right_accessor,
        "candidate_shared_accessor": left_accessor,
        "duplicate_payload_bytes_removed": right_length,
        "control_accessor_count": len(document["accessors"]),
        "candidate_accessor_count": len(candidate["accessors"]),
        "control_buffer_view_count": len(document["bufferViews"]),
        "candidate_buffer_view_count": len(candidate["bufferViews"]),
        "scale_payload_sha256": sha256_bytes(left),
    }


def mutate_right_scale_byte(control_glb: bytes) -> bytes:
    document, binary = parse_glb(control_glb)
    _, _, _, right_accessor = find_release_scale_accessors(document)
    row = document["accessors"][right_accessor]
    view = document["bufferViews"][int(row["bufferView"])]
    offset = int(view.get("byteOffset", 0)) + int(row.get("byteOffset", 0))
    mutated = bytearray(binary)
    mutated[offset] ^= 0x01
    return build_glb(document, bytes(mutated))


def flatten_positions(sample) -> list[list[float]]:
    meshes = sample.get("meshes")
    if not isinstance(meshes, list) or len(meshes) != 1:
        raise ValueError("bounded UC sample expected one mesh")
    rows = meshes[0].get("positions")
    if not isinstance(rows, list) or len(rows) != 184:
        raise ValueError("bounded UC sample expected 184 vertices")
    return rows


def nested_numeric_max_delta(first, second) -> float:
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return abs(float(first) - float(second))
    if isinstance(first, list) and isinstance(second, list) and len(first) == len(second):
        return max((nested_numeric_max_delta(a, b) for a, b in zip(first, second)), default=0.0)
    raise ValueError("bounded numeric comparison shape drift")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--uc-root", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    uc_root = Path(args.uc_root).resolve()

    git_text("merge-base", "--is-ancestor", TECHNICAL_ART_PARENT, "HEAD")
    transport_blob = git_text("rev-parse", "HEAD:src/axm_character_design/review006_uc_skin_transport.py")
    if transport_blob != TECHNICAL_ART_TRANSPORT_BLOB:
        raise ValueError(f"Technical Art transport producer drift: {transport_blob}")
    if git_text("rev-parse", "HEAD", cwd=uc_root) != UC_CURRENT_HEAD:
        raise ValueError("current UC checkout drift")
    if git_text("rev-parse", "HEAD:src/axm_uc/game_pose_runtime.py", cwd=uc_root) != UC_GAME_POSE_RUNTIME_BLOB:
        raise ValueError("current UC pose receiver blob drift")

    packed = pack_character_glb()
    control = packed.bytes
    if len(control) != EXPECTED_CONTROL_BYTES or sha256_bytes(control) != CONTROL_GLB_SHA256:
        raise ValueError("exact Technical Art control GLB identity drift")

    candidate, structural = deduplicate_bilateral_release_scale(control)
    control_document, control_binary = parse_glb(control)
    candidate_document, candidate_binary = parse_glb(candidate)

    mutated = mutate_right_scale_byte(control)
    negative_rejected = False
    try:
        deduplicate_bilateral_release_scale(mutated)
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
    if control_description != candidate_description:
        raise ValueError("UC receiver description changed after scale accessor sharing")

    clip_id = transport_contract()["animation"]["clip_id"]
    max_position_delta = 0.0
    max_palette_delta = 0.0
    changed_position_samples = 0
    changed_palette_samples = 0
    for time_s in packed.times:
        control_sample = control_asset.sample(clip_id, time_s, loop=False, vertices=True)
        candidate_sample = candidate_asset.sample(clip_id, time_s, loop=False, vertices=True)
        control_positions = flatten_positions(control_sample)
        candidate_positions = flatten_positions(candidate_sample)
        position_delta = max(math.dist(a, b) for a, b in zip(control_positions, candidate_positions))
        palette_delta = nested_numeric_max_delta(
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
    if binary_saved != EXPECTED_DUPLICATE_PAYLOAD_BYTES or file_saved <= binary_saved:
        raise ValueError("dedup byte budget did not match exact duplicated scale payload")

    result = {
        "schema": SCHEMA,
        "status": STATUS,
        "identity": {
            "runtime_head": git_text("rev-parse", "HEAD"),
            "technical_art_parent": TECHNICAL_ART_PARENT,
            "technical_art_transport_blob": transport_blob,
            "uc_current_head": UC_CURRENT_HEAD,
            "uc_game_pose_runtime_blob": UC_GAME_POSE_RUNTIME_BLOB,
        },
        "control": {
            "glb_bytes": len(control),
            "glb_sha256": sha256_bytes(control),
            "binary_bytes": len(control_binary),
            "accessors": len(control_document["accessors"]),
            "buffer_views": len(control_document["bufferViews"]),
        },
        "candidate": {
            "glb_bytes": len(candidate),
            "glb_sha256": sha256_bytes(candidate),
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
            "position_tolerance_reference_m": POSITION_TOLERANCE_M,
            "description_exactly_equal": True,
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
    }

    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "runtime-head.txt").write_text(result["identity"]["runtime_head"] + "\n", encoding="utf-8")
    (out / "technical-art-parent.txt").write_text(TECHNICAL_ART_PARENT + "\n", encoding="utf-8")
    (out / "uc-current-head.txt").write_text(UC_CURRENT_HEAD + "\n", encoding="utf-8")
    (out / "result-sha256.txt").write_text(canonical_sha(result) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
