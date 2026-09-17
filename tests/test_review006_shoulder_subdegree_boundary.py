import copy
import unittest

from axm_character_design.review006_shoulder_subdegree_boundary import (
    END_DEG,
    SAMPLE_COUNT_PER_SIDE,
    START_DEG,
    STATUS,
    STEP_DEG,
    _validate_contract,
    audit_review006_positive_subdegree_boundary,
    boundary_contract,
)


class Review006ShoulderSubdegreeBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_positive_subdegree_boundary()

    def test_subdegree_boundary_probe_is_green(self):
        audit = self.audit
        self.assertEqual(audit["status"], STATUS)
        probe = audit["subdegree_probe"]
        self.assertEqual(probe["range_deg"], [START_DEG, END_DEG])
        self.assertEqual(probe["step_deg"], STEP_DEG)
        self.assertEqual(probe["samples_per_side"], SAMPLE_COUNT_PER_SIDE)
        self.assertEqual(probe["posed_sample_count"], 2 * SAMPLE_COUNT_PER_SIDE)
        self.assertTrue(probe["all_structural_pass"])
        self.assertTrue(probe["bilateral_pose_mirror"])

    def test_integer_endpoints_are_reproduced(self):
        for side in ("L", "R"):
            rows = self.audit["subdegree_probe"]["rows"][side]
            self.assertEqual(rows[0]["angle_deg"], START_DEG)
            self.assertEqual(rows[0]["nonadjacent_intersection_pair_count"], 0)
            self.assertEqual(rows[-1]["angle_deg"], END_DEG)
            self.assertGreater(rows[-1]["nonadjacent_intersection_pair_count"], 0)
        self.assertEqual(self.audit["gates"]["integer_endpoint_reproduction"], "PASS")

    def test_transition_is_bilaterally_bracketed_within_one_sample_step(self):
        boundaries = self.audit["subdegree_probe"]["boundaries"]
        self.assertEqual(boundaries["L"], boundaries["R"])
        boundary = boundaries["L"]
        self.assertIsNotNone(boundary["last_sampled_clear_deg"])
        self.assertIsNotNone(boundary["first_sampled_failure_deg"])
        self.assertLess(boundary["last_sampled_clear_deg"], boundary["first_sampled_failure_deg"])
        self.assertGreater(boundary["transition_bracket_width_deg"], 0.0)
        self.assertLessEqual(boundary["transition_bracket_width_deg"], STEP_DEG + 1e-12)
        self.assertEqual(boundary["last_clear_pair_count"], 0)
        self.assertGreater(boundary["first_failure_pair_count"], 0)
        self.assertEqual(self.audit["gates"]["bilateral_boundary_match"], "PASS")
        self.assertEqual(self.audit["gates"]["transition_bracket_at_most_005deg"], "PASS")

    def test_false_guard_extension_is_rejected(self):
        negative = self.audit["negative_control"]
        self.assertTrue(negative["rejected"])
        self.assertEqual(self.audit["gates"]["guard_negative_control"], "PASS_EXPECTED_REJECTION")
        guard = self.audit["sampled_guard"]
        self.assertLess(
            guard["refined_positive_sampled_guard_max_deg"],
            guard["first_sampled_positive_failure_deg"],
        )

    def test_animation_runtime_and_continuity_are_not_promoted(self):
        gates = self.audit["gates"]
        self.assertEqual(gates["continuous_motion"], "NOT_PROVEN")
        self.assertEqual(gates["anatomical_range_of_motion"], "NOT_CLAIMED")
        self.assertEqual(gates["animation_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["runtime_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["technical_art_transport_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["visual_acceptance"], "NOT_EVALUATED")

    def test_contract_identity_fails_closed(self):
        mutated = copy.deepcopy(boundary_contract())
        mutated["sampling"]["step_deg"] = 0.10
        with self.assertRaisesRegex(ValueError, "contract identity drift"):
            _validate_contract(mutated)


if __name__ == "__main__":
    unittest.main()
