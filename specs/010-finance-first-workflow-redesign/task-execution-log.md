# 任务执行日志：财务优先工作流重设计
**功能编号**：`010-finance-first-workflow-redesign`
**创建日期**：2026-04-24
**状态**：进行中，当前已完成正式文档冻结、Phase 0 体验止血与 Phase 1 契约冻结，待进入 Phase 2 配置中心重做

## 1. 归档规则

- 本文件是 `010-finance-first-workflow-redesign` 的固定执行归档文件。
- 后续每完成一批任务，都在本文件末尾追加一个新的批次章节。
- 每次归档至少记录：任务编号、任务名称、改动范围、改动内容、新增/调整测试、执行命令、测试结果、是否符合任务目标。
- 若因环境或框架缺陷无法使用标准命令，也必须在本文件明确记录原因、替代方案和影响范围。

## 2. 批次记录

### Batch 2026-04-24-001 | T11 正式规格草案起草
#### 2.1 批次范围

- 覆盖任务：`T11`
- 覆盖阶段：Batch 1 正式规格草案与对抗评审收口
- 预读范围：`docs/invoice-assistant-gap-backlog.zh-CN.md`、`docs/superpowers/specs/2026-04-24-invoice-assistant-ux-redesign.md`、`specs/009-export-audit-surface-refresh/*`
- 激活规则：先冻结正式范围，再提交给两名对抗 agent 审阅，不带着未审稿进入后续开发

#### 2.2 统一验证命令

- `V0`（框架命令探测）
  - 命令：`python -m ai_sdlc workitem init --help`
  - 结果：通过，可确认框架提供 `workitem init`
- `V1`（框架初始化尝试）
  - 命令：`python -m ai_sdlc workitem init --wi-id 010-finance-first-workflow-redesign ...`
  - 结果：失败；报错缺少模板文件 `spec-template.md`
- `V2`（正式文档结构校验）
  - 命令：手工对读 `spec.md`、`plan.md`、`tasks.md`
  - 结果：通过；结构与现有 `specs/*` 一致

#### 2.3 任务记录

##### T11 | 起草 010 正式范围与非目标

- 改动范围：`specs/010-finance-first-workflow-redesign/spec.md`、`plan.md`、`tasks.md`、`task-execution-log.md`、`.ai-sdlc/project/config/project-state.yaml`
- 改动内容：
  - 新建 010 正式工单目录与核心文档草案。
  - 冻结本轮范围：配置中心重做、批次结果重做、人工确认闭环、导出与预览主流程收口。
  - 明确非目标：不重写 OCR 算法、不回写历史批次、不做权限系统。
  - 记录 `workitem init` 因环境模板缺失不可用，改为手工维护正式工单。
- 新增/调整的测试：无产品代码测试；当前为规格冻结阶段。
- 执行的命令：`V0`、`V1`、`V2`
- 测试结果：规格文档已生成；框架初始化命令因环境缺陷失败，但不影响正式文档落地。
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：已对齐。当前只冻结正式规格，不提前混入未审实现。
- 文档质量：规格、计划、任务拆解已明确用户问题、范围边界、阶段次序和验证方式。
- 风险：尚未完成两名对抗 agent 合议；文档状态暂不冻结为最终版。
- 结论：允许进入 `T12` 合议评审阶段。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：`T11` 已完成，`T12` 进行中，其余任务未开始。
- `related_plan` 同步状态：已与 `plan.md` 对齐。
- 说明：待合议评审结束后，再更新文档状态与后续执行建议。

### Batch 2026-04-24-002 | T12 两名对抗 agent 合议评审与冻结
#### 2.1 批次范围

- 覆盖任务：`T12`
- 覆盖阶段：Batch 1 正式规格草案与对抗评审收口
- 预读范围：`specs/010-finance-first-workflow-redesign/spec.md`、`plan.md`、`tasks.md`、`task-execution-log.md`
- 激活规则：只有两名对抗 agent 都给出通过结论，才允许把文档状态从 draft 切换为冻结

#### 2.2 统一验证命令

- `V3`（框架约束校验）
  - 命令：`python -m ai_sdlc verify constraints`
  - 结果：通过，`no BLOCKERs`
- `A1`（首轮对抗评审）
  - 方式：向两名 agent 分别发送正式工单草案并要求只报阻断级/高优先问题
  - 结果：两名 agent 均判定 `reject`
- `A2`（首轮修订后复审）
  - 方式：针对首轮 findings 修订文档后再次送审
  - 结果：财务体验侧 agent 通过，技术侧 agent 继续阻断
- `A3`（最终收口复审）
  - 方式：将 `ReviewQueueItem` 与 canonical business bucket 的最终冻结方案送审
  - 结果：两名 agent 均回复 `approve`

