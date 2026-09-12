#!/usr/bin/env bash
# kb-push.sh —— 知识库一键推送到 GitHub 远程线
#
# 【为什么不能直接 push】
# 本地主线 (D:\Document\local\knowledge) 与远程线 (agent-knowledge-base) 是两条
# **无共同祖先**的历史（本地 28 条 / 远程 55 条，内容各自独立，不是领先/落后关系）。
# 远程线是**脱敏后的发布线**，所以 `git push` 必然被拒，`git pull` 会报
# unrelated histories。正确做法是把本地改动搬到「基于远程线」的临时 worktree 里，
# 在那边脱敏、校验、提交，再推 HEAD:main。本脚本把这一整套流程封成一条命令。
#
# 【三道闸】—— 每一道都对应一次真实踩过的坑
#   ① 脱敏不回退：远程线上已存在的 [已脱敏] 占位，新版本不许变少。
#      （坑：远程 cache-relay.mjs 把 'Bearer ' 写成 '[已脱敏] '，直接覆盖会把
#        脱敏回退成公开 diff 里的「去脱敏」）
#   ② 敏感内容扫描：密钥 / 私钥 / 明文 token / 本机用户名，命中即拦。
#   ③ 空变更校验：算出来的文件集若为空或全部无实质变化，不产生空提交。
#
# 【用法】
#   kb-push.sh                       推送「上次推送以来」的所有本地变更
#   kb-push.sh a375de4..HEAD         推送指定区间
#   kb-push.sh --files a.md b.md     推送指定文件（相对仓库根的路径）
#
# 【选项】
#   -m "提交信息"   自定义提交信息（默认从区间内的本地提交摘录）
#   -y              跳过确认
#   --dry-run       只做检查：建 worktree、应用改动与脱敏、跑闸门，然后丢弃
#   --no-push       提交到 worktree 但不推送（用于先看一眼产物）
#   -h, --help      帮助
#
# 【脱敏规则存哪】
#   默认规则写在本脚本内（见 default_rules）。额外的规则可写在本机
#   .git/kb-push-redactions（每行 `路径glob|sed表达式`，以 # 开头为注释）——
#   放 .git/ 下是刻意的：它永远不会被推送，规则内容（含被脱敏的字面量）不公开。
#
# 依赖：git、sed、node（可选，用于 JSON 校验）。推送走 v2rayN 本地 SOCKS。

set -eo pipefail

REMOTE=origin
BRANCH=main
PROXY=socks5h://127.0.0.1:10808
SELF_REL=scripts/kb-push.sh          # 脚本自身路径：跳过脱敏规则，避免自我改写

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "✗ 当前不在 git 仓库里" >&2; exit 1; }
cd "$REPO"
RULES_FILE="$REPO/.git/kb-push-redactions"
LAST_FILE="$REPO/.git/kb-push.last"
LOCALUSER=$(basename "${HOME:-/}")   # 本机用户名，用于泄漏扫描（此处不写示例值，否则脚本自己会被闸②拦下）

# ── 参数解析 ──────────────────────────────────────────────────────────────
SPEC=""; FILES_MODE=0; FILES=(); MSG=""; YES=0; DRY=0; NOPUSH=0
while [ $# -gt 0 ]; do
  case "$1" in
    -m) MSG="$2"; shift 2 ;;
    -y) YES=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --no-push) NOPUSH=1; shift ;;
    --files) FILES_MODE=1; shift; while [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; do FILES+=("$1"); shift; done ;;
    -h|--help) sed -n '3,45p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "✗ 未知选项: $1" >&2; exit 1 ;;
    *) SPEC="$1"; shift ;;
  esac
done

