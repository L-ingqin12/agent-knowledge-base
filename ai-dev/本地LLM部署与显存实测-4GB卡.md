---
title: 本地 LLM 部署与显存实测（4GB 卡）
aliases: [4GB显存实测, 本地LLM基准, Ollama实测, GTX1650跑大模型]
tags: [ai, ai/learning, reference]
created: 2026-09-19
updated: 2026-09-19
status: review
---

# 本地 LLM 部署与显存实测（4GB 卡）

> [!abstract] 一句话
> 在 **GTX 1650 4GB** 笔记本上把本地 LLM 跑起来的完整实测账本：**哪些模型真能跑、跑多快、坑在哪**。
> 全部数字为亲手实测（含重复测量），非估算；估算与实测的差异也一并记录。

> [!info] 相关文档
> 机制层（量化/批处理/PagedAttention）见 [[LLM推理部署与量化]]；多模态管线见 [[多模态Agent平台实战]]；
> 本地模型接入 Agent Harness 见 [[Claude-Ops-KB-Home]] 一系的运维实践。
> 本地判断失误已录入 [[CORRECTIONS]]（C-026 / C-027 / C-028）。

## 一、硬件约束（先看这两条，比显存更致命）

| 约束 | 实测值 | 影响 |
|---|---|---|
| 显存 | 4GB（**Ollama 实际只用得到 3.2 GiB**） | 桌面/WDDM 吃掉 0.8GB |
| **BF16** | ❌ 不支持（Turing SM 7.5，需 Ampere 8.0+） | 多数新模型默认 BF16 |
| **FP8** | ❌ 不支持（需 Ada SM 8.9+） | **砍掉 2026 年主流低显存优化路径** |
| 支持精度 | FP32 / FP16 / INT8 / INT4 | 只剩 GGUF 量化一条路 |
| 内存 | 31.85 GB（实测空闲 16.6 GB） | MoE 走 CPU 的资本 |
| CPU | i7-9750H 6C/12T | prefill 算力瓶颈 |
| 显存带宽 | GDDR5，约 128 GB/s | decode 上限的分母 |

## 二、部署坐标

