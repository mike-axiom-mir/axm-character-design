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
    _static_skin_rows,
    direct_decomposition_audit,
    direction_frame_reference,
    owner_pose,
    pack_character_glb,
    side_contexts,
    source_to_gltf,
    transport_contract,
)

UC_CURRENT_HEAD = "fed35116c1aabe54789f1197b7b2423b3b516169"
RIGGING_FRAME_HEAD = "a218b2cf2727482a78db8ab21afcf1bb72637bcc"
RIGGING_FRAME_BLOB = "57c43aea818f293274a94457252bf87e20b98897"
RIGGING_FRAME_STATUS = "PASS_CHARACTER_REVIEW006_RIG_DEFORMATION_GRADIENT_FRAME_REFERENCE__STRUCTURAL_BOUNDARY_UNCHANGED"
PALETTE_FRAME_STATUS = "PASS_CHARACTER_REVIEW006_RIG_GRADIENT_TO_CURRENT_UC_PALETTE_DIRECTION_FRAME_BRIDGE"
RESULT = "PASS_CHARACTER_REVIEW006_DENSE_SKIN_POSITION_AND_RIG_GRADIENT_PALETTE_TRANSPORT_TO_CURRENT_UC__HOLD_TARGET_ENGINE_DIRECTION_FRAME"
FRAME_TOLERANCE = 5e-6
FRAME_MUTATION_MIN_DELTA = 1e-5


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_text(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd or ROOT, text=True).strip()


def git_check(*args: str, cwd: Path | None = None) -> None:
    subprocess.check_call(["git", *args], cwd=cwd or ROOT)


def verify_exact_identity(*, uc_root: Path, uc_head: str) -> dict:
    if uc_head != UC_CURRENT_HEAD:
        raise ValueError(f"UC current-head argument drift: {uc_head} != {UC_CURRENT_HEAD}")
    observed_uc_head = git_text("rev-parse", "HEAD", cwd=uc_root)
    if observed_uc_head != UC_CURRENT_HEAD:
        raise ValueError(f"checked-out current UC head drift: {observed_uc_head}")
    git_check("merge-base", "--is-ancestor", UC_HEAD, UC_CURRENT_HEAD, cwd=uc_root)
    observed_runtime_blob = git_text("rev-parse", f"HEAD:src/axm_uc/game_pose_runtime.py", cwd=uc_root)
    if observed_runtime_blob != UC_GAME_POSE_RUNTIME_BLOB:
        raise ValueError(f"UC game_pose_runtime blob drift: {observed_runtime_blob}")

    git_check("merge-base", "--is-ancestor", ANIMATION_HEAD, "HEAD")

    material_blob = git_text("rev-parse", f"{MATERIALS_HEAD}:tools/build_character_review006_shaded_shoulder_evidence.py")
    if material_blob != MATERIALS_NORMAL_TOOL_BLOB:
        raise ValueError(f"Materials normal-method tool blob drift: {material_blob}")

    rigging_blob = git_text(
        "rev-parse",
        f"{RIGGING_FRAME_HEAD}:src/axm_character_design/review006_shoulder_deformation_gradient_frame.py",
    )
    if rigging_blob != RIGGING_FRAME_BLOB:
        raise ValueError(f"Rigging frame-owner blob drift: {rigging_blob}")

    return {
        "character_technical_art_head": git_text("rev-parse", "HEAD"),
        "animation_parent_head": ANIMATION_HEAD,
        "rigging_frame_head": RIGGING_FRAME_HEAD,
        "rigging_frame_blob": rigging_blob,
        "uc_historical_transport_head": UC_HEAD,
        "uc_current_head": observed_uc_head,
        "uc_game_pose_runtime_blob": observed_runtime_blob,
        "uc_pose_runtime_unchanged_across_rebind": True,
        "materials_head": MATERIALS_HEAD,
        "materials_normal_tool_blob": material_blob,
    }


def flatten_positions(sample) -> list[list[float]]:
    meshes = sample.get("meshes")
    if not isinstance(meshes, list) or len(meshes) != 1:
        raise ValueError(
            "bounded UC receiver expected exactly one mesh primitive, observed "
            f"{type(meshes).__name__}:{len(meshes) if isinstance(meshes, list) else 'n/a'}"
        )
    positions = meshes[0].get("positions")
    if not isinstance(positions, list) or len(positions) != 184:
        raise ValueError("bounded UC receiver expected exactly 184 deformed vertices")
    return positions


