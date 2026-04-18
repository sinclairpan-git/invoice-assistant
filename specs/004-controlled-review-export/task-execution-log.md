# 任务执行日志：发票整理助手四期：受控复核与导出闭环

**功能编号**：`004-controlled-review-export`  
**创建日期**：2026-04-18  
**状态**：Batch 1、Batch 2 已完成；待进入单票结果字段与导出门槛批次

## 1. 归档规则

- 本文件是 `004-controlled-review-export` 的固定执行归档文件。
- 后续每完成一批任务，都在**本文件末尾追加一个新的批次章节**。
- 后续每一批任务开始前，必须先完成固定预读（PRD + 宪章 + 当前相关 spec 文档）。
- 后续每一批任务结束后，必须先完成实现和验证，再把本批结果追加归档到本文件。
- 执行归档与 `tasks.md` 勾选状态必须同步更新，避免文档真值漂移。
- 每个任务记录固定包含以下字段：
  - 任务编号
  - 任务名称
  - 改动范围
  - 改动内容
  - 新增/调整的测试
  - 执行的命令
  - 测试结果
  - 是否符合任务目标

## 2. 批次记录

### Batch 2026-04-18-001 | T11-T13

#### 2.1 批次范围

- 覆盖任务：`T11`、`T12`、`T13`
- 覆盖阶段：Batch 1 文档基线与治理边界冻结
- 预读范围：`发票整理助手_评审终版_重新生成.md`、`.ai-sdlc/memory/constitution.md`、`specs/001-invoice-assistant-mvp/spec.md`、`specs/003-runtime-state-recovery/spec.md`
- 激活的规则：`FR-001` 至 `FR-017` 的文档冻结基线

#### 2.2 统一验证命令

- `V1`（框架入口）
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS，记录当前 adapter acknowledgement
- `V2`（框架预演）
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS，当前 checkpoint 预演成功
- `V3`（work item 初始化）
  - 命令：`python -m ai_sdlc workitem init --wi-id 004-controlled-review-export --title '受控复核与导出闭环' --input '把操作者身份从前端自由输入改成后端可信身份；给规则修改、复核、导出挂上角色权限；单票结果补齐基础合规/业务合规/原因/建议动作；明确导出门槛和审计口径。'`
  - 结果：PASS，生成 `spec.md / plan.md / tasks.md / task-execution-log.md`

#### 2.3 任务记录

##### T11 | 固化四期规格与范围边界

- 改动范围：`specs/004-controlled-review-export/spec.md`
- 改动内容：将第二优先级需求收敛为可信身份、角色权限、单票解释层和导出门槛四条主线；明确不覆盖登录系统与规则引擎重写。
- 新增/调整的测试：无，本批仅冻结规格。
- 执行的命令：文档对账、现状代码检索、PRD 范围核对。
- 测试结果：不适用。
- 是否符合任务目标：是。

##### T12 | 固化四期实施计划与验证策略

- 改动范围：`specs/004-controlled-review-export/plan.md`
- 改动内容：补齐实现阶段、工作流、验证命令和执行边界，明确“红灯测试先行”和“不引入登录系统扩张”。
- 新增/调整的测试：无，本批仅冻结计划。
- 执行的命令：现状代码结构阅读、测试文件布局核对。
- 测试结果：不适用。
- 是否符合任务目标：是。

##### T13 | 建立四期任务批次与执行日志基线

- 改动范围：`specs/004-controlled-review-export/tasks.md`、`specs/004-controlled-review-export/task-execution-log.md`
- 改动内容：按文档冻结、身份权限实现、结果导出实现、验证归档四个批次拆解任务，并建立首批执行归档。
- 新增/调整的测试：无，本批仅建立任务与归档基线。
- 执行的命令：`git switch -c codex/004-controlled-review-export`
- 测试结果：不适用。
- 是否符合任务目标：是。

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：已对齐。四期文档明确落库，并以测试和审计作为收口依据。
- 代码质量：本批无生产代码改动。
- 测试质量：本批未进入 TDD 红灯阶段，下一批以回归测试先行。
- 结论：允许进入 Batch 2 的红灯回归与实现准备。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：已同步，Batch 1 勾选完成，后续批次保持待办。
- `related_plan`（如存在）同步状态：无额外 external plan。
- 关联 branch/worktree disposition 计划：继续在 `codex/004-controlled-review-export` 上推进 Batch 2。
- 说明：本批只完成文档冻结，不声明实现已开始。

#### 2.6 自动决策记录（如有）

- 后端可信身份方案暂按“后端受控配置 / 上下文派生，前端只读消费”收口，不扩展为完整登录系统。
- `suggested_pass_zip` 暂按“存在待复核票据则拒绝导出”冻结为四期规则。

#### 2.7 批次结论

- 四期文档基线已建立，可进入可信身份与权限控制的红灯回归阶段。

#### 2.8 归档后动作

- 已完成 git 提交：否
- 提交哈希：待后续实现批次提交时生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是，下一批为 `T21` / `T22` / `T23`

### Batch 2026-04-18-002 | T21-T23

#### 2.1 批次范围

- 覆盖任务：`T21`、`T22`、`T23`
- 覆盖阶段：Batch 2 红灯回归 + 可信身份与角色控制实现
- 预读范围：`.ai-sdlc/memory/constitution.md`、`specs/004-controlled-review-export/spec.md`、`specs/004-controlled-review-export/plan.md`、`specs/004-controlled-review-export/tasks.md`
- 激活的规则：受控动作身份派生、角色拒绝审计、前端只读身份消费

#### 2.2 统一验证命令

