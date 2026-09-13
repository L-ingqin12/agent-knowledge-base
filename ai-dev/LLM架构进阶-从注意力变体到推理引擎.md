---
title: LLM架构进阶-从注意力变体到推理引擎
aliases: [LLM进阶, 注意力变体, 推理系统]
tags: [ai/learning, ai]
created: 2026-08-26
updated: 2026-09-13
status: review
source: 论文与官方技术报告共识（FlashAttention/GQA/MLA/DeepSeek-V2V3、vLLM PagedAttention、Orca、GPTQ/AWQ/SmoothQuant）；前沿条目标待确认
fetched_at: 2026-08-26
---

# LLM 架构进阶：从注意力变体到推理引擎

> [!abstract] 定位
> [[AI大模型开发]] 手推导图的进阶续篇：现代 LLM 的结构决策（注意力变体/长上下文/MoE）与推理系统工程化（KV cache 数学、连续批处理、投机解码、量化）。每节回答"为什么这样设计"而非罗列名词。服务化实操在 [[LLM推理部署与量化]]，训练侧在 [[强化学习对齐-RLHF到GRPO]]。

See also: [[CS-KB-Home]] · [[深度学习算法基础]] · [[向量数据库与检索]] · [[AI-Dev-KB-Home]]

## 一、注意力变体：KV cache 压力驱动的演化

### 为什么变体存在：先算账
```
KV cache 显存 = 2 × layers × kv_heads × head_dim × seq_len × batch × bytes
例: 32层×32头×128维×4K seq×1 batch×fp16 = 2×32×32×128×4096×2B ≈ 2.1GB / 序列
长上下文×并发时, KV 而非权重成为显存杀手 → 所有变体都在压 kv_heads
```

| 变体 | 机制 | 代价 | 代表 |
|------|------|------|------|
| MHA | Q/K/V 各自多头 | 基线 | 原始 Transformer |
| MQA | 所有 Q 头共享 1 组 KV | 质量损失明显 | 早期 PaLM 类 |
| **GQA** | Q 分组共享 KV(如 8 组) | 质量≈MHA、显存∝组数 | Llama2-70b+/绝大多数现代模型 |
| **MLA**(DeepSeek) | KV 压成低秩隐向量, 解码时上投影 | 显存压缩一个量级+质量保持；实现复杂 | DeepSeek-V2/V3 |

直觉：GQA 砍"头数"，MLA 直接改"存储基"。选型看推理栈支持度——vLLM/SGLang 对 MLA 支持滞后于 GQA（版本相关**待确认**）。

> [!success] 残余复核（2026-09-13）：「滞后于 GQA」**判定为过时表述，就地订正**（原句保留如上）。依据（本机直查上游仓库内容接口，HTTP 200，查询于 2026-09-13；引 PyPI 当期版本 vllm `0.29.0` / sglang `0.5.19`）：
> - **vLLM 主干** `vllm/v1/attention/backends/mla/` 是一个**独立的 MLA backend 包**，内含 20+ 文件：`flashmla.py`、`flashattn_mla.py`、`flashinfer_mla.py`、`cutlass_mla.py`、`triton_mla.py`、`amx_mla.py`、`cpu_mla.py`、`rocm_aiter_mla.py`，另有 `*_sparse.py` 系与 `prefill/` 子目录；
> - **SGLang 主干** `python/sglang/srt/layers/attention/` 同样有 `flashmla_backend.py`、`flashinfer_mla_backend.py`、`trtllm_mla_backend.py`、`cutedsl_mla_backend.py`、`tokenspeed_mla_backend.py`、`hip_flash_mla.py`、`swa_mla_fallback/`，并有针对 DeepSeek-V4 的 `deepseek_v4_backend.py` 与 `dsv4/` 目录。
> **准确表述**：MLA 不被通用 attention kernel 覆盖、必须走**各引擎的专用 backend**（这是它与 GQA 的真实差别，选型时仍要看 backend 支持矩阵），但两家均已内置多个 MLA kernel，「滞后于 GQA」不再成立。
> **残余（仍开放）**：新代模型的 MLA 变体（如 sparse MLA）跟进速度仍逐版本漂移，判据见 §六 ①。
> 依据：`api.github.com/repos/vllm-project/vllm`（HEAD `b7e0cdac5d11`，2026-09-13）、`api.github.com/repos/sgl-project/sglang`（HEAD `6220f45d8e9a`，2026-09-13）。

