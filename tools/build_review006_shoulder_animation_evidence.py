#!/usr/bin/env python3
"""Build retained evidence for the review-006 Animation diagnostic loop."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from axm_character_design.review006_shoulder_animation_diagnostic import (
    STATUS,
    animation_contract,
    audit_review006_shoulder_animation,
    authored_clip_payload,
)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    audit = audit_review006_shoulder_animation()
    if audit["status"] != STATUS:
        raise SystemExit(f"Animation diagnostic did not pass: {audit['status']}")

    (out_dir / "animation-contract.json").write_text(
        json.dumps(animation_contract(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "authored-clip.json").write_text(
        json.dumps(authored_clip_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "animation-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with (out_dir / "dense-motion-trace.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "dense_sample_index",
            "time_s",
            "shoulder_angle_deg",
            "left_release_weight",
            "right_release_weight",
            "left_structural_pass",
            "right_structural_pass",
            "left_nonadjacent_pairs",
            "right_nonadjacent_pairs",
            "bilateral_mirrored_position_set",
        ])
        for row in audit["motion"]["rows"]:
            writer.writerow([
                row["dense_sample_index"],
                f"{row['time_s']:.9f}",
                f"{row['shoulder_angle_deg']:.15g}",
                f"{row['sides']['L']['release_weight']:.15g}",
                f"{row['sides']['R']['release_weight']:.15g}",
                row["sides"]["L"]["structural_pass"],
                row["sides"]["R"]["structural_pass"],
                row["sides"]["L"]["nonadjacent_intersection_pair_count"],
                row["sides"]["R"]["nonadjacent_intersection_pair_count"],
                row["bilateral_mirrored_position_set"],
            ])

    summary = {
        "schema": audit["schema"],
        "status": audit["status"],
        "exact_identity": audit["exact_identity"],
        "rigging_boundary_prerequisite": audit["rigging_boundary_prerequisite"],
        "motion": {
            key: value
            for key, value in audit["motion"].items()
            if key != "rows"
        },
        "negative_control": audit["negative_control"],
        "gates": audit["gates"],
        "handoffs": audit["handoffs"],
        "truth_boundary": audit["truth_boundary"],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/review006-animation-diagnostic")
    build(out)


if __name__ == "__main__":
    main()
