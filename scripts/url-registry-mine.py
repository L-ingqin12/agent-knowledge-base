#!/usr/bin/env python3
"""url-registry-mine — 从 vault 现有 markdown 中挖掘 URL，生成候选登记条目。

用途
    知识库内已积累数百个来源 URL，人工逐条登记不现实。本脚本扫描全库，
    提取去重后的 URL，推断主题分类，输出「带内联字段的条目草稿」，
    供人工确认后并入 sources/ 主题笔记（供 [[URL-Lookup]] 的 Dataview 检索）。

    URL-Lookup / URL-REGISTRY 的条目协议：
        - 来源:: <名称>
          use_when:: <何时用>
          url:: <链接>
          answers:: <能回答什么>
          authority:: 高|中|低
          verified:: YYYY-MM-DD

设计原则
    1. 只产出**草稿**，不自动改写 sources/ —— 主题与语义需人工判断。
    2. 分类是启发式的：命中关键词即归类，未命中进 unclassified，绝不臆造。
    3. 默认排除自身产出（URL-REGISTRY.md / URL-Lookup.md / sources/），
       避免把登记册自己的链接当成新来源，形成自反馈。

用法
    python url-registry-mine.py                      # 扫描并输出报告到 stdout
    python url-registry-mine.py --out-dir _out      # 分文件写出草稿
    python url-registry-mine.py --limit 0            # 不限量
    python url-registry-mine.py --vault D:\\path\\to\\vault

环境
    Python 3.13（本库约定解释器路径见本机笔记，不入库）
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# ── 主题分类（启发式，可扩展） ───────────────────────────────────────────
# 顺序即优先级：先匹配到的主题胜出。
TOPICS: list[tuple[str, str, tuple[str, ...]]] = [
    ("dep-cve", "依赖与 CVE", (
        "cve-", "ghsa", "/advisory", "security-tracker", "osv.dev", "vulndb",
        "npmjs.com/package", "registry.npmjs", "pypi.org/project", "snyk.io/vuln",
        "mend.io/vulnerability", "dependabot", "debian.org/security",
        "ubuntu.com/security", "alpinelinux.org/vuln", "cvedetails", "vuldb.com",
    )),
    ("dsh-routing", "DSH 与模型路由", (
        "openrouter.ai", "api-docs.deepseek", "platform.openai", "anthropic.com",
        "docs.anthropic", "dsh-tui", "@deepseek-ai", "cordis", "tiktoken",
        "modelcontextprotocol.io", "openai.com/api",
    )),
    ("proxy-relay", "代理与中继", (
        "xray", "v2ray", "clash", "nginx", "mitmproxy", "squid", "relay",
        "127.0.0.1:8790", "127.0.0.1:8899", "127.0.0.1:10808",
    )),
    ("network-device", "网络与设备", (
        "miwifi", "192.168.31", "192.168.", "router", "wifi", "dhcp",
        "ipv6", "openwrt",
    )),
    ("security-audit", "安全审计", (
        "owasp.org", "cwe.mitre", "icacls", "key-rotation", "hardening",
        "attack.mitre", "nvd.nist",
    )),
    ("learning-notes", "学习与调研", (
        "arxiv.org", "medium.com", "zhihu.com", "juejin.cn", "csdn.net",
        "cnblogs.com", "github.io", "wikipedia.org", "bilibili.com",
        "/blog/", "/docs/", "/tutorial", "/course", "/guide",
    )),
]

URL_RE = re.compile(r"https?://[^\s)\]<>\"'，。；、）】]+")
# 主机必须含点号（或为带端口的回环），否则视为截断产生的伪 URL
HOST_RE = re.compile(r"^https?://([^/?#]+)", re.I)
# 排除自身产出，避免自反馈
SKIP_NAME_PARTS = ("URL-REGISTRY", "URL-Lookup")
SKIP_DIR_PARTS = {".git", "__pycache__", "node_modules", "_install-tmp", "_bin"}
# 默认跳过历史归档，避免把过期信息当现行来源；用 --include-archive 打开
ARCHIVE_DIR_PARTS = {"_archive"}

TODAY = date.today().isoformat()


def valid_url(url: str) -> bool:
    """过滤截断/占位产生的伪 URL（如 https://L-ingqin12、裸 http://127.0.0.1）。"""
    m = HOST_RE.match(url)
    if not m:
        return False
    authority = m.group(1)
    host = authority.split(":")[0]
    if host == "localhost":
        return True
    if host in ("127.0.0.1", "0.0.0.0", "[::1]"):
        return ":" in authority          # 裸回环无意义，须带端口
    return "." in host


def classify(url: str, context: str) -> str:
    """返回主题 id；无命中则返回 unclassified（不臆造分类）。"""
    hay = f"{url} {context}".lower()
    for topic_id, _label, keys in TOPICS:
        if any(k in hay for k in keys):
            return topic_id
    return "unclassified"


def authority_of(url: str) -> str:
    """粗略权威度：官方/原始来源=高；知名聚合=中；其余=低（待人工复核）。"""
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    official = (
        "github.com", "npmjs.com", "pypi.org", "registry.npmjs.org",
        "security-tracker.debian.org", "ubuntu.com", "security.alpinelinux.org",
        "osv.dev", "cve.org", "nvd.nist.gov", "api-docs.deepseek.com",
        "openrouter.ai", "docs.anthropic.com", "obsidian.md", "nodejs.org",
        "python.org", "microsoft.com", "kernel.org", "gnu.org",
    )
    aggregator = ("vuldb.com", "mend.io", "snyk.io", "deps.dev", "cvedetails.com",
                  "opencve.io", "devguard.org", "circl.lu", "wiz.io")
    if any(host == o or host.endswith("." + o) for o in official):
        return "高"
    if any(host == a or host.endswith("." + a) for a in aggregator):
        return "中"
    return "低"


