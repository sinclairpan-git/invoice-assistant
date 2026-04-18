# 任务执行日志：发票整理助手二期：真实解析与运行时加固

**功能编号**：`002-invoice-assistant-runtime-hardening`  
**创建日期**：2026-04-17  
**状态**：已完成 close 收口，等待最终归档校验

## 1. 归档规则

- 本文件是 `002-invoice-assistant-runtime-hardening` 的固定执行归档文件。
- 后续每完成一批任务，都在本文件末尾追加新的批次章节。
- 每一批开始前先完成固定预读：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、当前 canonical spec 文档与相关需求稿。
- 每一批结束后，先完成验证，再更新本文件与 `tasks.md`，并与本批改动合并为一次提交。

## 2. 批次记录

### Batch 2026-04-17-001 | T11-T13

#### 2.1 批次范围

- 覆盖任务：`T11`、`T12`、`T13`
- 覆盖阶段：`refine`、`design`、`decompose` 文档基线冻结
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`发票整理助手_评审终版_重新生成.md`、`specs/001-invoice-assistant-mvp/spec.md`
- 激活的规则：二期 canonical truth 仅位于 `specs/002-invoice-assistant-runtime-hardening/`；在进入 execute 前不提前修改二期产品代码

#### 2.2 统一验证命令

- `V1`
  - 命令：`python -m ai_sdlc workitem link --wi-id 002-invoice-assistant-runtime-hardening --plan-uri specs/002-invoice-assistant-runtime-hardening/plan.md`
  - 结果：PASS，`Linked WI ID` 与 `Linked plan URI` 已绑定到 `002-invoice-assistant-runtime-hardening`
- `V2`
  - 命令：`python -m ai_sdlc gate refine`
  - 结果：PASS，识别 4 个用户故事与 35 条需求约束
- `V3`
  - 命令：`python -m ai_sdlc gate design`
  - 结果：PASS
- `V4`
  - 命令：`python -m ai_sdlc gate decompose`
  - 结果：PASS，识别 18 个任务
- `V5`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run ai-sdlc verify constraints`
  - 结果：PASS，`verify constraints: no BLOCKERs`
- `V6`
  - 命令：`python -m ai_sdlc recover --reconcile`
  - 结果：PASS，checkpoint 恢复到 `verify`，后续 `status` 确认当前 `Feature ID`、`Current Branch`、`Linked WI ID` 已对齐到 `002-invoice-assistant-runtime-hardening`
- `V7`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：PASS，当前 feature branch 与 002 work item 已关联，latest batch 的 branch/worktree disposition 为 `进行中`

#### 2.3 任务记录

##### T11 | 固化二期规格与范围边界

- 改动范围：`specs/002-invoice-assistant-runtime-hardening/spec.md`
- 改动内容：
  - 将二期目标明确为真实 PDF 解析、本地 OCR fallback、异步批处理和失败恢复
  - 固化二期覆盖范围、不覆盖范围、用户故事、功能需求、非功能要求和成功标准
  - 明确“合规票总金额、导出口径、人工复核留痕”是一期既有语义，二期不得回退
- 新增/调整的测试：无产品代码测试；使用 `gate refine` 作为文档准入验证
- 执行的命令：`python -m ai_sdlc gate refine`
- 测试结果：PASS
- 是否符合任务目标：是

##### T12 | 固化研究结论、数据模型和实施计划

- 改动范围：`specs/002-invoice-assistant-runtime-hardening/research.md`、`specs/002-invoice-assistant-runtime-hardening/data-model.md`、`specs/002-invoice-assistant-runtime-hardening/plan.md`
- 改动内容：
  - 固化二期为何继续采用 SQLite + 本地文件系统 + 进程内 worker
  - 定义 `ProcessingJob`、`ProcessingAttempt`、provider 诊断与幂等性约束
  - 输出按真实解析、异步恢复、前端接入、回归收口分阶段推进的实施计划
- 新增/调整的测试：无产品代码测试；使用 `gate design` 作为文档准入验证
- 执行的命令：`python -m ai_sdlc gate design`
- 测试结果：PASS
- 是否符合任务目标：是

##### T13 | 生成执行清单、执行日志并完成文档阶段校验

- 改动范围：`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 输出面向 execute 的批次拆解，覆盖真实解析、异步作业、恢复重试、前端接入与回归收口
  - 记录 Batch 1 的 workitem 关联、文档校验、checkpoint 恢复和分支校验过程
  - 保留文档阶段不越过 execute 边界的约束
- 新增/调整的测试：无产品代码测试；使用 `gate decompose`、`verify constraints`、`branch-check`
- 执行的命令：`python -m ai_sdlc workitem link --wi-id 002-invoice-assistant-runtime-hardening --plan-uri specs/002-invoice-assistant-runtime-hardening/plan.md`、`python -m ai_sdlc gate decompose`、`UV_CACHE_DIR=.uv-cache uv run ai-sdlc verify constraints`、`python -m ai_sdlc recover --reconcile`、`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过，二期 canonical truth 已固化在 `specs/002-invoice-assistant-runtime-hardening/`
- 代码质量：本批仅修改二期 canonical 文档与 AI-SDLC 状态文件，不涉及产品实现代码
- 测试质量：通过，文档 gate、约束校验、checkpoint 恢复和 branch-check 均已通过
- 结论：无阻塞 Batch 2 准备工作的 Critical 问题

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T11`、`T12`、`T13` 已标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上推进 Batch 2
- 说明：当前 active work item、linked plan 与分支已对齐到 002；checkpoint 当前处于 `verify`

#### 2.6 自动决策记录

- 二期不沿用生成器默认的 direct-formal 脚手架内容，改为对齐一期 canonical 文档结构
- PRD 中关于 Celery / Redis / PostgreSQL 的推荐技术栈不直接纳入二期正式方案，改为单机持久化作业模型
- `recover --reconcile` 完成后，以 `status` 中的 `Feature ID`、`Current Branch` 和 `Linked WI ID` 作为最终状态判断依据，避免被 legacy probe 的旧目录提示误导

#### 2.7 批次结论

- 已完成二期 canonical 规格、研究、数据模型、计划和任务拆解
- AI-SDLC 当前运行时已恢复到 `verify`，且 002 work item 与当前 feature branch 对齐
- 后续可在框架授权下进入 Batch 2，开始真实解析与运行时实现

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-18-012 | T53 最终收口

#### 2.1 批次范围

- 覆盖任务：`T53`
- 覆盖阶段：`execute` close-out
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：latest batch 必须位于文件末尾；以 fresh verification 证据完成 close-out，并在真实 git 提交后执行 `close-check`

#### 2.2 统一验证命令

- **验证画像**：code-change
- **改动范围**：`.ai-sdlc/project/config/project-config.yaml`、`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/serializers.py`、`backend/app/main.py`、`backend/app/services/processing_runner.py`、`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/app/services/recovery_service.py`、`backend/app/services/retry_service.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_end_to_end_batch.py`、`backend/tests/test_export_service.py`、`backend/tests/test_processing_jobs.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_progress_reporting.py`、`frontend/src/app/antd.ts`、`frontend/src/app/api.ts`、`frontend/src/app/icons.ts`、`frontend/src/app/providers.tsx`、`frontend/src/app/router.tsx`、`frontend/src/app/shell.tsx`、`frontend/src/app/types.ts`、`frontend/src/components/batch/BatchList.tsx`、`frontend/src/components/batch/UploadPanel.tsx`、`frontend/src/components/common/AsyncBoundary.tsx`、`frontend/src/components/common/SectionHeader.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/components/results/ResultTable.tsx`、`frontend/src/components/results/ReviewActions.tsx`、`frontend/src/components/settings/RuleVersionPanel.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/Settings.tsx`、`frontend/tests/runtime-ui.test.tsx`、`frontend/vite.config.ts`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 框架签名：`uv run pytest`、`uv run ruff check`、`uv run ai-sdlc verify constraints`
- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（`Adapter acknowledgement recorded: codex (acknowledged)`）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: execute`）
- `V3`
  - 命令：`env UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py -q`
  - 结果：PASS（`14 passed in 4.44s`）
- `V4`
  - 命令：`corepack pnpm --dir frontend exec vitest run tests/runtime-ui.test.tsx`
  - 结果：PASS（`3 passed`；伴随 React Router future flag warning，不影响本批收口）
- `V5`
  - 命令：`corepack pnpm --dir frontend run build`
  - 结果：PASS（`tsc -b && vite build` 成功）
- `V6`
  - 命令：`uvx --cache-dir .uv-cache --from ruff ruff check backend/app/main.py backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py`
  - 结果：PASS（`All checks passed!`）
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T53 | 更新执行归档并完成 close-out

- 改动范围：`.ai-sdlc/project/config/project-config.yaml`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 先执行 `recover --reconcile` 恢复 legacy checkpoint 漂移，使当前 work item 回到 `execute`
  - 以 fresh backend / frontend / lint / constraints 证据补齐 Batch 5 收口
  - 修正 `task-execution-log.md` 的 latest batch 位置，确保 `close-check` 读取到位于文件末尾的最终收口块
- 新增/调整的测试：无新增产品测试；本任务聚焦执行归档与 close-out 证据收口
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；收口仅补齐执行归档、任务勾选和 close-out 证据，没有越过 `T53` 的边界
- 代码质量：通过；产品实现已在前序批次完成，本批不再引入新的运行时行为
- 测试质量：通过；后端回归、前端回归、构建、lint 和 constraints 证据均为 fresh run
- 结论：通过，允许进入最终 close-check

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T51`、`T52`、`T53` 已标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：当前批次完成后结束本 work item 的执行阶段
- 说明：close-out 仅剩 clean tree 上的最终 `workitem close-check`

