import unittest

from axm_character_design.organic_form import canonical_digest
from axm_character_design.shoulder_bridge_refinement import (
    EXPECTED_REFINED_SOURCE_DIGEST,
    REFINED_ANCHOR_RADIUS_M,
)
from axm_character_design.shoulder_transition_profile import (
    DISTAL_ROOT_RING_INDICES,
    PROXIMAL_AXIS_SCALE,
    STATUS,
    audit_directional_shoulder_profile,
    directional_shoulder_profile_candidate,
)


class ShoulderTransitionProfileTests(unittest.TestCase):
    def test_profile_candidate_preserves_refined_identity_and_radius_references(self):
        candidate = directional_shoulder_profile_candidate()
        repair = candidate["shoulder_profile_repair"]
        self.assertEqual(repair["prior_refined_source_digest"], EXPECTED_REFINED_SOURCE_DIGEST)
        self.assertEqual(repair["anchor_radius_reference_m"], REFINED_ANCHOR_RADIUS_M)
        self.assertEqual(repair["upper_arm_root_radius_reference_m"], 0.075)
        self.assertEqual(tuple(repair["distal_root_ring_indices"]), DISTAL_ROOT_RING_INDICES)
        self.assertEqual(tuple(repair["proximal_world_axis_scale"]), PROXIMAL_AXIS_SCALE)
        for bridge in candidate["shoulder_transition_regions"]:
            self.assertEqual(bridge["radius_anchor_m"], REFINED_ANCHOR_RADIUS_M)
            self.assertEqual(bridge["radius_shoulder_m"], 0.075)
            self.assertTrue(bridge["open_underarm_sector"])
            self.assertEqual(
                bridge["profile_kind"],
                "OPEN_SUPERIOR_SADDLE_NOT_ANNULAR_TUBE",
            )

    def test_structural_open_saddle_gates(self):
        receipt = audit_directional_shoulder_profile()
        self.assertEqual(receipt["status"], STATUS)
        self.assertTrue(receipt["bounded_delta"]["prior_refined_candidate_preserved"])
        self.assertTrue(receipt["bounded_delta"]["whole_body_bounds_unchanged"])
        self.assertEqual(
            receipt["bounded_delta"]["profile_surface"],
            "OPEN_SUPERIOR_SADDLE_NOT_ANNULAR_TUBE",
        )
        for side in receipt["side_results"]:
            self.assertEqual(side["proximal_samples_inside_or_on_ribcage"], 6)
            self.assertEqual(side["proximal_sample_count"], 6)
            self.assertEqual(side["distal_samples_exactly_on_upper_arm_root_ring"], 6)
            self.assertEqual(side["distal_root_ring_sample_count"], 6)
            self.assertEqual(side["upper_arm_root_ring_total_samples"], 10)
            self.assertEqual(side["open_root_sector_samples_not_covered"], 4)
            self.assertEqual(side["patch_vertices"], 12)
            self.assertEqual(side["patch_triangles"], 10)

        metrics = receipt["form_metrics"]
        self.assertEqual(metrics["baseline_vertices"], 472)
        self.assertEqual(metrics["baseline_triangles"], 880)
        self.assertEqual(metrics["refined_vertices"], 516)
        self.assertEqual(metrics["refined_triangles"], 960)
        self.assertEqual(metrics["profile_candidate_vertices"], 496)
        self.assertEqual(metrics["profile_candidate_triangles"], 900)
        self.assertEqual(metrics["profile_added_vertices"], 24)
        self.assertEqual(metrics["profile_added_triangles"], 20)

    def test_candidate_is_deterministic(self):
        first = directional_shoulder_profile_candidate()
        second = directional_shoulder_profile_candidate()
        self.assertEqual(canonical_digest(first), canonical_digest(second))
        self.assertEqual(
            audit_directional_shoulder_profile(),
            audit_directional_shoulder_profile(),
        )

    def test_baseline_drift_fails_closed(self):
        candidate = directional_shoulder_profile_candidate()
        candidate["masses"][1]["radii"][0] += 0.001
        with self.assertRaises(ValueError):
            audit_directional_shoulder_profile(candidate)

    def test_acceptance_boundaries_remain_held(self):
        gates = audit_directional_shoulder_profile()["gates"]
        self.assertEqual(gates["art-direction-acceptance"], "NOT_CLAIMED")
        self.assertEqual(gates["visual-qa-acceptance"], "NOT_CLAIMED")
        self.assertEqual(gates["connected-topology-acceptance"], "NOT_CLAIMED")
        self.assertEqual(gates["rigging-or-deformation-acceptance"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
