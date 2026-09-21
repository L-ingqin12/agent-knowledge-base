---
title: Ollama 本地推理脚本集
aliases: [ollama-local脚本, 本地LLM脚本, llm入口脚本]
tags: [ai, ai/learning, reference, meta]
created: 2026-09-22
updated: 2026-09-22
status: review
---

# Ollama 本地推理脚本集

> [!abstract] 这个目录是什么
> 本机 Ollama 部署的**全部配套脚本**：一行式推理入口、参数调优应用、性能基准、探针与逃生备份。
> 对应知识文档：[[本地LLM部署与显存实测-4GB卡]]（实测账本） · [[本地推理栈探测与调优方法论]]（怎么做出来的）
> 运行环境：全局 Python `D:\ProgramData\miniconda3\python.exe`；Ollama 在 `http://127.0.0.1:11434`。

## 脚本清单

| 脚本 | 何时用 | 一句话 |
|---|---|---|
| **`llm.py` / `llm.cmd`** | 日常 | **一行式本地推理入口**。把琐碎任务从远端卸载：`llm "问题"`、`git diff \| llm "写 commit"`、`-t coder\|chat\|vision\|fast\|smart\|moe`、`-f 文件`、`-i 图片`、`--json`。**建议把所在目录加入 PATH** |
| `apply_tuning.py` | 换机/重装后 | 按实测最优档给 7 个模型烤入 `num_ctx`（+`num_gpu`）。同名覆盖，会校验 TEMPLATE/RENDERER/PARSER 未丢失 |
| `apply_sampling.py` | 同上 | 烤入各厂商模型卡的**官方推荐采样参数**（Qwen3.5 / Qwen3-VL / gpt-oss） |
| `verify_tuning.py` | 改完参数后 | 不指定 `num_ctx` 复测各模型实际驻留的上下文、GPU 占比与 decode 速度 |
| `tune_ctx_speed.py` | 定上下文档位时 | **上下文扫描**：同一模型在 4K/8K/16K/32K 下的 decode 与 GPU% |
| `test_needle_controlled.py` | 跨模型比较 | **受控捞针对照**：固定 num_ctx、同一套题与埋点，让模型间可比（架构/规模都不能预测检索能力，只能实测） |
| `test_accuracy.py` | 选准确性敏感任务前 | 8 题客观可判定的知识题，分档暴露「术语全称编造」 |
| `test_longrun.py` | 评估可用性 | **长输出 + 长上下文捞针**：测是否自然收尾、是否退化成复读机、能否从长文档里捞出唯一事实 |
| `bench_model.py` | 新增模型时 | 通用基准：驻留 + decode（自动/强制满 GPU）+ 长提示 prefill |
| `stress_chat.py` | 评估聊天体感 | 多轮对话压测，看随上下文增长的首字延迟与单轮耗时劣化 |
| `ollama_api.py` | 写集成时 | 客户端封装（默认走原生端点并关思考）。含 `chat()` / `stream()` / `v1_chat()` |
| `test_vision.py` + `make_testimage.py` | 验多模态 | 用纯标准库生成**内容已知**的测试图（红圆/蓝方/3绿块），再让模型描述并比对 |
| `modelfiles_backup/` | **出事时** | 7 个模型的**原始 Modelfile 备份** —— 唯一的还原依据，见下 |
| `user_path_backup.txt` | 出事时 | 改 PATH 之前的原值 |

## 逃生机制（改坏了怎么回去）

> [!danger] 两条必须记住的还原规则
> 1. **`ollama show --modelfile <模型> > 备份`** —— 每个模型在调优前都做了这份备份，就在 `modelfiles_backup/`。
> 2. **`FROM <模型名>` 会「继承」现有参数，删不掉。** 想去掉烤错的参数（如试错的 `num_batch`），
>    只写同名 `FROM` **无效**——必须用备份里的 **`FROM <blob 路径>`** 重建。
>    ⚠️ 而只取备份的 `FROM` 行会**丢掉 TEMPLATE**（本会话实测把 granite4 的消息模板弄没了一次）。
>    **正确做法：整份备份文件 + 追加你要的参数**，再 `ollama create <同名> -f`。

还原示例（把 granite4 恢复成「原模板 + 只要 num_ctx 32768」）：

```bash
# 用完整备份 + 追加参数，切勿只取 FROM 行
cat modelfiles_backup/granite4_micro-h.modelfile > /tmp/mf
echo "PARAMETER num_ctx 32768" >> /tmp/mf
ollama create granite4:micro-h -f /tmp/mf
```

## 关联

- [[本地LLM部署与显存实测-4GB卡]] —— 这些脚本量出来的**实测账本**（性能表、坑位、选型）
- [[本地推理栈探测与调优方法论]] —— 这些脚本**为什么这么写**：探针设计、对照原则、录包法
- [[CORRECTIONS]] —— 本次实测中判错的结论（C-026~C-028 测量类、C-029 同一故障三次误判）
- [[AGENTS]] —— 知识库协作规范（脚本归档要求、部署四规则）
- [[AI-Dev-KB-Home]] —— 所属子库 MOC
