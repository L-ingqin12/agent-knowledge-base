"""本机 Ollama 客户端（只依赖 requests）。

关键背景（实测结论）：
  qwen3.5 这类 thinking 模型会先输出一大段思考再吐正文，
  同一问题「思考开 vs 关」实测差 41 倍耗时、43 倍 token。
  而 OpenAI 兼容端点 /v1 不支持关闭思考，只有原生 /api/chat 支持 `think`。

  所以本客户端默认走原生端点 + think=False。需要 OpenAI 兼容协议时用 v1_chat()。

用法:
    from ollama_api import Ollama
    c = Ollama()
    print(c.chat("你好"))               # 默认关思考，快
    print(c.chat("推导一下", think=True))  # 需要推理时开
"""
import json
import time

import requests

NATIVE = "http://127.0.0.1:11434/api"
V1 = "http://127.0.0.1:11434/v1"


class Ollama:
    def __init__(self, host="http://127.0.0.1:11434", api_key="ollama", timeout=1800):
        self.native = host.rstrip("/") + "/api"
        self.v1 = host.rstrip("/") + "/v1"
        self.headers = {"Authorization": "Bearer " + api_key,
                        "Content-Type": "application/json"}
        self.timeout = timeout

    # ---------- 模型管理 ----------
    def models(self):
        r = requests.get(self.native + "/tags", timeout=30)
        r.raise_for_status()
        return [(m["name"], round(m["size"] / 1e9, 2)) for m in r.json()["models"]]

    def ps(self):
        """查看哪些模型驻留、以及 CPU/GPU 分配."""
        r = requests.get(self.native + "/ps", timeout=30)
        r.raise_for_status()
        return r.json().get("models", [])

    # ---------- 对话（原生端点，推荐）----------
    def chat(self, prompt, model="qwen3.5:2b", system=None, think=False,
             max_tokens=1024, temperature=0.7, gpu_layers=None):
        """返回 (content, thinking, 统计dict, 耗时秒)。"""
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        opts = {"num_predict": max_tokens, "temperature": temperature}
        if gpu_layers is not None:
            opts["num_gpu"] = gpu_layers
        body = {"model": model, "messages": msgs, "stream": False,
                "think": think, "options": opts}
        t0 = time.time()
        r = requests.post(self.native + "/chat", headers=self.headers,
                          data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                          timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        msg = d.get("message", {})
        stats = {"prompt_tokens": d.get("prompt_eval_count"),
                 "completion_tokens": d.get("eval_count"),
                 "finish": d.get("done_reason"),
                 "decode_tok_s": round(d.get("eval_count", 0) /
                                       (d.get("eval_duration", 1) / 1e9), 1),
                 "load_s": round(d.get("load_duration", 0) / 1e9, 1)}
        return msg.get("content", ""), msg.get("thinking", ""), stats, time.time() - t0

    def stream(self, prompt, model="qwen3.5:2b", think=False, max_tokens=1024):
        """流式。yield (content增量, thinking增量, 距开始秒数)。"""
        body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                "stream": True, "think": think,
                "options": {"num_predict": max_tokens}}
        t0 = time.time()
        with requests.post(self.native + "/chat", headers=self.headers,
                           data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                           timeout=self.timeout, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                d = json.loads(line)
                m = d.get("message", {})
                yield (m.get("content", ""), m.get("thinking", ""), time.time() - t0)
                if d.get("done"):
                    break

    # ---------- OpenAI 兼容端点（给现成工具用）----------
    def v1_chat(self, messages, model="granite4:tiny-h", max_tokens=1024):
        """注意：v1 端点无法关闭思考，思考型模型会先烧完 token 再吐正文，
        所以这里默认用非思考模型。要接 OpenAI SDK/客户端时用这个端点。"""
        body = {"model": model, "messages": messages,
                "max_tokens": max_tokens, "temperature": 0.7}
        r = requests.post(self.v1 + "/chat/completions", headers=self.headers,
                          data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                          timeout=self.timeout)
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    c = Ollama()
    print("== 模型 ==")
    for name, gb in c.models():
        print("   %-20s %.1f GB" % (name, gb))

    print("\n== 驻留 ==")
    for m in c.ps():
        print("   %-20s %s  ctx=%s" % (m.get("name"), m.get("processor"), m.get("context_length")))

    print("\n== 关思考（推荐） ==")
    content, thinking, stats, dt = c.chat("用一句话说明什么是量子纠缠。")
    print("   ", content)
    print("    ", stats, "%.1fs" % dt)
