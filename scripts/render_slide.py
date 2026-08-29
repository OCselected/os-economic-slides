#!/usr/bin/env python3
"""
Incremental single-slide / delta-deck renderer.

Only generates HTML for slides that are missing or explicitly requested.
This is the cost-efficient way to update content: edit the source .md,
then render only the changed slides.

Source markdown lives at:  scripts/slides_decks_source/{deck}.md
Output HTML lives at:       static/slides_decks/{deck}/pages/page_NNN.html

Usage:
  # Re-render only missing slides for a deck (delta mode):
  python3 scripts/render_slide.py --deck 01-software-business

  # Force re-render a specific slide:
  python3 scripts/render_slide.py --deck 01-software-business --slide 12

  # Force re-render a range of slides:
  python3 scripts/render_slide.py --deck 01-software-business --range 10-15

  # List all slides in a deck (dry run):
  python3 scripts/render_slide.py --deck 01-software-business --list

Notes:
  - Uses the same SYSTEM prompt and generate logic as generate_deck_slides.py
  - Does NOT touch .state.json (full-deck tool uses that for progress)
  - Skips any slide whose page_NNN.html already exists unless --slide/--range forces it
"""
import re, sys, time, json, hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / '.hermes' / 'skills' / 'sn-ppt-standard' / 'lib'))
from model_client import llm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / 'scripts' / 'slides_decks_source'
OUT_DIR = ROOT / 'static' / 'slides_decks'

SYSTEM = """You are a slide designer. Generate ONE complete standalone HTML document for a single slide.

Style system (Bauhaus academic):
- canvas: 1600 x 900 exactly
- background: warm parchment #F5F0E8
- primary ink: Prussian blue #1B3B6B
- secondary: copper #8B7355, muted gray #555
- fonts: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', serif for headings; 'Noto Sans SC' for body
- Bauhaus geometric composition: circles, squares, lines as decoration
- dark academic tone, restrained, intellectual
- no emoji, no icons, no gradients except subtle parchment texture
- use the provided visual metaphor as the central visual element

HTML contract:
- output ONLY the HTML document, no markdown fences, no explanation
- <!DOCTYPE html><html><head><meta charset="UTF-8"><title>... title ...</title><style>... all CSS inline ...</style></head><body>...</body></html>
- body/html must set width:1600px; height:900px; overflow:hidden; margin:0
- all positioning absolute or flex within 1600x900
- no viewport units (vw/vh), no @media queries, no transform:scale
- decorative classes are fine but must be defined in the <style>
- content language zh-CN
"""


def parse_deck(path):
    text = Path(path).read_text()
    header_m = re.match(r'^(.*?)(?=\n## Slide \d+)', text, re.DOTALL)
    header = header_m.group(1).strip() if header_m else ''
    slides = []
    for m in re.finditer(r'## Slide (\d+)\s*(.*?)(?=\n## Slide \d+|\Z)', text, re.DOTALL):
        slides.append({'num': int(m.group(1)), 'content': m.group(2).strip()})
    return header, slides


def slide_source_hash(header, slide):
    """Compute a stable hash of the source content that determines the rendered HTML.

    Includes both the deck-wide header (affects style) and this slide's content
    (affects text + visual metaphor). This way, either changing the header or
    changing the slide content will produce a different hash.
    """
    # Normalize whitespace to avoid accidental noise (trailing spaces, blank lines)
    norm = re.sub(r'\s+', ' ', f"{header}|||{slide['content']}").strip()
    return hashlib.sha256(norm.encode('utf-8')).hexdigest()[:16]


def extract_embedded_hash(html_text):
    """Extract the source_hash embedded in a previously rendered HTML file.

    Format: <!-- source_hash: abc12345 -->  (injected right after <html> tag)
    Returns None if no hash comment is found (legacy HTML rendered before this feature).
    """
    m = re.search(r'<!--\s*source_hash:\s*([0-9a-f]{16})\s*-->', html_text, re.IGNORECASE)
    return m.group(1) if m else None


def needs_render(page_path, expected_hash):
    """Decide whether to (re)render a slide given its existing HTML.

    Returns True (render) if:
      - page file doesn't exist
      - page file exists but has no embedded hash (legacy)
      - page file exists but embedded hash != expected_hash (source changed)
    Returns False (skip) only if the hash matches.
    """
    if not page_path.exists():
        return True
    embedded = extract_embedded_hash(page_path.read_text(errors='ignore'))
    if embedded is None:
        # Legacy HTML: no hash embedded. Be safe and re-render.
        return True
    return embedded != expected_hash


def generate_slide(header, slide, retries=3):
    prompt = f"""Context (deck-wide style and theme):
{header}

Generate the HTML for this slide:
{slide['content']}
"""
    for i in range(retries):
        try:
            raw = llm(SYSTEM, prompt, timeout=300, model='sensenova-6.8-flash-lite')
            raw = re.sub(r'^```html\s*', '', raw, flags=re.IGNORECASE | re.MULTILINE)
            raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
            if '<!DOCTYPE html>' not in raw and '<html' not in raw.lower():
                raise ValueError('output missing HTML doctype/html tag')
            if '<style>' not in raw:
                raise ValueError('output missing inline <style>')
            return raw
        except Exception as e:
            print(f'  retry {i+1}/{retries}: {e}', file=sys.stderr)
            time.sleep(2 ** i)
    raise SystemExit(f'FAILED after {retries} retries')