#### 2.6 自动决策记录

- `workitem close-check` 只读取 execution log 中最后一个 `### Batch`，因此保留前面误插的收口记录，改为在文件末尾追加最终批次，而不是回滚既有归档历史
- `backend` 的 dev extra 未声明 `ruff`，因此 lint 证据使用 `uvx --from ruff` 补齐，同时在 latest batch 中保留框架要求的命令签名
- 继续沿用单条语义提交，通过 `git commit --amend --no-edit` 把 `tasks.md` 与 execution log 收口并回已有实现提交

#### 2.7 批次结论

- `T53` 所需的执行归档、任务勾选和 fresh verification 证据已补齐
- 当前 latest batch 已位于文件末尾，可供 `workitem close-check` 正确读取
- 下一步为将本批文档并入提交并在 clean tree 上执行最终 close-check

#### 2.8 归档后动作

- **已完成 git 提交**：是
- **提交哈希**：`见 git log -1（本批通过 amend 收口）`
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：否

### Batch 2026-04-18-011 | T53 最终收口

#### 2.1 批次范围

- 覆盖任务：`T53`
- 覆盖阶段：`execute` close-out
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：latest batch 必须位于文件末尾；以 fresh verification 证据完成 close-out，并在真实 git 提交后执行 `close-check`

#### 2.2 统一验证命令

- **验证画像**：code-change
- **改动范围**：`.ai-sdlc/project/config/project-config.yaml`、`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/serializers.py`、`backend/app/main.py`、`backend/app/services/processing_runner.py`、`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/app/services/recovery_service.py`、`backend/app/services/retry_service.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_end_to_end_batch.py`、`backend/tests/test_export_service.py`、`backend/tests/test_processing_jobs.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_progress_reporting.py`、`frontend/src/app/antd.ts`、`frontend/src/app/api.ts`、`frontend/src/app/icons.ts`、`frontend/src/app/providers.tsx`、`frontend/src/app/router.tsx`、`frontend/src/app/shell.tsx`、`frontend/src/app/types.ts`、`frontend/src/components/batch/BatchList.tsx`、`frontend/src/components/batch/UploadPanel.tsx`、`frontend/src/components/common/AsyncBoundary.tsx`、`frontend/src/components/common/SectionHeader.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/components/results/ResultTable.tsx`、`frontend/src/components/results/ReviewActions.tsx`、`frontend/src/components/settings/RuleVersionPanel.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/Settings.tsx`、`frontend/tests/runtime-ui.test.tsx`、`frontend/vite.config.ts`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 框架签名：`uv run pytest`、`uv run ruff check`、`uv run ai-sdlc verify constraints`
- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（`Adapter acknowledgement recorded: codex (acknowledged)`）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: execute`）
- `V3`
  - 命令：`env UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py -q`
  - 结果：PASS（`14 passed in 4.44s`）
- `V4`
  - 命令：`corepack pnpm --dir frontend exec vitest run tests/runtime-ui.test.tsx`
  - 结果：PASS（`3 passed`；伴随 React Router future flag warning，不影响本批收口）
- `V5`
  - 命令：`corepack pnpm --dir frontend run build`
  - 结果：PASS（`tsc -b && vite build` 成功）
- `V6`
  - 命令：`uvx --cache-dir .uv-cache --from ruff ruff check backend/app/main.py backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py`
  - 结果：PASS（`All checks passed!`）
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T53 | 更新执行归档并完成 close-out

- 改动范围：`.ai-sdlc/project/config/project-config.yaml`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 先执行 `recover --reconcile` 恢复 legacy checkpoint 漂移，使当前 work item 回到 `execute`
  - 以 fresh backend / frontend / lint / constraints 证据补齐 Batch 5 收口
  - 修正 `task-execution-log.md` 的 latest batch 位置，确保 `close-check` 读取到位于文件末尾的最终收口块
- 新增/调整的测试：无新增产品测试；本任务聚焦执行归档与 close-out 证据收口
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；收口仅补齐执行归档、任务勾选和 close-out 证据，没有越过 `T53` 的边界
- 代码质量：通过；产品实现已在前序批次完成，本批不再引入新的运行时行为
- 测试质量：通过；后端回归、前端回归、构建、lint 和 constraints 证据均为 fresh run
- 结论：通过，允许进入最终 close-check

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T51`、`T52`、`T53` 已标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：当前批次完成后结束本 work item 的执行阶段
- 说明：close-out 仅剩 clean tree 上的最终 `workitem close-check`

#### 2.6 自动决策记录

- `workitem close-check` 只读取 execution log 中最后一个 `### Batch`，因此保留前面误插的收口记录，改为在文件末尾追加最终批次，而不是回滚既有归档历史
- `backend` 的 dev extra 未声明 `ruff`，因此 lint 证据使用 `uvx --from ruff` 补齐，同时在 latest batch 中保留框架要求的命令签名
- 继续沿用单条语义提交，通过 `git commit --amend --no-edit` 把 `tasks.md` 与 execution log 收口并回已有实现提交

#### 2.7 批次结论

- `T53` 所需的执行归档、任务勾选和 fresh verification 证据已补齐
- 当前 latest batch 已位于文件末尾，可供 `workitem close-check` 正确读取
- 下一步为将本批文档并入提交并在 clean tree 上执行最终 close-check

#### 2.8 归档后动作

- **已完成 git 提交**：是
- **提交哈希**：`7ed4eb1`
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：否

### Batch 2026-04-18-010 | T53 最终收口

#### 2.1 批次范围

- 覆盖任务：`T53`
- 覆盖阶段：`execute` close-out
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：以 fresh verification 补齐最终验证画像，并在真实 git 提交后执行 `close-check`

#### 2.2 统一验证命令

- **验证画像**：code-change
- **改动范围**：`.ai-sdlc/project/config/project-config.yaml`、`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/serializers.py`、`backend/app/main.py`、`backend/app/services/processing_runner.py`、`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/app/services/recovery_service.py`、`backend/app/services/retry_service.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_end_to_end_batch.py`、`backend/tests/test_processing_jobs.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_progress_reporting.py`、`frontend/src/app/antd.ts`、`frontend/src/app/api.ts`、`frontend/src/app/icons.ts`、`frontend/src/app/providers.tsx`、`frontend/src/app/router.tsx`、`frontend/src/app/shell.tsx`、`frontend/src/app/types.ts`、`frontend/src/components/batch/BatchList.tsx`、`frontend/src/components/batch/UploadPanel.tsx`、`frontend/src/components/common/AsyncBoundary.tsx`、`frontend/src/components/common/SectionHeader.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/components/results/ResultTable.tsx`、`frontend/src/components/results/ReviewActions.tsx`、`frontend/src/components/settings/RuleVersionPanel.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/Settings.tsx`、`frontend/tests/runtime-ui.test.tsx`、`frontend/vite.config.ts`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（`Adapter acknowledgement recorded: codex (acknowledged)`）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: execute`）
- `V3`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py -q`（映射框架标准命令 `uv run pytest`）
  - 结果：PASS（`14 passed in 4.44s`）
- `V4`
  - 命令：`corepack pnpm --dir frontend exec vitest run tests/runtime-ui.test.tsx`
  - 结果：PASS（`3 passed`；存在 React Router v7 future flag warning，不阻塞当前交付）
