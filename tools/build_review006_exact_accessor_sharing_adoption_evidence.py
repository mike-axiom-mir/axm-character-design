from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from axm_character_design.review006_exact_accessor_sharing import (
    ADOPTION_STATUS,
    LEFT_RELEASE_NODE,
    RIGHT_RELEASE_NODE,
    RUNTIME_DONOR_HEAD,
    _channel_output,
    mutate_duplicate_output_byte,
    pack_character_glb_with_shared_release_scale,
    parse_glb,
    share_exact_animation_output_accessor,
)
from axm_character_design.review006_uc_skin_transport import pack_character_glb, transport_contract

SCHEMA = "axm.character-review006-technical-art-accessor-sharing-current-uc-evidence/v0.1"
RESULT = "PASS_CHARACTER_REVIEW006_RUNTIME_EXACT_ACCESSOR_SHARING_ADOPTED_AT_TECHNICAL_ART_EXPORT_BOUNDARY_TO_CURRENT_UC"
TECHNICAL_ART_PARENT_HEAD = "36744749a592e067a119f3349a499d65f25af134"
UC_CURRENT_HEAD = "17b3533a73ae865080762cd9429a027baa5552b0"
UC_GAME_POSE_RUNTIME_BLOB = "dee5db003a56a0a5f55092c1b3db50f56a22de7e"
RUNTIME_DONOR_STATUS = "PASS_CHARACTER_REVIEW006_BILATERAL_RELEASE_SCALE_ACCESSOR_DEDUP_IMPORT_BUDGET__HOLD_TARGET_ENGINE_ART_QA_ADOPTION"
EXPECTED_CONTROL_SHA256 = "76acbfca2c50151f4c801bf34910f94eea6bd6d165caeb1e344b8001a2b83a99"
EXPECTED_CONTROL_BYTES = 44032
EXPECTED_CANDIDATE_BYTES = 40064


