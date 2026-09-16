import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from axm_character_design.organic_form import build_evidence
p=argparse.ArgumentParser(); p.add_argument("--out",default="evidence/character-neutral-a-001")
args=p.parse_args(); print(build_evidence(args.out))
