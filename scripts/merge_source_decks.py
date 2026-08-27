#!/usr/bin/env python3
"""
Merge source .md files (open-source-economics-lecture/) into unified lecture decks.

Rules:
- Files starting with 'economic-of-open-source-lecture-N*' are grouped by lecture number N
- Within each lecture, files sorted by: main (no -part), then part-2, part-3...
- Keep ONE header (from first file), strip headers from subsequent files
- Slide numbers are already continuous across files
- Output: content/slides_decks/{lecture-slug}.md
"""
import os, re, sys
from collections import OrderedDict

SRC = '/home/lee/developing/markdown-to-slides/open-source-economics-lecture'
OUT = '/home/lee/developing/os-economic-slides/content/slides_decks'

os.makedirs(OUT, exist_ok=True)

# Group files by lecture number
groups = OrderedDict()
for f in sorted(os.listdir(SRC)):
    if not f.endswith('.md'):
        continue
    # Skip non-lecture files
    m = re.match(r'economic-of-open-source-lecture-(\d+)(?:-(.+))?\.md', f)
    if not m:
        continue
    num = int(m.group(1))
    groups.setdefault(num, []).append(f)

# Sort each lecture's files: main first, then part-2, part-3...
for num in groups:
    files = groups[num]
    def sort_key(f):
        if '-part' not in f:
            return (0, 0)
        m = re.search(r'part-(\d+)', f)
        return (1, int(m.group(1)) if m else 0)
    groups[num].sort(key=sort_key)

# Lecture slug mapping (for Hugo URL)
lecture_titles = {
    0:  '00-introduction',
    1:  '01-software-business',
    2:  '02-intellectual-property',
    3:  '03-business-model',
    4:  '04-labor-market',
    5:  '05-transaction-cost',
    6:  '06-organization-governance',
    7:  '07-political-economy',
    8:  '08-information-economy',
    9:  '09-proprietary-rights',
    10: '10-labor-compensation',
    11: '11-culture-matters',
}

for num in sorted(groups):
    files = groups[num]
    slug = lecture_titles.get(num, f'{num:02d}-lecture-{num}')
    out_path = f'{OUT}/{slug}.md'

    parts = []
    for i, f in enumerate(files):
        text = open(SRC + '/' + f).read()
        if i == 0:
            # Keep full first file (header + slides)
            parts.append(text.rstrip())
        else:
            # Strip everything before first "## Slide"
            m = re.search(r'\n## Slide \d+', text)
            if m:
                parts.append(text[m.start()+1:].rstrip())
            else:
                parts.append(text.rstrip())

    merged = '\n\n'.join(parts)
    open(out_path, 'w').write(merged + '\n')

    # Stats
    total_slides = merged.count('## Slide ')
    first_slides = re.findall(r'## Slide (\d+)', merged)
    print(f"Lecture {num:02d} ({slug}): {len(files)} files → {total_slides} slides "
          f"(nums {first_slides[0]}–{first_slides[-1]})")

print(f"\nOutput: {OUT}/")
print(f"Total files: {sum(len(v) for v in groups.values())}")
print(f"Total decks: {len(groups)}")