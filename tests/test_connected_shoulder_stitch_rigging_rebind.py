from __future__ import annotations

from copy import deepcopy
import unittest

from axm_character_design.connected_shoulder_diagonal_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    successor_rig_profile,
)
from axm_character_design.connected_shoulder_stitch_rigging_rebind import (
    EXPECTED_REPRESENTATIVE_INTERSECTION_COUNTS,
    REPRESENTATIVE_ANGLES_DEG,
    STATUS,
    SWEEP_ANGLES_DEG,
    audit_stitch_edge_rigging_rebind,
    rebind_contract,
)
from axm_character_design.organic_form import canonical_digest


class StitchEdgeRiggingRebindTests(unittest.TestCase):
    def test_exact_rebind_passes_with_geometry_hold_preserved(self):
        report = audit_stitch_edge_rigging_rebind()
        self.assertEqual(report["status"], STATUS)
        self.assertEqual(report["sample_scope"]["samples_per_side"], 81)
        self.assertEqual(report["sample_scope"]["total_candidate_samples"], 162)
        self.assertEqual(report["sample_scope"]["representative_intersection_samples"], 10)
        self.assertEqual(report["dependencies"]["geometry_stitch_dense_pair_sum"], 1020)
        self.assertEqual(report["dependencies"]["geometry_stitch_strictly_reduced_samples"], 150)
        self.assertEqual(
            report["gates"]["sampled_self_intersection_freedom"],
            "HOLD_NONZERO_INTERSECTIONS_REMAIN",
        )
        self.assertFalse(report["representative_intersections"]["all_intersection_free"])

    def test_exact_rig_profile_identity_is_unchanged(self):
        self.assertEqual(canonical_digest(successor_rig_profile()), EXPECTED_PROFILE_DIGEST)
        report = audit_stitch_edge_rigging_rebind()
        self.assertEqual(
            canonical_digest(report["successor_rig_profile"]), EXPECTED_PROFILE_DIGEST
        )

    def test_all_162_samples_are_green_nonworse_mirrored_and_position_identical(self):
        report = audit_stitch_edge_rigging_rebind()
        for side in ("L", "R"):
            rows = report["results"][side]["candidate"]
            self.assertEqual([row["angle_deg"] for row in rows], list(SWEEP_ANGLES_DEG))
            for row in rows:
                label = f"{side} {row['angle_deg']}"
                self.assertEqual(row["status"], "PASS", msg=label)
                self.assertTrue(row["nonworse_than_anchored_proximal_control"], msg=label)
                self.assertTrue(row["matches_previous_rigging_pose_field"], msg=label)
                self.assertTrue(row["bilateral_mirrored_position_set"], msg=label)
                self.assertEqual(row["collapsed_triangles"], 0, msg=label)
                self.assertLessEqual(row["fixed_socket_max_drift_m"], 1e-9, msg=label)
                self.assertLessEqual(row["rigid_arm_radius_max_drift_m"], 1e-9, msg=label)

    def test_historical_anchors_and_boundary_improvement_survive_rebind(self):
        report = audit_stitch_edge_rigging_rebind()
        for side in ("L", "R"):
            by_angle = {
                row["angle_deg"]: row for row in report["results"][side]["candidate"]
            }
            for angle in (-40.0, 0.0, 40.0):
                self.assertTrue(by_angle[angle]["matches_historical_anchor_positions"])
            self.assertTrue(by_angle[-40.0]["strictly_improves_anchored_proximal_control"])
            self.assertTrue(by_angle[40.0]["strictly_improves_anchored_proximal_control"])

    def test_representative_intersection_counts_are_reobserved_exactly(self):
        report = audit_stitch_edge_rigging_rebind()
        samples = {
            (row["side"], row["angle_deg"]): row
            for row in report["representative_intersections"]["samples"]
        }
        self.assertEqual(set(angle for _side, angle in samples), set(REPRESENTATIVE_ANGLES_DEG))
        for side in ("L", "R"):
            for angle, expected in EXPECTED_REPRESENTATIVE_INTERSECTION_COUNTS[side].items():
                self.assertEqual(samples[(side, angle)]["pair_count"], expected)
        self.assertEqual(report["representative_intersections"]["pair_count_sum"], 68)

    def test_contract_drift_fails_closed(self):
        mutated = deepcopy(rebind_contract())
        mutated["geometry_stitch_repair_head"] = "0" * 40
        with self.assertRaisesRegex(
            ValueError, "stitch-edge Rigging rebind contract identity drift"
        ):
            audit_stitch_edge_rigging_rebind(mutated)


if __name__ == "__main__":
    unittest.main()
