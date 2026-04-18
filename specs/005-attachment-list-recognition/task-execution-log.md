# 任务执行日志：清单附件识别闭环

**功能编号**：`005-attachment-list-recognition`
**创建日期**：2026-04-18
**状态**：执行中

## 1. 归档规则

- 本文件是 `005-attachment-list-recognition` 的固定执行归档文件。
- 后续每完成一批任务，都在**本文件末尾追加一个新的批次章节**。
- 后续每一批任务开始前，必须先完成固定预读（PRD + 宪章 + 当前相关 spec 文档）。
- 后续每一批任务结束后，必须按固定顺序执行：
  - 先完成实现和验证
  - 再把本批结果追加归档到本文件
  - **单次提交（FR-097 / SC-022）**：将本批代码/测试与本次追加的归档段落、`tasks.md` 勾选 **合并为一次** `git commit`
  - 只有在当前批次已经提交完成后，才能进入下一批任务
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
- 覆盖阶段：Batch 1 文档基线冻结
- 预读范围：`发票整理助手_评审终版_重新生成.md`、`specs/001-invoice-assistant-mvp/spec.md`、`specs/004-controlled-review-export/spec.md`、`backend/app/services/rules/risk_classifier.py`、`backend/app/services/processing_service.py`、`backend/app/api/batches.py`
- 激活的规则：本地优先、可解释自动化、小步迭代、受控导出不回退

#### 2.2 统一验证命令

- `R1`（红灯验证，如有 TDD）
  - 命令：本批未涉及实现代码，未执行
  - 结果：N/A
- `V1`（定向验证）
  - 命令：`python -m ai_sdlc adapter activate`
  - 结果：通过
- `V2`（全量回归）
  - 命令：`python -m ai_sdlc run --dry-run`
  - 结果：通过（Stage close: PASS）

#### 2.3 任务记录

##### T11 | 替换 005 占位 spec 为正式业务范围

- 改动范围：`specs/005-attachment-list-recognition/spec.md`
- 改动内容：将 `workitem init` 生成的占位模板替换为真实产品规格，明确覆盖范围、非目标、三类用户故事、14 条功能需求、关键实体与成功标准。
- 新增/调整的测试：无
- 执行的命令：`python -m ai_sdlc workitem init --wi-id 005-attachment-list-recognition ...`，随后人工修正文档
- 测试结果：文档对账完成
- 是否符合任务目标：是

##### T12 | 固化实施计划与批次顺序

- 改动范围：`specs/005-attachment-list-recognition/plan.md`、`specs/005-attachment-list-recognition/tasks.md`
- 改动内容：补齐技术背景、宪章检查、源码结构、阶段计划、三条工作流、关键路径验证策略，并把任务分解改写为真实的五批实施计划。
- 新增/调整的测试：无
- 执行的命令：源码检索与文档修订
- 测试结果：文档对账完成
- 是否符合任务目标：是

##### T13 | 建立真实执行日志骨架

- 改动范围：`specs/005-attachment-list-recognition/task-execution-log.md`
- 改动内容：将脚手架日志替换为首批真实归档，记录 AI-SDLC 入口执行、工作项初始化、分支切换和文档基线修正。
- 新增/调整的测试：无
- 执行的命令：`git switch -c codex/005-attachment-list-recognition`
- 测试结果：分支创建成功
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：已把 005 收敛到“清单附件识别闭环”，并明确不扩展到 ERP/OA 或外部服务。
- 代码质量：本批仅修改正式文档，无实现代码风险。
- 测试质量：本批未进入实现阶段，已保留后续红灯测试任务。
- 结论：可进入 Batch 2 实现准备。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：已同步，T11-T13 标记完成，后续任务保持未开始
- `related_plan`（如存在）同步状态：已同步到 `plan.md`
- 关联 branch/worktree disposition 计划：已切换到 `codex/005-attachment-list-recognition` 继续承接 005
- 说明：`.ai-sdlc/project/config/project-config.yaml` 仅包含 adapter 激活时间戳更新，后续提交前按需要确认是否纳入版本控制

