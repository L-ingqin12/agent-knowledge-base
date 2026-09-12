#!/bin/bash
# ============================================================================
# Git Secrets Scanner — 可用于 pre-commit / CI / 手动扫描
#
# 用法:
#   git-secrets-scan.sh                  # 扫描 staged 文件 (pre-commit)
#   git-secrets-scan.sh --all            # 扫描整个仓库
#   git-secrets-scan.sh --file x.sh      # 扫描单个文件
#   git-secrets-scan.sh --mask           # 扫描 + 自动脱敏替换
# ============================================================================

PATTERNS=(
    'sk-[a-zA-Z0-9]{20,}'
    'ark-[a-z0-9]{20,}'
    'ghp_[a-zA-Z0-9]{20,}'
    'gho_[a-zA-Z0-9]{20,}'
    'github_pat_[a-zA-Z0-9]{20,}'
    'cli_aaa[a-z0-9]{10,}'
    'Authorization: Bearer [a-zA-Z0-9_\-]{20,}'
    '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
    '[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{30,}\.[a-zA-Z0-9_\-]{20,}'
)

EXCLUDE='sk-XXX|sk-your|sk-example|sk-oai-invalid|YOUR_API_KEY|REPLACE_ME|placeholder|<ARK|<FEISHU|<GITHUB|example\.com'

MASK=false
TARGET="staged"

for arg in "$@"; do
    case $arg in
        --all) TARGET="all" ;;
        --file) TARGET="file"; FILE="$2"; shift ;;
        --mask) MASK=true ;;
    esac
    shift 2>/dev/null
done

scan_content() {
    local content="$1" filepath="$2"
    local found=0

    for pattern in "${PATTERNS[@]}"; do
        local matches
        matches=$(echo "$content" | grep -nP "$pattern" 2>/dev/null | grep -vP "$EXCLUDE" 2>/dev/null)
        if [ -n "$matches" ]; then
            found=1
            while IFS= read -r line; do
                local masked
                masked=$(echo "$line" | sed -E 's/([a-zA-Z0-9_\-]{4})[a-zA-Z0-9_\-]{10,}([a-zA-Z0-9_\-]{4})/\1****\2/g')
                echo "VIOLATION|$filepath|$masked"
            done <<< "$matches"
        fi
    done
    return $found
}

# ── 主逻辑 ──
FOUND=0
case $TARGET in
    staged)
        while IFS= read -r file; do
            [ -z "$file" ] && continue
            content=$(git diff --cached "$file" 2>/dev/null)
            scan_content "$content" "$file" && FOUND=1
        done < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
        ;;
    all)
        while IFS= read -r file; do
            [ -z "$file" ] && continue
            case "$file" in
                *.lock|*.png|*.jpg|*.gif|*.ico|*.pdf|*.zip|*.tar*|*.gz|.git/*) continue ;;
            esac
            content=$(cat "$file" 2>/dev/null)
            scan_content "$content" "$file" && FOUND=1
        done < <(git ls-files 2>/dev/null)
        ;;
    file)
        content=$(cat "$FILE" 2>/dev/null)
        scan_content "$content" "$FILE" && FOUND=1
        ;;
esac

if [ $FOUND -eq 0 ]; then
    echo "CLEAN"
fi
exit $FOUND
