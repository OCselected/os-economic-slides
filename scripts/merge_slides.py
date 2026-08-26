#!/usr/bin/env python3
"""Merge 27 lecture files into 12 Hugo content pages.

Output format: each lecture page has ALL slides as frontmatter YAML list,
rendered by layout template (avoids Goldmark HTML rendering issues).
"""
import re, os, textwrap

SRC = os.path.join(os.path.dirname(__file__), '..', '..',
                   'markdown-to-slides', 'open-source-economics-lecture')
OUT = os.path.join(os.path.dirname(__file__), '..', 'content', 'lectures')
os.makedirs(OUT, exist_ok=True)

LECTURES = [
    ("00", "开源与经济学", "开源在数字社会中的概况 / 开源的历史发展 / 开源的经济效果", [
        "economic-of-open-source-lecture-0.md",
        "economic-of-open-source-lecture-0-part-2.md",
        "economic-of-open-source-lecture-0-part-3.md",
        "economic-of-open-source-lecture-0-part-4.md",
    ]),
    ("01", "软件的生产、分销和消费", "软件市场演变 / 闭源与开源 / 大教堂与集市 / 交付方式 / 订阅", [
        "economic-of-open-source-lecture-1-software-business.md",
        "economic-of-open-source-lecture-1-software-business-part-2.md",
    ]),
    ("02", "数字时代的知识财产法与开源许可", "许可与软件市场 / 知识财产权扩张 / 开源许可面临的挑战", [
        "economic-of-open-source-lecture-2-IP.md",
        "economic-of-open-source-lecture-2-IP-part-2.md",
    ]),
    ("03", "商业模式：规则下的具体操作", "软件商品化 / RedHat / WordPress / Android / Kubernetes", [
        "economic-of-open-source-lecture-3-business-model.md",
        "economic-of-open-source-lecture-3-business-model-part-2.md",
    ]),
    ("04", "软件开发劳动力市场", "代码不是商品 / 供需关系 / 开发者动机 / 兴趣与实践", [
        "economic-of-open-source-lecture-4-hr-market.md",
        "economic-of-open-source-lecture-4-hr-market-part-2.md",
    ]),
    ("05", "交易成本与路径依赖", "毋需法律的秩序 / 科斯贡献 / 路径依赖 / 开源吞噬软件", [
        "economic-of-open-source-lecture-5-transaction-cost.md",
        "economic-of-open-source-lecture-5-transaction-cost-part-2.md",
    ]),
    ("06", "组织结构与治理", "组织结构与治理 / 社区协作 / 决策机制 / 贡献者生态", [
        "economic-of-open-source-lecture-6-organization-and-governe.md",
        "economic-of-open-source-lecture-6-organization-and-governe-part-2.md",
        "economic-of-open-source-lecture-6-organization-and-governe-part-3.md",
    ]),
    ("07", "商业价值与社会价值：开源的政治经济学", "商业价值 / 社会价值 / Commons-based Peer Production / Platform Cooperativism", [
        "economic-of-open-source-lecture-7-politic-economic.md",
        "economic-of-open-source-lecture-7-politic-economic-part-2.md",
    ]),
    ("08", "信息规则与网络经济", "信息规则 / 网络经济 / 边际成本与规模 / 平台化", [
        "economic-of-open-source-lecture-8-information-economy.md",
        "economic-of-open-source-lecture-8-information-economy-part-2.md",
    ]),
    ("09", "排他权与容他权、比例原则与 copyleft", "排他权 / 容他权 / 比例原则 / copyleft", [
        "economic-of-open-source-lecture-9-proprietary-rights.md",
        "economic-of-open-source-lecture-9-proprietary-rights-part-2.md",
    ]),
    ("10", "劳动报酬与财产分配", "劳动报酬 / 财产分配 / 知识资本 / 激励与贡献", [
        "economic-of-open-source-lecture-10-labor-compensation.md",
        "economic-of-open-source-lecture-10-labor-compensation-part-2.md",
    ]),
    ("11", "文化的重要作用", "开源精神 / 协作伦理 / 文化的经济价值 / 知识社会", [
        "economic-of-open-source-lecture-11-culture-matters.md",
        "economic-of-open-source-lecture-11-culture-matters-part-2.md",
    ]),
]

def escape_yaml(s):
    """Escape a string for YAML flow scalar."""
    return s.replace('"', '\\"').replace('\n', ' ')

for num, title, topics, files in LECTURES:
    all_slides = []
    for fn in files:
        path = os.path.join(SRC, fn)
        if not os.path.exists(path):
            print(f"  WARNING: {fn} not found, skip")
            continue
        with open(path, encoding='utf-8') as f:
            text = f.read()
        chunks = re.split(r'^## Slide (\d+)', text, flags=re.MULTILINE)
        for i in range(1, len(chunks), 2):
            slide_num = int(chunks[i])
            slide_body = chunks[i+1]
            vm_m = re.search(r'\* 视觉隐喻：\s*\n\s*\* (.+)', slide_body)
            visual = vm_m.group(1).strip() if vm_m else ""
            bullets = re.findall(r'^[-*] (.+)$', slide_body, re.MULTILINE)
            bullets = [b for b in bullets if '视觉隐喻' not in b]
            all_slides.append((slide_num, visual, bullets))

    slide_count = len(all_slides)
    slug = f"{num}-{title}"

    # Build YAML frontmatter with slides as a list
    fm = f"""---
title: "第 {num} 期 · {title}"
lecture_number: {int(num)}
topics: "{topics}"
slide_count: {slide_count}
draft: false
editable: true
---
"""
    for slide_num, visual, bullets in all_slides:
        fm += f"## Slide {slide_num}\n"
        if visual:
            fm += f"* 视觉隐喻：{visual}\n"
        for b in bullets:
            fm += f"* {b}\n"
        fm += "\n"

    out_path = os.path.join(OUT, f'{num}.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(fm)
    print(f"  {num}: {slide_count} slides → {out_path}")

print("\nDone.")