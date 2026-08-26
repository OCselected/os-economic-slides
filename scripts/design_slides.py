#!/usr/bin/env python3
"""
Design slide HTML via LLM for a single lecture.
Reads frontmatter slides[] → calls LLM per slide → writes HTML fragment.
Output: <deck_dir>/slides_{N}.html (replaces content in single.html range)

Usage: python3 design_slides.py --lecture 02 --output-dir <dir>
"""
import argparse, json, os, sys, time

sys.path.insert(0, '/home/lee/.hermes/skills/sn-ppt-standard/lib')
from model_client import llm

DECK_BASE = os.path.expanduser('~/developing/os-economic-slides')

SYSTEM = """你是一个专业的学术幻灯片 HTML 设计师。你的任务是将 markdown slide 内容转化为精致的 HTML + CSS，用于网页幻灯片播放器。

设计原则：
1. **暗色学术风**：深普鲁士蓝 #1B3B6B 为底，古铜色 #D4A853 为强调，暖白 #F5F0E8 为主文
2. **极简学术**：衬线字体 Source Serif 4，大量留白，不堆砌装饰
3. **视觉隐喻落地**：每张 slide 的"视觉隐喻"字段描述了讲师意图，将其翻译为实际的 CSS 视觉效果（几何图形、色彩渐变、字体排印、装饰线等），而非字面插画
4. **类型自适应**：根据内容类型自动适配不同版式
   - 封面/标题页：大标题居中，副标题下方，几何装饰
   - 议程页：编号列表，左侧竖线，紧凑网格
   - 引用页：大字斜体，引号符号，署名右对齐
   - 时间线/历史：垂直或水平时间线，节点+标签
   - 对比/光谱：左右对照，中间分隔
   - 列表/要点：简洁bullet，图标或编号
   - 代码/技术：等宽字体，深色背景块
   - 结语/总结：居中，大字，古铜色下划线

CSS 约束：
- 只使用 CSS 变量：--prussian:#1B3B6B; --cream:#F5F0E8; --copper:#8B7355; --amber:#D4A853; --muted:#555555
- 字体：'Source Serif 4','Noto Serif SC',Georgia,serif
- 不要用外链资源（无外部图片、无网络字体）
- 不使用 SVG（除简单几何装饰可用 CSS box-shadow / border 实现）

HTML 结构要求：
- 根元素：<div class="slide-page designed"> ... </div>
- 在内部添加 <style> 标签，样式仅作用于该 slide
- 内容使用语义化 HTML：h1/h2/h3/p/ul/ol/li/span/strong/em/quote/cite
- 不要用 table

输出要求：
- 只输出 <div class="slide-page designed"> 到 </div>，不要包含其他内容
- 不要输出 markdown 代码块标记（```）
- 所有 CSS 变量必须带 var() 前缀，如 color: var(--amber)

每张 slide 都是独立的完整 HTML 片段。"""

def build_user_prompt(slide, total_slides):
    return json.dumps({
        "slide_num": slide["num"],
        "total_slides": total_slides,
        "visual_metaphor": slide.get("visual", ""),
        "bullets": slide.get("bullets", []),
    }, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lecture", required=True, help="Lecture number e.g. 02")
    ap.add_argument("--output-dir", required=True, help="Where to write per-slide HTML files")
    ap.add_argument("--start", type=int, default=1, help="Start slide (1-based)")
    ap.add_argument("--end", type=int, default=999, help="End slide (1-based)")
    ap.add_argument("--dry-run", action="store_true", help="Print prompt for slide 1 only")
    args = ap.parse_args()

    lecture_file = f"{DECK_BASE}/content/lectures/{args.lecture}.md"
    if not os.path.exists(lecture_file):
        print(f"File not found: {lecture_file}", file=sys.stderr)
        return 1

    import yaml, re
    with open(lecture_file) as f:
        text = f.read()
    fm_match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    fm = yaml.safe_load(fm_match.group(1))
    slides = fm["slides"]
    total = len(slides)

    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)

    # Filter by range
    idx_start = max(0, args.start - 1)
    idx_end = min(total, args.end)

    # Dry run: print prompt for slide 1
    if args.dry_run:
        print("=== System prompt (truncated) ===")
        print(SYSTEM[:500])
        print()
        print("=== User prompt for slide 1 ===")
        print(build_user_prompt(slides[0], total))
        return 0

    results = []
    for i in range(idx_start, idx_end):
        s = slides[i]
        user_prompt = build_user_prompt(s, total)

        # Save draft first
        out_file = os.path.join(out_dir, f"slide_{s['num']:03d}.html")
        if os.path.exists(out_file) and not args.force:
            print(f"  [skip] slide {s['num']} already exists", file=sys.stderr)
            continue

        try:
            html = llm(SYSTEM, user_prompt, timeout=120)
            # Strip markdown code fences if present
            html = re.sub(r'^```html\s*', '', html, flags=re.MULTILINE)
            html = re.sub(r'\s*```$', '', html, flags=re.MULTILINE)
            html = html.strip()

            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(html)
            results.append({"slide": s["num"], "status": "ok", "chars": len(html)})
            print(f"  [ok] slide {s['num']} ({len(html)} chars)", file=sys.stderr)
        except Exception as e:
            results.append({"slide": s["num"], "status": "error", "error": str(e)})
            print(f"  [error] slide {s['num']}: {e}", file=sys.stderr)

    print(json.dumps({
        "lecture": args.lecture,
        "total": total,
        "processed": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "errors": [r for r in results if r["status"] == "error"],
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())