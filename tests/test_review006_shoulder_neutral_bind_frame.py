import unittest

from axm_character_design.review006_shoulder_neutral_bind_frame import (
    NEGATIVE_CONTROL_MIN_MATRIX_DELTA,
    NEGATIVE_CONTROL_MIN_VERTEX_DRIFT_M,
    NEUTRAL_TOLERANCE,
    STATUS,
    audit_review006_neutral_bind_frame,
)


class Review006ShoulderNeutralBindFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_neutral_bind_frame()

    def test_status_and_exact_receiver_coverage(self):
        self.assertEqual(self.audit["status"], STATUS)
        neutral = self.audit["neutral_closure"]
        self.assertEqual(neutral["total_receiver_vertices"], 184)
        self.assertEqual(neutral["neutral_proximal_release_weight"], 0.0)
        self.assertEqual(len(neutral["group_rows"]), 10)

    def test_neutral_owner_pose_and_frames_close_to_identity(self):
        neutral = self.audit["neutral_closure"]
        self.assertTrue(neutral["all_receiver_vertices_close_to_source"])
        self.assertLessEqual(neutral["max_owner_vertex_drift_m"], NEUTRAL_TOLERANCE)
        self.assertLessEqual(
            neutral["max_gradient_identity_component_delta"],
            NEUTRAL_TOLERANCE,
        )
        self.assertLessEqual(
            neutral["max_normal_matrix_identity_component_delta"],
            NEUTRAL_TOLERANCE,
        )

    def test_hidden_non_neutral_joint_offset_fails_closed(self):
        negative = self.audit["negative_control"]
        self.assertTrue(negative["rejected"])
        for row in negative["rows"]:
            self.assertGreaterEqual(row["max_vertex_drift_m"], NEGATIVE_CONTROL_MIN_VERTEX_DRIFT_M)
            self.assertGreaterEqual(
                row["distal_gradient_identity_max_component_delta"],
                NEGATIVE_CONTROL_MIN_MATRIX_DELTA,
            )

    def test_structural_motion_boundary_is_not_widened(self):
        boundary = self.audit["representative_motion_boundary"]
        self.assertTrue(boundary["structural_boundary_unchanged"])
        self.assertEqual(boundary["last_sampled_clear_positive_deg"], 36.55)
        self.assertEqual(boundary["first_sampled_failing_positive_deg"], 36.60)
        self.assertEqual(boundary["representative_non_neutral_angles_deg"], [-30.0, 30.0])

    def test_downstream_authority_remains_held(self):
        gates = self.audit["gates"]
        self.assertEqual(gates["target_engine_bind_or_inverse_bind"], "NOT_EVALUATED")
        self.assertEqual(gates["target_engine_direction_frame"], "NOT_EVALUATED")
        self.assertEqual(gates["neutral_shaded_mismatch_explanation"], "NOT_ESTABLISHED")
        self.assertEqual(gates["animation_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["runtime_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["visual_acceptance"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
