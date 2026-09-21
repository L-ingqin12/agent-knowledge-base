"""长上下文 + 长输出能力实测。

两个维度：
  A. 长输出：要求生成尽可能长，看是否自然收尾、是否陷入重复、速度衰减
  B. 长上下文（大海捞针）：把唯一事实埋进不同位置的长文档，看能否准确捞出

设计要点（吸取本会话教训）：
  * 每次请求加**唯一 nonce 且放在开头**，避免命中 KV 缓存导致测出假高值
  * 长输出要统计**重复率**——小模型最典型的失败模式是退化成复读机
  * 捞针要分「开头/中间/结尾」三个位置，只测一个位置会漏掉 lost-in-the-middle
"""
import json
import os
import subprocess
import sys
import time

import requests

OLLAMA = r"C:\Users\28064\AppData\Local\Programs\Ollama\ollama.exe"
W = r"D:\OllamaModels\bench"
API = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

NEEDLE = "门禁密码是 7XK9-QW2M"
FILLER = ("本市轨道交通建设持续推进，各条线路按计划有序开展。"
          "工程部门将安全生产放在首位，定期开展隐患排查与应急演练。"
          "同时，沿线配套的商业与住宅项目也在同步规划中。")

LONG_OUT_Q = ("请写一篇尽可能详细完整的文章，主题是《城市轨道交通的发展历程与未来趋势》，"
              "要求覆盖：早期有轨电车、地铁的诞生、自动化驾驶、跨城互联、未来超高速管道交通。"
              "每个部分都要展开论述，写得越长越好，不要提前结束。")


def call(model, messages, max_tokens, ctx=None, think=False):
    opts = {"num_predict": max_tokens, "temperature": 0.7}
    if ctx:
        opts["num_ctx"] = ctx
    body = {"model": model, "stream": False, "think": think,
            "messages": messages, "options": opts}
    t0 = time.time()
    d = requests.post(API + "/chat", headers=H,
                      data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                      timeout=3600).json()
    m = d.get("message", {})
    return {
        "content": m.get("content") or "",
        "thinking": m.get("thinking") or "",
        "finish": d.get("done_reason"),
        "ptok": d.get("prompt_eval_count", 0),
        "psec": d.get("prompt_eval_duration", 0) / 1e9,
        "ctok": d.get("eval_count", 0),
        "csec": d.get("eval_duration", 0) / 1e9,
        "wall": time.time() - t0,
    }


def repeat_ratio(text, n=8):
    """重复 n-gram 占比——复读机检测。"""
    if len(text) < n * 2:
        return 0.0
    grams = [text[i:i + n] for i in range(0, len(text) - n)]
    return 1.0 - len(set(grams)) / len(grams) if grams else 0.0


def test_long_output(model, maxtok=3000):
    r = call(model, [{"role": "user", "content": LONG_OUT_Q}], max_tokens=maxtok)
    txt = r["content"] or r["thinking"]
    print("   输出: %5d tok / %6.1fs = %5.1f tok/s   finish=%-8s 重复率=%.1f%%  墙钟=%.0fs" %
          (r["ctok"], r["csec"], r["ctok"] / r["csec"] if r["csec"] else 0,
           r["finish"], repeat_ratio(txt) * 100, r["wall"]), flush=True)
    if r["ctok"] < 60:
        print("      ⚠️ 只产 %d token，可能被思考吃光或提前收尾" % r["ctok"], flush=True)


def test_needle(model, ctx, depth, units):
    """depth: 0=开头 0.5=中间 1=结尾"""
    filler_n = max(1, int(units * (1 - min(depth, 0.9) - 0.05)))
    tail_n = max(1, units - filler_n)
    doc = (FILLER * filler_n + "\n【注意】" + NEEDLE + "。\n" + FILLER * tail_n)
    q = ("[nonce:%d] 下面是一份长文档，请只回答：门禁密码是多少？如果文中没有，回答『未提及』。\n\n"
         "%s") % (time.time_ns(), doc)
    r = call(model, [{"role": "user", "content": q}], max_tokens=120, ctx=ctx)
    hit = "7XK9" in (r["content"] or "")
    print("     位置%-6s 提示%5d tok  prefill %6.1f tok/s  首token %5.1fs  捞出=%s" %
          ("%.0f%%" % (depth * 100), r["ptok"],
           r["ptok"] / r["psec"] if r["psec"] else 0, r["psec"],
           "✅" if hit else "❌ " + json.dumps((r["content"] or "")[:40], ensure_ascii=False)),
          flush=True)


MODELS = {
    "granite4:micro-h": 32768,
    "qwen2.5-coder:3b": 16384,
    "qwen3.5:0.8b": 16384,
    "qwen3-vl:2b": 8192,
}

only = sys.argv[1:] or list(MODELS)
for model in only:
    ctx = MODELS[model]
    print("=" * 68, flush=True)
    print("模型: %s（num_ctx=%d）" % (model, ctx), flush=True)
    print("  A. 长输出（上限 3000 token）", flush=True)
    try:
        test_long_output(model)
    except Exception as e:
        print("     失败:", str(e)[:80], flush=True)
    print("  B. 长上下文捞针", flush=True)
    for depth in (0.0, 0.5, 0.95):
        try:
            test_needle(model, ctx, depth, max(1, int(ctx * 0.5 / 22)))
        except Exception as e:
            print("     位置%.0f%% 失败: %s" % (depth * 100, str(e)[:60]), flush=True)
