---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "specs/002-invoice-assistant-runtime-hardening/spec.md"
---
# 实施计划：发票整理助手三期：运行时状态与恢复闭环

**编号**：`003-runtime-state-recovery` | **日期**：2026-04-18 | **规格**：`specs/003-runtime-state-recovery/spec.md`

## 概述

本计划用于对二期已完成的异步处理运行时做一次小范围收口。目标不是增加新能力，而是把“阶段语义一致、恢复后界面可见、最近失败窗口可控”这三处缺口补齐，并用回归测试锁定。

## 技术背景

- **语言 / 版本**：
  - 后端：Python 3.11+
  - 前端：TypeScript + React
- **主要依赖**：
  - 后端：FastAPI、SQLAlchemy、pytest
  - 前端：Vite、React、Vitest、Ant Design
- **存储**：SQLite + 本地文件系统
- **测试**：
  - 后端：`uv run pytest backend/tests/test_progress_reporting.py backend/tests/test_processing_recovery.py -q`
  - 前端：`npm test -- tests/runtime-ui.test.tsx`（在 `frontend/` 目录执行）
  - 框架治理：`python -m ai_sdlc run --dry-run`
- **目标平台**：本地单机运行环境
- **关键约束**：
  - 不改业务规则、导出口径、复核留痕与权限边界。
  - 不引入新的恢复机制；只在现有 `ProgressService`、`RecoveryService` 和工作台页面上收口。
  - 先写失败回归，再做实现修改。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Persist decisions to the repository | 三期范围、任务和执行记录全部落在 `specs/003-runtime-state-recovery/` |
| Prefer contract-level verification before closure | 以前后端回归测试作为收口主证据，再更新执行日志 |
| Keep docs and code traceable | 文档任务直接映射到 `progress_service.py`、`BatchWorkbench.tsx` 与对应测试文件 |

## 项目结构

### 文档结构

```text
specs/003-runtime-state-recovery/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 本次实现涉及的源码结构

```text
backend/
├── app/services/progress_service.py
└── tests/
    ├── test_progress_reporting.py
    └── test_processing_recovery.py

frontend/
├── src/pages/BatchWorkbench.tsx
└── tests/runtime-ui.test.tsx
```

## 阶段计划

### Phase 0：文档冻结与红灯回归

- **目标**：冻结三期范围、任务和验证口径，并写出当前会失败的回归测试。
- **产物**：`spec.md`、`plan.md`、`tasks.md`、红灯测试用例
- **验证方式**：文档自检 + 定向测试确认红灯
- **回退方式**：仅修改文档和测试，不变更生产逻辑

### Phase 1：运行时状态与最近失败窗口修复

- **目标**：收口活跃阶段集合、修正工作台活跃批次识别，并限制最近失败窗口。
- **产物**：前端活跃判定逻辑、后端最近失败裁剪与排序实现
- **验证方式**：前后端定向回归测试
- **回退方式**：改动限定在进度聚合和页面消费层，不触碰解析与规则链路

### Phase 2：验证、归档与收口

- **目标**：完成定向回归、更新任务与执行日志，确认 work item 进入可收口状态。
- **产物**：通过的测试记录、`task-execution-log.md` 更新、`tasks.md` 勾选
- **验证方式**：定向测试 + 必要的框架验证
- **回退方式**：若验证失败，仅回退三期局部改动，不影响二期主链路

## 工作流计划

### 工作流 A：工作台活跃批次判定收口

- **范围**：`BatchWorkbench.tsx` 与前端测试
- **影响范围**：活跃批次显示、自动轮询触发条件、失败重试入口可见性
- **验证方式**：`frontend/tests/runtime-ui.test.tsx`
- **回退方式**：恢复为原页面逻辑，不影响结果页和详情页

### 工作流 B：进度快照最近失败窗口收口

- **范围**：`ProgressService` 与后端测试
- **影响范围**：进度接口载荷规模、最近失败排序与数量
- **验证方式**：`backend/tests/test_progress_reporting.py`
- **回退方式**：恢复现有快照序列化逻辑，不影响底层处理 attempt 数据

### 工作流 C：恢复链路可见性回归

- **范围**：恢复测试与阶段语义核对
- **影响范围**：服务启动恢复后的批次可见性结论
- **验证方式**：`backend/tests/test_processing_recovery.py`
- **回退方式**：仅移除新增断言，不影响恢复机制本身

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 细粒度阶段仍被识别为活跃 | `frontend/tests/runtime-ui.test.tsx` | 工作台代码走查 |
| 最近失败窗口裁剪与排序 | `backend/tests/test_progress_reporting.py` | 进度服务日志与快照断言 |
| 恢复后批次仍具活跃语义 | `backend/tests/test_processing_recovery.py` | `ProgressService` 快照断言 |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 最近失败窗口的固定上限是否需要配置化 | 当前按常量 3 收口，不阻塞实现 | Phase 1 |
| 是否在后续引入专门的失败历史接口 | 明确不在三期范围内 | 不阻塞 |

## 执行授权边界

1. 三期只做运行时状态闭环，不顺带扩展财务治理、审批和权限需求。
2. 所有实现先由红灯回归界定，再进入生产代码修改。
3. 完成代码修改后必须同步更新 `tasks.md` 和执行归档，保持 work item 真值一致。

## 实施顺序建议

1. 先冻结三期文档与任务边界。
2. 再补前端和后端红灯测试，锁定当前缺口。
3. 然后实现活跃阶段集合和最近失败窗口修复。
4. 最后跑定向回归并更新执行归档。