#### 2.6 自动决策记录（如有）

- 结合 PRD 第二阶段增强列表与 001/004 已完成范围，选择“清单附件识别”作为 005 的承接主题。

#### 2.7 批次结论

- 005 的 formal 文档已从脚手架模板替换为可执行基线，下一步进入上传入口与数据模型实现。

#### 2.8 归档后动作

- 已完成 git 提交：是
- 提交哈希：见当前 `HEAD`（提交内回填精确哈希会导致哈希再次变化）
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：沿用当前工作区
- 是否继续下一批：是

### Batch 2026-04-18-002 | T21-T22

#### 2.1 批次范围

- 覆盖任务：`T21`、`T22`
- 覆盖阶段：Batch 2 上传入口与数据模型
- 预读范围：`specs/005-attachment-list-recognition/spec.md`、`specs/005-attachment-list-recognition/plan.md`、`specs/005-attachment-list-recognition/tasks.md`、`backend/app/db/models.py`、`backend/app/services/batch_service.py`、`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/app/api/serializers.py`、`frontend/src/components/batch/UploadPanel.tsx`
- 激活的规则：本地优先、可解释自动化、小步迭代、受控导出不回退

#### 2.2 统一验证命令

- `R1`（红灯验证，如有 TDD）
  - 命令：`uv run pytest backend/tests/test_batch_storage.py -q`
  - 结果：先红后绿；初始因 `AttachmentDocument` 未定义失败，补齐模型与分流逻辑后通过
- `V1`（定向验证）
  - 命令：`uv run pytest backend/tests/test_api_workflows.py -q`
  - 结果：通过（9 passed）
- `V2`（前端验证）
  - 命令：`npm test -- tests/runtime-ui.test.tsx`
  - 结果：通过（6 passed）
- `V3`（构建验证）
  - 命令：`npm run build`
  - 结果：通过

#### 2.3 任务记录

##### T21 | 为批次文件建立附件候选类型与持久化结构

- 改动范围：`backend/app/db/models.py`、`backend/app/services/batch_service.py`、`backend/tests/test_batch_storage.py`
- 改动内容：新增 `AttachmentDocument` 模型与批次关联；批次创建时按文件名关键字将清单附件单独落库，不再混入 `InvoiceRecord`；同时把 `total_files` 收敛为进入识别流水线的主发票数，避免附件破坏现有进度语义；重复文件校验补齐附件表覆盖。
- 新增/调整的测试：新增混合上传存储测试，断言主票/附件分流、附件状态为 `pending_match`，以及批次 `total_files` 仅统计主票。
- 执行的命令：`uv run pytest backend/tests/test_batch_storage.py -q`
- 测试结果：通过（4 passed）
- 是否符合任务目标：是

##### T22 | 扩展批次创建 API 与前端上传协议

- 改动范围：`backend/app/api/serializers.py`、`backend/tests/test_api_workflows.py`、`frontend/src/app/types.ts`、`frontend/src/components/batch/UploadPanel.tsx`
- 改动内容：批次序列化新增 `invoice_file_count` 与 `attachment_file_count`；异步创建批次接口用例改为混合上传并校验新字段；前端上传面板文案调整为支持“PDF 发票与清单附件”，保留最小提示而不引入人工关联步骤。
- 新增/调整的测试：扩展现有异步 API 用例，验证混合上传时返回的发票数/附件数与进度统计口径；前端运行时 UI 用例保持通过。
- 执行的命令：`uv run pytest backend/tests/test_api_workflows.py -q`、`npm test -- tests/runtime-ui.test.tsx`、`npm run build`
- 测试结果：通过
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：本批仅完成“上传入口与数据模型”，未提前进入附件解析和规则消费。
- 代码质量：附件通过独立表建模，避免污染既有发票处理链；批次进度统计继续沿用“主票驱动”口径，新增附件数单独暴露。
- 测试质量：覆盖了存储层分流、接口响应契约和前端运行时/构建回归。
- 结论：可进入 Batch 3 的附件解析与匹配实现。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：已同步，T21-T22 标记完成
- `related_plan`（如存在）同步状态：无需调整，仍以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `codex/005-attachment-list-recognition` 上推进 Batch 3
- 说明：`.ai-sdlc/project/config/project-config.yaml` 与 `.ai-sdlc/project/config/project-state.yaml` 仍为运行态变更，未纳入本批提交

