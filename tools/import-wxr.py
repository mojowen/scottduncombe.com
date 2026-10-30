#!/usr/bin/env python3
"""Import the WordPress WXR export into the static field-guide site.

Reads scott039swebsite.WordPress.2026-10-30.xml and:
  1. generates project/<slug>.html detail pages for every published WP
     project that doesn't already have a hand-authored page
     (pizza-to-the-polls, power-the-polls, moodmonitor are skipped),
  2. copies the referenced gallery/thumbnail images into
     assets/img/uploads/<year>/<file> (pre-resized by the importer's
     --img-mirror step; images are downloaded from the live WP site),
  3. links the matching spec-cards in work.html to the new pages,
  4. repairs rails whose rail-content was left as \\1 / \\2 placeholders.

Usage:
  python3 tools/import-wxr.py --wxr <export.xml> --img-mirror <dir> [--repo <dir>]
"""

import argparse
import html as htmlmod
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}
UPLOADS_PREFIX = "https://scottduncombe.com/wp-content/uploads/"

SKIP_SLUGS = {"pizza-to-the-polls", "power-the-polls"}  # hand-authored pages exist


def parse_wxr(path):
    ch = ET.parse(path).getroot().find("channel")
    attachments, projects, pages = {}, [], {}
    for it in ch.findall("item"):
        ptype = it.findtext("wp:post_type", namespaces=NS)
        if ptype == "attachment":
            attachments[it.findtext("wp:post_id", namespaces=NS)] = (
                it.findtext("wp:attachment_url", namespaces=NS) or ""
            )
        elif ptype == "project":
            if it.findtext("wp:status", namespaces=NS) != "publish":
                continue
            thumb = None
            for m in it.findall("wp:postmeta", namespaces=NS):
                if m.findtext("wp:meta_key", namespaces=NS) == "_thumbnail_id":
                    thumb = m.findtext("wp:meta_value", namespaces=NS)
            content = it.findtext("content:encoded", namespaces=NS) or ""
            projects.append(
                {
                    "title": (it.findtext("title") or "").strip(),
                    "slug": it.findtext("wp:post_name", namespaces=NS) or "",
                    "date": it.findtext("wp:post_date", namespaces=NS) or "",
                    "link": it.findtext("link") or "",
                    "content": content,
                    "thumb": thumb,
                    "gallery_ids": [
                        i.strip()
                        for g in re.findall(r"\[gallery[^\]]*ids=\"([\d,]+)\"", content)
                        for i in g.split(",")
                    ],
                }
            )
        elif ptype == "page":
            pages[it.findtext("wp:post_name", namespaces=NS)] = {
                "title": it.findtext("title") or "",
                "content": it.findtext("content:encoded", namespaces=NS) or "",
                "status": it.findtext("wp:status", namespaces=NS),
            }
    return attachments, projects, pages


def norm_title(t):
    t = t.lower().replace("&amp;", " and ").replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t


# --------------------------------------------------------------- cards -----