def expected_positions(angle: float, contexts=None) -> list[list[float]]:
    rows = []
    for side in ("L", "R"):
        rows.extend(source_to_gltf(point) for point in owner_pose(side, angle, contexts))
    return rows


def _mat3_from4(matrix):
    if not isinstance(matrix, list) or len(matrix) != 16:
        raise ValueError("UC skin palette matrix must contain 16 values")
    return [[float(matrix[r * 4 + c]) for c in range(3)] for r in range(3)]


def _mat3_identity():
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _mat3_add(a, b):
    return [[float(a[r][c]) + float(b[r][c]) for c in range(3)] for r in range(3)]


def _mat3_scale(a, scalar):
    return [[float(a[r][c]) * float(scalar) for c in range(3)] for r in range(3)]


def _mat3_mul(a, b):
    return [[sum(float(a[r][k]) * float(b[k][c]) for k in range(3)) for c in range(3)] for r in range(3)]


def _mat3_transpose(a):
    return [[float(a[c][r]) for c in range(3)] for r in range(3)]


def _mat3_det(a):
    return (
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    )


def _mat3_inverse(a):
    determinant = _mat3_det(a)
    if not math.isfinite(determinant) or abs(determinant) <= 1e-12:
        raise ValueError("transport direction-frame matrix is singular")
    aa, b, c = a[0]
    d, e, f = a[1]
    g, h, i = a[2]
    adjugate = [
        [e * i - f * h, c * h - b * i, b * f - c * e],
        [f * g - d * i, aa * i - c * g, c * d - aa * f],
        [d * h - e * g, b * g - aa * h, aa * e - b * d],
    ]
    return _mat3_scale(adjugate, 1.0 / determinant)


def _mat3_inverse_transpose(a):
    return _mat3_transpose(_mat3_inverse(a))


def _mat3_delta(a, b):
    return max(abs(float(a[r][c]) - float(b[r][c])) for r in range(3) for c in range(3))


def _source_frame_to_gltf(matrix):
    # source_to_gltf is the proper rotation Q: (x,y,z)->(x,z,-y).
    q = [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]]
    return _mat3_mul(_mat3_mul(q, matrix), _mat3_transpose(q))


def _weighted_palette_linear(palette, joints, weights, *, disable_nonroot=False):
    result = [[0.0, 0.0, 0.0] for _ in range(3)]
    identity = _mat3_identity()
    for joint, weight in zip(joints, weights):
        if weight <= 0.0:
            continue
        linear = identity if disable_nonroot and int(joint) != 0 else _mat3_from4(palette[int(joint)])
        result = _mat3_add(result, _mat3_scale(linear, weight))
    return result


def load_rigging_reference(path: Path) -> dict:
    row = json.loads(path.read_text(encoding="utf-8"))
    if row.get("status") != RIGGING_FRAME_STATUS:
        raise ValueError(f"Rigging frame reference is not green: {row.get('status')}")
    exact = row.get("exact_identity", {})
    if exact.get("profile_digest") != transport_contract()["rigging"]["profile_digest"]:
        raise ValueError("Rigging frame reference profile identity differs from transport owner")
    return row


