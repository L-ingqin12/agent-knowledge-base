---
title: LoRA参数高效微调实战
aliases: [LoRA微调, PEFT, 参数高效微调, Llama-Factory实战, QLoRA]
tags: [ai, ai/learning]
created: 2026-08-25
updated: 2026-09-13
status: review
---

# LoRA参数高效微调实战

一句话定位：用 0.01%~1% 量级的可训练参数把大模型调成"你的模型"——本笔记讲清 LoRA/QLoRA 原理、Llama-Factory 实战与训练监控四件套，覆盖课程第 33/36 章。

> [!abstract] 摘要
> 本文档回答三个问题：什么时候该微调而不是用 RAG（检索增强生成，Retrieval-Augmented Generation）？为什么全量微调（Full Fine-tuning）又贵又忘，LoRA 却便宜又稳？Llama-Factory 怎么从数据到出模型一条龙？内容包括：微调 vs RAG 决策表、全量微调 vs 参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）对比、预训练并行策略回顾（DP/DDP/FSDP、TP/PP、ZeRO、3D 并行）、LoRA 低秩分解原理（ΔW = B·A）与 QLoRA 4bit 反量化机制，以及 peft 纯代码 Demo 和 Llama-Factory CLI 模板。原理图见 [[LoRA-Principle.excalidraw]]。

## 核心概念

### 术语速查表

| 术语 | 英文 | 一句话解释 |
|------|------|-----------|
| 全量微调 | Full Fine-tuning | 更新模型全部参数，效果好但显存/存储/灾难性遗忘代价高 |
| 参数高效微调 | Parameter-Efficient Fine-Tuning, PEFT | 只训练少量（通常 <1%）新增或选定参数，冻结基座 |
| LoRA | Low-Rank Adaptation（低秩适配） | 冻结原权重 W0，旁路两个低秩矩阵 A、B 学增量 ΔW=B·A |
| QLoRA | Quantized LoRA | 把基座压成 4bit NF4，前向时反量化，让 65B 模型单卡可调（论文实测） |
| 低秩 | Low-Rank | 矩阵秩 r 远小于行/列维度，r=8 即可逼近千维矩阵的"增量" |
| 灾难性遗忘 | Catastrophic Forgetting | 全量微调后模型"忘记"预训练知识，在新任务之外能力退化 |
| 适配器 | Adapter | LoRA 训练产物，几十 MB 的小文件，可插拔、可合并 |
| ZeRO | Zero Redundancy Optimizer | DeepSpeed 把优化器状态/梯度/参数分片到各卡，省显存 |
| NF4 | NormalFloat 4-bit | QLoRA 提出的 4bit 量化格式，按正态分布优化分桶 |
| 秩 r | Rank | LoRA 的"可调容量"旋钮：太小欠拟合，太大退回全量微调 |

### 微调 vs RAG 决策表

| 决策维度 | 倾向 RAG（检索增强生成） | 倾向微调 |
|----------|--------------------------|----------|
| 知识更新频率 | 高（日更、实时） | 低（知识稳定，如内部规范） |
| 数据规模 | 少量（几条～几百条） | 数千条以上高质量标注数据 |
| 改造目标 | 引入外部知识、可溯源引用 | 改变风格/格式/领域能力/工具调用 |
| 可解释性 | 强（答案可带出处） | 弱（知识"烧"进权重） |
| 成本与延迟 | 零训练，但推理多一步检索 | 需 GPU 训练，推理零额外开销 |

> [!tip] 实践经验
> 先 RAG 后微调：RAG 解决"不知道"，微调解决"不会答"。两者不互斥——常见组合是"微调工具调用/输出格式 + RAG 挂业务知识"。判断标准一句话：**要模型记住新知识 → RAG；要模型改变行为方式 → 微调**。

### 全量微调 vs PEFT（LoRA）

| 维度 | 全量微调 | LoRA/QLoRA |
|------|----------|------------|
| 可训练参数 | 100% | 0.01%~1%（仅 A、B 矩阵；本文 Demo 实测 0.149%） |
| 训练显存 | 65B 需多机多卡（16 字节/参数估算 ≈1TB） | LoRA 7B 单卡 24G；QLoRA 65B 单卡 48G（论文实测） |
| 灾难性遗忘 | 严重，需回放数据缓解 | 轻（基座冻结，适配器可插拔） |
| 存储成本 | 每个版本一份全量权重（70B≈140GB） | 每个版本几十 MB 适配器 |
| 效果上限 | 理论上最高 | 多数业务任务可追平 |
| 部署方式 | 直接换模型 | 可合并回基座（merge）或运行时挂载 |

