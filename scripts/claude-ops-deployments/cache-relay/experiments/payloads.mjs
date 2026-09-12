// 测试语料：按真实 Claude Code 请求形状生成 payload，用于等价性测试与性能基准。
// 规模对齐实测：主锚点(tools+system) ≈ 25,344 tokens ≈ 149K 字符；整体 body 到 ~1.5MB。
import { createHash } from 'node:crypto'

const TOOL_NAMES = [
  'Agent', 'AskUserQuestion', 'Bash', 'CronCreate', 'CronDelete', 'CronList', 'DesignSync',
  'Edit', 'EnterPlanMode', 'EnterWorktree', 'ExitPlanMode', 'ExitWorktree', 'Glob', 'Grep',
  'ListAgents', 'mcp__codebase-memory-mcp__delete_project', 'mcp__codebase-memory-mcp__detect_changes',
  'mcp__codebase-memory-mcp__get_architecture', 'mcp__codebase-memory-mcp__get_code_snippet',
  'mcp__codebase-memory-mcp__get_graph_schema', 'mcp__codebase-memory-mcp__index_repository',
  'mcp__codebase-memory-mcp__index_status', 'mcp__codebase-memory-mcp__ingest_traces',
  'mcp__codebase-memory-mcp__list_projects', 'mcp__codebase-memory-mcp__manage_adr',
  'mcp__codebase-memory-mcp__query_graph', 'mcp__codebase-memory-mcp__search_code',
  'mcp__codebase-memory-mcp__search_graph', 'mcp__codebase-memory-mcp__trace_path', 'NotebookEdit',
  'Read', 'ReportFindings', 'ScheduleWakeup', 'SendMessage', 'Skill', 'TaskCreate', 'TaskGet',
  'TaskList', 'TaskOutput', 'TaskStop', 'TaskUpdate', 'WebFetch', 'WebSearch', 'Workflow', 'Write',
]

const pad = (s, n) => (s + ' ').repeat(Math.ceil(n / (s.length + 1))).slice(0, n)

function mkTool(name) {
  const desc = pad(`Use ${name} to accomplish the requested operation. This tool is part of the Claude Code harness and follows the standard invocation contract.`, 180)
  const props = {}
  for (const p of ['description', 'target', 'options', 'timeout', 'mode']) {
    props[p] = { type: 'string', description: pad(`The ${p} parameter controls behaviour of ${name}.`, 90) }
  }
  return {
    name,
    description: desc,
    input_schema: { type: 'object', properties: props, required: ['description'], additionalProperties: false },
  }
}

const CC_SYSTEM = pad(
  'You are Claude Code, Anthropic\'s official CLI for Claude. You are an interactive agent that helps users with software engineering tasks. '
  + 'TEXT OUTPUT: your text output is displayed to the user as GitHub-flavored markdown in a terminal. Tools run behind a user-selected permission mode. '
  + 'TONE AND STYLE: be concise, direct, and avoid unnecessary preamble or flattery. Reference code as file_path:line_number.',
  3000)

const CLASSIFIER_SYSTEM = pad(
  'You are a security monitor for autonomous AI coding agents. Your task is to determine whether the described action is safe to run without human approval. '
  + 'Consider the transcript, the tool call, and the user request. Respond with a JSON verdict. Be conservative for destructive operations.',
  2000)

// 一段「易变 env 块」：含日期 / git hash / uuid —— 应被 relocateVolatile 搬走，日期应被 stabilizeDates 稳定。
const ENV_BLOCK = [
  '<env>',
  'Working directory: C:\\Users\\<user>\\.cache-relay',
  'Is directory a git repo: true',
  "Today's date is 2026-09-12",
  'Current branch: master',
  'Recent commits: 3f2a1b9 fix: something; 88de41c feat: other',
  'Platform: win32',
  'OS Version: Windows 11 Home 10.0.26200',
  'Session id: 6f1c2f6e-9a4b-4c2d-8e11-7b3a5d9c0e21',
  '</env>',
].join('\n')

const CLAUDE_MD_BLOCK = [
  '<system-reminder>',
  'As you answer the user\'s questions, you can use the following context:',
  '# claudeMd',
  'Codebase and user instructions are shown below.',
  '## 全局 Python',
  '- 通用 Python 解释器：D:\\ProgramData\\miniconda3\\python.exe（3.13）',
  '## 会话红线 — 代理/节点类内容的上下文卫生',
  '- 禁止在对话或工具输出里回显裸节点域名、host:port 清单、订阅链接。',
  '- 涉及节点清单时引用文件路径（如 node-pool.txt、proxy-nodes.json）。',
  '</system-reminder>',
].join('\n')

