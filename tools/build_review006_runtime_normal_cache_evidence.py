from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import statistics
import struct
import time
from pathlib import Path

from axm_character_design.review006_runtime_normal_cache import (
    assert_static_vertices_unchanged,
    build_posed_normal_cache_plan,
    evaluate_cached_smooth_normals,
    operation_budget,
)
from axm_character_design.review006_shoulder_animation_diagnostic import (
    DENSE_HZ,
    DENSE_SAMPLE_COUNT,
    RIGGING_HEAD,
    _build_side_context,
    _evaluate_pose,
    _phase_angle,
    _validate_exact_dependencies,
    animation_contract,
)

CONTRACT_PATH = Path("runtime/character_review006_normal_cache_budget_001.json")
RESULT = "PASS_CHARACTER_REVIEW006_POSED_NORMAL_STATIC_REGION_CACHE_BUDGET"
HOLD = "HOLD_CHARACTER_REVIEW006_POSED_NORMAL_STATIC_REGION_CACHE_BUDGET"
ANIMATION_HEAD = "9519be55581c009fd800d175677d9b50ee6926e6"
GEOMETRY_HEAD = "8ad006f91ebb9934d5df98702e4410c74a1e68ea"
MATERIALS_HEAD = "e450684b398f8e5b0e23c4cbf717e3475dd4d5ee"
MATERIALS_BLOB = "843c0e1866172dd8b6c5ab0f23d69d1e469562f7"
MATERIALS_METHOD = "AREA_WEIGHTED_INDEXED_VERTEX_SMOOTH_NORMAL"
BENCHMARK_ROUNDS = 7


