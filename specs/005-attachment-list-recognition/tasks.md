---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "specs/001-invoice-assistant-mvp/spec.md"
  - "specs/004-controlled-review-export/spec.md"
---
# 任务分解：清单附件识别闭环

**编号**：`005-attachment-list-recognition` | **日期**：2026-04-18
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: 文档基线冻结
Batch 2: 上传入口与数据模型
Batch 3: 附件解析、匹配与分类
Batch 4: 结果展示与导出对齐
Batch 5: 回归验证与收口
```

---

## Batch 1：文档基线冻结

### Task 1.1 替换 005 占位 spec 为正式业务范围

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确覆盖范围、非目标、用户故事、功能需求与成功标准。
  2. 005 不再保留脚手架占位文案或与实际产品无关的任务描述。
- **验证**：文档对账
- **状态**：已完成

### Task 1.2 固化实施计划与批次顺序

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：plan.md
- **可并行**：否
- **验收标准**：
  1. `plan.md` 明确技术背景、关键工作流、验证策略和开放问题。
  2. 实施顺序能直接指导后续 execute，而不是再次做范围讨论。
- **验证**：文档对账
- **状态**：已完成

### Task 1.3 建立真实执行日志骨架

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T11
- **文件**：task-execution-log.md
- **可并行**：是
- **验收标准**：
  1. 归档规则保持与项目规范一致。
  2. 首批日志准确记录 work item 初始化、分支切换与文档基线修正。
- **验证**：文档对账
- **状态**：已完成

## Batch 2：上传入口与数据模型

### Task 2.1 为批次文件建立附件候选类型与持久化结构

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：`backend/app/db/models.py`, `backend/app/services/batch_service.py`, 相关迁移/测试文件
- **可并行**：否
- **验收标准**：
  1. 批次内能区分主发票文件和清单附件文件。
  2. 附件文件的原始信息、解析状态和主发票关联字段可落库。
- **验证**：`python -m pytest backend/tests/test_batch_service.py -q`
- **状态**：未开始

### Task 2.2 扩展批次创建 API 与前端上传协议

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：`backend/app/api/batches.py`, `backend/app/api/serializers.py`, `frontend/src/app/api.ts`, `frontend/src/components/batch/UploadPanel.tsx`
- **可并行**：否
- **验收标准**：
  1. 混合上传主发票与附件时，API 能正确接收、创建批次并返回附件状态。
  2. 前端上传面板对附件能力有最小可用提示，不要求用户先做人工关联。
- **验证**：`python -m pytest backend/tests/test_batch_api.py -q`，`npm test -- UploadPanel`
- **状态**：未开始

## Batch 3：附件解析、匹配与分类

### Task 3.1 为清单附件补充解析与匹配规则

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T21
- **文件**：`backend/app/services/processing_service.py`, `backend/app/services/parsing/*`, 相关测试夹具
- **可并行**：否
- **验收标准**：
  1. 清单附件能生成统一证据摘要，并尝试匹配到主发票。
  2. 匹配失败时会记录明确原因，而不是丢失附件上下文。
- **验证**：`python -m pytest backend/tests/test_processing_service.py -q`
- **状态**：未开始

### Task 3.2 让风险分类器消费附件证据

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31
- **文件**：`backend/app/services/rules/risk_classifier.py`, `backend/tests/test_rules_pipeline.py`
- **可并行**：否
- **验收标准**：
  1. 对“详见清单”主票，系统会优先检查可信附件证据。
  2. 附件足够可信时复用既有通过/拒绝规则；不足时保留 `review_required` 并写明原因。
- **验证**：`python -m pytest backend/tests/test_rules_pipeline.py -q`
- **状态**：未开始

## Batch 4：结果展示与导出对齐

### Task 4.1 扩展结果 API、详情抽屉与导出摘要

- **任务编号**：T41
- **优先级**：P1
- **依赖**：T32
- **文件**：`backend/app/api/serializers.py`, `backend/app/services/export_service.py`, `frontend/src/app/types.ts`, `frontend/src/components/results/InvoiceDrawer.tsx`
- **可并行**：否
- **验收标准**：
  1. 发票详情能看到附件状态、命中依据和失败原因。
  2. 导出摘要包含精简的附件识别结论，不破坏 004 的角色控制与字段边界。
- **验证**：`python -m pytest backend/tests/test_export_service.py -q`，`npm test -- InvoiceDrawer`
- **状态**：未开始

### Task 4.2 补齐前端混合上传与结果态提示

- **任务编号**：T42
- **优先级**：P1
- **依赖**：T22, T41
- **文件**：`frontend/src/pages/BatchWorkbench.tsx`, `frontend/src/pages/BatchResults.tsx`, 相关测试文件
- **可并行**：是
- **验收标准**：
  1. 用户能在上传和结果页理解哪些附件已匹配、哪些仍待处理。
  2. 新增状态不会挤占现有批次关键指标。
- **验证**：`npm test -- BatchWorkbench BatchResults`
- **状态**：未开始

## Batch 5：回归验证与收口

### Task 5.1 完成定向回归与 dry-run 收口

- **任务编号**：T51
- **优先级**：P0
- **依赖**：T42
- **文件**：测试与文档归档文件
- **可并行**：否
- **验收标准**：
  1. 005 相关定向测试通过。
  2. `python -m ai_sdlc run --dry-run` 通过，且无附件主路径回归不退化。
- **验证**：`python -m pytest backend/tests -q`，`npm test`，`python -m ai_sdlc run --dry-run`
- **状态**：未开始
