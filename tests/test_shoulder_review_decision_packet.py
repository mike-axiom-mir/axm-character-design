import unittest

from axm_character_design.shoulder_review_decision_packet import (
    GEOMETRY_PR15_HEAD,
    STATUS,
    audit_shoulder_review_decision_packet,
)
from axm_character_design.shoulder_pose_clearance_spatial_context import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
)


class ShoulderReviewDecisionPacketTests(unittest.TestCase):
    def test_packet_pins_exact_review006_and_keeps_form_frozen(self):
        receipt = audit_shoulder_review_decision_packet()
        self.assertEqual(receipt["status"], STATUS)
        self.assertTrue(receipt["form_is_frozen"])
        self.assertEqual(
            receipt["identities"]["review006_source_digest"],
            EXPECTED_REVIEW006_SOURCE_DIGEST,
        )
        self.assertEqual(
            receipt["identities"]["review006_mesh_digest"],
            EXPECTED_REVIEW006_MESH_DIGEST,
        )
        self.assertEqual(
            [row["landmark"] for row in receipt["changed_landmarks_from_accepted_E_parent"]],
            ["elbow_L", "elbow_R", "shoulder_L", "shoulder_R"],
        )

    def test_packet_keeps_geometry_and_rigging_authority_separate(self):
        receipt = audit_shoulder_review_decision_packet()
        geometry = receipt["separate_geometry_context"]
        self.assertEqual(geometry["geometry_pr15_head"], GEOMETRY_PR15_HEAD)
        self.assertEqual(geometry["inheritance"], "FORBIDDEN")
        self.assertEqual(receipt["gates"]["visual_acceptance"], "NOT_EVALUATED")
        self.assertEqual(
            receipt["gates"]["connected_topology_or_self_intersection"],
            "NOT_EVALUATED",
        )
        self.assertEqual(receipt["gates"]["rigging_or_deformation"], "NOT_EVALUATED")
        self.assertEqual(receipt["gates"]["source_adoption"], "NOT_CLAIMED")

    def test_packet_exposes_existing_review006_tradeoff_without_anatomy_claim(self):
        receipt = audit_shoulder_review_decision_packet()
        metrics = receipt["exact_form_context"]
        self.assertAlmostEqual(
            metrics["accepted_E_parent_elbow_flexion_from_straight_deg"],
            2.082565279731,
            places=12,
        )
        self.assertAlmostEqual(
            metrics["review006_elbow_flexion_from_straight_deg"],
            16.053919502336,
            places=12,
        )
        self.assertGreater(
            metrics["review006_vs_review005_elbow_chord_offset_reduction_m"],
            0.010,
        )
        self.assertTrue(
            any("not anatomy" in item.lower() for item in receipt["truth_boundary"])
        )


if __name__ == "__main__":
    unittest.main()