def git_text(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd or ROOT, text=True).strip()


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def canonical_sha(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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


def flatten_positions(sample: dict) -> list[list[float]]:
    meshes = sample.get("meshes")
    if not isinstance(meshes, list) or len(meshes) != 1:
        raise ValueError("bounded current-UC sample expected one mesh")
    rows = meshes[0].get("positions")
    if not isinstance(rows, list) or len(rows) != 184:
        raise ValueError("bounded current-UC sample expected 184 vertices")
    return rows


def nested_numeric_max_delta(first, second) -> float:
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return abs(float(first) - float(second))
    if isinstance(first, list) and isinstance(second, list) and len(first) == len(second):
        return max((nested_numeric_max_delta(a, b) for a, b in zip(first, second)), default=0.0)
    raise ValueError("bounded numeric comparison shape drift")


def validate_runtime_donor(runtime_donor_dir: Path, candidate_bytes: bytes) -> dict:
    result_path = runtime_donor_dir / "result.json"
    donor_candidate_path = runtime_donor_dir / "review006-candidate-shared-release-scale.glb"
    donor_control_path = runtime_donor_dir / "review006-control-duplicate-release-scale.glb"
    if not result_path.is_file() or not donor_candidate_path.is_file() or not donor_control_path.is_file():
        raise ValueError("Runtime donor evidence directory is incomplete")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("status") != RUNTIME_DONOR_STATUS:
        raise ValueError("Runtime donor result is not the exact green bounded state")
    if result.get("identity", {}).get("runtime_head") != RUNTIME_DONOR_HEAD:
        raise ValueError("Runtime donor head drift")
    donor_candidate = donor_candidate_path.read_bytes()
    donor_control = donor_control_path.read_bytes()
    if donor_candidate != candidate_bytes:
        raise ValueError("Technical Art producer candidate is not byte-identical to Runtime donor candidate")
    if sha256_bytes(donor_control) != EXPECTED_CONTROL_SHA256:
        raise ValueError("Runtime donor control identity drift")
    return {
        "runtime_head": RUNTIME_DONOR_HEAD,
        "runtime_status": result["status"],
        "runtime_result_sha256": canonical_sha(result),
        "candidate_byte_identical": True,
        "candidate_sha256": sha256_bytes(donor_candidate),
        "candidate_bytes": len(donor_candidate),
    }


def build_evidence(out: Path, uc_root: Path, runtime_donor_dir: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    git_text("merge-base", "--is-ancestor", TECHNICAL_ART_PARENT_HEAD, "HEAD")
    technical_art_head = git_text("rev-parse", "HEAD")
    uc_head = git_text("rev-parse", "HEAD", cwd=uc_root)
    if uc_head != UC_CURRENT_HEAD:
        raise ValueError(f"current UC checkout drift: {uc_head}")
    uc_blob = git_text("rev-parse", "HEAD:src/axm_uc/game_pose_runtime.py", cwd=uc_root)
    if uc_blob != UC_GAME_POSE_RUNTIME_BLOB:
        raise ValueError(f"current UC pose receiver blob drift: {uc_blob}")

    control = pack_character_glb()
    if len(control.bytes) != EXPECTED_CONTROL_BYTES or sha256_bytes(control.bytes) != EXPECTED_CONTROL_SHA256:
        raise ValueError("historical Technical Art control GLB identity drift")
    candidate, adoption = pack_character_glb_with_shared_release_scale()
    if adoption["status"] != ADOPTION_STATUS or len(candidate.bytes) != EXPECTED_CANDIDATE_BYTES:
        raise ValueError("Technical Art exact-sharing candidate did not reach expected bounded state")

    donor = validate_runtime_donor(runtime_donor_dir, candidate.bytes)

    control_path = out / "review006-control-duplicate-release-scale.glb"
    candidate_path = out / "review006-technical-art-shared-release-scale.glb"
    control_path.write_bytes(control.bytes)
    candidate_path.write_bytes(candidate.bytes)

    candidate_document, _ = parse_glb(candidate.bytes)
    _, left_scale = _channel_output(candidate_document, LEFT_RELEASE_NODE, "scale")
    _, right_scale = _channel_output(candidate_document, RIGHT_RELEASE_NODE, "scale")
    if left_scale != right_scale:
        raise ValueError("producer candidate does not actually share the bilateral scale accessor")

    mutated = mutate_duplicate_output_byte(
        control.bytes, duplicate_node_name=RIGHT_RELEASE_NODE, path="scale"
    )
    negative_rejected = False
    try:
        share_exact_animation_output_accessor(
            mutated,
            keeper_node_name=LEFT_RELEASE_NODE,
            duplicate_node_name=RIGHT_RELEASE_NODE,
            path="scale",
        )
    except ValueError as exc:
        negative_rejected = "not byte-identical" in str(exc)
    if not negative_rejected:
        raise ValueError("one-byte bilateral payload mismatch did not fail closed")

    if len(control.times) != 321 or not math.isclose(control.times[0], 0.0, abs_tol=1e-12):
        raise ValueError("review-006 dense source sample contract drift")
    source_duration_s = float(control.times[-1])
    if not math.isclose(source_duration_s, 2.0, abs_tol=1e-12):
        raise ValueError("review-006 dense source duration drift")
    source_dense_hz = int(round((len(control.times) - 1) / source_duration_s))
    if source_dense_hz != 160:
        raise ValueError("review-006 dense source rate drift")

    sys.path.insert(0, str(uc_root / "src"))
    from axm_uc.game_pose_runtime import load_game_pose_glb

    control_asset = load_game_pose_glb(control_path)
    candidate_asset = load_game_pose_glb(candidate_path)
    control_description = control_asset.describe()
    candidate_description = candidate_asset.describe()
    control_shape = receiver_semantic_shape(control_description)
    candidate_shape = receiver_semantic_shape(candidate_description)
    if control_shape != candidate_shape:
        raise ValueError("current UC semantic receiver shape changed after exact accessor sharing")

    clip_id = transport_contract()["animation"]["clip_id"]
    max_position_delta = 0.0
    max_palette_delta = 0.0
    changed_position_samples = 0
    changed_palette_samples = 0
    for time_s in control.times:
        control_sample = control_asset.sample(clip_id, time_s, loop=False, vertices=True)
        candidate_sample = candidate_asset.sample(clip_id, time_s, loop=False, vertices=True)
        first = flatten_positions(control_sample)
        second = flatten_positions(candidate_sample)
        position_delta = max(math.dist(a, b) for a, b in zip(first, second))
        palette_delta = nested_numeric_max_delta(
            control_sample["skin_world_matrices"], candidate_sample["skin_world_matrices"]
        )
        max_position_delta = max(max_position_delta, position_delta)
        max_palette_delta = max(max_palette_delta, palette_delta)
        changed_position_samples += int(position_delta != 0.0)
        changed_palette_samples += int(palette_delta != 0.0)
    if max_position_delta != 0.0 or max_palette_delta != 0.0:
        raise ValueError(
            f"current UC semantic delta after exact sharing: positions={max_position_delta}, palette={max_palette_delta}"
        )

    result = {
        "schema": SCHEMA,
        "result": RESULT,
        "identity": {
            "technical_art_head": technical_art_head,
            "technical_art_parent_head": TECHNICAL_ART_PARENT_HEAD,
            "runtime_donor_head": RUNTIME_DONOR_HEAD,
            "uc_current_head": uc_head,
            "uc_game_pose_runtime_blob": uc_blob,
        },
        "control": {
            "bytes": len(control.bytes),
            "sha256": sha256_bytes(control.bytes),
            "accessors": len(control.document["accessors"]),
            "buffer_views": len(control.document["bufferViews"]),
        },
        "candidate": {
            "bytes": len(candidate.bytes),
            "sha256": sha256_bytes(candidate.bytes),
            "accessors": len(candidate.document["accessors"]),
            "buffer_views": len(candidate.document["bufferViews"]),
            "bilateral_release_scale_shared_accessor": left_scale,
        },
        "source_dense_sampling": {
            "sample_count": len(control.times),
            "sample_rate_hz": source_dense_hz,
            "duration_s": source_duration_s,
            "first_time_s": float(control.times[0]),
            "last_time_s": float(control.times[-1]),
        },
        "before_after": {
            "file_bytes_saved": len(control.bytes) - len(candidate.bytes),
            "file_percent_reduction": 100.0 * (len(control.bytes) - len(candidate.bytes)) / len(control.bytes),
            "binary_payload_bytes_removed": adoption["sharing"]["removed_binary_bytes"],
        },
        "runtime_donor_reproduction": donor,
        "current_uc_equivalence": {
            "sample_count": len(control.times),
            "vertices_per_sample": 184,
            "semantic_shape_equal": True,
            "maximum_position_delta_m": max_position_delta,
            "changed_position_samples": changed_position_samples,
            "maximum_skin_palette_component_delta": max_palette_delta,
            "changed_palette_samples": changed_palette_samples,
            "control_semantic_shape": control_shape,
            "candidate_semantic_shape": candidate_shape,
        },
        "negative_control": {
            "mutation": "one byte changed only in duplicate right release-scale payload before sharing",
            "rejected_fail_closed": negative_rejected,
        },
        "technical_art_adoption": adoption,
        "target_engine_receiver": "PENDING_SAME_WORKFLOW_GODOT_RECEIPT",
        "truth_boundary": {
            "runtime_donor_mechanism_reproduced_exactly": True,
            "technical_art_export_candidate_byte_identical_to_runtime_candidate": True,
            "current_uc_position_and_skin_palette_equivalence": "EXACT_ALL_321_KEYS",
            "uc_modified": False,
            "runtime_policy_transferred": False,
            "rendered_frame_equivalence": "NOT_CLAIMED_BY_THIS_PYTHON_RECEIPT",
            "target_device_performance": "NOT_EVALUATED",
            "tangent_or_tangent_space": "NOT_EVALUATED",
            "art_or_qa_acceptance": False,
            "canon": False,
            "production_readiness": False,
        },
    }
    result["result_sha256"] = canonical_sha(result)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "uc-control-description.json").write_text(
        json.dumps(control_description, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "uc-candidate-description.json").write_text(
        json.dumps(candidate_description, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for name, value in (
        ("exact-technical-art-head.txt", technical_art_head),
        ("exact-runtime-donor-head.txt", RUNTIME_DONOR_HEAD),
        ("exact-uc-head.txt", uc_head),
    ):
        (out / name).write_text(value + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="lookdev-proof/generated/review006-accessor-sharing-adoption")
    parser.add_argument("--uc-root", required=True)
    parser.add_argument("--runtime-donor-dir", required=True)
    args = parser.parse_args()
    build_evidence(Path(args.out), Path(args.uc_root).resolve(), Path(args.runtime_donor_dir).resolve())


if __name__ == "__main__":
    main()
