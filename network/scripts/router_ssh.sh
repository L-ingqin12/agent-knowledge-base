#!/bin/bash
# router_ssh.sh — 小米 R4CM 路由器 SSH 包装器
#
# 【口令不再内嵌】
# 原版把口令明文写在 `-p "[已脱敏]"` 处，导致两处暴露：
#   ① 本地工作副本
#   ② 公开仓库（agent-knowledge-base）——且已进入 3 个 git 历史提交
# 现改为从环境变量或本机未跟踪文件读取，本文件中不含任何凭据。
#
# 【用法】
#   export ROUTER_SSH_PASS='<口令>'
#   bash scripts/router_ssh.sh '<远程命令>'
#
# 或把口令放进本机未跟踪文件（推荐，避免进 shell 历史）：
#   printf '%s' '<口令>' > ~/.ssh/router_pass && chmod 600 ~/.ssh/router_pass
#   bash scripts/router_ssh.sh '<远程命令>'
#
# 【为什么需要 legacy 加密套件】
# dropbear 0.52（R4CM 固件 2.14.87）与现代 OpenSSH 不兼容：
#   密钥免密不可用 → 只能口令登录；且必须显式启用下列旧算法。
#
# 【安全说明】
# - `StrictHostKeyChecking=no` 仅为兼容该老固件而保留；已实测其主机密钥稳定，
#   如需更严可改为 yes 并把指纹预置进 known_hosts。
# - 路径中的本机用户名由 kb-push 脱敏规则在推送时替换为 %USERPROFILE%，
#   本地文件保留真实路径以便直接运行。
set -eu

PASS_FILE="${ROUTER_PASS_FILE:-$HOME/.ssh/router_pass}"
if [ -n "${ROUTER_SSH_PASS:-}" ]; then
  SSHPASS_VALUE="$ROUTER_SSH_PASS"
elif [ -f "$PASS_FILE" ]; then
  SSHPASS_VALUE="$(cat "$PASS_FILE")"
else
  echo "router_ssh.sh: 缺少口令。请设置 ROUTER_SSH_PASS，或写入 $PASS_FILE" >&2
  exit 2
fi

SSH="/d/Users/%USERPROFILE%/AppData/Roaming/MobaXterm/slash/bin/ssh"
SSHPASS="[已脱敏]"
SSH_OPTS="-o KexAlgorithms=+diffie-hellman-group1-sha1 -o HostKeyAlgorithms=+ssh-rsa -o MACs=+hmac-sha1-96,hmac-sha1,hmac-md5 -o StrictHostKeyChecking=no -o ConnectTimeout=8"

exec "$SSHPASS" -p "[已脱敏]" "$SSH" $SSH_OPTS root@[IP已脱敏] "$@"
