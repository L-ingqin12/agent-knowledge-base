---
title: ds2ox-proxy 安全复核与退役归档
aliases: [ds2ox-proxy, ds2ox 归档, 模型路由代理退役, ds2ox-proxy-retirement]
tags: [ai/ops, incident, security]
created: 2026-09-12
updated: 2026-09-12
status: review
source: 本机 ~/.dsh/ds2ox-proxy.mjs（已脱敏归档）
---

# ds2ox-proxy 安全复核与退役归档

See also: [[deepseek-cache-key-and-sep-experiments]] | [[claude-flash-primary-analysis]] | [[claude-cache-relay-design]] | [[AGENTS]]

> [!abstract] 定位
> 记录 `~/.dsh/ds2ox-proxy.mjs`（本机模型路由改写代理）的**用途、路由行为、三处设计缺陷、脱敏归档位置与凭据处置建议**，并给出可追溯的配置来源。
> 归档正文：`scripts/claude-ops-deployments/ds2ox-proxy/ds2ox-proxy.mjs`（脱敏版，密钥外置）。
> 退役判定：**已无流量引用，属死代码**（证据见下）。

---

## 一、它是什么

一个**本地 HTTP 代理**（`127.0.0.1:8899`），把 DSH 的 `deepseek-official` 模型流量**改写路由**到 OpenRouter 上的免费模型，目的是绕开 deepseek 按量计费。

挂载方式是改写 `~/.dsh/settings.yaml`：

```yaml
llm-deepseek:
  baseURL: http://127.0.0.1:8899
```

关键机制：**`dsh-llm-deepseek` 逐请求重读 `settings.yaml`**，因此改配置即可切换路由，无需重启进程。

## 二、路由行为

| 条件 | 行为 |
|---|---|
| `POST /chat/completions` | 改写 `body.model` 后转发 OpenRouter（默认 `z-ai/glm-5.2:free`） |
| 上游 402/408/5xx/网络错误 | 回落 `api.deepseek.com`（透传原 body 与授权头） |
| 上游 429 | 原地退避重放（2.5s / 5s），仍 429 则换备用模型 `minimax/minimax-m3:free` |
| 窗口（5 条）满且成功率 < 0.4 | 熔断 3 分钟，期间全走 deepseek |
| `~/.dsh/ds2ox-proxy.disabled` 存在 | 全量旁路到 deepseek（软回滚开关） |
| `/anthropic/v1/messages` | 默认透传 deepseek（web_search 走此路径） |
| `~/.dsh/ds2ox-search.stub` 存在 | 返回空搜索结果（零成本） |

> [!info] 历史演进
> 目标模型多次随上游上下架调整：`stealth/ox-alpha` → 官方名为 `z-ai/glm-5.3-flash`（2026-08-26）→ 临时改 `z-ai/glm-5.2:free`。tokenra 网关路由已于 2026-08-26 移除。

## 三、三处设计缺陷（重新启用前必须修复）

> [!danger] D1 · 无入站鉴权
> 服务端**不校验任何凭据**。任何本机进程都能借用该代理发请求，或经它透传到带 `Authorization` 的 deepseek 上游。
> 修复：加随机 token 头校验。

> [!danger] D2 · 无 Host 头校验
> 存在浏览器侧 **DNS 重绑定 / 跨站请求**面。
> 修复：校验 `Host ∈ {127.0.0.1, localhost}`。

> [!danger] D3 · 抢占即劫持（最严重）
> `baseURL` 逐请求读取，因此**任何进程只要监听 8899 并伪装响应，就能在不触碰任何文件的情况下替换模型输出、窃取全部提示词与对话内容、注入工具调用**。
> 修复：改用 Unix domain socket，或加进程间共享密钥；端口改为非固定值。

## 四、退役判定与残留风险

| 检查项 | 结论 |
|---|---|
| `settings.yaml` 是否仍引用 8899 | **否**（`llm-deepseek` 段已移除，provider 为 `deepseek-official` 直连） |
| 进程是否在运行 | **否**（实测 8899 未监听，服务拒绝连接） |
| 日志最后活跃 | 2026-08-26 14:43 |
| git 历史是否含该硬编码密钥 | **否**（已用 `git log -S` 按完整密钥串核验，命中 0） |

