from copy import deepcopy
import unittest

from axm_character_design.organic_form import canonical_digest
from axm_character_design.shoulder_source_lineage import (
    EXPECTED_REVIEW_MESH_DIGEST,
    EXPECTED_REVIEW_SOURCE_DIGEST,
    SOURCE_ID,
    STATUS,
    adopted_character_source,
    audit_source_lineage_adoption,
    build_adopted_character_mesh,
)


class ShoulderSourceLineageTests(unittest.TestCase):
    def test_exact_e_form_is_migrated_without_geometry_drift(self):
        source = adopted_character_source()
        receipt = audit_source_lineage_adoption(source)
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(source["study_id"], SOURCE_ID)
        self.assertNotEqual(canonical_digest(source), EXPECTED_REVIEW_SOURCE_DIGEST)
        self.assertEqual(receipt["accepted_review_source_digest"], EXPECTED_REVIEW_SOURCE_DIGEST)
        self.assertEqual(receipt["accepted_review_mesh_digest"], EXPECTED_REVIEW_MESH_DIGEST)
        self.assertEqual(receipt["adopted_mesh_digest"], EXPECTED_REVIEW_MESH_DIGEST)
        self.assertEqual(receipt["form_metrics"]["vertex_count"], 504)
        self.assertEqual(receipt["form_metrics"]["triangle_count"], 908)
        self.assertEqual(receipt["form_metrics"]["degenerate_triangles"], 0)

    def test_source_lineage_preserves_exact_transition_contract(self):
        source = adopted_character_source()
        transition = source["shoulder_transition_repair"]
        self.assertEqual(transition["anchor_radius_reference_m"], 0.085)
        self.assertEqual(transition["upper_arm_root_radius_reference_m"], 0.075)
        self.assertEqual(transition["root_ring_indices"], [4, 5, 6, 7, 8, 9, 0, 1])
        self.assertEqual(
            transition["blend_weights"],
            [0.40, 0.65, 0.90, 1.0, 1.0, 0.90, 0.65, 0.40],
        )
        self.assertEqual(transition["target_axis_scale"], [0.55, 0.55, 0.85])
        self.assertTrue(transition["open_inferior_sector"])
        self.assertEqual(
            transition["status"],
            "SOURCE_LINEAGE_ADOPTED_FORM_DIRECTION_NOT_CONNECTED_TOPOLOGY",
        )

    def test_adopted_mesh_is_deterministic(self):
        first = build_adopted_character_mesh(adopted_character_source())
        second = build_adopted_character_mesh(adopted_character_source())
        self.assertEqual(canonical_digest(first), canonical_digest(second))
        self.assertEqual(canonical_digest(first), EXPECTED_REVIEW_MESH_DIGEST)

    def test_review_provenance_drift_fails_closed(self):
        source = adopted_character_source()
        source["source_lineage_adoption"]["accepted_review_mesh_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "review mesh provenance drift"):
            audit_source_lineage_adoption(source)

    def test_form_semantic_drift_fails_closed(self):
        source = adopted_character_source()
        source["shoulder_transition_repair"]["blend_weights"][0] = 0.41
        with self.assertRaisesRegex(ValueError, "changed accepted E form semantics"):
            audit_source_lineage_adoption(source)

    def test_geometry_drift_fails_closed(self):
        source = adopted_character_source()
        source["shoulder_transition_regions"][0]["anchor"][2] += 0.001
        with self.assertRaises(ValueError):
            audit_source_lineage_adoption(source)


if __name__ == "__main__":
    unittest.main()
