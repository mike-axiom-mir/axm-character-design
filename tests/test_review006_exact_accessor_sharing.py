import unittest

from axm_character_design.review006_exact_accessor_sharing import (
    EXPECTED_DUPLICATE_PAYLOAD_BYTES,
    LEFT_RELEASE_NODE,
    RIGHT_RELEASE_NODE,
    _channel_output,
    mutate_duplicate_output_byte,
    pack_character_glb_with_shared_release_scale,
    parse_glb,
    share_exact_animation_output_accessor,
)
from axm_character_design.review006_uc_skin_transport import pack_character_glb


class Review006ExactAccessorSharingTests(unittest.TestCase):
    def test_exact_bilateral_release_scale_is_shared(self):
        control = pack_character_glb()
        candidate, receipt = pack_character_glb_with_shared_release_scale()
        self.assertEqual(len(control.bytes), 44032)
        self.assertEqual(len(candidate.bytes), 40064)
        self.assertEqual(receipt["bytes_saved"], 3968)
        self.assertEqual(receipt["sharing"]["removed_binary_bytes"], EXPECTED_DUPLICATE_PAYLOAD_BYTES)
        document, _ = parse_glb(candidate.bytes)
        _, left = _channel_output(document, LEFT_RELEASE_NODE, "scale")
        _, right = _channel_output(document, RIGHT_RELEASE_NODE, "scale")
        self.assertEqual(left, right)
        self.assertEqual(len(document["accessors"]), 12)
        self.assertEqual(len(document["bufferViews"]), 12)

    def test_non_identical_payload_rejects_fail_closed(self):
        control = pack_character_glb().bytes
        mutated = mutate_duplicate_output_byte(
            control, duplicate_node_name=RIGHT_RELEASE_NODE, path="scale"
        )
        with self.assertRaisesRegex(ValueError, "not byte-identical"):
            share_exact_animation_output_accessor(
                mutated,
                keeper_node_name=LEFT_RELEASE_NODE,
                duplicate_node_name=RIGHT_RELEASE_NODE,
                path="scale",
            )

    def test_already_shared_candidate_is_not_silently_rewritten(self):
        candidate, _ = pack_character_glb_with_shared_release_scale()
        with self.assertRaisesRegex(ValueError, "already shares"):
            share_exact_animation_output_accessor(
                candidate.bytes,
                keeper_node_name=LEFT_RELEASE_NODE,
                duplicate_node_name=RIGHT_RELEASE_NODE,
                path="scale",
            )


if __name__ == "__main__":
    unittest.main()
