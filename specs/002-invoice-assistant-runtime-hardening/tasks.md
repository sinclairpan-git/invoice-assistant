---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "specs/001-invoice-assistant-mvp/spec.md"
---
# 任务分解：发票整理助手二期：真实解析与运行时加固

**编号**：`002-invoice-assistant-runtime-hardening` | **日期**：2026-04-17  
**来源**：`spec.md` + `research.md` + `data-model.md` + `plan.md`

## 分批策略

```text
Batch 1: 二期 canonical 文档基线与框架对齐
Batch 2: 真实 PDF 文本抽取与 OCR fallback
Batch 3: 持久化作业、异步执行与恢复
Batch 4: API 诊断、失败重试与前端接入
Batch 5: 回归验证、导出一致性与收口
```

## 路径约定

- 后端：`backend/app/**`、`backend/tests/**`
- 前端：`frontend/src/**`、`frontend/tests/**`
- 正式文档：`specs/002-invoice-assistant-runtime-hardening/**`

## Batch 1：二期 canonical 文档基线与框架对齐

- [x] T11 固化二期规格与范围边界
- [x] T12 固化研究结论、数据模型和实施计划
- [x] T13 生成执行清单、执行日志并完成文档阶段校验

### Task 1.1 固化二期规格与范围边界

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：`specs/002-invoice-assistant-runtime-hardening/spec.md`
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确二期覆盖范围、不覆盖范围、用户故事、功能需求、关键实体和成功标准。
  2. 文档清楚说明二期目标是“真实解析 + 运行时加固”，而不是重写一期业务规则。
  3. 不保留 `待补充`、脚手架占位或与现有仓库不一致的技术方案。
- **验证**：`python -m ai_sdlc gate refine`

### Task 1.2 固化研究结论、数据模型和实施计划

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：`specs/002-invoice-assistant-runtime-hardening/research.md`、`specs/002-invoice-assistant-runtime-hardening/data-model.md`、`specs/002-invoice-assistant-runtime-hardening/plan.md`
- **可并行**：否
- **验收标准**：
  1. `research.md` 明确二期为何维持 SQLite + 本地文件系统 + 进程内 worker，而不是引入 Redis / Celery。
  2. `data-model.md` 覆盖 `ProcessingJob`、`ProcessingAttempt`、provider 诊断和幂等性约束。
  3. `plan.md` 明确文档、真实解析、异步恢复、前端接入和收口顺序。
- **验证**：`python -m ai_sdlc gate design`

### Task 1.3 生成执行清单、执行日志并完成文档阶段校验

- **任务编号**：T13
- **优先级**：P0
- **依赖**：T12
- **文件**：`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- **可并行**：否
- **验收标准**：
  1. `tasks.md` 为后续 execute 提供分批任务、依赖、文件边界和验证命令。
  2. `task-execution-log.md` 记录 Batch 1 的文档冻结与校验过程。
  3. workitem 与当前分支、计划和文档阶段状态保持一致。
- **验证**：`python -m ai_sdlc gate decompose`、`uv run ai-sdlc verify constraints`、`python -m ai_sdlc workitem branch-check --wi specs/002-invoice-assistant-runtime-hardening`

## Batch 2：真实 PDF 文本抽取与 OCR fallback

- [x] T21 接入真实 PDF 文本抽取 provider
- [x] T22 接入本地 OCR fallback 与低置信降级
- [x] T23 补齐真实样本回归集和解析测试

### Task 2.1 接入真实 PDF 文本抽取 provider

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T13
- **文件**：`backend/pyproject.toml`、`backend/app/services/parsing/providers.py`、`backend/app/services/processing_service.py`、`backend/tests/test_document_evidence.py`
- **可并行**：否
- **验收标准**：
  1. 系统可对真实 PDF 二进制执行文本抽取。
  2. 真实文本抽取结果可映射到统一证据模型。
  3. provider 诊断信息能落到证据或 attempt 记录中。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_document_evidence.py -q`