| 项 | 值 |
|---|---|
| 运行时 | Ollama **0.34.2**（装时 0.34.1，后自动更新），per-user 装 `%LOCALAPPDATA%\Programs\Ollama` |
| 模型目录 | **`D:\OllamaModels`**（环境变量 `OLLAMA_MODELS` 改的，默认在 C 盘） |
| 基准脚本 | `D:\OllamaModels\bench\`（含 README、客户端、压测脚本） |

用户级环境变量（`setx` 写入，**必须先设再重启 Ollama**）：

```
OLLAMA_MODELS=D:\OllamaModels     OLLAMA_KV_CACHE_TYPE=q8_0
OLLAMA_CONTEXT_LENGTH=32768       OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1             OLLAMA_FLASH_ATTENTION=1
```

> [!danger] 安装坑：静默安装不改 PATH
> `OllamaSetup.exe /S` **不会把安装目录写进 PATH**，导致托盘程序 `ollama app.exe` 找不到 `ollama.exe` 去 spawn 服务端子进程，
> 日志永远报 `ollama server not ready`、11434 零监听——而手动 `ollama serve` 却秒起，极易误判为「Ollama 坏了」。
> 修复=把安装目录追加进用户 PATH。**改 PATH 必须用 `[Environment]::SetEnvironmentVariable('Path',$v,'User')`，不能用 `setx`（1024 字符处会截断）。**

> [!danger] 安装途径：本机 **winget 装不上**，但那不代表 Ollama 装不上
> winget 装 Ollama 报 **`0x80072efd`**——它的下载源指向 GitHub，被墙。
> 可靠路径是三步，**缺一不可**：
> 1. 走本机 SOCKS 代理下载官方安装包
>    （`curl --socks5-hostname 127.0.0.1:10808 -L -o OllamaSetup.exe <官方 release url>`）
> 2. **必须校验 SHA256**：从 `api.github.com` 取该 release 的 digest 做比对，不要凭大小猜
> 3. 再执行安装，然后处理上面那条 PATH 坑
>
> ⚠️ **403 / 连不上 ≠ 资源不存在**，八成只是没走代理。本机多次因为"默认抓不到"而误判过。

> [!info] 模型下载
> `ollama pull <模型名>`。模型落在 `OLLAMA_MODELS` 指向的目录（本机 **`D:\OllamaModels`**，不是 C 盘默认位置）。
> 下载慢或超时同样与网络有关，处理方式同上。拉下来的清单见 [[本地模型能力矩阵与任务路由]]。

## 三、实测性能总表

| 模型 | 体积 | 驻留 | decode | prefill(5.7K) |
|---|---|---|---|---|
| `qwen3.5:0.8b` | 1.0 GB | **100% GPU** | **81 tok/s** | **916 tok/s** |
| `qwen3-vl:2b`（视觉） | 1.9 GB | 80%→100%(强制) | **78.6 tok/s** | 338 tok/s |
| `qwen2.5-coder:3b` | 1.9 GB | 100% GPU | 49.8 tok/s | 196 tok/s |
| `granite4:micro-h` | 1.9 GB | 100% GPU | 42 tok/s | 170 tok/s |
| `qwen3.5:2b` | 2.7 GB | 63%→**100%**(强制) | 43.4 tok/s | 393 tok/s |
| `granite4:tiny-h`（MoE） | 4.2 GB | 49%/51% | 18.6 tok/s | 90 tok/s |
| `gpt-oss:20b`（MoE） | 13 GB | 84%/16% | 7.6 tok/s | 85 tok/s |

### 关键调优：`num_gpu: 999`

> [!tip] 单条最值钱的经验
> Ollama 的**自动分层过于保守**。`qwen3.5:2b` 被切成 63% GPU，实测强制 `num_gpu: 999` 后**完全放得下**（3307/4096 MiB），
> 解码从 24.7 → **43.4 tok/s（1.76x）**。装得下的模型（0.8b）不受影响；装不下的**一定要加**。

### 逐模型烤入参数（`ollama create` 同名覆盖）

**关键认识**：`OLLAMA_CONTEXT_LENGTH` 是**全局默认**，但两件事让它不该被当成唯一的旋钮——

1. **模型的 `PARAMETER num_ctx` 会覆盖它**（实测：全局 32768 下，烤了 16384 的模型实测就是 16384）
2. **不同模型的"黄金档"差很多**：同一个 32768 对 A 零代价、对 B 掉 36%、对 C 掉 2.7 倍

**做法**：`printf 'FROM <模型名>\nPARAMETER num_ctx <N>' | ollama create <同名> -f -`
—— 用 `FROM <模型名>` 会**继承原有 TEMPLATE / RENDERER / PARSER / 采样参数**，只叠加你要改的。
（已实测：7 个模型覆盖后这些片段均未丢失。改前先 `ollama show --modelfile <模型> > 备份` 即可还原。）

**`num_ctx` 对速度的影响实测**（decode tok/s，括号为 GPU 占比）：

| 模型 | 4K | 8K | 16K | 32K | 选定 |
|---|---|---|---|---|---|
| `granite4:micro-h` | 30.5 (100%) | 29.9 (100%) | 38.7 (100%) | **38.6 (100%)** | **32768** |
| `qwen2.5-coder:3b` | 44.1 (100%) | 44.6 (100%) | **43.9 (100%)** | 28.2 (79%) | **16384** |
| `qwen3.5:0.8b` | 64.9 | 66.4 | **62.8** | 63.7 | **16384** |
| `qwen3.5:2b` | — | 16.9 (63%) | 16.5 (61%) | 14.3 (55%) | **16384** |
| `qwen3-vl:2b` | **70.1 (100%)** | 46.2 (80%) | 25.7 (64%) | — | **8192** |
| `granite4:tiny-h` | 31.0 (51%) | 30.0 (51%) | 27.3 (50%) | — | **8192** |

**调优前后对比**（同机同提示词，复测确认）：

| 模型 | 调优前 | 调优后 | 变化 | 原因 |
|---|---|---|---|---|
| `qwen3.5:2b` | 16.9 | **35.8** | **+112%** | 烤入 `num_gpu 999` 强制满 GPU |
| `qwen3-vl:2b` | 25.7 | **46.6** | **+81%** | 上下文 16K→8K，GPU 64%→80% |
| `qwen2.5-coder:3b` | 28.2 | **40.4** | **+43%** | 上下文 32K→16K，GPU 79%→100% |
| `qwen3.5:0.8b` | 63.7 | **67.0** | 持平 | — |
| `granite4:micro-h` | 38.6 | 37.6 | 持平 | 32K 本就无代价 |

> [!warning] 两个容易踩的坑
> 1. **`num_ctx` 不是越大越好**。`qwen3-vl:2b` 在 4K 时 70 tok/s、16K 时只有 25.7——**差 2.7 倍**。它的视觉编码器常驻显存，留给 KV 的预算很少。
> 2. **`gpt-oss:20b` 的上下文不影响速度**（8K 与 16K 都约 5–6 tok/s，16% GPU），因为它本来就是 CPU 为主的 14GB 模型。别为它调上下文，调不动。
>
> ⚠️ 与 DSH 的张力：DSH 路由声明 `contextWindow: 32768` 才能算出正常预算，但**模型实际只服务 16K/8K**。
> 真实提示词约 5–6k token，日常够用；**超长会话会被 Ollama 静默截断而 DSH 来不及压缩**。
> 要保 DSH 长会话保真，就把该模型的 `num_ctx` 也设 32768（代价按上表算）。

### 长对话体感（每轮回复 400 token）

| 模型 | 上下文增长 | 首字延迟 | 单轮耗时 | 劣化 |
|---|---|---|---|---|
| `qwen3.5:0.8b` | 24 → 8028 tok | 0.3 → 1.1 s | 5.3 → 6.9 s | **几乎无** |
| `granite4:micro-h` | 55 → 6058 tok | **稳定 0.3 s** | ~10 s | **几乎无** |
| `qwen3.5:2b` | 24 → 5939 tok | 1.3 → 1.6 s | ~11 s | **几乎无** |

> [!warning] 别被「首 token 延迟」吓到——要分清冷启动与多轮
> 上表 prefill 列的 6～71 秒是**冷启动贴一份 5.7K 长文档**的延迟。
> **日常多轮对话不会这么慢**：上下文被 KV 缓存，每轮只需 prefill 新增的几百 token，实测首字 0.3～1.6 秒。
> 真正的坏消息是**长文档摘要 / RAG 的首轮**——那才是 60～110 秒的真实场景。

## 四、MoE 走 CPU 的真相

> [!success] MoE 是被低估的选项
> `granite4:tiny-h`（7B-A1B，仅 1B 激活）纯 CPU 跑出 **17.2 tok/s**；
> 而同等体积的**稠密** 7B 模型估算只有 3.5–5 tok/s —— **差 3–5 倍**。低激活参数直接换成速度。

> [!bug] 但给 GPU 几乎没用
> 同一模型三种配置实测：自动分层 **18.6** / 纯 CPU **17.2** / 强制满 GPU **18.5** tok/s —— **差别在噪声范围内**。
> 原因：MoE 每 token 只读激活的专家权重，瓶颈是**内存带宽而非算力**，而 4.2GB 根本装不进 4GB 卡。
> **结论：别为 C 档 MoE 折腾显存调优。**

## 五、多模态（看图）已可用

`qwen3.5` 系列本身支持图像输入；`qwen3-vl:2b` 是专职视觉模型且解码最快。用自制测试图（左上红圆 / 右上蓝方 / 底部 3 绿块）验证：

| 模型 | 左上 | 右上 | 数绿块 | decode |
|---|---|---|---|---|
| `qwen3-vl:2b` | ✅ | ✅ | ✅ **三个** | **78.6 tok/s** |
| `qwen3.5:2b` | ✅ | ✅ | ✅ 三个 | 43.4 tok/s |
| `qwen3.5:0.8b` | ✅ | ✅ | — | 81 tok/s |

调用（原生端点，base64 放进 `images`）：

```python
requests.post("http://127.0.0.1:11434/api/chat", json={
    "model": "qwen3-vl:2b", "stream": False, "think": False,
    "messages": [{"role": "user", "content": "描述这张图", "images": [b64]}]})
