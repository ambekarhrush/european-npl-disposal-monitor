"""Verify harvested candidates against their source PDFs and promote them.

A candidate only enters the corpus if its text can be located in the document
it claims to come from. Anything that fails is reported and discarded, and the
placeholder entry for that bank is left alone rather than quietly upgraded.

Run after scripts/harvest_disclosures.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402
from src import harvest as H  # noqa: E402
from src import intent as I  # noqa: E402


def main(apply: bool = False):
    with open(H.CANDIDATES_PATH) as fh:
        candidates = json.load(fh)["candidates"]

    print(f"Verifying {len(candidates)} candidates against source documents\n")

    passed, failed = [], []
    for cand in candidates:
        ok, note = H.verify_candidate(cand)
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {cand['bank'][:38]:<38} p.{cand['page_no']:<5} {note}")
        (passed if ok else failed).append(cand)

    print(f"\n{len(passed)} verified, {len(failed)} rejected")

    if not apply:
        print("\nDry run. Re-run with --apply to write them into the corpus.")
        return

    with open(I.CORPUS_PATH) as fh:
        corpus = json.load(fh)

    promoted_leis = {c["lei"] for c in passed}
    # Drop synthetic placeholders only for banks we now have real text for.
    kept = [
        e for e in corpus["entries"]
        if not (e["lei"] in promoted_leis and e["provenance"] == "SYNTHETIC_ILLUSTRATIVE")
    ]

    seen = {(e["lei"], e.get("quote", "")[:120]) for e in kept}
    for cand in passed:
        key = (cand["lei"], cand["quote"][:120])
        if key in seen:   # already promoted on an earlier run
            continue
        seen.add(key)
        kept.append({
            "lei": cand["lei"],
            "bank": cand["bank"],
            "country": cand.get("country", ""),
            "source_document": cand["source_document"],
            "source_url": cand["source_url"],
            "period": "2025",
            "quote": cand["quote"],
            "provenance": "VERIFIED_VERBATIM",
            "verification": "Located in source PDF by scripts/promote_candidates.py",
            "page_no": cand["page_no"],
        })

    corpus["entries"] = kept
    with open(I.CORPUS_PATH, "w") as fh:
        json.dump(corpus, fh, indent=2, ensure_ascii=False)

    verified = sum(1 for e in kept if e["provenance"] == "VERIFIED_VERBATIM")
    print(f"\nCorpus now holds {len(kept)} entries, {verified} verified.")
    print(f"Written to {I.CORPUS_PATH.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