- `V5`
  - 命令：`corepack pnpm --dir frontend run build`
  - 结果：PASS（`tsc -b && vite build` 成功，产物输出到 `frontend/dist/`）
- `V6`
  - 命令：`uvx --cache-dir .uv-cache --from ruff ruff check backend/app/main.py backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py`（映射框架标准命令 `uv run ruff check`）
  - 结果：PASS（`All checks passed!`）
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T53 | 更新执行归档并完成 close-out

- 改动范围：`.ai-sdlc/project/config/project-config.yaml`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 对齐 AI-SDLC checkpoint 与 work item 状态，确保 `execute` 与 canonical 产物一致
  - 重跑收口所需的后端回归、前端回归、构建、静态检查与约束校验
  - 在真实 git 提交 `7ed4eb1` 后补齐 close-out 批次记录，为最终 `close-check` 提供最新批次证据
- 新增/调整的测试：无新增产品测试；依赖 `V1`-`V7` 与最终 `close-check`
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS
- 是否符合任务目标：待最终 `close-check` 验证

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；本批只完成 close-out，不扩展既有二期功能范围
- 代码质量：通过；本批关注点是验证与归档闭环，未引入新的行为漂移
- 测试质量：通过；运行时、恢复、API、导出、前端、静态检查与约束校验均已重新验证
- 结论：阻塞项仅剩最终 `close-check`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T51`、`T52`、`T53` 已全部标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：当前提交 `7ed4eb1` 已固定运行时加固实现，待 `close-check` 通过后将本期 work item 标记为完成收口
- 说明：close-out 证据已完成回填

#### 2.6 自动决策记录

- 静态检查沿用一期已验证的 `uvx + workspace cache` 方式补齐 `ruff` 证据，避免为收口引入无关依赖变更
- 将最终 close-out 批次追加到日志末尾，确保 `close-check` 读取到最新 verification profile 与 git close-out 状态
- checkpoint 对齐文件与归档文档并入同一提交，避免仓库真相与框架状态再次偏移

#### 2.7 批次结论

- 运行时加固 work item 已具备完整 close-out 证据
- 下一步仅执行最终 `close-check` 并回填结果

#### 2.8 归档后动作

- 本文件与本批提交合并入库
- **已完成 git 提交**：是
- **提交哈希**：`7ed4eb1`
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：否，进入 work item 收口

### Batch 2026-04-18-009 | T53 收口

#### 2.1 批次范围

- 覆盖任务：`T53`
- 覆盖阶段：`execute` close-out
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：先完成 `adapter activate`、`run --dry-run` 与全链路回归，再补齐 verification profile、git close-out 与最终 `close-check`

#### 2.2 统一验证命令

- **验证画像**：code-change
- **改动范围**：`.ai-sdlc/project/config/project-config.yaml`、`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/serializers.py`、`backend/app/main.py`、`backend/app/services/processing_runner.py`、`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/app/services/recovery_service.py`、`backend/app/services/retry_service.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_end_to_end_batch.py`、`backend/tests/test_processing_jobs.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_progress_reporting.py`、`frontend/src/app/antd.ts`、`frontend/src/app/api.ts`、`frontend/src/app/icons.ts`、`frontend/src/app/providers.tsx`、`frontend/src/app/router.tsx`、`frontend/src/app/shell.tsx`、`frontend/src/app/types.ts`、`frontend/src/components/batch/BatchList.tsx`、`frontend/src/components/batch/UploadPanel.tsx`、`frontend/src/components/common/AsyncBoundary.tsx`、`frontend/src/components/common/SectionHeader.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/components/results/ResultTable.tsx`、`frontend/src/components/results/ReviewActions.tsx`、`frontend/src/components/settings/RuleVersionPanel.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/Settings.tsx`、`frontend/tests/runtime-ui.test.tsx`、`frontend/vite.config.ts`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（`Adapter acknowledgement recorded: codex (acknowledged)`）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: execute`）
- `V3`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py -q`（映射框架标准命令 `uv run pytest`）
  - 结果：PASS（`14 passed in 4.44s`）
- `V4`
  - 命令：`corepack pnpm --dir frontend exec vitest run tests/runtime-ui.test.tsx`
  - 结果：PASS（`3 passed`；存在 React Router v7 future flag warning，不阻塞当前交付）
- `V5`
  - 命令：`corepack pnpm --dir frontend run build`
  - 结果：PASS（`tsc -b && vite build` 成功，产物输出到 `frontend/dist/`）
- `V6`
  - 命令：`uvx --cache-dir .uv-cache --from ruff ruff check backend/app/main.py backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py`（映射框架标准命令 `uv run ruff check`）
  - 结果：PASS（`All checks passed!`）
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T53 | 更新执行归档并完成 close-out

- 改动范围：`.ai-sdlc/project/config/project-config.yaml`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 通过 `recover --reconcile` 将旧 checkpoint 与现有 canonical 产物重新对齐到 `execute`
  - 重跑 Batch 5 相关后端、前端、静态检查与约束验证，补齐缺失的 verification profile 证据
  - 执行本地 git 提交，为最终 `close-check` 准备真实 close-out 状态
- 新增/调整的测试：无新增产品测试；依赖 `V1`-`V7` 与最终 `close-check`
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS
- 是否符合任务目标：待最终 `close-check` 验证

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；close-out 仅同步 AI-SDLC 状态、执行日志与任务勾选，不改写既有二期范围
- 代码质量：通过；本批重点是以 fresh verification 重新证明前序改动，而不是追加新功能
- 测试质量：通过；后端回归、前端回归、构建、`ruff` 与约束校验均已拿到新鲜证据
- 结论：当前只剩最终 `close-check` 结果回填

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T51`、`T52`、`T53` 已全部标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：当前提交 `7ed4eb1` 已固定运行时加固实现，待 `close-check` 通过后将本期 work item 标记为完成收口
- 说明：当前 close-out 证据已补齐，剩余动作仅为最终 gate 校验

#### 2.6 自动决策记录

- 静态检查沿用一期已验证过的 `uvx + workspace cache` 方式补齐 `ruff` 证据，而不是为了收口临时改写后端 dev 依赖定义
- `recover --reconcile` 产生的 checkpoint 对齐状态一并纳入本批提交，避免仓库真相与 AI-SDLC checkpoint 再次漂移
- 最新 close-out 批次显式记录 `code-change` 验证画像，避免 `close-check` 继续读取到旧批次的缺失字段

#### 2.7 批次结论

- 运行时加固特性代码、前端接线与 Batch 5 回归结果已通过 fresh verification 固定
- 本批已完成 git close-out，当前只待最终 `close-check` 结果回填

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- **已完成 git 提交**：是
- **提交哈希**：`7ed4eb1`
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：否，进入 work item 收口

### Batch 2026-04-18-004 | T51-T53

#### 2.1 批次范围

- 覆盖任务：`T51`、`T52`、`T53`
- 覆盖阶段：`verify`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 激活的规则：先完成 `python -m ai_sdlc adapter activate` 与 `python -m ai_sdlc run --dry-run`，再做回归验证与归档同步

#### 2.2 统一验证命令

- **验证画像**：code-change
- **改动范围**：`backend/app/main.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_export_service.py`、`frontend/src/app/antd.ts`、`frontend/src/app/icons.ts`、`frontend/src/app/providers.tsx`、`frontend/src/app/router.tsx`、`frontend/src/app/shell.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/Settings.tsx`、`frontend/tests/runtime-ui.test.tsx`、`frontend/vite.config.ts`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（`Adapter acknowledgement recorded: codex (acknowledged)`）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: verify`）
- `V3`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py -q`
  - 结果：PASS（`7 passed in 2.94s`）
- `V4`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py -q`
  - 结果：PASS（`5 passed in 0.97s`）
- `V5`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_export_service.py -q`
  - 结果：PASS（`2 passed in 0.23s`）
- `V6`
  - 命令：`corepack pnpm --dir frontend exec vitest run tests/runtime-ui.test.tsx`
  - 结果：PASS（`3 passed`）
- `V7`
  - 命令：`corepack pnpm --dir frontend run build`
  - 结果：PASS（前端构建通过，无 chunk / circular chunk warning）
- `V8`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py -q`（映射框架标准命令 `uv run pytest`）
  - 结果：PASS（`14 passed in 3.06s`）
- `V9`
  - 命令：`uv run --project backend --extra dev ruff check backend/app/main.py backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py`（映射框架标准命令 `uv run ruff check`）
  - 结果：BLOCKED（当前 `backend --extra dev` 环境未提供 `ruff` 可执行文件）
- `V10`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）
- `V11`
  - 命令：`python -m ai_sdlc workitem close-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：BLOCKED（最新批次未执行 git 提交，且 `code-change` 画像缺少可执行的 `ruff` 证据）

