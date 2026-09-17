import unittest

from axm_character_design.connected_shoulder_diagonal_repair import (
    SELECTED_MASK,
    build_diagonal_mask_specimen,
)
from axm_character_design.connected_shoulder_stitch_edge_repair import TARGET_FACE_PAIRS
from axm_character_design.connected_shoulder_two_flip_search import (
    EXPECTED_CURRENT_DENSE_PAIR_SUM,
    EXPECTED_TRIANGLE_COUNT,
    EXPECTED_VERTEX_COUNT,
    HOLD_STATUS,
    PASS_STATUS,
    _current_combo,
    audit_disjoint_two_flip_search,
    build_two_flip_specimen,
    legal_disjoint_two_flip_combinations,
)


class ConnectedShoulderTwoFlipSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_disjoint_two_flip_search()

    def test_scoped_result_is_truthful_dynamic_pass_or_hold(self):
        self.assertIn(self.audit["status"], {PASS_STATUS, HOLD_STATUS})
        self.assertEqual(
            self.audit["current_control"]["dense_pair_sum"],
            EXPECTED_CURRENT_DENSE_PAIR_SUM,
        )
        self.assertTrue(self.audit["current_control"]["all_sampled_poses_nonzero"])
        self.assertEqual(self.audit["selection"]["worse_samples"], 0)
        self.assertLessEqual(
            self.audit["selection"]["dense_pair_sum"],
            EXPECTED_CURRENT_DENSE_PAIR_SUM,
        )

    def test_search_family_is_real_and_contains_current_control(self):
        combos = legal_disjoint_two_flip_combinations("L")
        self.assertGreater(len(combos), 0)
        self.assertEqual(
            len(combos),
            self.audit["search_scope"]["legal_face_disjoint_two_flip_combination_count"],
        )
        self.assertIn(_current_combo(), combos)
        self.assertEqual(
            _current_combo(),
            tuple(tuple(pair) for pair in sorted(TARGET_FACE_PAIRS)),
        )

    def test_selected_specimen_preserves_positions_groups_and_budget(self):
        combo = self.audit["selection"]["combo"]
        for side in ("L", "R"):
            base = build_diagonal_mask_specimen(side, SELECTED_MASK)
            selected = build_two_flip_specimen(side, combo)
            self.assertEqual(selected["positions"], [list(point) for point in base["positions"]])
            self.assertEqual(selected["groups"], list(base["groups"]))
            self.assertEqual(len(selected["positions"]), EXPECTED_VERTEX_COUNT)
            self.assertEqual(len(selected["faces"]), EXPECTED_TRIANGLE_COUNT)
            self.assertEqual(
                selected["local_preflight"]["status"],
                "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT",
            )

    def test_status_matches_measured_strict_improvement(self):
        selected_total = self.audit["selection"]["dense_pair_sum"]
        if self.audit["status"] == PASS_STATUS:
            self.assertTrue(self.audit["selection"]["strict_improvement"])
            self.assertLess(selected_total, EXPECTED_CURRENT_DENSE_PAIR_SUM)
            self.assertFalse(self.audit["selection"]["selected_is_current_control"])
            self.assertGreater(
                self.audit["search_scope"]["strict_dense_total_improvement_count"], 0
            )
        else:
            self.assertFalse(self.audit["selection"]["strict_improvement"])
            self.assertEqual(selected_total, EXPECTED_CURRENT_DENSE_PAIR_SUM)
            self.assertEqual(
                self.audit["search_scope"]["strict_dense_total_improvement_count"], 0
            )

    def test_overlapping_face_pairs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "face-disjoint"):
            build_two_flip_specimen("L", ((111, 112), (112, 113)))


if __name__ == "__main__":
    unittest.main()
