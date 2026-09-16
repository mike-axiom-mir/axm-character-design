import unittest

from axm_character_design.shoulder_mass_interface_context import (
    EXPECTED_CANDIDATE,
    EXPECTED_PARENT,
    STATUS,
    audit_shoulder_mass_interface_context,
)


class ShoulderMassInterfaceContextTests(unittest.TestCase):
    def test_exact_neutral_shoulder_context(self):
        receipt = audit_shoulder_mass_interface_context()
        self.assertEqual(receipt["status"], STATUS)
        self.assertEqual(receipt["parent_shoulder_context"], EXPECTED_PARENT)
        self.assertEqual(receipt["candidate_shoulder_context"], EXPECTED_CANDIDATE)
        self.assertEqual(receipt["root_ring_sample_count_per_shoulder"], 10)
        self.assertEqual(
            receipt["candidate_shoulder_context"][
                "root_ring_samples_inside_or_on_mass"
            ],
            2,
        )
        self.assertEqual(
            receipt["parent_shoulder_context"][
                "root_ring_samples_inside_or_on_mass"
            ],
            2,
        )

    def test_exterior_shift_is_recorded_not_promoted(self):
        receipt = audit_shoulder_mass_interface_context()
        self.assertEqual(
            receipt["candidate_minus_parent"],
            {
                "landmark_mass_implicit": 0.100218098958,
                "root_ring_min_mass_implicit": 0.130467772454,
                "root_ring_max_mass_implicit": 0.06377038812,
            },
        )
        self.assertEqual(
            receipt["gates"]["exterior_shift_interpretation"],
            "RECORDED_NOT_AUTOMATIC_DEFECT_OR_ACCEPTANCE",
        )
        self.assertEqual(receipt["gates"]["visual_acceptance"], "NOT_EVALUATED")
        self.assertEqual(
            receipt["gates"]["rigging_or_deformation_rebind"], "NOT_EVALUATED"
        )
        self.assertEqual(receipt["gates"]["source_adoption"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