#### 2.3 任务记录

##### T12 | 完成两名对抗 agent 合议评审

- 改动范围：`spec.md`、`plan.md`、`tasks.md`、`task-execution-log.md`、`development-summary.md`
- 改动内容：
  - 根据财务体验侧 agent 结论，前移 typed contract 冻结、稳定预览和“本批次重复”优先级。
  - 根据技术侧 agent 结论，补齐 `ConfigBundle` 的唯一事实源与版本规则、`StableInvoiceStatus` 的归档语义、兼容矩阵，以及 `ReviewQueueItem` 的持久化工作项定义。
  - 统一结果页 canonical business bucket 为“建议通过 / 待人工确认 / 本批次重复 / 需补充/重试”，技术失败降为次级原因。
  - 在两名 agent 均通过后，将 `spec.md` 状态切换为已冻结，并将 `tasks.md` 中 `T12` 标记为完成。
- 新增/调整的测试：无产品代码测试；本批次为治理文档与合议收口。
- 执行的命令：`V3`、`A1`、`A2`、`A3`
- 测试结果：两名对抗 agent 最终均通过；框架约束校验通过。
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：已对齐。正式工单在进入后续开发前完成了对抗式审查和阻断项收敛。
- 文档质量：已冻结范围、阶段顺序、兼容矩阵、领域契约和结果分组 canonical 术语。
- 风险：后续开发阶段仍需逐批验证实现与冻结契约的一致性，但当前治理文档已可作为 authoritative baseline。
- 结论：允许进入 Batch 2 及后续开发批次。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：`T11`、`T12` 已完成，其余任务未开始。
- `related_plan` 同步状态：已与 `plan.md` 对齐。
- 说明：当前 010 已完成规格冻结，下一步可进入 Phase 0 体验止血或 Phase 1 契约实现。

### Batch 2026-04-24-003 | T21-T23 Phase 0 体验止血实现与浏览器回归
#### 2.1 批次范围

- 覆盖任务：`T21`、`T22`、`T23`
- 覆盖阶段：Batch 2 Phase 0 体验止血
- 预读范围：`spec.md`、`plan.md`、`tasks.md`、`frontend/src/pages/Settings.tsx`、`frontend/src/pages/SetupWizard.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/components/results/*`
- 激活规则：先完成展示层止血，不提前进入 Phase 1 契约重写；所有状态与文案变更必须能被前端测试和 Playwright 回归共同验证。

#### 2.2 统一验证命令

- `V4`（前端运行时 UI 测试）
  - 命令：`corepack pnpm --dir frontend test -- --runInBand`
  - 结果：通过，`17 passed`
- `V5`（前端发布构建）
  - 命令：`corepack pnpm --dir frontend build`
  - 结果：通过，Vite 构建成功
- `V6`（本地开发态服务健康检查）
  - 命令：`Invoke-WebRequest http://127.0.0.1:8000/health`、`Invoke-WebRequest http://127.0.0.1:5173`
  - 结果：通过，前后端健康可访问
- `V7`（Playwright 配置中心与结果页回归）
  - 命令：使用 `npx --yes --package @playwright/cli playwright-cli`，配合 `output/playwright/playwright-cli.json` 指向系统 Chrome，完成首次配置、配置中心字段化入口、批次结果页、详情抽屉和高级诊断页回归
  - 结果：通过
- `V8`（Playwright 人工确认即时刷新回归）
  - 命令：在 `PW-REVIEW-20260424-01` 批次中打开 `03-review-required.pdf`，提交“确认通过”
  - 结果：通过；列表、抽屉、摘要同步刷新为“建议通过 / 已人工确认通过”

#### 2.3 任务记录

##### T21 | 移除后续配置 JSON 主入口

- 改动范围：`frontend/src/pages/Settings.tsx`、`frontend/src/pages/SetupWizard.tsx`、`frontend/tests/runtime-ui.test.tsx`
- 改动内容：
  - 将“配置中心”主路径改为字段摘要与字段化修改入口，不再在主视图展示技术 JSON。
  - 配置中心新增税务档案、审核策略、文件命名三组只读摘要，并提供“按字段修改配置”入口。
  - 复用首次配置向导作为后续调整表单；已配置场景下切换为“配置调整”文案，并在保存成功后返回配置中心。
- 新增/调整的测试：
  - 更新运行时 UI 测试，覆盖“配置中心”隐藏 JSON、显示字段摘要和“按字段修改配置”入口。
- 执行的命令：`V4`、`V5`、`V6`、`V7`
- 测试结果：通过；Playwright 已完成首次配置 -> 配置中心 -> 字段化修改入口回归。
- 是否符合任务目标：是