```

## 六、本地 API 与接入 Agent Harness

| 端点 | 用途 |
|---|---|
| `http://127.0.0.1:11434/v1` | **OpenAI 兼容**——接现成工具（base_url 填此，api_key 任意非空） |
| `http://127.0.0.1:11434/api` | 原生——支持 `think` 开关、`num_gpu` 等独有参数 |

### ⚠️ 最大的坑：thinking 会吃光 token 预算

> [!danger] 同一个问题差 41 倍
> `qwen3.5` 是 thinking 模型，**先输出一大段思考再吐正文**。实测同一中文问题：
>
> | 方式 | content | token | 耗时 |
> |---|---|---|---|
> | `/v1` 端点（思考开） | 空（预算耗尽） | 2449 | **106.8 秒** |
> | 原生端点 `think:false` | 正常 | **57** | **2.6 秒** |
>
> **而 `/v1` 端点无法关闭思考**（`think:false` 与 `/no_think` 提示词实测均不生效）。
> 所以：走 `/v1` 用**非思考模型**（granite 系列 / qwen2.5-coder / qwen3-vl）；用 `qwen3.5` 就走原生端点传 `think:false`。

**接入 DSH（DeepSeek Harness）**：`@deepseek-ai/dsh-llm-pi-ai` 支持路由到「OpenAI 兼容网关或自托管服务器」，
在 `~/.dsh/settings.yaml` 的 `llm-pi-ai.providers` 下加一条路由即可。

