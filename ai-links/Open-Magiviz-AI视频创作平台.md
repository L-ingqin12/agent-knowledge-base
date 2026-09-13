---
title: Open-Magiviz — AI 视频创作平台
aliases: [Magiviz, ItusiAI-Open-Magiviz]
tags: [ai/links, ai/tools, reference]
created: 2026-08-18
updated: 2026-09-13
status: stable
source_urls:
  - https://github.com/ItusiAI/Open-Magiviz
fetched_at: 2026-08-18
---

# Open-Magiviz — AI 视频创作平台

See also: [[AI-Links-KB-Home]] | [[2026-08-16-AI链接综述与归档]] | [[Articles-Index]] | [[AGENTS]]

> [!abstract] 定位
> [Open-Magiviz](https://github.com/ItusiAI/Open-Magiviz) 是开源 AI 视频创作 SaaS（magiviz.com 的公开源码）：从创意输入到成品视频的完整流水线，集成 Veo/Kling/Seedance/Wan 等多家视频生成模型，含用户系统、积分支付（Stripe）、版本管理与实时进度。技术栈：Next.js + TypeScript + Tailwind + Drizzle ORM + PostgreSQL + Stripe + Pusher + FAL AI。

## 一、核心工作流（五步串行 + 可中断可恢复）

```
创意输入 → ①AI剧情生成 → ②主角生成 → ③分镜图生成 → ④剧情视频生成 → ⑤完整视频合成
```

| 步骤 | 接口 | 要点 |
|---|---|---|
| ① 剧情 | `/api/ai/generate-story-details` | 结构化 JSON（标题/场景/角色/提示词）；LLM 非严格 JSON 兼容解析；按模型定分段时长（Veo 固定 8s、Seedance 4-30s 等） |
| ② 主角 | `/api/ai/generate-character-image` | 并行生成；支持参考图图生图；积分不足/解析失败独立分支 |
| ③ 分镜 | `/api/ai/generate-storyboard-image` | 并行；只传该场景引用角色的图片；**首尾帧模式**（首帧+尾帧同生，可单帧重生成） |
| ④ 视频 | `/api/ai/generate-story-video` | 并行；分镜图驱动；视频/音频多模态参考仅 Seedance 系支持；尾帧作为 additionalImageUrls |
| ⑤ 合成 | `/api/ai/fal/compose-story-video` | FAL AI 拼接：计算 keyframes（视频轨+音频轨）合并，输出总时长/缩略图/比例/大小 |

### 数据流串联（产物字段级，2026-09-13 补）

```
创意输入
  └─① generate-story-details ──→ 结构化 JSON（标题/场景/角色/提示词）
        │                          ✗ 失败落点：LLM 返回非严格 JSON 解析失败（独立分支，不进 ②）
        ├─② generate-character-image ─→ 角色图
        │        ✗ 失败落点：积分不足 / 解析失败（独立分支，流水线停在 character 态）
        ├─③ generate-storyboard-image ─→ 分镜图（首帧 + 可选尾帧）
        │        只传该场景引用角色的图片
        ├─④ generate-story-video ──────→ 分镜视频（videoUrls / audioUrls）
        │        generationType 标记普通 or 首尾帧；尾帧走 additionalImageUrls；
        │        视频/音频多模态参考仅 Seedance 系支持
        └─⑤ fal/compose-story-video ───→ 成品（keyframes 合轨：视频轨 + 音频轨）
```

- **谁产出什么、下一步吃什么**：②吃①的角色定义 → ③吃②的角色图 → ④吃③的分镜图（尾帧作为 `additionalImageUrls`）→ ⑤吃④的 `videoUrls` + `audioUrls` 合成总视频。
- **失败回哪一步**：①解析失败不进入②；②积分不足令会话停在 `character` 态；④/⑤失败由 `resumeWorkflow` 按步骤分发续跑，已完成步骤的产物不丢。

- **状态机**：`idle → script → character → storyboard → scenes → video`；暂停时先等待进行中 Pusher 任务（≤60s）再 abort；`resumeWorkflow` 按步骤分发恢复，不丢已有数据。
- **重生成语义**：单元素重生成会级联重跑下游（如重生成主角 → 受影响场景的分镜+视频+总视频）；每次重生成产生新 `versionGroupId` 实现双层版本控制（版本组 + 组内自增 version），历史不覆盖。

## 二、模型与参数

- 12 种视频模型：auto / veo31Lite / veo31Fast / veo31Quality / geminiOmni / seedance25 / seedance2 系 / kling3 / happyHorse / wan27 / minimaxH3。
  > [!warning] 更正（2026-09-13）：README 的模型表实列 **14 个别名**（原表述「12 种」沿用 README 正文口径）：auto、veo31Lite、veo31Fast、veo31Quality、geminiOmni、seedance25、seedance2Fast、seedance2Mini、seedance2、kling3、happyHorse、wan30、wan30Prime、minimaxH3；原列的 `wan27` 在 README 中已作 `wan30` / `wan30Prime`。来源：[README](https://raw.githubusercontent.com/ItusiAI/Open-Magiviz/main/README.md)。
- 参数面板：生成模式（普通/首尾帧）、比例（16:9/9:16）、时长（15s/30s/60s）、风格（auto/anime/hollywood/ads）。
- 上传视频/音频时自动锁定 Seedance 系并做媒体校验（数量/总时长/格式上限）。

## 三、商业系统

- **订阅计划 + 积分套餐**双轨：订阅用户积分消耗 67 折；积分按量购买；消费记录可查；推荐分销（邀请得积分）；管理员后台（用户管理/积分调整）；国际化 i18n。

## 四、技术栈与部署

- 前端：Next.js、TypeScript、Tailwind、shadcn/ui
- 后端：Next.js API Routes、Drizzle ORM、PostgreSQL
- 集成：Stripe（支付）、Pusher（实时推送）、FAL AI（视频合成）
- 模型路由层（2026-09-13 补）：**Kie.ai**（视频模型聚合，环境变量 `KIE_API_KEY` / `KIE_VEO_WEBHOOK_URL` / `KIE_VIDEO_WEBHOOK_URL`）、**ZenMux**（剧情 LLM 生成，`ZENMUX_API_KEY`）、**FAL AI**（合成）；`package.json` 依赖另有 `@fal-ai/client@^1.8.4`、`@aws-sdk/client-s3`、`@neondatabase/serverless`、`@auth/drizzle-adapter`。
  > 来源：[README](https://raw.githubusercontent.com/ItusiAI/Open-Magiviz/main/README.md)「AI 服务」段、[package.json](https://raw.githubusercontent.com/ItusiAI/Open-Magiviz/main/package.json)。原文只写「集成 Veo/Kling/Seedance/Wan 等多家视频生成模型」而全篇未出现实际承接方，本条补上服务商与仓库级集成点。
- 部署：Vercel 一键（推荐）；环境变量含数据库、Stripe、AI 服务密钥（详见仓库 README『安全特性』小节：敏感配置环境隔离）
- 注意：核心交互组件 `components/operate.tsx` 约 10,289 行（巨型组件，工程上可拆分的典型样本）

## 五、学习价值

- ★★★★☆ — 完整开源「AI 工作流 SaaS」参照：多模型编排、长流水线可中断/恢复/版本化、计费与实时进度推送，适合学习 AI 应用层产品化架构。
- 可借鉴点：五步流水线的状态机与级联重生成设计；双层版本管理（versionGroupId + version）；积分与订阅的商业化骨架。
- 注意点：巨型组件与内联 API 结构偏「小团队快跑」风格，生产级工程需重构分层。

## Related

- [[2026-08-16-AI链接综述与归档]] — 链接综述（本文作为追加条目 #17）
- [[AI-Links-KB-Home]] — 本子库 MOC
- [[Articles-Index]] — 文章库索引
- [[AGENTS]] — 知识库规范

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | 只写「集成 Veo/Kling/Seedance/Wan 等模型」与「FAL AI」，全篇无实际承接这些模型的服务商与仓库级集成点 | §四新增「模型路由层」条目：Kie.ai（视频模型聚合，三个 KIE_* 环境变量）、ZenMux（剧情 LLM）、FAL AI（合成），并补 `package.json` 依赖清单；来源为仓库 README「AI 服务」段与 package.json 原文 |
| 纠错 | §二记「12 种视频模型」且列 `wan27` | 保留原句并加更正块：README 模型表实列 14 个别名（auto/veo31Lite/veo31Fast/veo31Quality/geminiOmni/seedance25/seedance2Fast/seedance2Mini/seedance2/kling3/happyHorse/wan30/wan30Prime/minimaxH3）；`wan27` 已作 `wan30`/`wan30Prime`。依据：README 模型表逐字核取 |
| 加厚 | 五步流水线只有一行示意 + 接口表，读者看不到「谁产出什么、下一步吃什么、失败回哪一步」 | §一新增「数据流串联（产物字段级）」文字树与两条说明：产出/消费字段（`videoUrls`/`audioUrls`/`generationType`/`additionalImageUrls`）与失败落点（①解析失败、②积分不足、④⑤由 resumeWorkflow 续跑） |

依据：[README](https://raw.githubusercontent.com/ItusiAI/Open-Magiviz/main/README.md)、[package.json](https://raw.githubusercontent.com/ItusiAI/Open-Magiviz/main/package.json)。方法论回链：[[CORRECTIONS]]。
