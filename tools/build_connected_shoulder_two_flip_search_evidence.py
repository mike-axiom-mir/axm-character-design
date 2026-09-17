#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from axm_character_design.connected_shoulder_two_flip_search import (
    build_disjoint_two_flip_search_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_disjoint_two_flip_search_evidence(args.out)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "legal_face_disjoint_two_flip_combination_count": receipt["search_scope"][
                    "legal_face_disjoint_two_flip_combination_count"
                ],
                "anchor_no_worse_survivor_count": receipt["search_scope"][
                    "anchor_no_worse_survivor_count"
                ],
                "dense_no_worse_survivor_count": receipt["search_scope"][
                    "dense_no_worse_survivor_count"
                ],
                "current_dense_pair_sum": receipt["current_control"]["dense_pair_sum"],
                "selected_dense_pair_sum": receipt["selection"]["dense_pair_sum"],
                "selected_combo": receipt["selection"]["combo"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
