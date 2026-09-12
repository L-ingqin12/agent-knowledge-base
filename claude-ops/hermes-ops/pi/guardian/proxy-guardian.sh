#!/bin/bash
# ============================================================================
# 代理智能守护 v1 — 按需更新 + 动态测速 + 更新时机管控
#
# 策略:
#   0. 本地网络预检: 先确认路由器/DNS/局域网正常, 防止误判代理故障
#   1. 正常期: 速度正常 → 不更新, 仅记录
#   2. 减速期: 速度 < 阈值 且 冷却已过 → 全量测速择优
#   3. 冷却期: 全量更新后至少 2 小时不再更新 (避免频繁切换)
#   4. 保底期: 距离上次成功更新超过 8 小时 → 强制全量更新
#   5. 紧急期: 当前节点完全不通 且 本地网络正常 → 立即全量更新 (忽略冷却)
#
# 状态文件: /tmp/proxy-guardian.state
#   last_full_update=timestamp
#   last_health_check=timestamp
#   current_node=name
#   current_speed_kbps=N
#   update_count_today=N
#
# 部署:
#   */15 * * * * /home/pi/proxy-guardian.sh >> /var/log/proxy-guardian.log 2>&1
# ============================================================================
set -e

# ── 配置 ──
# 【订阅 URL 不再内嵌】
# 原版把 xray/V2Ray 订阅地址（含 host + 32 位路径 token，等同 bearer 凭据）明文写在此处。
# 该凭据可换取实时节点列表并消耗付费代理额度，故外置为：
#   ① 环境变量 SUB_URL，或
#   ② 本机未跟踪文件（推荐，避免进 shell 历史）
# 本文件不含任何凭据。缺失即拒绝启动，不做静默回退。
: "${SUB_URL_FILE:=$HOME/.config/proxy-guardian/sub_url}"
if [ -n "${SUB_URL:-}" ]; then
  :
elif [ -r "$SUB_URL_FILE" ]; then
  SUB_URL="$(cat "$SUB_URL_FILE")"
else
  echo "proxy-guardian: 缺少订阅地址。请设置 SUB_URL，或写入 $SUB_URL_FILE" >&2
  exit 2
fi
CONFIG="/usr/local/etc/xray/config.json"
SERVICE="xray-proxy"
PROXY="127.0.0.1:10808"
STATE_FILE="/tmp/proxy-guardian.state"
UPDATE_SCRIPT="/home/pi/update-proxy-sub.sh"
LOG_TAG="[$(date '+%m-%d %H:%M')]"

# 时机阈值
HEALTH_CHECK_INTERVAL=900       # 轻量测速间隔 (15min)
FULL_UPDATE_COOLDOWN=7200       # 全量更新冷却 (2h)
MAX_STALENESS=28800             # 最大陈旧 (8h) → 强制全量
MIN_SPEED_KBPS=30               # 低于此值触发全量更新
EMERGENCY_SPEED_KBPS=5          # 低于此值 → 紧急 (忽略冷却)
MAX_UPDATES_PER_DAY=12          # 每日全量更新上限

# ── 状态管理 ──
load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE" 2>/dev/null || true
    fi
    LAST_FULL_UPDATE=${last_full_update:-0}
    LAST_HEALTH_CHECK=${last_health_check:-0}
    CURRENT_NODE=${current_node:-"unknown"}
    CURRENT_SPEED=${current_speed_kbps:-0}
    UPDATE_COUNT=${update_count_today:-0}

    # 每日重置计数
    local today
    today=$(date +%Y%m%d)
    local state_day=${state_day:-$today}
    if [ "$state_day" != "$today" ]; then
        UPDATE_COUNT=0
    fi
}

save_state() {
    cat > "$STATE_FILE" << EOF
last_full_update=${LAST_FULL_UPDATE}
last_health_check=${LAST_HEALTH_CHECK}
current_node="${CURRENT_NODE}"
current_speed_kbps=${CURRENT_SPEED}
update_count_today=${UPDATE_COUNT}
state_day=$(date +%Y%m%d)
EOF
}

