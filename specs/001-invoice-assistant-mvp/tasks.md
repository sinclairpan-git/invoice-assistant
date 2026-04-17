---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 任务分解：发票整理助手一期 MVP

**编号**：`001-invoice-assistant-mvp` | **日期**：2026-04-17  
**来源**：`spec.md` + `research.md` + `data-model.md` + `plan.md`

## 分批策略

```text
Batch 1: 文档基线与框架对齐
Batch 2: 后端基础设施与存储骨架
Batch 3: 解析链路、规则判定与重命名
Batch 4: API、导出与批次可观察性
Batch 5: 前端工作台、结果页、配置中心
Batch 6: 端到端验证与交付收口
```

## 路径约定

- 后端：`backend/app/**`、`backend/tests/**`
- 前端：`frontend/src/**`、`frontend/tests/**`
- 正式文档：`specs/001-invoice-assistant-mvp/**`

## Batch 1：文档基线与框架对齐

- [x] T11 固化 canonical 规格与范围边界
- [x] T12 固化研究结论、数据模型和实施计划
- [x] T13 生成执行清单、执行日志并完成文档阶段校验

### Task 1.1 固化 canonical 规格与范围边界

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：specs/001-invoice-assistant-mvp/spec.md, docs/framework-defect-backlog.zh-CN.md
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确第一期覆盖范围、不覆盖范围、用户故事、功能需求和成功标准。
  2. 关键设计决策能追溯到 PRD 与辅助设计文档。
  3. 不再保留 `待补充`、错误技术栈或脚手架示例内容。
- **验证**：`python -m ai_sdlc gate refine`

### Task 1.2 固化研究结论、数据模型和实施计划

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：specs/001-invoice-assistant-mvp/research.md, specs/001-invoice-assistant-mvp/data-model.md, specs/001-invoice-assistant-mvp/plan.md
- **可并行**：否
- **验收标准**：
  1. `research.md` 明确第一期的关键技术选型与不采用方案。
  2. `data-model.md` 覆盖批次、发票、证据、规则版本、人工复核与导出对象。
  3. `plan.md` 明确阶段顺序、验证策略和 execute 授权边界。
- **验证**：`python -m ai_sdlc gate design`

### Task 1.3 生成执行清单、执行日志并完成文档阶段校验

- **任务编号**：T13
- **优先级**：P0
- **依赖**：T12
- **文件**：specs/001-invoice-assistant-mvp/tasks.md, specs/001-invoice-assistant-mvp/task-execution-log.md, .ai-sdlc/state/checkpoint.yml
- **可并行**：否
- **验收标准**：
  1. `tasks.md` 的每个 Task 块都包含依赖、文件、验收标准或验证字段。
  2. `task-execution-log.md` 记录本批文档冻结与验证过程。
  3. checkpoint 与当前 `specs/001-invoice-assistant-mvp/`、设计分支状态一致。
- **验证**：`python -m ai_sdlc gate decompose`、`python -m ai_sdlc recover --reconcile`、`python -m ai_sdlc verify constraints`

## Batch 2：后端基础设施与存储骨架

- [x] T21 建立 FastAPI 后端骨架与 SQLite 数据模型
- [x] T22 建立批次文件存储、原始文件落盘和规则快照写入
- [x] T23 建立配置中心版本表与审计日志

### Task 2.1 建立 FastAPI 后端骨架与 SQLite 数据模型

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T13
- **文件**：backend/pyproject.toml, backend/app/main.py, backend/app/db/models.py, backend/tests/test_app_boot.py
- **可并行**：否
- **验收标准**：
  1. 后端可启动并暴露健康检查接口。
  2. 数据库模型覆盖 `Batch`、`InvoiceRecord`、`DocumentEvidence`、`RuleVersion`、`ReviewAction`、`ExportJob`。
  3. 基础测试可验证应用启动和数据库初始化。
- **验证**：`pytest backend/tests/test_app_boot.py -q`

### Task 2.2 建立批次文件存储、原始文件落盘和规则快照写入

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：backend/app/services/storage_service.py, backend/app/services/batch_service.py, backend/tests/test_batch_storage.py
- **可并行**：否
- **验收标准**：
  1. 上传批次时原始文件落盘到 `storage/originals/<batch_no>/`。
  2. 批次记录能保存规则版本与快照。
  3. 重复导入和非法文件类型有明确失败路径。
- **验证**：`pytest backend/tests/test_batch_storage.py -q`

### Task 2.3 建立配置中心版本表与审计日志

- **任务编号**：T23
- **优先级**：P0
- **依赖**：T21
- **文件**：backend/app/services/config_service.py, backend/app/db/models.py, backend/tests/test_config_versioning.py
- **可并行**：是
- **验收标准**：
  1. 配置更新生成新版本，不覆盖旧记录。
  2. 审计日志记录变更人、变更时间、变更摘要和变更原因。
  3. 批次创建时能绑定最新生效版本。
