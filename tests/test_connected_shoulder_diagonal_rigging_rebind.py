from __future__ import annotations

from copy import deepcopy
import unittest

from axm_character_design.connected_shoulder_diagonal_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    MAX_RELEASE_WEIGHT,
    REPRESENTATIVE_ANGLES_DEG,
    STATUS,
    SUCCESSOR_RIG_ID,
    SWEEP_ANGLES_DEG,
    audit_diagonal_repair_rigging_rebind,
    rebind_contract,
    release_weight,
    successor_rig_profile,
)
from axm_character_design.organic_form import canonical_digest


class DiagonalRepairRiggingRebindTests(unittest.TestCase):
    def test_exact_rebind_passes_with_geometry_hold_preserved(self):
        report = audit_diagonal_repair_rigging_rebind()
        self.assertEqual(report["status"], STATUS)
        self.assertEqual(report["successor_rig_profile"]["rig_id"], SUCCESSOR_RIG_ID)
        self.assertEqual(report["sample_scope"]["samples_per_side"], 81)
        self.assertEqual(report["sample_scope"]["total_candidate_samples"], 162)
        self.assertEqual(report["sample_scope"]["representative_intersection_samples"], 10)
        self.assertEqual(report["dependencies"]["geometry_repair_sampled_total_pairs"], 52)
        self.assertEqual(report["dependencies"]["geometry_selected_mask"], 2)
        self.assertEqual(report["gates"]["sampled_self_intersection_freedom"], "HOLD_NONZERO_INTERSECTIONS_REMAIN")
        self.assertFalse(report["representative_intersections"]["all_intersection_free"])

    def test_profile_identity_and_endpoints_are_unchanged(self):
        self.assertEqual(canonical_digest(successor_rig_profile()), EXPECTED_PROFILE_DIGEST)
        self.assertEqual(release_weight(0.0), 0.0)
        self.assertEqual(release_weight(-40.0), MAX_RELEASE_WEIGHT)
        self.assertEqual(release_weight(40.0), MAX_RELEASE_WEIGHT)
        positive = [release_weight(float(angle)) for angle in range(0, 41)]
        self.assertEqual(positive, sorted(positive))
        for angle in range(0, 41):
            self.assertEqual(release_weight(float(-angle)), release_weight(float(angle)))

    def test_all_162_samples_are_structurally_green_nonworse_and_mirrored(self):
        report = audit_diagonal_repair_rigging_rebind()
        for side in ("L", "R"):
            rows = report["results"][side]["candidate"]
            self.assertEqual([row["angle_deg"] for row in rows], list(SWEEP_ANGLES_DEG))
            for row in rows:
                self.assertEqual(row["status"], "PASS", msg=f"{side} {row['angle_deg']}")
                self.assertTrue(row["nonworse_than_anchored_proximal_control"], msg=f"{side} {row['angle_deg']}")
                self.assertTrue(row["bilateral_mirrored_position_set"], msg=f"{side} {row['angle_deg']}")
                self.assertEqual(row["collapsed_triangles"], 0)
                self.assertLessEqual(row["fixed_socket_max_drift_m"], 1e-9)
                self.assertLessEqual(row["rigid_arm_radius_max_drift_m"], 1e-9)

    def test_historical_anchor_positions_and_boundary_improvement_survive_rebind(self):
        report = audit_diagonal_repair_rigging_rebind()
        for side in ("L", "R"):
            by_angle = {row["angle_deg"]: row for row in report["results"][side]["candidate"]}
            for angle in (-40.0, 0.0, 40.0):
                self.assertTrue(by_angle[angle]["matches_historical_anchor_positions"])
            self.assertTrue(by_angle[-40.0]["strictly_improves_anchored_proximal_control"])
            self.assertTrue(by_angle[40.0]["strictly_improves_anchored_proximal_control"])

    def test_representative_intersection_observer_keeps_anchor_counts_and_hold(self):
        report = audit_diagonal_repair_rigging_rebind()
        samples = {(row["side"], row["angle_deg"]): row for row in report["representative_intersections"]["samples"]}
        self.assertEqual(set(angle for _side, angle in samples), set(REPRESENTATIVE_ANGLES_DEG))
        for side in ("L", "R"):
            self.assertEqual(samples[(side, -40.0)]["pair_count"], 8)
            self.assertEqual(samples[(side, 0.0)]["pair_count"], 8)
            self.assertEqual(samples[(side, 40.0)]["pair_count"], 10)
        self.assertGreater(report["representative_intersections"]["pair_count_sum"], 0)

    def test_contract_drift_fails_closed(self):
        mutated = deepcopy(rebind_contract())
        mutated["geometry_repair_head"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "diagonal-repair Rigging rebind contract identity drift"):
            audit_diagonal_repair_rigging_rebind(mutated)


if __name__ == "__main__":
    unittest.main()