# ── 本地网络预检 ──
local_network_ok() {
    # 1. 检查默认网关是否可达
    local gateway
    gateway=$(ip route 2>/dev/null | awk '/^default/ {print $3; exit}')
    if [ -n "$gateway" ]; then
        if ! ping -c 1 -W 3 "$gateway" >/dev/null 2>&1; then
            echo "❌ 网关 $gateway 不可达"
            return 1
        fi
    fi

    # 2. 检查 DNS 是否可用 (解析 baidu.com — 国内必达)
    local dns_result
    dns_result=$(timeout 5 getent hosts www.baidu.com 2>/dev/null || timeout 5 host www.baidu.com 2>/dev/null || true)
    if [ -z "$dns_result" ]; then
        echo "❌ DNS 解析失败"
        return 1
    fi

    # 3. 检查能否直连百度 (确认本地网络出口正常)
    local baidu
    baidu=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 15 \
        "https://www.baidu.com" 2>/dev/null || echo "000")
    if [ "$baidu" != "200" ]; then
        echo "❌ 直连百度失败 (HTTP $baidu) — 本地网络可能有问题"
        return 1
    fi

    return 0
}

# ── 当前节点测速 ──
health_check() {
    # Pre-check: 确认 xray config 用的是 IPv4 IP 而非 hostname
    local current_addr
    current_addr=$(grep '"address"' "$CONFIG" 2>/dev/null | head -1 | grep -oP '\d+\.\d+\.\d+\.\d+' || true)
    if [ -z "$current_addr" ]; then
        echo "0|000|config_no_ipv4"
        return
    fi

    local result speed_bps speed_kb http_code time_total
    result=$(curl -s -o /dev/null -w "%{speed_download}|%{http_code}|%{time_total}" \
        --connect-timeout 8 --max-time 15 \
        --socks5-hostname "$PROXY" "https://github.com" 2>/dev/null || echo "0|000|99")

    speed_bps=$(echo "$result" | cut -d'|' -f1 | cut -d. -f1)
    http_code=$(echo "$result" | cut -d'|' -f2)
    time_total=$(echo "$result" | cut -d'|' -f3)

    speed_kb=0
    [ "${speed_bps:-0}" -gt 0 ] && speed_kb=$(awk "BEGIN {printf \"%.0f\", ${speed_bps}/1024}")

    echo "${speed_kb}|${http_code}|${time_total}"
}

# ── conntrack 监控 (防网络风暴) ──
check_conntrack() {
    local max=$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo 65536)
    local count=$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo 0)
    local pct=$((count * 100 / max))
    if [ $pct -gt 80 ]; then
        echo "$LOG_TAG ⚡ CONNTRACK 饱和 ${pct}% — 紧急清理 TIME_WAIT"
        sudo conntrack -D --state TIME_WAIT 2>/dev/null || true
        return 2
    elif [ $pct -gt 50 ]; then
        echo "$LOG_TAG ⚠ CONNTRACK 偏高 ${pct}% (${count}/${max})"
        return 1
    fi
    return 0
}


# ── 全量更新 (委托给 update-proxy-sub.sh) ──
full_update() {
    local trigger="$1"
    echo "$LOG_TAG 🔄 全量更新 (触发: $trigger)"

    # 运行更新脚本
    if sudo bash "$UPDATE_SCRIPT" 2>&1; then
        LAST_FULL_UPDATE=$(date +%s)
        UPDATE_COUNT=$((UPDATE_COUNT + 1))
        save_state
        echo "$LOG_TAG ✅ 全量更新完成"
    else
        echo "$LOG_TAG ❌ 全量更新失败 — 保持现有配置"
    fi
}

