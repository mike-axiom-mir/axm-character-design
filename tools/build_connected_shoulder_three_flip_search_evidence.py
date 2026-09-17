#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from axm_character_design.connected_shoulder_three_flip_search import (
    build_disjoint_three_flip_search_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = build_disjoint_three_flip_search_evidence(args.out)
    selection = receipt["selection"]
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "legal_three_flip_count": receipt["search_scope"][
                    "legal_face_disjoint_three_flip_combination_count"
                ],
                "prior_current_pair_extension_count": receipt["search_scope"][
                    "prior_current_pair_plus_third_extension_count"
                ],
                "new_triples_not_containing_current_pair_count": receipt["search_scope"][
                    "new_triples_not_containing_current_pair_count"
                ],
                "anchor_no_worse_survivor_count": receipt["search_scope"][
                    "anchor_no_worse_survivor_count"
                ],
                "dense_no_worse_survivor_count": receipt["search_scope"][
                    "dense_no_worse_survivor_count"
                ],
                "strict_dense_total_improvement_count": receipt["search_scope"][
                    "strict_dense_total_improvement_count"
                ],
                "current_dense_pair_sum": receipt["current_control"]["dense_pair_sum"],
                "selected_dense_pair_sum": (
                    selection["candidate_pair_sum"] if selection is not None else None
                ),
                "selected_combo": selection["combo"] if selection is not None else None,
                "decision": receipt["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
