from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from axm_character_design.review006_connected_geometry import build_opening_repair
from axm_character_design.review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    GEOMETRY_HEAD,
    STATUS as RIGGING_STATUS,
    audit_review006_rigging_rebind,
)

CONTRACT_PATH = Path("lookdev/character_review006_shaded_shoulder_review_001.json")
SCHEMA = "axm.character-review006-shaded-shoulder-payload/v0.1"
RESULT = "PASS_CHARACTER_REVIEW006_POSE_RECOMPUTED_SMOOTH_NORMAL_REVIEW_PAYLOAD"
RIGGING_PARENT_HEAD = "efa48c344f1b8c9e70c4c5dfdbf4a3031dacd777"
SAFE_POSES = (-40.0, 0.0, 36.0)
OUTSIDE_WITNESS = 37.0


def canonical_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def length(v):
    return math.sqrt(dot(v, v))


def normalize(v):
    n = length(v)
    if n <= 1e-15:
        raise ValueError("zero-length accumulated normal")
    return [c / n for c in v]


def smooth_normals(vertices, faces):
    accum = [[0.0, 0.0, 0.0] for _ in vertices]
    for face in faces:
        a, b, c = face
        e1 = sub(vertices[b], vertices[a])
        e2 = sub(vertices[c], vertices[a])
        n = cross(e1, e2)
        if length(n) <= 1e-15:
            raise ValueError("degenerate face in normal receiver")
        for idx in face:
            accum[idx][0] += n[0]
            accum[idx][1] += n[1]
            accum[idx][2] += n[2]
    return [normalize(v) for v in accum]


def normal_delta_summary(neutral, posed):
    angles = []
    changed = 0
    max_component_delta = 0.0
    for a, b in zip(neutral, posed):
        component_delta = max(abs(float(a[i]) - float(b[i])) for i in range(3))
        max_component_delta = max(max_component_delta, component_delta)
        d = max(-1.0, min(1.0, dot(a, b)))
        angle = math.degrees(math.acos(d))
        angles.append(angle)
        if component_delta > 1e-12:
            changed += 1
    return {
        "vertex_count": len(angles),
        "changed_vertex_count_gt_1e_12_component": changed,
        "maximum_component_delta": max_component_delta,
        "maximum_angle_delta_deg": max(angles) if angles else 0.0,
        "mean_angle_delta_deg": sum(angles) / len(angles) if angles else 0.0,
    }