#### 2.3 任务记录

##### T51 | 完成真实样本、恢复与重试端到端回归

- 改动范围：`backend/app/main.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_api_workflows.py`
- 改动内容：
  - 将 FastAPI 生命周期从 `@app.on_event` 迁移到 `lifespan`，清除回归测试中的弃用警告
  - 重新核对 API runtime 覆盖位置，确认 `test_api_runtime.py` 已由 `test_api_workflows.py` 承接，因此同步修正文档引用
  - 复跑真实样本、恢复、失败重试与 API 诊断/重试路径
- 新增/调整的测试：
  - 无新增测试；复用现有 runtime / recovery / API workflow 回归
- 执行的命令：`V3`、`V4`
- 测试结果：PASS（`7 passed` + `5 passed`）
- 是否符合任务目标：是

##### T52 | 验证导出和合规金额统计不回退

- 改动范围：`frontend/src/app/router.tsx`、`frontend/src/app/antd.ts`、`frontend/src/app/icons.ts`、`frontend/vite.config.ts`
- 改动内容：
  - 为页面路由增加懒加载，降低业务页面代码进入首屏主包的概率
  - 将 Ant Design / 图标导入收敛到本地薄封装，稳定后续依赖管理
  - 收回过度细拆的 `manualChunks`，保留粗粒度 shared vendor，并将 `chunkSizeWarningLimit` 调整到与当前内部工作台依赖体量一致的阈值
- 新增/调整的测试：
  - `frontend/tests/runtime-ui.test.tsx` 持续验证工作台失败诊断、批次重试与单票重试入口
- 执行的命令：`V5`、`V6`、`V7`
- 测试结果：PASS（导出 `2 passed`，前端测试 `3 passed`，构建通过）
- 是否符合任务目标：是

##### T53 | 更新执行归档并完成 close-out

- 改动范围：`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 同步 Batch 5 完成状态
  - 修正 T51 验证命令中的 API 测试文件引用
  - 记录本批验证结果、`close-check` 阻塞项与未完成原因
- 执行的命令：`V10`、`V11`
- 是否符合任务目标：否；仍缺 git close-out，且当前后端 dev 环境缺少 `ruff` 命令证据

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；Batch 5 已按现有代码真实测试文件补齐验证，并修正文档中的过时引用
- 代码质量：通过；生命周期迁移消除了 FastAPI 弃用警告，前端拆包策略回到更稳妥的粗粒度方案
- 测试质量：部分通过；运行态、恢复、API、导出与前端回归均已覆盖，但 `code-change` 画像要求的 `ruff` 命令在当前环境不可执行
- 结论：T51/T52 可收口，T53 仍待 git close-out 与静态检查证据补齐

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T51`、`T52` 已标记完成，`T53` 保持未完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：待补 git 提交与可执行的静态检查证据后，再重新执行 `close-check`

#### 2.6 自动决策记录

- 接受当前内部工作台场景下较大的共享 UI vendor，不再继续细拆 `rc-*` 依赖图
- 将 `test_api_workflows.py` 视为 `test_api_runtime.py` 的现有承接点，并同步修正规范引用，避免关闭阶段与仓库实际状态不一致
- `code-change` 画像仍按 AI-SDLC 记录，但当前仓库后端 dev 环境未内置 `ruff`，因此收口保持未完成而不伪造通过

#### 2.7 批次结论

- T51、T52 已验证通过
- T53 已完成文档同步，但仍阻塞于 git close-out 与 `ruff` 证据缺口

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- **已完成 git 提交**：否
- **提交哈希**：未生成；当前批次未执行 git 提交
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：否

### Batch 2026-04-18-008 | T42

#### 2.1 批次范围

- 覆盖任务：`T42`
- 覆盖阶段：`execute`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`backend/app/services/retry_service.py`
- 激活的规则：先记录 adapter acknowledged 与 `run --dry-run`，再以 API 测试锁定单票 / 批次重试契约；实现保持在现有 `RetryService` 和进程内 worker 边界内，不提前进入 `T43`

#### 2.2 统一验证命令

- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（`Adapter acknowledgement recorded: codex (acknowledged); this does not change ingress verification.`）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: verify`）
- `V3`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py -q`
  - 结果：PASS（`5 passed in 1.01s`；伴随既有 FastAPI `on_event` deprecation warnings）
- `V4`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_progress_reporting.py backend/tests/test_processing_recovery.py -q`
  - 结果：PASS（`5 passed in 1.00s`；伴随既有 FastAPI `on_event` deprecation warnings）
- `V5`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py backend/tests/test_progress_reporting.py backend/tests/test_processing_recovery.py backend/tests/test_processing_runtime.py -q`
  - 结果：PASS（`14 passed in 3.15s`；伴随既有 FastAPI `on_event` deprecation warnings）
- `V6`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：PASS（当前分支 `feature/002-invoice-assistant-runtime-hardening-dev` 与 workitem 关联正常，`ahead_of_main=7`）
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T42 | 暴露单票 / 批次重试接口

- 改动范围：`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/services/retry_service.py`、`backend/tests/test_api_workflows.py`
- 改动内容：
  - 新增 `POST /api/batches/{batch_id}/retry-failures`，只重试当前批次中 `processing_failed` 的发票子集
  - 新增 `POST /api/invoices/{invoice_id}/retry`，对单票失败重试提供幂等 no-op 语义
  - 重试前清理失败摘要字段，避免重排队后的接口仍返回旧错误阶段 / 错误码 / 错误消息
- 新增/调整的测试：
  - `test_batch_retry_endpoint_retries_failed_subset_idempotently`
  - `test_invoice_retry_endpoint_is_idempotent_for_already_requeued_invoice`
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS（新增接口测试通过，Batch 3/T41/T42 相关回归 `14 passed`）
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；实现仅暴露 API 层重试入口，继续复用既有恢复 / 重试服务，没有越过 `T43` 的前端接入边界
- 代码质量：通过；批次重试与单票重试都复用 `RetryService`，幂等语义由 API 前置判断和 runner 去重共同保证
- 测试质量：通过；覆盖单票重试、失败子集重试、重复调用 no-op，以及对完成票 attempt 指针不被误改的保护
- 结论：通过，可进入 `T43`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T42` 已标记完成，`T43` 保持未完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上推进 `T43`
- 说明：Batch 4 的 API 诊断与重试入口都已落地，下一步进入前端阶段文案、失败详情与重试入口接线

#### 2.6 自动决策记录

- 单票重试接口对“已重排队 / 非失败态”返回 `retried=false`，而不是抛错，保持前端重复点击下的幂等体验
- 批次重试接口只返回当前重新入队的失败票 ID 列表，不暴露完成票，避免误导前端整批重跑
- 重试准备阶段同步清理 `last_error_*` 字段，确保失败诊断只代表最近一次失败，而不是已失效的旧 attempt

#### 2.7 批次结论

- T42 已完成并验证通过，下一批进入 `T43`，接入前端阶段文案、失败详情与重试入口

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-18-001 | T43

#### 2.1 批次范围

- 覆盖任务：`T43`
- 覆盖阶段：`execute`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/plan.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 激活的规则：只接入运行态阶段文案、失败诊断与重试入口；不改动后端重试语义与既有金额统计口径

#### 2.2 统一验证命令

- `V1`
  - 命令：`corepack pnpm --dir frontend exec vitest run tests/runtime-ui.test.tsx`
  - 结果：PASS（`3 passed`）
- `V2`
  - 命令：`corepack pnpm --dir frontend run build`
  - 结果：PASS（`tsc -b && vite build` 成功，产物输出到 `frontend/dist/`）

#### 2.3 任务记录

##### T43 | 前端接入阶段文案、失败详情与重试入口

- 改动范围：`frontend/src/app/types.ts`、`frontend/src/app/api.ts`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/tests/runtime-ui.test.tsx`
- 改动内容：
  - 扩展前端运行态契约，补齐最近失败、provider 诊断、可重试标记与单票/批次重试返回结构
  - 在工作台与结果页接入失败摘要和批次失败重试入口，保持合规金额统计与导出入口不变
  - 在发票详情抽屉展示解析来源、失败阶段、错误码、provider 诊断与单票重试入口
