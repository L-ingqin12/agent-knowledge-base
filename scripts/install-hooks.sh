#!/usr/bin/env bash
# install-hooks.sh — 安装本地 git 钩子
#
# 安装后 `git push` 会自动先跑敏感内容自扫描；命中则**阻断推送**。
# 这是 C-013 的机器约束在「本地」的落点（CI 是第二道）。
#
# 钩子文件放在 .git/hooks/ 下（不进版本控制），本脚本负责生成它，
# 使「钩子内容」可被版本化与审阅。
#
# 用法：
#   bash scripts/install-hooks.sh          # 安装 / 更新
#   bash scripts/install-hooks.sh --remove # 卸载
#
# 绕过（仅限明确知情）：git push --no-verify

set -euo pipefail

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "✗ 不在 git 仓库内" >&2; exit 2; }
HOOK="$REPO/.git/hooks/pre-push"

if [ "${1:-}" = "--remove" ]; then
  rm -f "$HOOK"
  echo "✓ 已卸载 pre-push 钩子"
  exit 0
fi

mkdir -p "$REPO/.git/hooks"
cat > "$HOOK" <<'HOOKBODY'
#!/usr/bin/env bash
# 由 scripts/install-hooks.sh 生成——请勿直接编辑（改脚本后重跑安装）
#
# 推送前敏感内容自扫描。命中即阻断，避免把凭据推到公开仓库。
# 绕过：git push --no-verify（仅限明确知情的情况）
set -uo pipefail

REPO=$(git rev-parse --show-toplevel)
cd "$REPO"

if [ ! -f scripts/prepush-selfscan.sh ]; then
  echo "[pre-push] 未找到 scripts/prepush-selfscan.sh，跳过扫描" >&2
  exit 0
fi

echo "[pre-push] 敏感内容自扫描…"
if ! bash scripts/prepush-selfscan.sh --self-test; then
  cat >&2 <<'MSG'

✗ 推送被阻断：敏感内容自扫描未通过。
  修复后重试；确属误报请给该行加 `scan-ignore` 注释。
  明确知情要绕过：git push --no-verify
MSG
  exit 1
fi

# 格式校验：仅对已跟踪的 .md 做快速校验，避免拖慢推送
if [ -f scripts/validate-kb.py ]; then
  # 【解释器解析不能只看 PATH】Windows 上 `python` / `python3` 常被
  # Microsoft Store 的占位存根抢先命中（WindowsApps 下），它不执行任何脚本、
  # 实测返回 exit 49 —— 会让校验静默失败。因此按「显式可用」优先：
  #   1. $KB_PYTHON 环境变量（显式指定）
  #   2. 已知可用的 conda 解释器路径
  #   3. PATH 上的 python3 / python，且**必须通过可执行性探测**
  PY=""
  for cand in "${KB_PYTHON:-}" \
              "/d/ProgramData/miniconda3/python.exe" \
              "python3" "python"; do
    [ -z "$cand" ] && continue
    if [ -x "$cand" ] || command -v "$cand" >/dev/null 2>&1; then
      # 探测：Store 存根跑 --version 会返回非 0
      if "$cand" -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then PY="$cand"; break; fi
    fi
  done
  if [ -z "$PY" ]; then
    echo "[pre-push] 未找到可用 Python，跳过格式校验（可设 KB_PYTHON 指定）" >&2
  else
    echo "[pre-push] 知识库格式校验…（$PY）"
    if ! "$PY" scripts/validate-kb.py >/tmp/kb-validate.log 2>&1; then
      echo "✗ 格式校验未通过（详见 /tmp/kb-validate.log）：" >&2
      grep -E '✗' /tmp/kb-validate.log | head -10 >&2 || true
      echo "  修复后重试；明确知情要绕过：git push --no-verify" >&2
      exit 1
    fi
  fi
fi

echo "[pre-push] ✓ 通过"
exit 0
HOOKBODY

chmod +x "$HOOK"
echo "✓ 已安装 pre-push 钩子: $HOOK"
echo "  作用：push 前跑 scripts/prepush-selfscan.sh（敏感内容）+ scripts/validate-kb.py（格式）"
echo "  绕过：git push --no-verify"