def list_slides(deck_name):
    src = SOURCE_DIR / f'{deck_name}.md'
    if not src.exists():
        print(f'ERROR: {src} not found', file=sys.stderr)
        sys.exit(1)
    _, slides = parse_deck(src)
    out = OUT_DIR / deck_name / 'pages'
    print(f'Deck: {deck_name}  |  Source: {src}')
    print(f'{"Slide":>6}  {"File":<22}  {"Status"}')
    print('-' * 45)
    for s in slides:
        page = out / f'page_{s["num"]:03d}.html'
        exists = '✓' if page.exists() else '✗ MISSING'
        print(f'{s["num"]:>6}  {page.name:<22}  {exists}')
    present = sum(1 for s in slides if (out / f'page_{s["num"]:03d}.html').exists())
    print(f'\nTotal: {len(slides)} slides, {present} present')


def render(deck_name, slide_num=None, slide_range=None, force=False):
    src = SOURCE_DIR / f'{deck_name}.md'
    if not src.exists():
        print(f'ERROR: {src} not found', file=sys.stderr)
        sys.exit(1)

    header, slides = parse_deck(src)
    out = OUT_DIR / deck_name / 'pages'
    out.mkdir(parents=True, exist_ok=True)

    # Determine which slides to render
    targets = set()
    force_reason = ''
    if slide_num is not None:
        targets = {slide_num}
        force_reason = f'force single slide {slide_num}'
        print(f'[force] Render slide {slide_num}')
    elif slide_range is not None:
        m = re.match(r'(\d+)-(\d+)', slide_range)
        if not m:
            print(f'ERROR: --range must be N-M, got {slide_range}', file=sys.stderr)
            sys.exit(1)
        lo, hi = int(m.group(1)), int(m.group(2))
        targets = set(range(lo, hi + 1))
        force_reason = f'force range {lo}-{hi}'
        print(f'[force] Render slides {lo}-{hi}')
    else:
        # Delta mode: render any slide whose embedded hash != expected hash.
        # Legacy HTML (no hash comment) is treated as "needs render" by needs_render().
        # Migration of legacy hashes is a one-time operation — see migrate_slides_hash.py.
        for s in slides:
            page = out / f'page_{s["num"]:03d}.html'
            expected_hash = slide_source_hash(header, s)
            if needs_render(page, expected_hash):
                targets.add(s["num"])
        if not targets:
            print(f'Deck {deck_name}: all {len(slides)} slides match their source hashes. Nothing to do.')
            return
        print(f'[delta] Rendering {len(targets)} slide(s) with changed/missing hash: {sorted(targets)}')
        force_reason = f'delta hash mismatch ({len(targets)} slide(s))'

    n_total = len(slides)
    rendered_count = 0
    skipped_count = 0
    for slide in slides:
        n = slide["num"]
        page_path = out / f'page_{n:03d}.html'
        expected_hash = slide_source_hash(header, slide)
        if n not in targets:
            skipped_count += 1
            continue
        print(f'  [{n:3d}/{n_total:3d}] generating slide {n} (hash={expected_hash})...', end=' ', flush=True)
        html = generate_slide(header, slide)
        # Embed the source hash as a comment right after the <html ...> tag
        # so future delta runs can detect whether the source has changed.
        if '<html' in html.lower():
            html = re.sub(
                r'(<html[^>]*>)',
                r'\1<!-- source_hash: ' + expected_hash + ' -->',
                html,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            # Fallback: prepend comment if <html> tag not found (shouldn't happen)
            html = f'<!-- source_hash: {expected_hash} -->\n{html}'
        page_path.write_text(html)
        rendered_count += 1
        print(f'OK ({len(html)} chars)')
        time.sleep(0.5)

    print(f'\nDone. Rendered {rendered_count}, skipped {skipped_count} for deck {deck_name} ({force_reason or "no reason set"}).')


def main():
    deck = None
    slide = None
    slide_range = None
    list_only = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--deck' and i + 1 < len(sys.argv):
            deck = sys.argv[i + 1]; i += 2
        elif arg == '--slide' and i + 1 < len(sys.argv):
            slide = int(sys.argv[i + 1]); i += 2
        elif arg == '--range' and i + 1 < len(sys.argv):
            slide_range = sys.argv[i + 1]; i += 2
        elif arg == '--list':
            list_only = True; i += 1
        elif arg in ('-h', '--help'):
            print(__doc__); return
        else:
            print(f'Unknown arg: {arg}', file=sys.stderr); sys.exit(1)

    if not deck:
        print('ERROR: --deck {deck-id} is required', file=sys.stderr)
        print(__doc__); sys.exit(1)

    if list_only:
        list_slides(deck)
    else:
        render(deck, slide_num=slide, slide_range=slide_range)


if __name__ == '__main__':
    main()