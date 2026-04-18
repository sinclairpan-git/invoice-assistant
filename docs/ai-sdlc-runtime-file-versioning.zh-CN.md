# AI-SDLC 运行态文件版本控制审计

## 目的

归档 2026-04-19 对 `.ai-sdlc/` 与 `specs/` 工件边界的版本控制审计，并明确本仓库对运行态文件、formal 工件与遗留兼容文件的纳管策略。

## 审计起点（执行前）

- 已跟踪文件：
  - `.ai-sdlc/memory/constitution.md`
  - `.ai-sdlc/profiles/tech-stack.yml`
  - `.ai-sdlc/profiles/decisions.yml`
  - `.ai-sdlc/project/config/project-config.yaml`
  - `.ai-sdlc/project/config/project-state.yaml`
- 已忽略目录：
  - `.ai-sdlc/local/`
  - `.ai-sdlc/state/`
  - `.ai-sdlc/work-items/`

## 执行后状态

- 继续受版本控制：
  - `.ai-sdlc/memory/constitution.md`
  - `.ai-sdlc/profiles/tech-stack.yml`
  - `.ai-sdlc/profiles/decisions.yml`
  - `.ai-sdlc/project/config/project-state.yaml`
  - `.ai-sdlc/work-items/**/reviewer-decision*.yaml`
  - `specs/**/spec.md`
  - `specs/**/plan.md`
  - `specs/**/tasks.md`
  - `specs/**/task-execution-log.md`
  - `specs/**/development-summary.md`
  - `specs/**/release-gate-evidence.md`
- 停止跟踪并保留本地运行：
  - `.ai-sdlc/project/config/project-config.yaml`
- 保留已存在文件，但按遗留兼容镜像理解：
  - `specs/**/execution-log.md`

## 事实

1. 当前工作区唯一相关脏改动来自 `.ai-sdlc/project/config/project-config.yaml`，差异仅为 `adapter_activated_at` 时间戳。
2. AI-SDLC 上游实现将 `project-config.yaml` 定义为“often gitignored”：
   - `src/ai_sdlc/models/project.py`
   - `src/ai_sdlc/core/config.py`
   - `src/ai_sdlc/stages/init.yaml`
3. AI-SDLC 上游实现说明：当 `project-config.yaml` 缺失时，加载逻辑返回默认配置；后续保存或 IDE 适配会重新生成该文件。
4. `project-state.yaml` 是 init 阶段显式输出物，也是 pipeline gate 读取对象；当前没有同等证据表明它应默认移出版本控制。
5. 仅新增 `.gitignore` 规则不足以解决问题，因为 `project-config.yaml` 已经被 Git 跟踪；若要消除这类运行态 diff，必须停止跟踪该文件。
6. `project-state.yaml` 当前只包含 6 个低频字段：`status`、`project_name`、`initialized_at`、`last_updated`、`next_work_item_seq`、`version`。
7. AI-SDLC 上游仅在少数“项目真值变化”路径写回 `project-state.yaml`：
   - `bootstrap` 初始化项目时写入初值
   - `work_intake` 创建 intake work item 时推进 `next_work_item_seq`
   - `workitem_scaffold` 直接初始化 formal work item 时推进 `next_work_item_seq`
8. `python -m ai_sdlc run --dry-run` 不会改写 `project-state.yaml`；本轮审计中工作区在 dry-run 后保持干净。
9. 仓库历史中，`project-state.yaml` 的提交只出现在基线初始化、work item 序号推进、运行态恢复收口等少量节点，并未表现出类似 `project-config.yaml` 的频繁时间戳噪音。
10. `.ai-sdlc/work-items/003-runtime-state-recovery/reviewer-decision-pre-close.yaml` 已被仓库跟踪，但该目录此前被整目录 `.gitignore`，说明 ignore 规则与 formal reviewer gate 工件的真实使用存在冲突。
11. AI-SDLC 上游会把 `reviewer-decision-<checkpoint>.yaml` 作为 reviewer gate 的正式输入，并在 `close-check` 中校验其存在与审批结果。
12. `.ai-sdlc/memory/constitution.md`、`.ai-sdlc/profiles/tech-stack.yml`、`.ai-sdlc/profiles/decisions.yml` 被 stage/rule 直接引用，属于 canonical 治理与设计输入，而不是运行态缓存。
13. 这三份文件在仓库历史中仅出现在项目初始化基线提交中，本轮未观察到日常命令触发的自动改写行为。
14. AI-SDLC 上游 `pipeline.md` 将 direct-formal work item 的核心文档面定义为 `spec.md`、`plan.md`、`tasks.md` 与 `task-execution-log.md`，`close` 阶段也以 `task-execution-log.md` 和 `tasks.md` 作为主要输入。
15. 上游实现同时把 `development-summary.md`、`release-gate-evidence.md` 视为 formal close / verify 工件；它们会被 `reconcile`、`close-check`、`verify_constraints` 等路径读取。
16. 上游 `core/executor.py` 仍保留 `execution-log.md` 兼容写入，并明确注释“Keep legacy execution-log.md in sync until drift cleanup batch.”，说明它是遗留镜像而非新的独立真源。
17. 本仓库当前仅 `specs/002-invoice-assistant-runtime-hardening/` 存在 `execution-log.md`，且与 `task-execution-log.md` 内容一致，没有发生漂移。