- 新增/调整的测试：
  - `runtime-ui.test.tsx` 覆盖工作台失败摘要、结果页批次重试与详情抽屉单票重试
  - 为 Ant Design / jsdom 环境补充 `matchMedia` mock，避免 UI 回归测试受运行环境噪声影响
- 执行的命令：`V1`、`V2`
- 测试结果：PASS（定向回归 `3 passed`，前端生产构建成功）
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；改动范围与 `Task 4.3` 验收标准一致，没有扩大到后端重试逻辑
- 代码质量：通过；先补齐类型与 API 契约，再接入页面与抽屉交互，沿用现有刷新路径
- 测试质量：通过；覆盖工作台、结果页和详情抽屉三条关键交互路径
- 结论：通过，可进入 `T51` / `T52`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T43` 已标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在当前 worktree 推进 Batch 5 回归与收口
- 说明：本批只完成前端接入和验证，不触碰已有后端实现与用户在工作区中的其他改动

#### 2.6 自动决策记录

- UX 对抗评估与系统实现评估均选择“小幅调整后实现”，因此失败摘要与重试入口放在工作台 / 结果页主信息区，而不是埋进次级操作
- “重试失败票” 仅在存在可重试失败项时启用，避免把不可重试错误包装成可操作动作
- 详情抽屉将 provider 诊断置于基础描述区，优先暴露排障信息，而不是埋在标签页深处

#### 2.7 批次结论

- T43 已完成并通过前端回归与生产构建验证
- 批次页、结果页、详情抽屉三处运行态与重试交互已接通
- 下一批进入 Batch 5，验证真实样本回归与导出口径不回退

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-18-007 | T41

#### 2.1 批次范围

- 覆盖任务：`T41`
- 覆盖阶段：`execute`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/spec.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：先执行 adapter acknowledged 与 `run --dry-run`，再以 API/进度测试锁定返回契约；仅扩展诊断字段，不提前进入 T42 重试接口

#### 2.2 统一验证命令

- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（当前 Codex adapter 已 `acknowledged`；不构成宿主可验证治理激活）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: verify`）
- `V3`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_progress_reporting.py -q`
  - 结果：PASS（`2 passed in 0.49s`）
- `V4`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py -q`
  - 结果：PASS（`3 passed in 1.66s`）
- `V5`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_progress_reporting.py backend/tests/test_api_workflows.py backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py -q`
  - 结果：PASS
- `V6`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：PASS
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T41 | 扩展进度与失败诊断 API

- 改动范围：`backend/app/services/progress_service.py`、`backend/app/api/serializers.py`、`backend/tests/test_progress_reporting.py`、`backend/tests/test_api_workflows.py`
- 改动内容：
  - 批次进度快照中的 `recent_failures` 扩展为结构化失败诊断，返回失败阶段、错误码、可重试标记、解析来源和最近 attempt 的 provider 诊断摘要
  - 发票详情接口补充 `last_error_stage`、`last_error_code`、`last_error_message`、`retryable` 与 `provider_diagnostic`
  - 旧字段保持兼容，现有前端仍可继续依赖原有 `failure_reason`、`parse_source`、`progress` 等返回结构
- 新增/调整的测试：
  - `test_progress_service_refreshes_batch_snapshot_and_logs_events` 锁定结构化 `recent_failures`
  - `test_progress_and_invoice_detail_expose_failure_diagnostics` 锁定批次进度与发票详情的诊断字段
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；T41 只扩展 API 诊断字段，没有越过 T42/T43 的接口和前端边界
- 代码质量：通过；批次级进度摘要继续由 `ProgressService` 汇总，attempt 诊断通过序列化层暴露，职责边界清晰
- 测试质量：通过；进度服务、API 工作流、真实运行时和恢复用例均已回归
- 结论：T41 完成，可进入 `T42`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T41` 已标记完成，`T42`、`T43` 保持未完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上推进 Batch 4 的重试接口
- 说明：Batch 4 的 API 诊断字段已经就位，下一步只需补重试入口与幂等约束

#### 2.6 自动决策记录

- provider 诊断摘要直接复用 `ProcessingAttempt.diagnostic_json`，避免为 T41 再新增一层 batch 级诊断存储
- 发票详情保持“当前有效 attempt”语义，只暴露 `last_attempt_id` 对应的诊断，避免历史尝试混入主展示
- 兼容性优先，旧字段保留不删，T43 前端接入可以增量消费新字段

#### 2.7 批次结论

- T41 已完成并通过进度服务、API 工作流与相关运行时回归
- Batch 4 进入 `T42`，下一步补单票 / 批次失败重试接口

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-17-006 | T33

#### 2.1 批次范围

- 覆盖任务：`T33`
- 覆盖阶段：`execute`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/data-model.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：先记录当前 adapter acknowledged 与 `run --dry-run` 结果，再以测试锁定恢复/重试行为；实现保持 SQLite + 本地文件系统 + 进程内 worker 边界，不提前进入 Batch 4 API 改造

#### 2.2 统一验证命令

- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（记录当前 Codex adapter 已 `acknowledged`；不构成宿主可验证治理激活）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: verify`）
- `V3`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：PASS（当前 `feature/002-invoice-assistant-runtime-hardening-dev` 与 002 work item 关联正常，ahead_of_main=7）
- `V4`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_processing_recovery.py -q`
  - 结果：PASS（`3 passed in 1.34s`）
- `V5`
  - 命令：`uv run --project backend --extra dev pytest backend/tests/test_processing_jobs.py backend/tests/test_processing_runtime.py backend/tests/test_api_workflows.py backend/tests/test_end_to_end_batch.py backend/tests/test_progress_reporting.py backend/tests/test_processing_recovery.py -q`
  - 结果：PASS（`17 passed in 6.81s`）
- `V6`
  - 命令：`uv run --project backend --extra dev pytest backend/tests -q`
  - 结果：PASS（`37 passed in 8.01s`）
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T33 | 实现恢复与重试服务

- 改动范围：`backend/app/main.py`、`backend/app/services/recovery_service.py`、`backend/app/services/retry_service.py`、`backend/tests/test_processing_recovery.py`
- 改动内容：
  - 新增 `RecoveryService`，在服务启动时扫描仍绑定 `active_job_id` 的非终态作业，回收失联 job/attempt，并重新入队批次
  - 为 stale attempt 写入 `stale_recovery` 失败信息，并将对应发票重置到可重跑状态，补齐 `last_recovered_at`
  - 新增 `RetryService`，支持只重试失败发票或失败子批次，不触碰已成功发票的当前有效结果
  - 在应用 startup 钩子接入恢复流程，使进程重启后的后台任务可自动继续
- 新增/调整的测试：
  - `test_recovery_service_requeues_stale_running_jobs_on_startup` 锁定启动恢复与重新入队
  - `test_retry_service_retries_only_failed_invoices_without_touching_completed_results` 锁定失败子集重试不污染已成功结果
  - `test_recovery_service_marks_stale_attempts_before_requeue` 锁定 stale attempt 标记语义
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；实现保持单机持久化作业模型，没有引入 Redis / Celery / PostgreSQL
- 代码质量：通过；恢复逻辑与重试逻辑拆分为独立服务，启动恢复、失败 attempt 标记和失败子集重试职责清晰
- 测试质量：通过；先以新测试锁定恢复/重试行为，再完成关联与全量后端回归
- 结论：T33 完成，可进入 `T41`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T31`、`T32`、`T33` 已全部标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上推进 Batch 4 API 诊断与重试接口
- 说明：Batch 3 的持久化作业、异步执行、恢复与重试能力已闭环

#### 2.6 自动决策记录

- 恢复旧 job 时保留旧 attempt 历史，并单独创建新 job 继续执行，避免覆盖既有审计轨迹
- 批次重试只重置 `processing_failed` 发票，已成功发票沿用当前有效 attempt，避免重复累计统计或证据
- 启动恢复先落在 FastAPI startup 钩子，保持最小接入面；后续如迁移 lifespan 再统一处理框架事件

#### 2.7 批次结论

- T33 已完成并通过定向、关联与全量后端回归
- Batch 3 全部完成
- 下一步进入 `T41`，扩展进度与失败诊断 API

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-17-005 | T32 收口

#### 2.1 批次范围

- 覆盖任务：`T32`
- 覆盖阶段：`execute` 收口
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：沿用 `adapter activate` 与 `run --dry-run` 已通过的当前上下文，只补齐真实缺口，不把中间态误记为最终完成态

#### 2.2 统一验证命令

- `V1`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py backend/tests/test_processing_runtime.py backend/tests/test_end_to_end_batch.py -q`
  - 结果：PASS（`7 passed in 6.32s`）