def compare_uc_palette_direction_frames(asset, packed, rigging_reference) -> dict:
    contexts = side_contexts()
    oracle_rows = {}
    for row in rigging_reference["deformation_gradient_reference"]["rows"]:
        key = (row["side"], round(float(row["angle_deg"]), 8), row["group"])
        oracle_rows[key] = row

    rows = []
    max_gradient_delta = 0.0
    max_normal_delta = 0.0
    mutation_max_delta = 0.0
    sample_map = {80: -30.0, 160: 0.0, 240: 30.0}

    for sample_index, expected_angle in sample_map.items():
        time_s = packed.times[sample_index]
        actual_angle = packed.angles[sample_index]
        if abs(actual_angle - expected_angle) > 1e-9:
            raise ValueError(f"dense animation extrema drift at {sample_index}: {actual_angle}")
        sample = asset.sample(transport_contract()["animation"]["clip_id"], time_s, loop=False, vertices=False)
        palettes = sample.get("skin_world_matrices")
        if not isinstance(palettes, list) or len(palettes) != 1 or len(palettes[0]) != 5:
            raise ValueError("current UC pose receiver did not expose the exact five-joint skin palette")
        palette = palettes[0]

        for side in ("L", "R"):
            context = contexts[side]
            joint_rows, weight_rows = _static_skin_rows(side, context)
            for group, indexes in context["layout"]["groups"].items():
                if not indexes:
                    raise ValueError(f"empty Rigging group: {side}/{group}")
                first = int(indexes[0])
                expected_joint_row = joint_rows[first]
                expected_weight_row = weight_rows[first]
                for index in indexes:
                    if joint_rows[int(index)] != expected_joint_row or weight_rows[int(index)] != expected_weight_row:
                        raise ValueError(f"Technical Art static skin rows vary inside Rigging group {side}/{group}")

                observed_gradient = _weighted_palette_linear(palette, expected_joint_row, expected_weight_row)
                oracle = oracle_rows.get((side, round(expected_angle, 8), group))
                if oracle is None:
                    raise ValueError(f"Rigging owner oracle missing row {side}/{expected_angle}/{group}")
                expected_gradient = _source_frame_to_gltf(oracle["gradient"])
                gradient_delta = _mat3_delta(observed_gradient, expected_gradient)
                observed_normal = _mat3_inverse_transpose(observed_gradient)
                expected_normal = _source_frame_to_gltf(oracle["normal_matrix"])
                normal_delta = _mat3_delta(observed_normal, expected_normal)
                max_gradient_delta = max(max_gradient_delta, gradient_delta)
                max_normal_delta = max(max_normal_delta, normal_delta)

                mutation_delta = 0.0
                if group == "proximal" and expected_angle != 0.0:
                    mutated_gradient = _weighted_palette_linear(
                        palette,
                        expected_joint_row,
                        expected_weight_row,
                        disable_nonroot=True,
                    )
                    mutation_delta = _mat3_delta(mutated_gradient, expected_gradient)
                    mutation_max_delta = max(mutation_max_delta, mutation_delta)

                rows.append({
                    "sample_index": sample_index,
                    "time_s": time_s,
                    "angle_deg": expected_angle,
                    "side": side,
                    "group": group,
                    "gradient_max_component_delta": gradient_delta,
                    "normal_matrix_max_component_delta": normal_delta,
                    "gradient_determinant": _mat3_det(observed_gradient),
                    "helper_disabled_gradient_delta": mutation_delta,
                })

    pass_gate = (
        max_gradient_delta <= FRAME_TOLERANCE
        and max_normal_delta <= FRAME_TOLERANCE
        and mutation_max_delta >= FRAME_MUTATION_MIN_DELTA
    )
    if not pass_gate:
        raise ValueError(
            "UC palette direction-frame bridge failed: "
            f"gradient={max_gradient_delta} normal={max_normal_delta} mutation={mutation_max_delta}"
        )
    return {
        "schema": "axm.character-review006-uc-palette-direction-frame-bridge/v0.1",
        "status": PALETTE_FRAME_STATUS,
        "owner_reference": {
            "rigging_head": RIGGING_FRAME_HEAD,
            "rigging_frame_blob": RIGGING_FRAME_BLOB,
            "owner_map": "D=(1-w)I+wR(theta)",
            "owner_normal_map": "inverse_transpose(D)",
        },
        "receiver": {
            "uc_head": UC_CURRENT_HEAD,
            "uc_pose_runtime_blob": UC_GAME_POSE_RUNTIME_BLOB,
            "api_consumed": "GamePoseAsset.sample(...).skin_world_matrices",
            "uc_product_modified": False,
            "character_semantics_added_to_uc": False,
        },
        "comparison": {
            "sample_indices": sorted(sample_map),
            "angles_deg": [sample_map[index] for index in sorted(sample_map)],
            "row_count": len(rows),
            "matrix_component_tolerance": FRAME_TOLERANCE,
            "maximum_gradient_component_delta": max_gradient_delta,
            "maximum_inverse_transpose_normal_matrix_component_delta": max_normal_delta,
            "helper_disabled_minimum_required_delta": FRAME_MUTATION_MIN_DELTA,
            "helper_disabled_maximum_gradient_delta": mutation_max_delta,
            "helper_disabled_rejected": mutation_max_delta >= FRAME_MUTATION_MIN_DELTA,
            "rows": rows,
        },
        "truth_boundary": {
            "rig_local_affine_direction_frame_transport": "EVALUATED",
            "uc_direct_deformed_normal_or_tangent_api": "NOT_AVAILABLE",
            "final_vertex_normal_policy": "NOT_CLAIMED",
            "materials_pose_recomputed_smooth_normal_equivalence": "NOT_CLAIMED",
            "target_engine_direction_frame": "NOT_EVALUATED",
            "shaded_target_equivalence": "NOT_EVALUATED",
            "runtime_or_device_acceptance": "NOT_EVALUATED",
            "source_adoption_or_canon": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--uc-root", required=True)
    parser.add_argument("--uc-head", required=True)
    parser.add_argument("--rigging-reference", required=True)
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

    rigging_reference_path = Path(args.rigging_reference).resolve()
    rigging_reference = load_rigging_reference(rigging_reference_path)
    palette_frame = compare_uc_palette_direction_frames(asset, packed, rigging_reference)

    direction_reference = direction_frame_reference()
    if direction_reference["status"] != DIRECTION_STATUS:
        raise ValueError("direct UC deformed-normal boundary was silently promoted")
    changed_safe = [
        direction_reference["samples"][sample]["sides"][side]["changed_vertex_count_gt_1e_12_component"]
        for sample in ("080", "240")
        for side in ("L", "R")
    ]
    if not all(value > 0 for value in changed_safe):
        raise ValueError("direction-frame reference failed to retain safe-pose normal changes")

    mutated_contract = json.loads(json.dumps(contract))
    mutated_contract["uc_receiver"]["deformed_direction_frame_api"] = "CLAIMED_AVAILABLE"
    mutated_contract["truth_boundary"]["deformed_normals_or_tangents"] = "PASS"
    direction_claim_rejected = mutated_contract != transport_contract()
    if not direction_claim_rejected:
        raise ValueError("direct deformed-normal claim mutation was not rejected")

    result = {
        "schema": "axm.character-review006-uc-skin-transport-evidence/v0.2",
        "result": RESULT,
        "position_status": POSITION_STATUS,
        "palette_direction_frame_status": PALETTE_FRAME_STATUS,
        "direct_uc_deformed_normal_status": DIRECTION_STATUS,
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
            "palette_bridge_path": "uc-palette-direction-frame-bridge.json",
            "palette_bridge_status": palette_frame["status"],
            "materials_reference_path": "direction-frame-reference.json",
            "safe_pose_changed_vertex_counts": changed_safe,
            "direct_normal_claim_mutation_rejected": direction_claim_rejected,
            "meaning": (
                "Technical Art now proves the exact Rigging local affine gradient and inverse-transpose frame survive into "
                "the current UC-exposed skin palette at the three bounded clip extrema. UC still has no direct deformed "
                "normal/tangent API, Materials' pose-recomputed smooth-normal field is a separate semantic, and the real "
                "target-engine direction frame remains unproven."
            ),
        },
        "truth_boundary": {
            **contract["truth_boundary"],
            "rig_gradient_to_uc_skin_palette": "EVALUATED_PASS",
            "target_engine_direction_frame": "NOT_EVALUATED",
            "shaded_target_equivalence": "NOT_EVALUATED",
        },
    }

    write_json(out / "transport-contract.json", contract)
    write_json(out / "direct-factorization-audit.json", decomposition)
    write_json(out / "uc-pose-description.json", description)
    write_json(
        out / "dense-position-comparison.json",
        {"samples": sample_rows, "maximum_position_residual_m": maximum_residual, "worst_sample": worst},
    )
    write_json(out / "direction-frame-reference.json", direction_reference)
    write_json(out / "rigging-owner-deformation-gradient-reference.json", rigging_reference)
    write_json(out / "uc-palette-direction-frame-bridge.json", palette_frame)
    write_json(out / "result.json", result)
    (out / "character-technical-art-head.txt").write_text(identity["character_technical_art_head"] + "\n")
    (out / "animation-head.txt").write_text(ANIMATION_HEAD + "\n")
    (out / "rigging-frame-head.txt").write_text(RIGGING_FRAME_HEAD + "\n")
    (out / "rigging-frame-blob.txt").write_text(RIGGING_FRAME_BLOB + "\n")
    (out / "uc-historical-transport-head.txt").write_text(UC_HEAD + "\n")
    (out / "uc-current-head.txt").write_text(UC_CURRENT_HEAD + "\n")
    (out / "uc-game-pose-runtime-blob.txt").write_text(UC_GAME_POSE_RUNTIME_BLOB + "\n")
    (out / "materials-head.txt").write_text(MATERIALS_HEAD + "\n")
    (out / "materials-normal-tool-blob.txt").write_text(MATERIALS_NORMAL_TOOL_BLOB + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    main()
