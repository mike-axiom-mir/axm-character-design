from __future__ import annotations

import argparse
import json

from axm_character_design.shoulder_connected_topology import build_connected_shoulder_evidence
from axm_uc.mesh_topology import inspect_mesh_topology


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_connected_shoulder_evidence(
        args.out,
        topology_inspector=inspect_mesh_topology,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