def parse_cards(work_html):
    """Cards in work.html, in order: number, title, lede, specs, chips, habitat."""
    cards, habitat = [], None
    section = re.search(r"<p class=\"kicker\">Habitat ([IVX]+)[^<]*</p>", work_html)
    for m in re.finditer(
        r"<(?:div|a) class=\"spec-card\"(?:[^>]*)>(.*?)</(?:div|a)>\s*(?=<)",
        work_html,
        re.S,
    ):
        pass  # regex too fragile; use block scan below
    # block scan: each card starts at '<div class="spec-card">' or '<a class="spec-card"'
    starts = [m.start() for m in re.finditer(r"<(?:div|a) class=\"spec-card\"", work_html)]
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(work_html)
        block = work_html[s:e]
        # only top-level cards: these blocks include the trailing section close
        num = re.search(r"Nº\s*(\d+)", block)
        title = re.search(r"<h3 class=\"card-title\">(.*?)</h3>", block, re.S)
        lede = re.search(r"<p class=\"card-lede\">(.*?)</p>", block, re.S)
        specs = []
        for r in re.finditer(
            r"<dt>(.*?)</dt><span class=\"dots\"></span><dd>(.*?)</dd>", block
        ):
            specs.append((html_clean(r.group(1)), html_clean(r.group(2))))
        chips = [html_clean(c) for c in re.findall(r"<span class=\"chip\">(.*?)</span>", block)]
        if not (num and title):
            continue
        # habitat: last kicker before this card position
        hb = None
        for hm in re.finditer(
            r"<p class=\"kicker\">Habitat ([IVX]+)\s*<span[^>]*>\s*·\s*([^<]*)</span></p>",
            work_html,
        ):
            if hm.start() < s:
                hb = (hm.group(1), hm.group(2).strip())
        cards.append(
            {
                "num": int(num.group(1)),
                "title": htmlmod.unescape(title.group(1)).strip(),
                "lede": html_clean(lede.group(1)) if lede else "",
                "specs": specs,
                "chips": chips,
                "habitat": hb or ("I", ""),
            }
        )
    return cards


def html_clean(s):
    s = s.replace("\xa0", " ").replace("&nbsp;", " ")
    s = s.replace("</strong>", "</strong>")
    return s.strip()


# ------------------------------------------------------------- content -----

def strip_attrs(s):
    s = re.sub(r"\s+(target|rel)=\"[^\"]*\"", "", s)
    return s


def clean_inline(s):
    s = s.replace("\xa0", " ").replace("&nbsp;", " ")
    s = strip_attrs(s)
    # old internal links -> new page files
    s = re.sub(
        r"https?://scottduncombe\.com/project/([a-z0-9-]+)/?",
        r"../project/\1.html",
        s,
    )
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def project_content(content):
    """Split WP content: lede (first h3), prose paragraphs, field notes, gallery.
    WP's editor stored most body text as raw blank-line-separated lines (the
    theme ran wpautop at render time), so a paragraph is EITHER a <p> block
    OR a raw line group — parse sequentially to keep the original order."""
    body = content.replace("\r", "")
    gallery_ids = []
    body_lines = []
    for line in body.split("\n"):
        m = re.search(r"\[gallery[^\]]*ids=\"([\d,]+)\"[^\]]*\]", line)
        if m:
            gallery_ids += [i.strip() for i in m.group(1).split(",")]
            line = re.sub(r"\[gallery[^\]]*\]", "", line)
        body_lines.append(line)
    body = "\n".join(body_lines)

    h3 = re.search(r"<h3[^>]*>(.*?)</h3>", body, re.S)
    lede = clean_inline(h3.group(1)) if h3 else None
    body = re.sub(r"<h3[^>]*>.*?</h3>", "", body, count=1, flags=re.S)

    # A "field note" line: >> possibly wrapped in leading tags
    note_re = re.compile(r"^\s*(?:<[^>]+>\s*)*(?:(?:&gt;|>)\s*){2}")

    def as_note(text):
        t = note_re.sub("", text).strip()
        t = re.sub(r"<strong>\s*", "", t)
        t = re.sub(r"\s*</strong>", "", t)
        t = t.replace("&gt;&gt;", "").replace(">>", "").strip()
        t = re.sub(r"^\s*[—–-]\s*", "", t)
        t = re.sub(r"\s+", " ", t)
        return t.strip(" \xa0")

    # sequential scan: <p> blocks and raw text spans, in order
    token = re.compile(r"(<p[^>]*>.*?</p>)", re.S)
    prose, notes = [], []
    for part in token.split(body):
        if not part or not part.strip():
            continue
        if part.startswith("<p"):
            inner = part[part.index(">") + 1 : -4]
            blocks = [htmlmod.unescape(clean_inline(inner))]
        else:
            blocks = [
                htmlmod.unescape(clean_inline(b))
                for b in re.split(r"\n\s*\n", part)
            ]
        for text in blocks:
            if not text.strip():
                continue
            if note_re.match(text):
                t = as_note(text)
                if t:
                    notes.append(t)
            else:
                prose.append(clean_inline(text))
    return lede, prose, notes, gallery_ids


