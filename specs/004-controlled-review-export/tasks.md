---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "specs/001-invoice-assistant-mvp/spec.md"
  - "specs/003-runtime-state-recovery/spec.md"
---
# 任务分解：发票整理助手四期：受控复核与导出闭环

**编号**：`004-controlled-review-export` | **日期**：2026-04-18  
**来源**：`spec.md` + `plan.md`

## 分批策略

```text
Batch 1: 四期文档基线与治理边界冻结
Batch 2: 红灯回归 + 可信身份与角色控制实现
Batch 3: 单票结果字段、导出门槛与审计落地
Batch 4: 验证归档与 branch close-out 准备
```

## 路径约定

- 后端：`backend/app/**`、`backend/tests/**`
- 前端：`frontend/src/**`、`frontend/tests/**`
- 正式文档：`specs/004-controlled-review-export/**`

## Batch 1：四期文档基线与治理边界冻结

- [x] T11 固化四期规格与范围边界
- [x] T12 固化四期实施计划与验证策略
- [x] T13 建立四期任务批次与执行日志基线

### Task 1.1 固化四期规格与范围边界

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：`specs/004-controlled-review-export/spec.md`
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确四期仅覆盖可信身份、角色权限、单票解释层和导出门槛。
  2. 文档清楚写明导出门槛与审计要求。
  3. 不保留脚手架占位文本。
- **验证**：文档自检

### Task 1.2 固化四期实施计划与验证策略

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：`specs/004-controlled-review-export/plan.md`
- **可并行**：否
- **验收标准**：
  1. `plan.md` 明确红灯测试先行。
  2. 计划能追溯到可信身份、角色控制、结果字段和导出门槛四条主线。
  3. 计划不引入超出四期范围的登录系统扩张。
- **验证**：文档自检

### Task 1.3 建立四期任务批次与执行日志基线

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T12
- **文件**：`specs/004-controlled-review-export/tasks.md`、`specs/004-controlled-review-export/task-execution-log.md`
- **可并行**：否
- **验收标准**：
  1. `tasks.md` 将四期拆成“身份/权限”“结果/导出”“验证/归档”三类实现批次。
  2. 执行日志能记录本次文档冻结、后续红灯测试、实现修改和验证命令。
  3. 本批只记录已完成的文档动作，不提前写入实现结果。
- **验证**：执行归档自检

## Batch 2：红灯回归 + 可信身份与角色控制实现

- [x] T21 后端红灯测试覆盖可信身份派生与角色拒绝
- [x] T22 前端红灯测试覆盖操作者只读展示与自由输入移除
- [x] T23 实现后端可信身份上下文与受控 API 入参

### Task 2.1 后端红灯测试覆盖可信身份派生与角色拒绝

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T12
- **文件**：`backend/tests/test_api_workflows.py`
- **可并行**：是
- **验收标准**：
  1. 用例先暴露当前接口仍接受 `created_by` / `reviewed_by` / `changed_by` 的缺口。
  2. 用例覆盖缺少 `config_admin`、`reviewer`、`exporter` 角色时返回 `403`。
  3. 用例覆盖受控动作的审计写入。
- **验证**：`uv run --project backend --extra dev python -m pytest backend/tests/test_api_workflows.py -q`

### Task 2.2 前端红灯测试覆盖操作者只读展示与自由输入移除

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T12
- **文件**：`frontend/tests/app-shell.test.tsx`、`frontend/tests/runtime-ui.test.tsx`
- **可并行**：是
- **验收标准**：
  1. 用例先暴露当前设置页 / 上传 / 复核仍依赖本地默认操作者输入的缺口。
  2. 用例验证界面展示后端当前操作者，而不是本地自由输入值。
  3. 用例不依赖手工修改 localStorage。
- **验证**：`npm test -- tests/app-shell.test.tsx tests/runtime-ui.test.tsx`（在 `frontend/` 目录执行）

### Task 2.3 实现后端可信身份上下文与受控 API 入参

