import unittest

from axm_character_design.review006_shoulder_continuous_edge_adjacent_fold import (
    CERTIFICATE_MARGIN_RAD,
    STATUS,
    audit_review006_continuous_edge_adjacent_fold_margin,
    continuous_edge_adjacent_fold_contract,
)
from axm_character_design.review006_shoulder_continuous_clearance import (
    FIRST_SAMPLED_FAILURE_DEG,
    SAFE_END_DEG,
    SAFE_START_DEG,
)


class Review006ShoulderContinuousEdgeAdjacentFoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_continuous_edge_adjacent_fold_margin()

    def test_continuous_edge_adjacent_guard_passes(self):
        self.assertEqual(self.audit["status"], STATUS)
        guard = self.audit["continuous_edge_adjacent_fold_guard"]
        self.assertEqual(guard["range_deg"], [SAFE_START_DEG, SAFE_END_DEG])
        self.assertTrue(guard["all_real_owner_angles_certified"])
        self.assertTrue(guard["bilateral_pair_count_match"])
        for side in ("L", "R"):
            result = guard["sides"][side]
            self.assertEqual(result["edge_adjacent_pair_count"], 270)
            self.assertEqual(result["vertex_only_neighbor_pair_count"], 845)
            self.assertTrue(result["continuous_same_ray_fold_contact_free"])
            self.assertGreater(
                result["minimum_certificate_slack_rad"],
                CERTIFICATE_MARGIN_RAD,
            )

    def test_known_nonadjacent_failure_and_vertex_only_hold_remain(self):
        retained = self.audit["retained_boundaries"]
        self.assertEqual(
            retained["first_retained_nonadjacent_failure_deg"],
            FIRST_SAMPLED_FAILURE_DEG,
        )
        self.assertFalse(retained["vertex_only_neighbor_contact_proven"])
        self.assertIn(
            "The 845 vertex-only neighbouring face pairs per shoulder remain outside this claim.",
            self.audit["truth_boundary"],
        )
        self.assertIn(
            "The retained +36.60 nonadjacent 114/137 contact remains a separate failure class and is not waived.",
            self.audit["truth_boundary"],
        )

    def test_same_ray_negative_control_remains_rejected(self):
        negative = self.audit["negative_control"]
        self.assertTrue(negative["rejected"])
        for side in ("L", "R"):
            self.assertTrue(negative["sides"][side]["rejected"])

    def test_truth_boundary_does_not_transfer_animation_or_runtime_acceptance(self):
        truth = continuous_edge_adjacent_fold_contract()["truth_boundary"]
        self.assertTrue(truth["continuous_edge_adjacent_same_ray_fold_contact_proven"])
        self.assertFalse(truth["vertex_only_neighbor_contact_proven"])
        self.assertFalse(truth["animation_acceptance"])
        self.assertFalse(truth["technical_art_acceptance"])
        self.assertFalse(truth["runtime_acceptance"])
        self.assertFalse(truth["visual_acceptance"])
        self.assertFalse(truth["source_adoption_or_canon"])

    def test_contract_drift_fails_closed(self):
        drifted = continuous_edge_adjacent_fold_contract()
        drifted["continuous_fold_certificate"]["base_interval_deg"] = 0.10
        with self.assertRaises(ValueError):
            audit_review006_continuous_edge_adjacent_fold_margin(drifted)


if __name__ == "__main__":
    unittest.main()
