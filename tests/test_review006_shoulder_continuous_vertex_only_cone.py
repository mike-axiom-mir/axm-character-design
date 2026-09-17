import unittest

from axm_character_design.review006_shoulder_continuous_clearance import (
    FIRST_SAMPLED_FAILURE_DEG,
    SAFE_END_DEG,
    SAFE_START_DEG,
)
from axm_character_design.review006_shoulder_continuous_vertex_only_cone import (
    CERTIFICATE_MARGIN_RAD,
    STATUS,
    audit_review006_continuous_vertex_only_neighbor_cone,
    continuous_vertex_only_neighbor_contract,
)


class Review006ShoulderContinuousVertexOnlyConeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_continuous_vertex_only_neighbor_cone()

    def test_continuous_vertex_only_guard_passes(self):
        self.assertEqual(self.audit["status"], STATUS)
        guard = self.audit["continuous_vertex_only_neighbor_guard"]
        self.assertEqual(guard["range_deg"], [SAFE_START_DEG, SAFE_END_DEG])
        self.assertTrue(guard["all_real_owner_angles_certified"])
        self.assertTrue(guard["bilateral_pair_count_match"])
        self.assertLessEqual(guard["bilateral_minimum_slack_residual_rad"], 1e-12)
        for side in ("L", "R"):
            result = guard["sides"][side]
            self.assertEqual(result["vertex_only_neighbor_pair_count"], 845)
            self.assertTrue(result["continuous_vertex_only_neighbor_contact_free"])
            self.assertGreater(result["certified_interval_count"], 0)
            self.assertGreater(
                result["minimum_certificate_slack_rad"], CERTIFICATE_MARGIN_RAD
            )

    def test_retained_failure_boundary_is_not_promoted(self):
        retained = self.audit["retained_boundary"]
        self.assertEqual(retained["last_continuously_certified_clear_deg"], SAFE_END_DEG)
        self.assertEqual(
            retained["first_retained_sampled_nonadjacent_failure_deg"],
            FIRST_SAMPLED_FAILURE_DEG,
        )
        self.assertFalse(retained["exact_first_contact_angle_solved"])
        self.assertTrue(self.audit["negative_control"]["rejected"])
        for side in ("L", "R"):
            self.assertTrue(self.audit["negative_control"]["sides"][side]["rejected"])

    def test_truth_boundary_keeps_downstream_authority_held(self):
        truth = continuous_vertex_only_neighbor_contract()["truth_boundary"]
        self.assertTrue(truth["continuous_vertex_only_neighbor_contact_proven"])
        self.assertFalse(truth["nonadjacent_or_edge_adjacent_claim_replaced"])
        self.assertFalse(truth["exact_first_contact_angle_solved"])
        self.assertFalse(truth["anatomical_range_of_motion"])
        self.assertFalse(truth["animation_acceptance"])
        self.assertFalse(truth["technical_art_acceptance"])
        self.assertFalse(truth["runtime_acceptance"])
        self.assertFalse(truth["visual_acceptance"])
        self.assertFalse(truth["source_adoption_or_canon"])

    def test_contract_drift_fails_closed(self):
        drifted = continuous_vertex_only_neighbor_contract()
        drifted["continuous_vertex_only_certificate"]["range_deg"][1] = 36.60
        with self.assertRaises(ValueError):
            audit_review006_continuous_vertex_only_neighbor_cone(drifted)


if __name__ == "__main__":
    unittest.main()
