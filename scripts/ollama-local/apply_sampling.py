"""按各厂商模型卡的官方推荐采样参数烤入模型（同名覆盖）。

依据（全部来自厂商模型卡/生成配置原文）：
  * Qwen3.5 非思考·文本: temperature 1.0, top_p 1.00, top_k 20, min_p 0, presence_penalty 2.0
  * Qwen3-VL Thinking·视觉: temperature 1.0, top_p 0.95, top_k 20, presence_penalty 0.0
  * gpt-oss: temperature 1.0, top_p 1.0（OpenAI 官方 README）
  * granite4 / qwen2.5-coder: 未找到官方推荐 → 不动
"""
import os
import os
import subprocess

OLLAMA = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
W = r"D:\OllamaModels\bench"

PLAN = {
    "qwen3.5:0.8b": {
        "temperature": 1.0, "top_p": 1.0, "top_k": 20,
        "min_p": 0.0, "presence_penalty": 2.0, "repeat_penalty": 1.0,
    },
    "qwen3.5:2b": {
        "temperature": 1.0, "top_p": 1.0, "top_k": 20,
        "min_p": 0.0, "presence_penalty": 2.0, "repeat_penalty": 1.0,
    },
    "qwen3-vl:2b": {
        "temperature": 1.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0,
    },
    "gpt-oss:20b": {
        "temperature": 1.0, "top_p": 1.0,
    },
}

print("模型                    烤入参数                                   结果")
print("-" * 76)
for model, params in PLAN.items():
    mf = os.path.join(W, "_sp.txt")
    body = ["FROM %s" % model] + ["PARAMETER %s %s" % kv for kv in params.items()]
    with open(mf, "w", encoding="utf-8") as f:
        f.write("\n".join(body) + "\n")
    r = subprocess.run([OLLAMA, "create", model, "-f", mf], capture_output=True,
                       text=True, encoding="utf-8", errors="ignore", timeout=600)
    os.remove(mf)
    desc = " ".join("%s=%s" % kv for kv in params.items())
    print("%-22s %-42s %s" % (model, desc[:42], "OK" if r.returncode == 0 else
                              ((r.stderr or r.stdout)[:60])))
