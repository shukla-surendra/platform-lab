import re, sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
target_file = sys.argv[1]
enrich_file = sys.argv[2]

raw = Path(enrich_file).read_text(encoding='utf-8')
chunks = raw.split('%%TITLE%%')[1:]
entries = {}
order = []
for c in chunks:
    title_line, rest = c.split('\n', 1)
    title = title_line.strip()
    body = rest.split('%%BODY%%', 1)[1].split('%%END%%', 1)[0].strip('\n')
    entries[title] = body.strip()
    order.append(title)

path = repo / target_file
text = path.read_text(encoding='utf-8')
lines = text.split('\n')

# find all top-level heading line indices (exact "# Title")
heading_idxs = [i for i, l in enumerate(lines) if l.startswith('# ')]

# map title -> (start_idx, end_idx) using EXACT heading line match "# Title"
title_to_range = {}
dupes = {}
for n, idx in enumerate(heading_idxs):
    title = lines[idx][2:].strip()
    end = heading_idxs[n+1] if n+1 < len(heading_idxs) else len(lines)
    if title in title_to_range:
        dupes.setdefault(title, []).append((idx, end))
    else:
        title_to_range[title] = (idx, end)

missing = []
applied = []
# Apply replacements from bottom to top so earlier line indices stay valid
replacements = []
for title in order:
    if title not in title_to_range:
        missing.append(title)
        continue
    start, end = title_to_range[title]
    # sanity: the block between start+1 and end (exclusive of next heading) must end with the back-link
    block_lines = lines[start:end]
    # strip trailing blank lines
    while block_lines and block_lines[-1].strip() == '':
        block_lines.pop()
    if not block_lines or '[↑ Back to index](#index)' not in block_lines[-1]:
        missing.append(title + ' (no backlink at end, skipped for safety)')
        continue
    replacements.append((start, end, title))

for start, end, title in sorted(replacements, key=lambda x: -x[0]):
    body = entries[title]
    new_block = [f"# {title}", ""] + body.split('\n') + ["", "[↑ Back to index](#index)", ""]
    lines[start:end] = new_block
    applied.append(title)

path.write_text('\n'.join(lines), encoding='utf-8')
print(f"Applied {len(applied)}/{len(order)}")
if missing:
    print("MISSING/SKIPPED:", missing)
if dupes:
    print("WARNING duplicate headings found for:", list(dupes.keys()))
