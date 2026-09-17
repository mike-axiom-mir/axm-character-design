import copy
import unittest

from axm_character_design.review006_shoulder_safe_envelope import (
    FIRST_UNSAFE_POSITIVE_DEG,
    SAFE_MAX_DEG,
    SAFE_MIN_DEG,
    STATUS,
    _validate_contract,
    audit_review006_structural_safe_envelope,
    envelope_contract,
)


class Review006ShoulderSafeEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_structural_safe_envelope()

    def test_measured_safe_envelope_is_green(self):
        audit = self.audit
        self.assertEqual(audit["status"], STATUS)
        self.assertEqual(audit["safe_envelope"]["range_deg"], [SAFE_MIN_DEG, SAFE_MAX_DEG])
        self.assertEqual(audit["safe_envelope"]["sampled_pose_count"], 154)
        self.assertTrue(audit["safe_envelope"]["all_structural_pass"])
        self.assertTrue(audit["safe_envelope"]["all_nonadjacent_intersection_free"])
        self.assertEqual(audit["gates"]["safe_envelope_154_sample_structural_gate"], "PASS")
        self.assertEqual(audit["gates"]["safe_envelope_154_sample_nonadjacent_intersection_gate"], "PASS")

    def test_first_outside_positive_sample_is_retained_failure_witness(self):
        witness = self.audit["outside_envelope_witness"]
        self.assertEqual(witness["first_positive_sample_deg"], FIRST_UNSAFE_POSITIVE_DEG)
        self.assertTrue(witness["confirmed_nonzero_on_both_sides"])
        self.assertEqual(len(witness["rows"]), 2)
        self.assertTrue(all(row["pair_count"] > 0 for row in witness["rows"]))
        self.assertEqual(self.audit["gates"]["first_outside_envelope_positive_witness"], "PASS_EXPECTED_FAILURE")

    def test_safe_boundaries_still_improve_anchored_control(self):
        boundary = self.audit["boundary_control"]
        self.assertTrue(boundary["all_nonworse"])
        self.assertTrue(boundary["all_strictly_improve"])
        self.assertEqual(self.audit["gates"]["safe_boundary_vs_anchored_control"], "PASS")

    def test_animation_and_runtime_are_not_promoted(self):
        gates = self.audit["gates"]
        self.assertEqual(gates["continuous_motion"], "NOT_PROVEN")
        self.assertEqual(gates["anatomical_range_of_motion"], "NOT_CLAIMED")
        self.assertEqual(gates["animation_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["runtime_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["source_adoption"], "NOT_CLAIMED")

    def test_constraint_identity_fails_closed(self):
        mutated = copy.deepcopy(envelope_contract())
        mutated["constraint"]["safe_sampled_local_delta_deg"][1] = 37.0
        with self.assertRaisesRegex(ValueError, "contract identity drift"):
            _validate_contract(mutated)


if __name__ == "__main__":
    unittest.main()
