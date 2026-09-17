import unittest

from axm_character_design.target_host_surface_bridge import (
    EXACT_OWNER_ORDER,
    EXACT_REVERSED_WINDING,
    OTHER_INDEX_RELATION,
    classify_index_relation,
    flatten_faces,
    reverse_triangle_winding,
)


class TargetHostSurfaceBridgeTests(unittest.TestCase):
    def test_reverses_only_winding(self):
        faces = [[0, 1, 2], [2, 3, 4]]
        self.assertEqual(reverse_triangle_winding(faces), [[0, 2, 1], [2, 4, 3]])
        self.assertEqual(flatten_faces(faces), [0, 1, 2, 2, 3, 4])

    def test_classifies_exact_owner_order(self):
        faces = [[0, 1, 2], [2, 3, 4]]
        row = classify_index_relation(faces, [0, 1, 2, 2, 3, 4])
        self.assertEqual(row["relation"], EXACT_OWNER_ORDER)
        self.assertEqual(row["owner_order_mismatch_count"], 0)

    def test_classifies_exact_reversed_winding(self):
        faces = [[0, 1, 2], [2, 3, 4]]
        row = classify_index_relation(faces, [0, 2, 1, 2, 4, 3])
        self.assertEqual(row["relation"], EXACT_REVERSED_WINDING)
        self.assertEqual(row["owner_order_mismatch_count"], 4)
        self.assertEqual(row["reversed_winding_mismatch_count"], 0)
        self.assertEqual(row["exact_reversed_triangles"], 2)

    def test_other_relation_does_not_promote(self):
        faces = [[0, 1, 2], [2, 3, 4]]
        row = classify_index_relation(faces, [0, 2, 1, 2, 3, 4])
        self.assertEqual(row["relation"], OTHER_INDEX_RELATION)
        self.assertNotEqual(row["reversed_winding_mismatch_count"], 0)

    def test_rejects_invalid_payloads(self):
        with self.assertRaises(ValueError):
            reverse_triangle_winding([])
        with self.assertRaises(ValueError):
            reverse_triangle_winding([[0, 1]])
        with self.assertRaises(ValueError):
            reverse_triangle_winding([[0, 0, 1]])
        with self.assertRaises(ValueError):
            classify_index_relation([[0, 1, 2]], [0, 1])


if __name__ == "__main__":
    unittest.main()
