---
title: 箭头连接检查清单
aliases: [Arrow Checklist]
tags: [reference]
created: 2026-07-28
updated: 2026-09-13
status: stable
---

See also: [[AGENTS]] (绘图规范) | [[Network-DocGraph.excalidraw]] (文档关系图)

# Excalidraw 箭头连接检查清单

> [!note] 本清单已覆盖 6 张核心图的**箭头校验**（下表逐一列出）；其余新增图请在绘制时按本规范自检：逐项核对源/目标元素与方向，修复悬空、错位箭头。绘图规范见 [[AGENTS#十一、图表与可视化约定]]。

> [!warning] 更正（2026-09-13）：上面这句「已覆盖 6 张核心图的**箭头校验**」实际只到「视觉从-到方向」一层——全文 0 处提到 `startBinding` / `endBinding` / `boundElements` / `mode`，而字段级缺口实测为：SelfAttention-Flow 5 条箭头绑定不完整、MultiHead-Attention 3 条两端无绑定、Attention-Matrix-Flow 1 处缺回引，另有 16 张图从未登记（原表述为「本清单已覆盖 6 张核心图的**箭头校验**…其余新增图请…自检」）。字段级台账见 §7，失败模式与验收判据见 §8，全量登记表见 §9。

> 操作：在 Obsidian 中打开 `.excalidraw.md` → 按 `A` 选箭头工具 → 从源矩形边缘拖到目标矩形边缘（自动吸附对齐）→ 保存

---

## 1. Transformer-Architecture

| # | 箭头 | 从 | 到 | 方向 |
|---|------|----|----|:--:|
| 1 | Input → Encoder | `Input (today is sunny)` 右 | `Encoder` 框左 | → |
| 2 | Embedding → Encoder | `Token Embedding` 右 | `Multi-Head Self-Attention` 左 | → |
| 3 | +PE → Encoder | `+ Positional Encoding` 右 | `Multi-Head Self-Attention` 左 | → |
| 4 | MHSA → AddNorm | `Multi-Head Self-Attention` 底 | `Add & Norm`(第1个) 顶 | ↓ |
| 5 | AddNorm → FFN | `Add & Norm`(第1个) 底 | `Feed Forward` 顶 | ↓ |
| 6 | FFN → AddNorm | `Feed Forward` 底 | `Add & Norm`(第2个) 顶 | ↓ |
| 7 | Encoder → Decoder | `Add & Norm`(第2个) 右 | `Decoder` 框左 | → |
| 8 | MSA → AddNorm | `Masked Self-Attention` 底 | `Add & Norm`(第3个) 顶 | ↓ |
| 9 | AddNorm → CA | `Add & Norm`(第3个) 底 | `Cross-Attention` 顶 | ↓ |
| 10 | CA → AddNorm | `Cross-Attention` 底 | `Add & Norm`(第4个) 顶 | ↓ |
| 11 | AddNorm → FFN | `Add & Norm`(第4个) 底 | `Feed Forward`(解码器) 顶 | ↓ |
| 12 | FFN → AddNorm | `Feed Forward`(解码器) 底 | `Add & Norm`(第5个) 顶 | ↓ |
| 13 | Decoder → Output | `Add & Norm`(第5个) 右 | `Linear + Softmax` 左 | → |
| 14 | Linear → Predict | `Linear + Softmax` 底 | `Predict Next Token` 顶 | ↓ |

---

## 2. GPT-DecoderOnly

| # | 箭头 | 从 | 到 | 方向 |
|---|------|----|----|:--:|
| 1 | Input → Embedding | `Input Token IDs` 底 | `Token Embedding + RoPE` 顶 | ↓ |
| 2 | Embedding → Decoder | `Token Embedding + RoPE` 底 | `Decoder Layer` 框顶 | ↓ |
| 3 | Decoder → LM Head | `Decoder Layer` 框底 | `LM Head` 顶 | ↓ |
| 4 | LM Head → Softmax | `LM Head` 底 | `Softmax + Sampling` 顶 | ↓ |
| 5 | Softmax → Output | `Softmax + Sampling` 底 | `Next Token` 顶 | ↓ |
| 6 | Loop | `Next Token` 右 | 回到 Decoder 框右（`ogL9UXRS`: r6 → r3） | ↻ |
| 7 | MSA → AddNorm | `Causal Self-Attention (Masked)`（r3a）底 | `Add & Norm`（r3b）顶 | ↓ |

> [!warning] 更正（2026-09-13）：① 本节原只列 6 条，实测为 **7 条**——漏记 `M2R5ZB40`（`r3a` → `r3b`），小计 6 → **7**；② 第 6 行原标注「↻ (虚线)」与图不符：循环箭头 `ogL9UXRS`（`r6`→`r3`）的 `strokeStyle` 实为 `solid`（原表述为「↻ (虚线)」）；③ `r3c`（FFN (SwiGLU)）与 `r3d`（Add & Norm）在图上**没有任何箭头接入**（IN/OUT 均为空），本节此前既未登记也无说明——若是有意不接线请在图上注明，否则按 §8 记为待修项。

---

## 3. SelfAttention-Flow

| # | 箭头 | 从 | 到 | 方向 |
|---|------|----|----|:--:|
| 1 | X → Q | `Input X` 右 | `Q = XWq` 左 | → |
| 2 | X → K | `Input X` 右 | `K = XWk` 左 | → |
| 3 | X → V | `Input X` 右 | `V = XWv` 左 | → |
| 4 | Q → Scores | `Q = XWq` 右 | `Scores = Q×K^T` 左 | → |
| 5 | K → Scores | `K = XWk` 右 | `Scores = Q×K^T` 左下 | → |
| 6 | Scores → Scale | `Scores = Q×K^T` 底 | `÷√d_k` 顶 | ↓ |
| 7 | Scale → Mask | `÷√d_k` 底 | `+ Mask` 顶 | ↓ |
| 8 | Mask → Softmax | `+ Mask` 底 | `Softmax` 顶 | ↓ |
| 9 | Softmax → Weights | `Softmax` 右 | `Attention Weights` 左 | → |
| 10 | Weights → WSum | `Attention Weights` 底 | `Weighted Sum` 顶 | ↓ |
| 11 | V → WSum | `V = XWv` 右 | `Weighted Sum` 左 | → (虚线) |
| 12 | WSum → Output | `Weighted Sum` 底 | `Output` 顶 | ↓ |

---

## 4. MultiHead-Attention

| # | 箭头 | 从 | 到 | 方向 |
|---|------|----|----|:--:|
| 1 | Input → Split | `Input X` 底 | `Split into h heads` 顶 | ↓ |
| 2 | Split → Head1 | `Split` 左 | `Head_1` 顶 | ↙ |
| 3 | Split → Head2 | `Split` 中 | `Head_2` 顶 | ↓ |
| 4 | Split → Headh | `Split` 右 | `Head_h` 顶 | ↘ |
| 5 | Head1 → Attn1 | `Head_1` 底 | `Self-Attention_1` 顶 | ↓ |
| 6 | Head2 → Attn2 | `Head_2` 底 | `Self-Attention_2` 顶 | ↓ |
| 7 | Headh → Attnh | `Head_h` 底 | `Self-Attention_h` 顶 | ↓ |
| 8 | Attn1 → Concat | `Self-Attention_1` 底 | `Concat` 顶 | ↘ |
| 9 | Attn2 → Concat | `Self-Attention_2` 底 | `Concat` 顶 | ↓ |
| 10 | Attnh → Concat | `Self-Attention_h` 底 | `Concat` 顶 | ↙ |
| 11 | Concat → Project | `Concat` 底 | `Project` 顶 | ↓ |
| 12 | Project → Output | `Project` 底 | `Output` 顶 | ↓ |

---

## 5. Training-vs-Inference

| # | 箭头 | 从 | 到 | 方向 |
|---|------|----|----|:--:|
| 1 | Full text → Forward | `Full text` 底 | `Forward` 顶 | ↓ |
| 2 | Forward → Predict | `Forward` 底 | `Predict` 顶 | ↓ |
| 3 | Predict → Loss | `Predict` 底 | `Loss` 顶 | ↓ |
| 4 | Loss → Backward | `Loss` 底 | `Backward` 顶 | ↓ |
| 5 | Prompt → Forward | `Prompt` 底 | `Forward`(推理) 顶 | ↓ |
| 6 | Forward → Sample | `Forward`(推理) 底 | `Sample` 顶 | ↓ |
| 7 | Sample → Append | `Sample` 底 | `Append` 顶 | ↓ |
| 8 | Append → Loop | `Append` 底 | `Loop` 顶 | ↓ |
| 9 | Loop → Forward | `Loop` 右 | `Forward`(推理) 右（`GzhEHAsv`: i5 → i2） | ↻ |

> [!warning] 更正（2026-09-13）：第 9 行原标注「↻ (虚线)」不成立——真实循环箭头 `GzhEHAsv`（`i5`→`i2`）是 `solid`；文件里唯一一条 `dashed` 箭头是 `al`，它带 `isDeleted:true`（墓碑元素，Excalidraw 不渲染，不计入箭头数）。故**本节存活箭头仍为 9 条**（原表述为「↻ (虚线)」；「9→10」的修正会引入新错误）。

---

## 6. Attention-Matrix-Flow

| # | 箭头 | 从 | 到 | 方向 |
|---|------|----|----|:--:|
| 1 | X → Q | `Input X (4×512)` 右 | `Q (4×64)` 左 | → |
| 2 | X → K | `Input X (4×512)` 右 | `K (4×64)` 左 | → |
| 3 | X → V | `Input X (4×512)` 右 | `V (4×64)` 左 | → |
| 4 | Q → Scores | `Q (4×64)` 右 | `Scores (4×4)` 左 | → |
| 5 | K → Scale | `K (4×64)` 右 | `Scale: divide / sqrt(dk)`（`rd`）顶 | ↓ |
| 6 | Scores → Scale | `Scores (4×4)` 底 | `Scale` 顶 | ↓ |
| 7 | Scale → Mask | `Scale` 底 | `+ Mask` 顶 | ↓ |
| 8 | Mask → Softmax | `+ Mask` 底 | `Softmax (4×4)` 顶 | ↓ |
| 9 | Softmax → Output | `Softmax (4×4)` 右 | `Output 4×64 (per head)`（`ro`）顶 | ↓ |
| 10 | Weights → WSum | `Attention Weights (4×4)` 底 | `Weighted Sum (4×64)` 顶 | ↓ |
| 11 | V → WSum | `V (4×64)` 右 | `Weighted Sum (4×64)` 左 | → (虚线) |
| 12 | WSum → Output | `Weighted Sum (4×64)` 底 | `Output (4×64)` 顶 | ↓ |

> [!warning] 更正（2026-09-13）：本表第 5、9 行的「到」与图不符——① 第 5 行原表述为「`K (4×64)` 右 → `Scores (4×4)` 左」，实测 `aks` 的终点是 `Scale: divide / sqrt(dk)`（`rd`），`Scores`（`rs`）唯一入边是 `aqs`（`rq`→`rs`）：图上把 K 直接接进了 Scale，**这不是注意力的计算顺序**（应为 `Scores = Q×K^T` 之后才缩放）；② 第 9 行原表述为「`Softmax (4×4)` 右 → `Attention Weights (4×4)` 左」，实测 `asw` 的终点是 `Output 4×64 (per head)`（`ro`），`Attention Weights`（`rw`）**没有任何入边**，只有出边 `awv`→`Weighted Sum`；③ `rs` 的 `boundElements` 只有 `[ts, asd]`，缺 `aqs` 回引（全库缺回引计数 = 1）。三处均按 §8 记为待修项。

---

> **总计: 66 条箭头连接** — Transformer(14) + GPT(7) + SelfAttn(12) + MultiHead(12) + Training(9) + MatrixFlow(12)

> [!warning] 更正（2026-09-13）：原表述为「**总计: 65 条箭头连接** — Transformer(14) + GPT(6) + SelfAttn(12) + MultiHead(12) + Training(9) + MatrixFlow(12)」——65 是 §2 小计 6 的连带错误，按**存活元素**（`isDeleted:true` 的墓碑不计）应为 **66**。既不是 65，也不是把 Training 的 `al` 墓碑算进去得到的 67。

---

## 7. 字段级绑定台账（2026-09-13 实测）

> **复现方法**（详细步骤见 [[AGENTS#十一、图表与可视化约定]]）：取 `.excalidraw.md` 的绘图数据段（`%%` 包裹的 `compressed-json` 围栏；全库 22 张图中 13 张为压缩、9 张仍为未压缩的 `json` 围栏）→ 拼接时**去掉全部空白** → `LZString.decompressFromBase64()` → 统计 `elements`（`isDeleted:true` 为墓碑，不计入）→ 逐条比对箭头两端 binding 的 `elementId` 是否指向存活元素、目标元素 `boundElements` 是否回引该箭头 id。

| 图 | 存活元素 | 矩形/文本/箭头 | 悬空绑定 | 缺回引 | 字段级待修（元素 id 级） |
|---|---|---|---|---|---|
| Transformer-Architecture | 45 | 14/17/14 | 0 | **3** | 补回引：`a_ff_an2`→`ean2`、`a_msa_an1`→`dmhsa`、`a_lm_out`→`outPred`；`dmhsa` 无任何入边（缺 `Output Embedding(shifted right)`+`PE` → `dmhsa`）；`dca` 唯一入边 `B91WNJVQ`(`dan1`→`dca`) 在 Q 侧，缺编码器输出 → `dca` 的 K/V 箭头；5 个 Add & Norm（`ean1/ean2/dan1/dan2/dan3`）各只有 1 条入边，14 条箭头无一条绕过子层形成残差跳连 |
| GPT-DecoderOnly | 27 | 10/10/7 | 0 | **5**（本次回写实测） | `r3b`→`r3c`→`r3d` 无箭头（`M2R5ZB40` 只连到 `r3b`）；`r2`..`r6` 共 5 处目标未回引（`a12/a23/a34/a45/a56`） |
| SelfAttention-Flow | 34 | 11/11/12 | **5** | 0 | `aqs`/`aks`/`aso`/`awv` 两端皆 `null`、`avs` 仅 `endBinding` → 对应 §3 第 4/5/9/10/11 行 |
| MultiHead-Attention | 37 | 11/14/12 | **3** | 0 | `a1c`/`a2c`/`a3c` 两端皆 `null` → 对应 §4 第 8/9/10 行（Attn→Concat） |
| Training-vs-Inference | 31 | 10/12/9 | 0 | 0 | 无；另存 1 条 `isDeleted` 的 `dashed` 墓碑箭头 `al`（文件卫生问题） |
| Attention-Matrix-Flow | 34 | 11/11/12 | 0 | **1** | 补回引 `aqs`→`rs`；`aks`(`rk`→`rd`) 终点接在 Scale 上、`asw`(`rsm`→`ro`) 跳过 `rw`、`rw` 无入边（见 §6 更正） |
| Network-DocGraph | 23 | 10/13/**0** | — | — | 无箭头（纯矩形+文本），箭头校验 **N/A** |

**§7.1 行号 → 箭头 id 对照（供 §1~§6 各表定位；2026-09-13 实读）**

| 图（节） | 行号 → 箭头 id |
|---|---|
| §1 Transformer-Architecture | 1 `a_emb_enc` · 2 `7RwKwgrA` · 3 `SQUNhUA2` · 4 `a_sa_an1` · 5 `a_an1_ff` · 6 `a_ff_an2` · 7 `a_enc_dec` · 8 `a_msa_an1` · 9 `B91WNJVQ` · 10 `a_ca_an2` · 11 `a_an2_ff` · 12 `a_ff_an3` · 13 `a_dec_out` · 14 `a_lm_out` |
| §2 GPT-DecoderOnly | 1 `a12` · 2 `a23` · 3 `a34` · 4 `a45` · 5 `a56` · 6 `ogL9UXRS` · 7 `M2R5ZB40` |
| §3 SelfAttention-Flow | 1 `axq` · 2 `axk` · 3 `axv` · 4 `aqs` · 5 `aks` · 6 `GI9Wt9O8` · 7 `LX88hv1v` · 8 `XGqVqlfm` · 9 `aso` · 10 `awv` · 11 `avs` · 12 `L8dROJK3` |
| §4 MultiHead-Attention | 1 `a0` · 2 `as1` · 3 `as2` · 4 `as3` · 5 `2eqrcjNO` · 6 `06jKgBCW` · 7 `hEKlbkn8` · 8 `a1c` · 9 `a2c` · 10 `a3c` · 11 `S8m3BRoK` · 12 `d4QNJERL` |
| §5 Training-vs-Inference | 1 `ocjxGO1L` · 2 `TwMSmevG` · 3 `56yOLIim` · 4 `Q0kCBtrf` · 5 `sWGLyq2o` · 6 `EndFV1yH` · 7 `mF97G5ze` · 8 `7nYAhajW` · 9 `GzhEHAsv` |
| §6 Attention-Matrix-Flow | 1 `axq` · 2 `axk` · 3 `axv` · 4 `aqs` · 5 `aks` · 6 `asd` · 7 `adm` · 8 `ams` · 9 `asw` · 10 `awv` · 11 `avs` · 12 `awso` |

**显示文本 → 元素 id**（§1~§6 表里的元素名；下列均为 rectangle，标注 `(text)` 者为自由文本元素）：

- §1：`Input (today is sunny)`=`inGroup`(text) · `Token Embedding`=`embText`(text，`containerId=null`) · `+ Positional Encoding`=`peText`(text，`containerId=null`) · `Encoder`=`encB` · `Multi-Head Self-Attention`=`emhsa` · `Add & Norm`(编码器第 1/2 个)=`ean1`/`ean2` · `Feed Forward`(编码器)=`eff` · `Decoder`=`decB` · `Masked Self-Attention`=`dmhsa` · `Add & Norm`(解码器第 1/2/3 个)=`dan1`/`dan2`/`dan3` · `Cross-Attention`=`dca` · `Feed Forward`(解码器)=`dff` · `Linear + Softmax`=`outLM` · `Predict Next Token`=`outPred`
- §2：`Input Token IDs`=`r1` · `Token Embedding + RoPE`=`r2` · `Decoder Layer`=`r3` · `Causal Self-Attention (Masked)`=`r3a` · `Add & Norm`(层内第 1 个)=`r3b` · `FFN (SwiGLU)`=`r3c` · `Add & Norm`(层内第 2 个)=`r3d` · `LM Head`=`r4` · `Softmax + Sampling`=`r5` · `Next Token`=`r6`
- §3：`Input X`=`rx` · `Q = XWq`=`rq` · `K = XWk`=`rk` · `V = XWv`=`rv` · `Scores`=`rs` · `÷√d_k`=`rd` · `+ Mask`=`rm` · `Softmax`=`rsm` · `Attention Weights`=`rw` · `Weighted Sum`=`rws` · `Output`=`ro`
- §4：`Input X`=`rx` · `Split`=`rs` · `Head_1`/`Head_2`/`Head_h`=`h1`/`h2`/`hh` · `Self-Attention_1`/`_2`/`_h`=`a1`/`a2`/`ah` · `Concat`=`rc` · `Project`=`rp` · `Output`=`ro`
- §5：`Full text`=`t1` · `Forward`(训练)=`t2` · `Predict`=`t3` · `Loss`=`t4` · `Backward`=`t5` · `Prompt`=`i1` · `Forward`(推理)=`i2` · `Sample`=`i3` · `Append`=`i4` · `Loop`=`i5`
- §6：`X`=`rx` · `Q`=`rq` · `K`=`rk` · `V`=`rv` · `Scores`=`rs` · `Scale`=`rd` · `+ Mask`=`rm` · `Softmax`=`rsm` · `Attention Weights`=`rw` · `Weighted Sum`=`rws` · `Output`=`ro`

## 8. 失败模式 · 处置 · 验收判据（2026-09-13 新增）

| 失败模式 | 判据（可脚本化） | 处置 |
|---|---|---|
| 一端无绑定 | `startBinding` 或 `endBinding` 为 `null` | 在 Obsidian 中重拖该端吸附到目标元素；无法重连再改 JSON |
| 两端无绑定 | 两端皆 `null`（箭头悬在画布上） | 同上；先确认该箭头是否仍然需要 |
| 目标未回引 | 目标元素 `boundElements` 不含该箭头 id | 补 `{"id":"<箭头id>","type":"arrow"}` 到目标 `boundElements`（[[AGENTS]] 判废项） |
| 端点指向已删元素 | `binding.elementId` 不在存活元素集合内 | 重连或删除该箭头 |
| 端点未落在目标边 | `points` 终点距目标包围盒超出阈值 | 重拖端点（§1 表按显示文本+方位描述，id 级对照见 §7） |
| 墓碑元素 | `isDeleted:true` | 不计入统计；属文件卫生问题，在 Obsidian 中重开并保存可清理 |
| `mode: "skip"` | FixedPointBinding 的 `mode` 为 `skip` | 表示有意不吸附，需在图内注明 |

**验收判据（算术式）**：`存活箭头数 = 各小计之和`，且 `悬空绑定数 = 0`、`缺回引数 = 0`；任一项不为 0 即不通过。

**一次真实运行输出（2026-09-13，LZString 解压实读）**：Transformer 缺回引 3、SelfAttention 无绑定 5、MultiHead 无绑定 3、Training 存活悬空 0（另有 1 条 `isDeleted` 的 `al` 墓碑箭头）、Attention-Matrix-Flow 缺回引 1、GPT-DecoderOnly 缺回引 5（本次回写实测）。

## 9. diagrams/ 全量登记表（22 张，2026-09-13）

> 状态口径：**已核验** = 逐条比对过两端绑定与回引；**结构已测** = 只统计了元素/箭头数与两端是否为 `null`，未逐条核验回引。数字均由 LZString 解压实读得出（存活元素，墓碑不计）。

| # | 文件 | 存活元素 | 矩形 | 文本 | 箭头 | 核验状态 | 备注 |
|---|---|---|---|---|---|---|---|
| 1 | AI-Word2Vec-LossGradient.excalidraw.md | 23 | 7 | 9 | 7 | 结构已测 | 1 条仅 `endBinding`（`3RGaHFj0`）；2 条 `isDeleted` 墓碑箭头 |
| 2 | Attention-Matrix-Flow.excalidraw.md | 34 | 11 | 11 | 12 | 已核验 | 缺回引 1（`aqs`→`rs`）；见 §6/§7 |
| 3 | Drawing 2026-07-22 22.04.51.excalidraw.md | 23 | 7 | 9 | 7 | 结构已测 | 元素统计与 #1 完全一致（含 `isDeleted` 墓碑 id），疑似同一绘图的副本 |
| 4 | Function-Calling-Sequence.excalidraw.md | 21 | 6 | 9 | 6 | 结构已测 | 未压缩 `json`；6 条箭头全为 legacy `focus`/`gap` 绑定（12 处） |
| 5 | GPT-DecoderOnly.excalidraw.md | 27 | 10 | 10 | 7 | 已核验 | §2 漏记的第 7 条已补；`r3c`/`r3d` 无箭头接入；5 处目标未回引 |
| 6 | GraphRAG-Flow.excalidraw.md | 36 | 11 | 14 | 11 | 结构已测 | 未压缩 `json`；legacy 绑定 22 处 |
| 7 | LoRA-Principle.excalidraw.md | 30 | 9 | 13 | 8 | 结构已测 | 未压缩 `json`；legacy 绑定 16 处 |
| 8 | MCP-Architecture.excalidraw.md | 22 | 7 | 9 | 6 | 结构已测 | 未压缩 `json`；legacy 绑定 12 处 |
| 9 | Multi-Agent-Supervisor.excalidraw.md | 28 | 6 | 14 | 8 | 结构已测 | — |
| 10 | MultiHead-Attention.excalidraw.md | 37 | 11 | 14 | 12 | 已核验 | 无绑定 3（`a1c`/`a2c`/`a3c`） |
| 11 | Network-DocGraph.excalidraw.md | 23 | 10 | 13 | 0 | 已核验 | 无箭头 → 箭头校验 N/A |
| 12 | Prompt-Engineering-LtM-Flow.excalidraw.md | 23 | 7 | 8 | 8 | 结构已测 | 未压缩 `json`；legacy 绑定 16 处 |
| 13 | RAG-Pipeline.excalidraw.md | 44 | 11 | 23 | 10 | 结构已测 | 未压缩 `json`；legacy 绑定 20 处 |
| 14 | RLHF-GRPO-Pipeline.excalidraw.md | 20 | 7 | 8 | 5 | 结构已测 | 未压缩 `json`；legacy 绑定 10 处 |
| 15 | ReAct-Agent-Loop.excalidraw.md | 18 | 5 | 8 | 5 | 结构已测 | — |
| 16 | SelfAttention-Flow.excalidraw.md | 34 | 11 | 11 | 12 | 已核验 | 无绑定 5（`aqs`/`aks`/`aso`/`awv`/`avs`） |
| 17 | Training-vs-Inference.excalidraw.md | 31 | 10 | 12 | 9 | 已核验 | 1 条 `isDeleted` 墓碑箭头 `al` |
| 18 | Transformer-Architecture.excalidraw.md | 45 | 14 | 17 | 14 | 已核验 | 缺回引 3 + 2 处缺连线（详见 [[Transformer-Architecture.excalidraw]] 页内「核验发现与待修」） |
| 19 | Transformer-BlockNumericalFlow.excalidraw.md | 21 | 7 | 14 | 0 | 结构已测 | 无箭头 N/A |
| 20 | Transformer-Evolution.excalidraw.md | 43 | 10 | 22 | 11 | 结构已测 | 4 条一端或两端无绑定（`11zbjnt9JkgXJhMqFRaXs` 两端）；未逐条核验 |
| 21 | Transformer-PositionalEncoding.excalidraw.md | 35 | 0 | 35 | 0 | 结构已测 | 纯文本图，无箭头 N/A |
| 22 | Transformer-ResidualConnection.excalidraw.md | 27 | 8 | 19 | 0 | 结构已测 | 未压缩 `json`；无箭头 N/A |

**非产物名（避免后续审计反复当成现存文件）**：

| 名称 | 状态 | 依据 |
|---|---|---|
| `AI-Links-关系图.excalidraw.md` | **不产出（销项）** | 该 basename 全库零引用；[[AGENTS]] 第十一节「文档关系图 \| 文字树/表格」已允许该簇用文字树，[[AI-Links-KB-Home]] 即用缩进文字树 |
| `Proxy-Routing-Architecture.excalidraw.md` | **未产出（命名示例）** | 仅出现在 [[AGENTS]] 第十一节命名规范树中，该树是命名示例而非产物清单 |
| `Router-Network-Topology.excalidraw.md` | **未产出（待建）** | 拓扑目前只有文字形态：`network/2026-07-21-树莓派网络故障与路由器破解完整复盘.md` §1 物理拓扑文字树（`eth0` metric 100 / `wlan0` metric 600）；如产出需在 [[Network-KB-Home]] 与相关复盘 See also 处嵌入 |

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | §2 只列 6 条箭头（实为 7 条）；第 6 行把循环标为「虚线」（实为 `solid`） | 补第 7 行 `M2R5ZB40`，小计 6 → 7；标注更正并保留原表述（依据：LZString 解压实读 + §2 更正块） |
| 纠错 | §5 第 9 行「虚线」标注与存活循环箭头 `GzhEHAsv`(`solid`) 不符 | 更正为 `solid`，明确 `al` 是 `isDeleted` 墓碑、本节仍为 9 条（依据：同上） |
| 纠错 | §6 第 5、9 行的「到」与图不符（`aks` 终点是 Scale；`asw` 终点是 Output，`rw` 无入边） | 按图更正两行并保留原表述；补记 `aqs`→`rs` 缺回引（依据：同上） |
| 纠错 | 文末「总计 65 条」由 §2 小计错误连带 | 改为 66（14+7+12+12+9+12），保留原表述与 67 的口径说明 |
| 补疏漏 | 首段声称的「箭头校验」实际只到视觉方向一层，无任何绑定字段 | 新增 §7 字段级绑定台账（含元素 id）与复现方法 |
| 补疏漏 | 清单没有失败模式、处置动作与验收判据 | 新增 §8（7 类失败模式 + 处置 + 算术式验收判据 + 一次真实运行输出） |
| 补疏漏 | 22 张图只登记 6 张，其余无法区分「已核验」与「从未核验」 | 新增 §9 全量登记表（22 张 + 3 个非产物名），未逐条核验者标「结构已测」 |
| 加厚 | 外部依据缺登记 | 论文与插件来源已登记 `sources/learning-notes.md`（Annotated Transformer / Excalidraw types.ts / obsidian-excalidraw-plugin 2.25.3） |

> 回链：[[CORRECTIONS]]（[[AGENTS]] 已在本页页首 See also 链出，不重复添加）。
