from __future__ import annotations

import argparse
import json

from axm_character_design.shoulder_transition_feathered import build_feathered_shoulder_evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(build_feathered_shoulder_evidence(args.out), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
