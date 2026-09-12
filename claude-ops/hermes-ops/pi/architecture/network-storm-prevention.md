# 网络风暴防护方案

## 故障链路

WiFi省电休眠 → 代理超时 → hermes重试 → TCP连接堆积 → conntrack饱和 → 全网不可达

## 已部署 (4层)

| 层 | 措施 | 效果 |
|:--:|------|------|
| 1 | WiFi power_save off | 消除触发源 |
| 2 | api_max_retries: 1 | 连接风暴减67% |
| 3 | tcp_keepalive: 120s | 死连接2min清理 |
| 4 | tcp_fin_timeout: 30s | TIME_WAIT加速 |

## conntrack监控 (待加入proxy-guardian)

check_conntrack() {
    local max=$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo 65536)
    local count=$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo 0)
    local pct=$((count * 100 / max))
    if [ $pct -gt 80 ]; then
        sudo conntrack -D --state TIME_WAIT 2>/dev/null
        return 2  # critical
    fi
}

## 路由器建议

- 为Pi设静态DHCP
- 增大conntrack_max
- QoS限制单设备连接数
