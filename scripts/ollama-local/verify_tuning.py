"""验证调优效果：不指定 num_ctx，用模型烤入的值，测 decode 速度与 GPU 占比。"""
import json
import time

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}
Q = ("Write a detailed paragraph explaining how a bicycle works, "
     "covering the frame, wheels, drivetrain, and steering. ")

MODELS = ["granite4:micro-h", "qwen2.5-coder:3b", "qwen3.5:0.8b", "qwen3.5:2b",
          "qwen3-vl:2b", "granite4:tiny-h", "gpt-oss:20b"]

print("模型                     ctx      GPU    decode")
print("-" * 54)
for model in MODELS:
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": Q}],
            "options": {"num_predict": 96, "temperature": 0}}
    try:
        d = requests.post(API + "/chat", headers=H,
                          data=json.dumps(body).encode("utf-8"), timeout=2400).json()
    except Exception as exc:
        print("%-24s 失败: %s" % (model, str(exc)[:30]))
        continue
    if "eval_count" not in d:
        print("%-24s 报错: %s" % (model, json.dumps(d)[:70]))
        continue
    ec, ed = d.get("eval_count", 0), d.get("eval_duration", 1) or 1
    ps = requests.get(API + "/ps", timeout=30).json().get("models", [])
    ctx = gpu = None
    for m in ps:
        if m.get("model", "").startswith(model.split(":")[0]):
            s = m.get("size", 0) or 1
            gpu = round((m.get("size_vram", 0) or 0) / s * 100)
            ctx = m.get("context_length")
    print("%-24s %-8s %-6s %.1f tok/s" % (model, ctx, "%s%%" % gpu, ec / (ed / 1e9)))
    time.sleep(1)