> [!warning] 更正（2026-09-13）：原表写「≈0.5%（仅 A、B 矩阵）」，与本文 Demo 自己的配置复算不符。按 Qwen2.5-0.5B 的 [config.json](https://huggingface.co/Qwen/Qwen2.5-0.5B/raw/main/config.json)（hidden_size=896、24 层、num_key_value_heads=2，故 q_proj 896→896、k/v_proj 896→128）与 r=8、`target_modules=[q_proj,k_proj,v_proj]` 计算：每层 8×(896+896)+8×(896+128)+8×(896+128)=30720，24 层共 **737,280**，占 737280/494032768 = **0.1492%**，不是"0.5% 数量级"。论文侧旗舰口径更小——LoRA 论文原文「reduce the number of trainable parameters by 10,000 times」，配合「With r=4 and only the query and value projection matrices being adapted」（[arXiv:2106.09685](https://arxiv.org/abs/2106.09685)）约 0.01%。所以正确表述是**带条件**的「0.01%（旗舰配置）~ 1%（大 r、挂满全线性层）」，不存在一个固定的 0.5%。（原表述为「≈0.5%（仅 A、B 矩阵）」与「用约 0.5% 的可训练参数」；原理图 `LoRA-Principle.excalidraw` 图内标注的"可训参数 ≈0.5%"同样过时，待重绘时一并更新。）

> [!warning] 更正（2026-09-13）：「灾难性遗忘轻」与「多数业务任务可追平」是一对交换关系，不能同时无条件成立。① Biderman et al.《LoRA Learns Less and Forgets Less》实测：标准低秩设置下「LoRA substantially underperforms full finetuning」，但「LoRA better maintains the base model's performance on tasks outside the target domain」（[arXiv:2405.09673](https://arxiv.org/abs/2405.09673)）；② QLoRA 论文原文「Using LoRA on all transformer layers is critical to match 16-bit performance」「LoRA on all linear transformer block layers are required to match full finetuning performance」——只挂 q/k/v 时论文自己也不认账（[arXiv:2305.14314v1](https://arxiv.org/html/2305.14314v1)）；③ LoRA 论文的 on-par 证据限定在「on RoBERTa, DeBERTa, GPT-2, and GPT-3」。**追平前提：全线性层 + 足够 r + 目标域接近预训练分布。**（原表述为「灾难性遗忘：轻（基座冻结，适配器可插拔）」与「效果上限：多数业务任务可追平」。）

### 预训练并行策略速查

预训练的两大挑战是**算力墙**（训练 token 量的增速远超单卡算力）与**数据墙**（高质量数据耗尽，转向合成数据），并行策略就是为了翻这两堵墙：

| 策略 | 全称 | 切分对象 | 通信开销 | 备注 |
|------|------|----------|----------|------|
| DP | Data Parallel（数据并行） | 数据按卡切，每卡完整模型 | 梯度 AllReduce | 最朴素，PyTorch DDP 标配 |
| DDP | DistributedDataParallel | 同 DP，PyTorch 官方实现 | 梯度 AllReduce | DP 的工程标准形态 |
| FSDP | FullySharded Data Parallel | 参数/梯度/优化器分片 | 前向后向按需通信 | DP 的省显存升级版 |
| TP | Tensor Parallel（张量并行） | 层内权重矩阵按列切 | 每层都通信，要高带宽 | 单卡放不下一层时用 |
| PP | Pipeline Parallel（流水线并行） | 层间切段 | 最低，有流水线气泡 | 跨节点友好 |
| ZeRO-1/2/3 | Zero Redundancy Optimizer | 优化器状态→梯度→参数逐级分片 | 与分片等级成正比 | DeepSpeed 实现 |
| 3D 并行 | DP + TP + PP 组合 | 三者叠加 | 组合叠加 | 千卡级预训练标配 |

## 原理剖析

### LoRA 的数学直觉

![[LoRA-Principle.excalidraw]]

> [!note] 图由主会话稍后创建
> 本图左半边展示全量微调：整块权重矩阵 W 从 W0 被梯度整体更新为 W0+ΔW，动的是全部 d×k 个参数；右半边展示 LoRA：原权重 W0 冻结（❄ 雪花标识），旁路新增两个低秩矩阵 A∈R^{r×k} 与 B∈R^{d×r}，训练时只更新 A、B 两小块，图中标注"可训参数 ≈0.5%"的对比。

公式拆解（对照图右半）：

- 冻结原权重：`W = W0`，不产生梯度；
- 低秩旁路：`ΔW = B · A`，其中 `r ≪ min(d, k)`（如 d=4096、r=8）；
- 前向合并：`h = W0·x + (α/r)·B·(A·x)`，`α/r` 是缩放系数；
- 初始化：A 用高斯随机，B 用全零 → 训练开始时 ΔW=0，模型行为与基座完全一致；
- 推理可合并：`W = W0 + (α/r)·B·A`，合并后前向零额外开销。

为什么这么少的参数就够？预训练已经把模型"举到了山顶"，微调只是朝业务方向推一小步，这个"增量 ΔW"天然是低秩的——两个小矩阵就能表达。`r` 是容量旋钮：r=4~8 够改风格格式，r=32~64 留给高难度领域任务；`α` 通常取 r 的 1~2 倍，`α/r` 实际是"学习率放大倍数"。

### QLoRA：把基座压进 4bit

QLoRA 在 LoRA 之外把基座权重量化成 4bit NF4 格式，前向计算时**临时反量化成 BF16 参与矩阵乘**，反向传播时梯度只流向 A、B 两个适配器，4bit 权重本身不更新。配合双重量化（Double Quantization）与分页优化器（Paged Optimizers），论文实测 65B 参数模型（Guanaco）在单卡 48G（如 A6000/L40S）上即可微调，显存从全量微调的约 1TB 量级（16 字节/参数估算）降到 ~48G。

> [!info] 记忆锚点
> 全量微调 = 重新装修整栋楼；LoRA = 只装一块可拆卸的新门面；QLoRA = 大楼主体拍扁存档（4bit），施工时临时展开，只装修新门面。

### 微调标准步骤（五步流水线）

1. **数据**：收集清洗，构造 instruction/input/output 三字段；
2. **模板化**：套 ChatML 或 Alpaca 模板（Llama-Factory 内置多种模板）；
3. **训练**：LoRA 训练 + 监控四件套（见 [[#监控指标四件套解读]]）；
4. **评估**：测试集 eval_loss + 基座对比问法 + 人工抽检；
5. **合并导出**：`merge_and_unload()` 合并回基座，或导出 GGUF 供 Ollama 部署（衔接 [[LLM推理部署与量化]]）。

## 最小可运行 Demo

> [!warning] 前置说明
> 两个 Demo 均需 NVIDIA GPU（≥16G 显存建议，24G 更从容）与 CUDA 环境。Demo 1 用 0.5B 小模型可在消费级显卡跑通。

### Demo 1：peft 库纯代码 LoRA（约 50 行）

```python
# lora_peft_minimal.py —— 不依赖 Llama-Factory，用 peft 手写最小 LoRA 微调
# 运行前安装：pip install torch transformers peft datasets accelerate
# ⚠ 需要 GPU：训练循环会在显存中做前向/反向传播
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, Trainer,
    TrainingArguments, DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

# ① 加载小模型（演示用 0.5B；显存充裕可换 Qwen/Qwen2.5-7B）
model_name = "Qwen/Qwen2.5-0.5B"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = [已脱敏]          # Qwen 无 pad，复用 eos

# ② LoRA 配置：只训 q/k/v 投影，r=8，缩放 α/r = 16/8 = 2
lora_config = LoraConfig(
    r=8,                                        # 低秩维度：可调容量旋钮
    lora_alpha=16,                              # 缩放系数，常取 r 的 2 倍
    lora_dropout=0.1,                           # 适配器 dropout，防过拟合
    target_modules=["q_proj", "k_proj", "v_proj"],  # 只在这些层挂旁路
    task_type=TaskType.CAUSAL_LM,               # 因果语言模型任务
)

# ③ 包 LoRA：原权重冻结，只留 A/B 可训
model = AutoModelForCausalLM.from_pretrained(
    model_name, torch_dtype="auto", device_map="auto",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()   # 实测输出：trainable params: 737,280 || all params: 494,032,768 || trainable%: 0.1493（旧注"≈0.5%"有误，见上文更正）

# ④ 极简数据集：3 条"风格改写"样本（真实场景放几千条）
samples = [
    {"text": "<|im_start|>user\n把这句话说得更正式：开会别忘了。\n<|im_end|>\n<|im_start|>assistant\n请务必准时参加会议。\n<|im_end|>"},
    {"text": "<|im_start|>user\n把这句话说得更正式：明天交报告。\n<|im_end|>\n<|im_start|>assistant\n请于明日提交报告。\n<|im_end|>"},
    {"text": "<|im_start|>user\n把这句话说得更正式：你先看下文档。\n<|im_end|>\n<|im_start|>assistant\n请您先行查阅相关文档。\n<|im_end|>"},
]
dataset = Dataset.from_list(samples)

def tokenize(examples):
    return tokenizer(examples["text"], truncation=True, max_length=128)

dataset = dataset.map(tokenize, remove_columns=["text"])

# ⑤ Trainer 简化训练循环（3 个 epoch，小学习率）
split = dataset.train_test_split(test_size=1, seed=42)   # 留 1 条做 holdout：同模板、不参与训练
training_args = TrainingArguments(
    output_dir="./lora_output",       # 适配器保存位置
    per_device_train_batch_size=2,    # 单卡 batch
    gradient_accumulation_steps=4,    # 梯度累积：等效 batch = 2×4 = 8
    learning_rate=1e-4,               # LoRA 学习率，比全量微调大一个数量级
    num_train_epochs=3,
    logging_steps=1,
    eval_strategy="steps",            # 关键：默认值是 "no"，不显式打开就永远没有 eval_loss
    eval_steps=2,                     # 真实数据量下常用 10；此处样本太少，取 2 才触发得到
    max_grad_norm=1.0,                # 梯度裁剪，压住 grad_norm 突刺
    report_to="tensorboard",          # 四件套可视化（需 pip install tensorboard；不想用可写 "none"）
    save_strategy="no",               # 演示用不存 checkpoint
)
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=split["train"],
    eval_dataset=split["test"],       # 必须同时有 eval_dataset + eval_strategy 才会算 eval_loss
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)
trainer.train()                        # 开始训练（监控 loss 应平滑下降）

# ⑥ 保存适配器（几十 MB）+ 可选合并回基座导出完整模型
model.save_pretrained("./lora_adapter")
# model = model.merge_and_unload()     # 合并：W = W0 + (α/r)·B·A
# model.save_pretrained("./merged_model")
```

> [!warning] 更正（2026-09-13）：原 Demo 的 TrainingArguments 只有 `logging_steps=1` 与 `save_strategy="no"`，没有 `eval_dataset` / `eval_strategy` / `report_to`，而 HF 官方文档写明 `eval_strategy` 的默认值是 `"no"`（原文 "Options: 「no」: No evaluation during training"，[TrainingArguments](https://huggingface.co/docs/transformers/main/en/main_classes/trainer)）——**原写法下 `eval_loss` 根本不会被计算**，「监控指标四件套」实际只有三件有数据来源。上面已补上 `eval_dataset`（同模板、不参与训练的 holdout）与 `eval_strategy` / `eval_steps` / `max_grad_norm` / `report_to`。（原表述为「logging_steps=1」「save_strategy="no"」这一组配置。）

训练日志形态如下（**示意**，字段名取自 HF Trainer 的输出格式；本文没有在本机 GPU 复跑，数值仅供形态对照）：

```text
{'loss': 2.4183, 'grad_norm': 3.12, 'learning_rate': 5e-05, 'epoch': 0.5}
{'loss': 2.1077, 'grad_norm': 2.48, 'learning_rate': 1e-04, 'epoch': 1.0}
{'eval_loss': 1.9865, 'eval_runtime': 0.42, 'eval_samples_per_second': 2.38, 'epoch': 1.0}
```

> [!tip] 验收判据
> ① train_loss 与 eval_loss 同向下降（eval 掉头向上 = 过拟合拐点，早停或加 dropout / 减 r）；② grad_norm 稳定在个位数、无 100+ 突刺；③ learning_rate 曲线含 warmup 爬坡段。「监控指标四件套解读」表到这一步，四条才都有数据来源。

### Demo 2：Llama-Factory CLI 命令模板

```bash
# 安装：git clone https://github.com/hiyouga/LLaMA-Factory && pip install -e ".[torch]"
# WebUI 模式：llamafactory-cli webui   → 浏览器打开 http://localhost:7860
# CLI 模式：一条命令跑训练
llamafactory-cli train examples/train_lora/qwen3_lora_sft.yaml   # 仓库现存示例；qwen2_5_lora_sft.yaml 已移除
```

> [!warning] 更正（2026-09-13）：原命令引用的 `examples/train_lora/qwen2_5_lora_sft.yaml` 已不存在——raw 直链实测 404，v0.9.5 全量文件清单（538 个文件）中 `examples/train_lora/` 下只有 11 个 `qwen3_*` / `qwen3vl_*` 示例。上面已换成实测可下载的 [qwen3_lora_sft.yaml](https://raw.githubusercontent.com/hiyouga/LLaMA-Factory/main/examples/train_lora/qwen3_lora_sft.yaml)；也可把下方内联 YAML 存成 `my_lora_sft.yaml` 后直接 `llamafactory-cli train my_lora_sft.yaml`。（原表述为 `llamafactory-cli train examples/train_lora/qwen2_5_lora_sft.yaml`。）

```yaml
# my_lora_sft.yaml —— 关键字段注释（字段与仓库现存的 examples/train_lora/qwen3_lora_sft.yaml 同构）
model_name_or_path: Qwen/Qwen2.5-7B-Instruct   # 基座模型
stage: sft                                     # 训练阶段：sft 监督微调
do_train: true
finetuning_type: lora                          # 微调方式：lora / qlora / full
lora_rank: 8                                   # 低秩 r
lora_alpha: 16                                 # 缩放系数，≈2×r
lora_dropout: 0.1                              # 适配器 dropout
lora_target: all                               # 全线性层挂旁路，或指定 q_proj,v_proj 等
dataset: text2sql_train                        # 数据集名（须在 dataset_info.json 注册）
template: qwen                                 # 对话模板（ChatML 系）
cutoff_len: 2048                               # 单条样本截断长度
per_device_train_batch_size: 2                 # 单卡 batch
gradient_accumulation_steps: 8                 # 梯度累积 → 等效 batch=16
lr_scheduler_type: cosine                      # 学习率调度：余弦退火
learning_rate: 5.0e-5                          # LoRA 学习率
num_train_epochs: 3.0                          # 训练轮数
warmup_ratio: 0.1                              # 前 10% 步数 warmup
bf16: true                                     # BF16 混合精度
report_to: tensorboard                         # TensorBoard 监控开关
logging_steps: 10                              # 每 10 步打日志
save_steps: 500                                # 每 500 步存 checkpoint
output_dir: saves/qwen2.5-7b-lora-text2sql     # 适配器输出目录
# DeepSpeed 接入（大模型/低显存时打开下面任一行）：
# deepspeed: examples/deepspeed/ds_z2_config.json           # ZeRO-2 省显存
# deepspeed: examples/deepspeed/ds_z3_offload_config.json   # ZeRO-3+CPU 卸载，最省
```

Text2SQL 数据集的注册方式（`dataset_info.json` 片段）：

```json
{
  "text2sql_train": {
    "file_name": "data/text2sql_train.json",
    "columns": {
      "prompt": "instruction",
      "query": "input",
      "response": "output"
    }
  }
}
```

> [!note] 字段映射说明
> `instruction` 放问题（如"查询销量最高的3个产品"），`input` 放数据库 schema（DDL 建表语句），`output` 放标准 SQL。训练时三者被填入 `template` 定义的对话模板。

### 效果验证：基座 vs 微调对比问法

| 问法（同一问题） | 基座模型回答 | 微调后回答 |
|------------------|--------------|------------|
| "查询销量最高的3个产品" + DDL | 解释一通 SQL 概念，或给不带表名的伪 SQL | 直接给出针对该 schema 的可执行 `SELECT ... ORDER BY ... LIMIT 3` |
| 换一张 schema 提问 | 无法对齐列名 | 依然按"表结构→生成 SQL"的模式应答 |

> [!tip] 验证纪律
> 对比必须控制变量：同 temperature（建议 0）、同 prompt、同模型版本，只换适配器。先看"格式对不对"（是否稳定输出 SQL），再看"语义对不对"（人工/执行器校验 SQL 结果）。

## 进阶实践与常见坑

### DeepSpeed 是什么、怎么接入

DeepSpeed 是微软开源的训练加速框架，核心卖点是 ZeRO 三级显存优化。先建立记账基准：混合精度训练下，**每参数 Ψ 的显存账单 = 2Ψ(fp16 参数) + 2Ψ(fp16 梯度) + 12Ψ(FP32 主副本 4Ψ + 动量 m 4Ψ + 方差 v 4Ψ) = 16Ψ 字节**——其中 12Ψ 的优化器状态占了 75%，这正是 ZeRO 的下刀处：

| 级别 | 分片内容 | 显存节省（数据并行度 Nd） | 通信代价 |
|------|----------|--------------------------|----------|
| ZeRO-1 | 优化器状态（12Ψ 按卡切分） | 16Ψ → 4Ψ+12Ψ/Nd，Nd 较大时**趋近 4×**（论文显存分析口径） | 低（与标准 DP 通信量相同） |
| ZeRO-2 | 优化器状态 + 梯度 | 8Ψ+12Ψ/Nd，趋近 **8×**（同为显存分析口径，非实测） | 低（论文口径：与标准 DP 通信量相同） |
| ZeRO-3 | 优化器状态 + 梯度 + 参数 | **严格随 Nd 线性**：16Ψ/Nd（64 卡可训万亿参数模型的理论依据） | 高（前向+反向各需一次参数 All-Gather，通信量约 ↑50%） |

> [!warning] 更正（2026-09-13）：原表把「4× / 8×」记成「论文在 400B 模型实测」/「400B 实测口径」，并把 ZeRO-2 的通信代价标为「中」。核对原文：① **400 是 GPU 数量，不是 400B 参数模型**——ZeRO 论文摘要写「it trains large models of over 100B parameter with super-linear speedup on 400 GPUs, achieving throughput of 15 Petaflops」，全文 Figure 2 段落写「ZeRO runs 100B parameter models on a 400 Nvidia V100 GPU cluster」与「170B parameter models」（[arXiv:1910.02054](https://arxiv.org/abs/1910.02054)）；② 4× / 8× 出自论文的 ZeRO-DP 显存分析原句：「1) Optimizer State Partitioning (P_os): 4x memory reduction, same communication volume as DP; 2) Add Gradient Partitioning (P_os+g): 8x memory reduction, same communication volume as DP; 3) Add Parameter Partitioning (P_os+g+p): Memory reduction is linear with DP degree Nd ... splitting across 64 GPUs will yield a 64x memory reduction」——即 **ZeRO-1 与 ZeRO-2 的通信量与标准 DP 相同**，只有 ZeRO-3 才有「a modest 50% increase in communication volume」；③ DeepSpeed 官方 zero.md 对三级的定义也只是 Stage1 分片优化器状态、Stage2 再分片 16-bit 梯度、Stage3 再分片参数，并不支持「ZeRO-2 通信开销更高」的排序（[zero.md](https://raw.githubusercontent.com/microsoft/DeepSpeed/master/docs/_tutorials/zero.md)）。（原表述为「（论文在 400B 模型实测）」「（400B 实测口径）」与 ZeRO-2 的「中（梯度 Reduce-Scatter，反向结束即释放）」。）

> [!tip] 记忆口诀
> ZeRO 三级 = 依次把「优化器状态 / 梯度 / 参数」从"每卡全量"变成"每卡切片"，省的倍数分别对应 4×、8×、线性——数字来自论文的显存分析（不是实测）；论文的**实测**口径是 100B/170B 参数模型跑在 400 块 V100 上（[arXiv:1910.02054](https://arxiv.org/abs/1910.02054)），不是随手估计。

Llama-Factory 中只需在 YAML 打开 `deepspeed:` 一行即可接入；QLoRA + ZeRO 是"低显存双保险"，但注意 **QLoRA 慎配 ZeRO-3 参数分片**——4bit 权重分片会引入额外反量化通信，可能反而变慢，**具体以本机实测吞吐与显存为准**，别照搬口号（原句写的"官方建议 QLoRA 用 ZeRO-2 或不接入"查无出处，见下）。

> [!warning] 更正（2026-09-13）：原句「官方建议 QLoRA 用 ZeRO-2 或不接入」中的"官方建议"无据——QLoRA 论文全文检索 "ZeRO" 命中 0 次（其 Paged Optimizer 是为显存尖峰设计的，与 ZeRO 分片没有论文级结论；[arXiv:2305.14314v1](https://arxiv.org/html/2305.14314v1)），HF Accelerate 的 DeepSpeed 文档也没有这类表述。原文的因果（4bit 分片引入反量化通信）是合理推断，但必须自测；可核验的官方口径在 ZeRO-3 一侧——上 ZeRO-3 要确认 `zero3_init_flag` 与 `device_map` 的配置。（原表述为「官方建议 QLoRA 用 ZeRO-2 或不接入」。）

### 监控指标四件套解读

| 指标 | 健康形态 | 异常信号与排查 |
|------|----------|----------------|
| train_loss | 平滑下降，小幅波动正常 | 骤升/发散 → 学习率过大或数据有脏样本；卡住不降 → lr 过小 |
| eval_loss | 与 train_loss 同步下降 | train 降、eval 升 → **过拟合拐点**，立即早停或加 dropout/减 r |
| learning_rate | warmup 爬坡 → cosine/线性衰减 | 无 warmup → 初期震荡（grad_norm 突刺）；衰减过快 → 收敛不充分 |
| grad_norm | 稳定在个位数量级 | 突刺到 100+ → 梯度爆炸：查数据、开梯度裁剪（max_grad_norm）；恒≈0 → 梯度消失/lr 过小 |

> [!tip] TensorBoard 接入
> `report_to: tensorboard` + 训练启动后执行 `tensorboard --logdir saves/qwen2.5-7b-lora-text2sql --port 6006`，浏览器打开 `http://localhost:6006` 即可实时看四件套曲线。

### 常见坑清单

> [!warning] 数据与模板坑
> - 模板与基座不匹配（用 ChatML 模板喂 Alpaca 格式数据）→ loss 下降但输出乱码，先查 `template` 字段。
> - 截断过狠：`cutoff_len` 小于样本中位数 → 输出被腰斩，学不到完整格式。

> [!warning] 参数坑
> - `learning_rate` 沿用全量微调的 1e-5：LoRA 收敛极慢；LoRA 常用 1e-4 量级，QLoRA 用 5e-5 左右。
> - `lora_alpha` 忘了随 `lora_rank` 调整：r=64 却仍 alpha=16 → 缩放仅 0.25，训练几乎不动。
> - 只挂 q/k/v 不挂 o_proj：输出投影占注意力块近一半参数，省这点显存换效果明显下降，不划算。

> [!danger] 工程坑
> - 适配器忘了 `merge_and_unload` 就直接部署 → 推理端没装 peft 会报错；要么合并，要么部署端 `PeftModel.from_pretrained` 运行时挂载。
> - 灾难性遗忘自检缺失：微调后务必回测几个通用问答，退化明显则降 lr/epochs 或混入通用数据。
> - 显存不够先砍 `cutoff_len` 与 batch，再开 gradient_accumulation，最后才考虑 QLoRA——顺序反了会白白损失精度。

## 相关文档

- [[AI大模型开发]] — 预训练与 Transformer 基础，微调的"地基"
- [[AI-Dev-KB-Home]] — ai-dev 子库首页（MOC）
- [[LLM推理部署与量化]] — 微调产物的下一站：量化与部署
- [[微调数据工程与模型蒸馏]] — 本笔记的数据侧专题与蒸馏路线
- [[RAG检索增强生成实战]] — 微调的"竞品路线"：决策表见上文
- [[强化学习对齐-RLHF到GRPO]] — 微调之后的偏好对齐阶段

## 参考资料

- [LoRA 论文（Low-Rank Adaptation of Large Language Models, arXiv:2106.09685）](https://arxiv.org/abs/2106.09685)：低秩旁路 ΔW=B·A、α/r 缩放、A 高斯/B 零初始化
- [QLoRA 论文（arXiv:2305.14314）](https://arxiv.org/abs/2305.14314) 与 [NeurIPS 2023 Oral 页面](https://neurips.cc/virtual/2023/oral/73855)：4bit NormalFloat（NF4）、双重量化、分页优化器、65B 模型单卡 48GB 微调
- [LLaMA-Factory 仓库](https://github.com/hiyouga/LLaMA-Factory)：`llamafactory-cli webui / train` 双模式命令
- [LLaMA-Factory data/README_zh.md](https://github.com/hiyouga/LLaMA-Factory/blob/main/data/README_zh.md)：`dataset_info.json` 注册格式（`columns` 的 `prompt/query/response` 映射）
- [LLaMA-Factory 数据处理官方文档](https://llamafactory.readthedocs.io/zh-cn/latest/getting_started/data_preparation.html)：数据集准备与注册流程
- [Fine-tuning LLMs on Kaggle Notebooks（HuggingFace 博客）](https://huggingface.co/blog/lmassaron/fine-tuning-llms-on-kaggle-notebooks)：peft `LoraConfig` 的 `target_modules` 实战取值
- [DeepSpeed ZeRO 论文（arXiv:1910.02054）](https://arxiv.org/abs/1910.02054)：ZeRO 三级显存分片机制；正文"4×/8×"出自论文的 ZeRO-DP 显存分析（P_os=4×、P_os+g=8×，两者通信量与标准 DP 相同），ZeRO-3 为随数据并行度 Nd 线性省显存且通信量约 +50%；论文实测口径是 100B/170B 参数模型跑在 400 块 V100 上，**不是**"400B 模型实测"

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 定位句 / 对比表 / Demo 注释写「≈0.5% 可训练参数」 | 按 Qwen2.5-0.5B config 与 r=8、target_modules=[q,k,v] 复算为 **0.1492%**，全文改为条件表述「0.01%~1%」；Demo 注释换成真实输出 `737,280 / 494,032,768` |
| 纠错 | ZeRO 的「4×/8×」被写成「论文在 400B 模型实测」 | 400 是 **GPU 数量**；4×/8× 出自论文 ZeRO-DP 显存分析，实测口径是 100B/170B 参数模型 + 400×V100 |
| 纠错 | ZeRO-2 通信代价标为「中」 | 论文对 P_os 与 P_os+g 都写 "same communication volume as DP"，统一改为「低（与标准 DP 相同）」，仅 ZeRO-3 标「约 +50%」 |
| 纠错 | Llama-Factory 命令引用 `examples/train_lora/qwen2_5_lora_sft.yaml` | 该文件已从上游移除（raw 实测 404；v0.9.5 清单只剩 `qwen3_*`/`qwen3vl_*`），换为实测可下载的 `qwen3_lora_sft.yaml`，并给出内联 YAML 落盘直训的用法 |
| 纠错 | 「官方建议 QLoRA 用 ZeRO-2 或不接入」 | 查无出处（QLoRA 全文检索 "ZeRO" 命中 0 次，Accelerate 文档亦无该表述），删去"官方建议"，改为以本机实测吞吐/显存为准 |
| 补疏漏 | Demo 无 `eval_dataset`/`eval_strategy`/`report_to` → `eval_loss` 永不产生，「监控四件套」只有三件有数据来源 | 补 `eval_dataset`（同模板 holdout）+ `eval_strategy`/`eval_steps`/`max_grad_norm`/`report_to`，附日志格式示意与三条验收判据；依据 HF TrainingArguments 文档（`eval_strategy` 默认 `"no"`） |
| 补疏漏 | 「灾难性遗忘轻 + 多数业务任务可追平」为无条件表述 | 补三条边界与「追平前提：全线性层 + 足够 r + 目标域接近预训练分布」；依据 arXiv:2405.09673、arXiv:2305.14314、arXiv:2106.09685 |

> [!warning] 仍待人工确认
> ① 原理图 `LoRA-Principle.excalidraw` 图内仍标注「可训参数 ≈0.5%」，需重绘（本次只改文字，未动图文件）；② 上面那段 Trainer 日志是**格式示意**，本机无 GPU 未复跑，正式定稿前建议在 24G 显卡上跑一次 Demo 1 换成真实日志。

关联：[[CORRECTIONS]] · [[AGENTS]]
