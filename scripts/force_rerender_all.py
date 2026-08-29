#!/usr/bin/env python3
"""
Force all HTML slides to re-render by setting their source_hash to a
sentinel value ('0000000000000000') that will never match the actual
source hash.

Use when: source md was changed but the HTML content is outdated,
and the embedded hash comment was incorrectly seeded to match the
current source (so delta check would skip re-render).

Run once, then commit, then run the pipeline.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'static' / 'slides_decks'

PLACEHOLDER = '0000000000000000'
pattern = re.compile(r'<!--\s*source_hash:\s*[0-9a-f]{16}\s*-->')

count = 0
for html_file in sorted(OUT_DIR.glob('*/pages/*.html')):
    text = html_file.read_text(errors='ignore')
    new_text = pattern.sub(f'<!-- source_hash: {PLACEHOLDER} -->', text)
    if new_text != text:
        html_file.write_text(new_text)
        count += 1

print(f'Updated {count} HTML files with placeholder hash.')
print(f'Next: run the pipeline to re-render all slides.')
