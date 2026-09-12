#!/bin/bash
# ============================================================================
# API 用量监控 — 异常时通过飞书通知用户
#
# 数据来源: model_router (:18888/stats)
# 告警通道: hermes oneshot → 飞书
# 部署: */15 * * * * /home/pi/api-usage-monitor.sh >> /var/log/api-monitor.log 2>&1
# ============================================================================
set -e

# ── 配置 ──
ROUTER_URL="http://127.0.0.1:18888/stats"
STATE_FILE="/tmp/api-monitor.state"
LOG_FILE="/var/log/api-monitor.log"
HERMES="/home/pi/.local/bin/hermes"

# 告警阈值
HOURLY_CALL_LIMIT=50      # 每小时调用 > 50 次 → 告警
DAILY_CALL_LIMIT=200      # 每天调用 > 200 次 → 告警
SPIKE_RATIO=3             # 相比上一时段的增幅 > 3x → 告警
CHECK_INTERVAL=900        # 15分钟检查间隔

# ── 当前数据 ──
NOW=$(date +%s)
TODAY=$(date +%Y%m%d)
HOUR=$(date +%H)
LOG_TAG="[$(date '+%m-%d %H:%M')]"

# ── 获取路由器统计 ──
get_router_stats() {
    curl -s --max-time 5 "$ROUTER_URL" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tiers = d.get('tiers', {})
    total = sum(tiers.values())
    print(json.dumps({
        'total': total,
        'tiers': tiers,
        'errors': d.get('errors', 0),
        'fallbacks': sum(d.get('fallbacks', {}).values())
    }))
except:
    print('{\"total\":0,\"tiers\":{},\"errors\":0,\"fallbacks\":0}')
"
}

# ── 加载/保存状态 ──
load_state() {
    [ -f "$STATE_FILE" ] && source "$STATE_FILE" 2>/dev/null || true
    LAST_TOTAL=${last_total:-0}
    LAST_HOUR=${last_hour:-$HOUR}
    LAST_DAY=${last_day:-$TODAY}
    HOURLY_COUNT=${hourly_count:-0}
    DAILY_COUNT=${daily_count:-0}
    LAST_CHECK=${last_check:-$NOW}
    # 跨小时重置
    [ "$LAST_HOUR" != "$HOUR" ] && HOURLY_COUNT=0
    # 跨天重置
    [ "$LAST_DAY" != "$TODAY" ] && DAILY_COUNT=0
}

save_state() {
    cat > "$STATE_FILE" << EOF
last_total=${CURRENT_TOTAL}
last_hour=${HOUR}
last_day=${TODAY}
hourly_count=${HOURLY_COUNT}
daily_count=${DAILY_COUNT}
last_check=${NOW}
EOF
}

# ── 飞书通知 ──
notify_via_feishu() {
    local level="$1" msg="$2"
    local full_msg="⚠️ API用量告警 [$level]
时间: $(date '+%m-%d %H:%M:%S')
${msg}
---
来自 api-usage-monitor"

    echo "$LOG_TAG 告警: $level — $msg" | tee -a "$LOG_FILE"

    # 通过 hermes oneshot 发飞书消息
    if [ -x "$HERMES" ]; then
        echo "$full_msg" | timeout 30 "$HERMES" oneshot -m deepseek-v4-flash-260425 \
            "发送以下告警信息到飞书用户，直接发送不要做任何额外操作：$full_msg" \
            >> "$LOG_FILE" 2>&1 || echo "$LOG_TAG 飞书发送失败" >> "$LOG_FILE"
    fi
}

# ── 主逻辑 ──
main() {
    load_state

    local stats
    stats=$(get_router_stats)
    CURRENT_TOTAL=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])")

    # 本时段增量
    local increment=$((CURRENT_TOTAL - LAST_TOTAL))
    [ "$increment" -lt 0 ] && increment=0  # 路由器重启计数器归零

    HOURLY_COUNT=$((HOURLY_COUNT + increment))
    DAILY_COUNT=$((DAILY_COUNT + increment))

    local elapsed=$((NOW - LAST_CHECK))
    local hourly_rate=0
    [ "$elapsed" -gt 0 ] && hourly_rate=$((increment * 3600 / elapsed))

    echo "$LOG_TAG 总计: $CURRENT_TOTAL | 增量: $increment | 时速率: ${hourly_rate}/h | 今日: $DAILY_COUNT"

    # ── 告警判定 ──
    local alerts=""

    # 1. 小时超限
    if [ "$HOURLY_COUNT" -gt "$HOURLY_CALL_LIMIT" ]; then
        alerts="${alerts}小时调用 ${HOURLY_COUNT} > ${HOURLY_CALL_LIMIT} 阈值\n"
    fi

    # 2. 日超限
    if [ "$DAILY_COUNT" -gt "$DAILY_CALL_LIMIT" ]; then
        alerts="${alerts}今日调用 ${DAILY_COUNT} > ${DAILY_CALL_LIMIT} 阈值\n"
    fi

    # 3. 尖峰 (相较上一次检查增幅 > 3x)
    local prev_increment=${prev_increment:-$increment}
    if [ "$prev_increment" -gt 0 ] && [ "$increment" -gt $((prev_increment * SPIKE_RATIO)) ]; then
        alerts="${alerts}调用尖峰: ${prev_increment} → ${increment} (${SPIKE_RATIO}x增幅)\n"
    fi

    # 4. 错误率
    local errors
    errors=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin)['errors'])")
    if [ "$errors" -gt 10 ]; then
        alerts="${alerts}路由器错误累计: ${errors}\n"
    fi

    if [ -n "$alerts" ]; then
        local tier_detail
        tier_detail=$(echo "$stats" | python3 -c "
import sys,json
d = json.load(sys.stdin)
tiers = d.get('tiers', {})
print(' | '.join(f'{k}:{v}' for k,v in sorted(tiers.items())))
")
        notify_via_feishu "API" "分层: ${tier_detail}
今日: ${DAILY_COUNT} 次
时速率: ${hourly_rate}/h
${alerts}"
    fi

    # 保存状态 (含本次增量用于下次尖峰检测)
    cat > "$STATE_FILE" << EOF
last_total=${CURRENT_TOTAL}
last_hour=${HOUR}
last_day=${TODAY}
hourly_count=${HOURLY_COUNT}
daily_count=${DAILY_COUNT}
last_check=${NOW}
prev_increment=${increment}
EOF
}

main "$@"
