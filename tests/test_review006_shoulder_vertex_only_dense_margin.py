import unittest

from axm_character_design.review006_shoulder_continuous_clearance import (
    FIRST_SAMPLED_FAILURE_DEG,
    SAFE_END_DEG,
    SAFE_START_DEG,
)
from axm_character_design.review006_shoulder_vertex_only_dense_margin import (
    DENSE_STEP_DEG,
    STATUS,
    audit_review006_dense_vertex_only_neighbor_cone_margin,
    dense_vertex_only_neighbor_contract,
)
from axm_character_design.review006_shoulder_vertex_only_neighbor_cone_margin import (
    VERTEX_CONTACT_EPSILON_RAD,
)


class Review006ShoulderVertexOnlyDenseMarginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_dense_vertex_only_neighbor_cone_margin()

    def test_dense_vertex_only_guard_passes(self):
        self.assertEqual(self.audit["status"], STATUS)
        guard = self.audit["dense_sampled_vertex_only_guard"]
        self.assertEqual(guard["range_deg"], [SAFE_START_DEG, SAFE_END_DEG])
        self.assertEqual(guard["step_deg"], DENSE_STEP_DEG)
        self.assertEqual(guard["sample_count_per_side"], 1532)
        self.assertTrue(guard["all_sampled_vertex_only_pairs_cone_separated"])
        self.assertTrue(guard["bilateral_pair_count_match"])
        self.assertTrue(guard["bilateral_representative_pose_mirror"])
        self.assertLessEqual(
            guard["bilateral_minimum_cone_separation_residual_rad"], 1e-12
        )
        for side in ("L", "R"):
            result = guard["sides"][side]
            self.assertEqual(result["sample_count"], 1532)
            self.assertEqual(result["vertex_only_neighbor_pair_count"], 845)
            self.assertEqual(result["uncertified_sample_count"], 0)
            self.assertGreater(
                result["minimum_sampled_cone_separation_rad"],
                VERTEX_CONTACT_EPSILON_RAD,
            )

    def test_retained_failure_pose_remains_outside_dense_guard(self):
        retained = self.audit["retained_boundary"]
        self.assertEqual(
            retained["first_retained_nonadjacent_failure_deg"],
            FIRST_SAMPLED_FAILURE_DEG,
        )
        self.assertTrue(
            retained["vertex_only_cone_predicate_uncertified_at_failure_pose_both_sides"]
        )
        for side in ("L", "R"):
            outside = self.audit["dense_sampled_vertex_only_guard"]["sides"][side][
                "outside_boundary"
            ]
            self.assertEqual(outside["angle_deg"], FIRST_SAMPLED_FAILURE_DEG)
            self.assertGreater(outside["uncertified_pair_count"], 0)

    def test_inherited_negative_control_remains_rejected(self):
        negative = self.audit["negative_control"]
        self.assertTrue(negative["rejected"])
        for side in ("L", "R"):
            self.assertTrue(negative["sides"][side]["rejected"])

    def test_truth_boundary_keeps_continuity_and_downstream_held(self):
        truth = dense_vertex_only_neighbor_contract()["truth_boundary"]
        self.assertTrue(truth["dense_sampled_vertex_only_neighbor_contact_proven"])
        self.assertFalse(truth["continuous_vertex_only_neighbor_contact_proven"])
        self.assertFalse(truth["exact_first_contact_angle_solved"])
        self.assertFalse(truth["anatomical_range_of_motion"])
        self.assertFalse(truth["animation_acceptance"])
        self.assertFalse(truth["technical_art_acceptance"])
        self.assertFalse(truth["runtime_acceptance"])
        self.assertFalse(truth["visual_acceptance"])
        self.assertFalse(truth["source_adoption_or_canon"])

    def test_contract_drift_fails_closed(self):
        drifted = dense_vertex_only_neighbor_contract()
        drifted["dense_sampled_vertex_only_guard"]["step_deg"] = 0.10
        with self.assertRaises(ValueError):
            audit_review006_dense_vertex_only_neighbor_cone_margin(drifted)


if __name__ == "__main__":
    unittest.main()
