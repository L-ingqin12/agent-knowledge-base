#!/bin/bash
# ============================================================================
# Hermes Gateway Guardian v1.1
#
# 6 探针 → 综合评分 → 5 级恢复阶梯 → 自保护冷却
# 部署: sudo cp hermes-guardian.* /etc/systemd/system/ && systemctl enable --now hermes-guardian.timer
# ============================================================================
# set -e  # 禁用 strict mode, 探针失败不应杀死整个守护

# ── 配置 ──
CHECK_INTERVAL=300                  # 基础巡检间隔 (由 systemd timer 控制)
MIN_RESTART_INTERVAL=600            # 两次 gateway 重启最短间隔 (10min)
MAX_RESTARTS_PER_HOUR=3             # 每小时最多重启次数
L4_COOLDOWN=1800                    # L4 冷却 (30min)
L5_COOLDOWN=3600                    # L5 冷却 (1h)
FEISHU_PING_COOLDOWN=900            # 飞书 API ping 冷却 (15min)
DRAIN_BUFFER=10                     # drain_timeout 之上的额外等待
CONSECUTIVE_FAILURE_LIMIT=6         # 连续失败上限 → 放弃
TOOL_LOOP_THRESHOLD=10              # 连续 tool_call 超过此数 → 疑似循环
SESSION_COUNT_WARN=20               # 会话数警告
SESSION_COUNT_CRIT=50               # 会话数严重
MAX_CHECK_DURATION=90               # 单次巡检最长耗时 (秒)

# ── 路径 ──
STATE_FILE="/tmp/hermes-guardian.state"
LOG_FILE="/var/log/hermes-guardian.log"
INCIDENT_LOG="/var/log/hermes-guardian-incidents.log"
CONFIG_FILE="/home/pi/.hermes/config.yaml"
PROXY_STATE="/tmp/proxy-guardian.state"
SECRETS_FILE="/home/pi/.hermes-guardian-secrets.sh"
GATEWAY_LOG="/home/pi/.hermes/logs/gateway.log"
AGENT_LOG="/home/pi/.hermes/logs/agent.log"
ERROR_LOG="/home/pi/.hermes/logs/errors.log"

# ── 运行时变量 ──
NOW=$(date +%s)
TODAY=$(date +%Y%m%d)
HOUR_KEY="${TODAY}_$(date +%H)"
COMPOSITE_SCORE=0.0
ESCALATION_LEVEL=0
PROBE_RESULTS=""
ACTION_TAKEN=""

# ── 工具函数 ──
log() { echo "[$(date '+%m-%d %H:%M:%S')] $1 $2: $3" | tee -a "$LOG_FILE"; }
log_incident() { echo "$NOW|$1|$2|$COMPOSITE_SCORE|$3" >> "$INCIDENT_LOG"; }

load_state() {
    [ -f "$STATE_FILE" ] && source "$STATE_FILE" 2>/dev/null || true
    STATUS=${status:-NORMAL}
    LAST_HEALTHY=${last_healthy:-0}
    CONSECUTIVE_FAILURES=${consecutive_failures:-0}
    RESTART_COUNT_HOUR=${restart_count_hour:-0}
    RESTART_HOUR=${restart_hour:-$HOUR_KEY}
    LAST_RESTART_GW=${last_restart_gw:-0}
    LAST_RESTART_ROUTER=${last_restart_router:-0}
    LAST_RESTART_PROXY=${last_restart_proxy:-0}
    LAST_L4=${last_l4:-0}
    LAST_L5=${last_l5:-0}
    LAST_FEISHU_PING=${last_feishu_ping:-0}
    MAINTENANCE=${maintenance:-0}
    GAVE_UP=${gave_up:-0}

    # 每小时重置重启计数
    [ "$RESTART_HOUR" != "$HOUR_KEY" ] && { RESTART_COUNT_HOUR=0; RESTART_HOUR="$HOUR_KEY"; }
}

save_state() {
    cat > "$STATE_FILE" << EOF
status=${STATUS}
last_healthy=${LAST_HEALTHY}
consecutive_failures=${CONSECUTIVE_FAILURES}
restart_count_hour=${RESTART_COUNT_HOUR}
restart_hour=${RESTART_HOUR}
last_restart_gw=${LAST_RESTART_GW}
last_restart_router=${LAST_RESTART_ROUTER}
last_restart_proxy=${LAST_RESTART_PROXY}
last_l4=${LAST_L4}
last_l5=${LAST_L5}
last_feishu_ping=${LAST_FEISHU_PING}
maintenance=${MAINTENANCE}
gave_up=${GAVE_UP}
last_check=${NOW}
last_composite=${COMPOSITE_SCORE}
last_action="${ACTION_TAKEN}"
EOF
}

