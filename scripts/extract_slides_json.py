#!/usr/bin/env python3
"""
Pre-process content/lectures/*.md:
- Parse ## Slide N + * bullets
- Embed as frontmatter JSON field `slides`
- Remove slide body content (JS renders from JSON)
"""
import os, re, json

LECTURES_DIR = os.path.join(os.path.dirname(__file__), '..', 'content', 'lectures')

for f in sorted(os.listdir(LECTURES_DIR)):
    if not f.endswith('.md'):
        continue
    path = os.path.join(LECTURES_DIR, f)
    with open(path) as fh:
        text = fh.read()

    # Extract frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not fm_match:
        print(f"  {f}: no frontmatter, skip")
        continue

    fm = fm_match.group(1)
    rest = text[fm_match.end():]

    # Parse slides from body
    chunks = re.split(r'^## Slide (\d+)', rest, flags=re.MULTILINE)
    slides = []
    for i in range(1, len(chunks), 2):
        slide_num = int(chunks[i])
        body = chunks[i+1].strip()
        bullets = re.findall(r'^\* (.+)$', body, re.MULTILINE)
        visual = ""
        content_bullets = []
        for b in bullets:
            if '视觉隐喻' in b[:4]:
                visual = b.split('：', 1)[-1] if '：' in b else b
            else:
                content_bullets.append(b)
        slides.append({
            "num": slide_num,
            "visual": visual,
            "bullets": content_bullets,
        })

    # Rebuild frontmatter with slides YAML list (NOT block scalar!)
    fm += '\nslides:\n'
    for s in slides:
        fm += f'  - num: {s["num"]}\n'
        fm += f'    visual: "{s["visual"].replace(chr(34), chr(92)+chr(34))}"\n'
        fm += f'    bullets:\n'
        for b in s["bullets"]:
            safe_b = b.replace(chr(34), chr(92)+chr(34))
            fm += f'      - "{safe_b}"\n'

    fm += f'\ntotal_slides: {len(slides)}\n'

    new_text = f'---\n{fm}\n---\n'
    with open(path, 'w') as fh:
        fh.write(new_text)

    print(f"  {f}: {len(slides)} slides → frontmatter JSON")

print("\nDone")