#### 2.6 自动决策记录（如有）

- 将 `total_files` 定义为“进入 OCR/规则流水线的主发票数”，附件数通过新增字段单独暴露，以保持 001/004 既有进度与导出约束不回退。

#### 2.7 批次结论

- Batch 2 已完成混合上传落库、接口计数扩展与前端最小提示，附件识别闭环的下一步阻塞点转为“附件解析与主票匹配”。

#### 2.8 归档后动作

- 已完成 git 提交：是
- 提交哈希：见当前 `HEAD`（提交内回填精确哈希会导致哈希再次变化）
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：沿用当前工作区
- 是否继续下一批：是

### Batch 2026-04-19-001 | T31-T32

#### 2.1 批次范围

- 覆盖任务：`T31`、`T32`
- 覆盖阶段：Batch 3 附件解析、匹配与分类
- 预读范围：`specs/005-attachment-list-recognition/spec.md`、`specs/005-attachment-list-recognition/plan.md`、`specs/005-attachment-list-recognition/tasks.md`、`backend/app/services/processing_service.py`、`backend/app/services/rules/risk_classifier.py`、`backend/tests/test_processing_runtime.py`、`backend/tests/test_rules_pipeline.py`
- 激活的规则：TDD 优先、主票语义不回退、附件 sidecar 保守消费、失败口径与进度口径不扩散

#### 2.2 统一验证命令

- `R1`（红灯验证，如有 TDD）
  - 命令：`uv run pytest backend/tests/test_rules_pipeline.py -q`、`uv run pytest backend/tests/test_processing_runtime.py -q`
  - 结果：先红后绿；初始分别因 `classify_risk()` 尚不接受 `attachment_evidence`，以及附件状态仍停留在 `pending_match`/主票未重判而失败
- `V1`（定向验证）
  - 命令：`uv run pytest backend/tests/test_rules_pipeline.py -q`、`uv run pytest backend/tests/test_processing_runtime.py -q`
  - 结果：通过（6 passed, 7 passed）
- `V2`（回归验证）
  - 命令：`uv run pytest backend/tests/test_batch_storage.py -q`、`uv run pytest backend/tests/test_api_workflows.py -q`、`uv run pytest backend/tests/test_progress_reporting.py -q`
  - 结果：通过（4 passed, 9 passed, 3 passed）

#### 2.3 任务记录

##### T31 | 为清单附件补充解析与匹配规则

- 改动范围：`backend/app/services/processing_service.py`、`backend/tests/test_processing_runtime.py`
- 改动内容：在 `ProcessingService.process_batch` 末尾新增附件 sidecar phase；复用既有 `_parse_document` 解析 `AttachmentDocument`，按同批次发票号/代码/销方/金额做保守匹配，写回 `matched`/`consumed`/`ambiguous`/`unmatched`/`parse_failed` 状态与原因；附件解析失败不进入 `InvoiceRecord` 的失败通道，也不改变 `total_files`/`recent_failures` 语义。
- 新增/调整的测试：新增 runtime 场景覆盖“可信附件触发主票重判”“附件解析失败不产生运行时失败”“多发票歧义匹配保持保守”三条路径，并使用最小 PDF fixture 控制主票/附件元数据。
- 执行的命令：`uv run pytest backend/tests/test_processing_runtime.py -q`
- 测试结果：通过（7 passed）
- 是否符合任务目标：是

##### T32 | 让风险分类器消费附件证据