> [!warning] 残留复活路径（这是本归档存在的主要理由）
> 两个**配置备份**仍保留指向代理的配置，任何一次「从备份回滚」都会把代理重新接上：
>
> ```
> ~/.dsh/settings.yaml.pre-upgrade:16          baseURL: http://127.0.0.1:8899
> ~/.dsh/settings.yaml.pre-flash-20260912:23   baseURL: http://127.0.0.1:8899
> ```
>
> 建议随代理一并清理，否则「以为已退役」与「实际可被一键复活」会长期并存。

## 五、脱敏处理

归档正文按本库既有范式（参见 `scripts/claude-ops-deployments/cache-relay/cache-relay.mjs` 的「**密钥不落地（透传头）**」，以及 deployment-log 2026-09-06 的 `authTokenSource` 做法）处理：

| 项 | 原文 | 脱敏后 |
|---|---|---|
| OpenRouter 密钥 | 第 24 行硬编码（明文，前缀 `sk-or-…`） | 环境变量 `DS2OX_PROXY_KEY`，缺失即拒绝启动 |
| 端口 / 监听地址 | 常量 8899 / 127.0.0.1 | 环境变量 `DS2OX_PROXY_PORT` / `DS2OX_PROXY_HOST`（默认值不变） |
| 目标模型 | 常量 | 环境变量 `DS2OX_PROXY_MODEL` / `..._BACKUP_MODEL` |

> [!success] 归档文件不含任何真实凭据
> 且**不建议直接重新运行**——文件头已加醒目退役警告与缺陷清单，但它仍含完整的路由逻辑，若被误启动且配置指向 8899，即恢复 D1–D3 全部风险。

## 六、凭据处置建议

原文件中硬编码的 OpenRouter 密钥**共出现在 2 处**，须一并处理：

| # | 位置 | 处置 |
|---|---|---|
| 1 | `~/.dsh/ds2ox-proxy.mjs:24` | 随该文件一并删除；密钥轮换 |
| 2 | `~/.dsh/settings.yaml:33`（`llm-pi-ai.providers.ox-openrouter.headers.Authorization`） | **当前仍在用**（GLM 备份路由）；轮换后同步更新 |

**推荐处置顺序**：

1. 先在 OpenRouter 控制台**轮换（rotate）**该密钥 —— 不要先删文件，避免中途失去可用凭据
2. 更新 `settings.yaml` 中的 `ox-openrouter` 授权头为新密钥并验证 GLM 路由可用
3. 删除 `~/.dsh/ds2ox-proxy.mjs` 与 `~/.dsh/ds2ox-proxy.log`
4. 删除 `settings.yaml.pre-upgrade` 与 `settings.yaml.pre-flash-20260912`（含 8899 引用；同时注意前者还含已失效的 tokenra 密钥 `sk-<REDACTED>…`）
5. 确认开关文件不存在：`~/.dsh/ds2ox-proxy.disabled`、`~/.dsh/ds2ox-search.stub`
6. 全盘复核是否还有其他副本（见 [[URL-REGISTRY]] 的密钥扫描入口）

> [!note] 关于「归档却不删原文件」的取舍
> 本库规范是**保留文件不删除（Graph 历史可追溯）**，但那条针对的是**知识文档**。对**含凭据的运行时脚本**，建议以「脱敏归档 + 删除原件 + 轮换密钥」为准——归档给出了可追溯性，删除消除了活体风险，两者不冲突。

## 七、配置来源（供日后追溯）

| 来源 | 说明 | 链接 |
|---|---|---|
| DSH settings 结构 | `llm-deepseek` / `llm-pi-ai` 段的含义与逐请求重读行为 | 本机 `~/.dsh/settings.yaml` 注释 |
| OpenRouter API | 上游端点与模型命名（`z-ai/glm-5.x`） | <https://openrouter.ai/docs> |
| DeepSeek 官方 API | 回落目标 `api.deepseek.com` 与 anthropic 兼容端点 | <https://api-docs.deepseek.com> |
| 既有中继实现 | 同类「密钥不落地」范式参考 | `scripts/claude-ops-deployments/cache-relay/cache-relay.mjs` |

## 八、关联文档

- [[deepseek-cache-key-and-sep-experiments]] —— 记录了本代理的拆解与「遗留可清理项」原始条目
- [[claude-flash-primary-analysis]] —— flash / ox-alpha 主模型切换分析
- [[claude-cache-relay-design]] —— 替代方案：cache-relay（8790，密钥不落地、有健康检查与回滚）
- [[proxy-cancelretry-hook-incident]]、[[claude-proxy-deployment-postmortem]] —— 本库其他代理事故复盘
- [[AGENTS]] —— 治理规范（部署四规则、敏感信息推送规则）
