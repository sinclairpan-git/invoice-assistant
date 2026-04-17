# 任务执行日志：发票整理助手二期：真实解析与运行时加固

**功能编号**：`002-invoice-assistant-runtime-hardening`  
**创建日期**：2026-04-17  
**状态**：Batch 3 T31 已完成，T32 准备中

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
