"""多模态（视觉）实测：把已知内容的图喂给本地模型，看它能否正确描述。

用法: python test_vision.py [模型名 ...]
"""
import base64
import json
import sys
import time

import requests

NATIVE = "http://127.0.0.1:11434/api/chat"
IMG = r"D:\OllamaModels\bench\vision_test.png"
QUESTION = ("Look at the image and answer precisely: "
            "1) What color and shape is in the top-left? "
            "2) What color and shape is in the top-right? "
            "3) How many green squares are along the bottom?")
TRUTH = "应为: 左上红圆 / 右上蓝方 / 底部3个绿方块"


def ask(model):
    b64 = base64.b64encode(open(IMG, "rb").read()).decode()
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": QUESTION, "images": [b64]}],
            "options": {"num_predict": 300, "temperature": 0}}
    t0 = time.time()
    try:
        r = requests.post(NATIVE, data=json.dumps(body).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, timeout=900)
        d = r.json()
    except Exception as exc:
        print("  %-22s 请求失败: %s" % (model, exc))
        return
    if "message" not in d:
        print("  %-22s 返回异常: %s" % (model, json.dumps(d)[:150]))
        return
    content = d["message"].get("content", "")
    print("  %-22s (%.1fs) %s" % (model, time.time() - t0,
                                  json.dumps(content, ensure_ascii=False)[:320]))
    print("  %-22s 参考答案: %s" % ("", TRUTH))


models = sys.argv[1:] or ["qwen3.5:0.8b", "qwen3.5:2b"]
print("测试图:", IMG, "|", TRUTH, "\n")
for m in models:
    ask(m)
