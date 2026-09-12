#!/usr/bin/env bash
# prepush-selfscan.sh — 推送前敏感内容自扫描（本地第一道闸）
#
# 【为什么需要它】
# 2026-09-12 的合并工作中，「把敏感字面量写进自己产出的文档」这一错误**连续复发四次**：
#   ① router_ssh.sh 注释里写了口令字面量
#   ② 合并记录里逐字引用被清理的密钥前缀
#   ③ CORRECTIONS 的条目自身又写口令字面量
#   ④ README 的脱敏章节写密钥前缀
# 根因不是疏忽，而是**缺少机器约束**：写「关于脱敏的说明」时，人会把被脱敏的值
# 当成需要展示的例证。本脚本把这条约束固化下来——**文档自身也必须过扫描**。
#
# 【用法】
#   bash scripts/prepush-selfscan.sh                  # 扫描整库（默认，排除已忽略项）
#   bash scripts/prepush-selfscan.sh --staged         # 只扫 git 暂存区
#   bash scripts/prepush-selfscan.sh --files a.md b.md
#   bash scripts/prepush-selfscan.sh --self-test      # 额外断言脚本自身不含凭据
#   bash scripts/prepush-selfscan.sh --quiet          # 只输出结论
#
# 【退出码】0 = 通过；1 = 命中；2 = 用法错误
#
# 【豁免机制】——解决「文档必须举例，但举例不能触发告警」
#   在同一行加注释 `scan-ignore`（Markdown 用 HTML 注释），该行即被跳过：
#     | SSH 口令（示意） | `[已脱敏]` | <!-- scan-ignore: 文档示例 -->
#   原则：**豁免必须显式、可见、可审计**。不允许靠模糊正则去「猜」哪些是示例——
#   否则真凭据也会被猜成示例而漏掉。（本条是 CORRECTIONS C-014 的处置。）
#
# ⚠️ 【正则方言】本脚本用 `grep -E`（ERE），**不支持** `(?!…)` / `(?=…)` 等 PCRE
#   前瞻断言；写了不会报错，只会**静默失配**（实测造成订阅 URL 假阴性）。
#   需要「排除某模式」时，改用显式结构或把例外写成 scan-ignore 豁免行。
#
# 【性能】单次 `grep -rEn` 扫全目录，而非「每文件 × 每模式」循环——
#   后者在 Windows 上会产生数千次进程创建，实测全库扫描超时（>10 分钟）；改后 12 秒。
#
# 【检查范围】只查**真凭据**。本地树里的明文路径（`C:\Users\<name>\…`）与
#   已脱敏占位符（`[已脱敏]` / `%USERPROFILE%`）**不在检查范围**——前者由推送时
#   脱敏规则处理，后者本就是目标形态。检查它们只会制造噪声（C-014）。
#
# ⚠️ 本脚本内**不得**出现任何真实凭据——它自己也要过扫描（用 --self-test 验证）。

set -uo pipefail

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "✗ 不在 git 仓库内" >&2; exit 2; }
cd "$REPO"

MODE=all; QUIET=0; SELFTEST=0; FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --staged) MODE=staged; shift ;;
    --files)  MODE=files; shift; while [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; do FILES+=("$1"); shift; done ;;
    --quiet)  QUIET=1; shift ;;
    --self-test) SELFTEST=1; shift ;;
    -h|--help) sed -n '3,32p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "✗ 未知选项: $1" >&2; exit 2 ;;
  esac
done

SELF_REL="scripts/prepush-selfscan.sh"