def load_contract(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "axm.character-review006-shaded-shoulder-lookdev/v0.1":
        raise ValueError("lookdev contract schema drift")
    if data.get("rigging_parent_head") != RIGGING_PARENT_HEAD:
        raise ValueError("Rigging parent head drift")
    if data.get("source_sha256") != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("review006 source identity drift")
    if data.get("proof_mesh_sha256") != EXPECTED_REVIEW006_MESH_DIGEST:
        raise ValueError("review006 proof-mesh identity drift")
    if data.get("geometry_head") != GEOMETRY_HEAD:
        raise ValueError("Geometry head drift")
    if data.get("topology_digests") != EXPECTED_TOPOLOGY_DIGESTS:
        raise ValueError("topology digest drift")
    if data.get("rig_profile_digest") != EXPECTED_PROFILE_DIGEST:
        raise ValueError("Rigging profile digest drift")
    if tuple(float(x) for x in data.get("review_poses_deg", [])) != SAFE_POSES:
        raise ValueError("review pose set drift")
    if float(data.get("outside_envelope_witness_deg")) != OUTSIDE_WITNESS:
        raise ValueError("outside-envelope witness drift")
    material = data.get("material", {})
    if material.get("semantic") != "neutral_skin_response_review_only":
        raise ValueError("review material semantic drift")
    if float(material.get("metallic", -1)) != 0.0 or abs(float(material.get("roughness", -1)) - 0.62) > 1e-12:
        raise ValueError("bounded neutral review material drift")
    return data


def candidate_rows(audit, side):
    return {float(row["angle_deg"]): row for row in audit["results"][side]["candidate"]}


def build_payload(contract_path: Path = CONTRACT_PATH):
    contract = load_contract(contract_path)
    donor = audit_review006_rigging_rebind()
    if donor.get("status") != RIGGING_STATUS:
        raise ValueError(f"Rigging donor status drift: {donor.get('status')}")
    identity = donor["exact_identity"]
    if identity["review006_source_digest"] != EXPECTED_REVIEW006_SOURCE_DIGEST:
        raise ValueError("donor source identity mismatch")
    if identity["review006_proof_mesh_digest"] != EXPECTED_REVIEW006_MESH_DIGEST:
        raise ValueError("donor proof mesh identity mismatch")
    if identity["topology_digests"] != EXPECTED_TOPOLOGY_DIGESTS:
        raise ValueError("donor topology identity mismatch")
    if identity["profile_digest"] != EXPECTED_PROFILE_DIGEST:
        raise ValueError("donor profile identity mismatch")

    sides = {}
    normal_audit = {}
    for side in ("L", "R"):
        specimen = build_opening_repair(side)
        faces = [[int(i) for i in f] for f in specimen["faces"]]
        rows = candidate_rows(donor, side)
        neutral_positions = [[float(c) for c in v] for v in rows[0.0]["positions"]]
        neutral_normals = smooth_normals(neutral_positions, faces)
        pose_payload = {}
        pose_audit = {}
        for angle in SAFE_POSES + (OUTSIDE_WITNESS,):
            positions = [[float(c) for c in v] for v in rows[angle]["positions"]]
            posed_normals = smooth_normals(positions, faces)
            summary = normal_delta_summary(neutral_normals, posed_normals)
            pose_payload[str(int(angle))] = {
                "angle_deg": angle,
                "positions": positions,
                "pose_recomputed_normals": posed_normals,
                "nonadjacent_intersection_pair_count": int(rows[angle]["nonadjacent_intersection_pair_count"]),
            }
            pose_audit[str(int(angle))] = summary
        if pose_audit["0"]["maximum_component_delta"] != 0.0:
            raise ValueError(f"{side} neutral normal identity is not exact")
        for angle in (-40, 36):
            if pose_audit[str(angle)]["changed_vertex_count_gt_1e_12_component"] <= 0:
                raise ValueError(f"{side} pose {angle} does not change recomputed normals")
        if int(pose_payload["37"]["nonadjacent_intersection_pair_count"]) <= 0:
            raise ValueError(f"{side} +37 outside-envelope witness was lost")
        sides[side] = {
            "faces": faces,
            "neutral_positions": neutral_positions,
            "neutral_smooth_normals": neutral_normals,
            "poses": pose_payload,
        }
        normal_audit[side] = pose_audit

    payload = {
        "schema": SCHEMA,
        "result": RESULT,
        "rigging_parent_head": RIGGING_PARENT_HEAD,
        "exact_identity": {
            "review006_source_digest": EXPECTED_REVIEW006_SOURCE_DIGEST,
            "review006_proof_mesh_digest": EXPECTED_REVIEW006_MESH_DIGEST,
            "geometry_head": GEOMETRY_HEAD,
            "topology_digests": EXPECTED_TOPOLOGY_DIGESTS,
            "profile_digest": EXPECTED_PROFILE_DIGEST,
        },
        "review_contract": contract,
        "receiver": {
            "normal_method": "AREA_WEIGHTED_INDEXED_VERTEX_SMOOTH_NORMAL",
            "neutral_control": "REUSE_EXACT_NEUTRAL_NORMALS_ON_POSED_VERTICES",
            "candidate": "RECOMPUTE_SAME_NORMAL_METHOD_FROM_EXACT_POSED_VERTICES",
            "negative": "INVERT_POSE_RECOMPUTED_NORMALS",
            "source_positions_or_faces_changed": False,
        },
        "sides": sides,
        "normal_delta_audit": normal_audit,
        "truth_boundary": contract["truth_boundary"],
    }
    payload["payload_sha256"] = canonical_digest(payload)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(CONTRACT_PATH))
    parser.add_argument("--out", default="lookdev-proof/generated/character_review006_shaded_shoulder_payload.json")
    args = parser.parse_args()
    payload = build_payload(Path(args.contract))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": payload["result"],
        "payload_sha256": payload["payload_sha256"],
        "left_normal_audit": payload["normal_delta_audit"]["L"],
        "right_normal_audit": payload["normal_delta_audit"]["R"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
