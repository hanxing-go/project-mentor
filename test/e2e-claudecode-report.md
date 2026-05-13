# Project Mentor — Claude Code (Source Snapshot) 端到端测试报告

> **测试日期：** 2026-05-13  
> **测试仓库：** [hanxing-go/claude-code](https://github.com/hanxing-go/claude-code)  
> **测试工具：** Python scripts (v2)  
> **测试范围：** 7 阶段完整流程 + Pre-flight  
> **特别注意：** 此仓库为 Anthropic Claude Code CLI 的源码快照（非官方）

---

## 1. 测试环境

| 项目 | 值 |
|------|---|
| OS | Windows 11 Home China 10.0.26200 |
| Python | 3.x (Anaconda) |
| 获取方式 | GitHub API zipball（HTTPS/SSH clone 均失败） |
| 项目类型 | TypeScript CLI — Anthropic Claude Code 源码镜像 |

---

## 2. Pre-Flight 测试

### 2.1 项目识别

| 检查点 | 方式 | 结果 |
|--------|------|------|
| HTTPS clone | `git clone https://...` | ❌ `Recv failure: Connection was reset` |
| SSH clone | `git clone git@github.com:...` | ❌ `early EOF / unexpected disconnect` |
| API zipball | `curl -L https://api.github.com/repos/.../zipball/main` | ✅ 9.9 MB 下载成功 |
| `.git` 目录 | 检查 | ❌ 不存在（zip 下载） |

**发现：** 中国大陆网络环境下，GitHub API 仍可访问（`api.github.com`），但 `github.com` git 协议被阻断。

### 2.2 技术栈检测

```json
{
  "primary_language": "TypeScript",
  "language_breakdown": {"TypeScript": 1332, "TSX": 552, "JavaScript": 18},
  "framework": "React + Ink (Terminal UI)",
  "build_system": "Bun",
  "test_framework": null,
  "package_manager": "Bun (无 package.json 可见)",
  "total_files": 1902,
  "total_lines": "512,000+"
}
```

| 检查点 | 预期 | 实际 | 结果 |
|--------|------|------|------|
| primary_language | TypeScript | TypeScript + TSX | ✅ |
| runtime | Node/Bun | Bun | ✅ |
| framework | React + Ink | React + Ink | ✅ |
| 文件总数 | ~1900 | 1902 | ✅ |
| 总行数 | ~512K | 512K+ | ✅ |

### 2.3 项目类型分类

**分类结果：** CLI Developer Tool（开发者命令行工具）

判定依据：
- 无 HTTP Server → 非 Web Backend
- 使用 React + Ink → 终端 UI 应用
- 工具集包含 BashTool/FileEditTool/GrepTool 等 → 代码助手 CLI
- 有 sub-agent 协调器 → AI Agent 工具
- 有 IDE bridge 系统 → IDE 集成层
- **实为 Anthropic Claude Code 的完整 CLI 源码**

---

## 3. Phase 0：Git 考古

### 3.1 边界情况：Fork 仓库（单一快照）

仓库是 `instructkr/claude-code` 的 fork，于 2026-03-31 创建（源码 map 泄露当天）。仅有 README.md + src/ 目录，无 Git 历史。

| 检查点 | 处理方式 | 结果 |
|--------|----------|------|
| Git 历史 | 不存在（单一快照 dump） | ✅ 降级 |
| README 溯源 | 提供了完整的泄露事件说明 | ✅ |
| Phase 0 输出 | "源码快照仓库，无演化历史" | ✅ |

---

## 4. Phase 1：侦察 — 项目名片 + 架构

### 4.1 AST 骨架提取

```
python scripts/ast_skeleton.py <path>/src --extensions ts,tsx --no-skip-tests
```

| 检查点 | 值 | 结果 |
|--------|---|------|
| status | success | ✅ |
| files_found | 500 (受 500 文件限制) | ⚠️ 仅覆盖 26% |
| files_analyzed | 499 | ⚠️ |
| files_skipped | 1 | ✅ |
| 总行数（分析到） | 109,625 | ⚠️ |
| 函数提取 | 2,203 | ✅ |
| 类提取 | 0 | ❌ Bug #12 |
| 接口提取 | 21 | ⚠️ |
| exports | 1,004 | ✅ |
| imports | 4,697 | ✅ |

### 4.2 项目名片

```
📇 Project Card
├─ Name: Claude Code (CLI)
├─ One-liner: Anthropic 官方 CLI — 终端 AI 编程助手
├─ Language: TypeScript (1332 .ts + 552 .tsx)
├─ Runtime: Bun
├─ UI: React + Ink (Terminal React 框架)
├─ Files: 1,902
├─ Lines: 512,000+
├─ Architecture Type: CLI Developer Tool + AI Agent Platform
└─ Source: npm 包 .map 文件泄露 → 2026-03-31 公开
```

### 4.3 架构鸟瞰

```
src/ (~1900 files, ~512K lines)
│
├── main.tsx (4684 行)           ← CLI 主入口，Commander.js 路由
├── QueryEngine.ts (1295 行)     ← LLM 查询引擎
├── Tool.ts (792 行)             ← 工具基类 + 类型定义
├── commands.ts (754 行)          ← 命令注册表
├── tools.ts (389 行)            ← 工具注册表
├── context.ts                    ← 系统/用户上下文收集
├── cost-tracker.ts              ← Token 费用追踪
│
├── tools/ (~40+ 工具)
│   ├── BashTool/ (18 文件, 12,411 行) ← Shell 执行 + 完整安全系统
│   ├── FileEditTool/            ← 字符串替换编辑
│   ├── FileReadTool/            ← 文件读取（含图片/PDF/Jupyter）
│   ├── FileWriteTool/           ← 文件创建/覆写
│   ├── GrepTool/                ← ripgrep 内容搜索
│   ├── GlobTool/                ← 文件模式匹配
│   ├── AgentTool/               ← 子 Sub-Agent 生成
│   ├── SkillTool/               ← Skill 系统执行
│   ├── MCPTool/                 ← MCP 服务器工具调用
│   ├── LSPTool/                 ← Language Server Protocol
│   ├── NotebookEditTool/        ← Jupyter 笔记本编辑
│   ├── TaskCreateTool/          ← 任务创建
│   ├── TaskUpdateTool/          ← 任务更新
│   ├── SendMessageTool/         ← Agent 间消息
│   ├── EnterPlanModeTool/       ← 计划模式
│   ├── EnterWorktreeTool/       ← Git Worktree 隔离
│   ├── WebFetchTool/            ← URL 内容获取
│   ├── WebSearchTool/           ← Web 搜索
│   ├── TodoWriteTool/           ← Todo 列表
│   ├── AskUserQuestionTool/     ← 用户提问
│   ├── CronCreateTool/          ← 定时任务
│   ├── SleepTool/               ← 主动等待
│   └── ...更多
│
├── commands/ (~50+ 命令, 83 子目录)
│   ├── review/                  ← /review 代码审查
│   ├── compact/                 ← /compact 上下文压缩
│   ├── config/                  ← /config 设置管理
│   ├── doctor/                  ← /doctor 环境诊断
│   ├── mcp/                     ← /mcp MCP 管理
│   ├── memory/                  ← /memory 持久记忆
│   ├── skills/                  ← /skills 技能管理
│   ├── agents/                  ← /agents 子代理管理
│   ├── login/ /logout/          ← 认证
│   ├── cost/                    ← 费用检查
│   ├── theme/                   ← 主题切换
│   ├── vim/                     ← Vim 模式
│   ├── voice/                   ← 语音输入
│   ├── plugin/                  ← 插件管理
│   ├── resume/                  ← 会话恢复
│   └── ...更多
│
├── components/ (235 文件)
│   ├── agents/ (26 文件)        ← Agent UI 组件
│   ├── messages/ (12 文件)      ← 消息渲染
│   ├── mcp/ (13 文件)           ← MCP UI
│   ├── design-system/ (16 文件) ← 设计系统
│   ├── App.tsx                  ← Ink 应用根组件
│   └── ...
│
├── services/
│   ├── api/                     ← Anthropic API 客户端
│   ├── mcp/                     ← MCP 连接管理
│   ├── oauth/                   ← OAuth 2.0 流程
│   ├── lsp/                     ← LSP 管理器
│   ├── analytics/               ← GrowthBook 特性开关
│   ├── compact/                 ← 对话压缩
│   ├── plugins/                 ← 插件加载器
│   └── ...
│
├── bridge/ (31 文件)
│   ├── bridgeMain.ts (2999 行)  ← IDE Bridge 主循环
│   ├── replBridge.ts (2406 行)  ← REPL Bridge
│   └── ...                      ← VS Code / JetBrains 集成
│
├── coordinator/                 ← 多 Agent 协调器
├── tasks/                       ← 任务管理（8 种 Task 类型）
├── plugins/                     ← 插件系统
├── skills/                      ← Skill 系统
├── hooks/                       ← React Hooks + 权限钩子
├── ink/                         ← Ink 渲染器封装
├── vim/                         ← Vim 模式实现
├── voice/                       ← 语音输入
├── remote/                      ← 远程会话
├── server/                      ← 服务器模式
├── memdir/                      ← 持久记忆目录
├── state/                       ← 状态管理
├── migrations/                  ← 配置迁移
└── schemas/                     ← Zod 配置 Schema
```

---

## 5. Phase 2：入口 — 启动流程

### 5.1 入口识别

**CLI 入口：** `main.tsx:1` — Commander.js CLI 路由，4684 行

启动优化策略（前 30 行即展现）：
1. `profileCheckpoint` — 性能标记（在任何重型模块加载前）
2. `startMdmRawRead` — 启动 MDM 子进程（与下方 imports 并行）
3. `startKeychainPrefetch` — 并行预取 macOS Keychain 凭证（避免同步阻塞 ~65ms）

### 5.2 启动流程

```
┌─────────────────────────────────────────────────┐
│ 1. CLI 入口 (Bun)                                  │
│    → Node.js 参数解析                              │
│    → 环境变量初始化                                 │
│    → --resume / --continue 会话恢复                │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 2. 并行预取层（side-effects import）               │
│    ├── MDM raw read (plutil/reg query)            │
│    ├── Keychain OAuth + API Key 预取              │
│    └── 与后续 ~135ms imports 并行执行             │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 3. 认证 & 授权                                     │
│    ├── loadPolicyLimits (组织策略)                 │
│    ├── loadRemoteManagedSettings (远程设置)        │
│    ├── OAuth 2.0 流程 (macOS/Linux/Windows)       │
│    └── API Key 验证                               │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 4. GrowthBook 特性开关初始化                        │
│    → bun:bundle feature flags 死代码消除          │
│    → 语音/Vim/Desktop/IDE 等 feature 条件加载      │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 5. Commander.js Command Tree 构建                  │
│    → /command 注册 (~50+ 个)                      │
│    → Tool 注册表 (~40+ 个)                        │
│    → Hooks 系统（权限/通知）                       │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 6. React + Ink 渲染                                │
│    → App.tsx → 主屏渲染                           │
│    → PromptInput → 用户输入框                     │
│    → LogSelector → 消息历史                       │
│    → 权限对话框 / Agent 进度线 / Skills 面板       │
└─────────────────────────────────────────────────┘
```

---

## 6. Phase 3：骨架 — 模块依赖拓扑

### 6.1 核心依赖图

```
main.tsx (Commander CLI Router)
├── @commander-js/extra-typings   ← CLI 框架
├── React + Ink                    ← 终端 UI
├── chalk                          ← 终端着色
├── lodash-es                      ← 工具函数
│
├── context.ts                     ← 系统/用户上下文
├── QueryEngine.ts                 ← LLM 查询引擎
│     ├── services/api/            ← Anthropic API
│     ├── cost-tracker.ts          ← Token 计费
│     └── hooks/toolPermission/    ← 权限检查
│
├── commands.ts (命令注册表)
│     └── commands/**/*.tsx        ← 各 slash 命令实现
│
├── tools.ts (工具注册表)
│     └── tools/**/                ← 各工具实现
│           ├── BashTool/ (18 文件) ← 最复杂的工具
│           │     ├── bashSecurity.ts (2592 行)
│           │     ├── bashPermissions.ts (2621 行)
│           │     ├── pathValidation.ts (1303 行)
│           │     ├── readOnlyValidation.ts (1990 行)
│           │     └── sedValidation.ts (684 行)
│           └── ...
│
├── coordinator/coordinatorMode.ts ← 多 Agent 协调
│     └── tasks/                    ← Task 类型
│           ├── DreamTask/          ← 后台 Agent
│           ├── LocalAgentTask/     ← 本地 Sub-Agent
│           ├── RemoteAgentTask/    ← 远程 Sub-Agent
│           ├── LocalShellTask/     ← Shell 任务
│           └── InProcessTeammateTask/ ← 单进程 Teammate
│
├── bridge/                         ← IDE 集成
│     ├── bridgeMain.ts (2999 行)   ← Bridge 主循环
│     └── replBridge.ts (2406 行)   ← REPL Bridge
│
├── services/
│     ├── api/                      ← Anthropic API
│     ├── mcp/                      ← MCP
│     ├── oauth/                    ← OAuth
│     ├── lsp/                      ← LSP
│     ├── analytics/               ← GrowthBook
│     └── compact/                  ← 上下文压缩
│
├── plugins/                        ← 插件系统
├── skills/                         ← Skill 系统
│     └── bundled/                  ← 内置 Skills
│
├── hooks/
│     ├── toolPermission/           ← 权限钩子（3 层）
│     └── notifs/                   ← 通知钩子
│
└── utils/                          ← 大量工具函数
      ├── git/                      ← Git 操作
      ├── bash/                     ← Shell 工具
      ├── permissions/              ← 权限工具
      ├── settings/                 ← 配置管理
      ├── memory/                   ← 记忆系统
      └── sandbox/                  ← 沙箱
```

**依赖方向：** main.tsx → commands/tools/services → utils → external libs。单向无循环。

---

## 7. Phase 4：血脉 — 数据流追踪

### 7.1 场景 A：用户输入 → AI 响应（正常对话）

```
用户
  │ 输入: "帮我重构这个函数"
  ▼
PromptInput (Ink Component)
  │ onSubmit()
  ▼
QueryEngine.ts
  ├─ [1] 构建 System Prompt (context.ts)
  │      ├── 系统信息: OS / Shell / Git / 工作目录
  │      ├── 项目上下文: 文件树 / Git 状态 / CLAUDE.md
  │      └── 用户上下文: memory / settings / permissions
  ├─ [2] 构建 Message List
  │      ├── ChatMemory (从 memdir 加载)
  │      ├── 历史 Message 压缩 (compact service)
  │      └── 当前 User Message
  ├─ [3] 调用 Anthropic API (services/api/)
  │      ├── Model: claude-sonnet-4-6 / claude-opus-4-7
  │      ├── Tools: 注册的 Tool[] (JSON Schema)
  │      └── Stream: SSE → Ink 逐字渲染
  ├─ [4] 解析响应
  │      ├── Text → AgentProgressLine 渲染
  │      ├── ToolUse → 调用对应 Tool.execute()
  │      │     ├── BashTool → bashSecurity 检查 + 执行
  │      │     ├── FileEditTool → 替换文本
  │      │     └── ...
  │      └── ToolResult → 回传 API (继续推理)
  └─ [5] 更新上下文
         ├── cost-tracker: Token 累计
         ├── history: 消息持久化
         └── memory: 自动记忆提取 (extractMemories)
```

### 7.2 场景 B：Sub-Agent 生成 (AgentTool)

```
主 Agent
  │ AgentTool 被调用 { description, prompt }
  ▼
AgentTool.execute()
  ├─ 创建 Task (LocalAgentTask / RemoteAgentTask)
  │     ├── Task ID 生成
  │     ├── Task Queue 入队
  │     └── task.ts → 状态: pending → running
  ├─ 启动子进程 (Bun.spawn) 或独立 QueryEngine
  │     ├── 独立的 System Prompt (仅包含 task description)
  │     ├── 独立的 Tool 列表 (受限)
  │     └── 独立的 Context Window
  ├─ 进度推送 via bridge/sendMessage
  │     └── SendMessageTool → Redis/Bridge → 主 Agent
  └─ 结果回传
        └── Task 状态: completed → 结果合并到主 Agent 响应
```

### 7.3 场景 C：Bash 执行安全链路

```
BashTool.execute(command)
  │
  ├─ [Layer 1] modeValidation.ts
  │      └── 检查当前权限模式 (default/plan/auto/bypass)
  │
  ├─ [Layer 2] destructiveCommandWarning.ts
  │      └── 检查危险命令 (rm -rf /, git push --force, etc.)
  │
  ├─ [Layer 3] bashSecurity.ts (2,592 行)
  │      ├── 命令注入检测
  │      ├── 路径安全 (防止逃逸)
  │      └── 环境变量隔离
  │
  ├─ [Layer 4] pathValidation.ts (1,303 行)
  │      ├── 工作目录外路径拒绝
  │      └── 敏感路径拒绝 (.git/config, .env, etc.)
  │
  ├─ [Layer 5] readOnlyValidation.ts (1,990 行)
  │      └── 只读模式：拒绝任何修改操作
  │
  ├─ [Layer 6] shouldUseSandbox.ts
  │      └── 沙箱模式判断 (Docker/VM)
  │
  ├─ [Layer 7] userPermission prompt (hooks/toolPermission)
  │      └── CLI 权限对话框 → 用户批准/拒绝
  │
  └─ Execute
         └── Bun.spawn → stdout/stderr 流式返回
```

---

## 8. Phase 5：精髓 — 设计模式 & 巧妙实现

### 8.1 识别到的设计模式/技巧

| # | 发现 | 位置 | 类型 |
|---|------|------|------|
| 1 | **Command 模式** | `commands.ts` — 每个 slash 命令独立注册 | 设计模式 |
| 2 | **Strategy 模式** | `Tool.ts` — 每个 Tool 独立 schema + execute | 设计模式 |
| 3 | **Pipeline/Chain of Responsibility** | BashTool 7 层安全检查链 | 设计模式 |
| 4 | **Observer 模式** | Bridge 系统 — IDE 与 CLI 双向事件推送 | 设计模式 |
| 5 | **Builder 模式** | System Prompt 累积构建 (`context.ts`) | 惯用法 |
| 6 | **Feature Flags** | `bun:bundle` — 编译时死代码消除 | 架构技巧 |
| 7 | **并行预取优化** | `main.tsx` — Side-effects import 并行执行 | 性能优化 |
| 8 | **Sub-Agent Fan-out** | `coordinator/` — 任务分发到多个子 Agent | AI 模式 |
| 9 | **ReAct Loop** | `QueryEngine` — Reasoning→Action→Observation 循环 | AI 模式 |
| 10 | **Compaction 策略** | `services/compact/` — 上下文窗口压缩 | AI 优化 |
| 11 | **Memory 自动提取** | `services/extractMemories/` — 从对话中自动提取记忆 | AI 创新 |
| 12 | **Worktree 隔离** | `EnterWorktreeTool` — Git Worktree 子进程隔离 | 安全设计 |
| 13 | **Plugin 热加载** | `plugins/` — 运行时插件发现 + 加载 | 架构模式 |
| 14 | **Zod Schema 验证** | `schemas/` — 配置/工具输入的运行时类型安全 | 类型安全 |

### 8.2 巧妙实现细节

**BashTool 7 层安全链：**
```
modeValidation → destructiveWarning → bashSecurity → 
pathValidation → readOnlyValidation → sandbox → userPrompt → Execute
```
每层独立、可测试、可配置。这是生产级 Shell 安全的教科书实现。

**`bun:bundle` Feature Flags（编译时死代码消除）：**
```typescript
import { feature } from 'bun:bundle'
// 未启用的 feature 分支在构建时被完全移除
const voiceCommand = feature('VOICE_MODE')
  ? require('./commands/voice/index.js').default
  : null
```
不编译进最终产物的代码零字节开销。

**启动性能优化（并行预取）：**
```
Side-effects import 在模块解析期间启动 OS 子进程：
  - MDM raw read (plutil/reg query) ────┐
  - Keychain OAuth prefetch   ──────────┤ 并行执行
  - Keychain API Key prefetch ───────────┤
  - 剩余 ~135ms imports      ───────────┘
→ 节省 ~65ms 每次启动
```

**Agent 协调器（Fan-out / Fan-in）：**
```
主 Agent
  ├→ Sub-Agent 1 (LocalAgentTask) → 独立 Context
  ├→ Sub-Agent 2 (LocalAgentTask) → 独立 Context  
  └→ Sub-Agent 3 (RemoteAgentTask) → 远程执行
         │
         └→ SendMessageTool → 结果收集 → 主 Agent 汇总
```

**Context Compaction：**
当对话超过 Token 限制时，`compact/` 服务自动：
1. 识别可压缩的消息段
2. 调用 API 生成摘要
3. 用摘要替换原始消息
4. 保持关键上下文（文件编辑/工具调用结果）不被压缩

---

## 9. Phase 6：实战 — 动手任务

### 9.1 建议的练习

| 难度 | 任务 | 涉及区域 |
|------|------|----------|
| 🟢 初级 | 追踪一个简单 `/help` 命令从注册到渲染的完整路径 | commands/help, commands.ts, ink/ |
| 🟢 初级 | 理解 FileEditTool 的 `old_string` → `new_string` 替换逻辑 | tools/FileEditTool/ |
| 🟡 进阶 | 分析 BashTool 的 `sedEditParser` 如何解析 `sed` 兼容的编辑命令 | tools/BashTool/sedEditParser.ts |
| 🟡 进阶 | 追踪 `extractMemories` 服务如何在对话结束后自动生成记忆 | services/extractMemories/ |
| 🔴 深入 | 分析 Coordinator 如何决定何时创建 Sub-Agent vs 自己执行 | coordinator/ |
| 🔴 深入 | 理解 Bridge 协议如何在 VS Code 和 CLI 之间同步状态 | bridge/ |

---

## 10. Bug 发现 & 修复

### 10.1 本次测试发现

| # | 严重性 | 描述 | 位置 | 状态 |
|---|--------|------|------|------|
| 10 | 高 | Windows GBK 编码崩溃 — TS 源文件含 Unicode 字符（✦ 等），`print(json.dumps(ensure_ascii=False))` 在 GBK stdout 上抛出 `UnicodeEncodeError` | `ast_skeleton.py:439` | ✅ 已修复 |
| 11 | 中 | 500 文件硬限制 — `discover_files()` 返回 `found[:500]`，1902 文件仅分析 26% | `ast_skeleton.py:84` | ⚠️ 待修复 |
| 12 | 中 | TS `class` 未提取 — 正则 `^\s*class\s+` 不匹配 `export class` 等带修饰符的类声明 | `ast_skeleton.py:extract_typescript()` | ⚠️ 待修复 |

### 10.2 修复详情

**Bug #10 — Windows GBK 编码崩溃：**

`print()` 在 Windows 上默认使用 GBK 编码。当 TypeScript 源文件包含 Unicode 字符时，`json.dumps(ensure_ascii=False)` 产生的输出无法被 GBK 编码，导致 `UnicodeEncodeError`。

修复：
```python
def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ...
```

**Bug #11 — 500 文件硬限制：**

`discover_files()` 函数在 `return found[:500]` 处截断。对于大型项目（>500 文件），后续文件全部丢失。需要改为可配置参数或按模块采样。

**Bug #12 — TS class 提取失效：**

当前正则：`r'^\s*class\s+(\w+)'` 不匹配：
- `export class Foo` — 有 export 修饰
- `export default class Foo` — 有 default
- `abstract class Foo` — 有 abstract

需更新为：`r'^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)'`

### 10.3 全部 Bug 汇总

| # | 描述 | 状态 |
|---|------|------|
| 1 | `git_archaeology.sh` `$FILE_COUNT` 变量名错误 | ✅ |
| 2 | `clone_and_analyze.sh` bash 4.x `declare -A` 不兼容 macOS | ✅ |
| 3 | `.py` `subprocess.run` 未指定 `encoding='utf-8'` | ✅ |
| 4 | `.py` `active_branches` 包含 `HEAD ->` | ✅ |
| 5 | `.sh` `active_branches` 未过滤 `HEAD ->` | ✅ |
| 6 | C/C++ 文件无 `#include` 提取规则 | ✅ |
| 7 | C++ `Class::method()` 正则不匹配 | ✅ |
| 8 | HTTPS clone 中国大陆网络不稳定 | ⚠️ 网络 |
| 9 | Java package 声明提取缺失 | ✅ |
| **10** | **Windows GBK 编码崩溃（Unicode 字符）** | ✅ |
| **11** | **500 文件硬限制** | ⚠️ |
| **12** | **TS `export class` 提取失效** | ⚠️ |

---

## 11. 测试覆盖总结

| 层 | 内容 | 结果 |
|----|------|------|
| **脚本执行** | AST skeleton (500/1902 文件, 110K/512K 行) | ⚠️ 部分 |
| **Pre-flight** | API zipball 下载 + 技术栈 + 类型分类 | ✅ |
| **Phase 0** | Git 考古（单快照降级） | ✅ |
| **Phase 1** | 项目名片 + 架构鸟瞰 | ✅ |
| **Phase 2** | 入口识别 + 启动流程（含性能优化层） | ✅ |
| **Phase 3** | 依赖拓扑 + BashTool 安全链路 | ✅ |
| **Phase 4** | 3 条数据流（对话/Sub-Agent/Shell安全） | ✅ |
| **Phase 5** | 设计模式识别 (14 项) + 巧妙实现 (5 项) | ✅ |
| **Phase 6** | 实战任务设计 (6 个，3 级别) | ✅ |

### 未覆盖场景

| 场景 | 原因 |
|------|------|
| 多 commit 演化史 (Phase 0) | 无 `.git` 目录 |
| 完整 1902 文件 AST | 500 文件限制 (待修复) |
| Claude Code 运行时行为 | 需要 Anthropic API Key |
| Bun 构建流程 | 无 package.json/bunfig.toml |
| 导游模式/断点续传 | 需 Claude Code 交互环境 |

---

## 12. 结论

**Claude Code CLI 是 project-mentor 测试过的最复杂项目（~512K 行 TypeScript，1902 文件），揭示了大项目测试的多个边界问题。**

本次测试：
- 验证了 Windows GBK 编码问题在包含 Unicode 的项目上的严重性
- 发现了 `discover_files()` 500 文件上限对大项目的限制
- 暴露了 TS class 提取正则不完整的问题
- 分析了 Claude Code 的生产级架构：7 层 Bash 安全链、Bun feature flags、并行预取、Sub-Agent Fan-out、Context compaction

**Claude Code 源码核心洞察：**
1. **安全第一** — BashTool 仅安全相关代码就 ~12K 行（7 层验证链）
2. **极致性能** — 启动时 side-effects import 并行预取、`bun:bundle` 死代码消除
3. **Agent 架构** — 主 Agent + 8 种 Task 类型，支持本地/远程 Sub-Agent
4. **IDE 融合** — Bridge 系统实现 CLI ↔ VS Code/JetBrains 双向通信
5. **企业能力** — OAuth/GrowthBook/PolicyLimits/RemoteSettings 完整企业功能

---

> *测试完成于 2026-05-13 · project-mentor v2 · 测试者：Claude + Master*
