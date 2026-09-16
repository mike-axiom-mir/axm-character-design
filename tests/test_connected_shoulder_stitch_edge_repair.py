from __future__ import annotations

import unittest

from axm_character_design.connected_shoulder_diagonal_repair import (
    SELECTED_MASK,
    build_diagonal_mask_specimen,
)
from axm_character_design.connected_shoulder_diagonal_rigging_rebind import (
    ANCHOR_ANGLES_DEG,
    audit_diagonal_repair_rigging_rebind,
)
from axm_character_design.connected_shoulder_stitch_edge_repair import (
    STATUS,
    TARGET_FACE_PAIRS,
    audit_stitch_edge_repair,
    build_single_stitch_edge_specimen,
    build_stitch_edge_repair_specimen,
    search_single_stitch_edge_flips,
)
from axm_character_design.self_intersection import inspect_triangle_self_intersections


class ConnectedShoulderStitchEdgeRepairTests(unittest.TestCase):
    def test_candidate_changes_four_face_records_only_and_keeps_structural_budget(self):
        for side in ("L", "R"):
            base = build_diagonal_mask_specimen(side, SELECTED_MASK)
            candidate = build_stitch_edge_repair_specimen(side)
            self.assertEqual(candidate["positions"], base["positions"])
            self.assertEqual(candidate["groups"], base["groups"])
            self.assertEqual(len(candidate["positions"]), 93)
            self.assertEqual(len(candidate["faces"]), 180)
            changed = [
                index
                for index, (before, after) in enumerate(zip(base["faces"], candidate["faces"]))
                if list(before) != list(after)
            ]
            self.assertEqual(changed, [111, 112, 114, 115])
            self.assertEqual(
                candidate["construction"]["target_face_pairs"],
                [list(pair) for pair in TARGET_FACE_PAIRS],
            )
            preflight = candidate["local_preflight"]
            self.assertEqual(
                preflight["status"],
                "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT",
            )
            self.assertEqual(preflight["boundary_edge_count"], 0)
            self.assertEqual(preflight["nonmanifold_edge_count"], 0)
            self.assertEqual(preflight["orientation_conflict_edge_count"], 0)
            self.assertEqual(preflight["collapsed_triangle_count"], 0)
            self.assertEqual(preflight["triangle_component_count"], 1)

    def test_exact_single_edge_family_selects_two_non_overlapping_winners(self):
        search = search_single_stitch_edge_flips()
        self.assertEqual(search["legal_single_flip_count"], 22)
        self.assertEqual(
            search["distribution_by_total_pair_count"],
            {48: 2, 52: 17, 54: 2, 64: 1},
        )
        self.assertEqual(search["minimum_total_pair_count"], 48)
        self.assertEqual(
            search["winning_face_pairs"],
            [list(pair) for pair in TARGET_FACE_PAIRS],
        )
        self.assertTrue(set(TARGET_FACE_PAIRS[0]).isdisjoint(TARGET_FACE_PAIRS[1]))

    def test_dense_sweep_is_never_worse_but_remains_nonzero(self):
        receipt = audit_stitch_edge_repair()
        self.assertEqual(receipt["status"], STATUS)
        dense = receipt["dense_sweep"]
        self.assertEqual(dense["total_samples"], 162)
        self.assertEqual(dense["baseline_pair_count_sum"], 1320)
        self.assertEqual(dense["candidate_pair_count_sum"], 1020)
        self.assertEqual(dense["reduction_pair_count"], 300)
        self.assertEqual(dense["strictly_reduced_samples"], 150)
        self.assertEqual(dense["equal_samples"], 12)
        self.assertEqual(dense["worse_samples"], 0)
        self.assertEqual(dense["baseline_min_pair_count"], 8)
        self.assertEqual(dense["baseline_max_pair_count"], 10)
        self.assertEqual(dense["candidate_min_pair_count"], 6)
        self.assertEqual(dense["candidate_max_pair_count"], 10)
        self.assertTrue(dense["all_candidate_samples_still_nonzero"])
        anchors = [
            row["candidate_pair_count"]
            for row in dense["rows"]
            if row["angle_deg"] in ANCHOR_ANGLES_DEG
        ]
        self.assertEqual(anchors, [6, 6, 10, 6, 6, 10])
        self.assertEqual(
            receipt["gates"]["intersection_free"],
            "HOLD_NONZERO_INTERSECTIONS_REMAIN",
        )
        self.assertEqual(
            receipt["gates"]["rigging_rebind_for_this_topology"],
            "NOT_PERFORMED",
        )

    def test_known_single_edge_control_is_worse_not_silently_selected(self):
        rigging = audit_diagonal_repair_rigging_rebind()
        total = 0
        for side in ("L", "R"):
            specimen = build_single_stitch_edge_specimen(side, (115, 116))
            rows = {
                float(row["angle_deg"]): row["positions"]
                for row in rigging["results"][side]["candidate"]
            }
            for angle in ANCHOR_ANGLES_DEG:
                report = inspect_triangle_self_intersections(
                    rows[float(angle)],
                    specimen["indices"],
                )
                total += report["self_intersection_pair_count"]
        self.assertEqual(total, 64)

    def test_out_of_group_pair_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "ribcage_to_seam"):
            build_single_stitch_edge_specimen("L", (152, 153))


if __name__ == "__main__":
    unittest.main()