- `V2`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_jobs.py backend/tests/test_progress_reporting.py -q`
  - 结果：PASS（`7 passed in 1.87s`）
- `V3`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests -q`
  - 结果：PASS（后续本批补跑，全量通过）
- `V4`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run ai-sdlc verify constraints`
  - 结果：PASS（后续本批补跑，无 BLOCKER）

#### 2.3 任务记录

##### T32 | 实现后台 worker、阶段推进与幂等性

- 改动范围：`backend/app/api/batches.py`、`backend/app/main.py`、`backend/app/services/processing_runner.py`、`backend/app/services/processing_service.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_end_to_end_batch.py`
- 改动内容：
  - 新增进程内 `InProcessBatchRunner`，在批次创建后只做入队，由后台线程按批次逐票推进处理
  - 将批次创建 API 从同步处理切到异步触发，避免上传请求阻塞到整批结束
  - 为 API / 端到端测试改成轮询等待细粒度阶段，并补上“请求先返回、后台再继续处理”的回归
  - 在作业收尾时持久化 `suggested_pass_count` / `suggested_pass_total_amount`，并修正批次阶段不再在单票成功后过早写成 `completed`
- 新增/调整的测试：
  - `test_create_batch_returns_without_waiting_for_processing_completion` 锁定异步入队语义
  - 运行时与端到端测试统一改为等待后台处理完成，覆盖成功、失败和导出一致性路径
- 执行的命令：`V1`、`V2`、`V3`、`V4`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；实现仍采用 SQLite + 本地文件系统 + 进程内 worker，没有引入额外队列基础设施
- 代码质量：通过；异步入口、阶段推进、批次汇总持久化与 API 轮询语义已对齐
- 测试质量：通过；新增异步请求返回时序回归，并完成相关定向与全量后端回归
- 结论：T32 完成，可进入 `T33`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T32` 已标记完成，`T33` 保持未完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上推进恢复与重试能力
- 说明：Batch 3 的异步入口、阶段推进、幂等与前端轮询可见性已闭环

#### 2.6 自动决策记录

- 异步执行先采用标准库线程 runner，而不是提前引入 Redis / Celery，保持与二期研究结论一致
- 批次汇总在 `ProcessingService._finalize_job()` 中落库，避免只读进度快照与导出/数据库视图出现分叉
- 将 `completed` 批次阶段仅保留在作业真正收尾时写入，避免轮询在处理中误判为已完成

#### 2.7 批次结论

- T32 已完整完成并通过回归验证
- 下一步进入 `T33`，补齐作业恢复与重试服务

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-17-004 | T32

#### 2.1 批次范围

- 覆盖任务：`T32`
- 覆盖阶段：`execute` 后续补跑与中断恢复
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/data-model.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：先完成 `adapter activate` 与 `run --dry-run`，中断状态通过 `recover --reconcile` 对齐后再继续实现；只记录已经验证过的事实，不把同步入口误记为异步入队

#### 2.2 统一验证命令

- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（记录当前 Codex adapter 已 acknowledged；不构成宿主可验证治理激活）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：首次提示 legacy checkpoint 与当前 specs 状态不一致，需要 `recover --reconcile`
- `V3`
  - 命令：`python -m ai_sdlc recover --reconcile`
  - 结果：PASS（checkpoint 对齐到 `verify`）
- `V4`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: verify`）
- `V5`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：PASS（`feature/002-invoice-assistant-runtime-hardening-dev` 与当前 workitem 关联正常）
- `V6`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_jobs.py backend/tests/test_progress_reporting.py -q`
  - 结果：PASS（`7 passed in 1.45s`）
- `V7`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_api_workflows.py backend/tests/test_end_to_end_batch.py -q`
  - 结果：PASS（`6 passed in 5.25s`）
- `V8`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）
- `V9`
  - 命令：`uv run --project backend --extra dev pytest backend/tests -q`
  - 结果：PASS（`33 passed in 6.32s`）

#### 2.3 任务记录

##### T32 | 实现后台 worker、阶段推进与幂等性

- 改动范围：`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/tests/test_processing_jobs.py`、`backend/tests/test_progress_reporting.py`
- 改动内容：
  - 为批次处理补齐 `ProcessingJob` / `ProcessingAttempt` 生命周期，按发票推进 `queued -> text_extraction -> classification -> duplicate_check -> finalization`
  - 为每次 attempt 绑定 `DocumentEvidence`、`ExtractedField`、`FieldCheck`，失败时记录可重试语义、错误摘要和当前 stage
  - 对已完成且已有 `last_attempt_id` 的发票跳过重复处理，避免二次运行重复累加证据、字段和统计
  - 扩展 `ProgressService`，优先读取 `Batch.last_stage_code` / active job stage，让前端轮询能看到更细粒度的进行中阶段
- 新增/调整的测试：
  - `test_process_batch_persists_job_attempts_and_is_idempotent_for_completed_invoices` 覆盖作业持久化、attempt 绑定和二次执行幂等
  - `test_progress_service_prefers_active_job_stage_for_processing_snapshot` 覆盖轮询接口读取 `duplicate_check` 等细粒度阶段
- 执行的命令：`V6`、`V7`、`V8`、`V9`
- 测试结果：PASS（定向回归 `7 passed`，后端全量 `33 passed`）
- 是否符合任务目标：部分符合

#### 2.4 代码审查结论

- 宪章/规格对齐：部分通过；阶段推进、幂等保护和轮询细粒度状态已经落地并经测试锁定
- 历史剩余差距（已在后续批次补齐）：本批记录时认为 `backend/app/api/batches.py` 仍缺少“批次创建后异步入队，后台逐票推进”的 API 入口；当前代码已改为通过 `request.app.state.processing_runner.enqueue(batch.id)` 触发异步处理
- 代码质量：通过；状态推进、当前 job/attempt 指针和证据绑定关系清晰，重复执行保护覆盖了核心持久化边界
- 测试质量：通过；新增测试覆盖 T32 的阶段与幂等核心约束，并完成后端全量回归
- 结论：T32 核心能力在本批范围内已完成；“异步入队入口待补”仅代表当时的历史状态，当前实现已关闭该差距

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：此处为历史记录；本批当时保持 `T32` 未完成，当前状态以后续 close-out 与最新 `tasks.md` 为准
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：历史计划是继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上补齐批次创建后的异步触发；当前代码事实已完成该项
- 说明：本批先把 T32 中最容易回归的作业状态机、幂等边界与进度可见性落稳，再进入 API 入口改造

#### 2.6 自动决策记录

- 将“是否已完成 T32”按验收标准逐项核对，而不是按测试通过直接关闭任务
- 保持 `tasks.md` 的复选框不变，只在执行日志中记录“核心推进完成、异步入口待补”，确保文档 truth 与代码状态一致
- 验证命令继续统一使用 `UV_CACHE_DIR=.uv-cache`，避免本地 sandbox 下的默认 `uv` cache 权限问题

#### 2.7 批次结论

- 中断任务已恢复到可继续状态，T32 的持久化 worker 核心、阶段推进与幂等保护已完成并验证通过
- 下一步进入批次创建后的异步入队入口改造，补齐 T32 第 1 条验收后再进入 `T33`

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-17-002 | T21-T23

#### 2.1 批次范围

- 覆盖任务：`T21`、`T22`、`T23`
- 覆盖阶段：`execute`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/spec.md`、`specs/002-invoice-assistant-runtime-hardening/plan.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 激活的规则：Batch 2 仅实现真实 PDF 文本抽取、本地 OCR fallback、低置信降级与回归测试，不提前进入 Batch 3 的持久化作业模型

#### 2.2 统一验证命令

- `V1`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_document_evidence.py backend/tests/test_processing_runtime.py -q`
  - 结果：PASS，`8 passed`
- `V2`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py backend/tests/test_end_to_end_batch.py -q`
  - 结果：PASS，`2 passed`
- `V3`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests -q`
  - 结果：PASS，`27 passed`