> [!bug] 自定义路由**必须自带凭据**（文档措辞易误读）
> pi-ai 文档说"省略 `apiKeyEnv` 会让路由保持 configured-but-keyless，**交由 pi-ai 提供方原生的环境发现**"——
> 但那个回退**只对目录内置路由成立**。自定义路由省略凭据会直接报
> `turn error · No API key for provider: <路由名>`。
> **修法**：加 `headers.Authorization: "Bearer <占位值>"`（Ollama 不校验，占位即可）——同 `ox-openrouter` 那条的写法。

### 接入 Agent Harness 时的上下文预算（实测）

> [!success] 真实根因（2026-09-19 录包定位 + 端到端验证）
> **故障**：每轮都报 `turn max-tokens`、`content` 为空、`outputTokens: 1`。
>
> **真因**：DSH 的发包预算公式是
>
> ```
> 发出的 maxTokens = min(路由配的 maxTokens, contextWindow − 提示词估算)
> ```
>
> **而它的"提示词估算"包含 34 个工具的 JSON schema（实测 38,653 字符 ≈ 16.6k token）。**
> 窗口声明 16384 ⇒ 剩余 = 16384 − 16559 = **负数** ⇒ 钳到 **1**
> ⇒ Ollama 只生成 1 个 token ⇒ `finish_reason: length` ⇒ 界面报 `turn max-tokens`。
>
> **修法**：`contextWindow` 与 Ollama 的 `OLLAMA_CONTEXT_LENGTH` **同时**提到 **32768**。
> 改后录包实测 `max_completion_tokens` 从 **1 → 12288**，端到端跑通。
>
> **两组数据完全吻合公式**（这是它可信的依据）：
>
> | 场景 | 提示词估算 | 窗口−估算 | min(配的, 剩余) | 实测 |
> |---|---|---|---|---|
> | 无工具 | ~5,700 | 10,684 | min(4096,10684) | **4096** ✅ |
> | 34 工具 | ~16,559 | **−175** | → 钳到 | **1** ✅ |

> [!warning] 各模型能全量驻留 GPU 的最大上下文（实测）
>
> | 模型 | 8K | 16K | 32K | 64K |
> |---|---|---|---|---|
> | `granite4:micro-h` | 100% | 100% | **100%** | 81% |
> | `qwen2.5-coder:3b` | 100% | 100% | 79% | — |
> | `qwen3-vl:2b` | 80% | 64% | **45%** | — |
>
> ⚠️ **32K 是有代价的**：`qwen3-vl:2b` 从 80% 掉到 **45% GPU**（大量层卸载到 CPU，实测一次请求
> 10 分钟不返回）。所以 **DSH 路由里只放 `granite4:micro-h` / `qwen2.5-coder:3b` / `gpt-oss:20b`**，
> 视觉模型走原生端点并显式传较小的 `num_ctx`。

> [!danger] 三个被推翻的中间结论（**保留记录，因为它们看着都很有说服力**）
> 这个故障我连续判错**三次**，每次都是"抓到一个现象就当成根因"，没做「只改一个变量看它变不变」的对照。
>
> | # | 当时的判断 | 为什么错 |
> |---|---|---|
> | 1 | 空函数名 ⇒ **3B 模型能力不足，产不出合法 tool_call** | 空函数名只是「预算被钳到 1 个 token」的**另一个症状**——模型连工具调用语法都吐不完。窗口修好后 `granite4:micro-h` 产出 `name="ask_user_question"`、参数可解析 ✅ |
> | 2 | 抓包见 `max_completion_tokens: 1` ⇒ **就是这个字段** | 实测 **Ollama 完全忽略 `max_completion_tokens`**（发 1 得 38 token、发 5 得 48 token）。它不可能是成因 |
> | 3 | 把 `maxTokens` 从 4096 提到 12288 ⇒ **预算被工具开销吃光** | 改后 `max_completion_tokens` **仍是 1**。方向（工具开销）对了，但**变量选错了**——该改的是 `contextWindow` 而不是 `maxTokens` |
>
> **真正让答案浮出来的动作**：对比**两次 `n_tools` 不同**的抓包（0 个工具 → 4096；34 个工具 → 1）。
> 差异一出现，相关变量立刻现形。**做对照比做推理快。**

