import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from axm_character_design.flex_transition_audit import audit_flex_transitions

parser = argparse.ArgumentParser()
parser.add_argument("--out", default="evidence/character-neutral-a-001")
args = parser.parse_args()

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
report = audit_flex_transitions()
(out / "flex_transition_audit.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(report["summary"], sort_keys=True))
