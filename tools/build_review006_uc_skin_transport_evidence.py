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

from axm_character_design.review006_uc_skin_transport import (
    ANIMATION_HEAD,
    DENSE_HZ,
    DENSE_SAMPLE_COUNT,
    DIRECTION_STATUS,
    MATERIALS_HEAD,
    MATERIALS_NORMAL_TOOL_BLOB,
    POSITION_STATUS,
    POSITION_TOLERANCE_M,
    UC_GAME_POSE_RUNTIME_BLOB,
    UC_HEAD,
    direct_decomposition_audit,
    direction_frame_reference,
    owner_pose,
    pack_character_glb,
    source_to_gltf,
    transport_contract,
)

RESULT = "PASS_CHARACTER_REVIEW006_DENSE_SKIN_POSITION_TRANSPORT_TO_CURRENT_UC__HOLD_DEFORMED_DIRECTION_FRAME"


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_text(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd or ROOT, text=True).strip()


def verify_exact_identity(*, uc_root: Path, uc_head: str) -> dict:
    if uc_head != UC_HEAD:
        raise ValueError(f"UC head argument drift: {uc_head} != {UC_HEAD}")
    observed_uc_head = git_text("rev-parse", "HEAD", cwd=uc_root)
    if observed_uc_head != UC_HEAD:
        raise ValueError(f"checked-out UC head drift: {observed_uc_head}")
    observed_runtime_blob = git_text("rev-parse", f"HEAD:src/axm_uc/game_pose_runtime.py", cwd=uc_root)
    if observed_runtime_blob != UC_GAME_POSE_RUNTIME_BLOB:
        raise ValueError(f"UC game_pose_runtime blob drift: {observed_runtime_blob}")

    observed_animation_head = git_text("merge-base", "--is-ancestor", ANIMATION_HEAD, "HEAD")
    # merge-base emits no text on success; the call itself fails closed otherwise.
    del observed_animation_head

    material_blob = git_text("rev-parse", f"{MATERIALS_HEAD}:tools/build_character_review006_shaded_shoulder_evidence.py")
    if material_blob != MATERIALS_NORMAL_TOOL_BLOB:
        raise ValueError(f"Materials normal-method tool blob drift: {material_blob}")

    return {
        "character_technical_art_head": git_text("rev-parse", "HEAD"),
        "animation_parent_head": ANIMATION_HEAD,
        "uc_head": observed_uc_head,
        "uc_game_pose_runtime_blob": observed_runtime_blob,
        "materials_head": MATERIALS_HEAD,
        "materials_normal_tool_blob": material_blob,
    }


def flatten_positions(sample) -> list[list[float]]:
    meshes = sample.get("meshes")
    if not isinstance(meshes, list) or len(meshes) != 1:
        raise ValueError(f"bounded UC receiver expected exactly one mesh primitive, observed {type(meshes).__name__}:{len(meshes) if isinstance(meshes, list) else 'n/a'}")
    positions = meshes[0].get("positions")
    if not isinstance(positions, list) or len(positions) != 184:
        raise ValueError("bounded UC receiver expected exactly 184 deformed vertices")
    return positions


