import tempfile
import unittest
from pathlib import Path

from axm_character_design.shoulder_pose_clearance_visual_review import (
    STATUS,
    VIEWS,
    audit_shoulder_pose_clearance_visual_review,
    build_shoulder_pose_clearance_visual_review_evidence,
)
from axm_character_design.shoulder_pose_clearance_candidate import (
    EXPECTED_CANDIDATE_MESH_DIGEST,
    EXPECTED_CANDIDATE_SOURCE_DIGEST,
    EXPECTED_PARENT_MESH_DIGEST,
    EXPECTED_PARENT_SOURCE_DIGEST,
    VARIANT_ID,
)


class ShoulderPoseClearanceVisualReviewTests(unittest.TestCase):
    def test_exact_review_packet_identity_and_truth_boundary(self):
        receipt = audit_shoulder_pose_clearance_visual_review()
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(receipt["review_candidate"], VARIANT_ID)
        self.assertEqual(receipt["parent_source_digest"], EXPECTED_PARENT_SOURCE_DIGEST)
        self.assertEqual(receipt["parent_mesh_digest"], EXPECTED_PARENT_MESH_DIGEST)
        self.assertEqual(receipt["candidate_source_digest"], EXPECTED_CANDIDATE_SOURCE_DIGEST)
        self.assertEqual(receipt["candidate_mesh_digest"], EXPECTED_CANDIDATE_MESH_DIGEST)
        self.assertEqual(receipt["gates"]["visual_acceptance"], "NOT_EVALUATED")
        self.assertEqual(receipt["gates"]["connected_topology_rebind"], "NOT_EVALUATED")
        self.assertEqual(receipt["gates"]["rigging_or_deformation_rebind"], "NOT_EVALUATED")
        self.assertEqual(receipt["gates"]["source_adoption"], "NOT_CLAIMED")

    def test_build_retains_exact_neutral_filled_review_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = build_shoulder_pose_clearance_visual_review_evidence(tmp)
            out = Path(tmp)
            self.assertTrue((out / "shoulder-pose-clearance-visual-review.json").is_file())
            self.assertEqual(len(receipt["neutral_filled_views"]), len(VIEWS))
            for view in VIEWS:
                path = out / f"shoulder-pose-clearance-filled-{view}.svg"
                self.assertTrue(path.is_file())
                text = path.read_text(encoding="utf-8")
                self.assertIn("Parent accepted E", text)
                self.assertIn("Review candidate 005", text)


if __name__ == "__main__":
    unittest.main()