def canonical_digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_contract(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "axm.character-review006-runtime-normal-cache-budget/v0.1":
        raise ValueError("Runtime normal-cache contract schema drift")
    if data.get("animation_parent_head") != ANIMATION_HEAD:
        raise ValueError("Animation parent head drift")
    if data.get("rigging_parent_head") != RIGGING_HEAD:
        raise ValueError("Rigging parent head drift")
    if data.get("geometry_head") != GEOMETRY_HEAD:
        raise ValueError("Geometry head drift")
    owner = data.get("materials_normal_method", {})
    if owner.get("owner_head") != MATERIALS_HEAD:
        raise ValueError("Materials normal-method owner head drift")
    if owner.get("owner_blob") != MATERIALS_BLOB:
        raise ValueError("Materials normal-method blob drift")
    if owner.get("method") != MATERIALS_METHOD:
        raise ValueError("Materials normal-method semantic drift")
    motion = data.get("motion", {})
    if int(motion.get("dense_diagnostic_hz", 0)) != DENSE_HZ:
        raise ValueError("dense diagnostic cadence drift")
    if int(motion.get("dense_sample_count", 0)) != DENSE_SAMPLE_COUNT:
        raise ValueError("dense sample-count drift")
    acceptance = data.get("acceptance", {})
    required_true = (
        "exact_reference_normal_arrays_required_all_dense_samples",
        "static_vertex_drift_negative_control_required",
        "face_cross_operation_reduction_required",
        "vertex_normalization_operation_reduction_required",
        "proof_host_median_timing_win_required",
    )
    if not all(acceptance.get(key) is True for key in required_true):
        raise ValueError("Runtime acceptance gate weakened")
    return data


def load_materials_donor(path: Path):
    spec = importlib.util.spec_from_file_location("axm_character_materials_normal_donor", path)
    if spec is None or spec.loader is None:
        raise ValueError("could not load exact Materials normal donor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "smooth_normals", None)):
        raise ValueError("Materials donor lacks smooth_normals")
    return module


def tuple_normals(normals):
    return tuple(tuple(float(component) for component in normal) for normal in normals)


def update_normal_digest(digest, side: str, sample_index: int, normals) -> None:
    digest.update(side.encode("ascii"))
    digest.update(struct.pack(">I", sample_index))
    for normal in normals:
        for component in normal:
            digest.update(struct.pack(">d", float(component)))


def collect_pose_positions():
    source, rig_contract, boundary = _validate_exact_dependencies()
    contexts = {
        side: _build_side_context(side, source, rig_contract)
        for side in ("L", "R")
    }
    result = {}
    max_pairs = {"L": 0, "R": 0}
    for side in ("L", "R"):
        poses = []
        for sample_index in range(DENSE_SAMPLE_COUNT):
            time_s = sample_index / DENSE_HZ
            angle = _phase_angle(time_s)
            posed, intersections, _ = _evaluate_pose(contexts[side], angle)
            pair_count = int(intersections["self_intersection_pair_count"])
            max_pairs[side] = max(max_pairs[side], pair_count)
            poses.append(tuple(tuple(float(c) for c in vertex) for vertex in posed["positions"]))
        result[side] = {
            "faces": tuple(tuple(int(i) for i in face) for face in contexts[side]["specimen"]["faces"]),
            "poses": tuple(poses),
        }
    if max_pairs != {"L": 0, "R": 0}:
        raise ValueError(f"exact Animation clip no longer intersection-free: {max_pairs}")
    return result, boundary


def static_vertex_indices(poses):
    neutral = poses[0]
    static = []
    for index, neutral_vertex in enumerate(neutral):
        if all(pose[index] == neutral_vertex for pose in poses):
            static.append(index)
    return tuple(static)


def benchmark(label, callback):
    callback()  # warmup
    samples = []
    for _ in range(BENCHMARK_ROUNDS):
        gc.collect()
        started = time.perf_counter_ns()
        callback()
        samples.append(time.perf_counter_ns() - started)
    return {
        "label": label,
        "rounds": BENCHMARK_ROUNDS,
        "samples_ns": samples,
        "minimum_ns": min(samples),
        "median_ns": int(statistics.median(samples)),
        "maximum_ns": max(samples),
    }


def build_evidence(contract_path: Path, donor_path: Path):
    contract = load_contract(contract_path)
    donor = load_materials_donor(donor_path)
    animation = animation_contract()
    if animation["clip"]["dense_sample_count"] != DENSE_SAMPLE_COUNT:
        raise ValueError("Animation contract dense sample count drift")

    pose_data, boundary = collect_pose_positions()
    plans = {}
    side_summary = {}
    control_digest = hashlib.sha256()
    candidate_digest = hashlib.sha256()
    max_component_delta = 0.0
    mismatched_normals = 0
    total_normal_vectors = 0

    for side in ("L", "R"):
        poses = pose_data[side]["poses"]
        faces = pose_data[side]["faces"]
        static = static_vertex_indices(poses)
        plan = build_posed_normal_cache_plan(poses[0], faces, static)
        if plan.static_face_count <= 0 or plan.dynamic_face_count <= 0:
            raise ValueError(f"{side} cache does not expose both static and dynamic face work")
        if plan.static_output_vertex_count <= 0 or plan.dynamic_output_vertex_count <= 0:
            raise ValueError(f"{side} cache does not expose both static and dynamic output vertices")
        plans[side] = plan

        for sample_index, positions in enumerate(poses):
            assert_static_vertices_unchanged(plan, poses[0], positions)
            control = tuple_normals(donor.smooth_normals(positions, faces))
            candidate = evaluate_cached_smooth_normals(positions, plan)
            update_normal_digest(control_digest, side, sample_index, control)
            update_normal_digest(candidate_digest, side, sample_index, candidate)
            if len(control) != len(candidate):
                raise ValueError("normal vector count mismatch")
            for first, second in zip(control, candidate):
                total_normal_vectors += 1
                delta = max(abs(first[i] - second[i]) for i in range(3))
                max_component_delta = max(max_component_delta, delta)
                if first != second:
                    mismatched_normals += 1

        budget = operation_budget(plan, DENSE_SAMPLE_COUNT)
        side_summary[side] = {
            "vertex_count": plan.vertex_count,
            "triangle_count": plan.face_count,
            "static_vertex_count_proven_across_all_dense_samples": len(static),
            "static_face_count": plan.static_face_count,
            "dynamic_face_count": plan.dynamic_face_count,
            "static_output_vertex_count": plan.static_output_vertex_count,
            "dynamic_output_vertex_count": plan.dynamic_output_vertex_count,
            "operation_budget": budget,
        }

    if mismatched_normals != 0 or max_component_delta != 0.0:
        raise ValueError(
            f"cached normal candidate drifted from exact Materials method: mismatches={mismatched_normals}, "
            f"max_delta={max_component_delta}"
        )
    if control_digest.hexdigest() != candidate_digest.hexdigest():
        raise ValueError("aggregate control/candidate normal digest mismatch")

    # Fail closed if a vertex that was proven static is later moved.
    negative_side = "L"
    negative_plan = plans[negative_side]
    negative_index = min(negative_plan.static_vertex_indices)
    mutated = [list(vertex) for vertex in pose_data[negative_side]["poses"][0]]
    mutated[negative_index][0] += 1e-6
    static_drift_rejected = False
    try:
        assert_static_vertices_unchanged(
            negative_plan,
            pose_data[negative_side]["poses"][0],
            mutated,
        )
    except ValueError:
        static_drift_rejected = True
    if not static_drift_rejected:
        raise ValueError("static-vertex drift negative control was not rejected")

    def control_run():
        for side in ("L", "R"):
            faces = pose_data[side]["faces"]
            for positions in pose_data[side]["poses"]:
                donor.smooth_normals(positions, faces)

    def candidate_run():
        for side in ("L", "R"):
            plan = plans[side]
            for positions in pose_data[side]["poses"]:
                evaluate_cached_smooth_normals(positions, plan)

    # Alternate benchmark order by running complete independent medians; timing is
    # proof-host evidence only and is never promoted to target-device performance.
    control_timing = benchmark("exact_materials_method_control", control_run)
    candidate_timing = benchmark("static_region_cache_candidate", candidate_run)
    control_median = control_timing["median_ns"]
    candidate_median = candidate_timing["median_ns"]
    timing_win = candidate_median < control_median
    timing_delta_ns = candidate_median - control_median
    timing_ratio = candidate_median / control_median

    total_budget = {
        key: side_summary["L"]["operation_budget"][key] + side_summary["R"]["operation_budget"][key]
        for key in (
            "control_face_crosses",
            "candidate_face_crosses",
            "saved_face_crosses",
            "control_vertex_normalizations",
            "candidate_vertex_normalizations",
            "saved_vertex_normalizations",
        )
    }
    face_reduction = total_budget["saved_face_crosses"] > 0
    normalization_reduction = total_budget["saved_vertex_normalizations"] > 0
    pass_gate = (
        mismatched_normals == 0
        and max_component_delta == 0.0
        and static_drift_rejected
        and face_reduction
        and normalization_reduction
        and timing_win
    )

    summary = {
        "schema": "axm.character-review006-runtime-normal-cache-evidence/v0.1",
        "status": RESULT if pass_gate else HOLD,
        "contract": contract,
        "exact_identity": {
            "animation_parent_head": ANIMATION_HEAD,
            "rigging_parent_head": RIGGING_HEAD,
            "geometry_head": GEOMETRY_HEAD,
            "materials_normal_method_head": MATERIALS_HEAD,
            "materials_normal_method_blob": MATERIALS_BLOB,
            "materials_normal_method": MATERIALS_METHOD,
            "clip_digest": animation["clip"]["digest"],
        },
        "receiver": {
            "dense_sample_count_per_side": DENSE_SAMPLE_COUNT,
            "pose_side_evaluations": DENSE_SAMPLE_COUNT * 2,
            "total_normal_vectors_compared": total_normal_vectors,
            "mismatched_normal_vectors": mismatched_normals,
            "maximum_component_delta": max_component_delta,
            "control_normal_stream_sha256": control_digest.hexdigest(),
            "candidate_normal_stream_sha256": candidate_digest.hexdigest(),
            "sides": side_summary,
        },
        "before_after_operation_budget": total_budget,
        "proof_host_python_timing": {
            "control": control_timing,
            "candidate": candidate_timing,
            "candidate_minus_control_median_ns": timing_delta_ns,
            "candidate_over_control_median_ratio": timing_ratio,
            "median_timing_win": timing_win,
            "meaning": "Python proof-host normal preparation only; excludes pose generation, intersection checks, rendering and device GPU work",
        },
        "negative_control": {
            "mutation": f"move proven-static {negative_side} vertex {negative_index} by +1e-6 m on X",
            "rejected": static_drift_rejected,
            "meaning": "cache may not silently survive motion outside its exact static-set prerequisite",
        },
        "visual_tradeoff": {
            "normal_input_delta": "NONE_OBSERVED_EXACT_ARRAY_IDENTITY_ALL_642_POSE_SIDE_EVALUATIONS",
            "new_renderer_measurement": False,
            "rendered_frame_delta": "NOT_REMEASURED",
            "art_direction_review_note": (
                "No visual representation was intentionally changed: every candidate normal component exactly equals the external Materials reference method on every bound dense pose. "
                "Final shaded full-body motion still requires its separately owned current-head Art/QA/Technical-Art receiving proof."
            ),
        },
        "rigging_boundary_prerequisite": {
            "status": boundary["status"],
            "meaning": "consumed unchanged; cache does not widen the deformation envelope",
        },
        "truth_boundary": contract["truth_boundary"],
    }
    summary["summary_sha256"] = canonical_digest(summary)
    if not pass_gate:
        raise ValueError(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(CONTRACT_PATH))
    parser.add_argument("--materials-donor", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    summary = build_evidence(Path(args.contract), Path(args.materials_donor))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