##### T22 | 结果页与详情页默认收起内部诊断

- 改动范围：`frontend/src/pages/BatchResults.tsx`、`frontend/src/components/results/ResultTable.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/components/results/resultPresentation.ts`、`frontend/src/app/api.ts`、`frontend/tests/runtime-ui.test.tsx`
- 改动内容：
  - 抽取结果展示层映射，统一“建议通过 / 待人工确认 / 本批次重复 / 需补充/重试”等财务动作语言。
  - 结果页主表移除 `risk_flags` 等技术字段直出，`系统结论` 改为 `处理结论`，`人工复核` 改为 `人工确认`。
  - 详情抽屉首屏只保留业务摘要；provider、失败阶段、错误码等技术诊断下沉到“高级诊断”页签。
  - PDF 预览页签保留“打开原始 PDF”入口。
- 新增/调整的测试：
  - 更新运行时 UI 测试，验证结果页文案、详情页高级诊断分页、默认隐藏技术诊断信息。
- 执行的命令：`V4`、`V5`、`V6`、`V7`
- 测试结果：通过；Playwright 在 `PW-REVIEW-20260424-01` 批次中验证了默认业务首屏与“高级诊断”页签。
- 是否符合任务目标：是

##### T23 | 修复处理中等待态与人工确认即时刷新

- 改动范围：`frontend/src/pages/BatchResults.tsx`、`frontend/src/components/results/ResultTable.tsx`、`frontend/src/components/results/ReviewActions.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/components/results/resultPresentation.ts`、`frontend/tests/runtime-ui.test.tsx`
- 改动内容：
  - 批次仍处于活动阶段时自动轮询刷新结果页，处理中批次禁用“另存为”，避免过早导出。
  - 处理中与失败态在列表中使用独立文案分支，不再把未完成识别直接落成“税号缺失”。
  - 人工确认提交后，详情抽屉先乐观合并返回摘要，再刷新列表、批次摘要与详情数据，消除“待确认不刷新”的体验问题。
- 新增/调整的测试：
  - 更新运行时 UI 测试，覆盖人工确认动作返回更新后单票摘要；保留处理中/失败映射逻辑的组件级回归。
- 执行的命令：`V4`、`V5`、`V6`、`V7`、`V8`
- 测试结果：通过；Playwright 抓到 bulk 批次“处理中 1”的实时状态，并在 review 批次验证人工确认后主表、抽屉、批次摘要即时刷新。
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：已对齐。Batch 2 只做体验止血，没有提前引入 Phase 1 的大规模契约重写。
- 实现质量：配置中心、结果页、详情抽屉与人工确认统一切换到财务动作语言；技术诊断被收口到高级信息区。
- 风险：
  - Playwright 控制台仍有 React Router future warning。
  - 人工确认提交时出现一条第三方组件警告 `There may be circular references`，但不影响提交成功和状态刷新，需后续单独清理。
- 结论：允许将 `T21-T23` 标记为完成，并进入下一批契约冻结与兼容矩阵实现。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：`T11`、`T12`、`T21`、`T22`、`T23` 已完成，其余任务未开始。
- `related_plan` 同步状态：已与 `plan.md` 对齐；当前已完成 Phase 0 体验止血。
- 说明：本批次生成的浏览器回归证据位于 `output/playwright/phase0-results-processing.png`、`phase0-drawer-preview.png`、`phase0-review-before-submit.png`、`phase0-review-after-submit.png`。

### Batch 2026-04-24-004 | T31-T33 Phase 1 契约冻结与兼容矩阵落地
#### 2.1 批次范围

- 覆盖任务：`T31`、`T32`、`T33`
- 覆盖阶段：Batch 3 Phase 1 契约冻结与兼容矩阵
- 预读范围：`backend/app/services/config_service.py`、`backend/app/services/status_service.py`、`backend/app/api/config.py`、`backend/app/api/invoices.py`、`backend/app/db/models.py`、`frontend/src/app/types.ts`
- 激活规则：先把 canonical contract 写成真实代码和测试，再允许进入 Phase 2/3 的重 UI 与工作台开发

#### 2.2 统一验证命令

