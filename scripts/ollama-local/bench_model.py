"""通用模型基准：驻留情况 + decode 速度（自动/强制满 GPU）+ 长提示 prefill。

用法: python bench_model.py <模型名> [<模型名> ...]
"""
import json
import sys
import time

import requests

NATIVE = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

DECODE_Q = ("Write a detailed paragraph explaining how a bicycle works, "
            "covering the frame, wheels, drivetrain, and steering.")
SENT = ("The history of urban planning spans several millennia, from the grid "
        "streets of ancient civilizations to modern transit-oriented development. ")
PREFILL_Q = SENT * 260 + "\n\nSummarize the above in one short sentence."


def call(model, question, num_predict, gpu_layers=None):
    opts = {"num_predict": num_predict, "temperature": 0}
    if gpu_layers is not None:
        opts["num_gpu"] = gpu_layers
    body = {"model": model, "messages": [{"role": "user", "content": question}],
            "stream": False, "think": False, "options": opts}
    t0 = time.time()
    try:
        d = requests.post(NATIVE + "/chat", headers=H,
                          data=json.dumps(body).encode("utf-8"),
                          timeout=1800).json()
    except Exception as exc:
        return None, time.time() - t0, str(exc)
    ec, ed = d.get("eval_count", 0), d.get("eval_duration", 1) or 1
    pc, pd = d.get("prompt_eval_count", 0), d.get("prompt_eval_duration", 1) or 1
    return {"decode": ec / (ed / 1e9), "prefill": pc / (pd / 1e9) if pd else 0,
            "first_tok_s": pd / 1e9, "load_s": d.get("load_duration", 0) / 1e9,
            "tokens": ec}, time.time() - t0, None


def residency(model):
    """注意 /api/ps 没有 processor 字段（那是 CLI 自己算的），
    要用 size_vram / size 推算 GPU 占比。"""
    ps = requests.get(NATIVE + "/ps", timeout=30).json().get("models", [])
    for m in ps:
        if m.get("name") == model or m.get("model") == model:
            total = m.get("size", 0) or 1
            vram = m.get("size_vram", 0) or 0
            m["gpu_pct"] = round(vram / total * 100)
            return m
    return None


def bench(model):
    print("#" * 62)
    print("模型:", model)
    r, _, err = call(model, "hi", 4)
    if err:
        print("  加载失败:", err)
        return
    p = residency(model)
    if p:
        d = p.get("details", {})
        print("  驻留: %d%% GPU (vram %.2f/%.2f GB) | ctx=%s | 量化=%s | 参数=%s" %
              (p.get("gpu_pct", -1), (p.get("size_vram", 0) or 0) / 1e9,
               (p.get("size", 0) or 0) / 1e9, p.get("context_length"),
               d.get("quantization_level"), d.get("parameter_size")))

    # nonce 必须加在【开头】！Ollama 按最长公共前缀做 KV 缓存，
    # 加在末尾的话前缀照样命中，prefill 会测出荒谬的高值（曾测出 419 万 tok/s）。
    def uniq(q):
        return "[nonce:%d]\n\n" % time.time_ns() + q

    res, wall, err = call(model, uniq(DECODE_Q), 128)
    print("  [自动分层] decode=%.1f tok/s  墙钟=%.1fs" %
          (res["decode"], wall) if not err else "  失败: " + err)

    res2, wall2, err2 = call(model, uniq(DECODE_Q), 128, gpu_layers=999)
    if not err2:
        print("  [强制满GPU] decode=%.1f tok/s  墙钟=%.1fs" %
              (res2["decode"], wall2))
        print("  → 提速 %.2fx" % (res2["decode"] / res["decode"] if res else 0))

    res3, wall3, err3 = call(model, uniq(PREFILL_Q), 24)
    if not err3:
        print("  [长提示 5.7K] prefill=%.1f tok/s  首token=%.1fs" %
              (res3["prefill"], res3["first_tok_s"]))
    print()


for m in sys.argv[1:]:
    bench(m)