- 改动范围：`backend/app/services/rules/risk_classifier.py`、`backend/tests/test_rules_pipeline.py`
- 改动内容：为 `classify_risk` 增加可选 `attachment_evidence` 输入；仅当主票命中“详见清单”类关键词且附件自身达到置信阈值时，才用附件表格行替换主票的占位行文本，再复用既有白名单/拒绝/通过规则；主票低置信、附件低置信或未触发“详见清单”时均保持原判。
- 新增/调整的测试：新增三条纯规则单测，覆盖“可信附件可解除详见清单默认待复核”“低置信主票仍保留复核”“无详见清单触发时忽略附件”。
- 执行的命令：`uv run pytest backend/tests/test_rules_pipeline.py -q`
- 测试结果：通过（6 passed）
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：实现严格停留在 Batch 3，附件只作为 sidecar 证据参与匹配与重判，没有抬升为新的 processing 主对象。
- 代码质量：附件解析与匹配被限制在 `ProcessingService` 的批次后处理阶段；`risk_classifier` 仍保持纯函数，只接受紧凑证据输入。
- 测试质量：红绿循环覆盖了规则边界、附件状态机，以及 `total_files`/`recent_failures` 的回归口径。
- 结论：可进入 Batch 4 的结果展示与导出对齐。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：已同步，T31-T32 标记完成
- `related_plan`（如存在）同步状态：无需调整，仍以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `codex/005-attachment-list-recognition` 上推进 Batch 4
- 说明：`.ai-sdlc/project/config/project-config.yaml` 与 `.ai-sdlc/project/config/project-state.yaml` 仍为运行态变更，未纳入本批提交

#### 2.6 自动决策记录（如有）

- 在财务/工程双重对抗评估后，确定本批只做 `ProcessingService` 内的附件 sidecar：不扩散到 `ProcessingJob`、`ProcessingAttempt`、`DocumentEvidence` 或批次总览序列化。

#### 2.7 批次结论

- Batch 3 已完成附件摘要解析、同批次保守匹配和“详见清单”主票的受控重判，同时保持主票失败与进度统计语义不回退。

#### 2.8 归档后动作

- 已完成 git 提交：是
- 提交哈希：见当前 `HEAD`（提交内回填精确哈希会导致哈希再次变化）
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：沿用当前工作区
- 是否继续下一批：是

### Batch 2026-04-19-002 | T41-T42

#### 2.1 批次范围

