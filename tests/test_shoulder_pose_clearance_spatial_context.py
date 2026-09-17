import unittest

from axm_character_design.shoulder_pose_clearance_refinement import shoulder_pose_clearance_refinement_candidate
from axm_character_design.shoulder_pose_clearance_spatial_context import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    STATUS,
    audit_shoulder_pose_clearance_spatial_context,
    landmark_chain_spatial_context,
)
from axm_character_design.organic_form import canonical_digest
from axm_character_design.shoulder_source_lineage import build_adopted_character_mesh


class ShoulderPoseClearanceSpatialContextTests(unittest.TestCase):
    def test_exact_review006_spatial_context_is_retained(self):
        receipt = audit_shoulder_pose_clearance_spatial_context()
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(
            receipt["identities"]["review006_source_digest"],
            EXPECTED_REVIEW006_SOURCE_DIGEST,
        )
        self.assertEqual(
            receipt["identities"]["review006_mesh_digest"],
            EXPECTED_REVIEW006_MESH_DIGEST,
        )
        delta = receipt["review006_vs_review005"]
        self.assertAlmostEqual(delta["shoulder_to_wrist_chord_residual_m"], 0.0, places=12)
        self.assertGreater(delta["elbow_perpendicular_offset_reduction_m"], 0.010)
        self.assertGreater(delta["elbow_perpendicular_offset_reduction_ratio"], 0.20)
        self.assertGreater(delta["landmark_chain_excess_reduction_m"], 0.0)
        self.assertEqual(receipt["gates"]["visual_acceptance"], "NOT_EVALUATED")
        self.assertEqual(
            receipt["gates"]["connected_topology_or_intersection_rebind"],
            "NOT_EVALUATED",
        )
        self.assertEqual(receipt["gates"]["rigging_or_deformation_rebind"], "NOT_EVALUATED")
        self.assertEqual(receipt["gates"]["source_adoption"], "NOT_CLAIMED")

    def test_exact_review006_identity_matches_retained_closure(self):
        review006 = shoulder_pose_clearance_refinement_candidate()
        self.assertEqual(canonical_digest(review006), EXPECTED_REVIEW006_SOURCE_DIGEST)
        self.assertEqual(
            canonical_digest(build_adopted_character_mesh(review006)),
            EXPECTED_REVIEW006_MESH_DIGEST,
        )

    def test_straightened_control_has_zero_offset(self):
        review006 = shoulder_pose_clearance_refinement_candidate()
        shoulder = review006["landmarks"]["shoulder_R"]
        wrist = review006["landmarks"]["wrist_R"]
        control = dict(review006)
        control["landmarks"] = dict(review006["landmarks"])
        control["landmarks"]["elbow_R"] = [
            shoulder[i] + 0.55 * (wrist[i] - shoulder[i]) for i in range(3)
        ]
        context = landmark_chain_spatial_context(control, "R")
        self.assertAlmostEqual(context["elbow_perpendicular_offset_from_chord_m"], 0.0, places=12)
        self.assertAlmostEqual(context["landmark_chain_excess_over_chord_m"], 0.0, places=12)


if __name__ == "__main__":
    unittest.main()
