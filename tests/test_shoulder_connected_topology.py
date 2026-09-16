import copy
import unittest

from axm_character_design.shoulder_connected_topology import (
    EXPECTED_ADOPTED_MESH_DIGEST,
    EXPECTED_ADOPTED_SOURCE_DIGEST,
    _inspect_indexed_surface,
    audit_connected_shoulders,
    build_connected_shoulder_specimen,
)
from axm_character_design.organic_form import canonical_digest
from axm_character_design.shoulder_source_lineage import (
    adopted_character_source,
    build_adopted_character_mesh,
)


class ConnectedShoulderTopologyTests(unittest.TestCase):
    def test_exact_adopted_source_identity_is_unchanged(self):
        source = adopted_character_source()
        mesh = build_adopted_character_mesh(source)
        self.assertEqual(canonical_digest(source), EXPECTED_ADOPTED_SOURCE_DIGEST)
        self.assertEqual(canonical_digest(mesh), EXPECTED_ADOPTED_MESH_DIGEST)

    def test_bilateral_connected_specimens_are_closed_single_components(self):
        left = build_connected_shoulder_specimen("L")
        right = build_connected_shoulder_specimen("R")
        for specimen in (left, right):
            self.assertEqual(len(specimen["positions"]), 93)
            self.assertEqual(len(specimen["faces"]), 182)
            local = specimen["local_preflight"]
            self.assertEqual(local["status"], "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT")
            self.assertEqual(local["boundary_edge_count"], 0)
            self.assertEqual(local["nonmanifold_edge_count"], 0)
            self.assertEqual(local["orientation_conflict_edge_count"], 0)
            self.assertEqual(local["collapsed_triangle_count"], 0)
            self.assertEqual(local["triangle_component_count"], 1)

    def test_eight_accepted_E_trajectories_and_two_inferior_closures_are_explicit(self):
        specimen = build_connected_shoulder_specimen("L")
        provenance = specimen["construction"]["seam_provenance"]
        accepted = [item for item in provenance if item["kind"].startswith("ACCEPTED_E")]
        inferior = [item for item in provenance if "INFERIOR" in item["kind"]]
        self.assertEqual({item["root_ring_index"] for item in accepted}, {0, 1, 4, 5, 6, 7, 8, 9})
        self.assertEqual([item["root_ring_index"] for item in inferior], [2, 3])
        self.assertTrue(all(abs(item["ribcage_implicit"] - 1.0) <= 1e-8 for item in provenance))

    def test_mirrored_phase_repair_beats_phase_zero_without_moving_the_mesh(self):
        left = build_connected_shoulder_specimen("L")
        right = build_connected_shoulder_specimen("R")
        left_control = build_connected_shoulder_specimen("L", hole_phase=0)
        right_control = build_connected_shoulder_specimen("R", hole_phase=0)

        def outer_turn(specimen):
            return specimen["local_shape_diagnostics"]["seam_normal_turns"][
                "ribcage_to_seam_max_normal_turn_deg"
            ]

        def outer_area(specimen):
            return specimen["local_shape_diagnostics"]["stitch_triangle_areas"][
                "ribcage_to_seam"
            ]["minimum_over_median"]

        self.assertEqual(left["positions"], left_control["positions"])
        self.assertEqual(right["positions"], right_control["positions"])
        self.assertLess(outer_turn(left), outer_turn(left_control))
        self.assertLess(outer_turn(right), outer_turn(right_control))
        self.assertGreater(outer_area(left), outer_area(left_control))
        self.assertGreater(outer_area(right), outer_area(right_control))
        self.assertAlmostEqual(outer_turn(left), outer_turn(right), places=9)
        self.assertAlmostEqual(outer_area(left), outer_area(right), places=9)

    def test_single_triangle_winding_corruption_fails_local_preflight(self):
        specimen = build_connected_shoulder_specimen("L")
        faces = copy.deepcopy(specimen["faces"])
        faces[0] = [faces[0][0], faces[0][2], faces[0][1]]
        result = _inspect_indexed_surface(specimen["positions"], faces)
        self.assertNotEqual(result["status"], "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT")
        self.assertGreater(result["orientation_conflict_edge_count"], 0)

    def test_audit_runs_without_promoting_unchecked_domains(self):
        receipt = audit_connected_shoulders()
        self.assertEqual(
            receipt["status"],
            "PASS_CHARACTER_E_CLIPPED_CONNECTED_SHOULDER_TOPOLOGY_WITH_PHASE_REPAIR",
        )
        self.assertEqual(receipt["gates"]["pinned_UC_edge_topology"], "NOT_RUN")
        for key in ("self_intersection", "deformation", "visual_tangent_or_pinch_acceptance", "rigging", "runtime", "gameplay"):
            self.assertEqual(receipt["gates"][key], "NOT_CLAIMED")

    def test_invalid_side_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "side must be L or R"):
            build_connected_shoulder_specimen("X")


if __name__ == "__main__":
    unittest.main()
