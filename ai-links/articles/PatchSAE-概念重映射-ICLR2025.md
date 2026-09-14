---
title: "PatchSAE 概念重映射——ICLR 2025"
aliases: [PatchSAE, 概念重映射, SAE ICLR 2025]
tags: [ai/learning, reference]
created: 2024-12-06
updated: 2026-09-14
status: stable
source: "论文"
source_urls:
  - "https://arxiv.org/abs/2412.05276"
  # 官方定位符（2026-09-13 补录；ICLR 官方版与 arXiv 版可能不同）
  - "https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d5b603d631d595f56bc36b373458b27-Abstract-Conference.html"
author: "Hyesu Lim, Jinho Choi, Jaegul Choo, Steffen Schneider"
venue: "ICLR 2025"
date: "2024-12-06"
fetched_at: "2026-06-17"
---

# PatchSAE：Adaptation 不学新概念，只重映射旧概念——ICLR 2025 论文精读

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[SAE-视觉特征单义性-NeurIPS2025]] | [[给LLM做脑扫描-可解释性技术全景]] | [[AI大模型开发]]

> Sparse autoencoders reveal selective remapping of visual concepts during adaptation
> Hyesu Lim et al. · ICLR 2025 · [github.com/dynamical-inference/patchsae](https://github.com/dynamical-inference/patchsae)
> 官方定位符（2026-09-13 补）：[ICLR 2025 proceedings abstract 页](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d5b603d631d595f56bc36b373458b27-Abstract-Conference.html)（hash `3d5b603d631d595f56bc36b373458b27`，页面另给官方 Paper-Conference.pdf）；标题、作者序列（Hyesu Lim, Jinho Choi, Jaegul Choo, Steffen Schneider）与 venue「ICLR 2025」四项已逐字核对无误。

> [!warning] 未能核验（2026-09-13）：上方的代码仓库链接本轮**无法核验**——github.com 与 api.github.com 直连均失败（属**网络环境限制，不构成链接失效证据**），ICLR 官方 abstract 页也**未列 code 链接**，无法交叉印证。下一轮请用 `api.github.com/repos/dynamical-inference/patchsae` 做存在性与重定向检查。

> [!success] 未能核验项复核（2026-09-14）：**已结——仓库存在且与论文一一对应**。按上一轮指定的判据经 SOCKS5 代理直取 `api.github.com/repos/dynamical-inference/patchsae`（HTTP 200）：`full_name` 恰为请求名 → **无重定向，即无改名**；`description` 逐字为 "Implementation of PatchSAE as presented in \"Sparse autoencoders reveal selective remapping of visual concepts during adaptation\""，与本文标题一致；`default_branch = main`、`created_at = 2024-12-02`、`pushed_at = 2026-04-22`、`archived = false`、`fork = false`、license = **MIT**。另经 `raw.githubusercontent.com/.../main/README.md`（HTTP 200）取得仓库自述：其自定位为该论文的 **reference implementation**，并另指明后继库 FastSAE。⇒ 上一轮的读不到**纯属直连受限**，非链接失效；该链接可正常引用（依据：`https://api.github.com/repos/dynamical-inference/patchsae`，代理取回于 2026-09-14）。

**角色定位**：把 SAE 当作分析仪器，回答「adaptation 到底改了什么」——而不是把 SAE 本身当作研究对象。

---

## 一、和 NeurIPS 2025 (Pach et al.) 的关键差异

两篇都在 CLIP 视觉编码器上训 SAE，但挂载位置和核心问题完全不同：

| 维度 | NeurIPS 2025 (Pach et al.) | PatchSAE (Lim et al.) |
|------|---------------------------|----------------------|
| **SAE 输入** | CLS token（全局汇总向量） | **所有 token**（1 CLS + 576 patch tokens = 577（ViT-L/14 @336px）） |
| **空间定位** | 只知道「图里有狗」 | 知道「狗在第 3 行第 5 列 patch 上」 |
| **核心问题** | SAE 特征是不是单义的？能因果控制输出吗？ | Adaptation 时内部发生了什么？学新概念还是重用旧概念？ |
| **方法论贡献** | MS 指标 + MTurk 人类实验 + 因果干预 | 空间归因 + latent masking 消融 + adaptation 机制分析 |
| **实验下游** | LLaVA（多模态对话生成） | MaPLe prompt adaptation（few-shot 图像分类） |
| **SAE 角色** | **研究对象**（验证 SAE 本身靠不靠谱） | **分析仪器**（用 SAE 去研究另一个问题） |

---

## 二、PatchSAE 架构

### 2.1 核心设计：对所有 token 训 SAE

```
CLIP ViT 残差流输出 z ∈ ℝ^(N+1)×d  (N=576 patches + 1 CLS token，共 577, d=1024)
  → 逐 token 独立过 SAE
  → 每个 token 得到稀疏激活向量
  → 每个 SAE latent 同时有语义含义 + 空间位置信息
```

本质仍是标准 SAE：线性编码器 → ReLU → 线性解码器，L1 稀疏惩罚。唯一的架构差异是**输入是所有 token 而非仅 CLS**——这个简单的改变解锁了空间定位能力。

### 2.2 训练配置

| 项目 | 设置 |
|------|------|
| 基底模型 | CLIP ViT-L/14（frozen） |
| 钩子层 | ViT 中间层 attention block 残差流输出 |
| 训练数据 | ImageNet 训练集 |
| 稀疏策略 | L1 正则化 |
| 损失函数 | MSE (重建) + λ·L1 (稀疏) |

> [!warning] 补（2026-09-13）：「ViT 中间层 attention block 残差流输出」是**模糊指代**（第几层？几层都有？每层一个 SAE 还是共享？），这一点直接决定 §七 局限 3「SAE 训练在单层」能否成立——若其实训了多层，局限 3 就是错的；若只训一层，应写明是哪一层。对照组 NeurIPS 2025 篇把挂载位置写到残差流 CLS token 的 L11/17/22/23 + 最终投影层，可比性要求同样的精度。

### 2.3 四级分析粒度

| 粒度 | 定义 | 能回答什么 |
|------|------|-----------|
| **Token 级** | 单张图上单个 SAE latent 的 patch 激活分布 | 「这个概念在图片的哪个位置？」 |
| **图像级** | 汇总全图所有 token 的 latent 激活 | 「哪些参考图片最能激活这个概念？」 |
| **类级** | 对某个类的所有图片取平均激活 | 「分类 '斑马' 主要依赖哪些概念？」 |
| **任务级** | 跨数据集比较概念使用模式 | 「adapt 前后用的是同一组概念吗？」 |

---

## 三、关键发现 1：多粒度可定位概念

**多粒度**：同一个 SAE 同时拆出——
- 低层属性：颜色、纹理、形状
- 中层部件：轮子、窗户、腿
- 高层语义：物体类别、场景类型

**可定位**：激活 patch 能准确圈出概念在图片中的物理位置——不是全局模糊判断，是精确到 3×4 个 patch 的空间映射。

**跨数据集泛化**：ImageNet 上训的 PatchSAE 放到 domain-shifted 数据集（细粒度动植物等），概念保持可解释——SAE 学的是 CLIP ViT 内部通用的视觉概念，不是 ImageNet 特供版。

> [!warning] 补（2026-09-13）：官方摘要能**确证**的部分只有三条——PatchSAE 训在 CLIP vision transformer 上、训练数据来自 ImageNet、下游为图像分类并使用 prompt-based adaptation（本文 §5.1 进一步具体化为 MaPLe）。「细粒度动植物等」这种**指代无法复核**：domain-shifted 具体是哪些数据集（DomainNet / CUB / Oxford Flowers？）、评估协议是 few-shot 还是全量线性探针，都需回原文补，否则「跨数据集泛化」只有结论没有依据。
> - 来源：[ICLR 2025 proceedings abstract 页](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d5b603d631d595f56bc36b373458b27-Abstract-Conference.html)

---

## 四、关键发现 2：SAE latent 对分类有因果影响

**方法**：latent masking 消融
- 对某个类，找到 top activating SAE latents
- 将这些 latent 的激活值强制置零
- 观察分类准确率变化

**结果**：mask 掉关键 latent 后分类性能显著下降 → 这些概念不只在统计上和输出相关，在因果上参与了分类决策。

这一点与 NeurIPS 2025 的因果干预实验互相印证——NeurIPS 改一个 SAE 神经元能控制 LLaVA 的生成输出，PatchSAE mask 掉概念能损伤分类性能。两个都是因果性证据，一个正着做（插入/放大），一个反着做（掩码/删除）。

---

## 五、关键发现 3（核心贡献）：Adaptation = 重映射，不学新概念

### 5.1 实验设计

- **Adaptation 方法**：MaPLe（Khattak et al., 2023a）——CLIP 视觉+文本分支各加少量可学习 prompt token，联合微调
- **任务**：few-shot 图像分类（多下游数据集）
- **分析工具**：在**未 adapt 的基座 CLIP** 上训好 PatchSAE，用同一组 SAE latent 去观察 adapt 后的模型

### 5.2 两个竞争假设

| 假设 | 含义 | 如果是真，预期观察到 |
|------|------|-------------------|
| **H1：学新概念** | Adaptation 让模型学到了基座模型没有的新视觉概念 | SAE latent 激活模式 adapt 前后大幅变化 |
| **H2：重映射旧概念** | Adaptation 只是重新调整了已有概念和下游类别之间的权重 | 激活模式变化不大，但概念→类别的映射关系变了 |

### 5.3 结果：H2 胜出

- adapt 前后，同一个 SAE latent 在同一张图的同一个 patch 上的激活强度**变化很小**
- 但 adapt 后的模型对下游类的预测更多依赖「真正相关的概念」、更少依赖无关概念
- 统计：**大部分性能提升可以用基座模型已有的概念解释**

### 5.4 核心结论

> Prompt-based adaptation 的主要机制不是教会模型「看新东西」，而是教会它「做这道题时重点看哪些老东西」——这是 **selective remapping（选择性重映射）**，不是 concept learning（概念学习）。

这解释了为什么 prompt-based adaptation 只需要很少的训练样本就能生效——它不是从零学概念（那需要大量数据），只是重新加权已有概念（少量样本就够）。

---

## 六、两篇 SAE 论文串起来看

```
NeurIPS 2025 (Pach et al.):
  Q: SAE 特征可靠吗？                    → YES (MS + MTurk 82.8% + 因果干预)
  Q: 改一个特征能控制输出吗？             → YES (LLaVA steering: 综合 52.5% vs DiffMean 33.3%)
  Q: 跨编码器泛化吗？                     → YES (4 种编码器都有效)
  角色: 把 SAE 当研究对象

PatchSAE (Lim et al.):
  Q: 视觉概念能空间定位吗？               → YES (patch 级激活图)
  Q: Adaptation 学新概念还是重映射？       → 重映射 (selective remapping)
  Q: SAE 特征对分类有因果作用吗？          → YES (masking 消融)
  角色: 把 SAE 当分析仪器
```

两条线互补。NeurIPS 那篇验证了 SAE 这个工具本身靠谱（才能放心当仪器用），PatchSAE 拿这个已验证的工具去发现了 adaptation 的机制秘密。

---

## 七、局限

1. **只用 L1 稀疏**——未比较 BatchTopK/Matryoshka 等更优策略（NeurIPS 那篇已证明 BatchTopK 比 L1 好）

> [!warning] 更正（2026-09-13）：官方摘要**没有**「BatchTopK 比 L1 好」这种表述，原文是「SAEs trained on VLMs significantly enhance the monosemanticity of individual neurons, **with sparsity and wide latents being the most influential factors**」——决定单义性的是**稀疏度与隐层宽度**两个因子，BatchTopK vs L1 属实现选择的下游，引用时应改用官方口径。另经核对，本文通篇未给 PatchSAE 的扩展因子 ε 与隐层宽度（§2.2 训练配置表无这两项），而对照组 NeurIPS 篇明确 ε ∈ {1,2,4,8,16,64}（见该文 §2.3），故这条「未比较更优策略」的局限**无法自证**。
> - 来源：[ICLR 2025 proceedings abstract 页](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d5b603d631d595f56bc36b373458b27-Abstract-Conference.html) · [NeurIPS 2025 poster 页](https://neurips.cc/virtual/2025/loc/san-diego/poster/119210)
2. **只在分类任务上分析 adaptation**——未涉及 captioning/VQA/对话等多模态任务
3. **SAE 训练在单层**——未系统性比较多层的信息差异（NeurIPS 覆盖了 L11/17/22/23/last 五层）
4. **只分析了 MaPLe**——CoOp/CoCoOp 等其他 prompt-based 方法的内部机制可能不同
5. **仅视觉侧**——未分析文本编码器侧的 adaptation 机制

---

## 八、一句话记忆标签

> PatchSAE 让我们能看到：adaptation 不是教会模型看新东西，而是告诉它「做这道题时，看你本来就认识的那些东西里的这几个。」

> CLS 能告诉你「有狗」，patch token 能告诉你「狗在哪」——SAE 挂在 CLS 上能拆语义，挂在 patch 上还能拆空间。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 加厚 | frontmatter 只有 arXiv 一条，缺官方定位符 | 补 ICLR 2025 proceedings abstract 页（hash `3d5b603…`，含官方 PDF）；标题、4 位作者、venue 三项已逐字核对无误 |
| 补疏漏 | 代码仓库链接无法判断是否失效 | 标注「本轮未能核验」，并说明 github.com / api.github.com 直连失败属**环境限制、不构成失效证据**，下一轮用 API 复核 |
| 补疏漏 | §三「跨数据集泛化（细粒度动植物等）」只有结论 | 标注官方摘要只能确证三条（CLIP ViT 上训练 / ImageNet 数据 / 分类 + prompt-based adaptation），数据集与评估协议需回原文补；依据 ICLR 官方摘要页 |
| 纠错 | §七 局限 1 称「NeurIPS 那篇已证明 BatchTopK 比 L1 好」 | 改用官方口径「sparsity and wide latents being the most influential factors」；并指出本文未给 ε 与隐层宽度，该局限无法自证；依据 ICLR 与 NeurIPS 两个官方页 |
| 补疏漏 | §2.2 钩子层写「ViT 中间层」过于模糊，直接影响局限 3 | 标注需写明第几层 / 每层是否各一个 SAE，并给出对照组的内存粒度（L11/17/22/23 + 投影层）作为可比性要求 |
| 未能核验项复核 | 上一条「代码仓库链接无法判断是否失效」 | **已结**：按上轮指定的 API 判据经代理直取 `api.github.com/repos/dynamical-inference/patchsae`（HTTP 200）——`full_name` 无重定向、description 与论文标题一致、MIT、`archived=false`、`pushed_at=2026-04-22`；README 自述为论文 reference implementation。原「直连失败」确属环境限制（代理取回于 2026-09-14） |

- 回链：[[CORRECTIONS]]｜[[AGENTS]]
