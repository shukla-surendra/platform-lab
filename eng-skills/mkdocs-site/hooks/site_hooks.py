"""MkDocs hooks for the eng-skills site.

1. Parses the word-bank Markdown files into flashcard decks and writes them to
   site/assets/flashcards/*.json (consumed by the Practice → Flashcards page and the
   home page's Word of the Day).
2. Turns word-bank pages (vocab, phrasal verbs, idioms, ...) into a filterable list:
   every entry is wrapped in <section class="wb-entry">, the giant A–Z link wall is
   collapsed into a <details>, and a toolbar (filter box, A–Z strip, random) is injected.
3. Replaces {{count:<deck>}} / {{count:total}} placeholders in pages with live counts.

The source .md files are never modified — everything happens at build time.
"""
from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

import markdown as md_lib
from pymdownx.slugs import slugify

_slug = slugify(case="lower")

# deck id -> (source path, entry heading level, label, short description)
DECKS = {
    "vocab": ("Vocabulary-Collections/vocab.md", 1, "Vocabulary", "Single words"),
    "phrasal": ("Vocabulary-Collections/phrasal-verbs.md", 1, "Phrasal Verbs", "Verb + particle"),
    "idioms": ("Vocabulary-Collections/idioms.md", 1, "Idioms", "Fixed expressions"),
    "technical": ("Vocabulary-Collections/technical-english.md", 1, "Technical English", "Architecture verbs & phrases"),
    "business": ("Vocabulary-Collections/business-communication.md", 2, "Business", "Meeting & business idioms"),
    "architect": ("Vocabulary-Collections/architect-influence-word-table.md", 0, "Architect Register", "Influence phrases (table)"),
}
WORD_BANK_PAGES = {src: (level, deck) for deck, (src, level, *_rest) in DECKS.items() if level}
SKIP_TITLES = {"index", "contents"}
MAX_BODY_CHARS = 2600

_cache: dict[str, list[dict]] = {}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
PRON_RE = re.compile(r"^\*Pronunciation:\*\s*(.+)$")
BACK_RE = re.compile(r"^\s*\[↑ Back to index\]\(#index\)\s*$")
NUMBERED_RE = re.compile(r"^\d+\.\s+")