## 结论

### P1 立即执行：停止跟踪 `project-config.yaml`

- **状态**：本轮执行
- **原因**：
  - 文件内容以 IDE 适配状态、激活证据、时间戳等运行态元数据为主
  - 上游实现已明确按“通常应被 gitignore”设计
  - 继续跟踪只会让 `adapter activate` 一类常规动作不断制造无意义 diff

### P2 保持 `project-state.yaml` 继续受控

- **状态**：保留
- **原因**：
  - 该文件承载初始化状态、序列号等流水线真值
  - 现阶段缺少足够证据支持把它也降为纯运行态
  - 缺失该文件会破坏 AI-SDLC formal bootstrap / work item 初始化入口
  - 它的变更频率与“项目状态跃迁”相关，而不是与每次日常命令执行相关

### P3 不采用 `skip-worktree` 作为仓库方案

- **状态**：拒绝
- **原因**：
  - 这是本地掩盖手段，不是团队可见策略
  - 容易把真正需要审阅的配置改动一起藏掉

### P4 收窄 `.ai-sdlc/work-items/` 的 ignore 范围

- **状态**：本轮执行
- **原因**：
  - work item 目录下大部分文件确实是运行态产物，仍应保持忽略
  - 但 `reviewer-decision*.yaml` 属于 formal reviewer gate 工件，不能继续被整目录 ignore 误伤
  - 调整后，未来新增 reviewer decision 工件可正常进入版本控制，其余运行态 work item 文件仍保持忽略

### P5 保持宪章与 profiles 文件继续受控

- **状态**：确认保留
- **原因**：
  - 它们属于 stage/rule 的直接输入
  - 当前没有运行时噪音改写迹象
  - 将其移出版本控制会削弱仓库内的 canonical 治理与设计基线

### P6 明确 `specs/` 与 `.ai-sdlc/work-items/` 的真值边界

- **状态**：本轮补充归档规则
- **原因**：
  - `specs/NNN/` 承载 formal work item 的可审阅真源，至少包括 `spec.md`、`plan.md`、`tasks.md`、`task-execution-log.md`
  - `development-summary.md`、`release-gate-evidence.md` 在生成后也属于 formal 归档/验证工件，应继续受控
  - `.ai-sdlc/work-items/NNN/` 下的 `runtime.yaml`、`working-set.yaml`、`resume-pack.yaml`、`latest-summary.md`、`execution-plan.yaml` 仍是执行期状态面，不应替代 `specs/` 真源
  - `execution-log.md` 目前仅作为历史兼容镜像存在；在上游完成 drift cleanup 之前，可保留已生成文件，但不应把它当成独立来源或单独编辑

## 本轮落地动作

1. 在 `.gitignore` 中显式忽略 `.ai-sdlc/project/config/project-config.yaml`
2. 将 `project-config.yaml` 从 Git 跟踪集合移除，但保留本地文件供 AI-SDLC 继续读写
3. 执行 `python -m ai_sdlc run --dry-run`，确认仓库约定未被破坏
4. 核对 `specs/002-invoice-assistant-runtime-hardening/execution-log.md` 与 `task-execution-log.md` 一致，确认遗留镜像未发生漂移
5. 新增 `workspace_tools/version_control_policy.py` 与 `backend/tests/test_git_tracked_policy.py`，把运行态文件版本控制边界固化为自动回归守卫

## 后续约束

1. 功能提交、文档提交、归档提交均不再混入 `project-config.yaml` 的运行态变更。
2. 若未来确实需要持久化非默认的稳定项目级配置，应新增专门的受控模板/默认文件，而不是重新把运行态文件纳回版本控制。
3. `project-state.yaml` 只应在以下场景进入提交：
   - 项目初始化或 bootstrap 修复
   - 新建 canonical work item 导致 `next_work_item_seq` 合法推进
   - 经确认的状态恢复/真值修复
4. `.ai-sdlc/work-items/` 下仅 `reviewer-decision*.yaml` 允许作为 formal 工件入库，其他 work item 运行态文件继续忽略。
5. `.ai-sdlc/memory/constitution.md`、`.ai-sdlc/profiles/*.yml` 继续作为 canonical 基线受控，不按运行态文件处理。
6. 在没有新的上游证据前，不扩展到 `.ai-sdlc/project/config/project-state.yaml` 之外的更多 project 配置文件。
7. `specs/` 下如需追加或修改 formal work item 归档，优先更新 `task-execution-log.md`；若仓库内已存在同目录 `execution-log.md`，仅在保持与前者同步时被动保留，禁止把两者当作两个独立文档面维护。
8. `.ai-sdlc/work-items/` 运行态文件只作为恢复执行上下文使用，不作为 close、verify、traceability 的最终审阅依据；最终真值以 `specs/` 下 formal 文档为准。
9. 任何新提交若试图重新纳入 `project-config.yaml`、`.ai-sdlc/work-items/` 运行态文件或新的 `specs/**/execution-log.md`，都应先更新自动策略守卫与审计文档，再解释为何要突破当前边界。
