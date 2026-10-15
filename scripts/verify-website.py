#!/usr/bin/env python3
"""Check static website links, fragment targets, assets, and JavaScript syntax.

No server, simulator, browser download, or network access is required.
Use a browser separately for rendered layout and interaction changes.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

SITE = Path(__file__).resolve().parents[1] / "docs"


class Page(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        for name in ("href", "src"):
            if attributes.get(name):
                self.links.append(attributes[name])


def validate(site: Path) -> list[str]:
    site = site.resolve()
    pages = {path: Page(path.read_text()) for path in site.rglob("*.html")}
    errors = []
    references = [(path, link) for path, page in pages.items() for link in page.links]
    for path in site.rglob("*.css"):
        references.extend((path, link) for link in re.findall(
            r"url\(\s*['\"]?([^'\"\s)]+)['\"]?\s*\)", path.read_text()))
    for source, link in references:
        url = urlsplit(link)
        if url.scheme or url.netloc:
            continue
        local = unquote(url.path)
        target = ((site / local.lstrip("/")) if local.startswith("/") else source.parent / local).resolve()
        if not local:
            target = source
        if not target.is_relative_to(site):
            errors.append(f"{source.relative_to(site)}: link leaves website: {link}")
            continue
        if target.is_dir():
            target /= "index.html"
        if not target.is_file():
            errors.append(f"{source.relative_to(site)}: missing local target: {link}")
        elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
            errors.append(f"{source.relative_to(site)}: missing fragment: {link}")
    return errors


def main() -> None:
    errors = validate(SITE)
    if errors:
        raise SystemExit("\n".join(errors))
    print("Website links, fragments, and assets passed.", flush=True)
    node = shutil.which("node")
    if node:
        for path in sorted(SITE.rglob("*.js")):
            subprocess.run([node, "--check", str(path)], check=True)
        print("Website JavaScript syntax passed.")
    else:
        print("Node is unavailable; JavaScript syntax checks skipped.")


if __name__ == "__main__":
    main()