# 从 hermes config.yaml 读值
read_hermes_config() {
    local key="$1" default="$2"
    local val
    val=$(grep -E "^\s*${key}:" "$CONFIG_FILE" 2>/dev/null | tail -1 | sed 's/.*:\s*//;s/\s*$//')
    echo "${val:-$default}"
}

# 读飞书凭据 (可选文件)
load_feishu_secrets() {
    [ -f "$SECRETS_FILE" ] && source "$SECRETS_FILE" 2>/dev/null || true
}

# ============================================================================
# 探针 P1: 网关进程
# ============================================================================
probe_gateway_process() {
    local state pid
    state=$(systemctl --user show hermes-gateway.service -p ActiveState -p MainPID 2>/dev/null | grep "ActiveState=" | cut -d= -f2)
    pid=$(systemctl --user show hermes-gateway.service -p MainPID 2>/dev/null | grep "MainPID=" | cut -d= -f2)

    case "$state" in
        active)
            if [ "$pid" -gt 0 ] 2>/dev/null && kill -0 "$pid" 2>/dev/null; then
                echo "0|0.0|GW_ACTIVE_PID_$pid"
            else
                echo "1|0.6|GW_ACTIVE_NO_PID"
            fi
            ;;
        inactive|deactivating)
            echo "2|1.0|GW_${state}"
            ;;
        failed)
            echo "2|1.0|GW_FAILED"
            ;;
        *)
            echo "2|0.9|GW_UNKNOWN_${state}"
            ;;
    esac
}

# ============================================================================
# 探针 P2: 模型路由器
# ============================================================================
probe_model_router() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 \
        http://127.0.0.1:18888/health 2>/dev/null || echo "000")

    case "$http_code" in
        200) echo "0|0.0|ROUTER_OK" ;;
        5*)  echo "1|0.5|ROUTER_ERR_$http_code" ;;
        4*)  echo "1|0.4|ROUTER_CLIENT_ERR_$http_code" ;;
        000) echo "2|1.0|ROUTER_UNREACHABLE" ;;
        *)   echo "1|0.3|ROUTER_$http_code" ;;
    esac
}

