"""Rank word-bank entries by how sparse their explanation is.

Usage: python3 scripts/audit_gaps.py <file.md>

Prints one line per `# Title` entry, worst (shortest, no example) first:
  <word_count>  ex=<0|1>  mw=<0|1>  <title>
ex=1 means a quoted example sentence was found; mw=1 means a part-of-speech
or "means/refers to" cue was found. Only scans top-level `# ` headings — all
current word banks (vocab.md, phrasal-verbs.md, idioms.md) use that level;
a file using `## ` headings would need that flag added first.
"""
import re, sys, json
from pathlib import Path

def parse_entries(path):
    text = Path(path).read_text(encoding='utf-8')
    lines = text.split('\n')
    # find top-level headings "# Title" after the index (skip first heading which is doc title)
    heading_idxs = [i for i,l in enumerate(lines) if l.startswith('# ')]
    entries = []
    for n, idx in enumerate(heading_idxs):
        title = lines[idx][2:].strip()
        if title.lower() in ('vocabulary','phrasal verbs','idioms'):
            continue
        end = heading_idxs[n+1] if n+1 < len(heading_idxs) else len(lines)
        body = lines[idx+1:end]
        body_text = '\n'.join(body).strip()
        entries.append((title, body_text))
    return entries

def score(body):
    # crude richness heuristics
    word_count = len(body.split())
    has_example = bool(re.search(r'["“].{5,}["”]', body)) or bool(re.search(r'\*".{5,}"\*', body))
    has_meaning_word = bool(re.search(r'\b(means?|meaning|refers to|used to|used when|verb|noun|adjective|adverb)\b', body, re.I))
    return word_count, has_example, has_meaning_word

def audit(path):
    entries = parse_entries(path)
    results = []
    for title, body in entries:
        wc, ex, mw = score(body)
        results.append({'title': title, 'words': wc, 'has_example': ex, 'has_meaning_word': mw})
    return results

if __name__ == '__main__':
    path = sys.argv[1]
    results = audit(path)
    results.sort(key=lambda r: (r['has_example'], r['words']))
    for r in results:
        print(f"{r['words']:4d}  ex={int(r['has_example'])}  mw={int(r['has_meaning_word'])}  {r['title']}")
