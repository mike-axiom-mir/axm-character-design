import unittest

from axm_character_design.connected_shoulder_diagonal_repair import (
    SELECTED_MASK,
    build_diagonal_mask_specimen,
)
from axm_character_design.connected_shoulder_stitch_edge_repair import TARGET_FACE_PAIRS
from axm_character_design.connected_shoulder_three_flip_search import (
    EXPECTED_CURRENT_DENSE_PAIR_SUM,
    EXPECTED_TRIANGLE_COUNT,
    EXPECTED_VERTEX_COUNT,
    HOLD_STATUS,
    PASS_STATUS,
    _canonical_combo,
    audit_disjoint_three_flip_search,
    build_three_flip_specimen,
    legal_disjoint_three_flip_combinations,
)
from axm_character_design.connected_shoulder_third_flip_search import (
    legal_third_flip_face_pairs,
)


class ConnectedShoulderThreeFlipSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_disjoint_three_flip_search()
        cls.left = legal_disjoint_three_flip_combinations("L")
        cls.right = legal_disjoint_three_flip_combinations("R")

    def test_scoped_result_is_truthful_pass_or_hold(self):
        self.assertIn(self.audit["status"], {PASS_STATUS, HOLD_STATUS})
        self.assertEqual(
            self.audit["current_control"]["dense_pair_sum"],
            EXPECTED_CURRENT_DENSE_PAIR_SUM,
        )
        self.assertTrue(self.audit["current_control"]["all_sampled_poses_nonzero"])
        self.assertTrue(
            self.audit["search_scope"]["face_disjoint_three_flip_family_exhausted"]
        )
        self.assertFalse(
            self.audit["search_scope"]["arbitrary_three_edge_remeshing_exhausted"]
        )
        self.assertFalse(
            self.audit["search_scope"]["four_plus_edge_remeshing_exhausted"]
        )
        self.assertFalse(self.audit["search_scope"]["vertex_movement_exhausted"])

    def test_family_is_bilateral_pairwise_face_disjoint_and_broader_than_pr14(self):
        self.assertEqual(self.left, self.right)
        self.assertGreater(len(self.left), 16)
        for combo in self.left:
            self.assertEqual(len(combo), 3)
            flattened = [value for pair in combo for value in pair]
            self.assertEqual(len(set(flattened)), 6)

        previous = {
            _canonical_combo(tuple(TARGET_FACE_PAIRS) + (third_pair,))
            for third_pair in legal_third_flip_face_pairs("L")
        }
        current_family = set(self.left)
        self.assertTrue(previous.issubset(current_family))
        self.assertEqual(
            len(previous),
            self.audit["search_scope"]["prior_current_pair_plus_third_extension_count"],
        )
        self.assertEqual(
            len(current_family) - len(previous),
            self.audit["search_scope"]["new_triples_not_containing_current_pair_count"],
        )

    def test_representative_three_flip_specimens_preserve_positions_groups_and_budget(self):
        indexes = sorted({0, len(self.left) // 2, len(self.left) - 1})
        for side in ("L", "R"):
            base = build_diagonal_mask_specimen(side, SELECTED_MASK)
            for index in indexes:
                combo = self.left[index]
                specimen = build_three_flip_specimen(side, combo)
                self.assertEqual(specimen["positions"], [list(p) for p in base["positions"]])
                self.assertEqual(specimen["groups"], list(base["groups"]))
                self.assertEqual(len(specimen["positions"]), EXPECTED_VERTEX_COUNT)
                self.assertEqual(len(specimen["faces"]), EXPECTED_TRIANGLE_COUNT)
                self.assertEqual(len(specimen["changed_face_indexes"]), 6)
                self.assertEqual(
                    specimen["local_preflight"]["status"],
                    "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT",
                )

    def test_status_matches_strict_dense_improvement_only(self):
        strict_count = self.audit["search_scope"]["strict_dense_total_improvement_count"]
        if self.audit["status"] == PASS_STATUS:
            self.assertGreater(strict_count, 0)
            self.assertIsNotNone(self.audit["selection"])
            self.assertTrue(self.audit["selection"]["strict_improvement"])
            self.assertLess(
                self.audit["selection"]["candidate_pair_sum"],
                EXPECTED_CURRENT_DENSE_PAIR_SUM,
            )
            self.assertEqual(self.audit["selection"]["worse_samples"], 0)
        else:
            self.assertEqual(strict_count, 0)
            self.assertIsNone(self.audit["selection"])
            self.assertEqual(
                self.audit["decision"],
                "HOLD_NO_NEW_TOPOLOGY_IDENTITY__CURRENT_TWO_FLIP_CONTROL_REMAINS",
            )

    def test_overlap_duplicate_and_illegal_pairs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "face-disjoint"):
            _canonical_combo(((111, 112), (112, 113), (114, 115)))
        with self.assertRaisesRegex(ValueError, "repeat"):
            _canonical_combo(((111, 112), (111, 112), (114, 115)))
        with self.assertRaisesRegex(ValueError, "outside the exact legal stitch family"):
            build_three_flip_specimen(
                "L", ((111, 112), (114, 115), (998, 999))
            )


if __name__ == "__main__":
    unittest.main()
