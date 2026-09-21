"""量化 num_ctx 对响应速度的影响：同一模型在不同上下文下的 decode 速度与 GPU 占比。

用途：为每个模型定出「既够用又不掉 GPU」的上下文档位。
"""
import json
import time

import requests

NATIVE = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}
Q = ("Write a detailed paragraph explaining how a bicycle works, "
     "covering the frame, wheels, drivetrain, and steering. ")


def measure(model, ctx):
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": Q}],
            "options": {"num_predict": 96, "num_ctx": ctx, "temperature": 0}}
    try:
        d = requests.post(NATIVE + "/chat", headers=H,
                          data=json.dumps(body).encode("utf-8"), timeout=1800).json()
    except Exception as exc:
        return None, str(exc)
    ec, ed = d.get("eval_count", 0), d.get("eval_duration", 1) or 1
    ps = requests.get(NATIVE + "/ps", timeout=30).json().get("models", [])
    gpu = None
    for m in ps:
        if m.get("model") == model:
            s = m.get("size", 0) or 1
            gpu = round((m.get("size_vram", 0) or 0) / s * 100)
    return {"decode": ec / (ed / 1e9), "gpu": gpu,
            "tokens": ec}, None


for model in ["granite4:micro-h", "qwen2.5-coder:3b", "qwen3.5:0.8b"]:
    print("===", model)
    for ctx in (4096, 8192, 16384, 32768):
        r, err = measure(model, ctx)
        if err:
            print("   ctx=%-6d 失败: %s" % (ctx, err[:60]))
            continue
        print("   ctx=%-6d decode=%6.1f tok/s   GPU %s%%" %
              (ctx, r["decode"], r["gpu"]))
        time.sleep(1)
