import copy
import unittest

from axm_character_design.review006_shoulder_animation_diagnostic import (
    AMPLITUDE_DEG,
    AUTHORED_SAMPLE_COUNT,
    DENSE_SAMPLE_COUNT,
    EXPECTED_LAST_CLEAR_POSITIVE_DEG,
    FAIL_STATUS,
    STATUS,
    _validate_contract,
    animation_contract,
    audit_review006_shoulder_animation,
)


class Review006ShoulderAnimationDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_shoulder_animation()

    def test_dense_animation_diagnostic_is_green(self):
        audit = self.audit
        self.assertEqual(audit["status"], STATUS)
        motion = audit["motion"]
        self.assertEqual(motion["authored_sample_count"], AUTHORED_SAMPLE_COUNT)
        self.assertEqual(motion["dense_sample_count"], DENSE_SAMPLE_COUNT)
        self.assertTrue(motion["all_dense_structural_pass"])
        self.assertTrue(motion["all_dense_nonadjacent_intersection_free"])
        self.assertTrue(motion["all_dense_bilateral_mirror"])
        self.assertTrue(motion["monotonic_within_each_phase"])
        self.assertTrue(motion["exact_phase_extrema_and_neutral_endpoints"])

    def test_clip_stays_inside_bounded_rigging_review_surface(self):
        audit = self.audit
        boundary = audit["rigging_boundary_prerequisite"]
        self.assertEqual(boundary["animation_positive_amplitude_deg"], AMPLITUDE_DEG)
        self.assertEqual(boundary["last_sampled_clear_positive_deg"], EXPECTED_LAST_CLEAR_POSITIVE_DEG)
        self.assertGreater(boundary["margin_below_last_sampled_clear_positive_deg"], 0.0)
        self.assertEqual(audit["motion"]["maximum_nonadjacent_intersection_pairs"], {"L": 0, "R": 0})

    def test_loop_and_authored_dense_subset_close_exactly(self):
        motion = self.audit["motion"]
        self.assertLessEqual(motion["loop_max_vertex_residual_m"]["L"], 1e-12)
        self.assertLessEqual(motion["loop_max_vertex_residual_m"]["R"], 1e-12)
        self.assertLessEqual(motion["authored_subset_max_angle_residual_deg"], 1e-12)
        self.assertEqual(self.audit["gates"]["exact_loop_closure"], "PASS")
        self.assertEqual(self.audit["gates"]["authored_keys_are_dense_subset"], "PASS")

    def test_source_curve_phase_joins_are_zero_velocity_and_acceleration(self):
        kinematics = self.audit["motion"]["source_curve_boundary_kinematics"]
        self.assertEqual(kinematics["angle_deg"], [0.0, -AMPLITUDE_DEG, 0.0, AMPLITUDE_DEG, 0.0])
        self.assertEqual(kinematics["analytic_velocity_deg_s"], [0.0] * 5)
        self.assertEqual(kinematics["analytic_acceleration_deg_s2"], [0.0] * 5)

    def test_hidden_between_key_overshoot_fails_closed(self):
        negative = self.audit["negative_control"]
        self.assertLessEqual(negative["authored_key_max_angle_residual_deg"], 1e-12)
        self.assertGreaterEqual(negative["max_mutated_dense_angle_deg"], negative["target_midpoint_angle_deg"] - 1e-12)
        self.assertGreater(negative["dense_failure_count"], 0)
        self.assertIsNotNone(negative["first_dense_failure"])
        self.assertTrue(negative["rejected"])
        self.assertEqual(self.audit["gates"]["hidden_subframe_overshoot_control"], "PASS_EXPECTED_REJECTION")

    def test_animation_does_not_promote_runtime_or_gameplay(self):
        gates = self.audit["gates"]
        self.assertEqual(gates["mathematical_continuity"], "NOT_PROVEN")
        self.assertEqual(gates["target_engine_interpolation"], "NOT_EVALUATED")
        self.assertEqual(gates["target_engine_playback"], "NOT_EVALUATED")
        self.assertEqual(gates["technical_art_transport"], "NOT_EVALUATED")
        self.assertEqual(gates["runtime_controller"], "NOT_EVALUATED")
        self.assertEqual(gates["gameplay"], "NOT_EVALUATED")
        self.assertEqual(gates["final_visual_acceptance"], "NOT_EVALUATED")

    def test_contract_identity_fails_closed(self):
        mutated = copy.deepcopy(animation_contract())
        mutated["clip"]["amplitude_deg"] = 31.0
        with self.assertRaisesRegex(ValueError, "Animation diagnostic contract identity drift"):
            _validate_contract(mutated)

    def test_fail_status_constant_is_distinct(self):
        self.assertNotEqual(STATUS, FAIL_STATUS)


if __name__ == "__main__":
    unittest.main()
