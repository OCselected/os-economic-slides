# 开源的经济学 · 12 讲 — Slide 展示

**The Economics of Open Source — Institutional Economics of Open Source Software**

「开源之道」·适兕 主讲的《开源的经济学》12 讲 Slide 展示站点。

- **站点**：https://os-economic.opensourceway.blog/
- **课程大纲**：[12-lectures-of-open-source](https://opensourceway.blog/posts/open-source-economic/12-lectures-of-open-source/)
- **数据源**：[markdown-to-slides](https://github.com/OCselected/markdown-to-slides)

## 架构

| 层 | 说明 |
|---|------|
| 框架 | Hugo 0.164 纯静态，无主题依赖 |
| 样式 | dark academic — 深普鲁士蓝 `#1B3B6B` + 暖白 `#F5F0E8` + Bauhaus 几何 |
| 部署 | GitHub Pages → CNAME `os-economic.opensourceway.blog` |

## 内容

12 个 markdown 文件（`content/lectures/00.md` — `11.md`），每个包含 20-52 张 slide，共 368 张。

- Slide 以 `<details>` 折叠卡片展示
- 每张卡片含：编号 + 视觉隐喻提示 + 展开后的要点列表
- 支持关键词搜索过滤

## 数据流

```
markdown-to-slides/open-source-economics-lecture/
  └── 27 个 markdown 文件（NotebookLM 分页格式）
       │
       ▼  scripts/merge_slides.py
       │
content/lectures/{00..11}.md
       │
       ▼  hugo build
       │
public/  →  GitHub Pages
```

## 本地开发

```bash
hugo server --baseURL http://localhost:1313/
```

## 维护

- **新增 slide**：更新 `markdown-to-slides/open-source-economics-lecture/` 中的源文件，
  然后在仓库内运行 `python3 scripts/merge_slides.py`，重新 `hugo build`，提交 `content/lectures/` 变更。
- **不改** `markdown-to-slides/` 原始文件。
- **域名**：GitHub Pages 部署后，在 DNS 添加 CNAME `os-economic.opensourceway.blog` → `ocselected.github.io`。

## License

CC BY-NC-ND 4.0 · 开源之道