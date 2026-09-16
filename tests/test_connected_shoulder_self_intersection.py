import unittest

from axm_character_design.connected_shoulder_self_intersection import (
    STATUS,
    audit_connected_shoulder_self_intersection,
)
from axm_character_design.self_intersection import inspect_triangle_self_intersections


class ConnectedShoulderSelfIntersectionTests(unittest.TestCase):
    def test_exact_rigging_candidate_is_fully_classified_without_preclaim(self):
        receipt = audit_connected_shoulder_self_intersection()
        self.assertEqual(receipt["sample_scope"]["sample_count"], 6)
        self.assertIn(
            receipt["status"],
            (STATUS, "FAIL_CHARACTER_CONNECTED_SHOULDER_SAMPLED_NONADJACENT_SELF_INTERSECTION_GATE"),
        )
        self.assertEqual(
            receipt["negative_controls"]["status"],
            "PASS_DETECTS_BOTH_CONTROL_INTERSECTIONS",
        )
        for sample in receipt["samples"]:
            count = sample["inspection"]["self_intersection_pair_count"]
            expected = "PASS" if count == 0 else "FAIL"
            self.assertEqual(sample["status"], expected)
            self.assertEqual(
                sample["inspection"]["status"],
                "PASS_NO_NONADJACENT_SELF_INTERSECTIONS" if count == 0 else "SELF_INTERSECTIONS_DETECTED",
            )

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