def _plain(text: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    return text.strip()


def _url_for(src: str) -> str:
    return src[:-3] + "/"


def _unique(base: str, seen: set[str]) -> str:
    """Mirror python-markdown toc's duplicate-id handling (foo, foo_1, foo_2...)."""
    candidate = base
    n = 0
    while candidate in seen or not candidate:
        n += 1
        candidate = f"{base}_{n}"
    seen.add(candidate)
    return candidate


def _render(body_lines: list[str]) -> str:
    body = "\n".join(body_lines).strip()
    if len(body) > MAX_BODY_CHARS:
        cut = body.rfind("\n", 0, MAX_BODY_CHARS)
        body = body[: cut if cut > 0 else MAX_BODY_CHARS].rstrip() + "\n\n…"
    out = md_lib.markdown(body, extensions=["tables", "sane_lists"])
    # in-page anchors from the source file don't resolve inside a flashcard
    return re.sub(r'<a href="#[^"]*">([^<]*)</a>', r"\1", out)


def _parse_heading_deck(path: Path, src: str, level: int) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    url = _url_for(src)
    seen_ids: set[str] = set()
    cards: list[dict] = []
    current: dict | None = None
    in_fence = False
    first_h1_seen = False

    def flush():
        if current is not None:
            current["h"] = _render(current.pop("_body"))
            cards.append(current)

    for line in lines:
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        m = None if in_fence else HEADING_RE.match(line)
        if m:
            depth, raw = len(m.group(1)), m.group(2)
            title = _plain(raw)
            anchor = _unique(_slug(title, "-"), seen_ids)
            is_page_title = depth == 1 and not first_h1_seen
            if depth == 1:
                first_h1_seen = True
            if depth <= level:
                flush()
                current = None
                if is_page_title or title.lower() in SKIP_TITLES:
                    continue
                if depth == level:
                    if level == 1 and NUMBERED_RE.match(title) and len(title.split()) > 5:
                        continue  # stray numbered sub-meaning promoted to H1 in the source
                    current = {"t": NUMBERED_RE.sub("", title), "u": f"{url}#{anchor}", "p": "", "_body": []}
                continue
        if current is None:
            continue
        if BACK_RE.match(line):
            continue
        pm = PRON_RE.match(line.strip())
        if pm and not current["p"]:
            current["p"] = pm.group(1).strip()
            continue
        current["_body"].append(line)
    flush()
    return [c for c in cards if c["t"]]


def _parse_table_deck(path: Path, src: str) -> list[dict]:
    url = _url_for(src)
    cards = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---") or "Term / Phrase" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        _, term, typ, func, meaning, example = cells[:6]
        body = (
            f'<p class="fc-meta">{html_lib.escape(typ)} · {html_lib.escape(func)}</p>'
            f"<p>{html_lib.escape(meaning)}</p>"
            f"<blockquote><p>{html_lib.escape(example)}</p></blockquote>"
        )
        cards.append({"t": term, "u": url, "p": "", "h": body})
    return cards


def _load_decks(docs_dir: str) -> dict[str, list[dict]]:
    root = Path(docs_dir)
    decks = {}
    for deck, (src, level, *_rest) in DECKS.items():
        path = root / src
        if not path.exists():
            decks[deck] = []
            continue
        decks[deck] = _parse_table_deck(path, src) if level == 0 else _parse_heading_deck(path, src, level)
    return decks


# ---------------------------------------------------------------- mkdocs events

def on_pre_build(config, **_):
    _cache.clear()
    _cache.update(_load_decks(config["docs_dir"]))


def on_page_markdown(markdown, page, config, files, **_):
    if "{{count:" in markdown:
        total = sum(len(v) for v in _cache.values())

        def repl(m):
            key = m.group(1)
            n = total if key == "total" else len(_cache.get(key, []))
            return f"{n:,}"

        markdown = re.sub(r"\{\{count:([a-z]+)\}\}", repl, markdown)
    if page.file.src_uri in WORD_BANK_PAGES:
        hide = page.meta.setdefault("hide", [])
        if "toc" not in hide:
            hide.append("toc")
    return markdown


_TAG_RE = re.compile(r"<[^>]+>")


def _heading_text(chunk: str, level: int) -> tuple[str, str]:
    m = re.match(rf'<h{level} id="([^"]*)"[^>]*>(.*?)</h{level}>', chunk, re.S)
    if not m:
        return "", ""
    text = html_lib.unescape(_TAG_RE.sub("", m.group(2))).replace("¶", "").strip()
    return m.group(1), text


def on_page_content(html, page, config, files, **_):
    info = WORD_BANK_PAGES.get(page.file.src_uri)
    if not info:
        return html
    level, deck = info
    parts = re.split(rf'(?=<h{level} id=")', html)
    head_parts, entries, index_block = [], [], None
    first_letter: dict[str, str] = {}
    for i, chunk in enumerate(parts):
        anchor, text = _heading_text(chunk, level)
        if not anchor:
            head_parts.append(chunk)
            continue
        if level == 1 and not entries and not head_parts_has_title(head_parts):
            head_parts.append(chunk)  # the page's own <h1> title + intro (+ index h2)
            continue
        if text.lower() in SKIP_TITLES:
            index_block = chunk
            continue
        letter = text[:1].upper()
        letter = letter if "A" <= letter <= "Z" else "#"
        first_letter.setdefault(letter, anchor)
        entries.append(
            f'<section class="wb-entry" data-term="{html_lib.escape(text.lower(), quote=True)}" '
            f'data-letter="{letter}">{chunk}</section>'
        )

    # level-1 pages: the index h2 lives inside the title chunk — pull it out
    head = "".join(head_parts)
    if index_block is None:
        m = re.search(r'<h2 id="(index|contents)"', head)
        if m:
            index_block, head = head[m.start():], head[: m.start()]
    index_html = ""
    if index_block:
        inner = re.sub(r"^<h\d[^>]*>.*?</h\d>", "", index_block, count=1, flags=re.S)
        index_html = (
            '<details class="wb-index"><summary>Full A–Z index (classic view)</summary>'
            f"{inner}</details>"
        )

    letters = "".join(
        f'<a class="wb-letter" href="#{first_letter[l]}" data-letter="{l}">{l}</a>'
        if l in first_letter
        else f'<span class="wb-letter is-empty">{l}</span>'
        for l in [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "#"]
        if l != "#" or "#" in first_letter
    )
    toolbar = f"""
<div class="wb-toolbar" data-deck="{deck}">
  <div class="wb-row">
    <div class="wb-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 3A6.5 6.5 0 0 1 16 9.5c0 1.61-.59 3.09-1.56 4.23l.27.27h.79l5 5-1.5 1.5-5-5v-.79l-.27-.27A6.52 6.52 0 0 1 9.5 16 6.5 6.5 0 0 1 3 9.5 6.5 6.5 0 0 1 9.5 3m0 2C7 5 5 7 5 9.5S7 14 9.5 14 14 12 14 9.5 12 5 9.5 5Z"/></svg>
      <input type="search" class="wb-filter" placeholder="Filter {len(entries):,} entries…" aria-label="Filter entries" autocomplete="off">
    </div>
    <label class="wb-deep"><input type="checkbox" class="wb-deep-toggle"> search meanings too</label>
    <span class="wb-count"><b>{len(entries):,}</b> entries</span>
    <button type="button" class="wb-btn wb-random" title="Jump to a random entry">🎲 Random</button>
    <a class="wb-btn wb-practice" href="{_rel(page, 'practice/flashcards/')}?deck={deck}" title="Practise these as flashcards">🃏 Practise</a>
  </div>
  <nav class="wb-letters" aria-label="Jump to letter">{letters}</nav>
</div>"""
    return head + toolbar + index_html + '<div class="wb-list">' + "".join(entries) + "</div>" + '<p class="wb-empty" hidden>No entries match your filter.</p>'


def head_parts_has_title(parts: list[str]) -> bool:
    return any(re.search(r"<h1 id=", p) for p in parts)


def _rel(page, target: str) -> str:
    depth = page.url.count("/")
    return "../" * depth + target


def on_post_build(config, **_):
    out = Path(config["site_dir"]) / "assets" / "flashcards"
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for deck, (src, _level, label, desc) in DECKS.items():
        cards = _cache.get(deck, [])
        (out / f"{deck}.json").write_text(json.dumps(cards, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index.append({"id": deck, "label": label, "desc": desc, "count": len(cards), "page": _url_for(src)})
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
