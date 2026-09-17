import unittest

from axm_character_design.review006_shoulder_continuous_clearance import (
    FIRST_SAMPLED_FAILURE_DEG,
    SAFE_END_DEG,
    SAFE_START_DEG,
    STATUS,
    audit_review006_continuous_nonadjacent_clearance,
    continuous_clearance_contract,
)


class Review006ShoulderContinuousClearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_continuous_nonadjacent_clearance()

    def test_continuous_nonadjacent_clearance_is_certified(self):
        self.assertEqual(self.audit["status"], STATUS)
        clearance = self.audit["continuous_clearance"]
        self.assertEqual(clearance["range_deg"], [SAFE_START_DEG, SAFE_END_DEG])
        self.assertTrue(clearance["nonadjacent_triangle_clearance_proven_for_all_real_angles"])
        self.assertTrue(clearance["bilateral_representative_pose_mirror"])
        for side in ("L", "R"):
            result = clearance["sides"][side]
            self.assertTrue(result["certified"])
            self.assertEqual(result["start_endpoint_intersections"], 0)
            self.assertEqual(result["end_endpoint_intersections"], 0)
            self.assertGreater(result["minimum_certificate_slack_m"], 0.0)
            self.assertGreater(result["certified_interval_count"], 0)

    def test_retained_contact_bracket_and_negative_control(self):
        transition = self.audit["contact_transition"]
        self.assertEqual(transition["last_continuously_certified_clear_deg"], SAFE_END_DEG)
        self.assertEqual(transition["first_retained_sampled_failure_deg"], FIRST_SAMPLED_FAILURE_DEG)
        self.assertAlmostEqual(transition["transition_bracket_width_deg"], 0.05, places=10)
        self.assertFalse(transition["exact_contact_angle_solved"])
        for side in ("L", "R"):
            self.assertGreater(
                transition["first_failure_rows"][side]["nonadjacent_intersection_pair_count"],
                0,
            )
        self.assertTrue(self.audit["negative_control"]["rejected"])
        for side in ("L", "R"):
            self.assertEqual(
                self.audit["negative_control"]["side_results"][side]["reason"],
                "END_ENDPOINT_NOT_CLEAR",
            )

    def test_truth_boundary_keeps_animation_and_runtime_held(self):
        contract = continuous_clearance_contract()
        truth = contract["truth_boundary"]
        self.assertTrue(truth["nonadjacent_triangle_continuity_only"])
        self.assertFalse(truth["indexed_neighbor_fold_contact_proven"])
        self.assertFalse(truth["anatomical_range_of_motion"])
        self.assertFalse(truth["animation_acceptance"])
        self.assertFalse(truth["technical_art_transport_acceptance"])
        self.assertFalse(truth["runtime_acceptance"])
        self.assertFalse(truth["visual_acceptance"])
        self.assertFalse(truth["source_adoption_or_canon"])

    def test_contract_drift_fails_closed(self):
        drifted = continuous_clearance_contract()
        drifted["contact_boundary"]["last_continuously_certified_clear_deg"] = 36.60
        with self.assertRaises(ValueError):
            audit_review006_continuous_nonadjacent_clearance(drifted)


if __name__ == "__main__":
    unittest.main()
