# 示例 3: 链式工作流 — 有依赖的串行委托

## 场景
用户报告了一个 bug，修好后希望重构该模块。

## OpenCode 会话

```
👤 用户: "用户反馈上传图片后偶尔会损坏(约10%概率)，
         修好后把上传模块整体重构一下"

🧠 Orchestrator 思考:
  [意图分析]
    - debug (Bug 定位修复)
    - refactor (重构)
  [依赖分析]
    - refactor 依赖 debug 的结果（需要先知道哪里出问题）
    - 串行执行: debugger → refactor-specialist
  [策略] 阶段 1: 定位 Bug → 阶段 2: 修复确认 → 阶段 3: 重构

═══════════════════════════════════════════════
阶段 1: Bug 定位
═══════════════════════════════════════════════

🧠 Orchestrator 委托:
  Task(
    subagent_type: "debugger",
    description: "排查图片上传损坏",
    prompt: """
## 任务
排查图片上传后约 10% 概率损坏的根因

## 范围
- src/upload/handler.js (上传请求处理)
- src/upload/processor.js (图片处理逻辑)
- src/upload/storage.js (存储层)

## 现象
- 概率: 约 10%
- 表现: 上传后的图片无法打开，文件大小异常
- 环境: Node.js 20 + Sharp 图片处理库

## 预期输出
根因定位 + 精确的修复 diff
"""
  )

🐛 Debugger 执行:
  [分析] 读取 src/upload/processor.js
  [发现] processor.js:67 处:
    await sharp(buffer).jpeg().toFile(tmpPath)
    await fs.rename(tmpPath, finalPath)  // rename 可能失败!
  
  [假设] fs.rename 与 sharp.toFile 的写入流可能存在竞态
  [验证] 检查日志 → 损坏文件确实都是 0 字节 → 写入未完成就 rename 了
  
  🐛 Debugger 返回:
    ## 根因分析
    - 位置: src/upload/processor.js:67
    - 原因: sharp().toFile() 返回的 Promise resolve 后，
            文件可能尚未完全刷新到磁盘。
            fs.rename 在文件完全写入前就执行了。
    - 影响: ~10% 概率取决于磁盘 IO 时序
    
    ## 修复
    ```diff
    - await sharp(buffer).jpeg().toFile(tmpPath)
    - await fs.rename(tmpPath, finalPath)
    + await sharp(buffer).jpeg().toFile(finalPath)
    + // 直接写入最终路径，避免 rename 竞态
    ```

═══════════════════════════════════════════════
阶段 2: 验证修复
═══════════════════════════════════════════════

🧠 Orchestrator 验证:
  [分析修复逻辑] 
    - sharp 直接写 finalPath → 消除了 rename 步骤 → 可行 ✓
    - 但丢失了原子性（写入失败会留下半成品文件）→ 需要改进
    
  [决策] 接受修复方向但补充原子性保护:
    在调试器修复基础上增加 try/catch + 失败清理

🧠 Orchestrator 自行修改（小改动，不需要委托）:
  Edit(file=src/upload/processor.js, ...)  # 增加错误处理和清理逻辑

🧠 Orchestrator 回复用户:
  "根因已定位：sharp 写入文件的异步时序问题导致 ~10% 写入不完整。
   修复方案已验证并应用。现在进入重构阶段..."

═══════════════════════════════════════════════
阶段 3: 重构
═══════════════════════════════════════════════

🧠 Orchestrator 委托:
  Task(
    subagent_type: "refactor-specialist",
    description: "重构上传模块",
    prompt: """
## 任务
重构 src/upload/ 模块，消除代码味道

## 范围
- src/upload/handler.js (180 行)
- src/upload/processor.js (120 行)
- src/upload/storage.js (90 行)

## 约束
- ⚠️ 保留 processor.js 中刚刚修复的 toFile 逻辑（不再使用 rename）
- 不改变 API 签名
- 所有现有测试必须通过

## 关键上下文
- handler.js 和 processor.js 都包含了重复的文件类型检查逻辑
- storage.js 的 save() 和 saveMultiple() 有 60% 重复代码
- 当前没有错误码标准化

## 预期输出
重构计划 + 分步 diff + 测试运行结果
"""
  )

♻️ Refactor Specialist 执行:
  Step 1: 提取公共文件类型检查 → src/upload/validators.js
  Step 2: 提取 storage.js 中的公共存储逻辑 → 私有方法 _saveOne()
  Step 3: 统一错误码 → src/upload/errors.js
  每一步后运行测试: ✅ 全部通过

♻️ Refactor Specialist 返回:
  ## 重构完成
  - 消除了 handler.js 和 processor.js 中重复的文件类型检查
  - storage.js 从 90 行减少到 50 行
  - 新增 errors.js 统一错误码
  - 所有 23 个现有测试通过 ✅

═══════════════════════════════════════════════
最终整合
═══════════════════════════════════════════════

🧠 Orchestrator 最终回复:
  "上传模块修复 + 重构完成：
   
   🐛 Bug 修复:
   - 根因: sharp 文件写入异步时序问题
   - 修复: 直接写入目标路径 + 增加写入失败清理
   
   ♻️ 重构:
   - 提取公共验证逻辑到 validators.js
   - Storage 从 90 行精简到 50 行
   - 新增统一错误码定义
   
   📊 指标:
   - 修复前: 3 个文件, 390 行, 10% 损坏率
   - 修复后: 4 个文件, 310 行, 0% 损坏率
   - 测试: 23 个全部通过"

## 关键要点

1. **分阶段执行** — debug → refactor 有强依赖
2. **主控介入** — 修复方案不完美时主控自行微调（避免再委托的开销）
3. **上下文传递** — 阶段 2 的修复细节传递给阶段 3 作为约束
4. **每步验证** — 每个阶段的结果都经过主控验证才进入下一步

## 链式工作流的触发条件

当用户请求中出现以下模式时，使用串行链：
- "修 bug + 重构" → debugger → refactor-specialist
- "修 bug + 写测试" → debugger → test-writer
- "重构 + 验证" → refactor-specialist → code-reviewer
- "修复 + 安全审计" → debugger → security-auditor
- "新功能 + 文档 + 测试" → test-writer + doc-writer 并行 → code-reviewer 串行
