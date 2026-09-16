import unittest

from axm_character_design.connected_shoulder_deformation import (
    STATUS as RIGGING_STATUS,
    audit_connected_shoulder_deformation,
)
from axm_character_design.self_intersection import inspect_triangle_self_intersections
from axm_character_design.shoulder_connected_topology import build_connected_shoulder_specimen


class ConnectedShoulderSelfIntersectionTests(unittest.TestCase):
    def test_exact_rigging_candidate_has_no_sampled_nonadjacent_self_intersections(self):
        rigging = audit_connected_shoulder_deformation()
        self.assertEqual(rigging["status"], RIGGING_STATUS)
        observed = 0
        for side in ("L", "R"):
            specimen = build_connected_shoulder_specimen(side)
            for pose in rigging["results"][side]["candidate"]:
                report = inspect_triangle_self_intersections(pose["positions"], specimen["indices"])
                self.assertEqual(report["status"], "PASS_NO_NONADJACENT_SELF_INTERSECTIONS")
                self.assertEqual(report["self_intersection_pair_count"], 0)
                observed += 1
        self.assertEqual(observed, 6)

    def test_crossing_triangle_negative_control_is_detected(self):
        positions = [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.5, 0.5, -1.0],
            [0.5, 0.5, 1.0],
            [1.5, 0.5, 0.0],
        ]
        report = inspect_triangle_self_intersections(positions, [0, 1, 2, 3, 4, 5])
        self.assertEqual(report["status"], "SELF_INTERSECTIONS_DETECTED")
        self.assertEqual(report["self_intersection_pair_count"], 1)

    def test_coplanar_overlap_negative_control_is_detected(self):
        positions = [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.25, 0.25, 0.0],
            [1.25, 0.25, 0.0],
            [0.25, 1.25, 0.0],
        ]
        report = inspect_triangle_self_intersections(positions, [0, 1, 2, 3, 4, 5])
        self.assertEqual(report["status"], "SELF_INTERSECTIONS_DETECTED")
        self.assertEqual(report["self_intersection_pair_count"], 1)


if __name__ == "__main__":
    unittest.main()
