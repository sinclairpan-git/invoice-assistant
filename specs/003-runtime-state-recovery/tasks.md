---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "specs/002-invoice-assistant-runtime-hardening/spec.md"
---
# 任务分解：发票整理助手三期：运行时状态与恢复闭环

**编号**：`003-runtime-state-recovery` | **日期**：2026-04-18  
**来源**：`spec.md` + `plan.md`

## 分批策略

```text
Batch 1: 三期文档基线与收口边界冻结
Batch 2: 红灯回归 + 运行时状态闭环实现
Batch 3: 验证归档与 branch close-out 准备
```

## 路径约定

- 后端：`backend/app/**`、`backend/tests/**`
- 前端：`frontend/src/**`、`frontend/tests/**`
- 正式文档：`specs/003-runtime-state-recovery/**`

## Batch 1：三期文档基线与收口边界冻结

- [x] T11 固化三期规格与范围边界
- [x] T12 固化三期实施计划与验证策略
- [x] T13 建立三期执行日志基线

### Task 1.1 固化三期规格与范围边界

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：`specs/003-runtime-state-recovery/spec.md`
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确三期仅覆盖运行时状态与恢复闭环。
  2. 文档清楚写明活跃阶段收口、最近失败窗口和恢复可见性三条主线。
  3. 不保留脚手架占位文本。
- **验证**：文档自检

### Task 1.2 固化三期实施计划与验证策略

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：`specs/003-runtime-state-recovery/plan.md`
- **可并行**：否
- **验收标准**：
  1. `plan.md` 明确红灯测试先行。
  2. 计划能追溯到前端工作台、进度聚合和恢复回归三处实现面。
  3. 计划不引入超出三期范围的新基础设施或新产品面。
- **验证**：文档自检

### Task 1.3 建立三期执行日志基线

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T12
- **文件**：`specs/003-runtime-state-recovery/task-execution-log.md`
- **可并行**：否
- **验收标准**：
  1. 执行日志能记录本次红灯测试、实现修改和验证命令。
  2. 日志与 `tasks.md` 勾选状态保持一致。
  3. 本批未完成前，不提前写入“已完成提交”结论。
- **验证**：执行归档自检

## Batch 2：红灯回归 + 运行时状态闭环实现

- [x] T21 前端红灯测试覆盖细粒度活跃阶段
- [x] T22 后端红灯测试覆盖最近失败窗口上限与排序
- [x] T23 实现活跃阶段收口与最近失败窗口修复

### Task 2.1 前端红灯测试覆盖细粒度活跃阶段

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T12
- **文件**：`frontend/tests/runtime-ui.test.tsx`
- **可并行**：是
- **验收标准**：
  1. 构造 `text_extraction` 或 `recovering` 阶段批次时，当前实现先暴露空态判定缺口。
  2. 用例直接验证工作台出现活跃条带而不是空态。
  3. 用例不依赖额外手工操作。
- **验证**：`npm test -- tests/runtime-ui.test.tsx`（在 `frontend/` 目录执行）

### Task 2.2 后端红灯测试覆盖最近失败窗口上限与排序

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T12
- **文件**：`backend/tests/test_progress_reporting.py`
- **可并行**：是
- **验收标准**：
  1. 构造超过 3 张失败票时，当前实现先暴露全量返回缺口。
  2. 用例验证 `recent_failures` 仅返回最近 3 条。
  3. 用例验证最近失败按 attempt 时间倒序排列。
- **验证**：`uv run pytest backend/tests/test_progress_reporting.py -q`

### Task 2.3 实现活跃阶段收口与最近失败窗口修复

- **任务编号**：T23
- **优先级**：P0
- **依赖**：T21、T22
- **文件**：`frontend/src/pages/BatchWorkbench.tsx`、`backend/app/services/progress_service.py`、`backend/tests/test_processing_recovery.py`
- **可并行**：否
- **验收标准**：
  1. 工作台能识别细粒度处理中阶段和恢复态为活跃批次。
  2. 进度快照只返回最近 3 条失败记录，并按最近失败排序。
  3. 恢复回归继续通过，证明三期修复未破坏已有启动恢复能力。
- **验证**：`npm test -- tests/runtime-ui.test.tsx`（在 `frontend/` 目录执行）、`uv run pytest backend/tests/test_progress_reporting.py backend/tests/test_processing_recovery.py -q`

## Batch 3：验证归档与 branch close-out 准备

- [x] T31 更新执行日志与任务勾选
- [x] T32 完成框架验证与工作区收口检查

### Task 3.1 更新执行日志与任务勾选

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T23
- **文件**：`specs/003-runtime-state-recovery/task-execution-log.md`、`specs/003-runtime-state-recovery/tasks.md`
- **可并行**：否
- **验收标准**：
  1. 记录红灯、实现、验证三类命令和结果。
  2. 勾选状态与实际完成项一致。
  3. 不把未执行的 close-out 动作写成已完成。
- **验证**：执行归档自检

### Task 3.2 完成框架验证与工作区收口检查

- **任务编号**：T32
- **优先级**：P1
- **依赖**：T31
- **文件**：工作区状态与必要的 framework 记录
- **可并行**：否
- **验收标准**：
  1. 定向回归通过后再执行必要的框架检查。
  2. 工作区状态可解释，不包含与三期无关的意外修改。
  3. 为后续分支归档 / 合并准备清晰的收口说明。
- **验证**：`python -m ai_sdlc run --dry-run`、`git status --short`
