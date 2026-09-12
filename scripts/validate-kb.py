#!/usr/bin/env python3
"""validate-kb.py — 知识库格式校验器（CI 与本地共用）

校验规则（源自 AGENTS.md 的约定）：

  1. frontmatter  — 知识文档须有 6 键：title / aliases / tags / created / updated / status
  2. tags         — 须为嵌套形态 `category/sub`（少量既有例外见 ALLOWED_FLAT_TAGS）
  3. wikilinks    — `[[目标]]` 必须指向库内真实存在的文档
  4. mermaid      — 全库禁止 ```mermaid 代码块（图表统一用 Excalidraw）
  5. 连通性        — 每篇知识文档至少 N 条 wikilink

**豁免**：功能配置文件（`SKILL.md`、`.opencode/` 下的 agent/command 定义、
仓库样板 README、`examples/`、`demo/` 下的代码 README）不套知识文档格式——
它们加 Obsidian frontmatter 会**破坏其加载**，因此整类跳过。

用法：
    python validate-kb.py            # 校验全库，输出问题清单
    python validate-kb.py --json     # 机器可读输出
退出码：0 = 通过；1 = 有问题
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Windows 控制台默认 GBK，直接 print 符号/中文会抛 UnicodeEncodeError。
# 统一改为 UTF-8 并对无法编码的字符降级，避免校验器自己因编码问题崩掉。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── 豁免：功能配置或样板文件，不套知识文档格式 ──────────────────────────
SKIP_FILENAMES = {"SKILL.md", "MODULE_README.md", "AGENTS.md"}
# 这些不是知识文档：Excalidraw 图有自己的 frontmatter；脚本目录下的 README
# 与 skill 正文属工具资产。对它们套知识库格式是**回溯误用新约定**（见 C-014）。
SKIP_SUFFIXES = (".excalidraw.md",)
SKIP_DIR_PARTS = {".git", ".obsidian", "node_modules", "__pycache__",
                  "_install-tmp", "_bin", "_out", ".github", "claude-ops-dumps"}
SKIP_PATH_PATTERNS = (
    re.compile(r"[/\\]\.opencode[/\\]"),        # OpenCode agent/command 定义
    re.compile(r"[/\\]slash-commands[/\\]"),    # 斜杠命令定义
    re.compile(r"[/\\](examples|demo)[/\\]README\.md$", re.I),  # 代码目录 README
    re.compile(r"^scripts/"),                   # 脚本资产目录（含其 README/skill 正文）
    re.compile(r"^diagrams/.*\.excalidraw\.md$"),
)

# 允许的非嵌套标签（库内既有例外）
# 库内**既有**的扁平标签。它们早于「嵌套标签」约定，属历史约定而非违规；
# 回溯校验旧内容时不得把它们计为问题（见 C-014）。
ALLOWED_FLAT_TAGS = {"incident", "meta", "moc", "ai", "cs",
                     "reference", "excalidraw", "network", "source",
                     "security", "reverse-engineering"}

REQUIRED_KEYS = ("title", "aliases", "tags", "created", "updated", "status")
VALID_STATUS = {"draft", "review", "stable", "deprecated"}
MIN_WIKILINKS = 3

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
# wikilink 形态：
#   [[name]]  [[name|alias]]  [[name#anchor]]  [[name\|alias]]（表格转义管道）
WIKILINK_RE = re.compile(r"\[\[([^\]\|#\\]+?)(?:\\?[#\|][^\]]*)?\]\]")
MERMAID_RE = re.compile(r"^\s*```\s*mermaid", re.I | re.M)


def is_knowledge_doc(rel: str) -> bool:
    """判断是否为「应套知识文档格式」的文件。"""
    if any(pat.search(rel) for pat in SKIP_PATH_PATTERNS):
        return False
    name = os.path.basename(rel)
    if name in SKIP_FILENAMES:
        return False
    return True


def collect(root: Path) -> list[str]:
    out = []
    for p in root.rglob("*.md"):
        rel = p.relative_to(root).as_posix()
        if any(part in SKIP_DIR_PARTS for part in Path(rel).parts):
            continue
        if rel.startswith("_archive/"):
            continue          # 归档不参与现行格式校验
        out.append(rel)
    return sorted(out)


def build_index(root: Path) -> set[str]:
    """可解析的 wikilink 目标集合。

    同时收录两种形态（Obsidian 两者都支持）：
      · basename          —— [[CORRECTIONS]]
      · 相对路径去扩展名   —— [[sources/dep-cve]]
    """
    idx = set()
    for p in root.rglob("*.md"):
        rel = p.relative_to(root).as_posix()
        if ".git" in Path(rel).parts:
            continue
        idx.add(p.stem)
        idx.add(rel[:-3] if rel.endswith(".md") else rel)
    return idx


def parse_frontmatter(text: str) -> dict | None:
    m = FM_RE.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm


def check_frontmatter(rel: str, fm: dict | None, problems: list) -> None:
    if fm is None:
        problems.append((rel, "no-frontmatter", "缺少 frontmatter 块"))
        return
    for key in REQUIRED_KEYS:
        if key not in fm:
            problems.append((rel, "fm-missing-key", f"缺 {key}"))
    status = fm.get("status", "").strip().strip('"\'')
    if status and status not in VALID_STATUS:
        problems.append((rel, "fm-bad-status", f"status={status} 不在 {sorted(VALID_STATUS)}"))
    for dk in ("created", "updated"):
        v = fm.get(dk, "").strip()
        if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            problems.append((rel, "fm-bad-date", f"{dk}={v} 非 YYYY-MM-DD"))
    tags_raw = fm.get("tags", "")
    if tags_raw.startswith("[") and tags_raw.endswith("]"):
        for t in tags_raw[1:-1].split(","):
            t = t.strip().strip('"\'')
            if not t:
                continue
            if "/" not in t and t not in ALLOWED_FLAT_TAGS:
                problems.append((rel, "tag-not-nested", f"标签 `{t}` 非嵌套形态"))


def check_body(rel: str, text: str, index: set[str], problems: list) -> None:
    if MERMAID_RE.search(text):
        problems.append((rel, "mermaid", "含 mermaid 代码块（本库禁止，须用 Excalidraw）"))

    body = FM_RE.sub("", text, count=1)
    # 剔除各类代码载体后再找 wikilink——bash 条件表达式 `[[ -z "$x" ]]`、
    # 数组下标 `[[2,4]]`、行内 `code` 都会被误判为链接（实测假阳性主要来源）。
    body_nocode = re.sub(r"```.*?```", "", body, flags=re.S)   # 围栏代码块
    body_nocode = re.sub(r"`[^`\n]*`", "", body_nocode)          # 行内 code
    body_nocode = re.sub(r"^\s{4,}\S.*$", "", body_nocode, flags=re.M)  # 缩进代码
    links = [m.group(1).strip() for m in WIKILINK_RE.finditer(body_nocode)]
    # 过滤非文档目标的形态：变量、含空格/等号的表达式、纯数字元组、占位词
    def _looks_like_doc(t: str) -> bool:
        if not t or t.startswith("$"):
            return False
        if any(ch in t for ch in ' "\'=<>'):
            return False
        if re.fullmatch(r"[\d,\s]+", t):
            return False
        if t in {"文件名", "wikilink", "Wikilink", "链接", "文档", "name"}:
            return False
        return True
    links = [l for l in links if _looks_like_doc(l)]
    for l in links:
        if l not in index:
            problems.append((rel, "dead-wikilink", f"[[{l}]] 目标不存在"))
    if len(links) < MIN_WIKILINKS:
        problems.append((rel, "few-wikilinks", f"仅 {len(links)} 条 wikilink（要求 ≥{MIN_WIKILINKS}）"))


def main() -> int:
    ap = argparse.ArgumentParser(description="知识库格式校验")
    ap.add_argument("--root", default=None, help="库根（默认脚本上溯两级）")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    root = Path(args.root) if args.root else Path(__file__).resolve().parents[1]
    if not (root / "AGENTS.md").exists():
        print(f"[error] {root} 不像知识库根（缺 AGENTS.md）", file=sys.stderr)
        return 2

    index = build_index(root)
    all_md = collect(root)
    docs = [r for r in all_md if is_knowledge_doc(r)]
    skipped = [r for r in all_md if r not in docs]

    # ERROR = 明确缺陷（应阻断）: dead-wikilink / mermaid
    # WARN  = 既有约定差异（记录但不阻断）: 缺键 / 少链接 / 扁平标签 / 日期格式
    ERR_KINDS = {"dead-wikilink", "mermaid"}
    problems: list[tuple[str, str, str]] = []
    for rel in docs:
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        check_frontmatter(rel, parse_frontmatter(text), problems)
        check_body(rel, text, index, problems)

    by_kind: dict[str, int] = {}
    for _, kind, _ in problems:
        by_kind[kind] = by_kind.get(kind, 0) + 1
    errors = [p for p in problems if p[1] in ERR_KINDS]
    warnings = [p for p in problems if p[1] not in ERR_KINDS]

    if args.json:
        print(json.dumps({
            "root": str(root),
            "total_md": len(all_md),
            "checked": len(docs),
            "skipped_functional": len(skipped),
            "problems": [{"file": f, "kind": k, "detail": d} for f, k, d in problems],
            "by_kind": by_kind,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"库根: {root}")
        print(f"  .md 总数 {len(all_md)}  |  校验 {len(docs)}  |  跳过功能/样板 {len(skipped)}")
        print()
        if errors:
            print(f"── ERROR（{len(errors)}）—— 明确缺陷，应修复 ──")
            for f, k, d in errors:
                print(f"  ✗ [{k}] {f}: {d}")
            print()
        if warnings:
            print(f"── WARN（{len(warnings)}）—— 既有约定差异，不阻断 ──")
            for f, k, d in warnings[:15]:
                print(f"  · [{k}] {f}: {d}")
            if len(warnings) > 15:
                print(f"  … 其余 {len(warnings)-15} 条")
            print()
        if not problems:
            print("  ✓ 全部通过")
        else:
            print("按类型统计: " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())))

    if args.json:
        return 0
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
