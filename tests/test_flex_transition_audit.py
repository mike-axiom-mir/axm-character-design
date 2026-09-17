import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from axm_character_design.flex_transition_audit import audit_flex_transitions
from axm_character_design.organic_form import canonical_digest, neutral_character_study


class FlexTransitionAuditTests(unittest.TestCase):
    def test_all_declared_flex_zones_have_neutral_context(self):
        study = neutral_character_study()
        report = audit_flex_transitions(study)
        self.assertEqual(report["source_digest"], canonical_digest(study))
        self.assertFalse(report["source_geometry_modified_by_audit"])
        self.assertEqual(report["coverage"]["declared_flex_zone_count"], 13)
        self.assertEqual(report["coverage"]["audited_flex_zone_count"], 13)
        self.assertEqual(report["coverage"]["internal_segment_transition_count"], 8)
        self.assertEqual(report["coverage"]["mass_interface_count"], 5)
        self.assertEqual(report["gates"]["declared-flex-zone-coverage"], "PASS")
        self.assertEqual(report["gates"]["rigging-or-deformation-acceptance"], "NOT_CLAIMED")

    def test_source_radius_steps_are_exposed_not_silently_repaired(self):
        report = audit_flex_transitions()
        by_id = {item["flex_zone"]: item for item in report["internal_segment_transitions"]}
        self.assertEqual(report["summary"]["exact_radius_match_count"], 2)
        self.assertEqual(report["summary"]["source_radius_step_count"], 6)
        self.assertAlmostEqual(report["summary"]["max_abs_radius_delta_m"], 0.01)
        self.assertAlmostEqual(by_id["elbow_L"]["signed_radius_delta_m"], 0.0)
        self.assertAlmostEqual(by_id["wrist_L"]["signed_radius_delta_m"], 0.005)
        self.assertAlmostEqual(by_id["knee_L"]["signed_radius_delta_m"], -0.003)
        self.assertAlmostEqual(by_id["ankle_L"]["signed_radius_delta_m"], 0.01)
        self.assertEqual(
            by_id["ankle_L"]["observation"],
            "SOURCE_RADIUS_STEP_RECORDED_NOT_REPAIRED",
        )

    def test_mass_interface_overlap_is_observation_not_acceptance(self):
        report = audit_flex_transitions()
        by_id = {item["flex_zone"]: item for item in report["mass_interfaces"]}
        self.assertEqual(by_id["neck"]["root_ring_samples_inside_or_on_mass"], 10)
        self.assertEqual(by_id["shoulder_L"]["root_ring_samples_inside_or_on_mass"], 2)
        self.assertEqual(by_id["shoulder_R"]["root_ring_samples_inside_or_on_mass"], 2)
        self.assertEqual(by_id["hip_L"]["root_ring_samples_inside_or_on_mass"], 5)
        self.assertEqual(by_id["hip_R"]["root_ring_samples_inside_or_on_mass"], 5)
        self.assertEqual(
            report["summary"]["least_embedded_mass_interfaces_by_root_ring_samples"],
            ["shoulder_L", "shoulder_R"],
        )
        self.assertEqual(
            report["gates"]["mass-interface-neutral-context"],
            "RECORDED_NOT_DEFORMATION_GATE",
        )

    def test_bilateral_transition_delta_negative_control(self):
        study = copy.deepcopy(neutral_character_study())
        hand_r = next(segment for segment in study["segments"] if segment["id"] == "hand_R")
        hand_r["radius_a"] += 0.004
        with self.assertRaisesRegex(ValueError, "bilateral transition delta mismatch: wrist"):
            audit_flex_transitions(study)

    def test_declared_flex_coverage_negative_control(self):
        study = copy.deepcopy(neutral_character_study())
        study["flex_zones"] = [zone for zone in study["flex_zones"] if zone["id"] != "ankle_R"]
        with self.assertRaisesRegex(ValueError, "flex audit coverage drift"):
            audit_flex_transitions(study)

    def test_report_is_deterministic(self):
        a = audit_flex_transitions()
        b = audit_flex_transitions()
        self.assertEqual(
            json.dumps(a, sort_keys=True, separators=(",", ":")),
            json.dumps(b, sort_keys=True, separators=(",", ":")),
        )


if __name__ == "__main__":
    unittest.main()
