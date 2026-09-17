import unittest

from axm_character_design.review006_shoulder_edge_adjacent_fold_margin import (
    FOLD_CONTACT_EPSILON_RAD,
    SAMPLE_STEP_DEG,
    STATUS,
    audit_review006_sampled_edge_adjacent_fold_margin,
    edge_adjacent_fold_contract,
)
from axm_character_design.review006_shoulder_continuous_clearance import (
    SAFE_END_DEG,
    SAFE_START_DEG,
)


class Review006ShoulderEdgeAdjacentFoldMarginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_sampled_edge_adjacent_fold_margin()

    def test_sampled_edge_adjacent_fold_guard_passes(self):
        self.assertEqual(self.audit["status"], STATUS)
        guard = self.audit["sampled_edge_adjacent_fold_guard"]
        self.assertEqual(guard["range_deg"], [SAFE_START_DEG, SAFE_END_DEG])
        self.assertEqual(guard["step_deg"], SAMPLE_STEP_DEG)
        self.assertEqual(guard["sample_count_per_side"], 1532)
        self.assertTrue(guard["all_sampled_edge_adjacent_pairs_clear_of_same_ray_fold_contact"])
        self.assertTrue(guard["bilateral_pair_count_match"])
        self.assertTrue(guard["bilateral_minimum_fold_angle_match"])
        self.assertTrue(guard["bilateral_representative_pose_mirror"])
        for side in ("L", "R"):
            result = guard["sides"][side]
            self.assertEqual(result["sample_count"], 1532)
            self.assertGreater(result["edge_adjacent_pair_count"], 0)
            self.assertGreater(result["vertex_only_neighbor_pair_count"], 0)
            self.assertEqual(result["fold_contact_sample_count"], 0)
            self.assertGreater(result["minimum_sampled_fold_angle_rad"], FOLD_CONTACT_EPSILON_RAD)

    def test_known_nonadjacent_failure_remains_separate(self):
        guard = self.audit["sampled_edge_adjacent_fold_guard"]
        for side in ("L", "R"):
            rows = guard["sides"][side]["representative_rows"]
            failure_boundary = next(row for row in rows if row["angle_deg"] == 36.60)
            self.assertTrue(failure_boundary["outside_sampled_edge_guard"])
            self.assertTrue(failure_boundary["known_nonadjacent_contact_witness"])
        self.assertIn(
            "The +36.60 retained nonadjacent contact remains a separate failure class",
            self.audit["truth_boundary"][3],
        )

    def test_negative_same_ray_fold_is_rejected(self):
        negative = self.audit["negative_control"]
        self.assertTrue(negative["rejected"])
        for side in ("L", "R"):
            row = negative["sides"][side]
            self.assertTrue(row["rejected"])
            self.assertLessEqual(row["observed_fold_angle_rad"], FOLD_CONTACT_EPSILON_RAD)

    def test_truth_boundary_keeps_continuity_vertex_neighbors_and_receivers_held(self):
        truth = edge_adjacent_fold_contract()["truth_boundary"]
        self.assertTrue(truth["edge_adjacent_sampled_fold_contact_only"])
        self.assertFalse(truth["continuous_edge_adjacent_fold_contact_proven"])
        self.assertFalse(truth["vertex_only_neighbor_contact_proven"])
        self.assertFalse(truth["nonadjacent_contact_replaced"])
        self.assertFalse(truth["anatomical_range_of_motion"])
        self.assertFalse(truth["animation_acceptance"])
        self.assertFalse(truth["technical_art_acceptance"])
        self.assertFalse(truth["runtime_acceptance"])
        self.assertFalse(truth["visual_acceptance"])
        self.assertFalse(truth["source_adoption_or_canon"])

    def test_contract_drift_fails_closed(self):
        drifted = edge_adjacent_fold_contract()
        drifted["sampled_fold_guard"]["step_deg"] = 0.10
        with self.assertRaises(ValueError):
            audit_review006_sampled_edge_adjacent_fold_margin(drifted)


if __name__ == "__main__":
    unittest.main()
