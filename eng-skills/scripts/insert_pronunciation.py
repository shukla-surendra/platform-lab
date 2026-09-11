"""Insert a *Pronunciation:* line into existing word-bank entries without
touching the rest of the entry body. Safe by construction: it only inserts
at a known heading-line index, it never deletes or replaces existing lines.

Usage: python3 scripts/insert_pronunciation.py <file.md> <scratch.txt>

Scratch file format (one per entry):
%%TITLE%%Word
%%PRON%%uh-BUR-in-teet
%%END%%
"""
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
target_file = sys.argv[1]
pron_file = sys.argv[2]

raw = Path(pron_file).read_text(encoding='utf-8')
chunks = raw.split('%%TITLE%%')[1:]
prons = {}
order = []
for c in chunks:
    title_line, rest = c.split('\n', 1)
    title = title_line.strip()
    pron = rest.split('%%PRON%%', 1)[1].split('%%END%%', 1)[0].strip()
    prons[title] = pron
    order.append(title)

path = repo / target_file
text = path.read_text(encoding='utf-8')
lines = text.split('\n')

heading_idxs = [i for i, l in enumerate(lines) if l.startswith('# ')]
title_to_idx = {}
dupes = set()
for idx in heading_idxs:
    title = lines[idx][2:].strip()
    if title in title_to_idx:
        dupes.add(title)
    else:
        title_to_idx[title] = idx

missing = []
insertions = []  # (idx, title)
for title in order:
    if title not in title_to_idx:
        missing.append(title)
        continue
    if title in dupes:
        missing.append(title + ' (duplicate heading, skipped for safety)')
        continue
    insertions.append((title_to_idx[title], title))

# insert from bottom to top so earlier indices stay valid
applied = []
for idx, title in sorted(insertions, key=lambda x: -x[0]):
    # heading line is lines[idx] == "# Title"; next line should be blank, then body starts
    insert_at = idx + 1
    # skip the single blank line after heading if present
    if insert_at < len(lines) and lines[insert_at].strip() == '':
        insert_at += 1
    new_lines = [f"*Pronunciation:* {prons[title]}", ""]
    lines[insert_at:insert_at] = new_lines
    applied.append(title)

path.write_text('\n'.join(lines), encoding='utf-8')
print(f"Inserted {len(applied)}/{len(order)}")
if missing:
    print("MISSING/SKIPPED:", missing)
