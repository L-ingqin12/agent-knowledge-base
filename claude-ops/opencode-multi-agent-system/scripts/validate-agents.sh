#!/usr/bin/env bash
# validate-agents.sh — 验证所有 OpenCode 智能体定义的格式正确性
# 用法: bash scripts/validate-agents.sh

set -euo pipefail

AGENT_DIR=".opencode/agent"
ERRORS=0
WARNINGS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "  OpenCode Agent Validation"
echo "============================================"
echo ""

# 检查目录存在
if [ ! -d "$AGENT_DIR" ]; then
    echo -e "${RED}✗${NC} Agent directory not found: $AGENT_DIR"
    exit 1
fi

echo "📁 Scanning: $AGENT_DIR"
echo ""

# 有效值定义
VALID_MODES="primary subagent all"
VALID_TOOLS="read write edit bash grep glob list patch todowrite todoread webfetch websearch task"

# 遍历所有 .md 文件
for agent_file in "$AGENT_DIR"/*.md; do
    if [ ! -f "$agent_file" ]; then
        echo -e "${YELLOW}⚠${NC}  No .md files found in $AGENT_DIR"
        break
    fi

    AGENT_NAME=$(basename "$agent_file" .md)
    echo "🔍 Validating: $AGENT_NAME"

    # 检查是否有 frontmatter (--- 开始)
    if ! head -1 "$agent_file" | grep -q "^---$"; then
        echo -e "  ${RED}✗${NC} Missing YAML frontmatter (must start with ---)"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    # 提取 frontmatter (第二个 --- 之前)
    FRONTMATTER=$(awk 'BEGIN{c=0} /^---$/{c++; if(c==2)exit; next} c==1{print}' "$agent_file")

    # 检查必填字段
    # mode
    MODE=$(echo "$FRONTMATTER" | grep "^mode:" | sed 's/^mode:\s*//' | tr -d '"' | tr -d "'" | xargs)
    if [ -z "$MODE" ]; then
        echo -e "  ${YELLOW}⚠${NC}  mode not set (defaults to 'all')"
        WARNINGS=$((WARNINGS + 1))
    elif ! echo "$VALID_MODES" | grep -qw "$MODE"; then
        echo -e "  ${RED}✗${NC} Invalid mode: '$MODE' (must be: $VALID_MODES)"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "  ${GREEN}✓${NC} mode: $MODE"
    fi

    # description
    DESC=$(echo "$FRONTMATTER" | grep "^description:" | sed 's/^description:\s*//' | tr -d '"' | xargs)
    if [ -z "$DESC" ]; then
        echo -e "  ${YELLOW}⚠${NC}  description is empty"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "  ${GREEN}✓${NC} description: ${DESC:0:50}..."
    fi

    # tools
    if echo "$FRONTMATTER" | grep -q "^tools:"; then
        TOOLS_COUNT=0
        while IFS=':' read -r tool value; do
            tool=$(echo "$tool" | xargs)
            value=$(echo "$value" | xargs)
            if [ -n "$tool" ] && [ "$tool" != "tools" ]; then
                TOOLS_COUNT=$((TOOLS_COUNT + 1))
                if [ "$value" != "true" ] && [ "$value" != "false" ]; then
                    echo -e "  ${YELLOW}⚠${NC}  Tool '$tool' value should be true/false, got: $value"
                    WARNINGS=$((WARNINGS + 1))
                fi
            fi
        done <<< "$(echo "$FRONTMATTER" | sed -n '/^tools:/,/^[a-z]/p' | grep -v "^[a-z]")"
        echo -e "  ${GREEN}✓${NC} tools: $TOOLS_COUNT configured"
    else
        echo -e "  ${YELLOW}⚠${NC}  No tools section (all tools default to enabled)"
        WARNINGS=$((WARNINGS + 1))
    fi

    # 检查内容不为空 (frontmatter 之后)
    BODY=$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$agent_file")
    if [ -z "$(echo "$BODY" | tr -d '[:space:]')" ]; then
        echo -e "  ${RED}✗${NC} Body is empty — agent has no system prompt"
        ERRORS=$((ERRORS + 1))
    else
        BODY_LINES=$(echo "$BODY" | wc -l)
        echo -e "  ${GREEN}✓${NC} body: $BODY_LINES lines"
    fi

    # 模式特定检查
    if [ "$MODE" = "primary" ]; then
        # Primary agent 应该是 orchestrator，只应有一个
        echo -e "  ${GREEN}✓${NC} role: primary (appears in Tab cycle)"
    elif [ "$MODE" = "subagent" ]; then
        # 检查是否有 write/edit 权限（如果需要）
        HAS_WRITE=$(echo "$FRONTMATTER" | grep "write:\s*true" || true)
        HAS_EDIT=$(echo "$FRONTMATTER" | grep "edit:\s*true" || true)
        if [ -z "$HAS_WRITE" ] && [ -z "$HAS_EDIT" ]; then
            echo -e "  ${GREEN}✓${NC} role: read-only subagent (by design)"
        else
            echo -e "  ${GREEN}✓${NC} role: read-write subagent"
        fi
    fi

    echo ""
done

echo "============================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "  ${GREEN}✅ All agents validated successfully${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "  ${YELLOW}⚠️  Validation passed with $WARNINGS warning(s)${NC}"
else
    echo -e "  ${RED}❌ Validation failed: $ERRORS error(s), $WARNINGS warning(s)${NC}"
fi
echo "============================================"

exit $ERRORS