# ------------------------------------------------------------ templates ----

RAIL = """  <aside class="rail">
    <div class="rail-header">
      <a class="sig" href="{root}" aria-label="Scott Riker Duncombe — home">
        <svg viewBox="0 0 512 512" role="img" aria-hidden="true">
          <rect class="field" width="512" height="512" rx="96" fill="#580035"/>
          <path class="shade" d="M96 416 L416 96 V416 Z" fill="#ffffff" opacity="0.10"/>
          <path class="split" d="M96 416 L416 96" stroke="#fdfafc" stroke-width="10" stroke-linecap="round"/>
          <g class="s-ink"><text x="176" y="260" text-anchor="middle" dominant-baseline="central" font-family="Georgia, 'Times New Roman', serif" font-weight="bold" font-size="168" fill="#fdfafc">S</text></g>
          <g class="d-ink"><text x="330" y="336" text-anchor="middle" dominant-baseline="central" font-family="Georgia, 'Times New Roman', serif" font-weight="bold" font-size="168" fill="#f0c7dd">D</text></g>
        </svg>
      </a>
      <div class="photo-wrap"><img class="photo" src="{root}assets/img/me.jpg" alt="Scott Duncombe"></div>
      <p class="name"><a href="{root}">Scott Riker Duncombe</a></p>
      <p class="tagline">Creator of fine internet technologies for startups, nonprofits, candidates, organizers, &amp; most other folks.</p>
    </div>

    <div class="rail-content">
      <nav class="nav" aria-label="Main">
        <a href="{root}">Selected work</a>
        <a href="{root}work/">All the work</a>
        <a href="{root}about/">About</a>
        <a href="{root}press/">Press</a>
        <a href="{root}writing/">Dispatches</a>
      </nav>

      <ul class="social">
        <li><a href="https://github.com/mojowen">GitHub</a></li>
        <li><a href="https://www.linkedin.com/in/scottduncombe">LinkedIn</a></li>
        <li><a href="https://bsky.app/profile/sduncombe.bsky.social">Bluesky</a></li>
      </ul>
    </div>

    <div class="rail-footer">
      <p class="rail-foot">Portland, Oregon <span class="dot">working from anywhere</span></p>
    </div>
  </aside>
"""