> [!tip] 可复用的诊断手法
> 1. **卡在"看不到对方发了什么"时，就造一个看得见的中间人。** 本次最终靠一个
>    **记录+转发代理**（DSH → 本地代理 → Ollama，双向报文落盘）一次拿到全貌。
>    先用回声服务器（只录不发）排除了"是 Ollama 坏了吗"，再用转发代理定位。
> 2. **本地复现不出、但对方稳定复现时，大概率是"对方那一侧的状态"**（本次是 DSH 自己的
>    上下文估算），不是被测服务的问题。
> 3. **改配置时一次只改一个变量。** 我同时改了 `reasoningEfforts`、`maxTokens`、`contextWindow`，
>    三次误判都源于此——改对了也不知道是哪个生效。

## 六·五、一行式本地推理入口 `llm`

定位：**把「小、碎、重复」的推理任务从远端模型卸载到本机**（省远端 token 与长任务成本）。
脚本：`D:\OllamaModels\bin\llm.py` + `llm.cmd`（建议把 `bin` 加进 PATH）。

```bash
llm "用一句话解释什么是向量数据库"          # fast 档，约 0.7s
git diff | llm "写一条 commit message"      # 管道 + 指令（核心用法）
llm -t coder "写个判断闰年的函数"
llm -t vision -i shot.png "这个报错是什么"
llm --json -q "..."                          # 附带用时/速度统计
llm --list                                   # 用途别名
```

用途别名 → 模型：`fast`(qwen3.5:0.8b) / `chat`(granite4:micro-h) / `smart`(qwen3.5:2b) / `coder`(qwen2.5-coder:3b) / `moe`(granite4:tiny-h) / `vision`(qwen3-vl:2b)

### 三个实测踩出来的设计要点

> [!success] 思考模型的「关思考」——分三类，搞混会反噬
>
> | 模型族 | 正确做法 | 依据 |
> |---|---|---|
> | `qwen3.5` | 原生端点传 `think:false` **就够**（**别再塞 prefill**，否则模型把字面量 `<think>` 当正文吐出来——实测翻车） | 实测 |
> | `qwen3-vl` | 模板里 `<think>` 是**无条件写死**的，`think:false` 压不住。必须 `think:true` + **末尾预填一个已闭合的空 think 块** | 实测：18.7s→1.3s，thinking 归零 |
> | `gpt-oss` | `think` **只认 low/medium/high 字符串，传 true/false 被忽略**。未传时模板默认注入 `Reasoning: medium`。默认给 `low` | 实测 think=low 把 thinking 从 123 压到 20、4.7→7.2 tok/s |
>
> **为什么 `/no_think` 怎么试都没用**：ollama 二进制里 grep `no_think` **零命中**——它根本不认这个串。
> 而且 **Qwen 官方已声明 Qwen3.5 不再支持 `/think` `/nothink` 软开关**。

> [!bug] `qwen3-vl:2b` 是一个已知未修 Ollama bug 的原案模型
> Issue **#17978**（open）：parser 状态机进入 `CollectingThinking` 后，**若模型不吐 `</think>`，
> 整段生成（含最终答案）都被归为 thinking，`Message.Content` 恒为空**。
> 机理见 PR **#18187**，上游修复未进 0.34.2。
> **上面那个「预填已闭合 think 块」正是绕过它的手段**——维护者给的官方绕过方案也是同一机制。

> [!warning] `FROM <模型名>` 会**继承**现有参数，删不掉
> 想把烤进去的参数**去掉**（比如我试错的 `num_batch`），只写 `FROM <同名模型>` 是**无效的**——
> 它会连同旧参数一起继承。必须 **`FROM <blob 路径>`** 重建，或直接还原备份的完整 Modelfile。
> 另外只取备份的 `FROM` 行会**丢掉 TEMPLATE**（实测把 granite4 的消息模板弄没了）。