## 二、长上下文：位置编码外推

- RoPE 是旋转位置编码：绝对位置→QK 内积中的相对旋转角
- 直接换算超训长度会崩（高频角度未见分布）→ 三代方案：
  1. **PI 线性插值**：位置整体除以缩放因子 s——高频信息被压扁
  2. **NTK-aware 缩放**：改 base 频率而非线性插值，高低频区别对待
  3. **YaRN**：按频段分段插值+注意力温度补偿——当前主流口径
- 训练期决定上限：宣称 128K 的模型其有效上下文(needle 通过率)常低于标称——评测见 RAG 课程检索章节的交叉印证（**2026-09-13 补出处**：该断言的一手来源为 RULER——官方仓库并列给出 Claimed Length / Effective Length 两列并以定性阈值判定，原文「only half of them can effectively handle sequence length of 32K by exceeding a qualitative threshold…」；详见 §六 ②的残余复核）

## 三、MoE：稀疏激活的工程真相

```
router(x) → softmax 打分 → Top-K 专家(典型 k=2/8) → 加权组合输出
```

- 参数多≠计算多：总参=全部专家，激活参=路由到的 k 个——容量与算力解耦
- 三大工程问题：
  1. **负载不均**：router 塌缩到少数专家 → aux loss(负载均衡) + noise routing
  2. **专家容量溢出**：token 超专家容量被丢弃(dropped) → capacity factor 调参
  3. **all-to-all 通信**：专家分布式放置后每层两次全互联——EP 并行的通信墙（对照 [[LLM推理部署与量化]] 并行章节）
- 共享专家(DeepSeek)+细粒度专家是当前配方主流

## 四、推理系统：两阶段的不对称性

| 阶段 | 性质 | 瓶颈 | 对策 |
|------|------|------|------|
| Prefill(整 prompt 一次前向) | 计算密集(AI 高强度) | 算力 | chunked prefill 与解码交错 |
| Decode(逐 token) | 访存密集(每步读全 KV/权重) | **带宽** | 连续批处理摊薄 |

Roofline 视角（[[计算机组成原理]] §七）：decode 算术强度低→在带宽墙下运行→**批越大单 token 成本越低**——这是所有推理引擎优化的第一性原理。

### 连续批处理 + PagedAttention
- 传统 static batching：整批等最长序列完成，GPU 大量空转 → **Orca 式迭代级调度**：每个 decode step 重新组批，完成即出队、新请求即插入
- KV 显存的碎片问题：按 seq 预留连续空间→内部+外部碎片 → **PagedAttention**：KV 切 block 页表化管理(类虚拟内存)，碎片近零、copy-on-write 支持 beam/前缀共享(prefix caching 命中率是新指标)

### 投机解码（speculative decoding）
```
小草稿模型连猜 γ 个 token → 大模型一次并行验证 → 按接受长度回退修正
数学保证: 采样分布与大模型单独采样完全一致(拒绝采样构造)
加速 ≈ (1-α^(γ+1))/(1-α) · c , α=草稿接受率
```
适用条件：验证并行收益 > 草稿开销；α 高的任务(代码/模板文本)收益最大。Medusa/self-speculation 变体省独立草稿模型（成熟度**待确认**）。

> [!success] 残余复核（2026-09-13）：**「省独立草稿模型」成立**；但代表实现的**命名按当期上游口径订正**，成熟度一项**仍开放**（原句保留如上）。依据（上游仓库直查，HTTP 200，2026-09-13）：
> - vLLM 主干 `vllm/v1/spec_decode/` 确有 `medusa.py`，且 `medusa` 在模型注册表内——**代码路径存在**；
> - 但 vLLM 官方《Speculative Decoding》文档的**方法对照表里没有 Medusa 条目**，其列出的免独立草稿方案是 **MLP speculator**（原文「Medium to high gain / Medium gain / Good when compatible MLP speculators are available.」）与 **MTP**；表中唯一带实验性标记的是 **Custom Proposer**（原文「Bring your own proposer class (experimental).」），Suffix decoding 的说明为「No extra draft model; dynamic speculation depth.」；
> - SGLang 主干 `python/sglang/srt/speculative/` **无 Medusa 模块**（只有 `eagle_*` / `ngram_*` / `*mtp*` / `dflash_*` / `uno_*` 等）。
> **处置**：按上游方法名表述为「MLP speculator（Medusa 式多头即此族）/ MTP / EAGLE / N-gram / Suffix decoding 等免独立草稿模型的变体」，不再以「Medusa」作代表名。
> **残余判据**：逐引擎的成熟度分级本库未取得可引用标签——若需断言，须在上游文档中核到显式 `experimental/beta` 标记；命令 `curl -s https://api.github.com/repos/<org>/<repo>/contents/<spec_decode_path>`，期望看到对应 proposer 文件与其在文档方法表中的收益行。
> 依据：`api.github.com/repos/vllm-project/vllm`（HEAD `b7e0cdac5d11`）、`api.github.com/repos/sgl-project/sglang`（HEAD `6220f45d8e9a`）、vLLM 文档 `https://docs.vllm.ai/en/latest/features/speculative_decoding.html`（HTTP 200，均 2026-09-13）。

