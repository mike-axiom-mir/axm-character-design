from __future__ import annotations

import argparse
import json

from axm_character_design.shoulder_pose_clearance_spatial_context import (
    build_shoulder_pose_clearance_spatial_context_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_shoulder_pose_clearance_spatial_context_evidence(args.out)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
