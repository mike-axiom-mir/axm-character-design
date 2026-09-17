import copy
import unittest

from axm_character_design.organic_form import canonical_digest
from axm_character_design.review006_shoulder_rigging_rebind import (
    EXPECTED_PROFILE_DIGEST,
    EXPECTED_TOPOLOGY_DIGESTS,
    REPRESENTATIVE_ANGLES_DEG,
    STATUS,
    _validate_contract,
    audit_review006_rigging_rebind,
    historical_successor_profile,
    rebind_contract,
    release_weight,
)


class Review006ShoulderRiggingRebindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_rigging_rebind()

    def test_exact_historical_profile_identity_is_preserved(self):
        self.assertEqual(canonical_digest(historical_successor_profile()), EXPECTED_PROFILE_DIGEST)
        self.assertEqual(release_weight(0.0), 0.0)
        self.assertEqual(release_weight(-40.0), 0.10)
        self.assertEqual(release_weight(40.0), 0.10)
        self.assertEqual(release_weight(-20.0), release_weight(20.0))

    def test_exact_review006_receiver_is_bound(self):
        audit = self.audit
        self.assertEqual(audit["status"], STATUS)
        self.assertEqual(audit["exact_identity"]["topology_digests"], EXPECTED_TOPOLOGY_DIGESTS)
        self.assertEqual(audit["sample_scope"]["candidate_pose_count"], 162)
        self.assertEqual(audit["sample_scope"]["representative_angles_deg"], list(REPRESENTATIVE_ANGLES_DEG))
        self.assertFalse(audit["sample_scope"]["continuous_interpolation_proven"])

    def test_full_sampled_structural_envelope_and_neutral_gate(self):
        audit = self.audit
        self.assertEqual(audit["gates"]["all_162_structural_samples"], "PASS")
        self.assertEqual(audit["gates"]["bilateral_mirror"], "PASS")
        self.assertEqual(audit["gates"]["neutral_geometry_intersection_reproduction"], "PASS")
        self.assertTrue(audit["nonadjacent_self_intersection"]["neutral_bilateral_zero"])
        for side in ("L", "R"):
            self.assertEqual(len(audit["results"][side]["candidate"]), 81)
            self.assertEqual(audit["results"][side]["topology_digest"], EXPECTED_TOPOLOGY_DIGESTS[side])

    def test_truth_boundary_keeps_animation_and_runtime_unaccepted(self):
        gates = self.audit["gates"]
        self.assertEqual(gates["animation_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["runtime_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["source_adoption"], "NOT_CLAIMED")

    def test_contract_identity_fails_closed(self):
        mutated = copy.deepcopy(rebind_contract())
        mutated["rig_method"]["joint_semantics"]["L"]["axis"] = [0.0, 1.0, 0.0]
        with self.assertRaisesRegex(ValueError, "contract identity drift"):
            _validate_contract(mutated)


if __name__ == "__main__":
    unittest.main()
