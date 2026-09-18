from __future__ import annotations

import math
import unittest

from axm_character_design.review006_runtime_normal_cache import (
    assert_static_vertices_unchanged,
    build_posed_normal_cache_plan,
    evaluate_cached_smooth_normals,
    operation_budget,
)


def reference_normals(vertices, faces):
    accum = [[0.0, 0.0, 0.0] for _ in vertices]
    for a, b, c in faces:
        e1 = [vertices[b][i] - vertices[a][i] for i in range(3)]
        e2 = [vertices[c][i] - vertices[a][i] for i in range(3)]
        n = [
            e1[1] * e2[2] - e1[2] * e2[1],
            e1[2] * e2[0] - e1[0] * e2[2],
            e1[0] * e2[1] - e1[1] * e2[0],
        ]
        if math.sqrt(sum(v * v for v in n)) <= 1e-15:
            raise ValueError("degenerate")
        for index in (a, b, c):
            for axis in range(3):
                accum[index][axis] += n[axis]
    output = []
    for value in accum:
        magnitude = math.sqrt(sum(v * v for v in value))
        output.append(tuple(v / magnitude for v in value))
    return tuple(output)


class Review006RuntimeNormalCacheTests(unittest.TestCase):
    def setUp(self):
        self.neutral = (
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (2.0, 0.0, 0.0),
            (3.0, 0.0, 0.0),
            (2.0, 1.0, 0.0),
        )
        self.faces = ((0, 1, 2), (3, 4, 5))
        self.plan = build_posed_normal_cache_plan(
            self.neutral,
            self.faces,
            static_vertex_indices=(0, 1, 2),
        )

    def test_mixed_static_dynamic_candidate_matches_reference(self):
        posed = list(self.neutral)
        posed[5] = (2.0, 1.0, 0.5)
        assert_static_vertices_unchanged(self.plan, self.neutral, posed)
        self.assertEqual(
            evaluate_cached_smooth_normals(posed, self.plan),
            reference_normals(posed, self.faces),
        )
        self.assertEqual(self.plan.static_face_count, 1)
        self.assertEqual(self.plan.dynamic_face_count, 1)
        self.assertEqual(self.plan.static_output_vertex_count, 3)
        self.assertEqual(self.plan.dynamic_output_vertex_count, 3)

    def test_static_vertex_motion_fails_closed(self):
        posed = list(self.neutral)
        posed[0] = (0.001, 0.0, 0.0)
        with self.assertRaisesRegex(ValueError, "static vertex moved"):
            assert_static_vertices_unchanged(self.plan, self.neutral, posed)

    def test_operation_budget_reports_real_reduction(self):
        budget = operation_budget(self.plan, 10)
        self.assertEqual(budget["control_face_crosses"], 20)
        self.assertEqual(budget["candidate_face_crosses"], 10)
        self.assertEqual(budget["saved_face_crosses"], 10)
        self.assertEqual(budget["control_vertex_normalizations"], 60)
        self.assertEqual(budget["candidate_vertex_normalizations"], 30)
        self.assertEqual(budget["saved_vertex_normalizations"], 30)


if __name__ == "__main__":
    unittest.main()
