#!/usr/bin/env python3
"""Rebind the exact Character review-006 Geometry receiver to merged UC self-intersection evidence.

This is a read-only successor/migration receipt. It preserves the historical
Character-local observer and compares only the overlapping static neutral
nonadjacent-triangle claim on the exact selected receiver. It does not mutate
geometry, retire the local implementation, transfer Animal evidence, or widen
this finite observation into deformation/contact/runtime acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from axm_character_design.review006_connected_geometry import (
    audit_review006_geometry_rebind,
    build_stage,
)
from axm_character_design.review006_self_intersection import (
    inspect_triangle_self_intersections as inspect_local_self_intersections,
)
from axm_uc.mesh_self_intersection import (
    DEFAULT_MAX_TRIANGLE_PAIR_CHECKS,
    inspect_triangle_self_intersections as inspect_uc_self_intersections,
)

UC_REPOSITORY = "mike-axiom-mir/axm-universal-creation"
EXPECTED_UC_MERGE_HEAD = "41b4d9134e4d2e5f4fadaada2a1d6a56eed92ab0"
UC_MODULE = "src/axm_uc/mesh_self_intersection.py"
EXPECTED_UC_OBSERVER_BLOB = "2de80eada941de54a067b551e51b75a9bde0500b"
EXPECTED_STAGE = "opening_repair"
EXPECTED_TOPOLOGY_DIGESTS = {
    "L": "ea00241192b2af9113a28c4b723e871b440d4d37d32ebe5457c64f94b7650d5d",
    "R": "aeca6971c25e9786bcdea4f28103f69db642d3c360226b0705752229050b850a",
}
EPSILON = 1e-9


def _crossing_control() -> tuple[list[list[float]], list[int]]:
    """Two nonadjacent triangles with one deterministic geometric crossing."""
    return (
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.5, 0.5, -1.0],
            [0.5, 0.5, 1.0],
            [1.5, 0.5, 0.0],
        ],
        [0, 1, 2, 3, 4, 5],
    )


def _side_receipt(side: str) -> dict:
    specimen = build_stage(side, EXPECTED_STAGE)
    local = inspect_local_self_intersections(
        specimen["positions"], specimen["indices"], epsilon=EPSILON
    )
    shared = inspect_uc_self_intersections(
        specimen["positions"], specimen["indices"], epsilon=EPSILON
    )

    triangle_count = len(specimen["indices"]) // 3
    required_pairs = triangle_count * (triangle_count - 1) // 2
    budget_hold = inspect_uc_self_intersections(
        specimen["positions"],
        specimen["indices"],
        epsilon=EPSILON,
        max_triangle_pair_checks=required_pairs - 1,
    )

    checks = {
        "selected_receiver_budget_92v_180t": (
            len(specimen["positions"]) == 92 and triangle_count == 180
        ),
        "historical_local_observer_clear": (
            local["status"] == "PASS_NO_NONADJACENT_SELF_INTERSECTIONS"
            and local["self_intersection_pair_count"] == 0
        ),
        "merged_uc_observer_clear": (
            shared["status"] == "PASS_NO_NONADJACENT_SELF_INTERSECTIONS"
            and shared["inspection_complete"] is True
            and shared["self_intersection_pair_count"] == 0
        ),
        "exact_pair_work_accounted": (
            local["triangle_pair_count"]
            == shared["triangle_pair_checks_required"]
            == shared["triangle_pair_checks_performed"]
            == required_pairs
        ),
        "topological_neighbor_exclusion_count_matches": (
            local["skipped_topological_neighbor_pairs"]
            == shared["skipped_topological_neighbor_pairs"]
        ),
        "budget_hold_fails_closed_before_scan": (
            budget_hold["status"] == "HOLD_TRIANGLE_PAIR_BUDGET_EXCEEDED"
            and budget_hold["inspection_complete"] is False
            and budget_hold["triangle_pair_checks_required"] == required_pairs
            and budget_hold["triangle_pair_checks_performed"] == 0
            and budget_hold["self_intersection_pair_count"] is None
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise ValueError(
            f"{side} merged-UC self-intersection rebind failed checks: {failed}; "
            f"local={local}; shared={shared}; budget_hold={budget_hold}"
        )

    return {
        "side": side,
        "selected_stage": EXPECTED_STAGE,
        "vertex_count": len(specimen["positions"]),
        "triangle_count": triangle_count,
        "required_pair_checks": required_pairs,
        "checks": checks,
        "historical_character_local_observer": local,
        "merged_uc_observer": shared,
        "merged_uc_budget_hold_control": budget_hold,
    }


def build_receipt(uc_head: str, uc_observer_blob: str) -> dict:
    if uc_head != EXPECTED_UC_MERGE_HEAD:
        raise ValueError(
            f"UC merged head drift: expected {EXPECTED_UC_MERGE_HEAD}, observed {uc_head}"
        )
    if uc_observer_blob != EXPECTED_UC_OBSERVER_BLOB:
        raise ValueError(
            "UC self-intersection-observer blob drift: "
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

    negative_positions, negative_indices = _crossing_control()
    local_negative = inspect_local_self_intersections(
        negative_positions, negative_indices, epsilon=EPSILON
    )
    shared_negative = inspect_uc_self_intersections(
        negative_positions, negative_indices, epsilon=EPSILON
    )
    if not (
        local_negative["self_intersection_pair_count"] == 1
        and shared_negative["self_intersection_pair_count"] == 1
        and shared_negative["status"] == "SELF_INTERSECTIONS_DETECTED"
    ):
        raise ValueError(
            "crossing negative-control mismatch; "
            f"local={local_negative}; shared={shared_negative}"
        )

    sides = [_side_receipt(side) for side in ("L", "R")]
    return {
        "schema": "axm.character-review006-merged-uc-self-intersection-rebind/v0.1",
        "status": "PASS_CHARACTER_REVIEW006_MERGED_UC_SELF_INTERSECTION_OBSERVER_REBIND",
        "pattern": "PRESERVE_HISTORICAL_LOCAL_RECEIPT_AND_REBIND_EXACT_PRODUCT_TO_SHARED_SELF_INTERSECTION_SUCCESSOR",
        "exact_identity": {
            "character_selected_stage": EXPECTED_STAGE,
            "character_left_topology_digest": EXPECTED_TOPOLOGY_DIGESTS["L"],
            "character_right_topology_digest": EXPECTED_TOPOLOGY_DIGESTS["R"],
            "uc_repository": UC_REPOSITORY,
            "uc_merge_head": uc_head,
            "uc_module": UC_MODULE,
            "uc_mesh_self_intersection_blob": uc_observer_blob,
            "uc_pr": 188,
            "epsilon": EPSILON,
            "uc_default_max_triangle_pair_checks": DEFAULT_MAX_TRIANGLE_PAIR_CHECKS,
        },
        "observations": {
            "sides": sides,
            "both_sides_local_and_shared_clear": all(
                row["historical_character_local_observer"]["self_intersection_pair_count"] == 0
                and row["merged_uc_observer"]["self_intersection_pair_count"] == 0
                for row in sides
            ),
            "crossing_negative_control": {
                "historical_character_local": local_negative,
                "merged_uc": shared_negative,
            },
        },
        "migration_state": {
            "shared_successor_rebound": True,
            "historical_local_receipt_preserved": True,
            "local_implementation_retired": False,
            "mesh_modified": False,
            "rigging_retune_requested": False,
        },
        "handoffs": {
            "rigging": (
                "Selected opening_repair topology identity is unchanged. No weight, range, or deformation "
                "retune is requested; this receipt advances only neutral static observer lineage."
            ),
            "universal_creation": (
                "Merged shared observer is now exercised by the exact Character review-006 receiver in addition "
                "to Animal. Product receipts remain local; no PASS transfers by analogy."
            ),
            "geometry": (
                "Keep the Character-local observer until an explicit retirement decision has independent "
                "migration/lineage evidence. Do not delete it merely because shared parity is green."
            ),
        },
        "truth_boundary": [
            "This receipt does not mutate Character geometry, source form, topology, normals, UVs, skinning, animation or materials.",
            "Only exact static neutral nonadjacent-triangle self-intersection observation is rebound; historical Character-local evidence is preserved rather than rewritten.",
            "Topological-neighbor triangle pairs remain excluded, so adjacent fold/contact is not proven absent.",
            "Continuous deformation safety, arbitrary pose safety, visual quality, target-host shading, runtime benefit, collision/gameplay suitability and source adoption are not established.",
            "No local-observer retirement, CANON, production readiness, game readiness or Geometry mastery is claimed.",
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
    path = out / "review006-merged-uc-self-intersection-observer-rebind.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