HEAD = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Scott Riker Duncombe :: {title}</title>
  <meta name="description" content="{desc}">
  <!-- Open Graph -->
  <meta property="og:title" content="Scott Riker Duncombe :: {title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://scottduncombe.com/project/{slug}/">
  <meta property="og:image" content="{ogimg}">
  <meta property="og:image:alt" content="{title}">
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Scott Riker Duncombe :: {title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{ogimg}">
  <meta name="twitter:image:alt" content="{title}">
  <meta name="twitter:creator" content="@sduncombe">
  <meta name="twitter:site" content="@sduncombe">
  <link rel="icon" href="../assets/img/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,400;0,600;0,700;0,900;1,400;1,600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/site.css">
</head>
<body>

{rail}

  <main class="main">
    <div class="content">
"""

FOOT = """      <footer class="foot">
        <p>Proudly powered by <a href="https://polls.pizza">coffee &amp; free pizza</a> · <a href="https://github.com/mojowen">fork this code</a>.</p>
        <p class="mono">© <span data-year>2026</span> Scott Duncombe Web Design and all that · prototype v0</p>
      </footer>

    </div>
  </main>

  <script src="../assets/js/site.js"></script>
</body>
</html>
"""


def render_project(card, wp, images, next_card, repo):
    root = "../../"
    title = card["title"]
    lede, prose, notes, gallery_ids = project_content(wp["content"])
    lede = lede or card["lede"]
    # description: tag-free lede, capped
    plain_lede = htmlmod.unescape(re.sub(r"<[^>]+>", "", lede or ""))
    desc = plain_lede if len(plain_lede) < 180 else plain_lede[:177] + "..."

    ogimg = "https://scottduncombe.com/assets/img/me.jpg"
    if wp["thumb"] and wp["thumb"] in images:
        local = images[wp["thumb"]]
        ogimg = "https://scottduncombe.com/assets/img/uploads/" + local

    specs = "\n".join(
        f'          <div class="row"><dt>{dt}</dt><span class="dots"></span><dd>{dd}</dd></div>'
        for dt, dd in card["specs"]
    )
    chips = "".join(f'<span class="chip">{c}</span>' for c in card["chips"])

    out = [HEAD.format(rail=RAIL.format(root=root), title=title, slug=wp["slug"], desc=htmlmod.escape(desc), ogimg=ogimg)]
    out.append(
        f"""      <p class="kicker">Specimen Nº {card['num']:02d} <span class="no">· Habitat {card['habitat'][0]} — {card['habitat'][1]}</span></p>
      <h1 class="display">{title}</h1>
      <p class="lede">{lede}</p>

      <div class="specimen-head">
        <span class="sticker stamp">Specimen</span>
        <dl class="specs">
{specs}
        </dl>
        <div class="chips">{chips}</div>
      </div>

      <div class="prose" style="margin-top: 34px;">
"""
    )
    for p in prose:
        out.append(f"        <p>{p}</p>\n")
    out.append("      </div>\n")

    if gallery_ids:
        imgs = []
        for gid in gallery_ids:
            if gid in images:
                local = images[gid]
                imgs.append(
                    f'          <img src="../assets/img/uploads/{local}" alt="{title} — plate">'
                )
        if imgs:
            out.append(
                """      <section class="section">
        <p class="kicker">Plates <span class="no">· from the field</span></p>
        <div class="gallery">
"""
                + "\n".join(imgs)
                + "\n        </div>\n      </section>\n"
            )

    if notes:
        out.append(
            """      <section class="section field-notes">
        <p class="kicker">Field notes</p>
"""
        )
        for n in notes:
            out.append(f'        <div class="note">{n}</div>\n')
        out.append("      </section>\n")

    nxt = (
        f'<a href="{next_card["slug"]}.html">next specimen: {next_card["title"]} →</a>'
        if next_card
        else ""
    )
    out.append(
        f"""      <nav class="prevnext">
        <a href="../work.html">← back to the field guide</a>
        {nxt}
      </nav>

{FOOT}"""
    )
    return "".join(out)


# ----------------------------------------------------------------- main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wxr", required=True)
    ap.add_argument("--img-mirror", required=True, help="dir mirroring wp-content/uploads/")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()

    attachments, wps, pages = parse_wxr(args.wxr)

    # id -> local uploads path (copy from mirror into repo)
    images = {}
    needed = set()
    for wp in wps:
        if wp["slug"] in SKIP_SLUGS:
            continue
        if wp["thumb"]:
            needed.add(wp["thumb"])
        needed.update(wp["gallery_ids"])
    for pid in needed:
        if pid in attachments:
            url = attachments[pid]
            if not url.startswith(UPLOADS_PREFIX):
                continue
            rel = url[len(UPLOADS_PREFIX):]
            src = os.path.join(args.img_mirror, rel)
            if os.path.exists(src):
                images[pid] = rel

    work_path = os.path.join(args.repo, "work/index.html")
    work_html = open(work_path).read()
    cards = parse_cards(work_html)
    by_norm = {norm_title(c["title"]): c for c in cards}

    # order: work.html card order restricted to WP projects we generate
    gen = []
    for c in cards:
        match = next((w for w in wps if norm_title(w["title"]) == norm_title(c["title"])), None)
        if match and match["slug"] not in SKIP_SLUGS:
            gen.append((c, match))
    # moodmonitor card has no WP twin; keep order of cards for next-links
    print("generating", len(gen), "project pages:")
    for card, wp in gen:
        # next specimen = next generated card (by card number)
        later = sorted((c2 for c2, _ in gen if c2["num"] > card["num"]), key=lambda c: c["num"])
        next_card = None
        if later:
            nxt_wp = next(w2 for c2, w2 in gen if c2["num"] == later[0]["num"])
            next_card = {"slug": nxt_wp["slug"], "title": later[0]["title"]}
        page = render_project(card, wp, images, next_card, args.repo)
        out_dir = os.path.join(args.repo, "project", wp["slug"])
        os.makedirs(out_dir, exist_ok=True)
        open(os.path.join(out_dir, "index.html"), "w").write(page)
        print(f"  project/{wp['slug']}/  (Nº {card['num']:02d}, {len(wp['gallery_ids'])} plates)")

    # copy needed images into repo
    copied = 0
    for pid, rel in images.items():
        src = os.path.join(args.img_mirror, rel)
        dst = os.path.join(args.repo, "assets", "img", "uploads", rel)
        if os.path.exists(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    print("copied", copied, "images into assets/img/uploads/")

    # link cards in work.html: wrap each unlinked <div class="spec-card"> in an
    # <a>, matching the div's OWN closing tag via depth counting
    slug_by_num = {card["num"]: wp["slug"] for card, wp in gen}
    s = open(work_path).read()
    opens = [m for m in re.finditer(r'<div class="spec-card">', s)]
    for m in reversed(opens):
        # find matching close: scan div tokens after the open tag
        depth, pos = 1, m.end()
        close = None
        for t in re.finditer(r'<div\b[^>]*>|</div>', s[m.end():]):
            if t.group(0).startswith("<div"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    close = m.end() + t.start()
                    break
        if close is None:
            print("WARN: unmatched div for card at", m.start())
            continue
        block = s[m.start():close + len("</div>")]
        num = re.search(r"Nº\s*(\d+)", block)
        if not num or int(num.group(1)) not in slug_by_num:
            continue
        slug = slug_by_num[int(num.group(1))]
        linked = f'<a class="spec-card" href="../project/{slug}/">' + block[len('<div class="spec-card">'):-len("</div>")] + "</a>"
        s = s[:m.start()] + linked + s[close + len("</div>"):]
    open(work_path, "w").write(s)
    print("work.html cards linked")

    # repair broken rails (\\1 / \\2 placeholders) in root pages + project pages
    fixed = []
    for path in [
        "about/index.html", "press/index.html", "work/index.html", "writing/index.html",
        "project/moodmonitor/index.html", "project/pizza-to-the-polls/index.html",
        "project/power-the-polls/index.html",
    ]:
        p = os.path.join(args.repo, path)
        if not os.path.exists(p):
            continue
        s = open(p).read()
        root = "../../" if path.startswith("project/") else "../"
        active = {
            "index.html": {"about": "About", "press": "Press", "work": "All the work", "writing": "Dispatches"},
        }.get(os.path.basename(os.path.dirname(path)), {})
        nav_repl = RAIL.format(root=root)
        # build nav+social block with active state
        block = f"""<div class="rail-content">
      <nav class="nav" aria-label="Main">
        <a href="{root}">Selected work</a>
        <a href="{root}work/">All the work</a>
        <a href="{root}about/">About</a>
        <a href="{root}press/">Press</a>
        <a href="{root}writing/">Dispatches</a>
      </nav>

      <ul class="social">
        <li><a href="https://github.com/mojowen">GitHub</a></li>
        <li><a href="https://www.linkedin.com/in/scottduncombe">LinkedIn</a></li>
        <li><a href="https://bsky.app/profile/sduncombe.bsky.social">Bluesky</a></li>
      </ul>
    </div>"""
        if active:
            block = block.replace(f">{active}</a>", f' class="active">{active}</a>', 1)
        new_s, n = re.subn(
            r'<div class="rail-content">\s*\\1\s*\\?\s*\\2\s*</div>',
            lambda m: block,
            s,
        )
        if n:
            open(p, "w").write(new_s)
            fixed.append((path, n))
    print("rails repaired:", fixed if fixed else "none found")


if __name__ == "__main__":
    main()