- **任务编号**：T23
- **优先级**：P0
- **依赖**：T21、T22
- **文件**：`backend/app/api/dependencies.py`、`backend/app/api/batches.py`、`backend/app/api/invoices.py`、`backend/app/api/config.py`、`frontend/src/app/api.ts`、`frontend/src/app/shell.tsx`、`frontend/src/app/operator-settings.tsx`
- **可并行**：否
- **验收标准**：
  1. 前端不再提交自由输入操作者字段。
  2. 后端从可信上下文派生操作者信息写入批次、复核、规则版本和导出记录。
  3. 受控接口缺角色时稳定返回 `403` 并写入审计。
- **验证**：`uv run --project backend --extra dev python -m pytest backend/tests/test_api_workflows.py -q`、`npm test -- tests/app-shell.test.tsx tests/runtime-ui.test.tsx`（在 `frontend/` 目录执行）

## Batch 3：单票结果字段、导出门槛与审计落地

- [x] T31 红灯测试覆盖单票结果字段和导出门槛
- [x] T32 实现单票解释层、导出台账字段和导出门槛

### Task 3.1 红灯测试覆盖单票结果字段和导出门槛

- **任务编号**：T31
- **优先级**：P0
- **依赖**：T23
- **文件**：`backend/tests/test_export_service.py`、`backend/tests/test_end_to_end_batch.py`
- **可并行**：是
- **验收标准**：
  1. 用例先暴露当前详情和 manifest 缺少基础合规 / 业务合规 / 原因 / 建议动作字段。
  2. 用例覆盖 `suggested_pass_zip` 在存在待复核票据时必须被拒绝。
  3. 用例覆盖导出成功和导出拒绝的审计差异。
- **验证**：`uv run --project backend --extra dev python -m pytest backend/tests/test_export_service.py backend/tests/test_end_to_end_batch.py -q`

### Task 3.2 实现单票解释层、导出台账字段和导出门槛

- **任务编号**：T32
- **优先级**：P0
- **依赖**：T31
- **文件**：`backend/app/api/serializers.py`、`backend/app/services/export_service.py`、`backend/app/db/models.py`、`frontend/src/app/types.ts`、`frontend/src/components/results/InvoiceDrawer.tsx`、`frontend/src/pages/BatchResults.tsx`
- **可并行**：否
- **验收标准**：
  1. 单票摘要 / 详情 / manifest 共用同一套财务解释字段。
  2. `suggested_pass_zip`、`issue_zip`、`excel_manifest` 的门槛和拒绝原因符合四期规格。
  3. 导出成功与拒绝都能在审计中体现门槛判断结果。
- **验证**：`uv run --project backend --extra dev python -m pytest backend/tests/test_export_service.py backend/tests/test_end_to_end_batch.py -q`

## Batch 4：验证归档与 branch close-out 准备

- [x] T41 更新执行日志与任务勾选
- [x] T42 完成框架验证与工作区收口检查

### Task 4.1 更新执行日志与任务勾选

- **任务编号**：T41
- **优先级**：P1
- **依赖**：T32
- **文件**：`specs/004-controlled-review-export/task-execution-log.md`、`specs/004-controlled-review-export/tasks.md`
- **可并行**：否
- **验收标准**：
  1. 记录红灯、实现、验证三类命令和结果。
  2. 勾选状态与实际完成项一致。
  3. 不把未执行的 close-out 动作写成已完成。
- **验证**：执行归档自检

### Task 4.2 完成框架验证与工作区收口检查

- **任务编号**：T42
- **优先级**：P1
- **依赖**：T41
- **文件**：工作区状态与必要的 framework 记录
- **可并行**：否
- **验收标准**：
  1. 定向回归通过后再执行必要的框架检查。
  2. 工作区状态可解释，不包含与四期无关的意外修改。
  3. 为后续分支归档 / 合并准备清晰的收口说明。
- **验证**：`python -m ai_sdlc run --dry-run`、`git status --short`