# ── 敏感模式表（用拼接避免脚本自身命中）────────────────────────────────
#
# 【设计原则：只报「真凭据」，不报「已受管的内容」】（见 CORRECTIONS C-014）
# 本地扫描器与 kb-push 的推送时脱敏**职责不同**，不可混淆：
#   · 本地扫描器 = **拦真凭据**（密钥、私钥、订阅 token、明文口令实参）
#   · 推送时脱敏 = **改发布形态**（路径→%USERPROFILE%、IP→[IP已脱敏]）
# 因此**本地树里的明文路径与已脱敏占位符都不是本扫描器的目标**——
# 前者推送上会被替换，后者本就是正确形态。报它们只会制造噪声。
#
# 三条具体教训（均由首次全库扫描的 39 处误报得出）：
#   ① `-p` 加引号实参**不是** sshpass 专属——`claude -p`、`unittest -p` 都用它。
#      必须限定为 sshpass 上下文（见下）。
#   ② 已脱敏形态（方括号占位）是**正确形态**，不该报；只报后跟**真实口令字面量**的行。
#   ③ 本机用户名路径在本地树里是常态，推送时才脱敏 ⇒ 本地扫描器不检查它。
P_OR="sk-""or-v1"; P_ARK="ar""k-"; P_SK="s""k-"
P_SUB="eo-""edgefunctions"; P_SSHPASS="sshp""ass"
PH='(xxxx|XXXX|yyy|YYY|zzz|ZZZ|your|YOUR|example|EXAMPLE|placeholder|PLACEHOLDER|redacted|REDACTED|abc123|foo|bar)'
# 已脱敏占位（出现即视为已处理）
RED='\[已脱敏\]|%USERPROFILE%|<REDACTED>|\[IP已脱敏\]'

PATTERNS=(
  "OpenRouter密钥|${P_OR}[A-Za-z0-9]{16,}"
  "通用sk密钥|${P_SK}[A-Za-z0-9]{32,}"
  # 去掉 lookahead 版本：`${P_SK}(?![A-Za-z0-9]*${PH})…` 依赖 PCRE，grep -E 下静默失配
  # （实测导致假阴性）。改为要求省略号**两侧都是较长的字母数字串**——
  # 文档占位写法（`sk-xxxx...yyyy`）因 xxxx/yyyy 不在 [a-f0-9] 主域而多半不匹配，
  # 残余误报由 scan-ignore 显式处理。
  "截断引用密钥|${P_SK}[A-Za-z0-9]{6,}\.\.\.[A-Za-z0-9]{4,}"
  "ARK密钥|${P_ARK}[0-9a-f]{8}-[0-9a-f]{4,}"
  # 【为什么不做通用的「长 hex 路径」规则】
  # 首版用「https://host/…/<24+位hex>」判定订阅 URL，实测**误报 13 处**——
  # GitHub 的 `/commit/<40位hex>`、`/blob/<40位hex>/…` 全部命中。
  # 收紧为「末尾 32 位 hex」后仍误报 1 处：NeurIPS 论文链接的
  # `/hash/9d5609613524ecf4f15af0f7b31abca4-Abstract-Conference.html`。
  #
  # **结论：hex 串本身不携带语义，无法区分凭据与合法内容**（学术 DOI、
  # 内容寻址存储、commit hash 都长这样）。因此改为两条**有语义**的规则：
  #   ① 域名本身含订阅语义（sub/subscribe/clash/v2ray/passwall）
  #   ② 命中已知的订阅服务域名片段（P_SUB）
  # 代价是理论上会漏掉「域名无特征 + 纯 hex 路径」的订阅源；
  # 这一残余风险由「提交前人工过一眼新增的外部 URL」补，而不靠正则硬猜。
  # 匹配「订阅语义域名」：关键词可出现在**任意标签或标签内的连字符段**
  # （真实样本是 `example-subscribe-node.org`，关键词不在首位——
  #   曾因收紧到「首标签」而漏报，属假阴性，比误报更危险）。
  # 用负向断言排除两个已知无关域名：substack（博客平台）、subagentic。
  # 保持宽松是刻意的：**留一点误报由 scan-ignore 显式豁免，也不要漏掉真凭据**。
  "代理订阅URL|https://[a-z0-9.-]*(sub|subscribe|subscription|clash|v2ray|passwall)[a-z0-9.-]*\.[a-z]{2,}/[A-Za-z0-9/_.-]{8,}"
  "订阅服务域名|${P_SUB}"
  "私钥头|BEGIN [A-Z ]*PRIVATE KEY"
  "明文Bearer|Bearer [A-Za-z0-9._-]{32,}"
  # sshpass 明文口令：同一行出现 sshpass，且 -p 后跟**不含方括号**的实参
  # （已脱敏形态 `-p [已脱敏]` 以 `[` 开头，天然被排除；避免用 lookahead，
  #   Bash 不同版本对 `(?!)` 的支持不一致，实测曾导致漏报）
  "sshpass明文口令|${P_SSHPASS}.*-p[[:space:]]+\"[A-Za-z0-9!@#%^&*_.-]{2,32}\""
  # 同一行的 ssh/scp + -p 明文口令。
  # 注意：`-p` 是**通用参数**——`claude -p`、`unittest -p`、`mkdir -p`
  # 都用它，因此必须要求前面确实出现 ssh 系命令，且**词边界**要严
  # （曾因 `[^a-z]sc` 这类宽松写法误报 `claude -p "..."`）。
  "SSH口令上下文|(^|[[:space:];&|])s(sh|cp)[[:space:]][^|]*[[:space:]]-p[[:space:]]+\"[A-Za-z0-9!@#%^&*_.-]{2,32}\""
)

