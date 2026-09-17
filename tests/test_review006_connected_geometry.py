import unittest

from axm_character_design.review006_connected_geometry import (
    EXPECTED_REVIEW006_MESH_DIGEST,
    EXPECTED_REVIEW006_SOURCE_DIGEST,
    STAGES,
    _inspect_indexed_surface,
    audit_review006_geometry_rebind,
    build_stage,
)
from axm_character_design.review006_self_intersection import (
    inspect_triangle_self_intersections,
)


class Review006ConnectedGeometryTests(unittest.TestCase):
    def test_exact_review006_identity_and_four_stage_rebind(self):
        audit = audit_review006_geometry_rebind()
        identity = audit["exact_identity"]
        self.assertEqual(identity["review006_source_digest"], EXPECTED_REVIEW006_SOURCE_DIGEST)
        self.assertEqual(identity["review006_proof_mesh_digest"], EXPECTED_REVIEW006_MESH_DIGEST)
        self.assertEqual(identity["review006_proof_vertex_count"], 504)
        self.assertEqual(identity["review006_proof_triangle_count"], 908)
        self.assertEqual([row["stage"] for row in audit["stage_summaries"]], list(STAGES))
        self.assertEqual(audit["gates"]["old_geometry_result_transfer"], "FORBIDDEN_AND_NOT_PERFORMED")

    def test_every_stage_structurally_passes_and_is_bilateral(self):
        audit = audit_review006_geometry_rebind()
        for row in audit["stage_rows"]:
            preflight = row["local_preflight"]
            self.assertTrue(preflight["status"].startswith("PASS_"))
            self.assertEqual(preflight["boundary_edge_count"], 0)
            self.assertEqual(preflight["nonmanifold_edge_count"], 0)
            self.assertEqual(preflight["orientation_conflict_edge_count"], 0)
            self.assertEqual(preflight["collapsed_triangle_count"], 0)
            self.assertEqual(preflight["triangle_component_count"], 1)
            self.assertEqual(preflight["disconnected_vertex_fan_count"], 0)
            self.assertEqual(preflight["isolated_vertex_count"], 0)

        for summary in audit["stage_summaries"]:
            self.assertEqual(summary["neutral_pairs_L"], summary["neutral_pairs_R"])

    def test_selection_is_current_source_evidence_driven(self):
        audit = audit_review006_geometry_rebind()
        summaries = audit["stage_summaries"]
        selected = audit["selection"]["selected_summary"]
        best_key = min(
            (row["neutral_pairs_total"], row["triangle_count_per_side"], list(STAGES).index(row["stage"]))
            for row in summaries
        )
        selected_key = (
            selected["neutral_pairs_total"],
            selected["triangle_count_per_side"],
            list(STAGES).index(selected["stage"]),
        )
        self.assertEqual(selected_key, best_key)

    def test_stage_budgets_are_bounded(self):
        baseline = build_stage("L", "connected_baseline")
        self.assertEqual((len(baseline["positions"]), len(baseline["faces"])), (93, 182))
        for stage in ("opening_repair", "diagonal_repair", "stitch_repair"):
            specimen = build_stage("L", stage)
            self.assertEqual((len(specimen["positions"]), len(specimen["faces"])), (92, 180))

    def test_surface_preflight_fails_closed_on_winding_flip(self):
        specimen = build_stage("L", "stitch_repair")
        faces = [list(face) for face in specimen["faces"]]
        faces[0] = [faces[0][0], faces[0][2], faces[0][1]]
        report = _inspect_indexed_surface(specimen["positions"], faces)
        self.assertEqual(report["status"], "FAIL_CHARACTER_REVIEW006_SURFACE_PREFLIGHT")
        self.assertGreater(report["orientation_conflict_edge_count"], 0)

    def test_nonadjacent_intersection_observer_detects_crossing_triangles(self):
        positions = [
            [-1.0, -1.0, 0.0],
            [1.0, -1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, -0.5, -1.0],
            [0.0, -0.5, 1.0],
            [0.0, 0.75, 0.0],
        ]
        report = inspect_triangle_self_intersections(positions, [0, 1, 2, 3, 4, 5])
        self.assertEqual(report["status"], "SELF_INTERSECTIONS_DETECTED")
        self.assertEqual(report["self_intersection_pair_count"], 1)


if __name__ == "__main__":
    unittest.main()