## 五、量化在栈里的位置

| 方案 | 类型 | 思路 |
|------|------|------|
| GPTQ | 权重 W4A16 | 基于 Hessian 的逐层误差补偿 OBQ 近似 |
| AWQ | 权重 W4A16 | 按"激活幅度"保护显著权重通道，免反传 |
| SmoothQuant | W8A8 | 把激活 outlier 的尺度迁到权重(migrate)，整型化 |
| FP8(E4M3/E5M2) | 前沿硬件原生 | H100+ 训推直用，配 per-tensor scale |

选型锚点：显存不够才量化；W4A16 主流落地质量损耗 <1% 困难任务除外——**必须带自家 eval 回归**（呼应 [[agent-evals-observability]] 评测先行）。

## 六、待确认项

> ① MLA 在各推理引擎的支持与 kernel 优化进度；② 长上下文有效长度各家评测协议统一情况(RULER 类)；③ MoE 专家并行的通信-容量联合调优公开基准；④ 线性注意力/混合架构(Mamba 系)在生产模型的占比变化。

> [!warning] 残余复核（2026-09-13）：本节四条**按性质分为「已解决 1 / 部分解决 1 / 仍开放 2」**——仍开放的两条属**研究前沿跟踪项，本库无法离线判定**，故不写成结论，只补可核锚点（原句保留如上）。另按本库规矩声明：**本节原文未给出任何出处**，其趋势性表述一律按「本库未能核验」对待，不得作为选型依据。
> - **① MLA 支持与 kernel 进度 —— 已解决**：处置见 §一 的残余复核（上游 main 的专用 MLA backend 目录与 kernel 清单已查得）。**残余判据**：复核新代模型变体是否随版本补齐——`curl -s https://api.github.com/repos/vllm-project/vllm/contents/vllm/v1/attention/backends/mla`（SGLang 对应 `python/sglang/srt/layers/attention`），期望在该目录看到与当期模型对应的新 kernel 文件。
> - **② 长上下文有效长度评测协议 —— 部分解决（已锚到事实标准的官方原文）；「各家是否统一」仍开放**：**RULER 官方仓库即定义了该协议**——原文标题《RULER: What's the Real Context Size of Your Long-Context Language Models》（arXiv:2404.06654），以可配置序列长度 + 4 类共 13 个合成任务评测 17 个开源模型，结果表**并列给出 Claimed Length / Effective Length 两列**，并以**定性阈值**判定有效长度，逐字为「While all models claim context size of 32k tokens or greater, only half of them can effectively handle sequence length of 32K by exceeding **a qualitative threshold, Llama-2-7b performance at 4K (85.6%)**」与「Almost all models fall below the threshold before reaching the claimed context lengths.」。**故「标称窗口 ≠ 有效上下文」有官方原文支撑**（§二「宣称 128K 的模型其有效上下文(needle 通过率)常低于标称」一句由此获得一出处，原文未给出处属本库缺失，本轮补上）。**仍开放**：厂商是否**统一**采用该协议与同一阈值，须逐家模型卡核。**判据**：在模型卡中检索是否**同时**给出 claimed 与 effective 长度且写明判定阈值；只报标称窗口即视为未统一。来源 `https://raw.githubusercontent.com/NVIDIA/RULER/main/README.md`（HTTP 200，2026-09-13）。
> - **③ MoE 专家并行通信-容量联合调优的公开基准 —— 仍开放**（公开的**算法**已定位，公开的**基准**未找到）：DeepSeek 已开源其线上部署用的 EP 负载均衡器 **EPLB**——采用**冗余专家**复制 + 启发式打包，含 hierarchical / global 两套策略以兼顾负载均衡与降低跨节点流量（即通信面），但 README 明确「the exact method to predict the loads of experts is out of this repo's scope」，**即给出的是算法实现而非带实测数据的联合调优基准**。**判据**：须在公开基准或论文中核到同一硬件与 EP 配置下**同时**给出 all-to-all 通信占比与专家容量溢出率的实测数据；只有单项数据不算「联合」基准。来源 `https://raw.githubusercontent.com/deepseek-ai/EPLB/main/README.md`（HTTP 200，2026-09-13；MIT）。
> - **④ 线性注意力/混合架构在生产模型的占比变化 —— 仍开放（趋势数据不可离线取得）**；本轮可确定的只有**引擎侧已就位**：vLLM 主干 `vllm/v1/attention/backends/` 含 `mamba_attn.py`、`mamba1_attn.py`、`mamba2_attn.py`、`linear_attn.py`、`gdn_attn.py`、`short_conv_attn.py`，SGLang 含 `linear/`、`mamba/`、`hybrid_linear_attn_backend.py`（HTTP 200，2026-09-13）。**占比变化本身仍无出处**，判据：须以当期模型清单（如各厂商开源模型发布表）逐一点名统计，而非引用趋势断言。
> 依据：`api.github.com` 仓库内容查询（vLLM HEAD `b7e0cdac5d11`、SGLang HEAD `6220f45d8e9a`）、`raw.githubusercontent.com` 取 RULER / EPLB README（均 2026-09-13）。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 残余复核 | §一「vLLM/SGLang 对 MLA 支持滞后于 GQA（版本相关**待确认**）」 | **已解决：表述过时，就地订正。** 上游 main 直查（2026-09-13）：vLLM `vllm/v1/attention/backends/mla/` 是独立 MLA backend 包（`flashmla.py`/`flashattn_mla.py`/`flashinfer_mla.py`/`cutlass_mla.py`/`triton_mla.py`/`amx_mla.py`/`cpu_mla.py`/`rocm_aiter_mla.py` + `*_sparse.py` + `prefill/`）；SGLang `python/sglang/srt/layers/attention/` 有 `flashmla_backend.py`/`flashinfer_mla_backend.py`/`trtllm_mla_backend.py`/`cutedsl_mla_backend.py`/`hip_flash_mla.py`/`swa_mla_fallback/` 及 DeepSeek-V4 的 `dsv4/`。准确表述：MLA 需各引擎专用 kernel，但两家均已内置多个。「滞后」仅在新代变体跟进速度上仍可能成立，判据见 §六 ① |
| 残余复核 | §四「Medusa/self-speculation 变体省独立草稿模型（成熟度**待确认**）」 | **部分已解决。**「省独立草稿模型」成立：vLLM 文档《Speculative Decoding》方法表列有 MLP speculator / MTP 等免独立 draft 方案，主干 `vllm/v1/spec_decode/medusa.py` 存在。**命名订正**：vLLM 文档方法表**无 Medusa 条目**、SGLang `python/sglang/srt/speculative/` **无 Medusa 模块**，故改按上游方法名表述。**残余**：逐引擎成熟度分级无可引用标签，判据已写在 §四 |
| 残余复核 | §六 待确认项 4 条 | **①已解决**（同上）；**②部分解决**——已锚到 RULER 官方协议原文（claimed vs effective 双列 + 定性阈值 85.6%），「各家是否统一采用」仍开放；**③仍开放**——已定位 DeepSeek 开源的 EPLB（算法实现，README 自述负荷预测不在范围内），**公开基准仍未找到**；**④仍开放**——占比趋势不可离线取得，仅引擎侧支持已确证。另声明：本节趋势性表述属**本库未能核验**（原文无出处），不作选型依据 |
| 补记 | 本文此前未被 2026-09-13 全库回写覆盖（无 `## 补完记录` 表、`updated` 停在 2026-08-26） | 本轮补齐：`updated` 改 2026-09-13、新增本表；**原文与行号一律未动**，三处结论均以就地 callout 给出 |

回链：[[CORRECTIONS]] · [[AGENTS]]

## Related

[[CS-KB-Home]] · [[AI大模型开发]] · [[LLM推理部署与量化]] · [[深度学习算法基础]] · [[RAG检索增强生成实战]] · [[AI-Dev-KB-Home]]
