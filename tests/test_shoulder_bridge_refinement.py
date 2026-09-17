import unittest

from axm_character_design.organic_form import canonical_digest
from axm_character_design.shoulder_bridge_candidate import build_shoulder_bridge_mesh
from axm_character_design.shoulder_bridge_refinement import (
    EXPECTED_REFINED_MESH_DIGEST,
    EXPECTED_REFINED_SOURCE_DIGEST,
    PREVIOUS_ANCHOR_RADIUS_M,
    REFINED_ANCHOR_RADIUS_M,
    STATUS,
    audit_shoulder_bridge_refinement,
    refined_shoulder_bridge_candidate,
)


class ShoulderBridgeRefinementTests(unittest.TestCase):
    def test_exact_refined_identity_and_bounded_radius_delta(self):
        candidate = refined_shoulder_bridge_candidate()
        self.assertEqual(canonical_digest(candidate), EXPECTED_REFINED_SOURCE_DIGEST)
        self.assertEqual(
            canonical_digest(build_shoulder_bridge_mesh(candidate)),
            EXPECTED_REFINED_MESH_DIGEST,
        )
        self.assertEqual(
            candidate["shoulder_bridge_refinement"]["previous_value_m"],
            PREVIOUS_ANCHOR_RADIUS_M,
        )
        self.assertEqual(
            candidate["shoulder_bridge_refinement"]["refined_value_m"],
            REFINED_ANCHOR_RADIUS_M,
        )
        for bridge in candidate["shoulder_transition_regions"]:
            self.assertEqual(bridge["radius_anchor_m"], REFINED_ANCHOR_RADIUS_M)
            self.assertEqual(bridge["radius_shoulder_m"], 0.075)

    def test_audit_reduces_local_bulk_and_improves_overlap_proxy(self):
        receipt = audit_shoulder_bridge_refinement()
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(receipt["bounded_delta"]["previous_anchor_radius_m"], 0.10)
        self.assertEqual(receipt["bounded_delta"]["refined_anchor_radius_m"], 0.085)
        self.assertEqual(receipt["bounded_delta"]["absolute_reduction_m"], 0.015)
        self.assertEqual(receipt["bounded_delta"]["relative_reduction"], 0.15)
        self.assertTrue(receipt["bounded_delta"]["other_candidate_fields_preserved"])

        for item in receipt["side_comparison"]:
            self.assertEqual(item["previous_proximal_ring_inside_or_on_ribcage"], 6)
            self.assertEqual(item["refined_proximal_ring_inside_or_on_ribcage"], 8)
            self.assertEqual(item["distal_radius_m"], 0.075)
            self.assertEqual(item["upper_arm_root_radius_m"], 0.075)

        metrics = receipt["global_form_metrics"]
        self.assertEqual(metrics["baseline_vertices"], 472)
        self.assertEqual(metrics["candidate_vertices"], 516)
        self.assertEqual(metrics["baseline_triangles"], 880)
        self.assertEqual(metrics["candidate_triangles"], 960)
        self.assertTrue(metrics["whole_body_bounds_unchanged"])

        for side in ("L", "R"):
            region_id = f"shoulder_bridge_{side}"
            before = receipt["previous_bridge_bounds_m"][region_id]
            after = receipt["refined_bridge_bounds_m"][region_id]
            before_depth = before["max"][1] - before["min"][1]
            after_depth = after["max"][1] - after["min"][1]
            self.assertLess(after_depth, before_depth)

    def test_acceptance_boundaries_remain_held(self):
        receipt = audit_shoulder_bridge_refinement()
        self.assertEqual(receipt["gates"]["art-direction-acceptance"], "NOT_CLAIMED")
        self.assertEqual(receipt["gates"]["visual-qa-acceptance"], "NOT_CLAIMED")
        self.assertEqual(receipt["gates"]["connected-topology-acceptance"], "NOT_CLAIMED")
        self.assertEqual(receipt["gates"]["rigging-or-deformation-acceptance"], "NOT_CLAIMED")

    def test_deterministic_receipt(self):
        self.assertEqual(
            audit_shoulder_bridge_refinement(),
            audit_shoulder_bridge_refinement(),
        )


if __name__ == "__main__":
    unittest.main()
