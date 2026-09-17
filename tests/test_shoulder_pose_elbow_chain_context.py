import unittest

from axm_character_design.shoulder_pose_elbow_chain_context import (
    EXPECTED_CANDIDATE,
    EXPECTED_FLEXION_INCREASE_DEG,
    EXPECTED_PARENT,
    STATUS,
    audit_shoulder_pose_elbow_chain_context,
)


class ShoulderPoseElbowChainContextTests(unittest.TestCase):
    def test_exact_bilateral_neutral_elbow_chain_context(self):
        receipt = audit_shoulder_pose_elbow_chain_context()
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(receipt["parent_elbow_chain_context"], EXPECTED_PARENT)
        self.assertEqual(receipt["candidate_elbow_chain_context"], EXPECTED_CANDIDATE)
        self.assertEqual(
            receipt["candidate_minus_parent_flexion_from_straight_deg"],
            EXPECTED_FLEXION_INCREASE_DEG,
        )
        self.assertTrue(receipt["bilateral_source_context"])

    def test_landmark_chain_context_is_not_promoted(self):
        receipt = audit_shoulder_pose_elbow_chain_context()
        self.assertEqual(
            receipt["gates"]["landmark_chain_change_interpretation"],
            "RECORDED_NOT_AUTOMATIC_DEFECT_OR_ACCEPTANCE",
        )
        self.assertEqual(receipt["gates"]["visual_acceptance"], "NOT_EVALUATED")
        self.assertEqual(
            receipt["gates"]["rigging_or_joint_rest_acceptance"], "NOT_EVALUATED"
        )
        self.assertEqual(receipt["gates"]["source_adoption"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
