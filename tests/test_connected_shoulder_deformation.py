from copy import deepcopy
import unittest

from axm_character_design.connected_shoulder_deformation import (
    CANDIDATE_PROXIMAL_WEIGHT,
    CANDIDATE_DIGESTS,
    GEOMETRY_HEAD,
    POSE_ANGLES_DEG,
    SOURCE_DIGEST,
    STATUS,
    audit_connected_shoulder_deformation,
    rig_plan,
)


class ConnectedShoulderDeformationTests(unittest.TestCase):
    def test_exact_connected_shoulders_pass_bounded_socket_deformation(self):
        result = audit_connected_shoulder_deformation()
        self.assertEqual(result["status"], STATUS)
        self.assertEqual(result["geometry_head"], GEOMETRY_HEAD)
        self.assertEqual(result["source_digest"], SOURCE_DIGEST)
        self.assertEqual(result["rig_plan"]["weights"]["proximal_arm_ring_child_weight"], CANDIDATE_PROXIMAL_WEIGHT)
        self.assertEqual(result["pose_scope"]["angles_deg"], list(POSE_ANGLES_DEG))

        for side in ("L", "R"):
            self.assertEqual(result["results"][side]["geometry_digest"], CANDIDATE_DIGESTS[side])
            self.assertEqual(
                result["results"][side]["weight_counts"],
                {"fixed": 72, "blended": 10, "rigid": 11},
            )
            rows = result["results"][side]["candidate"]
            self.assertEqual([row["angle_deg"] for row in rows], list(POSE_ANGLES_DEG))
            for row in rows:
                self.assertEqual(row["status"], "PASS")
                self.assertEqual(row["collapsed_triangles"], 0)
                self.assertLessEqual(row["fixed_socket_max_drift_m"], 1e-9)
                self.assertLessEqual(row["rigid_arm_radius_max_drift_m"], 1e-9)
                self.assertTrue(row["bilateral_mirrored_position_set"])
                self.assertTrue(row["improves_anchored_proximal_control"])
            self.assertEqual(rows[1]["neutral_max_vertex_drift_m"], 0.0)

    def test_nonzero_boundary_release_improves_all_four_distortion_extrema(self):
        result = audit_connected_shoulder_deformation()
        for side in ("L", "R"):
            candidates = result["results"][side]["candidate"]
            controls = result["results"][side]["anchored_proximal_control"]
            for candidate, control in zip(candidates, controls):
                if candidate["angle_deg"] == 0.0:
                    continue
                self.assertGreater(candidate["minimum_triangle_area_ratio"], control["minimum_triangle_area_ratio"])
                self.assertLess(candidate["maximum_triangle_area_ratio"], control["maximum_triangle_area_ratio"])
                self.assertGreater(candidate["minimum_edge_length_ratio"], control["minimum_edge_length_ratio"])
                self.assertLess(candidate["maximum_edge_length_ratio"], control["maximum_edge_length_ratio"])

    def test_rig_plan_identity_drift_fails_closed(self):
        mutated = deepcopy(rig_plan())
        mutated["weights"]["proximal_arm_ring_child_weight"] = 0.11
        with self.assertRaisesRegex(ValueError, "rig plan identity drift"):
            audit_connected_shoulder_deformation(mutated)


if __name__ == "__main__":
    unittest.main()
