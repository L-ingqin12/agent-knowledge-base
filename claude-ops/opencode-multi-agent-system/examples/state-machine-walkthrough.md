---
title: 状态机回环实战演练
aliases: [状态机演练, 质量门控回环实例, 双任务串行演练]
tags: [ai/agent, ai/learning]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# 状态机回环实战演练

## 场景: 修复密码安全 + 审计确认

用户要求修复 `src/auth.js` 的密码明文存储问题，修复后让安全审计确认。

这是一个**双任务串行 + 质量门控回环**的典型场景。

---

## 完整状态转换序列

```
═══════════════════════════════════════════════
[ANALYZE] 
═══════════════════════════════════════════════

用户请求: "修复 src/auth.js 的密码明文存储，修完后让安全审计确认"

意图提取:
  - Task 1: debugger — 修复密码存储
  - Task 2: security-auditor — 审计修复结果

依赖: Task 2 依赖 Task 1 → 串行执行

任务队列:
  T1: {agent: debugger, retryCount: 0, maxRetries: 3, previousFailures: []}
  T2: {agent: security-auditor, retryCount: 0, maxRetries: 3, previousFailures: []}

═══════════════════════════════════════════════
[DELEGATE] T1:R1 — 首次尝试
═══════════════════════════════════════════════

debugger, 
## 任务
修复 src/auth.js 中密码明文存储的安全漏洞。
密码应使用 bcrypt 哈希存储。

## 范围
- 文件: src/auth.js
- 约束: 不改变 API 签名

## 预期输出
修复 diff + 运行测试确认

---

🐛 debugger 返回:
```diff
@@ -13,7 +13,7 @@
 function createUser(username, password) {
     const user = {
         id: users.length + 1,
-        password: password,
+        password: bcrypt.hashSync(password, 10),
         createdAt: new Date()
     };
```

═══════════════════════════════════════════════
[VERIFY] T1:R1 — 质量门控
═══════════════════════════════════════════════

✅ GATE:syntax — 代码语法正确
❌ GATE:completeness — 使用了 bcrypt.hashSync() 但缺少:
   - `const bcrypt = require('bcrypt')` 导入
   - package.json 中未添加 bcrypt 依赖
   - login() 函数中的密码比较未同步修改为 bcrypt.compare()
✅ GATE:consistency — 风格匹配

BLOCKER: GATE:completeness — 3 项缺失
→ FAIL → RETRY

═══════════════════════════════════════════════
[RETRY] T1:R2 — 携带反馈
═══════════════════════════════════════════════

debugger, 
## 任务
修复 src/auth.js 中密码明文存储的安全漏洞。
密码应使用 bcrypt 哈希存储。

## 范围
- 文件: src/auth.js
- 约束: 不改变 API 签名

## ⚠️ 上一轮未通过质量检查
### 阻塞问题:
[GATE:completeness] 修复不完整:
  1. 缺少 `const bcrypt = require('bcrypt')` 导入语句
  2. 未更新 package.json 添加 bcrypt 依赖
  3. login() 函数仍使用 user.password == password 明文比较
     需要改为 bcrypt.compare(password, user.password)

### 本轮要求:
请完成以上 3 项缺失，确保整个认证流程使用 bcrypt。

---

🐛 debugger 返回 (Round 2):
```diff
@@ -1,5 +1,6 @@
 const crypto = require('crypto');
+const bcrypt = require('bcrypt');

@@ -15,7 +16,7 @@
-        password: password,
+        password: bcrypt.hashSync(password, 10),

@@ -24,7 +25,7 @@
-    if (user && user.password == password) {
+    if (user && bcrypt.compareSync(password, user.password)) {
```
+ package.json: dependencies 中新增 "bcrypt": "^5.1.0"

═══════════════════════════════════════════════
[VERIFY] T1:R2 — 重新质量门控
═══════════════════════════════════════════════

✅ GATE:syntax — 代码语法正确
✅ GATE:completeness — bcrypt 导入 + 存储 + 验证 + 依赖 全部覆盖
✅ GATE:consistency — 风格匹配
✅ GATE:no_hallucination — bcrypt 是真实 npm 包, hashSync/compareSync 确实存在

→ PASS ✓

═══════════════════════════════════════════════
[INTEGRATE] T1 完成 → 继续 T2
═══════════════════════════════════════════════

T1 结果: 2 轮完成，最终修复覆盖 4 处变更

═══════════════════════════════════════════════
[DELEGATE] T2:R1 — 安全审计
═══════════════════════════════════════════════

security-auditor, 
## 任务
审计 src/auth.js 修复后的安全性，确认密码存储问题已解决

## 范围
- 文件: src/auth.js
- 已知修复: 密码已改用 bcrypt hashSync + compareSync

## 预期输出
安全审计报告

---

🛡️ security-auditor 返回:
```
## 安全审计报告
...
### [W-01] resetPassword 函数未验证旧密码
位置: src/auth.js:33
修复: 在修改密码前应该要求输入旧密码并验证
...
```

═══════════════════════════════════════════════
[VERIFY] T2:R1
═══════════════════════════════════════════════

✅ GATE:specificity — 引用具体行号
✅ GATE:actionable — 有修复建议
✅ GATE:file_check — 文件路径正确

→ PASS ✓ (W-01 是 WARNING 级别，不阻塞)

═══════════════════════════════════════════════
[INTEGRATE] 最终汇总
═══════════════════════════════════════════════

整合:
  T1 (debugger): 密码存储修复完成 (2 轮, bcrypt 全面覆盖)
  T2 (security-auditor): 审计通过, 发现 1 个 WARNING

交叉验证:
  security-auditor 确认密码存储修复正确 → T1 方案有效
  security-auditor 额外发现 resetPassword 缺少旧密码验证
  → 这是新发现, 不在原始任务范围, 但值得报告

═══════════════════════════════════════════════
[DONE] 汇报用户
═══════════════════════════════════════════════

✅ 密码存储修复完成 (debugger, 2轮)
   - bcrypt 哈希替代明文存储
   - 登录验证改用 bcrypt.compareSync
   - 第二轮补充了缺失的导入和依赖

✅ 安全审计确认 (security-auditor, 1轮)
   - 密码存储漏洞已修复
   - ⚠️ 额外发现: resetPassword() 未验证旧密码 (非原始任务范围)

📊 统计:
   - 总轮次: 3 (debugger×2 + security-auditor×1)
   - 门控拦截: 1 次 (completeness gate)
   - 重试后通过率: 100%
```

---

## 状态图

```
        ANZ    DEL    VER    INT    DON
         │      │      │      │      │
T1:R1 ───●──────●──────●──────┐      │
                         │ FAIL│      │
T1:R2 ──────────────────●──────●──────┤
                         │ PASS│      │
T2:R1 ─────────────────────────●──────●──────●
                                PASS
```

---

## 如果连续失败会发生什么

```
T1:R1 → VERIFY FAIL (syntax error)
T1:R2 → VERIFY FAIL (same syntax error — 死循环检测!)
        → ESCALATE 而非 RETRY
        → "debugger 连续 2 次产生相同的语法错误: 第 5 行缺少分号。
           已暂停。请指示：1) 手动修复 2) 换 refactor-specialist 3) 接受现状"
```

## 如果 Fan-Out 时一个任务回环

```
并行: T1(debugger) + T2(code-reviewer) + T3(doc-writer)

T1: R1→FAIL→R2→PASS ✓ (2轮)
T2: R1→PASS ✓ (1轮)  
T3: R1→PASS ✓ (1轮)

→ T1 的回环不影响 T2, T3
→ 总耗时: max(T1两轮, T2一轮, T3一轮) = T1 两轮
→ 串行: 1+2+1 = 4轮，并行: max(2,1,1) = 2轮，加速 2x
```

> 🔗 相关文档：[[chain-workflow]] · [[state-machine-control]] · [[state-machine-quality-gate-loop]]
