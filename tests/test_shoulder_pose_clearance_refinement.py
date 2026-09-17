import unittest

from axm_character_design.organic_form import canonical_digest
from axm_character_design.shoulder_pose_clearance_candidate import shoulder_pose_clearance_candidate
from axm_character_design.shoulder_pose_clearance_refinement import (
    ELBOW_X_M,
    ELBOW_Z_M,
    MIN_REVIEW005_FLEX_REDUCTION_DEG,
    STATUS,
    VARIANT_ID,
    audit_shoulder_pose_clearance_refinement,
    shoulder_pose_clearance_refinement_candidate,
)
from axm_character_design.shoulder_source_lineage import build_adopted_character_mesh


class ShoulderPoseClearanceRefinementTests(unittest.TestCase):
    def test_exact_bounded_review_refinement(self):
        candidate = shoulder_pose_clearance_refinement_candidate()
        receipt = audit_shoulder_pose_clearance_refinement(candidate)
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(candidate["study_id"], VARIANT_ID)
        self.assertEqual(receipt["form_metrics"]["vertex_count"], 504)
        self.assertEqual(receipt["form_metrics"]["triangle_count"], 908)
        self.assertEqual(receipt["form_metrics"]["degenerate_triangles"], 0)
        self.assertGreaterEqual(
            receipt["form_metrics"]["review005_minus_candidate_flexion_deg"],
            MIN_REVIEW005_FLEX_REDUCTION_DEG,
        )

    def test_only_elbows_move_relative_to_review005(self):
        review005 = shoulder_pose_clearance_candidate()
        candidate = shoulder_pose_clearance_refinement_candidate()
        self.assertEqual(candidate["landmarks"]["elbow_L"], [-ELBOW_X_M, 0.0, ELBOW_Z_M])
        self.assertEqual(candidate["landmarks"]["elbow_R"], [ELBOW_X_M, 0.0, ELBOW_Z_M])
        for name in ("shoulder_L", "shoulder_R", "wrist_L", "wrist_R", "hand_tip_L", "hand_tip_R"):
            self.assertEqual(candidate["landmarks"][name], review005["landmarks"][name])
        self.assertEqual(candidate["masses"], review005["masses"])
        self.assertEqual(candidate["segments"], review005["segments"])
        self.assertEqual(candidate["flex_zones"], review005["flex_zones"])

    def test_candidate_mesh_is_deterministic(self):
        first = build_adopted_character_mesh(shoulder_pose_clearance_refinement_candidate())
        second = build_adopted_character_mesh(shoulder_pose_clearance_refinement_candidate())
        self.assertEqual(canonical_digest(first), canonical_digest(second))

    def test_refinement_preserves_review005_a_rest_line_and_segment_bound(self):
        receipt = audit_shoulder_pose_clearance_refinement()
        metrics = receipt["form_metrics"]
        self.assertEqual(metrics["candidate_a_rest_down_angle_deg"], metrics["review005_a_rest_down_angle_deg"])
        for value in metrics["candidate_vs_parent_segment_length_delta_ratios"].values():
            self.assertLessEqual(abs(value), 0.01)
        self.assertLess(
            metrics["candidate_flexion_from_straight_deg"],
            metrics["review005_flexion_from_straight_deg"],
        )

    def test_protected_landmark_drift_fails_closed(self):
        candidate = shoulder_pose_clearance_refinement_candidate()
        candidate["landmarks"]["wrist_R"][2] += 0.001
        with self.assertRaises(ValueError):
            audit_shoulder_pose_clearance_refinement(candidate)

    def test_truth_state_cannot_be_silently_promoted(self):
        candidate = shoulder_pose_clearance_refinement_candidate()
        candidate["shoulder_pose_clearance_refinement"]["status"] = "ADOPTED"
        with self.assertRaisesRegex(ValueError, "truth-state drift"):
            audit_shoulder_pose_clearance_refinement(candidate)


if __name__ == "__main__":
    unittest.main()
