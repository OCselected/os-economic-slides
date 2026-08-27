#!/usr/bin/env python3
"""
Generate standalone 1600x900 HTML slides from source deck markdown.

Pipeline:
  content/slides_decks/{deck}.md
      -> parse header + ## Slide N blocks
      -> LLM generates full HTML with inline <style>
      -> slides_decks/{deck}/pages/page_NNN.html

Output format matches osbook architecture:
  - each page is an independent HTML document
  - fixed 1600x900 viewport
  - inline <style>, no external CSS
  - iframe-scale friendly (no responsive px hacks)

Usage:
  python3 scripts/generate_deck_slides.py 00-introduction
  python3 scripts/generate_deck_slides.py --all
"""
import os, re, sys, time, json
from pathlib import Path

# model_client needs its own lib dir on sys.path (no __init__.py at skill root)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / '.hermes' / 'skills' / 'sn-ppt-standard' / 'lib'))
from model_client import llm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DECKS_DIR = ROOT / 'content' / 'slides_decks'
OUT_DIR = ROOT / 'slides_decks'  # git-tracked (history/diff); deploy copies to public/


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
    # Extract header (everything before first ## Slide)
    header_m = re.match(r'^(.*?)(?=\n## Slide \d+)', text, re.DOTALL)
    header = header_m.group(1).strip() if header_m else ''

    slides = []
    for m in re.finditer(r'## Slide (\d+)\s*(.*?)(?=\n## Slide \d+|\Z)', text, re.DOTALL):
        slides.append({
            'num': int(m.group(1)),
            'content': m.group(2).strip(),
        })
    return header, slides


def generate_slide(header, slide, retries=3):
    prompt = f"""Context (deck-wide style and theme):
{header}

Generate the HTML for this slide:
{slide['content']}
"""
    last_err = None
    for i in range(retries):
        try:
            raw = llm(SYSTEM, prompt, timeout=300,
                       model='sensenova-6.8-flash-lite')
            # Strip any markdown code fences
            raw = re.sub(r'^```html\s*', '', raw, flags=re.IGNORECASE | re.MULTILINE)
            raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
            if '<!DOCTYPE html>' not in raw and '<html' not in raw.lower():
                raise ValueError('output missing HTML doctype/html tag')
            # Validate inline <style> exists
            if '<style>' not in raw:
                raise ValueError('output missing inline <style>')
            return raw
        except Exception as e:
            last_err = e
            print(f'  retry {i+1}/{retries}: {e}', file=sys.stderr)
            time.sleep(2 ** i)
    raise last_err


def main(deck_name):
    deck_path = DECKS_DIR / f'{deck_name}.md'
    if not deck_path.exists():
        print(f'ERROR: {deck_path} not found', file=sys.stderr)
        sys.exit(1)

    header, slides = parse_deck(deck_path)
    out = OUT_DIR / deck_name / 'pages'
    out.mkdir(parents=True, exist_ok=True)

    print(f'Deck {deck_name}: {len(slides)} slides, output -> {out}')

    # Load any existing state
    state_path = out / '.state.json'
    done = set()
    if state_path.exists():
        st = json.loads(state_path.read_text())
        done = set(st.get('done', []))

    failed = []
    for slide in slides:
        n = slide['num']
        page_path = out / f'page_{n:03d}.html'
        if n in done:
            continue
        print(f'  [{n:3d}/{len(slides):3d}] generating slide {n}...', end=' ', flush=True)
        try:
            html = generate_slide(header, slide)
            page_path.write_text(html)
            done.add(n)
            state_path.write_text(json.dumps({'done': sorted(done)}))
            print(f'OK ({len(html)} chars)')
            time.sleep(0.5)
        except Exception as e:
            print(f'FAILED: {e}')
            failed.append(n)

    print(f'\nDone. {len(done)} generated, {len(failed)} failed: {failed}')


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == '--all':
        decks = sorted(DECKS_DIR.glob('*.md'))
        for d in decks:
            main(d.stem)
    else:
        main(sys.argv[1])