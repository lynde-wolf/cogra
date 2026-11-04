"""Check that every local link and image in the built site points at a file.

python docs/check_links.py        # after docs/build.py
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))

SITE = Path(__file__).resolve().parent / "_site"
BLOB = "https://github.com/lynde-wolf/cogra/blob/main/"


def broken_links(site: Path = SITE) -> list[str]:
    bad = []
    for page in site.rglob("*.html"):
        text = page.read_text(errors="replace")
        ids = set(re.findall(r'\bid="([^"]+)"', text))
        for url in re.findall(r'(?:href|src)="([^"]+)"', text):
            if url.startswith(BLOB):  # must be a file the repository will have
                from build import ROOT, _in_repo

                rel = url[len(BLOB) :].partition("#")[0]
                if not _in_repo(ROOT / rel):
                    bad.append(f"{page.relative_to(site)}: {url} (not in the repository)")
                continue
            if re.match(r"^(https?:|mailto:|data:|javascript:)", url) or "{" in url:
                continue
            path, _, frag = url.partition("#")
            if not path:
                if frag and frag not in ids:
                    bad.append(f"{page.relative_to(site)}: #{frag}")
                continue
            target = (page.parent / unquote(path)).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                bad.append(f"{page.relative_to(site)}: {url}")
            elif frag and target.suffix == ".html":
                if f'id="{frag}"' not in target.read_text(errors="replace"):
                    bad.append(f"{page.relative_to(site)}: {url} (no such anchor)")
    return bad


if __name__ == "__main__":
    bad = broken_links()
    print("\n".join(bad) or "no broken links")
    sys.exit(1 if bad else 0)