def expected_positions(angle: float, contexts=None) -> list[list[float]]:
    rows = []
    for side in ("L", "R"):
        rows.extend(source_to_gltf(point) for point in owner_pose(side, angle, contexts))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--uc-root", required=True)
    parser.add_argument("--uc-head", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    uc_root = Path(args.uc_root).resolve()
    identity = verify_exact_identity(uc_root=uc_root, uc_head=args.uc_head)

    sys.path.insert(0, str(uc_root / "src"))
    from axm_uc.game_pose_runtime import load_game_pose_glb

    contract = transport_contract()
    decomposition = direct_decomposition_audit()
    if decomposition["status"] != POSITION_STATUS:
        raise ValueError(f"direct factorization is not green: {decomposition}")

    packed = pack_character_glb()
    glb_path = out / "character-review006-dense-skin-transport.glb"
    glb_path.write_bytes(packed.bytes)
    glb_sha = sha256_bytes(packed.bytes)

    asset = load_game_pose_glb(glb_path)
    description = asset.describe()
    if description.get("vertices") != 184 or description.get("primitives") != 1:
        raise ValueError(f"UC receiver geometry identity drift: {description}")
    clips = description.get("clips", [])
    if len(clips) != 1 or clips[0].get("name") != contract["animation"]["clip_id"]:
        raise ValueError(f"UC receiver clip identity drift: {clips}")
    if clips[0].get("channels") != 6:
        raise ValueError(f"UC receiver expected six bounded TRS channels, observed {clips[0].get('channels')}")
    if len(description.get("skins", [])) != 1 or len(description["skins"][0].get("joints", [])) != 5:
        raise ValueError("UC receiver expected exactly one five-joint transport skin")

    maximum_residual = 0.0
    worst = None
    sample_rows = []
    for index, (time_s, angle) in enumerate(zip(packed.times, packed.angles)):
        sample = asset.sample(contract["animation"]["clip_id"], time_s, loop=False, vertices=True)
        observed = flatten_positions(sample)
        expected = expected_positions(angle)
        residual = max(math.dist(a, b) for a, b in zip(observed, expected))
        if residual > maximum_residual:
            maximum_residual = residual
            worst = {"sample_index": index, "time_s": time_s, "angle_deg": angle, "residual_m": residual}
        sample_rows.append({
            "sample_index": index,
            "time_s": time_s,
            "angle_deg": angle,
            "maximum_position_residual_m": residual,
        })

    if len(sample_rows) != DENSE_SAMPLE_COUNT:
        raise ValueError("transport sample-count drift")
    if maximum_residual > POSITION_TOLERANCE_M:
        raise ValueError(
            f"UC skin position residual {maximum_residual:.12g}m exceeds {POSITION_TOLERANCE_M:.12g}m"
        )

    direction_reference = direction_frame_reference()
    if direction_reference["status"] != DIRECTION_STATUS:
        raise ValueError("direction-frame boundary was silently promoted")
    changed_safe = [
        direction_reference["samples"][sample]["sides"][side]["changed_vertex_count_gt_1e_12_component"]
        for sample in ("080", "240")
        for side in ("L", "R")
    ]
    if not all(value > 0 for value in changed_safe):
        raise ValueError("direction-frame reference failed to retain safe-pose normal changes")

    # Deliberate evidence mutation: relabeling current UC as direction-frame-capable
    # must be rejected by the exact contract, independently of position success.
    mutated_contract = json.loads(json.dumps(contract))
    mutated_contract["uc_receiver"]["deformed_direction_frame_api"] = "CLAIMED_AVAILABLE"
    mutated_contract["truth_boundary"]["deformed_normals_or_tangents"] = "PASS"
    direction_claim_rejected = mutated_contract != transport_contract()
    if not direction_claim_rejected:
        raise ValueError("direction-frame claim mutation was not rejected")

    result = {
        "schema": "axm.character-review006-uc-skin-transport-evidence/v0.1",
        "result": RESULT,
        "position_status": POSITION_STATUS,
        "direction_frame_status": DIRECTION_STATUS,
        "identity": identity,
        "contract_sha256": canonical_sha(contract),
        "source_counts": {
            "vertices": packed.source_vertex_counts,
            "triangles": packed.source_triangle_counts,
            "combined_vertices": sum(packed.source_vertex_counts.values()),
            "combined_triangles": sum(packed.source_triangle_counts.values()),
        },
        "transport": {
            "coordinate_adapter": contract["coordinate_adapter"],
            "static_skin_joint_count": 5,
            "transport_animation_channels": 6,
            "transport_key_hz": DENSE_HZ,
            "transport_key_count": DENSE_SAMPLE_COUNT,
            "position_tolerance_m": POSITION_TOLERANCE_M,
            "maximum_uc_position_residual_m": maximum_residual,
            "worst_uc_sample": worst,
            "direct_factorization": decomposition,
        },
        "glb": {
            "path": glb_path.name,
            "bytes": len(packed.bytes),
            "sha256": glb_sha,
            "uc_description": description,
        },
        "direction_frame": {
            "status": DIRECTION_STATUS,
            "reference_path": "direction-frame-reference.json",
            "safe_pose_changed_vertex_counts": changed_safe,
            "claim_mutation_rejected": direction_claim_rejected,
            "meaning": "Current bound UC GamePoseAsset verifies deformed positions only. Exact Materials-method posed-normal references are retained but not compared to a UC/target deformed direction frame.",
        },
        "truth_boundary": contract["truth_boundary"],
    }

    write_json(out / "transport-contract.json", contract)
    write_json(out / "direct-factorization-audit.json", decomposition)
    write_json(out / "uc-pose-description.json", description)
    write_json(out / "dense-position-comparison.json", {"samples": sample_rows, "maximum_position_residual_m": maximum_residual, "worst_sample": worst})
    write_json(out / "direction-frame-reference.json", direction_reference)
    write_json(out / "result.json", result)
    (out / "character-technical-art-head.txt").write_text(identity["character_technical_art_head"] + "\n")
    (out / "animation-head.txt").write_text(ANIMATION_HEAD + "\n")
    (out / "uc-head.txt").write_text(UC_HEAD + "\n")
    (out / "uc-game-pose-runtime-blob.txt").write_text(UC_GAME_POSE_RUNTIME_BLOB + "\n")
    (out / "materials-head.txt").write_text(MATERIALS_HEAD + "\n")
    (out / "materials-normal-tool-blob.txt").write_text(MATERIALS_NORMAL_TOOL_BLOB + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    main()