# ============================================================================
# 探针 P3: 代理连通性 (复用 proxy-guardian 状态)
# ============================================================================
probe_proxy() {
    # 优先读 proxy-guardian 的缓存结果
    if [ -f "$PROXY_STATE" ]; then
        local speed age
        # shellcheck source=/dev/null
        source "$PROXY_STATE" 2>/dev/null || true
        speed=${current_speed_kbps:-0}
        age=$((NOW - ${last_health_check:-0}))

        if [ "$age" -lt 900 ] && [ "$speed" -gt 30 ]; then
            echo "0|0.0|PROXY_CACHED_${speed}KBps"
            return
        fi
        if [ "$age" -lt 1800 ] && [ "$speed" -gt 10 ]; then
            echo "1|0.3|PROXY_SLOW_${speed}KBps"
            return
        fi
    fi

    # 独立验证
    local result code speed
    result=$(curl -s -o /dev/null -w "%{http_code}|%{speed_download}" \
        --connect-timeout 8 --max-time 15 \
        --socks5-hostname 127.0.0.1:10808 https://www.google.com 2>/dev/null || echo "000|0")
    code=$(echo "$result" | cut -d'|' -f1)
    speed=$(echo "$result" | cut -d'|' -f2 | cut -d. -f1)

    if [ "$code" = "200" ] || [ "$code" = "302" ] || [ "$code" = "301" ]; then
        local speed_kb=$((speed / 1024))
        if [ "$speed_kb" -gt 30 ]; then
            echo "0|0.0|PROXY_OK_${speed_kb}KBps"
        else
            echo "1|0.4|PROXY_SLOW_${speed_kb}KBps"
        fi
    else
        echo "2|0.9|PROXY_DOWN_HTTP_$code"
    fi
}

# ============================================================================
# 探针 P4: 飞书响应 (三步复合)
# ============================================================================
probe_feishu() {
    local ws_score=0.0 log_score=0.0 api_score=0.0
    local ws_detail="" log_detail="" api_detail=""

    # ── 4a: WebSocket 连接状态 ──
    local ws_time
    ws_time=$(grep "\[Feishu\] Connected" "$GATEWAY_LOG" 2>/dev/null | tail -1 | awk '{print $1, $2}')
    if [ -n "$ws_time" ]; then
        local ws_epoch
        ws_epoch=$(date -d "$ws_time" +%s 2>/dev/null || echo 0)
        local ws_age=$((NOW - ws_epoch))
        if [ "$ws_age" -lt 300 ]; then
            ws_score=0.0; ws_detail="WS_OK_${ws_age}s"
        elif [ "$ws_age" -lt 900 ]; then
            ws_score=0.3; ws_detail="WS_AGING_${ws_age}s"
        else
            ws_score=0.7; ws_detail="WS_STALE_${ws_age}s"
        fi
    else
        ws_score=0.8; ws_detail="WS_NO_LOG"
    fi

    # ── 4b: 日志收发比率 (最近 15 分钟) ──
    local since
    since=$(date -d '-15 min' '+%Y-%m-%d %H:%M:%S')
    local incoming outgoing
    incoming=$(grep "inbound message.*platform=feishu" "$GATEWAY_LOG" 2>/dev/null | awk -v s="$since" '$0 >= s' | wc -l)
    outgoing=$(grep "response ready.*platform=feishu\|Sending response" "$GATEWAY_LOG" 2>/dev/null | awk -v s="$since" '$0 >= s' | wc -l)

    if [ "$incoming" -eq 0 ] && [ "$outgoing" -eq 0 ]; then
        log_score=0.0; log_detail="NO_TRAFFIC"
    elif [ "$incoming" -gt 0 ] && [ "$outgoing" -eq 0 ]; then
        log_score=0.9; log_detail="SILENT_${incoming}in_0out"
    elif [ "$incoming" -gt 0 ]; then
        local ratio=$((outgoing * 100 / incoming))
        if [ "$ratio" -lt 30 ]; then
            log_score=0.5; log_detail="LOW_RESPONSE_${ratio}pct"
        else
            log_score=0.0; log_detail="RESPONDING_${ratio}pct"
        fi
    else
        log_score=0.0; log_detail="NO_INCOMING"
    fi

    # ── 4c: API 心跳 ping (有冷却) ──
    local ping_age=$((NOW - LAST_FEISHU_PING))
    if [ "$ping_age" -ge "$FEISHU_PING_COOLDOWN" ]; then
        load_feishu_secrets
        if [ -n "${FEISHU_APP_ID:-}" ] && [ -n "${FEISHU_APP_SECRET:-}" ] && [ -n "${FEISHU_CHAT_ID:-}" ]; then
            local token msg_id
            token=$(curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
                -H 'Content-Type: application/json' \
                -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}" 2>/dev/null | \
                python3 -c "import sys,json; print(json.load(sys.stdin).get('tenant_access_token',''))" 2>/dev/null)

            if [ -n "$token" ]; then
                msg_id=$(curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
                    -H "Authorization: Bearer $token" \
                    -H 'Content-Type: application/json' \
                    -d "{\"receive_id\":\"$FEISHU_CHAT_ID\",\"msg_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"/ping\\\"}\"}" 2>/dev/null | \
                    python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('data',{}).get('message_id',''))" 2>/dev/null)

                LAST_FEISHU_PING=$NOW
                api_detail="PING_SENT_${msg_id:-FAIL}"

                # 不等待响应 (会阻塞), 由下一轮检查日志确认
                if [ -z "$msg_id" ]; then
                    api_score=0.6
                else
                    api_score=0.0
                fi
            else
                api_score=0.4; api_detail="TOKEN_FAIL"
            fi
        else
            api_score=0.0; api_detail="NO_CREDENTIALS"
        fi
    else
        api_score=0.0; api_detail="COOLDOWN_${ping_age}s"
    fi

    # ── 复合计算 ──
    local composite
    composite=$(awk "BEGIN { printf \"%.2f\", 0.30*$ws_score + 0.25*$log_score + 0.30*$api_score }")

    local status=0
    [ "$(echo "$composite > 0.5" | bc -l 2>/dev/null || echo 0)" = "1" ] && status=1
    [ "$(echo "$composite > 0.8" | bc -l 2>/dev/null || echo 0)" = "1" ] && status=2

    echo "${status}|${composite}|FEISHU_${ws_detail}_${log_detail}_${api_detail}"
}

# ============================================================================
# 探针 P5: 工具循环检测
# ============================================================================
probe_tool_loop() {
    local since
    since=$(date -d '-30 min' '+%Y-%m-%d %H:%M:%S')
    local loop_count=0
    local detail=""

    # 取活跃会话 ID
    local session_ids
    session_ids=$(grep -oP 'session=\K[a-z0-9_:]+' "$GATEWAY_LOG" 2>/dev/null | sort -u | tail -10)

    for sid in $session_ids; do
        [ -z "$sid" ] && continue
        local events
        events=$(grep "$sid" "$AGENT_LOG" 2>/dev/null | awk -v s="$since" '$0 >= s' | tail -100)
        local tool_calls responses
        tool_calls=$(echo "$events" | grep -c "tool.*completed\|tool_executor" 2>/dev/null || echo 0)
        responses=$(echo "$events" | grep -c "response ready\|conversation.*text\|chat.*response" 2>/dev/null || echo 0)

        if [ "$tool_calls" -gt "$TOOL_LOOP_THRESHOLD" ] && [ "$responses" -eq 0 ]; then
            loop_count=$((loop_count + 1))
            detail="${detail} ${sid##*:}(tc=${tool_calls})"
        fi
    done

    # 也检查 errors.log 中的 tool loop 警告
    local warnings
    warnings=$(grep "tool.*loop\|same_tool_failure\|repeated_exact" "$ERROR_LOG" 2>/dev/null | awk -v s="$since" '$0 >= s' | wc -l)

    if [ "$loop_count" -gt 0 ]; then
        echo "2|0.8|LOOP_${loop_count}sessions${detail}_${warnings}warnings"
    elif [ "$warnings" -gt 5 ]; then
        echo "1|0.4|LOOP_WARNINGS_${warnings}"
    elif [ "$warnings" -gt 0 ]; then
        echo "0|0.1|LOOP_TRACE_${warnings}"
    else
        echo "0|0.0|LOOP_CLEAN"
    fi
}

# ============================================================================
# 探针 P6: 会话数
# ============================================================================
probe_session_count() {
    local count
    count=$(ls /home/pi/.hermes/sessions/*.json 2>/dev/null | wc -l)

    if [ "$count" -le "$SESSION_COUNT_WARN" ]; then
        echo "0|0.0|SESSIONS_${count}"
    elif [ "$count" -le "$SESSION_COUNT_CRIT" ]; then
        echo "1|0.3|SESSIONS_HIGH_${count}"
    else
        echo "2|0.7|SESSIONS_CRIT_${count}"
    fi
}

# ============================================================================
# 综合评分 & 升级判定
# ============================================================================
compute_composite() {
    local scores=""
    local weights="" detail=""
    local gw router proxy feishu tool session
    local gw_score=0 router_score=0 proxy_score=0 feishu_score=0 tool_score=0 session_score=0

    IFS='|' read -r _ gw_score detail <<< "$(echo "$PROBE_RESULTS" | grep "^GW:" | cut -d' ' -f2-)"
    IFS='|' read -r _ router_score detail <<< "$(echo "$PROBE_RESULTS" | grep "^ROUTER:" | cut -d' ' -f2-)"
    IFS='|' read -r _ proxy_score detail <<< "$(echo "$PROBE_RESULTS" | grep "^PROXY:" | cut -d' ' -f2-)"
    IFS='|' read -r _ feishu_score detail <<< "$(echo "$PROBE_RESULTS" | grep "^FEISHU:" | cut -d' ' -f2-)"
    IFS='|' read -r _ tool_score detail <<< "$(echo "$PROBE_RESULTS" | grep "^TOOL:" | cut -d' ' -f2-)"
    IFS='|' read -r _ session_score detail <<< "$(echo "$PROBE_RESULTS" | grep "^SESSION:" | cut -d' ' -f2-)"

    # 加权: GW 35%, ROUTER 25%, PROXY 15%, FEISHU 15%, TOOL 5%, SESSION 5%
    COMPOSITE_SCORE=$(awk "BEGIN {
        s = 0.35*${gw_score:-0} + 0.25*${router_score:-0} + 0.15*${proxy_score:-0} + 0.15*${feishu_score:-0} + 0.05*${tool_score:-0} + 0.05*${session_score:-0};
        printf \"%.2f\", s
    }")
}

determine_escalation() {
    # 检查是否有任何探针返回 status=2 (critical)
    local critical_count
    critical_count=$(echo "$PROBE_RESULTS" | grep -c "^[A-Z]*:2|" 2>/dev/null || echo 0)

    # 检查是否有工具循环
    local tool_loop
    tool_loop=$(echo "$PROBE_RESULTS" | grep "^TOOL:" | grep -c "LOOP_[1-9]" 2>/dev/null || echo 0)

    # 检查飞书假活
    local feishu_silent
    feishu_silent=$(echo "$PROBE_RESULTS" | grep "^FEISHU:" | grep -c "SILENT" 2>/dev/null || echo 0)

    local c
    c=$(echo "$COMPOSITE_SCORE * 100" | bc | cut -d. -f1)

    if [ "$GAVE_UP" -eq 1 ]; then
        # 已放弃, 仅日志
        ESCALATION_LEVEL=0
        ACTION_TAKEN="GAVE_UP"
    elif [ "$critical_count" -ge 3 ]; then
        # 至少 3 个探针 critical → L5
        ESCALATION_LEVEL=5
        ACTION_TAKEN="L5_MULTI_CRITICAL"
    elif [ "$critical_count" -ge 2 ]; then
        # 2 个 critical → L4
        ESCALATION_LEVEL=4
        ACTION_TAKEN="L4_DUAL_CRITICAL"
    elif [ "$critical_count" -eq 1 ]; then
        # 1 个 critical → L3
        ESCALATION_LEVEL=3
        ACTION_TAKEN="L3_SINGLE_CRITICAL"
    elif [ "$c" -ge 50 ]; then
        # 综合 >0.5
        ESCALATION_LEVEL=3
        ACTION_TAKEN="L3_HIGH_COMPOSITE"
    elif [ "$c" -ge 30 ]; then
        ESCALATION_LEVEL=2
        ACTION_TAKEN="L2_DEGRADED"
    elif [ "$tool_loop" -gt 0 ]; then
        ESCALATION_LEVEL=2
        ACTION_TAKEN="L2_TOOL_LOOP"
    else
        ESCALATION_LEVEL=0
        ACTION_TAKEN="HEALTHY"
    fi
}

# ============================================================================
# 恢复动作
# ============================================================================

# L2: 警告 + 杀单会话
l2_action() {
    log "WARN" "L2" "$ACTION_TAKEN"
    log_incident "L2" "$ACTION_TAKEN" "composite=$COMPOSITE_SCORE"

    # 如果有工具循环, 杀掉问题会话
    if echo "$ACTION_TAKEN" | grep -q "TOOL_LOOP"; then
        local stuck_sessions
        stuck_sessions=$(grep -oP 'session=\K[a-z0-9_:]+' "$AGENT_LOG" 2>/dev/null | sort -u | tail -3)
        for sid in $stuck_sessions; do
            log "ACTION" "L2" "Force-closing stuck session: $sid"
            # 通过结束对应 agent 进程来关闭会话
            local agent_pids
            agent_pids=$(pgrep -f "hermes.*$sid" 2>/dev/null || true)
            for pid in $agent_pids; do
                kill "$pid" 2>/dev/null && log "ACTION" "L2" "Killed agent PID $pid (session $sid)"
            done
        done
    fi
}

# L3: 重启 gateway
l3_action() {
    local cooldown=$((NOW - LAST_RESTART_GW))
    if [ "$cooldown" -lt "$MIN_RESTART_INTERVAL" ]; then
        log "WARN" "L3" "冷却中 (${cooldown}s < ${MIN_RESTART_INTERVAL}s) — 跳过"
        return
    fi
    if [ "$RESTART_COUNT_HOUR" -ge "$MAX_RESTARTS_PER_HOUR" ]; then
        log "WARN" "L3" "每小时重启已达上限 ($MAX_RESTARTS_PER_HOUR) — 跳过"
        return
    fi

    log "ACTION" "L3" "Restarting hermes-gateway..."
    log_incident "L3" "RESTART_GATEWAY" ""

    systemctl --user stop hermes-gateway.service 2>/dev/null

    # 等待排水
    local drain_timeout
    drain_timeout=$(read_hermes_config "restart_drain_timeout" 60)
    local wait_time=$((drain_timeout + DRAIN_BUFFER))
    log "INFO" "L3" "等待排水 ${wait_time}s (config drain=${drain_timeout}s + buffer=${DRAIN_BUFFER}s)"
    sleep "$wait_time"

    # 强制杀残留
    pkill -f "hermes.*gateway run" 2>/dev/null || true
    sleep 3

    systemctl --user start hermes-gateway.service 2>/dev/null
    sleep 10

    if systemctl --user is-active --quiet hermes-gateway.service; then
        log "OK" "L3" "Gateway 重启成功"
        LAST_RESTART_GW=$NOW
        RESTART_COUNT_HOUR=$((RESTART_COUNT_HOUR + 1))
        CONSECUTIVE_FAILURES=0
    else
        log "ERROR" "L3" "Gateway 重启失败 → 升级到 L4"
        l4_action
    fi
}

# L4: 清会话 + 重启 router + 重启 gateway
l4_action() {
    local cooldown=$((NOW - LAST_L4))
    if [ "$cooldown" -lt "$L4_COOLDOWN" ]; then
        log "WARN" "L4" "L4 冷却中 (${cooldown}s < ${L4_COOLDOWN}s) — 跳过"
        return
    fi

    log "ACTION" "L4" "Killing sessions + restart router + restart gateway"
    log_incident "L4" "KILL_SESSIONS" ""

    # 1. 杀所有 hermes agent 子进程
    pkill -f "hermes.*agent" 2>/dev/null || true
    sleep 5
    pkill -9 -f "hermes.*agent" 2>/dev/null || true

    # 2. 清理会话锁文件
    rm -f /home/pi/.hermes/sessions/*.lock 2>/dev/null || true

    # 3. 重启 router
    systemctl --user restart model-router.service 2>/dev/null
    sleep 5
    LAST_RESTART_ROUTER=$NOW

    # 4. 重启 gateway (复用 L3 的最后部分)
    systemctl --user restart hermes-gateway.service 2>/dev/null
    sleep 15

    if systemctl --user is-active --quiet hermes-gateway.service; then
        log "OK" "L4" "恢复成功"
        LAST_L4=$NOW
        LAST_RESTART_GW=$NOW
        RESTART_COUNT_HOUR=$((RESTART_COUNT_HOUR + 1))
        CONSECUTIVE_FAILURES=0
    else
        log "ERROR" "L4" "恢复失败 → 升级到 L5"
        l5_action
    fi
}

# L5: 全栈重启 + 通知
l5_action() {
    local cooldown=$((NOW - LAST_L5))
    if [ "$cooldown" -lt "$L5_COOLDOWN" ]; then
        log "WARN" "L5" "L5 冷却中 (${cooldown}s < ${L5_COOLDOWN}s) — 跳过"
        return
    fi

    log "CRITICAL" "L5" "全栈重启"
    log_incident "L5" "FULL_STACK" ""

    # 1. 重启代理
    sudo systemctl restart xray-proxy.service 2>/dev/null || true
    sleep 5
    LAST_RESTART_PROXY=$NOW

    # 2. 重启 router
    systemctl --user restart model-router.service 2>/dev/null || true
    sleep 5
    LAST_RESTART_ROUTER=$NOW

    # 3. 杀掉所有 hermes 进程
    pkill -f "hermes_cli" 2>/dev/null || true
    sleep 5
    pkill -9 -f "hermes_cli" 2>/dev/null || true

    # 4. 清理状态
    rm -f /home/pi/.hermes/sessions/*.lock 2>/dev/null || true
    rm -f /home/pi/.hermes/gateway_state.json 2>/dev/null || true

    # 5. 启动
    systemctl --user start model-router.service 2>/dev/null || true
    sleep 3
    systemctl --user start hermes-gateway.service 2>/dev/null || true
    sleep 20

    # 6. 验证
    if systemctl --user is-active --quiet hermes-gateway.service; then
        log "OK" "L5" "全栈重启成功"
        LAST_L5=$NOW
        LAST_RESTART_GW=$NOW
        RESTART_COUNT_HOUR=$((RESTART_COUNT_HOUR + 1))
        CONSECUTIVE_FAILURES=0
        GAVE_UP=0
    else
        CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
        log "CRITICAL" "L5" "全栈重启失败 (第 $CONSECUTIVE_FAILURES 次连续失败)"

        if [ "$CONSECUTIVE_FAILURES" -ge "$CONSECUTIVE_FAILURE_LIMIT" ]; then
            GAVE_UP=1
            STATUS="GIVE_UP"
            log "CRITICAL" "L5" "已达连续失败上限 ($CONSECUTIVE_FAILURE_LIMIT), 放弃自动恢复, 需人工介入"
            log_incident "L5" "GAVE_UP" "consecutive_failures=$CONSECUTIVE_FAILURES"
        fi
    fi
}

# ============================================================================
# 主流程
# ============================================================================
main() {
    # 防止并发运行
    exec 200>/tmp/hermes-guardian.lock
    flock -n 200 || { log "INFO" "GUARDIAN" "已有实例在运行 — 跳过"; exit 0; }

    log "INFO" "═════" "巡检开始 ═════"
    local start_ns
    start_ns=$(date +%s%N)

    load_state

    # 维护模式
    if [ "$MAINTENANCE" -eq 1 ]; then
        log "INFO" "GUARDIAN" "维护模式 — 跳过所有动作"
        save_state
        exit 0
    fi

    # 运行全部探针
    PROBE_RESULTS="GW:$(probe_gateway_process)"
    log "PROBE" "P1" "$(echo "$PROBE_RESULTS" | grep "^GW:" | cut -d: -f3-)"

    PROBE_RESULTS="$PROBE_RESULTS
ROUTER:$(probe_model_router)"
    log "PROBE" "P2" "$(echo "$PROBE_RESULTS" | grep "^ROUTER:" | cut -d: -f3-)"

    PROBE_RESULTS="$PROBE_RESULTS
PROXY:$(probe_proxy)"
    log "PROBE" "P3" "$(echo "$PROBE_RESULTS" | grep "^PROXY:" | cut -d: -f3-)"

    PROBE_RESULTS="$PROBE_RESULTS
FEISHU:$(probe_feishu)"
    log "PROBE" "P4" "$(echo "$PROBE_RESULTS" | grep "^FEISHU:" | cut -d: -f3-)"

    PROBE_RESULTS="$PROBE_RESULTS
TOOL:$(probe_tool_loop)"
    log "PROBE" "P5" "$(echo "$PROBE_RESULTS" | grep "^TOOL:" | cut -d: -f3-)"

    PROBE_RESULTS="$PROBE_RESULTS
SESSION:$(probe_session_count)"
    log "PROBE" "P6" "$(echo "$PROBE_RESULTS" | grep "^SESSION:" | cut -d: -f3-)"

    # 评分 & 升级
    compute_composite
    determine_escalation
    log "INFO" "SCORE" "composite=$COMPOSITE_SCORE, level=$ESCALATION_LEVEL, action=$ACTION_TAKEN"

    # 如果全部健康
    exit 0
    if [ "$ESCALATION_LEVEL" -eq 0 ]; then
        LAST_HEALTHY=$NOW
        STATUS="HEALTHY"
        CONSECUTIVE_FAILURES=0
        GAVE_UP=0
        log "OK" "GUARDIAN" "全部健康"
    exit 0
    else
        # 执行恢复动作
        case $ESCALATION_LEVEL in
            2) l2_action ;;
            3) l3_action ;;
            4) l4_action ;;
            5) l5_action ;;
        esac
    fi

    save_state

    local elapsed_ms
    elapsed_ms=$(( ($(date +%s%N) - start_ns) / 1000000 ))
    log "INFO" "GUARDIAN" "巡检完成 (${elapsed_ms}ms, level=$ESCALATION_LEVEL)"
    log "INFO" "═════" ""

    # 超时保护: 如果本脚本运行超过 MAX_CHECK_DURATION 秒, 强制退出
    [ "$((elapsed_ms / 1000))" -gt "$MAX_CHECK_DURATION" ] && log "WARN" "GUARDIAN" "巡检超时 ${elapsed_ms}ms > ${MAX_CHECK_DURATION}s"
}

main "$@"

# 代理降级时触发 proxy-guardian 立即更新 (不等到 cron 周期)
trigger_proxy_update() {
    if [ -x /home/pi/proxy-guardian.sh ]; then
        log "ACTION" "proxy-trigger" "代理降级, 触发即时更新"
        timeout 120 sudo bash /home/pi/proxy-guardian.sh >> /var/log/proxy-guardian.log 2>&1 &
    fi
}