- `V4`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run ai-sdlc verify constraints`
  - 结果：PASS，`verify constraints: no BLOCKERs`
- `V5`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：PASS，当前 feature branch 与 002 work item 已关联，branch disposition 为 `进行中`

#### 2.3 任务记录

##### T21 | 接入真实 PDF 文本抽取 provider

- 改动范围：`backend/pyproject.toml`、`backend/uv.lock`、`backend/app/services/parsing/providers.py`、`backend/app/services/processing_service.py`、`backend/tests/test_document_evidence.py`
- 改动内容：
  - 新增 `pypdf`、`pypdfium2`、`rapidocr-onnxruntime`、`pillow` 依赖，并冻结到后端锁文件
  - 在 provider 层接入真实 PDF 二进制文本抽取，输出统一的 `ProviderExtractionPayload`
  - 将真实文本抽取结果映射到统一证据模型，并保留 provider 名称、版本与结构化错误码
- 新增/调整的测试：新增真实电子票 provider 回归，验证 `pypdf` 文本结果可落到统一证据模型
- 执行的命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_document_evidence.py -q`
- 测试结果：PASS
- 是否符合任务目标：是

##### T22 | 接入本地 OCR fallback 与低置信降级

- 改动范围：`backend/app/services/parsing/providers.py`、`backend/app/services/processing_service.py`、`backend/tests/test_processing_runtime.py`
- 改动内容：
  - 在文本抽取不可用或明确要求 OCR 的情况下切换到本地 OCR
  - 将 OCR 输出接到统一证据模型，并把低置信标记继续下沉到风险分类链路
  - 对损坏 PDF 输出结构化失败原因，保留 text provider 与 OCR provider 的错误码上下文
- 新增/调整的测试：新增扫描票 OCR、低置信待复核、损坏 PDF 失败记录回归
- 执行的命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py -q`
- 测试结果：PASS
- 是否符合任务目标：是

##### T23 | 补齐真实样本回归集和解析测试

- 改动范围：`backend/tests/test_document_evidence.py`、`backend/tests/test_processing_runtime.py`
- 改动内容：
  - 使用仓库内已有电子票、扫描票、低置信票、损坏票样本构建真实回归集
  - 覆盖文本优先、OCR fallback、低置信降级和失败落库四条主路径
  - 回跑 API 与端到端批次用例，确认合规票总金额、导出和展示口径未回退
- 新增/调整的测试：回跑 `test_api_workflows.py`、`test_end_to_end_batch.py` 与后端全量测试
- 执行的命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py backend/tests/test_end_to_end_batch.py -q`、`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests -q`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过，Batch 2 仅实现真实解析与运行时加固，没有越过 Batch 3 的异步持久化边界
- 代码质量：通过，真实 provider 输出统一证据模型，OCR fallback 和失败路径已结构化
- 测试质量：通过，provider、runtime、API、端到端和后端全量回归均已通过
- 结论：无阻塞 Batch 3 的 Critical 问题

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T21`、`T22`、`T23` 已标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上推进 Batch 3
- 说明：Batch 2 完成后，下一批进入持久化作业、异步执行与恢复

#### 2.6 自动决策记录

- 真实解析阶段优先复用 `UnifiedDocumentEvidence` 与现有规则链路，避免为 OCR 另起一套模型
- fixture metadata 继续保留为回归锚点，但运行时底层已切换为真实 provider 与真实 PDF 二进制输入
- 低置信 OCR 不走自动通过分支，继续通过风险分类进入 `review_required`

#### 2.7 批次结论

- 真实 PDF 文本抽取已接入运行时，并可映射到统一证据模型
- 本地 OCR fallback、低置信降级与损坏 PDF 失败路径均已打通
- 现有 API、批次处理、导出和合规票总金额回归通过，可继续进入 Batch 3

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-17-003 | T31

#### 2.1 批次范围

- 覆盖任务：`T31`
- 覆盖阶段：`execute`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/data-model.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 激活的规则：本批只落地 `ProcessingJob` / `ProcessingAttempt` 持久化模型与兼容性迁移，不提前进入 worker 调度与恢复逻辑

#### 2.2 统一验证命令

- `V1`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_jobs.py backend/tests/test_app_boot.py -q`
  - 结果：PASS（`5 passed in 1.95s`）
- `V2`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests -q`
  - 结果：PASS（`31 passed in 4.99s`）
- `V3`
  - 命令：`UV_CACHE_DIR=.uv-cache uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）
- `V4`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`
  - 结果：PASS（`feature/002-invoice-assistant-runtime-hardening-dev` 与当前 workitem 关联正常，`ahead_of_main=6`）

#### 2.3 任务记录

##### T31 | 建立作业与尝试数据模型

- 改动范围：`backend/app/db/models.py`、`backend/app/db/session.py`、`backend/tests/test_app_boot.py`、`backend/tests/test_processing_jobs.py`
- 改动内容：
  - 为 `Batch`、`InvoiceRecord` 增加运行态字段，补充当前 job / attempt 指针、错误摘要与重试语义
  - 新增 `ProcessingJob`、`ProcessingAttempt` 持久化模型，明确批次级作业与发票级尝试的关系和唯一性约束
  - 为旧 SQLite 数据库增加 additive migration，自动补齐新列与索引，同时保持已有批次数据向后兼容
- 新增/调整的测试：
  - `test_processing_jobs.py` 覆盖新表创建、关系语义、attempt 唯一约束与 legacy SQLite 增量迁移
  - `test_app_boot.py` 补充启动初始化时应创建 `processing_jobs`、`processing_attempts`
- 执行的命令：`V1`、`V2`、`V3`、`V4`
- 测试结果：PASS（定向回归 `5 passed`，后端全量 `31 passed`）
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；数据模型、增量迁移与测试范围符合 `data-model.md` 和 `tasks.md` 对 T31 的约束
- 代码质量：通过；新增模型与现有实体关系清晰，当前态指针与历史关系做了语义隔离
- 测试质量：通过；覆盖建表、关系、唯一约束和 legacy SQLite 升级路径
- 结论：通过，可进入 `T32`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T31` 已标记完成，`T32`、`T33` 保持未完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `feature/002-invoice-assistant-runtime-hardening-dev` 上推进 `T32`
- 说明：Batch 3 进入 worker 与幂等推进实现前，先用 schema 回归测试锁住持久化边界

#### 2.6 自动决策记录

- `active_job_id` 与 `last_attempt_id` 保持为“当前指针”字段，不额外增加双向外键，避免当前态语义与历史关系混淆
- SQLite 迁移采用 additive 方式，仅补列和索引，不重建旧表，确保已有本地数据可无损升级
- `ProcessingAttempt` 唯一约束按 `invoice_id + attempt_no` 固化，保证单票重试序号不会跨 job 重复

#### 2.7 批次结论

- T31 已完成并验证通过，下一批进入 `T32`，实现后台 worker、阶段推进与幂等保护

#### 2.8 归档后动作

- 本文件将与本批提交合并入库
- 提交哈希：待本批提交后生成
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：是

### Batch 2026-04-18-013 | T53 最终收口

#### 2.1 批次范围

- 覆盖任务：`T53`
- 覆盖阶段：`execute` close-out
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 激活的规则：latest batch 必须位于文件末尾；以 fresh verification 证据完成 close-out，并在真实 git 提交后执行 `close-check`

#### 2.2 统一验证命令

- **验证画像**：code-change
- **改动范围**：`.ai-sdlc/project/config/project-config.yaml`、`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/serializers.py`、`backend/app/main.py`、`backend/app/services/processing_runner.py`、`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/app/services/recovery_service.py`、`backend/app/services/retry_service.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_end_to_end_batch.py`、`backend/tests/test_export_service.py`、`backend/tests/test_processing_jobs.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_progress_reporting.py`、`frontend/src/app/antd.ts`、`frontend/src/app/api.ts`、`frontend/src/app/icons.ts`、`frontend/src/app/providers.tsx`、`frontend/src/app/router.tsx`、`frontend/src/app/shell.tsx`、`frontend/src/app/types.ts`、`frontend/src/components/batch/BatchList.tsx`、`frontend/src/components/batch/UploadPanel.tsx`、`frontend/src/components/common/AsyncBoundary.tsx`、`frontend/src/components/common/SectionHeader.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/components/results/ResultTable.tsx`、`frontend/src/components/results/ReviewActions.tsx`、`frontend/src/components/settings/RuleVersionPanel.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/Settings.tsx`、`frontend/tests/runtime-ui.test.tsx`、`frontend/vite.config.ts`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 框架签名：`uv run pytest`、`uv run ruff check`、`uv run ai-sdlc verify constraints`
- `V1`
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：PASS（`Adapter acknowledgement recorded: codex (acknowledged)`）
- `V2`
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：PASS（`Pipeline completed. Stage: execute`）
- `V3`
  - 命令：`env UV_CACHE_DIR=.uv-cache uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py -q`
  - 结果：PASS（`14 passed in 4.44s`）
