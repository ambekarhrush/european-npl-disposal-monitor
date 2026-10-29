"""Pull candidate disclosure passages from bank IR sites.

Output is a review queue, not a corpus. Nothing here is trusted until a human
has opened the source document and confirmed the passage reads as extracted.
Banks the crawler cannot reach are printed as a targeted manual worklist.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import harvest as H  # noqa: E402
from src import config as C  # noqa: E402


def main():
    print("Harvesting candidate disclosure passages\n")
    candidates, statuses = H.harvest_all()

    served = [s for s in statuses if s["outcome"] == "harvested"]
    pending = H.worklist(statuses)

    print(f"\n{len(candidates)} candidates from {len(served)}/{len(statuses)} banks")
    print(f"Written to {H.CANDIDATES_PATH.relative_to(C.ROOT)}")

    if pending:
        print("\nManual worklist -- open these and pull the NPE/disposal passage by hand:")
        for s in pending:
            print(f"  [{s['outcome']:<12}] {s['bank'][:44]:<44} {s['manual_url']}")

    print(
        "\nNext: review data/processed/harvest_candidates.json, move the passages that\n"
        "genuinely discuss disposal intent into data/raw/disclosure_corpus.json, and set\n"
        "provenance to VERIFIED_VERBATIM once checked against the source."
    )


if __name__ == "__main__":
    main()