# ── 主逻辑 ──
main() {
    load_state
    local now
    now=$(date +%s)

    echo "$LOG_TAG ═══ 守护巡检 ═══"
    echo "$LOG_TAG 当前节点: $CURRENT_NODE | 上次速度: ${CURRENT_SPEED}KB/s | 今日更新: $UPDATE_COUNT"

    # —— 0. 本地网络预检 ——
    local net_status
    net_status=$(local_network_ok 2>&1)
    if [ $? -ne 0 ]; then
        echo "$LOG_TAG 🏠 本地网络异常: $net_status"
        echo "$LOG_TAG ⏸ 跳过代理检查 — 等本地网络恢复"
        save_state
        echo ""
        return
    fi
    echo "$LOG_TAG 🏠 本地网络: OK"

    check_conntrack
    local ct_rc=$?
    [ $ct_rc -eq 2 ] && echo "$LOG_TAG 🚨 CONNTRACK紧急 → 立即切换节点"
    
    # —— 检查当前健康 ——
    local hc
    hc=$(health_check)
    local hc_speed hc_code hc_time
    hc_speed=$(echo "$hc" | cut -d'|' -f1)
    hc_code=$(echo "$hc" | cut -d'|' -f2)
    hc_time=$(echo "$hc" | cut -d'|' -f3)

    CURRENT_SPEED=$hc_speed
    LAST_HEALTH_CHECK=$now

    local stale_sec=$((now - LAST_FULL_UPDATE))

    if [ "$hc_code" = "200" ] && [ "$hc_speed" -gt "$MIN_SPEED_KBPS" ]; then
        # === 正常: 节点工作良好 ===
        echo "$LOG_TAG ✅ 正常 — ${hc_speed}KB/s (HTTP $hc_code, ${hc_time}s)"

        # 检查是否过于陈旧 (超过 MAX_STALENESS 强制更新)
        if [ "$stale_sec" -gt "$MAX_STALENESS" ] && [ "$UPDATE_COUNT" -lt "$MAX_UPDATES_PER_DAY" ]; then
            echo "$LOG_TAG ⏰ 陈旧 ${stale_sec}s > ${MAX_STALENESS}s — 强制全量更新"
            full_update "stale_${stale_sec}s"
        else
            save_state
        fi

    elif [ "$hc_code" = "000" ] && [ "$hc_speed" -le "$EMERGENCY_SPEED_KBPS" ]; then
        # === 紧急: 完全不通 ===
        echo "$LOG_TAG 🚨 紧急: 代理不通 — 忽略冷却, 立即全量更新"
        full_update "emergency_down"

    elif [ "$hc_speed" -le "$MIN_SPEED_KBPS" ]; then
        # === 减速: 太慢 ===
        echo "$LOG_TAG ⚠ 减速: ${hc_speed}KB/s < ${MIN_SPEED_KBPS}KB/s"

        local cooldown=$((now - LAST_FULL_UPDATE))
        if [ "$cooldown" -lt "$FULL_UPDATE_COOLDOWN" ]; then
            echo "$LOG_TAG ⏳ 冷却中 (${cooldown}s < ${FULL_UPDATE_COOLDOWN}s) — 跳过"
            save_state
        elif [ "$UPDATE_COUNT" -ge "$MAX_UPDATES_PER_DAY" ]; then
            echo "$LOG_TAG 🛑 已达每日更新上限 ($MAX_UPDATES_PER_DAY) — 跳过"
            save_state
        else
            full_update "slow_${hc_speed}KBps"
        fi

    else
        # === 边缘: 勉强可用但不够好 ===
        echo "$LOG_TAG ⚡ 可用但偏慢 — ${hc_speed}KB/s"
        local cooldown=$((now - LAST_FULL_UPDATE))
        if [ "$cooldown" -gt "$FULL_UPDATE_COOLDOWN" ] && [ "$UPDATE_COUNT" -lt "$MAX_UPDATES_PER_DAY" ]; then
            full_update "degraded_${hc_speed}KBps"
        else
            save_state
        fi
    fi

    echo ""
}

main