def iter_markdown(vault: Path, include_archive: bool = False):
    for p in vault.rglob("*.md"):
        if any(part in SKIP_DIR_PARTS for part in p.parts):
            continue
        if not include_archive and any(part in ARCHIVE_DIR_PARTS for part in p.parts):
            continue
        if any(s in p.name for s in SKIP_NAME_PARTS):
            continue
        yield p


def mine(vault: Path, include_archive: bool = False) -> dict[str, list[dict]]:
    """返回 {topic_id: [entry, ...]}，entry 含 url/来源/上下文。"""
    seen: dict[str, dict] = {}
    skipped: list[str] = []
    for path in iter_markdown(vault, include_archive):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"[warn] read failed {path}: {exc}", file=sys.stderr)
            continue
        for line in text.splitlines():
            for url in URL_RE.findall(line):
                url = url.rstrip(".,;:!")
                if url in seen:
                    continue
                if not valid_url(url):
                    skipped.append(url)
                    continue
                seen[url] = {
                    "url": url,
                    "file": path.relative_to(vault).as_posix(),
                    "context": line.strip()[:160],
                }

    grouped: dict[str, list[dict]] = defaultdict(list)
    for url, meta in seen.items():
        topic = classify(url, meta["context"])
        meta["topic"] = topic
        meta["authority"] = authority_of(url)
        grouped[topic].append(meta)
    for items in grouped.values():
        items.sort(key=lambda m: (m["file"], m["url"]))
    grouped["__skipped__"] = [{"url": u} for u in skipped]  # 供报告统计伪 URL
    return grouped


def render(topic_id: str, label: str, items: list[dict], limit: int) -> str:
    shown = items if limit <= 0 else items[:limit]
    out = [
        f"### {label}（{len(items)} 条唯一 URL"
        + (f"，下列展示前 {len(shown)} 条" if len(shown) < len(items) else "")
        + "）",
        "",
        "```markdown",
    ]
    for m in shown:
        # 来源名暂用域名，answers/use_when 留待人工填写——不臆造语义
        host = re.sub(r"^https?://", "", m["url"]).split("/")[0]
        out += [
            f"- 来源:: {host}",
            f"  use_when:: 【待填写】来自 {m['file']}",
            f"  url:: {m['url']}",
            "  answers:: 【待填写】",
            f"  authority:: {m['authority']}",
            f"  verified:: {TODAY}",
        ]
    out += ["```", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="从 vault 挖掘 URL 并生成登记草稿")
    ap.add_argument("--vault", default=None, help="vault 根目录（默认脚本所在目录）")
    ap.add_argument("--out-dir", default=None, help="写出草稿的目录；缺省只打印报告")
    ap.add_argument("--limit", type=int, default=40, help="每个主题最多输出条数，0=不限")
    ap.add_argument("--include-archive", action="store_true",
                    help="一并扫描 _archive/ 历史归档（默认跳过，避免过期信息当现行来源）")
    args = ap.parse_args()

    vault = Path(args.vault) if args.vault else Path(__file__).resolve().parents[1]
    if not (vault / ".obsidian").is_dir():
        print(f"[error] {vault} is not an Obsidian vault (missing .obsidian)", file=sys.stderr)
        return 2

    grouped = mine(vault, include_archive=args.include_archive)
    skipped = grouped.pop("__skipped__", [])
    total = sum(len(v) for v in grouped.values())
    unclassified = len(grouped.get("unclassified", []))

    label_of = {tid: lbl for tid, lbl, _ in TOPICS}
    label_of["unclassified"] = "未分类（需人工判断）"

    header = [
        f"# URL 挖掘草稿 — {TODAY}",
        "",
        f"- vault: `{vault}`",
        f"- 唯一 URL 总数: **{total}**",
        f"- 未分类: **{unclassified}**（占 {unclassified * 100 // max(total, 1)}%）",
        f"- 已滤除伪 URL/占位: **{len(skipped)}**（无 TLD 或裸回环，见 `valid_url()`）",
        f"- 历史归档 `_archive/`: {'已包含' if args.include_archive else '已跳过（--include-archive 可纳入）'}",
        "",
        "> 本文件由 `scripts/url-registry-mine.py` 生成，**仅供人工确认**。",
        "> `use_when` / `answers` 一律留空待填——脚本不臆造语义。",
        "> 确认后把条目并入 `sources/<主题>.md`，即可被 [[URL-Lookup]] 检索。",
        "> 分类是启发式的：`unclassified` 属正常结果，不应强行归类。",
        "",
        "---",
        "",
    ]

    order = [tid for tid, _, _ in TOPICS] + ["unclassified"]
    body = [render(tid, label_of[tid], grouped.get(tid, []), args.limit)
            for tid in order if grouped.get(tid)]
    report = "\n".join(header) + "\n".join(body)

    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = vault / out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "URL-MINE-DRAFT.md"
        dest.write_text(report, encoding="utf-8")
        print(f"wrote: {dest}")
    else:
        print(report)

    print(f"\n[summary] unique_urls={total} unclassified={unclassified} "
          f"filtered_placeholders={len(skipped)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
