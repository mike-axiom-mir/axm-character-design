import unittest

from axm_character_design.connected_shoulder_stitch_edge_repair import (
    TARGET_FACE_PAIRS,
    build_stitch_edge_repair_specimen,
)
from axm_character_design.connected_shoulder_third_flip_search import (
    EXPECTED_CURRENT_DENSE_PAIR_SUM,
    EXPECTED_TRIANGLE_COUNT,
    EXPECTED_VERTEX_COUNT,
    HOLD_STATUS,
    PASS_STATUS,
    _current_face_indexes,
    audit_current_pair_third_flip_search,
    build_third_flip_specimen,
    legal_third_flip_face_pairs,
)


class ConnectedShoulderThirdFlipSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_current_pair_third_flip_search()

    def test_scoped_result_is_truthful_pass_or_hold(self):
        self.assertIn(self.audit["status"], {PASS_STATUS, HOLD_STATUS})
        self.assertEqual(
            self.audit["current_control"]["dense_pair_sum"],
            EXPECTED_CURRENT_DENSE_PAIR_SUM,
        )
        self.assertTrue(self.audit["current_control"]["all_sampled_poses_nonzero"])
        self.assertFalse(
            self.audit["search_scope"]["arbitrary_three_flip_combinations_exhausted"]
        )

    def test_family_is_real_and_disjoint_from_current_pair(self):
        left = legal_third_flip_face_pairs("L")
        right = legal_third_flip_face_pairs("R")
        self.assertEqual(left, right)
        self.assertGreater(len(left), 0)
        self.assertEqual(
            len(left),
            self.audit["search_scope"][
                "legal_face_disjoint_third_flip_extension_count"
            ],
        )
        occupied = _current_face_indexes()
        for pair in left:
            self.assertTrue(set(pair).isdisjoint(occupied))

    def test_every_third_flip_preserves_positions_groups_and_budget(self):
        for side in ("L", "R"):
            current = build_stitch_edge_repair_specimen(side)
            for pair in legal_third_flip_face_pairs(side):
                specimen = build_third_flip_specimen(side, pair)
                self.assertEqual(specimen["positions"], current["positions"])
                self.assertEqual(specimen["groups"], current["groups"])
                self.assertEqual(len(specimen["positions"]), EXPECTED_VERTEX_COUNT)
                self.assertEqual(len(specimen["faces"]), EXPECTED_TRIANGLE_COUNT)
                self.assertEqual(
                    specimen["changed_face_indexes_from_current"], list(pair)
                )
                self.assertEqual(
                    specimen["local_preflight"]["status"],
                    "PASS_CHARACTER_LOCAL_CLOSED_ORIENTED_SINGLE_COMPONENT",
                )

    def test_status_matches_strict_dense_improvement_only(self):
        strict_count = self.audit["search_scope"][
            "strict_dense_total_improvement_count"
        ]
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

    def test_current_flip_or_overlap_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "face-disjoint"):
            build_third_flip_specimen("L", TARGET_FACE_PAIRS[0])
        with self.assertRaisesRegex(ValueError, "face-disjoint"):
            build_third_flip_specimen("R", (TARGET_FACE_PAIRS[0][1], 999))


if __name__ == "__main__":
    unittest.main()