### 其他实测结论

- **`num_batch` 调优是死路**：`granite4:micro-h` 默认 35.3 tok/s；`256`→34.2、`1024`→28.4、**`2048`→19.1（掉 46%）**。默认值即最优。
- **gpt-oss 官方采样参数**：OpenAI 只推荐 `temperature=1.0, top_p=1.0`（README 原文），无 top_k/min_p 建议；Ollama 的 registry params blob 也只设 `temperature:1`。
- **Qwen3.5 官方推荐**（HF 模型卡原文）：非思考·文本 = `temp 1.0 / top_p 1.00 / top_k 20 / min_p 0 / presence_penalty 2.0`。
  ⚠️ Qwen 官方说 **0.8B/2B 默认应是 non-thinking**，而 Ollama 给它们配的是 **thinking 档参数**；官方还**点名这两款在 thinking 下容易陷入死循环**。
- **管道用法有个坑**：不能写成「有提示词就不读 stdin」——那样 `git diff | llm "写 commit"` 会**静默丢掉管道内容**（实测模型反过来问用户"请提供原文"）。

## 七、视频生成：本机不可行

> [!danger] 量级上不够，不是「慢一点」
> - 无 BF16、**无 FP8** —— 2026 年主流低显存视频方案几乎都建立在 FP8 上
> - 唯一候选 `Wan 2.1 T2V-1.3B` GGUF Q4 需 4–6GB，本机 3.2GB 压线
> - 第三方在 GTX 1650 4GB 实测：**256×256，约 1 分钟/帧，评级 F**
> - [WanGP](https://github.com/deepbeepmeep/Wan2GP)（专为穷显卡、支持 MiniMax H3）标称**最低 6GB**，仍超
>
> 换算：5 秒视频（16fps = 80 帧）≈ **80 分钟**，只有 256×256。建议走 API 或云 GPU。

## 八、测量方法论（踩过的坑）

> [!warning] 这三条是本次实测翻车换来的，详见 [[CORRECTIONS]]
> 1. **单次测量不可信**——某模型首轮测出 36.0 tok/s，复测两轮是 18.7 / 18.5，那个 36.0 是假象（[[CORRECTIONS#C-026 拿单次测量当可复现结论]]）
> 2. **别把自己工具的缺陷当成被测对象的缺陷**——中文「乱码」实为 bash+curl 编码问题，我一度归因到 GPU 内核（[[CORRECTIONS#C-027 把自己工具的缺陷当成被测对象的缺陷]]）
> 3. **基准会被服务端缓存污染**——Ollama 按**最长公共前缀**缓存 KV，cache-busting 的随机串**必须加在提示词开头**，加末尾测出过「419 万 tok/s」（[[CORRECTIONS#C-028 基准测量被服务端缓存污染]]）

其他可复用的实测细节：

- `/api/ps` **没有 `processor` 字段**（那是 CLI 自己算显示的），要用 `size_vram / size` 推算 GPU 占比
- 用 bash+curl 传非 ASCII 文本给模型会因编码问题让模型收到乱码，**测中文必须用 Python 显式 UTF-8 编码**发请求

## 九、选型速查

| 需求 | 用哪个 |
|---|---|
| 日常对话（最快） | `qwen3.5:0.8b`（走**原生端点**关思考） |
| 对话 + 看图 | `qwen3-vl:2b` 或 `qwen3.5:2b`，**原生端点** + `think:false` + 较小的 `num_ctx` |
| 接进 DSH 当 agent 后端 | `granite4:micro-h`（最快）/ `qwen2.5-coder:3b` / `gpt-oss:20b`，**路由 `contextWindow` 必须 ≥32768** |
| 代码补全 | `qwen2.5-coder:3b` |
| 接入 OpenAI 兼容工具链 | `granite4:micro-h`（非思考） |
| 长文档 / RAG | **换机器或走 API** |
| 视频生成 | **换机器或走 API** |

---

回链：[[AI-Dev-KB-Home]]（本子库 MOC） · [[本地推理栈探测与调优方法论]]（这些结论是**怎么测出来的**：探针设计/对照原则/录包法） · [[Ollama本地推理脚本集|Ollama 脚本集]]（配套脚本与**还原机制**） · [[LLM推理部署与量化]]（机制层） · [[多模态Agent平台实战]] · [[CORRECTIONS]]（本次错误记录 C-026~C-029）
