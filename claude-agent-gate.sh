#!/bin/bash
# ============================================================================
# Agent Resource Gate — 子代理资源门控 (Phase 2 + 2b)
# ============================================================================
# 子命令:
#   cleanup          — 清理孤儿 claude 进程 (PPID=1, age>120s)
#   count            — 计数 claude 进程 (含当前, max=4)
#   memcheck         — 检查 MemAvailable (RED<800MB, YELLOW<1200MB)
#   status           — 单行状态摘要
#   check            — 组合门控: cleanup → read-state → count → memcheck
#   mark-interactive — 标记交互状态 (PreToolUse hook)
#   mark-idle        — 标记空闲状态 (Stop hook)
#   read-state       — 读取交互状态 (含过期检测)
#   prioritize       — 根据状态 renice/ionice 子代理
# ============================================================================
# 退出代码:
#   0 = 通过 (可 spawn) | 1 = 警告 (降级) | 2 = 拒绝 (不 spawn)
#   其他 = 故障安全 (允许, 不阻塞操作)
# ============================================================================
set +e

# ── 配置常量 ────────────────────────────────────────────────────────
MIN_MEM_GREEN=1200          # MB, 允许全部并发
MIN_MEM_RED=800             # MB, 拒绝新子代理
MAX_TOTAL_PROCS=4           # 含父进程的 claude 进程总数上限
MAX_IDLE_CONCURRENT=2       # idle 状态最大并发子代理
MAX_YELLOW_CONCURRENT=1     # 黄色内存状态最大并发
ORPHAN_AGE=120              # 孤儿进程最小存活秒数
STATE_TTL=120               # 状态文件过期秒数
STATE_FILE="/root/.claude/session-state.json"
COOLDOWN_FILE="/tmp/claude-agent-gate-cooldown"
COOLDOWN_SEC=5              # spawn 冷却窗口 (缓解竞态)

# ── 工具函数 ────────────────────────────────────────────────────────

now_ts() { date -u +%s 2>/dev/null || echo 0; }

# 安全计数 claude 进程 (容错 pgrep 不可用)
count_claude_procs() {
    pgrep -x claude 2>/dev/null | wc -l || echo 0
}

# 读取 MemAvailable (kB → MB), 容错 /proc 不可读
read_mem_available_mb() {
    local val
    val=$(awk '/MemAvailable/{print $2}' /proc/meminfo 2>/dev/null)
    if [ -n "$val" ] && [ "$val" -gt 0 ] 2>/dev/null; then
        echo $((val / 1024))
    else
        # 退而求其次: MemFree + Cached
        local free cached
        free=$(awk '/MemFree/{print $2}' /proc/meminfo 2>/dev/null || echo 0)
        cached=$(awk '/^Cached/{print $2}' /proc/meminfo 2>/dev/null || echo 0)
        echo $(((free + cached) / 1024))
    fi
}

