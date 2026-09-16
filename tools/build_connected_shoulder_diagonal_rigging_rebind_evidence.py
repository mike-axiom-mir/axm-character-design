from __future__ import annotations

import argparse

from axm_character_design.connected_shoulder_diagonal_rigging_rebind import (
    build_diagonal_repair_rigging_rebind_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    build_diagonal_repair_rigging_rebind_evidence(args.out)


if __name__ == "__main__":
    main()
