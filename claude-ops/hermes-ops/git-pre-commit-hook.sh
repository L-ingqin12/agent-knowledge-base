#!/bin/bash
# ======================================================================
# Git Pre-Commit Hook — detect-secrets + 自定义正则 (双重检测)
#
# 引擎 1: detect-secrets (Yelp) — 28 插件 + Base64/Hex 高熵
# 引擎 2: 自定义正则 — 覆盖国内服务商 (ARK/飞书)
#
# 部署: git config --global init.templateDir ~/.git-templates
# ======================================================================

RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
VIOLATIONS=0

# 获取待提交的非二进制文件
FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | \
    grep -vE '\.(lock|png|jpg|jpeg|gif|ico|pdf|zip|tar|gz|bz2|7z|min\.js|min\.css|map|woff|ttf|eot)$' 2>/dev/null)
[ -z "$FILES" ] && exit 0

# ── 引擎 1: detect-secrets (熵检测 + 28 内置插件) ──
if command -v detect-secrets-hook &>/dev/null; then
    result=$(detect-secrets-hook --json $FILES 2>/dev/null)
    if [ -n "$result" ]; then
        count=$(echo "$result" | python3 -c "
import json,sys
try:
    data = json.load(sys.stdin)
    total = sum(len(v) for v in data.get('results',{}).values())
    print(total)
except: print(0)
" 2>/dev/null)

        if [ "${count:-0}" -gt 0 ]; then
            echo ""
            echo -e "${RED}╔═══════════════════════════════════════════════╗${NC}"
            echo -e "${RED}║  ⛔ detect-secrets 高熵/模式检测 — 提交已阻止  ║${NC}"
            echo -e "${RED}╚═══════════════════════════════════════════════╝${NC}"
            echo ""
            echo "$result" | python3 -c "
import json,sys
data = json.load(sys.stdin)
for fname, findings in data.get('results',{}).items():
    for f in findings:
        tp = f.get('type','?')
        line = f.get('line_number','?')
        print(f'  {tp:40s} | {fname}:{line}')
" 2>/dev/null
            VIOLATIONS=$((VIOLATIONS + count))
        fi
    fi
fi

# ── 引擎 2: 自定义正则 (境内服务商覆盖) ──
CUSTOM=(
    'ark-[a-z0-9]{20,}'
    'cli_aaa[a-z0-9]{10,}'
    'Authorization: Bearer [a-zA-Z0-9_\-]{20,}'
    '(?<![a-z])(sk-(?!(ant-|proj-|svcacct-|live_|oai-))[a-zA-Z0-9]{20,})'
)

EXCLUDE='xxx\|XXXX\|your\|placeholder\|example\|sample\|demo\|fake\|dummy\|invalid\|test_key\|<ARK\|<FEISHU\|sk-oai-invalid\|node_modules\|package-lock'

for pattern in "${CUSTOM[@]}"; do
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        matches=$(git diff --cached "$file" 2>/dev/null | grep -nP "$pattern" 2>/dev/null | grep -vP "$EXCLUDE" 2>/dev/null)
        if [ -n "$matches" ]; then
            if [ $VIOLATIONS -eq 0 ]; then
                echo ""
                echo -e "${RED}╔═══════════════════════════════════════════════╗${NC}"
                echo -e "${RED}║  ⛔ 自定义正则检测到敏感信息 — 提交已阻止       ║${NC}"
                echo -e "${RED}╚═══════════════════════════════════════════════╝${NC}"
                echo ""
            fi
            echo -e "${YELLOW}  📄 ${file}${NC}"
            while IFS= read -r line; do
                masked=$(echo "$line" | sed -E 's/([a-zA-Z0-9_\-]{4})[a-zA-Z0-9_\-]{10,}([a-zA-Z0-9_\-]{4})/\1****\2/g')
                echo -e "     ${RED}→${NC} $masked"
            done <<< "$matches"
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    done <<< "$FILES"
done

# ── 判定 ──
if [ $VIOLATIONS -gt 0 ]; then
    echo ""
    echo -e "  ${CYAN}检测引擎:${NC} detect-secrets (熵+28插件) + 自定义正则"
    echo -e "  ${RED}共 ${VIOLATIONS} 处敏感信息${NC}"
    echo -e "  ${YELLOW}git commit --no-verify 可强制绕过 (不推荐)${NC}"
    echo ""
    exit 1
fi

exit 0
