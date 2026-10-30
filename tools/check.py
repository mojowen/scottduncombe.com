#!/usr/bin/env python3
"""Static-site checks for scottduncombe.com.

Crawls every page, verifies internal links/assets resolve, feeds parse,
and the style rules hold (no .html links, no draft/specimen language,
og:image targets exist). Run against a checkout:

    python3 tools/check.py --root .

Exit 0 = clean; exit 1 prints the failure list.
"""

import argparse
import html.parser
import os
import re
import sys
import xml.dom.minidom

FORBIDDEN_HTML = [
    # draft-copy marks and specimen language were retired 2026-10-30
    ('class="todo"', "draft .todo mark"),
    ("Specimen", "specimen language"),
    # the field-guide/specimen conceit (habitat, Nº, plates…) was retired 2026-10-30
    ("habitat", "habitat language"),
    ("nº", "field-guide numbering"),
    ("first observed", "specimen language"),
    ("field guide", "field-guide language"),
    ("field notes", "field-guide language"),
    (">plates", "field-guide language"),
    ("measurements", "specimen language"),
    ("diet", "specimen language"),
]
ORIGIN = "https://scottduncombe.com"


class PageParser(html.parser.HTMLParser):
    def __init__(self, page_dir):
        super().__init__()
        self.page_dir = page_dir
        self.urls = []  # (kind, url)
        self.og_images = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for attr in ("href", "src"):
            url = d.get(attr)
            if url:
                self.urls.append((attr, url))
        if d.get("property") == "og:image" or d.get("name") == "twitter:image":
            self.og_images.append(d.get("content", ""))


def discover_pages(root):
    pages = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath:
            continue
        rel = os.path.relpath(dirpath, root)
        for fn in filenames:
            if fn.endswith(".html"):
                pages.append(os.path.join(rel, fn))
    return sorted(pages)


def resolve(root, page, url):
    """Resolve an internal URL against the page; return filesystem path or None."""
    base = os.path.dirname(os.path.join(root, page))
    path = os.path.normpath(os.path.join(base, url))
    if not path.startswith(os.path.abspath(root)):
        return None
    if os.path.isdir(path):
        path = os.path.join(path, "index.html")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    failures = []

    pages = discover_pages(root)
    if not pages:
        print("no pages found under --root; wrong tree?")
        return 1

    for page in pages:
        src = open(os.path.join(root, page), encoding="utf-8").read()
        body = src.split("<body", 1)[-1]
        for needle, why in FORBIDDEN_HTML:
            if needle.lower() in body.lower():
                failures.append(f"{page}: {why} ({needle!r})")

        parser = PageParser(os.path.dirname(page))
        parser.feed(src)

        for attr, url in parser.urls:
            if url.startswith(("http:", "https:", "mailto:", "tel:", "#", "data:", "//")):
                continue
            if ".html" in url and not url.startswith("404.html"):
                failures.append(f"{page}: extensionless-URL rule broken, {attr}={url!r}")
                continue
            path = resolve(root, page, url)
            if not path or not os.path.isfile(path):
                failures.append(f"{page}: broken {attr} {url!r}")

        for og in parser.og_images:
            if og.startswith("http") and not og.startswith("http"):
                continue
            if og.startswith("//"):
                og = "https:" + og
            if og.startswith(ORIGIN):
                og = og[len(ORIGIN):].lstrip("/")
            elif og.startswith("http"):
                continue
            path = os.path.normpath(os.path.join(root, og))
            if not os.path.isfile(path):
                failures.append(f"{page}: og:image missing {og!r}")

    for feed in ("press.xml", "writing.xml"):
        feed_path = os.path.join(root, feed)
        if os.path.isfile(feed_path):
            try:
                xml.dom.minidom.parse(feed_path)
            except Exception as e:
                failures.append(f"{feed}: invalid XML ({e})")
        else:
            failures.append(f"{feed}: missing")

    if failures:
        print(f"FAIL ({len(failures)}):")
        for f in failures:
            print(" -", f)
        return 1
    print(f"OK: {len(pages)} pages crawled, feeds valid, links resolve, style rules hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())