say()    { printf '%s\n' "$*"; }                              # 原样输出，不解释转义（路径里可能有 \）
step()   { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
banner() { printf '\n\033[%sm%s\033[0m\n' "$1" "$2"; }        # banner <色码> <文本>
die()    { printf '\n\033[31m✗ %b\033[0m\n' "$*" >&2; exit 1; }  # %b：消息内可用 \n

# ── 1. 确定要推送的文件集 ────────────────────────────────────────────────
step "确定变更集"
if [ "$FILES_MODE" = 1 ]; then
  [ ${#FILES[@]} -gt 0 ] || die "--files 后面要跟至少一个路径"
  [ -n "$MSG" ] || MSG=$(git log -1 --format='%B' HEAD)
  CHANGES=$(for f in "${FILES[@]}"; do
    [ -e "$f" ] && echo "M	$f" || echo "D	$f"
  done)
  say "  显式指定 ${#FILES[@]} 个文件"
else
  if [ -z "$SPEC" ]; then
    [ -f "$LAST_FILE" ] || die "首次使用请给一个区间（之后会自动记住上次推到哪），例如：\n    kb-push.sh a375de4..HEAD"
    SPEC="$(cat "$LAST_FILE")..HEAD"
    say "  沿用上次推送点: $SPEC"
  fi
  git rev-parse --verify -q "${SPEC%%..*}" >/dev/null || die "区间起点不存在: ${SPEC%%..*}"
  CHANGES=$(git -c core.quotePath=false diff --name-status --no-renames "$SPEC")
  [ -n "$CHANGES" ] || die "$SPEC 区间内没有文件变更"
  N=$(printf '%s\n' "$CHANGES" | wc -l)
  if [ -z "$MSG" ]; then
    NC=$(git rev-list --count "$SPEC")
    if [ "$NC" = 1 ]; then
      # 单提交：整段正文照搬，别把辛苦写的 commit body 丢了
      MSG=$(git -c core.quotePath=false log -1 --format='%B' "$SPEC")
    else
      TITLE=$(git -c core.quotePath=false log --format='%s' --reverse "$SPEC" | head -1)
      TITLE="$TITLE；等 $NC 个本地提交"
      LIST=$(git -c core.quotePath=false log --format='%h %s' --reverse "$SPEC" | sed 's/^/- /')
      MSG="$TITLE

本地提交：
$LIST"
    fi
  fi
  say "  区间 $SPEC → $N 个文件"
fi

mapfile -t PUSH_PATHS < <(printf '%s\n' "$CHANGES" | cut -f2 | sed '/^$/d')
[ ${#PUSH_PATHS[@]} -gt 0 ] || die "文件集为空"
printf '    %s\n' "${PUSH_PATHS[@]}" | head -20
[ ${#PUSH_PATHS[@]} -gt 20 ] && say "    … 其余 $(( ${#PUSH_PATHS[@]} - 20 )) 个"

# ── 2. 拉取远程线（走代理） ──────────────────────────────────────────────
step "拉取 $REMOTE/$BRANCH"
git -c http.proxy="$PROXY" -c https.proxy="$PROXY" fetch "$REMOTE" "$BRANCH" -q \
  || die "fetch 失败——检查 v2rayN 的 SOCKS 是否在 10808 上监听"
say "  远程线 HEAD: $(git rev-parse --short "$REMOTE/$BRANCH")"

# ── 3. 建 worktree 并铺变更 ──────────────────────────────────────────────
WT=$(mktemp -d "${TMPDIR:-/tmp}/kb-push-wt.XXXXXX")
cleanup() {
  if [ -d "$WT" ]; then
    git worktree remove --force "$WT" 2>/dev/null || { git worktree prune 2>/dev/null; rm -rf "$WT" 2>/dev/null || true; }
  fi
}
trap cleanup EXIT

step "建 worktree（基于远程线）"
git worktree add --detach -q "$WT" "$REMOTE/$BRANCH" || die "git worktree add 失败"
say "  $WT"

step "铺变更"
while IFS=$'\t' read -r st path; do
  [ -n "$path" ] || continue
  case "$st" in
    D)
      if [ -e "$WT/$path" ]; then git -C "$WT" rm -q -f -- "$path"; say "  删除 $path"; fi
      ;;
    A|M|T|C)
      [ -f "$path" ] || { say "  ⚠ 跳过（本地不存在）$path"; continue; }
      mkdir -p "$WT/$(dirname "$path")"
      command cp -f "$path" "$WT/$path"        # 本环境 cp 被 alias 成交互式，必须 command cp -f
      say "  $st      $path"
      ;;
    *) say "  ⚠ 未知状态 $st: $path" ;;
  esac
done < <(printf '%s\n' "$CHANGES")

# ── 4. 应用脱敏规则 ──────────────────────────────────────────────────────
default_rules() {
  # 路径glob|sed表达式      —— 这些字面量只存在本机 .git/ 与未推送的 worktree 副本里
  cat <<'RULES'
scripts/claude-ops-deployments/cache-relay/*.mjs|s/authorization: 'Bearer ' + /authorization: '[已脱敏] ' + /g
RULES
}

step "应用脱敏规则"
APPLIED=0
while IFS='|' read -r glob expr; do
  glob=$(printf '%s' "$glob" | sed 's/[[:space:]]*$//')
  [ -z "$glob" ] && continue
  case "$glob" in \#*) continue ;; esac
  for path in "${PUSH_PATHS[@]}"; do
    case "$path" in $glob) ;; *) continue ;; esac
    [ "$path" = "$SELF_REL" ] && continue          # 不给自己套规则，避免自我改写
    [ -f "$WT/$path" ] || continue
    before=$(cksum < "$WT/$path")
    sed -i "$expr" "$WT/$path"
    after=$(cksum < "$WT/$path")
    [ "$before" != "$after" ] && { say "  脱敏 $path"; APPLIED=$((APPLIED+1)); }
  done
done < <(default_rules; cat "$RULES_FILE" 2>/dev/null || true)
[ "$APPLIED" = 0 ] && say "  （无命中，本次不需脱敏）"

# ── 5. 闸门 ──────────────────────────────────────────────────────────────
FAILED=0

step "闸① 脱敏不回退（远程已有占位不许变少）"
for path in "${PUSH_PATHS[@]}"; do
  [ -f "$WT/$path" ] || continue
  rc=$(git show "$REMOTE/$BRANCH:$path" 2>/dev/null | grep -c '已脱敏' || true); rc=${rc:-0}
  [ "$rc" = 0 ] && continue
  nc=$(grep -c '已脱敏' "$WT/$path" 2>/dev/null || true); nc=${nc:-0}
  if [ "$nc" -lt "$rc" ]; then
    say "  ✗ $path：远程有 $rc 处 [已脱敏]，新版本只剩 $nc 处"
    say "    这是「去脱敏」——请把规则补进 $RULES_FILE 后重跑"
    FAILED=1
  else
    say "  ✓ $path（远程 $rc / 新版 $nc）"
  fi
done

step "闸② 敏感内容扫描"
# 字面量拆开拼接：否则本行自己就会被这些模式命中（脚本也要扫自己，不能跳过）
P_OR="sk-""or-v1"
P_TPL="s""k-"
PATTERNS="${P_OR}|${P_TPL}[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY|Bearer [A-Za-z0-9._-]{20,}|(password|passwd|secret)[[:space:]]*[:=][[:space:]]*[\"'][^\"']{8,}|${LOCALUSER}"
for path in "${PUSH_PATHS[@]}"; do
  [ -f "$WT/$path" ] || continue
  hits=$(grep -cE "$PATTERNS" "$WT/$path" 2>/dev/null || true); hits=${hits:-0}
  if [ "$hits" -gt 0 ]; then
    say "  ✗ $path：命中 $hits 行（不回显原文，请自行核查）"
    FAILED=1
  fi
done
[ "$FAILED" = 0 ] && say "  ✓ 全部干净（扫描面：密钥前缀/私钥/明文 bearer/口令赋值/本机用户名「$LOCALUSER」）"

step "闸③ 空变更校验"
git -C "$WT" add -A
if git -C "$WT" diff --cached --quiet; then
  die "工作区没有实质变化——无需推送"
fi
say "  ✓ 有实质变化"
git -C "$WT" diff --cached --stat | tail -3

[ "$FAILED" = 0 ] || die "闸门未通过，已中止（worktree 已丢弃，本地与远程均未改动）"

# ── 6. 提交 ──────────────────────────────────────────────────────────────
step "提交"
# (脱敏) 必须落在标题行——多行消息时追加到整条末尾会甩到正文底部，破坏 KB 既有约定
T=$(printf '%s\n' "$MSG" | head -1 | sed 's/[[:space:]]*$//')
case "$T" in *"(脱敏)"*) ;; *) T="$T (脱敏)" ;; esac
B=$(printf '%s\n' "$MSG" | tail -n +2)
if [ -n "$B" ]; then MSG="$T
$B"; else MSG="$T"; fi
MSGFILE=$(mktemp)
printf '%s\n' "$MSG" > "$MSGFILE"
git -C "$WT" commit -q -F "$MSGFILE" || die "commit 失败"
rm -f "$MSGFILE"
C=$(git -C "$WT" rev-parse --short HEAD)
say "  提交 $C"
say "  ── 提交信息 ──"
git -C "$WT" log -1 --format='%B' | sed 's/^/    /'

if [ "$DRY" = 1 ]; then
  banner 33 "--dry-run：到此为止，worktree 即将丢弃，未推送"
  exit 0
fi

if [ "$NOPUSH" = 1 ]; then
  banner 33 "--no-push：提交留在 $WT（进程退出时会一并丢弃）"
  exit 0
fi

# ── 7. 确认并推送 ────────────────────────────────────────────────────────
if [ "$YES" != 1 ] && [ -t 0 ]; then
  printf '\n推送到 %s/%s？[y/N] ' "$REMOTE" "$BRANCH"
  read -r ans
  case "$ans" in y|Y) ;; *) die "已取消" ;; esac
fi

step "推送（走 $PROXY）"
git -C "$WT" -c http.proxy="$PROXY" -c https.proxy="$PROXY" push "$REMOTE" HEAD:"$BRANCH" 2>&1 | tail -8
NEW=$(git rev-parse --short "$REMOTE/$BRANCH")
say "  远程线现为 $NEW"

# ── 8. 记住推送点 ────────────────────────────────────────────────────────
if [ "$FILES_MODE" != 1 ]; then
  git rev-parse HEAD > "$LAST_FILE"
  say "  已记住本地推送点 $(git rev-parse --short HEAD)（下次 kb-push.sh 无参即从这推）"
fi
banner 32 "✓ 完成"