function mkMessages(n, { withDate = true, withTokens = true, withCacheCtl = false, withEnv = true } = {}) {
  const msgs = []
  const head = [CLAUDE_MD_BLOCK]
  if (withEnv) head.push(withDate ? ENV_BLOCK : ENV_BLOCK.replace("Today's date is 2026-09-12", ''))
  msgs.push({ role: 'user', content: head.join('\n\n') })
  msgs.push({ role: 'assistant', content: [{ type: 'text', text: pad('Understood. I will follow these instructions.', 400) }] })
  for (let i = 2; i < n - 1; i++) {
    if (i % 4 === 0) {
      const parts = [{ type: 'text', text: pad(`Step ${i}: analysing the repository state and planning the next action.`, 700) }]
      if (withCacheCtl) parts[parts.length - 1].cache_control = { type: 'ephemeral' }
      msgs.push({ role: 'assistant', content: parts })
      msgs.push({ role: 'user', content: [{ type: 'tool_result', tool_use_id: `toolu_${i}`, content: pad(`result payload for step ${i}`, 900) }] })
    } else {
      msgs.push({ role: 'user', content: pad(`continue with step ${i}`, 500) })
    }
  }
  const tail = withTokens ? `<system-reminder>\n<total_tokens>${withTokens === true ? 1000000 - n : withTokens} tokens left</total_tokens>\n</system-reminder>` : 'plain tail'
  msgs.push({ role: 'user', content: tail })
  return msgs
}

/** 主会话 payload（45 tools）。opts 控制各易变特征的有无，用于验证快速短路判据。 */
function mainPayload({ model = 'deepseek-v4-pro', msgs = 300, sorted = true, ...opts } = {}) {
  const tools = TOOL_NAMES.map(mkTool)
  if (!sorted) tools.reverse()
  return {
    model,
    max_tokens: 32000,
    system: [{ type: 'text', text: CC_SYSTEM }],
    tools,
    messages: mkMessages(msgs, opts),
  }
}

/** 分类器 payload：0 tools + security monitor system。 */
function classifierPayload({ model = 'deepseek-v4-pro[1m]', ...opts } = {}) {
  return {
    model,
    max_tokens: 64,
    system: [{ type: 'text', text: CLASSIFIER_SYSTEM }],
    tools: [],
    messages: [
      { role: 'user', content: CLAUDE_MD_BLOCK + '\n\nThe following is the user\'s CLAUDE.md configuration.' },
      { role: 'user', content: pad('Action: run `rm -rf /tmp/x` in the working directory.', 1500) },
    ],
  }
}

/** 覆盖所有会对快速短路产生分歧的特征组合。 */
export function corpus() {
  const cases = []
  const add = (name, body, provider) => cases.push({ name, provider, body })

  add('main-full', mainPayload({ withDate: true, withTokens: true, withCacheCtl: true, withEnv: true }), 'deepseek')
  add('main-bare', mainPayload({ withDate: false, withTokens: false, withCacheCtl: false, withEnv: false }), 'deepseek')
  add('main-date-only', mainPayload({ withDate: true, withTokens: false, withCacheCtl: false, withEnv: false }), 'deepseek')
  add('main-tokens-only', mainPayload({ withDate: false, withTokens: 987654, withCacheCtl: false, withEnv: false }), 'deepseek')
  add('main-cachectl-only', mainPayload({ withDate: false, withTokens: false, withCacheCtl: true, withEnv: false }), 'deepseek')
  add('main-unsorted-tools', mainPayload({ sorted: false, withDate: true, withTokens: true }), 'deepseek')
  add('main-heavy', mainPayload({ msgs: 900 }), 'deepseek')
  add('main-small', mainPayload({ msgs: 6 }), 'deepseek')
  add('main-one-msg', mainPayload({ msgs: 1, withDate: false, withTokens: false, withEnv: false }), 'deepseek')

  add('classifier', classifierPayload(), 'deepseek')
  add('classifier-bare', classifierPayload({ withDate: false, withTokens: false, withEnv: false }), 'deepseek')

  for (const provider of ['glm', 'anthropic', 'openrouter', 'generic']) {
    add(`main-full@${provider}`, mainPayload(), provider)
    add(`classifier@${provider}`, classifierPayload(), provider)
  }
  return cases
}

/** 深拷贝（payload 全是 JSON 安全结构）。 */
export function clone(o) { return JSON.parse(JSON.stringify(o)) }

export function sha(s) { return createHash('sha256').update(s).digest('hex').slice(0, 16) }

/** 「对齐后可缓存前缀」的指纹：与 relay 的 anchorFingerprint 同义。 */
export function anchorOf(body) { return sha(JSON.stringify({ tools: body?.tools, system: body?.system })) }

export { TOOL_NAMES }