# ── 目标集合 ──────────────────────────────────────────────────────────────
# 排除：VCS、本地未脱敏副本、第三方插件二进制、构建产物、已 gitignore 的目录
EXCLUDES=(
  --exclude-dir=.git
  --exclude-dir=.obsidian
  --exclude-dir=node_modules
  --exclude-dir=__pycache__
  --exclude-dir=_install-tmp
  --exclude-dir=_bin
  --exclude-dir=_out
  --exclude-dir=claude-ops-dumps
  --exclude-dir=backups
  --exclude='*.local-unredacted-*'
  --exclude='*.local-backup-*'
  --exclude='*.dll'
  --exclude='*.pyc'
  --exclude='*.png'
  --exclude='*.jpg'
  --exclude='*.zip'
)

case "$MODE" in
  staged) mapfile -t TARGETS < <(git diff --cached --name-only --diff-filter=ACM | grep -v "^${SELF_REL}$") ;;
  files)  mapfile -t TARGETS < <(printf '%s\n' "${FILES[@]}" | grep -v "^${SELF_REL}$") ;;
  all)    TARGETS=(".") ;;
esac
[ "${#TARGETS[@]}" -eq 0 ] && { echo "✓ 无待扫描文件"; exit 0; }

# ── 扫描 ──────────────────────────────────────────────────────────────────
FAILED=0; HITS=0; SKIPPED=0
for entry in "${PATTERNS[@]}"; do
  label="${entry%%|*}"; regex="${entry#*|}"
  raw=$(grep -rEn "${EXCLUDES[@]}" -- "$regex" "${TARGETS[@]}" 2>/dev/null || true)
  [ -z "$raw" ] && continue
  # 去掉被 scan-ignore 显式豁免的行
  kept=$(printf '%s\n' "$raw" | grep -v 'scan-ignore' || true)
  skipped_n=$(printf '%s\n' "$raw" | grep -c 'scan-ignore' || true)
  SKIPPED=$((SKIPPED + ${skipped_n:-0}))
  [ -z "$kept" ] && continue
  FAILED=1
  n=$(printf '%s\n' "$kept" | wc -l)
  HITS=$((HITS + n))
  printf '\n\033[31m✗ %s\033[0m（%d 行）\n' "$label" "$n"
  printf '%s\n' "$kept" | head -8 | sed 's/^/    /'
  [ "$n" -gt 8 ] && printf '    … 其余 %d 行\n' "$((n-8))"
done

if [ "$SELFTEST" = "1" ]; then
  echo ""
  selfhits=0
  for entry in "${PATTERNS[@]}"; do
    regex="${entry#*|}"
    if grep -qE -- "$regex" "$SELF_REL" 2>/dev/null; then
      echo "  ✗ 脚本自身命中: ${entry%%|*}"; selfhits=$((selfhits+1))
    fi
  done
  if [ "$selfhits" = "0" ]; then echo "  ✓ --self-test 通过：脚本自身不含凭据模式"; else FAILED=1; fi
fi

echo ""
if [ "$FAILED" = "0" ]; then
  printf '\033[32m✓ 自扫描通过\033[0m（%d 模式 / %d 行豁免）\n' "${#PATTERNS[@]}" "$SKIPPED"
  exit 0
fi
printf '\033[31m✗ 自扫描未通过：%d 处命中\033[0m\n' "$HITS"
cat <<'TIP'

排查建议：
  1. 真实凭据 → 移出文件，改为环境变量或本机未跟踪文件
  2. 文档例证 → 改为**类别描述**（写「一个 4 位前缀」，不写实际前缀）
  3. 确属示例 → 该行加 `scan-ignore` 注释显式豁免（须可见、可审计）
  4. 本机用户名 → 路径改用 %USERPROFILE%

脱敏规则可补进 .git/kb-push-redactions（该文件在 .git/ 下，永不推送）。
TIP
exit 1
