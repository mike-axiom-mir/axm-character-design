import copy, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from axm_character_design.organic_form import neutral_character_study, validate_study, build_mesh, mesh_checks, build_evidence

class OrganicCharacterTests(unittest.TestCase):
    def test_source_validates(self):
        m=validate_study(neutral_character_study())
        self.assertEqual(m["flex_zone_count"],13)
        self.assertGreater(m["a_pose_down_angle_deg"],20)
        self.assertLess(m["a_pose_down_angle_deg"],40)

    def test_mesh_is_finite_and_nondegenerate(self):
        c=mesh_checks(build_mesh())
        self.assertGreater(c["vertex_count"],100)
        self.assertGreater(c["triangle_count"],200)
        self.assertEqual(c["degenerate_triangles"],0)

    def test_bilateral_negative_control(self):
        s=neutral_character_study(); s["landmarks"]["wrist_R"][2]+=0.02
        with self.assertRaisesRegex(ValueError,"bilateral symmetry"): validate_study(s)

    def test_height_negative_control(self):
        s=neutral_character_study(); s["masses"][2]["radii"][2]=0.20
        with self.assertRaisesRegex(ValueError,"height"): validate_study(s)

    def test_flex_status_cannot_silently_promote(self):
        s=neutral_character_study(); s["flex_zones"][0]["status"]="DEFORMATION_TESTED"
        with self.assertRaisesRegex(ValueError,"flex truth-state"): validate_study(s)

    def test_deterministic_evidence(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ea=build_evidence(a); eb=build_evidence(b)
            self.assertEqual(ea["source_digest"],eb["source_digest"])
            self.assertEqual(ea["mesh_digest"],eb["mesh_digest"])
            for n in ("source.json","mesh.json","character.obj","front.svg","side.svg","top.svg","evidence.json"):
                with open(os.path.join(a,n),"rb") as fa, open(os.path.join(b,n),"rb") as fb:
                    self.assertEqual(fa.read(),fb.read())

if __name__ == "__main__": unittest.main()