- 覆盖任务：`T41`、`T42`
- 覆盖阶段：Batch 4 结果展示与导出对齐
- 预读范围：`specs/005-attachment-list-recognition/spec.md`、`specs/005-attachment-list-recognition/plan.md`、`specs/005-attachment-list-recognition/tasks.md`、`backend/app/api/serializers.py`、`backend/app/services/export_service.py`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/BatchResults.tsx`、`backend/tests/test_api_workflows.py`、`backend/tests/test_export_service.py`、`frontend/tests/runtime-ui.test.tsx`
- 激活的规则：TDD 优先、附件 sidecar 保守暴露、004 导出角色边界不回退、结果态最小增量展示

#### 2.2 统一验证命令

- `R1`（红灯验证，如有 TDD）
  - 命令：`uv run pytest backend/tests/test_api_workflows.py::test_batch_and_invoice_api_workflows_cover_summary_detail_and_review backend/tests/test_export_service.py::test_export_service_blocks_pending_review_pass_export_and_success_manifest_includes_compliance_fields -q`、`npm test -- tests/runtime-ui.test.tsx`
  - 结果：先红后绿；后端初始因缺少 `attachment_status_counts` 与导出清单附件列失败，前端初始因结果页/抽屉未展示附件识别文本失败
- `V1`（定向验证）
  - 命令：`uv run pytest backend/tests/test_api_workflows.py::test_batch_and_invoice_api_workflows_cover_summary_detail_and_review backend/tests/test_export_service.py::test_export_service_blocks_pending_review_pass_export_and_success_manifest_includes_compliance_fields -q`、`npm test -- tests/runtime-ui.test.tsx`
  - 结果：通过（2 passed，6 passed）
- `V2`（回归验证）
  - 命令：`uv run pytest backend/tests/test_api_workflows.py backend/tests/test_export_service.py -q`、`npm test -- tests/runtime-ui.test.tsx`、`npm run build`
  - 结果：通过（13 passed，6 passed，build passed）

#### 2.3 任务记录

##### T41 | 扩展结果 API、详情抽屉与导出摘要

- 改动范围：`backend/app/api/serializers.py`、`backend/app/services/export_service.py`、`backend/tests/test_api_workflows.py`、`backend/tests/test_export_service.py`、`frontend/src/app/types.ts`、`frontend/src/components/results/InvoiceDrawer.tsx`
- 改动内容：批次/发票序列化新增附件状态统计与已匹配附件详情；详情抽屉展示附件文件名、识别状态和匹配依据/失败原因；导出清单补入精简的“清单附件 / 附件识别 / 附件匹配依据”列，仅输出与当前发票关联的 sidecar 结论，不改变 004 的角色控制或审核通过门槛。
- 新增/调整的测试：扩展 API 工作流用例，校验批次状态统计与发票详情附件序列化；扩展导出服务用例，校验 Excel manifest 含附件列和值；抽屉类型同步更新以承接新字段。
- 执行的命令：`uv run pytest backend/tests/test_api_workflows.py::test_batch_and_invoice_api_workflows_cover_summary_detail_and_review backend/tests/test_export_service.py::test_export_service_blocks_pending_review_pass_export_and_success_manifest_includes_compliance_fields -q`
- 测试结果：通过（2 passed）
- 是否符合任务目标：是

##### T42 | 补齐前端混合上传与结果态提示

- 改动范围：`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/tests/runtime-ui.test.tsx`
- 改动内容：批次工作台与结果页补充“清单附件 X”与附件状态标签，保持主票关键指标仍位于首位；仅在存在附件时展示附件统计，避免挤占无附件场景；结果抽屉展示单票附件识别细节，未匹配附件继续保留在批次级统计而不强塞进单票详情。
- 新增/调整的测试：运行时 UI 用例补充工作台、结果页与发票抽屉的附件状态断言，覆盖 `已消费`、`未匹配`、`解析失败` 等文本。
- 执行的命令：`npm test -- tests/runtime-ui.test.tsx`、`npm run build`
- 测试结果：通过（6 passed，build passed）
- 是否符合任务目标：是

#### 2.4 代码审查结论（Mandatory）

- 宪章/规格对齐：本批只做结果层暴露与导出摘要补齐，保持附件仍是 `ProcessingService` sidecar，不抬升为新的 processing 主实体。
- 代码质量：批次级显示只暴露聚合状态计数，单票详情只展示已匹配附件，未匹配/歧义附件继续留在批次层，避免误导用户把附件当成主票。
- 测试质量：红绿循环覆盖 API 契约、Excel manifest 文案、结果页状态条和详情抽屉，外加前端构建回归。
- 结论：可进入 Batch 5 的回归验证与收口。

#### 2.5 任务/计划同步状态（Mandatory）

- `tasks.md` 同步状态：已同步，T41-T42 标记完成
- `related_plan`（如存在）同步状态：无需调整，仍以 `plan.md` 为准
- 关联 branch/worktree disposition 计划：继续在 `codex/005-attachment-list-recognition` 上推进 Batch 5
- 说明：`.ai-sdlc/project/config/project-config.yaml` 与 `.ai-sdlc/project/config/project-state.yaml` 仍为运行态变更，未纳入本批提交

#### 2.6 自动决策记录（如有）

- 结果层仅暴露“附件状态计数 + 已匹配附件详情”；未匹配附件不挂到单张发票详情，避免把批次级匹配失败错误归因到某一主票。

#### 2.7 批次结论

- Batch 4 已完成结果展示与导出对齐，附件识别闭环现在已经覆盖上传、解析、风险消费、结果展示与导出摘要。

#### 2.8 归档后动作

- 已完成 git 提交：否（待本批代码与文档一起提交）
- 提交哈希：N/A
- 当前批次 branch disposition 状态：进行中
- 当前批次 worktree disposition 状态：沿用当前工作区
- 是否继续下一批：是