- **验证**：`pytest backend/tests/test_config_versioning.py -q`

## Batch 3：解析链路、规则判定与重命名

- [x] T31 建立统一证据模型与解析适配层
- [x] T32 实现购方校验、风险分类和疑似重复检测
- [x] T33 实现重命名与派生显示状态

### Task 3.1 建立统一证据模型与解析适配层

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T22
- **文件**：backend/app/services/parsing/evidence_models.py, backend/app/services/parsing/providers.py, backend/tests/test_document_evidence.py
- **可并行**：否
- **验收标准**：
  1. 文本提取和 OCR 输出都能转换成统一 `DocumentEvidence`。
  2. 证据模型记录来源、供应商信息、字段候选和置信度摘要。
  3. 解析失败能输出结构化错误。
- **验证**：`pytest backend/tests/test_document_evidence.py -q`

### Task 3.2 实现购方校验、风险分类和疑似重复检测

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31, T23
- **文件**：backend/app/services/rules/buyer_validation.py, backend/app/services/rules/risk_classifier.py, backend/app/services/rules/duplicate_detector.py, backend/tests/test_rules_pipeline.py
- **可并行**：否
- **验收标准**：
  1. 高置信购方字段不一致时输出 `suggested_reject`。
  2. 模糊明细、低置信或混合票降级为 `review_required`。
  3. 疑似重复票会被单独标记并排除出建议通过统计。
- **验证**：`pytest backend/tests/test_rules_pipeline.py -q`

### Task 3.3 实现重命名与派生显示状态

- **任务编号**：T33
- **优先级**：P1
- **依赖**：T32
- **文件**：backend/app/services/naming_service.py, backend/app/services/status_service.py, backend/tests/test_naming_and_display_status.py
- **可并行**：是
- **验收标准**：
  1. 默认命名模板为 `YYYYMMDD_金额_发票号码.pdf`。
  2. 缺少关键字段时跳过重命名并记录原因。
  3. `display_status` 派生逻辑与 spec 中的优先级一致。
- **验证**：`pytest backend/tests/test_naming_and_display_status.py -q`

## Batch 4：API、导出与批次可观察性

- [x] T41 暴露批次、结果、详情和配置 API
- [x] T42 实现 ZIP / Excel 导出
- [x] T43 建立批次进度与错误可观察性

### Task 4.1 暴露批次、结果、详情和配置 API

- **任务编号**：T41
- **优先级**：P0
- **依赖**：T32
- **文件**：backend/app/api/batches.py, backend/app/api/invoices.py, backend/app/api/config.py, backend/tests/test_api_workflows.py
- **可并行**：否
- **验收标准**：
  1. 前端可读取批次列表、批次详情、结果筛选和配置项。
  2. 详情接口返回字段证据、校验结果、风险依据和疑似重复依据。
  3. 人工复核接口只写留痕，不覆盖系统判定。
- **验证**：`pytest backend/tests/test_api_workflows.py -q`

### Task 4.2 实现 ZIP / Excel 导出

- **任务编号**：T42
- **优先级**：P1
- **依赖**：T33, T41
- **文件**：backend/app/services/export_service.py, backend/tests/test_export_service.py
- **可并行**：是
- **验收标准**：
  1. 可导出系统建议通过 ZIP、问题票 ZIP 和 Excel 台账。
  2. 导出统计口径与结果页一致。
  3. 导出结果记录到 `ExportJob`。
- **验证**：`pytest backend/tests/test_export_service.py -q`

### Task 4.3 建立批次进度与错误可观察性

- **任务编号**：T43
- **优先级**：P1
- **依赖**：T41
- **文件**：backend/app/services/progress_service.py, backend/app/core/logging.py, backend/tests/test_progress_reporting.py
- **可并行**：是
- **验收标准**：
  1. 批次工作台能读取实时进度与阶段文案。
  2. 失败记录包含可展示的失败原因。
  3. 关键后台动作有可追溯日志。
- **验证**：`pytest backend/tests/test_progress_reporting.py -q`

## Batch 5：前端工作台、结果页、配置中心

- [x] T51 建立前端工程骨架与路由
- [x] T52 交付批次工作台和进度展示
- [x] T53 交付结果页、详情抽屉和金额汇总
- [x] T54 交付配置中心和人工复核交互

### Task 5.1 建立前端工程骨架与路由

