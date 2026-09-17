from __future__ import annotations

import json
import math
import struct
import unittest

from axm_character_design.review006_uc_skin_transport import (
    ANIMATION_HEAD,
    DENSE_SAMPLE_COUNT,
    DIRECTION_STATUS,
    JOINTS,
    POSITION_STATUS,
    STATIC_CORRECTION_WEIGHT,
    STATIC_ROOT_WEIGHT,
    UC_HEAD,
    correction_transform,
    direct_decomposition_audit,
    direction_frame_reference,
    pack_character_glb,
    source_to_gltf,
    transport_contract,
)


class Review006UcSkinTransportTests(unittest.TestCase):
    def test_contract_keeps_authority_and_receiver_holds_explicit(self):
        contract = transport_contract()
        self.assertEqual(contract["status"], POSITION_STATUS)
        self.assertEqual(contract["animation"]["head"], ANIMATION_HEAD)
        self.assertEqual(contract["uc_receiver"]["head"], UC_HEAD)
        self.assertEqual(
            contract["truth_boundary"]["deformed_normals_or_tangents"],
            DIRECTION_STATUS,
        )
        self.assertFalse(contract["materials_reference"]["semantics_copied_into_uc"])
        self.assertEqual(contract["coordinate_adapter"]["determinant"], 1)
        self.assertFalse(contract["coordinate_adapter"]["winding_reversed"])

    def test_coordinate_adapter_is_proper_z_up_to_y_up_rotation(self):
        self.assertEqual(source_to_gltf([1, 2, 3]), [1.0, 3.0, -2.0])
        x = source_to_gltf([1, 0, 0])
        y = source_to_gltf([0, 1, 0])
        z = source_to_gltf([0, 0, 1])
        cross = [
            x[1] * y[2] - x[2] * y[1],
            x[2] * y[0] - x[0] * y[2],
            x[0] * y[1] - x[1] * y[0],
        ]
        self.assertEqual(cross, z)

    def test_static_transport_weights_are_exact_binary_fractions(self):
        self.assertEqual(STATIC_CORRECTION_WEIGHT, 0.125)
        self.assertEqual(STATIC_ROOT_WEIGHT, 0.875)
        self.assertEqual(STATIC_CORRECTION_WEIGHT + STATIC_ROOT_WEIGHT, 1.0)
        self.assertEqual(JOINTS, {"root": 0, "L_distal": 1, "L_release": 2, "R_distal": 3, "R_release": 4})

    def test_dynamic_release_factorization_matches_owner_dense_samples(self):
        audit = direct_decomposition_audit()
        self.assertEqual(audit["status"], POSITION_STATUS)
        self.assertEqual(audit["sample_count"], DENSE_SAMPLE_COUNT)
        self.assertLessEqual(audit["maximum_real_arithmetic_position_residual_m"], 1e-10)
        self.assertTrue(audit["disabled_helper_rejected"])
        self.assertGreater(audit["disabled_helper_maximum_residual_m"], 1e-6)

    def test_correction_transform_stays_bounded(self):
        for angle in (-30.0, -10.0, 0.0, 10.0, 30.0):
            row = correction_transform(angle)
            self.assertGreaterEqual(row["k"], 0.0)
            self.assertLessEqual(row["k"], 1.0)
            self.assertGreater(row["planar_scale"], 0.0)
        neutral = correction_transform(0.0)
        self.assertEqual(neutral["release_weight"], 0.0)
        self.assertEqual(neutral["helper_angle_deg"], 0.0)
        self.assertEqual(neutral["planar_scale"], 1.0)

    def test_glb_is_bounded_static_weight_skin_with_dense_trs_channels(self):
        packed = pack_character_glb()
        self.assertEqual(packed.bytes[:4], b"glTF")
        _, version, total = struct.unpack("<4sII", packed.bytes[:12])
        self.assertEqual(version, 2)
        self.assertEqual(total, len(packed.bytes))
        self.assertEqual(packed.source_vertex_counts, {"L": 92, "R": 92})
        self.assertEqual(packed.source_triangle_counts, {"L": 180, "R": 180})
        doc = packed.document
        self.assertEqual(len(doc["skins"][0]["joints"]), 5)
        self.assertEqual(len(doc["animations"]), 1)
        self.assertEqual(doc["animations"][0]["name"], transport_contract()["animation"]["clip_id"])
        self.assertEqual(len(doc["animations"][0]["channels"]), 6)
        self.assertEqual(len(packed.times), DENSE_SAMPLE_COUNT)
        self.assertEqual(packed.times[0], 0.0)
        self.assertEqual(packed.times[-1], 2.0)
        primitive = doc["meshes"][0]["primitives"][0]
        joint_accessor = doc["accessors"][primitive["attributes"]["JOINTS_0"]]
        self.assertEqual(joint_accessor["componentType"], 5121)
        self.assertEqual(joint_accessor["count"], 184)

    def test_direction_frame_reference_is_retained_but_not_promoted(self):
        reference = direction_frame_reference()
        self.assertEqual(reference["status"], DIRECTION_STATUS)
        neutral = reference["samples"]["000"]
        self.assertEqual(neutral["angle_deg"], 0.0)
        for side in ("L", "R"):
            self.assertEqual(neutral["sides"][side]["changed_vertex_count_gt_1e_12_component"], 0)
        for sample in ("080", "240"):
            for side in ("L", "R"):
                self.assertGreater(reference["samples"][sample]["sides"][side]["changed_vertex_count_gt_1e_12_component"], 0)
                self.assertGreater(reference["samples"][sample]["sides"][side]["maximum_angle_from_neutral_deg"], 0.0)


if __name__ == "__main__":
    unittest.main()
