---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "specs/001-invoice-assistant-mvp/spec.md"
---
# 实施计划：发票整理助手二期：真实解析与运行时加固

**编号**：`002-invoice-assistant-runtime-hardening` | **日期**：2026-04-17 | **规格**：`specs/002-invoice-assistant-runtime-hardening/spec.md`

## 概述

本计划用于把一期 MVP 的“夹具文本 + 同步串行处理”升级为“真实 PDF 解析 + 本地 OCR 兜底 + 异步可恢复运行时”。当前阶段先冻结二期 canonical 文档与任务边界；随后按批次推进真实解析 provider、持久化作业、恢复重试和前端诊断能力。

## 技术背景

- **语言 / 版本**：
  - 后端：Python 3.11+
  - 前端：TypeScript + React
- **主要依赖**：
  - 后端现状：FastAPI、SQLAlchemy、Pydantic、SQLite、Uvicorn、pytest
  - 二期预期新增：真实 PDF 文本抽取库、本地 OCR 适配依赖、异步任务协调所需的标准库或轻量组件
  - 前端现状：Vite、React、Ant Design、Vitest
- **存储**：SQLite + 本地文件系统
- **测试**：
  - 后端：`pytest`
  - 前端：构建检查 + 页面级测试
  - 框架治理：`python -m ai_sdlc gate ...`、`uv run ai-sdlc verify constraints`
- **目标平台**：macOS / Linux 本地环境，本机浏览器访问本地服务
- **关键约束**：
  - 单机、本地优先，不引入 Redis / Celery / PostgreSQL
  - 保持一期业务规则、金额统计、导出和人工复核语义不回退
  - 解析 provider 差异不得穿透统一证据模型边界

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Persist decisions to the repository | 二期正式决策只落在 `specs/002-invoice-assistant-runtime-hardening/` |
| Prefer contract-level verification before closure | 先完成 `refine / design / decompose / verify constraints`，再进入 execute 批次 |
| Keep docs and code traceable | 每个实现批次都回指 `spec.md`、`research.md`、`data-model.md` 与 `tasks.md` |

## 项目结构

### 文档结构

```text
specs/002-invoice-assistant-runtime-hardening/
├── spec.md
├── research.md
├── data-model.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 计划中的源码结构

```text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   └── services/
│       ├── parsing/
│       ├── rules/
│       └── ...
└── tests/

frontend/
├── src/
│   ├── api/
│   ├── components/
│   ├── pages/
│   └── types/
└── tests/
```

## 阶段计划

### Phase 0：文档冻结与 workitem 对齐

- **目标**：完成二期 canonical 规格、研究结论、数据模型、实施计划、任务拆解和执行日志基线。
- **产物**：`spec.md`、`research.md`、`data-model.md`、`plan.md`、`tasks.md`、`task-execution-log.md`
- **验证方式**：
  - `python -m ai_sdlc gate refine`
  - `python -m ai_sdlc gate design`
  - `python -m ai_sdlc gate decompose`
  - `uv run ai-sdlc verify constraints`
- **回退方式**：仅修改 `specs/002-invoice-assistant-runtime-hardening/` 与 workitem 关联状态，不触碰产品实现

### Phase 1：真实 PDF 文本抽取与 OCR fallback

- **目标**：接入真实 PDF 文本抽取 provider、本地 OCR fallback 与统一证据映射。
- **产物**：provider 接口、provider 实现、真实解析适配测试、OCR fallback 测试
- **验证方式**：provider 单元测试、真实样本解析测试
- **回退方式**：维持 adapter 边界，保留一期规则层与展示层不变

### Phase 2：持久化作业、异步执行与恢复

- **目标**：建立 `ProcessingJob` / `ProcessingAttempt`、后台 worker、恢复逻辑和幂等性保护。
- **产物**：作业表、attempt 表、后台执行服务、恢复服务、重试服务
- **验证方式**：批量处理集成测试、重启恢复测试、幂等性测试
- **回退方式**：以独立服务层接入现有 API，不影响已完成的业务规则逻辑

### Phase 3：进度诊断、失败重试与前端接入

- **目标**：让前端看到细粒度阶段、失败原因、provider 诊断，并支持单票 / 批次失败重试。
- **产物**：扩展进度 API、失败诊断 API、重试 API、前端状态展示与重试入口
- **验证方式**：API 测试、页面构建验证、手工走查
- **回退方式**：新增字段与入口均采用加法设计，保持旧字段兼容

### Phase 4：回归验证与收口

- **目标**：验证真实样本、扫描票、恢复重试、导出与金额统计口径全部稳定。
- **产物**：回归样本集、端到端验证记录、执行归档和 close-out 结果
- **验证方式**：后端全量测试、前端构建、手工样本走查、`close-check`
- **回退方式**：保留样本与诊断数据，按批次回退到上一稳定提交

## 工作流计划

### 工作流 A：真实解析到统一证据

- **范围**：真实 PDF 文本抽取、OCR fallback、统一证据模型映射
- **影响范围**：`backend/app/services/parsing/**`、`ProcessingService`、解析测试
- **验证方式**：电子票与扫描票样本测试、字段抽取测试
- **回退方式**：provider 层失败时统一落回结构化失败，不改动规则层语义

### 工作流 B：异步批处理与恢复

- **范围**：作业入队、后台 worker、心跳、恢复、重试、幂等性
- **影响范围**：数据库模型、服务协调器、批次 API、进度 API
- **验证方式**：批量集成测试、服务重启恢复测试、重复重试测试
- **回退方式**：作业与 attempt 独立建模，不直接覆盖主业务表历史

### 工作流 C：失败诊断、金额统计与导出兼容

- **范围**：失败详情、人类可读提示、详情页 provider 诊断、金额统计不回退、导出一致性
- **影响范围**：API 序列化、前端结果页 / 抽屉、导出服务
- **验证方式**：金额统计回归测试、导出结果对账、前端交互走查
- **回退方式**：保持原有汇总逻辑，以当前有效 `InvoiceRecord` 为唯一统计来源

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 文档阶段完整性 | `refine / design / decompose` gate | `uv run ai-sdlc verify constraints` |
| 真实电子票解析 | provider 单元测试 + 电子票样本测试 | 结果详情字段对账 |
| 扫描票 OCR fallback | OCR fallback 测试 | 手工样本走查 |
| 异步与恢复 | 批量集成测试 + 启停恢复测试 | 进度 API 轮询验证 |
| 重试幂等性 | attempt 级测试 | 导出 / 金额统计回归 |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 真实 PDF 文本抽取库与 OCR 引擎的具体版本 | 待 execute 时结合环境确认 | Phase 1 |
| 回归样本的脱敏与目录布局 | 待 execute 时落盘 | Phase 1 |
| 是否需要 OCR 图像预处理步骤 | 待真实样本验证后决定 | Phase 1 / 2 |

## 执行授权边界

1. 当前阶段仅冻结二期文档基线，不等于全部实现已完成。
2. 二期 execute 必须沿 `tasks.md` 的批次顺序推进，先接入真实解析，再加作业与恢复，再接前端诊断。
3. 任一批次提交前，都要验证不回退一期“合规票总金额、导出口径、人工复核留痕”的既有语义。

## 实施顺序建议

1. 先冻结二期文档并完成 workitem 关联与 gate 校验。
2. 再接入真实文本抽取与 OCR fallback，验证统一证据模型不变。
3. 然后补齐持久化作业、恢复和重试。
4. 最后扩展前端进度、失败诊断、重试入口并完成端到端回归。