### Task 2.2 接入本地 OCR fallback 与低置信降级

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：`backend/app/services/parsing/providers.py`、`backend/app/services/processing_service.py`、`backend/tests/test_processing_runtime.py`
- **可并行**：否
- **验收标准**：
  1. 文本抽取不可用时自动切换本地 OCR。
  2. OCR 低置信结果进入 `review_required`，不直接自动通过。
  3. OCR 失败能输出结构化失败信息。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py -q`

### Task 2.3 补齐真实样本回归集和解析测试

- **任务编号**：T23
- **优先级**：P1
- **依赖**：T22
- **文件**：`backend/tests/fixtures/**`、`backend/tests/test_processing_runtime.py`
- **可并行**：是
- **验收标准**：
  1. 覆盖电子票、扫描票、低置信票、损坏票或加密票样本。
  2. 样本可验证文本优先、OCR fallback 和失败路径。
  3. 样本命名与脱敏方式可在仓库内长期维护。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py -q`

## Batch 3：持久化作业、异步执行与恢复

- [x] T31 建立作业与尝试数据模型
- [x] T32 实现后台 worker、阶段推进与幂等性
- [x] T33 实现恢复与重试服务

### Task 3.1 建立作业与尝试数据模型

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T13
- **文件**：`backend/app/db/models.py`、`backend/app/db/session.py`、`backend/tests/test_processing_jobs.py`
- **可并行**：否
- **验收标准**：
  1. 建立 `ProcessingJob`、`ProcessingAttempt` 及关联字段。
  2. 现有 `Batch`、`InvoiceRecord` 保持向后兼容。
  3. attempt 唯一性与当前有效 attempt 语义明确。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_processing_jobs.py -q`

### Task 3.2 实现后台 worker、阶段推进与幂等性

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31、T22
- **文件**：`backend/app/services/processing_service.py`、`backend/app/services/progress_service.py`、`backend/tests/test_processing_jobs.py`
- **可并行**：否
- **验收标准**：
  1. 批次创建后异步入队，后台逐票推进。
  2. 阶段推进具有幂等性，不重复累加统计和证据。
  3. 前端轮询接口能读取更细粒度阶段信息。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_processing_jobs.py -q`

### Task 3.3 实现恢复与重试服务

- **任务编号**：T33
- **优先级**：P0
- **依赖**：T32
- **文件**：`backend/app/services/recovery_service.py`、`backend/app/services/retry_service.py`、`backend/tests/test_processing_recovery.py`
- **可并行**：是
- **验收标准**：
  1. 服务启动时可回收失联作业。
  2. 失败票和失败子批次支持重试。
  3. 重试后不重复生成统计、导出或旧 attempt 副作用。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_processing_recovery.py -q`

## Batch 4：API 诊断、失败重试与前端接入

- [x] T41 扩展进度与失败诊断 API
- [x] T42 暴露单票 / 批次重试接口
- [x] T43 前端接入阶段文案、失败详情与重试入口

### Task 4.1 扩展进度与失败诊断 API

- **任务编号**：T41
- **优先级**：P0
- **依赖**：T32
- **文件**：`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/serializers.py`、`backend/tests/test_api_workflows.py`
- **可并行**：否
- **验收标准**：
  1. 批次进度接口返回更细粒度阶段、最近失败、provider 诊断摘要。
  2. 发票详情接口返回 parse source、失败阶段、错误码和可重试标记。
  3. 旧前端依赖字段保持兼容。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py -q`

### Task 4.2 暴露单票 / 批次重试接口

- **任务编号**：T42
- **优先级**：P1
- **依赖**：T33、T41
- **文件**：`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/tests/test_api_workflows.py`
- **可并行**：是
- **验收标准**：
  1. 失败票支持单票重试。
  2. 批次支持只重试失败子集，而不是强制整批重跑。
  3. 重试接口遵循幂等约束。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_api_workflows.py -q`

### Task 4.3 前端接入阶段文案、失败详情与重试入口

- **任务编号**：T43
- **优先级**：P1
- **依赖**：T41、T42
- **文件**：`frontend/src/pages/BatchWorkbench.tsx`、`frontend/src/pages/BatchResults.tsx`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/tests/runtime-ui.test.tsx`
- **可并行**：否
- **验收标准**：
  1. 工作台展示更细粒度阶段文案、最近失败和失败数量。
  2. 详情抽屉展示解析来源、provider 诊断和是否可重试。
  3. 结果页与批次页可触发重试，不影响既有合规金额展示。
- **验证**：`corepack pnpm --dir frontend run build`

## Batch 5：回归验证、导出一致性与收口

- [x] T51 完成真实样本、恢复与重试端到端回归
- [x] T52 验证导出和合规金额统计不回退
- [x] T53 更新执行归档并完成 close-out

### Task 5.1 完成真实样本、恢复与重试端到端回归

- **任务编号**：T51
- **优先级**：P0
- **依赖**：T43
- **文件**：`backend/tests/test_processing_runtime.py`、`backend/tests/test_processing_recovery.py`、`backend/tests/test_api_workflows.py`
- **可并行**：否
- **验收标准**：
  1. 电子票、扫描票、损坏票和重试路径全部跑通。
  2. 重启恢复验证通过。
  3. 无永久卡住的运行态记录。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_processing_runtime.py backend/tests/test_processing_recovery.py backend/tests/test_api_workflows.py -q`

### Task 5.2 验证导出和合规金额统计不回退

- **任务编号**：T52
- **优先级**：P0
- **依赖**：T43
- **文件**：`backend/app/services/export_service.py`、`backend/tests/test_export_service.py`、`frontend/src/pages/BatchResults.tsx`
- **可并行**：是
- **验收标准**：
  1. 导出 ZIP / Excel 统计口径与界面一致。
  2. 合规票总金额继续在批次级和筛选级展示。
  3. 疑似重复票继续排除在合规金额之外。
- **验证**：`uv run --project backend --extra dev pytest backend/tests/test_export_service.py -q`、`corepack pnpm --dir frontend run build`

### Task 5.3 更新执行归档并完成 close-out

- **任务编号**：T53
- **优先级**：P0
- **依赖**：T51、T52
- **文件**：`specs/002-invoice-assistant-runtime-hardening/tasks.md`、`specs/002-invoice-assistant-runtime-hardening/task-execution-log.md`
- **可并行**：否
- **验收标准**：
  1. 执行日志完整记录各批次验证结果。
  2. 所有任务勾选状态与代码实际完成情况一致。
  3. `close-check` 可验证通过。
- **验证**：`python -m ai_sdlc workitem close-check --wi specs/002-invoice-assistant-runtime-hardening`
