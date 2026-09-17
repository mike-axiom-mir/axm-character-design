from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_character_design.review006_connected_geometry import (
    build_review006_geometry_rebind_evidence,
)


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "review006-geometry-rebind"
    audit = build_review006_geometry_rebind_evidence(target)
    print(audit["verdict"])
    for row in audit["stage_summaries"]:
        print(
            row["stage"],
            f'{row["vertex_count_per_side"]}v/{row["triangle_count_per_side"]}t',
            f'neutral={row["neutral_pairs_total"]}',
        )
    print("selected", audit["selection"]["selected_stage"])


if __name__ == "__main__":
    main()
