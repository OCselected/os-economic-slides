#!/usr/bin/env python3
"""
One-time migration: embed source_hash comments into legacy HTML slides.

Legacy slides rendered before the hash-embedding feature have no
<!-- source_hash: ... --> comment. Without it, the delta check in
render_slide.py would re-render them on every pipeline run.

This script seeds each legacy HTML with the CURRENT source hash.
Run once, then commit the changed HTML files to git.

Usage:
  python3 scripts/migrate_slides_hash.py              # all decks
  python3 scripts/migrate_slides_hash.py --deck NAME  # one deck
  python3 scripts/migrate_slides_hash.py --dry-run    # preview only
"""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from render_slide import (
    SOURCE_DIR, OUT_DIR, parse_deck, slide_source_hash, extract_embedded_hash,
)


def migrate(deck_name: str, dry_run: bool = False) -> dict:
    src = SOURCE_DIR / f'{deck_name}.md'
    out = OUT_DIR / deck_name / 'pages'
    if not src.exists():
        return {'deck': deck_name, 'error': 'source missing'}
    if not out.exists():
        return {'deck': deck_name, 'error': 'out dir missing'}

    header, slides = parse_deck(src)
    seeded = 0
    already = 0
    changed_files = []

    for s in slides:
        page = out / f'page_{s["num"]:03d}.html'
        if not page.exists():
            continue
        text = page.read_text(errors='ignore')
        if extract_embedded_hash(text) is not None:
            already += 1
            continue

        new_hash = slide_source_hash(header, s)
        if '<html' in text.lower():
            new_text = re.sub(
                r'(<html[^>]*>)',
                r'\1<!-- source_hash: ' + new_hash + ' -->',
                text,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            new_text = f'<!-- source_hash: {new_hash} -->\n{text}'

        if new_text != text:
            changed_files.append(page)
            if not dry_run:
                page.write_text(new_text)
            seeded += 1

    return {
        'deck': deck_name,
        'seeded': seeded,
        'already_had_hash': already,
        'changed_files': [str(p.relative_to(OUT_DIR.parent.parent)) for p in changed_files],
    }


def main():
    dry_run = '--dry-run' in sys.argv
    deck_arg = None
    if '--deck' in sys.argv:
        i = sys.argv.index('--deck')
        if i + 1 < len(sys.argv):
            deck_arg = sys.argv[i + 1]

    if deck_arg:
        decks = [deck_arg]
    else:
        decks = sorted(p.stem for p in SOURCE_DIR.glob('*.md'))

    total_seeded = 0
    total_files = []
    for deck in decks:
        r = migrate(deck, dry_run)
        if r.get('error'):
            print(f'  {deck}: ERROR {r["error"]}')
            continue
        print(f'  {deck}: seeded {r["seeded"]}, already {r["already_had_hash"]}')
        total_seeded += r['seeded']
        total_files.extend(r['changed_files'])

    verb = 'WOULD seed' if dry_run else 'Seeded'
    print(f'\n{verb} {total_seeded} slide(s) across {len(decks)} deck(s).')
    if total_files:
        print('\nChanged files:')
        for f in sorted(set(total_files)):
            print(f'  {f}')
        if not dry_run:
            print('\nNow commit these to git:')
            print(f'  git add {total_files[0]}')


if __name__ == '__main__':
    main()