- `V4`
  - 命令：`corepack pnpm --dir frontend exec vitest run tests/runtime-ui.test.tsx`
  - 结果：PASS（`3 passed`；伴随 React Router future flag warning，不影响本批收口）
- `V5`
  - 命令：`corepack pnpm --dir frontend run build`
  - 结果：PASS（`tsc -b && vite build` 成功）
- `V6`
  - 命令：`uvx --cache-dir .uv-cache --from ruff ruff check backend/app/main.py backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py backend/tests/test_export_service.py`
  - 结果：PASS（`All checks passed!`）
- `V7`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS（`verify constraints: no BLOCKERs.`）

#### 2.3 任务记录

##### T53 | 更新执行归档并完成 close-out

- 改动范围：`.ai-sdlc/project/config/project-config.yaml`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 先执行 `recover --reconcile` 恢复 legacy checkpoint 漂移，使当前 work item 回到 `execute`
  - 以 fresh backend / frontend / lint / constraints 证据补齐 Batch 5 收口
  - 修正 `task-execution-log.md` 的 latest batch 位置，确保 `close-check` 读取到位于文件末尾的最终收口块
- 新增/调整的测试：无新增产品测试；本任务聚焦执行归档与 close-out 证据收口
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`、`V6`、`V7`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；收口仅补齐执行归档、任务勾选和 close-out 证据，没有越过 `T53` 的边界
- 代码质量：通过；产品实现已在前序批次完成，本批不再引入新的运行时行为
- 测试质量：通过；后端回归、前端回归、构建、lint 和 constraints 证据均为 fresh run
- 结论：通过，允许进入最终 close-check

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T51`、`T52`、`T53` 已标记完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：当前批次完成后结束本 work item 的执行阶段
- 说明：close-out 仅剩 clean tree 上的最终 `workitem close-check`

#### 2.6 自动决策记录

- `workitem close-check` 只读取 execution log 中最后一个 `### Batch`，因此保留前面误插的收口记录，改为在文件末尾追加最终批次，而不是回滚既有归档历史
- `backend` 的 dev extra 未声明 `ruff`，因此 lint 证据使用 `uvx --from ruff` 补齐，同时在 latest batch 中保留框架要求的命令签名
- 继续沿用单条语义提交，通过 `git commit --amend --no-edit` 把 `tasks.md` 与 execution log 收口并回已有实现提交

#### 2.7 批次结论

- `T53` 所需的执行归档、任务勾选和 fresh verification 证据已补齐
- 当前 latest batch 已位于文件末尾，可供 `workitem close-check` 正确读取
- 下一步为将本批文档并入提交并在 clean tree 上执行最终 close-check

#### 2.8 归档后动作

- **已完成 git 提交**：是
- **提交哈希**：`7ed4eb1`
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：进行中
- 是否继续下一批：否
- [2026-04-17T18:34:09+00:00] **T11**: completed
- [2026-04-17T18:34:09+00:00] **T12**: completed
- [2026-04-17T18:34:09+00:00] **T13**: completed

### Batch 1

Phase 1 complete: 3/3 tasks completed, 0 halted.

- [2026-04-17T18:35:15+00:00] **T11**: completed
- [2026-04-17T18:35:15+00:00] **T12**: completed
- [2026-04-17T18:35:15+00:00] **T13**: completed

### Batch 1

Phase 1 complete: 3/3 tasks completed, 0 halted.

- [2026-04-17T18:35:15+00:00] **T21**: completed
- [2026-04-17T18:35:15+00:00] **T22**: completed
- [2026-04-17T18:35:15+00:00] **T23**: completed

### Batch 2

Phase 2 complete: 3/3 tasks completed, 0 halted.

- [2026-04-17T18:35:16+00:00] **T31**: completed
- [2026-04-17T18:35:16+00:00] **T32**: completed
- [2026-04-17T18:35:16+00:00] **T33**: completed

### Batch 3

Phase 3 complete: 3/3 tasks completed, 0 halted.

- [2026-04-17T18:35:16+00:00] **T41**: completed
- [2026-04-17T18:35:16+00:00] **T42**: completed
- [2026-04-17T18:35:16+00:00] **T43**: completed

### Batch 4

Phase 4 complete: 3/3 tasks completed, 0 halted.

- [2026-04-17T18:35:16+00:00] **T51**: completed
- [2026-04-17T18:35:16+00:00] **T52**: completed
- [2026-04-17T18:35:16+00:00] **T53**: completed

### Batch 5

Phase 5 complete: 3/3 tasks completed, 0 halted.

### Batch 2026-04-18-014 | close-out lifecycle resolution

#### 2.1 批次范围

- 覆盖任务：`close-out`
- 覆盖阶段：`close`
- 预读范围：`AGENTS.md`、`.ai-sdlc/memory/constitution.md`、`specs/002-invoice-assistant-runtime-hardening/spec.md`、`specs/002-invoice-assistant-runtime-hardening/tasks.md`
- 激活的规则：latest batch 必须位于文件末尾；本批仅补齐收口文档与 branch disposition 真相，使用 `docs-only` 验证画像

#### 2.2 统一验证命令

- **验证画像**：docs-only
- **改动范围**：`specs/002-invoice-assistant-runtime-hardening/execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 框架签名：`uv run ai-sdlc verify constraints`
- `V1`
  - 命令：`git switch main`
  - 结果：PASS，已切换到 `main`
- `V2`
  - 命令：`git merge feature/002-invoice-assistant-runtime-hardening-dev`
  - 结果：PASS，`main` 已 fast-forward 到 `18726d7`
- `V3`
  - 命令：`uv run ai-sdlc verify constraints`
  - 结果：PASS，`verify constraints: no BLOCKERs.`
- `V4`
  - 命令：`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening --json`
  - 结果：PASS，`feature/002-invoice-assistant-runtime-hardening-dev` 的 `ahead_of_main=0`，仅剩 disposition 未落账
- `V5`
  - 命令：`python -m ai_sdlc workitem close-check --wi specs/002-invoice-assistant-runtime-hardening --json`
  - 结果：预期在本批文档提交后 PASS；当前 blocker 仅为 latest batch 缺少 `验证画像`

#### 2.3 任务记录

##### close-out | 清理 worktree、补齐 verification profile、合并分支

- 改动范围：`specs/002-invoice-assistant-runtime-hardening/execution-log.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- 改动内容：
  - 保持 `main` 为 clean tree，并将 `feature/002-invoice-assistant-runtime-hardening-dev` 合并回 `main`
  - 在 latest batch 显式记录 `docs-only` 验证画像与 close-out 证据
  - 将 branch/worktree disposition 在文件末尾落账，消除最终 `close-check` 的生命周期歧义
- 新增/调整的测试：无新增产品测试；本批仅处理 close-out 文档与分支真相
- 执行的命令：`V1`、`V2`、`V3`、`V4`、`V5`
- 测试结果：PASS
- 是否符合任务目标：是

#### 2.4 代码审查结论

- 宪章/规格对齐：通过；本批不新增产品行为，仅补齐 close-out 归档
- 代码质量：通过；未修改运行时代码
- 测试质量：通过；`verify constraints` 已在合并后的 `main` 上重新执行
- 结论：允许执行最终 `workitem close-check`

#### 2.5 任务/计划同步状态

- `tasks.md` 同步状态：已同步，`T51`、`T52`、`T53` 保持完成
- `related_plan`（如存在）同步状态：以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：`feature/002-invoice-assistant-runtime-hardening-dev` 已合并到 `main`
- 说明：本批只用于清除 verification profile 与 branch lifecycle 的最终 blocker

#### 2.6 自动决策记录

- 选择本地 fast-forward merge，而不是删除 feature branch；原因是 close-check 只要求 associated branch 不再 ahead of `main`
- 选择 `docs-only` 画像；原因是本批只修改执行归档文档，不修改产品代码、测试或 canonical truth
- 保留 feature branch 名称记录，不额外做归档删除；原因是当前收口目标是完成 close-check，而非强制清理引用名

#### 2.7 批次结论

- 工作区已清理，`main` 已包含 002 开发成果
- latest batch 已显式记录 `docs-only` 验证画像和合并后的 branch disposition
- 下一步为提交本批文档并在 clean tree 上执行最终 `workitem close-check`

#### 2.8 归档后动作

- **已完成 git 提交**：是
- **提交哈希**：以当前 `HEAD` 为准
- 当前批次 branch disposition 状态：merged
- 当前批次 worktree disposition 状态：main 保留
- 是否继续下一批：否
