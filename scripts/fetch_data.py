"""Download the EBA Transparency Exercise source files into data/raw/.

The EBA host rejects requests without a browser user-agent, which is the usual
reason a naive fetch of these URLs returns an error page instead of a CSV.
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def fetch(name: str, url: str, force: bool = False) -> Path:
    dest = C.RAW / name
    if dest.exists() and not force:
        print(f"  skip  {name} ({dest.stat().st_size / 1e6:.1f} MB already present)")
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers=HEADERS, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for block in r.iter_content(chunk_size=1 << 20):
                fh.write(block)
    print(f"  ok    {name} ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


def main(force: bool = False):
    print(f"Downloading EBA Transparency Exercise -> {C.RAW}")
    for name, url in C.EBA_FILES.items():
        fetch(name, url, force=force)
    print("done")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
