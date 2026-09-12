#!/usr/bin/env python3
"""check-links.py — 外链可用性巡检（CI 与本地共用）

设计取舍（见 CORRECTIONS C-014：门禁的价值等于其信噪比）：
  · **不阻断**：外链会限流、临时宕机、地域不可达。把「外链 404」当失败会让门禁
    长期飘红而被忽略。本脚本只产报告，退出码恒为 0。
  · **绝不因单条 URL 崩掉**：任何异常都收敛为一条「探测失败」记录。

踩过的坑（本脚本已规避）：
  1. URL 中的**方括号占位符**（`http://[IP已脱敏`）会被 `urllib` 当作 IPv6 字面量，
     在 **构造 Request 时**就抛 `ValueError: Invalid IPv6 URL` —— 而异常发生在
     try 块之外，会让整个线程池迭代崩掉。故此处先做**词法白名单**再构造请求。
  2. `concurrent.futures` 的 `map` 在迭代时会把 worker 异常抛出；必须让 worker
     自身永不抛异常（catch-all + return_exceptions）。

用法：
    python scripts/check-links.py                 # 巡检，写 linkcheck-report.md
    python scripts/check-links.py --limit 50      # 只查前 50 条（快速自检）
    python scripts/check-links.py --timeout 20
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import pathlib
import re
import ssl
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXCLUDE_DIRS = {".git", ".obsidian", "node_modules", "_install-tmp", "_bin", "_out"}
URL_RE = re.compile(r'https?://[^\s)\]<>"\'\u3000]+')
# 合法 URL 的词法白名单：只允许 ASCII 可见字符，且显式排除方括号
SAFE_URL_RE = re.compile(r'^https?://[A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+$')
HOST_RE = re.compile(r'^https?://([^/?#]+)')
SKIP_SUBSTRINGS = ("github.com/L-ingqin12", "localhost", "127.0.0.1", "0.0.0.0")

# 文档占位符 / 内网示例域名——**不是可行动的死链**，报告里必须与真死链分开。
# 这些都是文档写作中刻意保留的模板（如 CVE-XXXX-YYYY）或示意地址
# （grafana.internal.example.com、opencode.yourcompany.com、192.168.x.x）。
# 不加过滤会让报告被噪声淹没，真死链反而被忽略（CORRECTIONS C-014）。
PLACEHOLDER_HOST_RE = re.compile(
    r'(^|\.)('
    r'internal|local|localhost|example\.com|example\.org|yourcompany\.com|'
    r'company\.com|your-domain\.com|yourdomain\.com|test\.com|invalid'
    r')$'
)
PLACEHOLDER_PATH_RE = re.compile(
    r'(XXXX|YYYY|your-|YOUR_|your_|<[^>]+>|\$[A-Z_]+\{|\{[^}]*\}|'
    r'/user/repo|/team/|TODO|placeholder)'
)
PRIVATE_IP_RE = re.compile(
    r'^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.)'
)

UA = "kb-linkcheck/1.0 (+https://github.com/L-ingqin12/agent-knowledge-base)"


def extract(root: pathlib.Path) -> dict[str, str]:
    """返回 {url: 首个出现它的文件}。"""
    urls: dict[str, str] = {}
    for p in root.rglob("*.md"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in URL_RE.finditer(text):
            u = m.group(0).rstrip(".,;:!。，；：")
            urls.setdefault(u, str(p))
    return urls


def is_plausible(u: str) -> bool:
    """词法过滤：不可探测的 URL 直接排除，不进线程池。

    这一步是必需的——`urllib` 对 `[` 开头的 host 会抛 ValueError，
    且异常发生在构造阶段（try 之外）。
    """
    if not SAFE_URL_RE.match(u):
        return False
    m = HOST_RE.match(u)
    if not m:
        return False
    host = m.group(1).split(":")[0]
    if "[" in host or "]" in host:          # IPv6 字面量或占位符，跳过
        return False
    if not re.fullmatch(r"[A-Za-z0-9.\-]+", host):
        return False
    if "." not in host:                     # 必须有 TLD
        return False
    if PRIVATE_IP_RE.match(host):           # 内网地址，文档示意
        return False
    if PLACEHOLDER_HOST_RE.search(host):    # internal/local/example 等示意域名
        return False
    if PLACEHOLDER_PATH_RE.search(u):       # 路径含 XXXX/$VAR/{...} 等模板片段
        return False
    return True


def _try(u: str, method: str, timeout: int):
    req = urllib.request.Request(u, method=method, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.status


def probe(u: str, timeout: int) -> tuple[str, int | str]:
    """单条探测，**保证不抛异常**。

    先 HEAD，失败（含 4xx/5xx）再 GET —— 有些站点不支持 HEAD 却正常服务 GET
    （实测 news.qiniu.com、ntfy.sh 属此类，只查 HEAD 会误报为死链）。
    """
    try:
        return u, _try(u, "HEAD", timeout)
    except urllib.error.HTTPError as e:
        first = e.code
    except Exception as e:
        first = type(e).__name__
    try:
        return u, _try(u, "GET", timeout)
    except urllib.error.HTTPError as e:
        return u, e.code if e.code != 404 or first == 404 else first
    except Exception:
        # GET 也失败：报第一次的结果（更可能是真实原因，如 DNS 失败）
        return u, first


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="linkcheck-report.md")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    all_urls = extract(root)
    targets = [(u, f) for u, f in all_urls.items()
               if not any(s in u for s in SKIP_SUBSTRINGS)]
    plausible = [(u, f) for u, f in targets if is_plausible(u)]
    skipped_lexical = [(u, f) for u, f in targets if not is_plausible(u)]
    if args.limit:
        plausible = plausible[:args.limit]

    print(f"提取 URL {len(all_urls)} 条；待查 {len(targets)} 条；"
          f"词法过滤掉 {len(skipped_lexical)} 条（含占位符/非 ASCII host）")

    results: list[tuple[str, str, object]] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(probe, u, args.timeout): (u, f) for u, f in plausible}
        for fut in cf.as_completed(futs):
            u, f = futs[fut]
            try:
                _, st = fut.result()
            except Exception as e:          # 双保险
                st = type(e).__name__
            results.append((u, f, st))

    bad = [(u, f, s) for u, f, s in results if s != 200]
    print(f"探测完成 {len(results)} 条；非 200 共 {len(bad)} 条")

    lines = ["# 外链巡检报告", "",
             f"- 文档中提取 URL：{len(all_urls)} 条",
             f"- 实际探测：{len(results)} 条",
             f"- 词法过滤（占位符/非法 host）：{len(skipped_lexical)} 条",
             f"- **非 200 响应：{len(bad)} 条**", ""]
    if skipped_lexical:
        lines += ["## 词法过滤（不可探测，通常为文档占位符）", ""]
        lines += [f"- `{u}` ← {f}" for u, f in sorted(skipped_lexical)[:50]]
        lines += [""]
    if bad:
        lines += ["## 非 200 响应", ""]
        lines += [f"- `{s}` {u} ← {f}" for u, f, s in sorted(bad, key=lambda x: str(x[2]))]
    else:
        lines += ["## 结论", "", "全部探通。"]

    pathlib.Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"报告已写入 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