- **任务编号**：T51
- **优先级**：P0
- **依赖**：T41
- **文件**：frontend/package.json, frontend/src/app/router.tsx, frontend/src/app/providers.tsx, frontend/tests/app-shell.test.tsx
- **可并行**：否
- **验收标准**：
  1. 前端可本地启动并连接后端 API。
  2. 建立批次工作台、结果页、配置中心的基础路由。
  3. 统一错误态、加载态和页面布局骨架。
- **验证**：`corepack pnpm --dir frontend run build`

### Task 5.2 交付批次工作台和进度展示

- **任务编号**：T52
- **优先级**：P0
- **依赖**：T51, T43
- **文件**：frontend/src/pages/BatchWorkbench.tsx, frontend/src/components/batch/UploadPanel.tsx, frontend/src/components/batch/BatchList.tsx
- **可并行**：否
- **验收标准**：
  1. 首页以批次工作台为主，而不是纯上传页。
  2. 最近批次列表能展示总文件数、完成数、失败数、系统建议通过数量与金额。
  3. 活跃批次能展示阶段进度和状态文案。
- **验证**：`corepack pnpm --dir frontend run build`

### Task 5.3 交付结果页、详情抽屉和金额汇总

- **任务编号**：T53
- **优先级**：P0
- **依赖**：T52, T41, T42
- **文件**：frontend/src/pages/BatchResults.tsx, frontend/src/components/results/ResultTable.tsx, frontend/src/components/results/InvoiceDrawer.tsx
- **可并行**：否
- **验收标准**：
  1. 结果页支持按显示状态筛选。
  2. 顶部展示批次系统建议通过金额和当前筛选下系统建议通过金额。
  3. 详情抽屉展示字段证据、购方校验、风险依据、疑似重复依据和人工复核入口。
- **验证**：`corepack pnpm --dir frontend run build`

### Task 5.4 交付配置中心和人工复核交互

- **任务编号**：T54
- **优先级**：P1
- **依赖**：T51, T41
- **文件**：frontend/src/pages/Settings.tsx, frontend/src/components/settings/RuleVersionPanel.tsx, frontend/src/components/results/ReviewActions.tsx
- **可并行**：是
- **验收标准**：
  1. 配置中心能编辑税务档案、风险规则、命名模板和默认操作者名。
  2. 历史版本和变更日志可查看。
  3. 人工复核动作和备注可从详情抽屉发起。
- **验证**：`corepack pnpm --dir frontend run build`

## Batch 6：端到端验证与交付收口

- [ ] T61 准备样例数据并跑通核心流程
- [ ] T62 完成交付文档、执行归档与 close 前检查

### Task 6.1 准备样例数据并跑通核心流程

- **任务编号**：T61
- **优先级**：P0
- **依赖**：T53, T54
- **文件**：backend/tests/fixtures/invoices/, backend/tests/test_end_to_end_batch.py, frontend/tests/manual-checklist.md
- **可并行**：否
- **验收标准**：
  1. 至少覆盖标准电子票、扫描票、待复核票和疑似重复票样例。
  2. 核心流程从上传到导出可跑通。
  3. 页面统计、导出结果和数据库状态一致。
- **验证**：`pytest backend/tests/test_end_to_end_batch.py -q`

### Task 6.2 完成交付文档、执行归档与 close 前检查

- **任务编号**：T62
- **优先级**：P0
- **依赖**：T61
- **文件**：specs/001-invoice-assistant-mvp/task-execution-log.md, specs/001-invoice-assistant-mvp/tasks.md, docs/pull-request-checklist.zh.md
- **可并行**：否
- **验收标准**：
  1. `task-execution-log.md` 归档每个已完成批次的命令、测试和结论。
  2. `tasks.md` 与实际完成情况一致。
  3. `python -m ai_sdlc workitem close-check --wi specs/001-invoice-assistant-mvp` 无阻塞项。
- **验证**：`python -m ai_sdlc workitem close-check --wi specs/001-invoice-assistant-mvp`

## 依赖与执行顺序

### 阶段依赖

- Batch 1 → Batch 2 → Batch 3 → Batch 4 → Batch 5 → Batch 6

### 可并行机会

- `T23` 可与 `T22` 部分并行，但都依赖 `T21`
- `T33` 可在规则核心稳定后独立推进
- `T42` 与 `T43` 可在 API 基础完成后并行
- `T54` 可在前端骨架完成后与结果页部分并行

## 实施策略

### MVP 优先

1. 先完成 Batch 1 文档冻结。
2. 再完成 Batch 2 和 Batch 3，把后端主链路跑通。
3. 随后交付 Batch 4 和 Batch 5 的对外可用界面。
4. 最后用 Batch 6 做端到端验证和收口。

### 渐进式交付

1. 批次可创建
2. 发票可解析和判定
3. 结果可查看和导出
4. 配置与人工复核可留痕
5. 端到端可复现
