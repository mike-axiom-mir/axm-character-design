from __future__ import annotations

import unittest

from axm_character_design.connected_shoulder_deformation import audit_connected_shoulder_deformation
from axm_character_design.connected_shoulder_diagonal_repair import (
    SELECTED_MASK,
    STATUS,
    audit_selected_diagonal_repair,
    build_diagonal_mask_specimen,
)
from axm_character_design.connected_shoulder_intersection_repair import (
    build_opening_repair_specimen,
)
from axm_character_design.self_intersection import inspect_triangle_self_intersections


class ConnectedShoulderDiagonalRepairTests(unittest.TestCase):
    def test_selected_candidate_changes_one_quad_only_and_keeps_budget(self):
        for side in ("L", "R"):
            base = build_opening_repair_specimen(side)
            candidate = build_diagonal_mask_specimen(side, SELECTED_MASK)
            self.assertEqual(candidate["positions"], base["positions"])
            self.assertEqual(candidate["groups"], base["groups"])
            self.assertEqual(len(candidate["positions"]), 93)
            self.assertEqual(len(candidate["faces"]), 180)
            self.assertEqual(candidate["construction"]["flipped_quad_indices"], [1])
            changed = [
                index for index, (before, after) in enumerate(zip(base["faces"], candidate["faces"]))
                if before != after
            ]
            self.assertEqual(changed, [152, 153])
            preflight = candidate["local_preflight"]
            self.assertEqual(preflight["status"], "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT")
            self.assertEqual(preflight["boundary_edge_count"], 0)
            self.assertEqual(preflight["nonmanifold_edge_count"], 0)
            self.assertEqual(preflight["orientation_conflict_edge_count"], 0)
            self.assertEqual(preflight["collapsed_triangle_count"], 0)
            self.assertEqual(preflight["triangle_component_count"], 1)

    def test_selected_candidate_reduces_every_retained_anchor_but_remains_hold(self):
        receipt = audit_selected_diagonal_repair()
        self.assertEqual(receipt["status"], STATUS)
        comparison = receipt["sampled_intersection_comparison"]
        self.assertEqual(comparison["baseline_total_pairs"], 58)
        self.assertEqual(comparison["candidate_total_pairs"], 52)
        self.assertEqual(comparison["reduction_pair_count"], 6)
        self.assertTrue(comparison["all_six_samples_strictly_reduced"])
        self.assertTrue(comparison["all_candidate_samples_still_nonzero"])
        self.assertEqual(
            [row["intersection_pair_count"] for row in comparison["candidate_rows"]],
            [8, 8, 10, 8, 8, 10],
        )
        self.assertEqual(receipt["gates"]["intersection_free"], "HOLD_NONZERO_INTERSECTIONS_REMAIN")
        self.assertEqual(receipt["gates"]["rigging_rebind_for_this_topology"], "NOT_PERFORMED")

    def test_known_opposite_local_diagonal_is_worse_not_silently_selected(self):
        rigging = audit_connected_shoulder_deformation()
        total = 0
        for side in ("L", "R"):
            specimen = build_diagonal_mask_specimen(side, 1 << 3)
            for pose in rigging["results"][side]["candidate"]:
                report = inspect_triangle_self_intersections(pose["positions"], specimen["indices"])
                total += report["self_intersection_pair_count"]
        self.assertEqual(total, 64)

    def test_invalid_mask_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "mask must be an integer"):
            build_diagonal_mask_specimen("L", -1)
        with self.assertRaisesRegex(ValueError, "mask must be an integer"):
            build_diagonal_mask_specimen("L", 1024)


if __name__ == "__main__":
    unittest.main()
