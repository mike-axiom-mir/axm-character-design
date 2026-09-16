import unittest

from axm_character_design.organic_form import canonical_digest
from axm_character_design.shoulder_pose_clearance_candidate import (
    ELBOW_X_M,
    ELBOW_Z_M,
    EXPECTED_CANDIDATE_MESH_DIGEST,
    EXPECTED_PARENT_MESH_DIGEST,
    EXPECTED_PARENT_SOURCE_DIGEST,
    SHOULDER_WIDTH_M,
    SHOULDER_X_M,
    STATUS,
    VARIANT_ID,
    audit_shoulder_pose_clearance_candidate,
    shoulder_pose_clearance_candidate,
)
from axm_character_design.shoulder_source_lineage import (
    adopted_character_source,
    build_adopted_character_mesh,
)


class ShoulderPoseClearanceCandidateTests(unittest.TestCase):
    def test_exact_bounded_review_candidate(self):
        candidate = shoulder_pose_clearance_candidate()
        receipt = audit_shoulder_pose_clearance_candidate(candidate)
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(candidate["study_id"], VARIANT_ID)
        self.assertEqual(receipt["parent_source_digest"], EXPECTED_PARENT_SOURCE_DIGEST)
        self.assertEqual(receipt["parent_mesh_digest"], EXPECTED_PARENT_MESH_DIGEST)
        self.assertEqual(receipt["candidate_mesh_digest"], EXPECTED_CANDIDATE_MESH_DIGEST)
        self.assertEqual(receipt["form_metrics"]["vertex_count"], 504)
        self.assertEqual(receipt["form_metrics"]["triangle_count"], 908)
        self.assertEqual(receipt["form_metrics"]["degenerate_triangles"], 0)

    def test_only_intended_landmarks_and_width_move(self):
        parent = adopted_character_source()
        candidate = shoulder_pose_clearance_candidate()
        self.assertEqual(candidate["landmarks"]["shoulder_L"], [-SHOULDER_X_M, 0.0, 1.48])
        self.assertEqual(candidate["landmarks"]["shoulder_R"], [SHOULDER_X_M, 0.0, 1.48])
        self.assertEqual(candidate["landmarks"]["elbow_L"], [-ELBOW_X_M, 0.0, ELBOW_Z_M])
        self.assertEqual(candidate["landmarks"]["elbow_R"], [ELBOW_X_M, 0.0, ELBOW_Z_M])
        self.assertEqual(candidate["design_constraints"]["shoulder_width_m"], SHOULDER_WIDTH_M)
        for name in ("wrist_L", "wrist_R", "hand_tip_L", "hand_tip_R"):
            self.assertEqual(candidate["landmarks"][name], parent["landmarks"][name])
        self.assertEqual(candidate["masses"], parent["masses"])
        self.assertEqual(candidate["segments"], parent["segments"])
        self.assertEqual(candidate["flex_zones"], parent["flex_zones"])

    def test_accepted_e_transition_semantics_are_exactly_preserved(self):
        parent = adopted_character_source()
        candidate = shoulder_pose_clearance_candidate()
        self.assertEqual(candidate["shoulder_transition_repair"], parent["shoulder_transition_repair"])
        self.assertEqual(candidate["shoulder_transition_regions"], parent["shoulder_transition_regions"])

    def test_candidate_proof_mesh_identity_is_deterministic(self):
        first = build_adopted_character_mesh(shoulder_pose_clearance_candidate())
        second = build_adopted_character_mesh(shoulder_pose_clearance_candidate())
        self.assertEqual(canonical_digest(first), canonical_digest(second))
        self.assertEqual(canonical_digest(first), EXPECTED_CANDIDATE_MESH_DIGEST)

    def test_outside_delta_drift_fails_closed(self):
        candidate = shoulder_pose_clearance_candidate()
        candidate["landmarks"]["wrist_R"][2] += 0.001
        with self.assertRaisesRegex(ValueError, "outside bounded shoulder/elbow delta"):
            audit_shoulder_pose_clearance_candidate(candidate)

    def test_e_transition_drift_fails_closed(self):
        candidate = shoulder_pose_clearance_candidate()
        candidate["shoulder_transition_repair"]["blend_weights"][0] = 0.41
        with self.assertRaises(ValueError):
            audit_shoulder_pose_clearance_candidate(candidate)

    def test_truth_state_cannot_be_silently_promoted(self):
        candidate = shoulder_pose_clearance_candidate()
        candidate["shoulder_pose_clearance_review"]["status"] = "ADOPTED"
        with self.assertRaisesRegex(ValueError, "truth-state drift"):
            audit_shoulder_pose_clearance_candidate(candidate)


if __name__ == "__main__":
    unittest.main()
