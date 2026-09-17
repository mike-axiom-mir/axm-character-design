import unittest

from axm_character_design.review006_shoulder_deformation_gradient_frame import (
    NEGATIVE_CONTROL_MIN_ANGULAR_ERROR_DEG,
    OWNER_RESIDUAL_TOLERANCE_M,
    ORTHOGONALITY_TOLERANCE,
    STATUS,
    audit_review006_deformation_gradient_frame,
)


class Review006ShoulderDeformationGradientFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_review006_deformation_gradient_frame()

    def test_status_and_exact_boundary(self):
        self.assertEqual(self.audit["status"], STATUS)
        boundary = self.audit["structural_boundary"]
        self.assertTrue(boundary["unchanged"])
        self.assertEqual(boundary["last_sampled_clear_positive_deg"], 36.55)
        self.assertEqual(boundary["first_sampled_failing_positive_deg"], 36.60)

    def test_owner_affine_prediction_matches_pose(self):
        reference = self.audit["deformation_gradient_reference"]
        self.assertLessEqual(
            reference["max_owner_affine_position_residual_m"],
            OWNER_RESIDUAL_TOLERANCE_M,
        )
        self.assertLessEqual(
            reference["max_frame_orthogonality_abs_dot"],
            ORTHOGONALITY_TOLERANCE,
        )
        self.assertGreater(reference["min_frame_handedness_triple_product"], 0.999999999)

    def test_continuous_local_gradient_is_invertible_without_claiming_collision(self):
        reference = self.audit["deformation_gradient_reference"]
        self.assertTrue(reference["continuous_local_gradient_invertible"])
        self.assertGreater(
            reference["continuous_proximal_determinant_lower_bound_minus40_plus40"],
            0.95,
        )
        self.assertEqual(self.audit["gates"]["continuous_collision_freedom"], "NOT_PROVEN")

    def test_naive_rigid_proximal_frame_fails_closed(self):
        negative = self.audit["negative_control"]
        self.assertTrue(negative["rejected"])
        for row in negative["rows"]:
            self.assertGreaterEqual(
                row["naive_full_child_rotation_normal_error_deg"],
                NEGATIVE_CONTROL_MIN_ANGULAR_ERROR_DEG,
            )

    def test_owner_boundaries_remain_separate(self):
        gates = self.audit["gates"]
        self.assertEqual(gates["animation_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["technical_art_transport_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["runtime_acceptance"], "NOT_EVALUATED")
        self.assertEqual(gates["visual_acceptance"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
