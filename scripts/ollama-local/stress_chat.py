"""长对话体感压测：多轮真实对话，测每轮的首字延迟与总耗时随上下文增长的劣化。

用法: python stress_chat.py [模型名] [轮数]
"""
import json
import sys
import time

import requests

NATIVE = "http://127.0.0.1:11434/api"
H = {"Content-Type": "application/json"}

# 一组逐步深入的追问，用来模拟真实的多轮问答
TURNS = [
    "我想学做手冲咖啡，需要哪些基础器具？",
    "其中磨豆机怎么选？预算 500 元左右。",
    "那水温、粉水比和注水节奏分别应该怎么控制？",
    "为什么我冲出来总是偏酸？可能是哪些环节出了问题？",
    "如果换成浅烘的耶加雪菲，参数要怎么调？",
    "保存咖啡豆有什么讲究？冷冻可以吗？",
    "手冲和爱乐压做出来的风味差异主要在哪？",
    "我想在办公室也喝到，有什么便携方案？",
    "家用的话，除了手冲还有别的入门选择吗？",
    "帮我把上面这些建议整理成一份简明的入门清单。",
]


def one_turn(model, history, question, max_tokens, gpu_layers=None):
    """一轮对话，流式，返回 (回答, 首字延迟, 总耗时, prompt_tokens, completion_tokens)。"""
    history.append({"role": "user", "content": question})
    opts = {"num_predict": max_tokens, "temperature": 0.7}
    if gpu_layers is not None:
        opts["num_gpu"] = gpu_layers   # 999 = 尽量全塞进显存，通常显著提速
    body = {"model": model, "messages": history, "stream": True, "think": False,
            "options": opts}
    t0 = time.time()
    first = None
    answer = ""
    prompt_tokens = completion_tokens = 0
    with requests.post(NATIVE + "/chat", headers=H,
                       data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                       timeout=1800, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            d = json.loads(line)
            piece = d.get("message", {}).get("content", "")
            if piece:
                if first is None:
                    first = time.time() - t0
                answer += piece
            if d.get("done"):
                prompt_tokens = d.get("prompt_eval_count", 0)
                completion_tokens = d.get("eval_count", 0)
                break
    history.append({"role": "assistant", "content": answer})
    return answer, first, time.time() - t0, prompt_tokens, completion_tokens


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5:0.8b"
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else len(TURNS)
    gpu = int(sys.argv[3]) if len(sys.argv) > 3 else None
    max_tokens = 400

    print("模型: %s | 轮数: %d | 每轮上限 %d token | num_gpu=%s\n" %
          (model, rounds, max_tokens, gpu if gpu is not None else "自动"))
    print("轮次  上下文tok  回复tok  首字延迟  本轮总耗时")
    print("-" * 52)

    history = []
    total = 0.0
    last_pt = 0
    for i in range(1, rounds + 1):
        q = TURNS[(i - 1) % len(TURNS)]          # 轮数超过题目数就循环追问
        try:
            ans, first, dt, pt, ct = one_turn(model, history, q, max_tokens, gpu)
        except Exception as exc:
            print("  第 %d 轮失败: %s" % (i, exc))
            break
        total += dt
        last_pt = pt
        flag = "  ← 上下文接近上限" if pt > 7600 else ""
        print("%3d   %8d  %7d  %7.1fs  %8.1fs%s" %
              (i, pt, ct, first if first else -1, dt, flag))
    print("-" * 52)
    print("累计耗时: %.1fs | 末轮上下文: %d tok" % (total, last_pt))


if __name__ == "__main__":
    main()
