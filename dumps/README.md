# Permafrost 补丁前后 dump 对比 (已脱敏)

## dump-before-currentdate.json
原版 permafrost — currentDate 随真实日期变化(如 2026/06/12)
跨天时 msg[0] 字节变化 → DeepSeek 前缀缓存全部失效

## dump-after-currentdate.json
补丁版本 — currentDate 锁定为 2000-01-01
跨天无变化 → 缓存前缀稳定 → 命中率 99%+

## dump-*-structure.json (较早版本)
仅工具集+system块结构对比
