import tempfile
import unittest
from pathlib import Path

from axm_character_design.shoulder_bridge_refinement import REFINED_ANCHOR_RADIUS_M
from axm_character_design.shoulder_transition_feathered import (
    BLEND_WEIGHTS,
    ROOT_RING_INDICES,
    STATUS,
    TARGET_AXIS_SCALE,
    audit_feathered_shoulder,
    build_feathered_shoulder_evidence,
    feathered_shoulder_candidate,
)


class ShoulderTransitionFeatheredTests(unittest.TestCase):
    def test_bounded_profile_preserves_radius_references(self):
        candidate = feathered_shoulder_candidate()
        repair = candidate["shoulder_transition_repair"]
        self.assertEqual(repair["anchor_radius_reference_m"], REFINED_ANCHOR_RADIUS_M)
        self.assertEqual(repair["upper_arm_root_radius_reference_m"], 0.075)
        self.assertEqual(tuple(repair["root_ring_indices"]), ROOT_RING_INDICES)
        self.assertEqual(tuple(repair["blend_weights"]), BLEND_WEIGHTS)
        self.assertEqual(tuple(repair["target_axis_scale"]), TARGET_AXIS_SCALE)

    def test_structural_feathered_open_saddle_gates(self):
        receipt = audit_feathered_shoulder()
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(receipt["bounded_delta"]["profile_surface"], "FEATHERED_OPEN_SADDLE_NOT_ANNULAR_TUBE")
        for side in receipt["side_results"]:
            self.assertEqual(side["proximal_samples_inside_or_on_ribcage"], 8)
            self.assertEqual(side["proximal_sample_count"], 8)
            self.assertEqual(side["distal_samples_exactly_on_upper_arm_root_ring"], 8)
            self.assertEqual(side["root_ring_sample_count"], 8)
            self.assertEqual(side["root_ring_total_samples"], 10)
            self.assertEqual(side["open_inferior_samples_not_covered"], 2)
            self.assertEqual(side["patch_vertices"], 16)
            self.assertEqual(side["patch_triangles"], 14)
        metrics = receipt["form_metrics"]
        self.assertEqual(metrics["baseline_vertices"], 472)
        self.assertEqual(metrics["baseline_triangles"], 880)
        self.assertEqual(metrics["refined_vertices"], 516)
        self.assertEqual(metrics["refined_triangles"], 960)
        self.assertEqual(metrics["candidate_vertices"], 504)
        self.assertEqual(metrics["candidate_triangles"], 908)
        self.assertEqual(metrics["added_vertices"], 32)
        self.assertEqual(metrics["added_triangles"], 28)

    def test_evidence_builder_retains_neutral_and_diagnostic_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = build_feathered_shoulder_evidence(tmp)
            self.assertEqual(receipt["status"], STATUS)
            for view in ("front", "top", "three-quarter"):
                self.assertTrue((Path(tmp) / f"shoulder-transition-feathered-{view}.svg").is_file())
                self.assertTrue((Path(tmp) / f"shoulder-transition-feathered-{view}-diagnostic.svg").is_file())

    def test_source_drift_fails_closed(self):
        candidate = feathered_shoulder_candidate()
        candidate["landmarks"]["shoulder_L"][0] -= 0.001
        with self.assertRaises(ValueError):
            audit_feathered_shoulder(candidate)

    def test_acceptance_boundaries_remain_held(self):
        gates = audit_feathered_shoulder()["gates"]
        self.assertEqual(gates["art-direction-acceptance"], "NOT_CLAIMED")
        self.assertEqual(gates["visual-qa-acceptance"], "NOT_CLAIMED")
        self.assertEqual(gates["connected-topology-acceptance"], "NOT_CLAIMED")
        self.assertEqual(gates["rigging-or-deformation-acceptance"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
