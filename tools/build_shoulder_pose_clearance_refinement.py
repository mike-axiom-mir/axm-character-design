from __future__ import annotations

import argparse

from axm_character_design.shoulder_pose_clearance_refinement import (
    build_shoulder_pose_clearance_refinement_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_shoulder_pose_clearance_refinement_evidence(args.out)
    print(receipt["status"])
    print(receipt["candidate_source_digest"])
    print(receipt["candidate_mesh_digest"])


if __name__ == "__main__":
    main()
