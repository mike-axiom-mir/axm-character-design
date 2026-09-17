import unittest

from axm_character_design.organic_form import canonical_digest, neutral_character_study
from axm_character_design.shoulder_bridge_candidate import (
    CANDIDATE_STUDY_ID,
    STATUS,
    audit_shoulder_bridge,
    shoulder_bridge_candidate,
)


class ShoulderBridgeCandidateTests(unittest.TestCase):
    def test_candidate_preserves_baseline_source_and_adds_only_transition_regions(self):
        baseline = neutral_character_study()
        baseline_digest = canonical_digest(baseline)
        candidate = shoulder_bridge_candidate(baseline)
        self.assertEqual(canonical_digest(baseline), baseline_digest)
        self.assertEqual(candidate["study_id"], CANDIDATE_STUDY_ID)
        self.assertEqual(candidate["landmarks"], baseline["landmarks"])
        self.assertEqual(candidate["segments"], baseline["segments"])
        self.assertEqual(candidate["masses"], baseline["masses"])
        self.assertEqual(candidate["flex_zones"], baseline["flex_zones"])
        self.assertEqual(
            [item["id"] for item in candidate["shoulder_transition_regions"]],
            ["shoulder_bridge_L", "shoulder_bridge_R"],
        )

    def test_audit_records_local_transition_without_global_pose_or_bounds_drift(self):
        receipt = audit_shoulder_bridge()
        self.assertEqual(receipt["status"], STATUS)
        self.assertTrue(receipt["form_metrics"]["whole_body_bounds_unchanged"])
        self.assertEqual(receipt["form_metrics"]["baseline_vertices"], 472)
        self.assertEqual(receipt["form_metrics"]["candidate_vertices"], 516)
        self.assertEqual(receipt["form_metrics"]["baseline_triangles"], 880)
        self.assertEqual(receipt["form_metrics"]["candidate_triangles"], 960)
        self.assertEqual(receipt["form_metrics"]["added_vertices"], 44)
        self.assertEqual(receipt["form_metrics"]["added_triangles"], 80)
        self.assertEqual(
            receipt["form_metrics"]["baseline_a_rest_down_angle_deg"],
            receipt["form_metrics"]["candidate_a_rest_down_angle_deg"],
        )
        for side in receipt["shoulder_transition_observations"]:
            self.assertEqual(side["original_upper_arm_root_ring_samples_inside_or_on_ribcage"], 2)
            self.assertEqual(side["bridge_proximal_ring_samples_inside_or_on_ribcage"], 6)
            self.assertEqual(side["bridge_distal_radius_m"], side["upper_arm_root_radius_m"])
            self.assertLessEqual(side["bridge_anchor_ribcage_implicit"], 1.0)

    def test_deterministic_candidate_and_receipt(self):
        first = shoulder_bridge_candidate()
        second = shoulder_bridge_candidate()
        self.assertEqual(canonical_digest(first), canonical_digest(second))
        self.assertEqual(audit_shoulder_bridge(first), audit_shoulder_bridge(second))

    def test_rejects_bilateral_bridge_anchor_drift(self):
        candidate = shoulder_bridge_candidate()
        candidate["shoulder_transition_regions"][1]["anchor"][0] = 0.18
        with self.assertRaisesRegex(ValueError, "bilateral x drift"):
            audit_shoulder_bridge(candidate)

    def test_rejects_detached_bridge_anchor(self):
        candidate = shoulder_bridge_candidate()
        candidate["shoulder_transition_regions"][0]["anchor"][0] = -0.38
        candidate["shoulder_transition_regions"][1]["anchor"][0] = 0.38
        with self.assertRaisesRegex(ValueError, "anchor detached from ribcage"):
            audit_shoulder_bridge(candidate)

    def test_rejects_insufficient_proximal_ring_overlap(self):
        candidate = shoulder_bridge_candidate()
        for bridge in candidate["shoulder_transition_regions"]:
            bridge["radius_anchor_m"] = 0.14
        with self.assertRaisesRegex(ValueError, "insufficient bridge proximal-ring ribcage overlap"):
            audit_shoulder_bridge(candidate)

    def test_rejects_bridge_to_upper_arm_radius_mismatch(self):
        candidate = shoulder_bridge_candidate()
        for bridge in candidate["shoulder_transition_regions"]:
            bridge["radius_shoulder_m"] = 0.07
        with self.assertRaisesRegex(ValueError, "bridge-to-upper-arm radius mismatch"):
            audit_shoulder_bridge(candidate)

    def test_rejects_baseline_landmark_drift(self):
        candidate = shoulder_bridge_candidate()
        candidate["landmarks"]["shoulder_R"][0] = 0.21
        with self.assertRaisesRegex(ValueError, "bilateral symmetry failed|candidate landmark drift"):
            audit_shoulder_bridge(candidate)


if __name__ == "__main__":
    unittest.main()