# 读取 Swap 使用率 (%)
read_swap_pct() {
    local total free used
    total=$(awk '/SwapTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0)
    free=$(awk '/SwapFree/{print $2}' /proc/meminfo 2>/dev/null || echo 0)
    if [ "$total" -gt 0 ] 2>/dev/null; then
        used=$((total - free))
        echo $((used * 100 / total))
    else
        echo 0
    fi
}

# 检查冷却窗口 (防止竞态: 两次 check 间隔太短)
check_cooldown() {
    local now cooldown_ts elapsed
    now=$(now_ts)
    if [ -f "$COOLDOWN_FILE" ]; then
        cooldown_ts=$(cat "$COOLDOWN_FILE" 2>/dev/null || echo 0)
        elapsed=$((now - cooldown_ts))
        if [ "$elapsed" -lt "$COOLDOWN_SEC" ] 2>/dev/null; then
            return 1  # 冷却中
        fi
    fi
    return 0  # 冷却已过
}

# 设置冷却时间戳
set_cooldown() {
    now_ts > "$COOLDOWN_FILE" 2>/dev/null || true
}

# ── 子命令实现 ──────────────────────────────────────────────────────

# cleanup: 清理孤儿 claude 进程
do_cleanup() {
    local my_pid cleaned
    my_pid=$$
    cleaned=0

    for pid in $(pgrep -x claude 2>/dev/null); do
        # 跳过自身
        [ "$pid" = "$my_pid" ] && continue
        # 跳过当前 session 的父进程
        [ "$pid" = "$PPID" ] && continue

        local ppid age
        ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
        age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')

        # 孤儿检测: PPID=1 (init 收养) 或 父进程不存在
        if [ "$ppid" = "1" ] 2>/dev/null || ! kill -0 "$ppid" 2>/dev/null; then
            if [ -n "$age" ] && [ "$age" -gt "$ORPHAN_AGE" ] 2>/dev/null; then
                kill "$pid" 2>/dev/null && cleaned=$((cleaned + 1))
            fi
        fi
    done

    # 60s 后仍未死 → SIGKILL (后台异步)
    if [ "$cleaned" -gt 0 ]; then
        (
            sleep 60
            for pid in $(pgrep -x claude 2>/dev/null); do
                [ "$pid" = "$my_pid" ] && continue
                local ppid
                ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
                if [ "$ppid" = "1" ] 2>/dev/null; then
                    kill -9 "$pid" 2>/dev/null || true
                fi
            done
        ) &
    fi

    echo "cleanup: $cleaned orphans terminated"
}

# count: 检查进程数上限
do_count() {
    local total current
    total=$(count_claude_procs)
    current=$((total > 0 ? total : 1))  # 至少算自身

    if [ "$current" -ge "$MAX_TOTAL_PROCS" ] 2>/dev/null; then
        echo "count: DENY ($current running, max $MAX_TOTAL_PROCS)"
        return 2
    fi
    echo "count: OK ($current running)"
    return 0
}

# memcheck: 内存门槛检查
do_memcheck() {
    local mem swap
    mem=$(read_mem_available_mb)
    swap=$(read_swap_pct)

    if [ "$mem" -lt "$MIN_MEM_RED" ] 2>/dev/null; then
        echo "memcheck: DENY (${mem}MB available < ${MIN_MEM_RED}MB, swap ${swap}%)"
        return 2
    elif [ "$mem" -lt "$MIN_MEM_GREEN" ] 2>/dev/null; then
        echo "memcheck: WARN (${mem}MB available < ${MIN_MEM_GREEN}MB, swap ${swap}%)"
        return 1
    fi
    echo "memcheck: OK (${mem}MB available, swap ${swap}%)"
    return 0
}

# read-state: 读取交互状态 (含过期检测, epoch 秒比较)
do_read_state() {
    local state epoch now age
    now=$(now_ts)

    if [ ! -f "$STATE_FILE" ]; then
        echo "read-state: missing → interactive (safe default)"
        return 1
    fi

    state=$(grep -oP '"state":"\K[^"]+' "$STATE_FILE" 2>/dev/null || echo "interactive")
    epoch=$(grep -oP '"epoch":\K[0-9]+' "$STATE_FILE" 2>/dev/null || echo 0)

    if [ -z "$epoch" ] || [ "$epoch" -eq 0 ] 2>/dev/null; then
        echo "read-state: corrupt → interactive (safe default)"
        return 1
    fi

    age=$((now - epoch))

    if [ "$age" -gt "$STATE_TTL" ] 2>/dev/null; then
        echo "read-state: stale (${age}s > ${STATE_TTL}s) → interactive"
        return 1
    fi

    echo "read-state: $state (${age}s ago)"
    if [ "$state" = "idle" ]; then
        return 0
    else
        return 1
    fi
}

# 写入状态文件 (epoch 秒, 无时区歧义)
write_state() {
    local state="$1" hook="${2:-manual}"
    local epoch
    epoch=$(date +%s 2>/dev/null || echo 0)
    echo "{\"state\":\"$state\",\"epoch\":$epoch,\"hook\":\"$hook\"}" > "$STATE_FILE" 2>/dev/null || true
}

# mark-interactive: PreToolUse hook 调用
do_mark_interactive() {
    write_state "interactive" "PreToolUse"
    do_prioritize  # 立即降权已有子代理
    echo "mark-interactive: state=interactive"
}

# mark-idle: Stop / SessionStart hook 调用
do_mark_idle() {
    write_state "idle" "Stop"
    do_prioritize  # 恢复子代理优先级
    echo "mark-idle: state=idle"
}

# prioritize: 根据当前状态 renice/ionice 子代理
do_prioritize() {
    local state target_nice target_ionice my_pid
    my_pid=$$

    # 读取当前状态
    if do_read_state >/dev/null 2>&1; then
        state="idle"
        target_nice=0
        target_ionice="2 -n 0"  # best-effort
    else
        state="interactive"
        target_nice=19
        target_ionice="3"       # idle class
    fi

    for pid in $(pgrep -x claude 2>/dev/null); do
        [ "$pid" = "$my_pid" ] && continue
        [ "$pid" = "$PPID" ] && continue

        renice -n "$target_nice" -p "$pid" 2>/dev/null || true
        ionice -c $target_ionice -p "$pid" 2>/dev/null || true
    done
}

# status: 单行状态摘要
do_status() {
    local mem swap procs state_info
    mem=$(read_mem_available_mb)
    swap=$(read_swap_pct)
    procs=$(count_claude_procs)

    if do_read_state >/dev/null 2>&1; then
        state_info="idle"
    else
        state_info="interactive"
    fi

    # 判断内存状态等级
    local mem_level
    if [ "$mem" -lt "$MIN_MEM_RED" ] 2>/dev/null; then
        mem_level="RED"
    elif [ "$mem" -lt "$MIN_MEM_GREEN" ] 2>/dev/null; then
        mem_level="YELLOW"
    else
        mem_level="GREEN"
    fi

    echo "MemAvail=${mem}MB SwapUsed=${swap}% ClaudeProcs=${procs} MemLevel=${mem_level} State=${state_info}"
}

# check: 组合门控 (PreToolUse hook 调用)
do_check() {
    local result

    # 1. 清理孤儿
    do_cleanup >/dev/null 2>&1 || true

    # 2. 冷却检查 (缓解竞态)
    if ! check_cooldown; then
        echo '{"status":"DENY","reason":"cooldown (spawn too fast)","action":"wait_5s"}'
        return 2
    fi

    # 3. 交互状态检查 (Phase 2b)
    if ! do_read_state >/dev/null 2>&1; then
        local reason
        reason=$(do_read_state 2>&1)
        echo "{\"status\":\"DENY\",\"reason\":\"interactive state\",\"detail\":\"$reason\",\"action\":\"retry_when_idle\"}"
        return 2
    fi

    # 4. 进程数检查
    result=$(do_count)
    local count_rc=$?
    if [ "$count_rc" -eq 2 ]; then
        echo "{\"status\":\"DENY\",\"reason\":\"process limit\",\"detail\":\"$result\",\"action\":\"wait_or_reduce\"}"
        return 2
    fi

    # 5. 内存检查
    result=$(do_memcheck)
    local mem_rc=$?
    if [ "$mem_rc" -eq 2 ]; then
        echo "{\"status\":\"DENY\",\"reason\":\"memory low\",\"detail\":\"$result\",\"action\":\"clean_orphans_first\"}"
        return 2
    elif [ "$mem_rc" -eq 1 ]; then
        echo "{\"status\":\"WARN\",\"reason\":\"memory moderate\",\"detail\":\"$result\",\"action\":\"reduce_concurrency\"}"
        set_cooldown
        return 1
    fi

    # 6. 通过
    set_cooldown
    echo "{\"status\":\"OK\",\"reason\":\"resources sufficient\",\"detail\":\"$result\"}"
    return 0
}

# ── 主入口 ──────────────────────────────────────────────────────────

case "${1:-}" in
    cleanup)          do_cleanup ;;
    count)            do_count ;;
    memcheck)         do_memcheck ;;
    read-state)       do_read_state ;;
    status)           do_status ;;
    check)            do_check ;;
    mark-interactive) do_mark_interactive ;;
    mark-idle)        do_mark_idle ;;
    prioritize)       do_prioritize ;;
    *)
        echo "Usage: $0 {cleanup|count|memcheck|read-state|status|check|mark-interactive|mark-idle|prioritize}"
        echo ""
        echo "Agent Resource Gate — subagent spawn control"
        echo ""
        echo "Gate commands (Phase 2):"
        echo "  cleanup           Kill orphan claude processes (PPID=1, age>${ORPHAN_AGE}s)"
        echo "  count             Check total claude processes (max ${MAX_TOTAL_PROCS})"
        echo "  memcheck          Check MemAvailable (RED<${MIN_MEM_RED}MB, YELLOW<${MIN_MEM_GREEN}MB)"
        echo "  status            Single-line resource summary"
        echo "  check             Combined gate: cleanup→state→count→memcheck (for PreToolUse)"
        echo ""
        echo "Interactive state (Phase 2b):"
        echo "  mark-interactive  Set interactive state + deprioritize subagents (PreToolUse hook)"
        echo "  mark-idle         Set idle state + restore priority (Stop hook)"
        echo "  read-state        Print current state with staleness check"
        echo "  prioritize        Apply nice/ionice to subagents based on state"
        exit 0
        ;;
esac
