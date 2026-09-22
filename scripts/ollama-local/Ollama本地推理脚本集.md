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

## 一键启停与学习入口（2026-09-22 新增）

> [!tip] 日常只需要记三个命令（都在 `D:\OllamaModels\bin\`，该目录已在 PATH 里，可裸命令调用）
> | 命令 | 作用 |
> |---|---|
> | `llm-start` | 拉起 Ollama 服务（幂等，已在跑就跳过） |
> | `llm-stop` | 完整停止并**回收残留**（含 Python 客户端、校验端口） |
> | `llm-learn` | 一条命令进入学习实践台：先起服务，再进菜单 |

**为什么 `llm-stop` 要单独写**：`taskkill ollama.exe` **不会**杀掉它的子进程 `llama-server.exe`。
实测残留 2 个孤儿占 \7 GB 内存 + 3802 MiB 显存，模型 GPU 占比掉到 8%、解码速度腰斩。
所以必须按 **app → ollama → llama-server** 的顺序杀整棵树。

> [!warning] 三个实测出来的坑（都实际踩过）
> 1. **验证不能用 `Get-Process ollama,llama-server`** —— 这是**精确匹配**，**看不见 `ollama app.exe`**。
>    实测：`Get-Process ollama` 只返回 `ollama`；`Get-Process *ollama*` 才返回 `ollama` + `ollama app`。
>    用精确匹配时的「已清理干净」是**假通过**。
> 2. **`llm-start lab` 里 `%PY%` 必须写成 `!PY!`** —— 在 `if (...)` 块内 `%VAR%` 在**解析期**就展开，
>    而同一块里的 `set PY=` 那时还没执行，会展开成空 → **静默失败**。
> 3. **`llm-learn.cmd` 必须存成 GBK** —— cmd 按 ANSI(936) 读批处理文件，存 UTF-8 菜单会乱码。
>    （`llm-start.cmd` / `llm-stop.cmd` 是纯 ASCII，不受影响。）

**实测速度**：`llm-stop` **3.3 s**、`llm-start` 冷启动 **11.3 s**。
早期版本 `llm-stop` 要 **6.2 s**——多出来的时间全花在一个「有界端口轮询」上：
curl 探**已停止**的端口要 **1178 ms**（连接被丢弃而非拒绝），所以轮询**从不提前跳出**。
`taskkill /F` 本来就是同步的，等待纯属多余，已删除。

> [!info] `llm-stop` 的端口检查为什么**只报告、不作判据**
> 早期版本拿「11434 与 3000 都已释放」当验收条件，错了两处：
> 实测发现 `ollama app.exe` **可以在运行而 3000 没有监听**（"app 常驻占 3000"的假设不成立）；
> 而 3000 是最常见的开发端口之一，任何无关程序占用它都会让脚本**误报失败并 exit 1**。
> 现在的验收判据是**进程检查**，端口只打印出来供人核对。

## 学习实践台（2026-09-22 新增）

| 脚本 | 位置 | 学什么 |
|---|---|---|
| `agent-lab.py` | `bin\` | **裸 API + 手写 ReAct 循环**：每一轮的工具名 / 参数 / 返回值都打印出来 |
| `lg-lab.py` | `lab\` | **LangGraph 6 节课**：最小图 → 条件边 → ReAct agent → reducer → checkpointer → 自由实践 |
| `test_langgraph_skill.py` | `lab\` | **能力自测**：先 stub 验图接线，再测模型（结果见 [[本地模型能力矩阵与任务路由]] 四·九） |

`lab\` 用**独立 venv**（`lab\.venv`），不污染 miniconda base：

```bash
D:\ProgramData\miniconda3\python.exe -m venv D:\OllamaModels\lab\.venv
D:\OllamaModels\lab\.venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple langchain==1.4.2 langgraph==1.2.12 langchain-ollama==1.1.0
```

> [!note] 为什么 venv 必须钉版本
> `lg-lab.py` 依赖 `from langchain.agents import create_agent`（**langchain 1.x 才有**；
> 旧的 `langgraph.prebuilt.create_react_agent` 已废弃，参数也从 `prompt=` 改成了 `system_prompt=`）。
> 不钉版本，将来装到 2.x 会在 import 处直接失败。

## 补登：本表此前未收录的脚本

| 脚本 | 用途 |
|---|---|
| `test_toolcall_skill.py` | 工具调用合法性 + 工具选择（能不能学 Agent 的分水岭） |
| `test_faithful_writeup.py` | 忠实扩写**初测**（5 素材 × 4 模型） |
| `test_faithful_ext.py` / `test_faithful_ext2.py` | 忠实扩写**扩测**（8 素材 × 6 模型）；**v2 修掉了 v1 的「600 字」假阳性** |
| `faithful_ext2_raw.json` | v2 的**原始输出落盘**，可逐条人工复核 |
| `test_longrun_new.py` | 新稠密模型长输出 / 复读复测 |

## 关联

- [[本地LLM部署与显存实测-4GB卡]] —— 这些脚本量出来的**实测账本**（性能表、坑位、选型）
- [[本地推理栈探测与调优方法论]] —— 这些脚本**为什么这么写**：探针设计、对照原则、录包法
- [[CORRECTIONS]] —— 本次实测中判错的结论（C-026\C-028 测量类、C-029 同一故障三次误判）
- [[AGENTS]] —— 知识库协作规范（脚本归档要求、部署四规则）
- [[AI-Dev-KB-Home]] —— 所属子库 MOC
