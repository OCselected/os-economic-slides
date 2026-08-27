#!/usr/bin/env python3
"""Sanitize LLM slide CSS: px → rem/clamp, preserving indentation."""
import re, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/..'
os.chdir(ROOT)


def sanitize_line(line):
    """Apply px→rem/clamp transformations to one CSS line, preserving all other content."""
    result = line

    # font-size: NNpx → clamp
    if 'font-size' in line and 'px' in line:
        result = re.sub(
            r'(font-size\s*:\s*)(\d{2,3})\s*px',
            lambda m: f"{m.group(1)}clamp({max(0.5, int(m.group(2))//16)}rem, "
                      f"{int(m.group(2))*0.016}vw, {max(0.5, int(m.group(2))//10)}rem)",
            result
        )

    # padding: NNpx NNpx NNpx NNpx; (full line match, keeps leading whitespace)
    result = re.sub(
        r'^(\s*padding\s*:\s*)(\d{2,3})px(\s+\d{2,3}px)?(\s+\d{2,3}px)?(\s+\d{2,3}px)?\s*;',
        _padding_margin_4_repl,
        result
    )
    # padding-top/right/bottom/left: NNpx;
    result = re.sub(
        r'^(\s*padding-(?:top|right|bottom|left)\s*:\s*)(\d{2,3})px\s*;',
        _padding_margin_1_repl,
        result
    )

    # margin: NNpx (skip 'auto')
    if 'margin' in result and 'auto' not in result:
        result = re.sub(
            r'^(\s*margin\s*:\s*)(\d{2,3})px(\s+\d{2,3}px)?(\s+\d{2,3}px)?(\s+\d{2,3}px)?\s*;',
            _padding_margin_4_repl,
            result
        )
        result = re.sub(
            r'^(\s*margin-(?:top|right|bottom|left)\s*:\s*)(\d{2,3})px\s*;',
            _padding_margin_1_repl,
            result
        )

    # gap: NNpx;
    result = re.sub(
        r'^(\s*gap\s*:\s*)(\d{2,3})px\s*;',
        _gap_repl,
        result
    )

    return result


def _rem(v):
    return f'{max(1, int(v)//10)}rem'


def _padding_margin_4_repl(m):
    parts = [m.group(2)]
    for i in [3, 4, 5]:
        g = m.group(i)
        if g:
            parts.append(re.search(r'\d+', g).group())
    return f"{m.group(1)}{' '.join(_rem(p) for p in parts)};"


def _padding_margin_1_repl(m):
    val = int(m.group(2))
    if val < 10:
        return m.group(0)  # keep original
    return f"{m.group(1)}{_rem(val)};"


def _gap_repl(m):
    val = int(m.group(2))
    if val < 10:
        return m.group(0)
    return f"{m.group(1)}{_rem(val)};"


def sanitize_style(style):
    return '\n'.join(sanitize_line(l) for l in style.split('\n'))


def process_lecture(ln):
    path = f'content/lectures/{ln:02d}.md'
    with open(path) as f:
        content = f.read()

    def repl(m):
        return f'<style>\n{sanitize_style(m.group(1))}\n      </style>'

    new = re.sub(r'<style>(.*?)</style>', repl, content, flags=re.DOTALL)
    changed = new != content
    n_styles = new.count('<style>')
    return path, new, changed, n_styles


def main():
    changed_total = 0
    for ln in range(12):
        path, content, changed, n_styles = process_lecture(ln)
        if changed:
            with open(path, 'w') as f:
                f.write(content)
            changed_total += 1
        print(f"L{ln:02d}: {n_styles} <style> blocks, {'MODIFIED' if changed else 'unchanged'}")

    print(f"\nTotal lectures modified: {changed_total}/12")


if __name__ == '__main__':
    main()