- `V1`（adapter acknowledgement）
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS，记录当前 Codex adapter acknowledgement；仍按 `soft_prompt_only` 理解。
- `V2`（框架预演）
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：RETRY，`execute` / `close` 阶段仍有 open gates；本批继续在预演成功范围内推进定向实现和测试。
- `V3`（后端定向回归）
  - 命令：`uv run --project backend --extra dev python -m pytest backend/tests/test_api_workflows.py -q`
  - 结果：先 RED（4 failed, 5 passed），完成实现后 GREEN（9 passed）。
- `V4`（前端定向回归）
  - 命令：`npm test -- tests/app-shell.test.tsx tests/runtime-ui.test.tsx`（在 `frontend/` 目录执行）
  - 结果：先 RED（2 failed, 5 passed），修正 shell 文案冲突后 GREEN（7 passed）。

#### 2.3 任务记录

##### T21 | 后端红灯测试覆盖可信身份派生与角色拒绝

- 改动范围：`backend/tests/test_api_workflows.py`
- 改动内容：沿用上一轮已写入的红灯测试，覆盖 `/api/me`、受控动作身份派生、缺少 `config_admin` / `reviewer` / `exporter` 时的 `403` 和 denied audit。
- 新增/调整的测试：`test_controlled_identity_comes_from_backend_actor_context`、`test_rule_version_requires_config_admin_and_records_denied_audit`、`test_review_action_requires_reviewer_and_records_denied_audit`、`test_export_requires_exporter_and_records_denied_audit`
- 执行的命令：`uv run --project backend --extra dev python -m pytest backend/tests/test_api_workflows.py -q`
- 测试结果：RED 阶段暴露 `/api/me` 缺失及受控接口仍要求前端提交 `changed_by` / `reviewed_by` / `created_by`。
- 是否符合任务目标：是。

##### T22 | 前端红灯测试覆盖操作者只读展示与自由输入移除

- 改动范围：`frontend/tests/app-shell.test.tsx`、`frontend/tests/runtime-ui.test.tsx`
- 改动内容：沿用上一轮已写入的红灯测试，校验界面必须消费后端当前操作者，并移除上传、复核、配置表单中的可编辑操作者输入。
- 新增/调整的测试：`App shell > renders navigation and workbench title`、`runtime UI > removes editable operator inputs from upload, review, and config forms`
- 执行的命令：`npm test -- tests/app-shell.test.tsx tests/runtime-ui.test.tsx`
- 测试结果：RED 阶段暴露界面仍显示本地伪造姓名、仍保留可编辑操作者输入。
- 是否符合任务目标：是。

##### T23 | 实现后端可信身份上下文与受控 API 入参

- 改动范围：`backend/app/api/actors.py`、`backend/app/api/dependencies.py`、`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/config.py`、`backend/app/main.py`、`frontend/src/app/api.ts`、`frontend/src/app/types.ts`、`frontend/src/app/operator-settings.tsx`、`frontend/src/app/shell.tsx`、`frontend/src/components/batch/UploadPanel.tsx`、`frontend/src/components/results/ReviewActions.tsx`、`frontend/src/components/settings/RuleVersionPanel.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/pages/Settings.tsx`
- 改动内容：
  - 新增 `/api/me` 和 `TrustedActor` 解析逻辑，后端从可信上下文派生操作者并在缺少角色时写 denied audit。
  - 将批次创建、复核、规则版本、导出接口中的 `created_by` / `reviewed_by` / `changed_by` 调整为受控派生或兼容回填，不再要求前端自由输入。
  - 前端引入 `getCurrentActor()`，将 `OperatorSettingsProvider` 改为只读消费后端身份，并移除上传、复核、配置、导出流程中的可编辑操作者字段。
- 新增/调整的测试：使用 `T21`、`T22` 的定向回归作为实现验证。
- 执行的命令：
  - `uv run --project backend --extra dev python -m pytest backend/tests/test_api_workflows.py -q`
  - `npm test -- tests/app-shell.test.tsx tests/runtime-ui.test.tsx`
- 测试结果：GREEN，后端 `9 passed`；前端 `7 passed`。
- 是否符合任务目标：是。

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：已对齐。Batch 2 仅落地可信身份、角色控制和 denied audit，不扩展为登录系统。
- 代码质量：实现沿用现有 API 边界，新增 `/api/me` 与依赖解析，前端只改身份来源与受控表单入口。
- 测试质量：先观察 RED，再补最小实现并复跑 GREEN；结果与 Batch 2 任务定义一致。
- 结论：允许进入 Batch 3 的结果字段与导出门槛红灯回归。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：已同步，`T21` / `T22` / `T23` 勾选完成。
- `related_plan`（如存在）同步状态：无额外 external plan。
- 关联 branch/worktree disposition 计划：继续在 `codex/004-controlled-review-export` 上推进 Batch 3。
- 说明：本批已完成实现与定向回归，但未声明 Batch 3 / Batch 4 已完成。

#### 2.6 自动决策记录（如有）

- 前端保留 `useOperatorSettings()` 命名，仅替换为后端可信身份读取，避免在当前批次做无关的上下文重构。
- 后端保留对未配置可信 actor 的兼容回填，以减少既有非受控路径的破坏面，但在受控测试场景下严格忽略前端伪造姓名。
- `AppShell` 的静态标签使用“可信上下文”而不是“后端可信身份”，避免与真实操作者名重复导致前端测试歧义。

#### 2.7 批次结论

- Batch 2 已完成，系统现在可以从后端可信上下文派生操作者，并对受控动作实施角色拒绝与 denied audit。

#### 2.8 归档后动作

- 已完成 git 提交：否
- 提交哈希：待后续实现批次提交时生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是，下一批为 `T31` / `T32`
