from __future__ import annotations

from copy import deepcopy
import unittest

from axm_character_design.connected_shoulder_deformation_sweep import (
    REPRESENTATIVE_ANGLES_DEG,
    STATUS,
    SWEEP_ANGLES_DEG,
    audit_connected_shoulder_deformation_sweep,
    sweep_contract,
)


class ConnectedShoulderDeformationSweepTests(unittest.TestCase):
    def test_exact_dense_sweep_passes(self):
        report = audit_connected_shoulder_deformation_sweep()
        self.assertEqual(report["status"], STATUS)
        self.assertEqual(report["sample_scope"]["samples_per_side"], 81)
        self.assertEqual(report["sample_scope"]["total_candidate_samples"], 162)
        self.assertFalse(report["sample_scope"]["continuous_interpolation_proven"])
        self.assertFalse(report["sample_scope"]["interior_self_intersection_checked"])

    def test_every_candidate_sample_is_green_mirrored_and_nonworse(self):
        report = audit_connected_shoulder_deformation_sweep()
        for side in ("L", "R"):
            rows = report["results"][side]["candidate"]
            self.assertEqual([row["angle_deg"] for row in rows], list(SWEEP_ANGLES_DEG))
            for row in rows:
                self.assertEqual(row["status"], "PASS")
                self.assertTrue(row["improves_anchored_proximal_control"])
                self.assertTrue(row["bilateral_mirrored_position_set"])
                self.assertEqual(row["collapsed_triangles"], 0)
                self.assertEqual(row["fixed_socket_max_drift_m"], 0.0)
                self.assertLessEqual(row["rigid_arm_radius_max_drift_m"], 1e-9)

    def test_original_three_rigging_anchors_are_exactly_preserved(self):
        report = audit_connected_shoulder_deformation_sweep()
        for side in ("L", "R"):
            anchors = {
                row["angle_deg"]: row["matches_original_rigging_anchor"]
                for row in report["results"][side]["candidate"]
                if row["matches_original_rigging_anchor"] is not None
            }
            self.assertEqual(anchors, {-40.0: True, 0.0: True, 40.0: True})

    def test_representative_midpoints_are_retained(self):
        report = audit_connected_shoulder_deformation_sweep()
        for side in ("L", "R"):
            self.assertEqual(
                [row["angle_deg"] for row in report["representative"][side]],
                list(REPRESENTATIVE_ANGLES_DEG),
            )

    def test_sweep_contract_drift_fails_closed(self):
        mutated = deepcopy(sweep_contract())
        mutated["sweep"]["step_deg"] = 2.0
        with self.assertRaisesRegex(ValueError, "sweep contract identity drift"):
            audit_connected_shoulder_deformation_sweep(mutated)


if __name__ == "__main__":
    unittest.main()
