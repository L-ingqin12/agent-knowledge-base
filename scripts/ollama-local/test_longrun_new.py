"""对新增的两个稠密模型做长输出 + 复读检测（与既有模型同一套题、同一口径）。"""
import json
import time

import requests

API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}
LONG_OUT_Q = ("请写一篇尽可能详细完整的文章，主题是《城市轨道交通的发展历程与未来趋势》，"
              "要求覆盖：早期有轨电车、地铁的诞生、自动化驾驶、跨城互联、未来超高速管道交通。"
              "每个部分都要展开论述，写得越长越好，不要提前结束。")


def repeat_ratio(text, n=8):
    if len(text) < n * 2:
        return 0.0
    grams = [text[i:i + n] for i in range(0, len(text) - n)]
    return 1.0 - len(set(grams)) / len(grams) if grams else 0.0


for model, ctx in [("llama3.2:3b", 8192), ("phi4-mini:latest", 8192)]:
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": LONG_OUT_Q}],
            "options": {"num_predict": 3000, "num_ctx": ctx, "temperature": 0.7}}
    t0 = time.time()
    try:
        d = requests.post(API + "/chat", headers=H,
                          data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                          timeout=2400).json()
    except Exception as exc:
        print("  %-20s 失败/超时: %s" % (model, str(exc)[:50]), flush=True)
        continue
    m = d.get("message", {})
    txt = (m.get("content") or m.get("thinking") or "")
    ec, ed = d.get("eval_count", 0), d.get("eval_duration", 1) or 1
    paras = [p for p in txt.split("\n") if p.strip()]
    print("  %-20s %5d tok  %5.1f tok/s  finish=%-8s 重复率=%4.1f%%  段=%d/唯一%d  %.0fs"
          % (model, ec, ec / (ed / 1e9), d.get("done_reason"), repeat_ratio(txt) * 100,
             len(paras), len(set(paras)), time.time() - t0), flush=True)
    if txt:
        print("     开头:", json.dumps(txt[:80], ensure_ascii=False), flush=True)
