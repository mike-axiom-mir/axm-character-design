from __future__ import annotations

import unittest

from axm_character_design.connected_shoulder_intersection_repair import (
    STATUS,
    audit_opening_repair,
    build_opening_repair_specimen,
)
from axm_character_design.shoulder_connected_topology import build_connected_shoulder_specimen


class ConnectedShoulderIntersectionRepairTests(unittest.TestCase):
    def test_candidate_is_topology_only_closed_and_bounded(self):
        for side in ("L", "R"):
            base = build_connected_shoulder_specimen(side)
            candidate = build_opening_repair_specimen(side)
            self.assertEqual(candidate["positions"], base["positions"])
            self.assertEqual(len(candidate["positions"]), 93)
            self.assertEqual(len(base["faces"]), 182)
            self.assertEqual(len(candidate["faces"]), 180)
            preflight = candidate["local_preflight"]
            self.assertEqual(preflight["status"], "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT")
            self.assertEqual(preflight["boundary_edge_count"], 0)
            self.assertEqual(preflight["nonmanifold_edge_count"], 0)
            self.assertEqual(preflight["orientation_conflict_edge_count"], 0)
            self.assertEqual(preflight["collapsed_triangle_count"], 0)
            self.assertEqual(preflight["triangle_component_count"], 1)
            self.assertEqual(candidate["construction"]["expanded_hole_vertex_count"], 12)
            self.assertFalse(candidate["construction"]["positions_moved"])

    def test_exact_sampled_intersections_are_reduced_but_not_hidden(self):
        receipt = audit_opening_repair()
        self.assertEqual(receipt["status"], STATUS)
        comparison = receipt["sampled_intersection_comparison"]
        self.assertEqual(comparison["base_total_pairs"], 374)
        self.assertEqual(comparison["candidate_total_pairs"], 58)
        self.assertEqual(comparison["reduction_pair_count"], 316)
        self.assertTrue(comparison["all_candidate_samples_still_nonzero"])
        self.assertEqual(comparison["neutral_base_pairs_per_side"], 61)
        self.assertEqual(comparison["neutral_candidate_pairs_per_side"], 9)
        self.assertEqual(len(comparison["samples"]), 6)
        for row in comparison["samples"]:
            self.assertGreater(row["candidate_intersection_pair_count"], 0)
            self.assertLess(
                row["candidate_intersection_pair_count"],
                row["base_intersection_pair_count"],
            )
        self.assertEqual(receipt["gates"]["intersection_free"], "HOLD_NONZERO_INTERSECTIONS_REMAIN")
        self.assertEqual(receipt["gates"]["rigging_rebind"], "NOT_PERFORMED")

    def test_invalid_side_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "side must be L or R"):
            build_opening_repair_specimen("X")


if __name__ == "__main__":
    unittest.main()
