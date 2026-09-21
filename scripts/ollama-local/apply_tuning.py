"""按实测最优档给每个模型烤入 num_ctx（+必要时 num_gpu），同名覆盖。

安全性：
  - 用 `FROM <模型名>` 继承原有 TEMPLATE / RENDERER / PARSER / 采样参数
  - 覆盖后逐项校验这些关键片段是否仍在
  - 原始 Modelfile 已备份在 modelfiles_backup/
"""
import json
import os
import os
import subprocess
import time

import requests

OLLAMA = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
W = r"D:\OllamaModels\bench"
API = "http://127.0.0.1:11434/api"

# 模型 -> (num_ctx, 额外参数dict)
PLAN = {
    "granite4:micro-h":   (32768, {}),                 # 32K 无代价，DSH 主力
    "qwen2.5-coder:3b":   (16384, {}),                 # 32K 掉 36%
    "qwen3.5:0.8b":       (16384, {}),                 # 无代价，留余量
    "qwen3.5:2b":         (16384, {"num_gpu": 999}),   # 强制满 GPU（实测 1.76x）
    "qwen3-vl:2b":        (8192,  {}),                 # 极度上下文敏感：16K 掉 2.7 倍
    "granite4:tiny-h":    (8192,  {}),                 # CPU 为主，省内存
    "gpt-oss:20b":        (16384, {}),                 # 省内存
}

KEY_SECTIONS = ("TEMPLATE", "RENDERER", "PARSER")


def snapshot(model):
    r = subprocess.run([OLLAMA, "show", "--modelfile", model],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="ignore", timeout=120)
    lines = r.stdout.splitlines()
    return {k: any(l.startswith(k) for l in lines) for k in KEY_SECTIONS}


def apply(model, ctx, extra):
    before = snapshot(model)
    mf = os.path.join(W, "_tune.txt")
    body = ["FROM %s" % model, "PARAMETER num_ctx %d" % ctx]
    for k, v in extra.items():
        body.append("PARAMETER %s %s" % (k, v))
    with open(mf, "w", encoding="utf-8") as f:
        f.write("\n".join(body) + "\n")
    r = subprocess.run([OLLAMA, "create", model, "-f", mf],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="ignore", timeout=600)
    os.remove(mf)
    if r.returncode:
        return None, (r.stderr or r.stdout)[:200], before
    after = snapshot(model)
    lost = [k for k in KEY_SECTIONS if before[k] and not after[k]]
    return (ctx, extra), (None if not lost else "丢失片段: %s" % lost), before


print("模型                        num_ctx   额外          结果")
print("-" * 66)
for model, (ctx, extra) in PLAN.items():
    res, err, before = apply(model, ctx, extra)
    ex = ",".join("%s=%s" % kv for kv in extra.items()) or "-"
    print("%-26s %-8d %-13s %s" % (model, ctx, ex, err or "OK ✅"))
    time.sleep(0.5)
