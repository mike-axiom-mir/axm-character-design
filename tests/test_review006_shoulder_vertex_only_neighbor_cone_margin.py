import unittest

from axm_character_design.review006_shoulder_continuous_clearance import (
    SAFE_END_DEG,
    SAFE_START_DEG,
)
from axm_character_design.review006_shoulder_vertex_only_neighbor_cone_margin import (
    SAMPLE_STEP_DEG,
    STATUS,
    VERTEX_CONTACT_EPSILON_RAD,
    audit_review006_sampled_vertex_only_neighbor_cone_margin,
    sampled_vertex_only_neighbor_contract,
)


class Review006ShoulderVertexOnlyNeighborConeMarginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_sampled_vertex_only_neighbor_cone_margin()

    def test_sampled_vertex_only_guard_passes(self):
        self.assertEqual(self.audit["status"], STATUS)
        guard = self.audit["sampled_vertex_only_neighbor_guard"]
        self.assertEqual(guard["range_deg"], [SAFE_START_DEG, SAFE_END_DEG])
        self.assertEqual(guard["regular_step_deg"], SAMPLE_STEP_DEG)
        self.assertTrue(guard["exact_safe_endpoint_included"])
        self.assertEqual(guard["sample_count_per_side"], 308)
        self.assertTrue(guard["all_sampled_vertex_only_pairs_cone_separated"])
        self.assertTrue(guard["bilateral_pair_count_match"])
        self.assertTrue(guard["bilateral_representative_pose_mirror"])
        self.assertLessEqual(
            guard["bilateral_minimum_cone_separation_residual_rad"], 1e-12
        )
        for side in ("L", "R"):
            result = guard["sides"][side]
            self.assertEqual(result["sample_count"], 308)
            self.assertEqual(result["vertex_only_neighbor_pair_count"], 845)
            self.assertEqual(result["uncertified_sample_count"], 0)
            self.assertGreater(
                result["minimum_sampled_cone_separation_rad"],
                VERTEX_CONTACT_EPSILON_RAD,
            )

    def test_known_nonadjacent_failure_remains_separate(self):
        guard = self.audit["sampled_vertex_only_neighbor_guard"]
        for side in ("L", "R"):
            row = next(
                item
                for item in guard["sides"][side]["representative_rows"]
                if item["angle_deg"] == 36.60
            )
            self.assertTrue(row["outside_sampled_vertex_only_guard"])
            self.assertTrue(row["known_nonadjacent_contact_witness"])
        self.assertIn(
            "The +36.60 retained nonadjacent contact remains a separate failure class",
            self.audit["truth_boundary"][3],
        )

    def test_overlapping_cone_negative_control_is_rejected(self):
        negative = self.audit["negative_control"]
        self.assertTrue(negative["rejected"])
        for side in ("L", "R"):
            row = negative["sides"][side]
            self.assertTrue(row["rejected"])
            self.assertLessEqual(
                row["observed_cone_separation_rad"], VERTEX_CONTACT_EPSILON_RAD
            )

    def test_truth_boundary_keeps_continuity_and_receivers_held(self):
        truth = sampled_vertex_only_neighbor_contract()["truth_boundary"]
        self.assertTrue(truth["sampled_vertex_only_neighbor_contact_proven"])
        self.assertFalse(truth["continuous_vertex_only_neighbor_contact_proven"])
        self.assertFalse(truth["edge_adjacent_or_nonadjacent_claim_replaced"])
        self.assertFalse(truth["exact_first_contact_angle_solved"])
        self.assertFalse(truth["anatomical_range_of_motion"])
        self.assertFalse(truth["animation_acceptance"])
        self.assertFalse(truth["technical_art_acceptance"])
        self.assertFalse(truth["runtime_acceptance"])
        self.assertFalse(truth["visual_acceptance"])
        self.assertFalse(truth["source_adoption_or_canon"])

    def test_contract_drift_fails_closed(self):
        drifted = sampled_vertex_only_neighbor_contract()
        drifted["sampled_vertex_only_guard"]["regular_step_deg"] = 0.50
        with self.assertRaises(ValueError):
            audit_review006_sampled_vertex_only_neighbor_cone_margin(drifted)


if __name__ == "__main__":
    unittest.main()
