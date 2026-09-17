import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from axm_character_design.shoulder_bridge_candidate import build_shoulder_bridge_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--out", default="evidence/character-neutral-a-001")
args = parser.parse_args()
print(build_shoulder_bridge_evidence(args.out))