- `V9`（Phase 1 后端定向回归）
  - 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_config_versioning.py backend/tests/test_naming_and_display_status.py backend/tests/test_api_workflows.py -q`
  - 结果：通过，`31 passed`
- `V10`（前端发布构建）
  - 命令：`corepack pnpm --dir frontend build`
  - 结果：通过，Vite 构建成功
- `V11`（源码语法编译）
  - 命令：`backend/.venv/Scripts/python.exe -m compileall backend/app frontend/src`
  - 结果：通过
- `V12`（标准工具链受限记录）
  - 命令：`workspace/.venv/Scripts/pytest.exe ...`、`workspace/.venv/Scripts/ruff.exe ...`
  - 结果：失败；当前工作目录不是 Git 仓库，tracked-file policy 包装器在 `git ls-files` 处提前退出，因此本批次改用 `backend/.venv` 直接执行 pytest，并以 `compileall + frontend build` 补足静态校验

#### 2.3 任务记录

##### T31 | 冻结 ConfigBundle 的唯一事实源与版本规则

- 改动范围：`backend/app/services/config_service.py`、`backend/app/api/config.py`、`backend/app/db/models.py`、`backend/app/services/batch_service.py`、`frontend/src/app/types.ts`
- 改动内容：
  - 将后续配置写入统一收敛到 `ConfigBundle` 发布逻辑；旧 `/api/config/{kind}/versions` 入口改为兼容包装器，不再直接单写单类规则。
  - 为每次 bundle 发布分配统一 `bundle_version_no`，并在规则版本、当前配置响应、批次对象上暴露该版本号。
  - 新增 bundle 版本列表接口与 canonical config 响应字段，保留旧 `active_snapshot` / `active_versions` 兼容读取。
- 新增/调整的测试：
  - 更新 `backend/tests/test_config_versioning.py`，覆盖 shared bundle version、active bundle、批次绑定最新 bundle 快照。
- 执行的命令：`V9`、`V10`、`V11`
- 测试结果：通过
- 是否符合任务目标：是

##### T32 | 冻结稳定状态模型、归档语义与兼容矩阵

- 改动范围：`backend/app/services/status_service.py`、`backend/app/api/serializers.py`、`backend/app/services/export_service.py`、`frontend/src/app/types.ts`
- 改动内容：
  - 新增 `StableInvoiceStatus` 与 canonical business bucket，统一派生 `processing_status / review_status / archive_status`。
  - 在单票摘要与详情接口增加 `stable_status`、`business_bucket`、`business_bucket_label`，保留旧 `display_status` 作为兼容展示层字段。
  - 将“另存为 ZIP”动作与 `archive_status=saved` 对齐，避免再把自动落盘语义混入归档状态。
- 新增/调整的测试：
  - 更新 `backend/tests/test_naming_and_display_status.py`，覆盖稳定状态、business bucket 与 canonical summary。
  - 更新 `backend/tests/test_api_workflows.py`，覆盖 `archive_status` 与 action summary 响应。
- 执行的命令：`V9`、`V10`、`V11`
- 测试结果：通过
- 是否符合任务目标：是

##### T33 | 冻结人工确认工作项的最小领域契约

- 改动范围：`backend/app/db/models.py`、`backend/app/services/review_queue_service.py`、`backend/app/api/invoices.py`、`backend/app/services/processing_service.py`、`backend/app/services/retry_service.py`
- 改动内容：
  - 新增持久化 `ReviewQueueItem`，冻结同批次同发票唯一工作项、打开/关闭状态与原因码。
  - 在处理完成、失败重试、人工确认提交等状态切换点同步 review queue。
  - 新增 `/api/review-queue` 接口，并让复核提交返回 `review_queue_item` 与权威 `batch_action_summary`。
- 新增/调整的测试：
  - 更新 `backend/tests/test_api_workflows.py`，覆盖 review queue 列表、复核后队列关闭和批次摘要刷新。
- 执行的命令：`V9`、`V10`、`V11`
- 测试结果：通过
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：已对齐。Phase 1 只冻结领域契约与兼容矩阵，没有提前把 Phase 2/3 的重 UI 混进来。
- 实现质量：`ConfigBundle`、稳定状态、`ReviewQueueItem` 已经成为可被前后端共同消费的真实契约，不再只是规格文字。
- 风险：
  - 当前工作区不是 Git 仓库，`workspace/.venv` 下的 tracked-file policy 包装器无法执行标准 pytest/ruff 入口；后续如需恢复完整工具链，需在正式仓库环境复验。
  - Phase 2 配置中心发布确认页、Phase 3 独立人工确认工作台与结果页 business bucket 重构仍未开始。
- 结论：允许将 `T31-T33` 标记为完成，并进入 `T41/T42` 或 `T51-T54` 开发批次。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：`T11`、`T12`、`T21`、`T22`、`T23`、`T31`、`T32`、`T33` 已完成，其余任务未开始。
- `related_plan` 同步状态：已与 `plan.md` 对齐；当前已完成 Batch 3 Phase 1 契约冻结与兼容矩阵。
- 说明：下一批应优先进入 `T41/T42` 配置中心重做，或在需要先打通高频路径时进入 `T51/T52` 结果页分组与人工确认工作台。
