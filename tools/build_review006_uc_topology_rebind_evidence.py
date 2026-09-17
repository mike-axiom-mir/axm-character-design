#!/usr/bin/env python3
"""Bind the exact Character review-006 Geometry receiver to merged UC topology evidence.

This is a read-only compatibility/evidence bridge. It does not replace the
Character-local topology construction, mutate the mesh, or transfer any UC PASS
into Character without re-running the exact Character receiver through the exact
merged observer identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from axm_character_design.review006_connected_geometry import (
    audit_review006_geometry_rebind,
    build_stage,
)
from axm_uc.mesh_topology import inspect_mesh_topology

EXPECTED_UC_MERGE_HEAD = "5bdeea950ed1292de23f65012d66a876ecf5c094"
EXPECTED_UC_OBSERVER_BLOB = "7afa348f5dd67aa7eaa66bdaf04a6ec5e4579dba"
EXPECTED_STAGE = "opening_repair"
EXPECTED_TOPOLOGY_DIGESTS = {
    "L": "ea00241192b2af9113a28c4b723e871b440d4d37d32ebe5457c64f94b7650d5d",
    "R": "aeca6971c25e9786bcdea4f28103f69db642d3c360226b0705752229050b850a",
}
WELD_TOLERANCE = 1e-9


def _side_receipt(side: str) -> dict:
    specimen = build_stage(side, EXPECTED_STAGE)
    local = specimen["local_preflight"]
    uc = inspect_mesh_topology(
        specimen["positions"],
        specimen["indices"],
        weld_tolerance=WELD_TOLERANCE,
    )

    checks = {
        "character_local_preflight_pass": local["status"].startswith("PASS_"),
        "source_vertex_count_match": uc["source_vertex_count"] == local["vertex_count"] == 92,
        "triangle_count_match": uc["triangle_count"] == local["triangle_count"] == 180,
        "all_source_vertices_referenced": uc["all_source_vertices_referenced"] is True,
        "unreferenced_source_vertex_count_zero": uc["unreferenced_source_vertex_count"] == 0,
        "all_referenced_source_vertex_fans_connected": (
            uc["all_referenced_source_vertex_fans_connected"] is True
        ),
        "disconnected_source_vertex_fan_count_zero": uc["disconnected_source_vertex_fan_count"] == 0,
        "local_disconnected_vertex_fan_count_zero": local["disconnected_vertex_fan_count"] == 0,
        "local_isolated_vertex_count_zero": local["isolated_vertex_count"] == 0,
        "collapsed_triangle_count_zero": uc["collapsed_triangle_count"] == 0,
        "boundary_edge_count_zero": uc["boundary_edge_count"] == 0,
        "nonmanifold_edge_count_zero": uc["nonmanifold_edge_count"] == 0,
        "orientation_conflict_edge_count_zero": uc["orientation_conflict_edge_count"] == 0,
        "triangle_component_count_one": uc["triangle_component_count"] == 1,
        "uc_closed_oriented_edge_candidate": (
            uc["status"] == "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise ValueError(f"{side} merged-UC topology rebind failed checks: {failed}; uc={uc}; local={local}")

    return {
        "side": side,
        "selected_stage": EXPECTED_STAGE,
        "checks": checks,
        "character_local_preflight": local,
        "merged_uc_observer": uc,
    }


def build_receipt(uc_head: str, uc_observer_blob: str) -> dict:
    if uc_head != EXPECTED_UC_MERGE_HEAD:
        raise ValueError(
            f"UC merged head drift: expected {EXPECTED_UC_MERGE_HEAD}, observed {uc_head}"
        )
    if uc_observer_blob != EXPECTED_UC_OBSERVER_BLOB:
        raise ValueError(
            "UC topology-observer blob drift: "
            f"expected {EXPECTED_UC_OBSERVER_BLOB}, observed {uc_observer_blob}"
        )

    character = audit_review006_geometry_rebind()
    selected = character["selection"]
    if selected["selected_stage"] != EXPECTED_STAGE:
        raise ValueError("Character review-006 selected Geometry stage drift")
    if selected["left_topology_digest"] != EXPECTED_TOPOLOGY_DIGESTS["L"]:
        raise ValueError("Character review-006 left topology digest drift")
    if selected["right_topology_digest"] != EXPECTED_TOPOLOGY_DIGESTS["R"]:
        raise ValueError("Character review-006 right topology digest drift")

    sides = [_side_receipt(side) for side in ("L", "R")]
    return {
        "schema": "axm.character-review006-merged-uc-topology-observer-rebind/v0.1",
        "status": "PASS_CHARACTER_REVIEW006_MERGED_UC_SOURCE_INDEX_TOPOLOGY_OBSERVER_REBIND",
        "pattern": "EXACT_PRODUCT_RECEIVER_REBIND_TO_MERGED_SHARED_OBSERVER_BEFORE_PASS_TRANSFER",
        "exact_identity": {
            "character_selected_stage": EXPECTED_STAGE,
            "character_left_topology_digest": EXPECTED_TOPOLOGY_DIGESTS["L"],
            "character_right_topology_digest": EXPECTED_TOPOLOGY_DIGESTS["R"],
            "uc_merge_head": uc_head,
            "uc_mesh_topology_blob": uc_observer_blob,
            "uc_pr": 187,
            "uc_weld_tolerance": WELD_TOLERANCE,
        },
        "observations": {
            "sides": sides,
            "both_sides_exact_source_vertices_referenced": all(
                row["merged_uc_observer"]["all_source_vertices_referenced"] for row in sides
            ),
            "both_sides_exact_source_vertex_fans_connected": all(
                row["merged_uc_observer"]["all_referenced_source_vertex_fans_connected"]
                for row in sides
            ),
            "both_sides_uc_closed_oriented_edge_candidates": all(
                row["merged_uc_observer"]["status"]
                == "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"
                for row in sides
            ),
        },
        "handoffs": {
            "rigging": (
                "No Rigging range or deformation PASS changes. Continue binding the exact opening_repair "
                "topology digests; this receipt only strengthens read-only structural provenance."
            ),
            "universal_creation": (
                "The merged observer is now exercised by one exact Character product receiver. This is a "
                "consumer rebind, not evidence that every product mesh inherits the same result."
            ),
            "geometry": (
                "Future products must bind the exact merged observer identity and rerun product-local evidence; "
                "do not transfer this Character receipt by analogy."
            ),
        },
        "truth_boundary": [
            "This receipt does not mutate Character geometry, source form, topology, normals, UVs, skinning or materials.",
            "Merged UC source-index liveness/fan and seam-welded edge observations are re-run on the exact Character opening_repair receiver; historical UC or Character PASS states are not copied across repositories.",
            "Closed oriented edge incidence plus connected exact-source fans is still only a bounded structural candidate, not a full geometric vertex-manifold or self-intersection proof.",
            "Neutral nonadjacent self-intersection evidence remains owned by the Character Geometry audit and is not replaced by the UC observer.",
            "No deformation quality, target-host shading, runtime benefit, collision/gameplay suitability, source adoption, CANON, production readiness, game readiness or Geometry mastery is claimed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir")
    parser.add_argument("--uc-head", required=True)
    parser.add_argument("--uc-observer-blob", required=True)
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt = build_receipt(args.uc_head, args.uc_observer_blob)
    path = out / "review006-merged-uc-topology-observer-rebind.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
