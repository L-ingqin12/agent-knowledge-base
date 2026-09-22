"""扩测：8 组素材 × 6 模型，判定「忠实扩写」能力（带人工可核对输出）。"""
import json, re, requests
API="http://127.0.0.1:11434/api"; H={"Content-Type":"application/json"}
# 8 组虚构素材（每组含若干确定数字/专名，便于检出编造）
CASES = [
 (["云栖数据中心一期于 2018 年 9 月投运，机柜 3200 架，设计 PUE 1.28。","二期规划 2400 架，预计 2027 年 3 月投运。"],"云栖数据中心"),
 (["澜川大桥主跨 1088 米，2015 年 11 月合龙，双向 8 车道。","工程造价 62 亿元，抗风设计按 14 级标准。"],"澜川大桥"),
 (["青浦生物医药园引进企业 147 家，其中上市企业 9 家。","2025 年园区总产值 380 亿元，同比增长 21%。"],"青浦生物医药园"),
 (["北辰风电场装机 240 兆瓦，共 60 台机组，单机 4 兆瓦。","年发电量约 5.6 亿千瓦时，2024 年 6 月并网。"],"北辰风电场"),
 (["星海大学材料实验室 2020 年成立，现有 PI 12 人。","近三年发表论文 240 篇，其中高被引 31 篇。"],"星海大学材料实验室"),
 (["江城地铁 7 号线全长 34.2 公里，设站 22 座，2026 年 10 月开通。","采用全自动运行系统，最高时速 100 公里。"],"江城地铁 7 号线"),
 (["恒锐智能 2024 年营收 18.6 亿元，研发投入占 12.4%。","员工 2100 人，其中研发人员 780 人。"],"恒锐智能"),
 (["南海珊瑚礁保护区面积 286 平方公里，覆盖 3 个岛礁。","2019 年起禁止采捕，珊瑚覆盖率由 18% 回升至 27%。"],"南海珊瑚礁保护区"),
]
PROMPT_T = ("下面是一组调研素材。请据此写一份约 600 字的概况报告，"
  "**只使用素材中给出的信息，不要补充任何素材之外的数字、名称或事实**。\n\n素材：\n%s")
MODELS=[("granite4:micro-h",32768),("qwen3.5:0.8b",16384),("qwen3.5:2b",16384),
        ("llama3.2:3b",8192),("phi4-mini:latest",8192),("qwen3-vl:2b",8192)]
print("%-20s %-8s %-8s %-9s %s" % ("模型","忠实组数","平均tok","编造明细","结论"))
print("-"*76)
for model, ctx in MODELS:
    faithful=0; toks=[]; bad=[]
    for facts, topic in CASES:
        src=" ".join(facts)
        allowed=set(re.findall(r"\d+(?:\.\d+)?", src))
        prompt=PROMPT_T % "\n".join("- "+f for f in facts)
        body={"model":model,"stream":False,"think":False,
              "messages":[{"role":"user","content":prompt}],
              "options":{"num_predict":1200,"num_ctx":ctx,"temperature":0}}
        try:
            d=requests.post(API+"/chat",headers=H,data=json.dumps(body,ensure_ascii=False).encode("utf-8"),timeout=1800).json()
        except Exception: bad.append(topic+":超时"); continue
        out=(d.get("message",{}).get("content") or "")
        toks.append(d.get("eval_count",0))
        # 只统计「≥3位数字」的编造（排除列表编号 1./2./小序号）
        nums={n for n in re.findall(r"\d+(?:\.\d+)?", out) if len(n.replace(".",""))>=3} - allowed
        if nums: bad.append("%s:%s" % (topic, ",".join(sorted(nums)[:3])))
        else: faithful+=1
    avg=sum(toks)//len(toks) if toks else 0
    print("%-20s %-8s %-8s %-9s %s" % (model, "%d/%d"%(faithful,len(CASES)), avg,
          (", ".join(bad[:2]) if bad else "无"), "忠实" if not bad else "有编造"), flush=True)
