"""受控捞针对照：固定 num_ctx，同一套题、同一埋点，跨模型可比。

动机：此前那条「混合架构 → 长上下文检索弱」的推断，对照里**规模、专训、架构三个变量
同时变了**（成功者 3B+代码专训，失败者 0.8–2B+混合），n 又只有 3。不足以定因果。
本脚本把 **num_ctx 固定为 8192**，让所有模型在完全相同的条件下过同一组题。
"""
import json
import re
import time

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}
CTX = 8192
NEEDLE = "门禁密码是 7XK9-QW2M"
FILLER = ("本市轨道交通建设持续推进，各条线路按计划有序开展。"
          "工程部门将安全生产放在首位，定期开展隐患排查与应急演练。"
          "同时，沿线配套的商业与住宅项目也在同步规划中。")

MODELS = ["granite4:micro-h", "granite4:tiny-h", "qwen3.5:0.8b", "qwen3.5:2b",
          "qwen3-vl:2b", "qwen2.5-coder:3b", "llama3.2:3b", "phi4-mini"]


def ask(model, doc, q):
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": q + "\n\n" + doc}],
            "options": {"num_predict": 100, "num_ctx": CTX, "temperature": 0}}
    d = requests.post(API + "/chat", headers=H,
                      data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                      timeout=2400).json()
    return (d.get("message", {}).get("content") or "", d)


print("受控捞针：num_ctx 固定 %d，三个埋点，每题同一填充文" % CTX)
print("%-20s %-8s %-8s %-8s %s" % ("模型", "开头", "中间", "结尾", "prefill"))
print("-" * 62)

for model in MODELS:
    hits = []
    prefill = 0
    for depth in (0.05, 0.5, 0.92):
        # 固定填充体量：约 0.5 * CTX token 的填充文
        units = 190
        head_n = max(1, int(units * depth))
        tail_n = max(1, units - head_n)
        doc = FILLER * head_n + "\n【注意】" + NEEDLE + "。\n" + FILLER * tail_n
        q = "[nonce:%d] 下面是一份长文档，请只回答：门禁密码是多少？没有就答『未提及』。" % time.time_ns()
        try:
            ans, d = ask(model, doc, q)
        except Exception as exc:
            hits.append("超时"); continue
        hits.append("OK" if "7XK9" in ans else "x")
        pc, pd = d.get("prompt_eval_count", 0), d.get("prompt_eval_duration", 1) or 1
        prefill = max(prefill, pc / (pd / 1e9) if pd else 0)
    score = sum(1 for h in hits if h == "OK")
    print("%-20s %-8s %-8s %-8s %.0f tok/s   %d/3" %
          (model, hits[0], hits[1], hits[2], prefill, score), flush=True)
