#!/bin/bash
# ============================================================================
# 一键部署: 防泄漏 + 用量监控 + 消费告警
# 在 Pi 上线后执行: bash deploy-monitoring.sh
# ============================================================================
set -e
PI_IP="${1:-192.168.0.191}"
PI_USER="pi"

echo "=== 1. 部署 API 用量监控 ==="
scp api-usage-monitor.sh ${PI_USER}@${PI_IP}:/home/pi/
ssh ${PI_USER}@${PI_IP} 'chmod +x /home/pi/api-usage-monitor.sh'

echo "=== 2. 部署 Sentinel (git pre-commit) ==="
ssh ${PI_USER}@${PI_IP} '
# 下载 Sentinel ARM64 二进制
curl -fsSL https://github.com/sentinel-cli/sentinel/releases/latest/download/sentinel-linux-arm64 -o /tmp/sentinel 2>/dev/null && chmod +x /tmp/sentinel && sudo mv /tmp/sentinel /usr/local/bin/sentinel && echo "Sentinel installed" || echo "Sentinel download failed — skip"

# 全局 git hook 模板
mkdir -p ~/.git-templates/hooks
cat > ~/.git-templates/hooks/pre-commit << '\''HOOK'\''
#!/bin/bash
# API key 检测 — 禁止提交含敏感信息的文件
patterns="sk-[a-zA-Z0-9]{20,}|ark-[a-z0-9]{20,}|Bearer [a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9]{20,}"
if git diff --cached --name-only | xargs grep -lPE "$patterns" 2>/dev/null; then
    echo "⛔ 检测到 API key! 请从文件中移除后再提交"
    echo "   匹配: sk-*/ark-*/Bearer */ghp_*/github_pat_*"
    exit 1
fi
HOOK
chmod +x ~/.git-templates/hooks/pre-commit
git config --global init.templateDir ~/.git-templates
echo "Git pre-commit hook installed"
'

echo "=== 3. 配置 cron ==="
ssh ${PI_USER}@${PI_IP} '
# 每15分钟检查用量
(crontab -l 2>/dev/null | grep -v "api-usage-monitor"; echo "*/15 * * * * /home/pi/api-usage-monitor.sh >> /var/log/api-monitor.log 2>&1") | crontab -

# 每周日 GitHub 全量扫描
(crontab -l 2>/dev/null | grep -v "weekly-key-scan"; echo "0 2 * * 0 /home/pi/weekly-key-scan.sh >> /var/log/key-scan.log 2>&1") | crontab -

echo "Cron updated"
crontab -l | grep -E "api-usage|key-scan"
'

echo "=== 4. 创建每周扫描脚本 ==="
ssh ${PI_USER}@${PI_IP} '
cat > /home/pi/weekly-key-scan.sh << '\''SCAN'\''
#!/bin/bash
# 每周 GitHub key 扫描
LOG="/var/log/key-scan.log"
echo "[$(date)] 开始 GitHub 全量 key 扫描..." >> "$LOG"
for repo in $(gh repo list L-ingqin12 --limit 50 --json name -q ".[].name" 2>/dev/null); do
    rm -rf "/tmp/scan-$repo" 2>/dev/null
    gh repo clone "L-ingqin12/$repo" "/tmp/scan-$repo" -- --depth 1 2>/dev/null || continue
    matches=$(grep -rnP "sk-[a-zA-Z0-9]{20,}|ark-[a-z0-9]{20,}|Bearer [a-zA-Z0-9_-]{20,}" "/tmp/scan-$repo/" \
        --include="*.sh" --include="*.md" --include="*.json" --include="*.yaml" --include="*.py" 2>/dev/null | \
        grep -v "node_modules\|.git/\|package-lock\|placeholder\|example\|<ARK\|<FEISHU")
    [ -n "$matches" ] && echo "⚠️ $repo: $matches" >> "$LOG"
    rm -rf "/tmp/scan-$repo"
done
echo "[$(date)] 扫描完成" >> "$LOG"
SCAN
chmod +x /home/pi/weekly-key-scan.sh
'

echo ""
echo "=== 部署完成 ==="
echo "组件:"
echo "  /home/pi/api-usage-monitor.sh    每15min用量检查+异常飞书告警"
echo "  /home/pi/weekly-key-scan.sh      每周日GitHub全量key扫描"
echo "  ~/.git-templates/hooks/pre-commit 阻止提交含key的文件"
echo "  sentinel                         备用(若下载成功)"
