---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "docs/superpowers/specs/2026-04-24-invoice-assistant-ux-redesign.md"
  - "specs/010-finance-first-workflow-redesign/spec.md"
---
# 实施计划：财务优先工作流重设计
**编号**：`010-finance-first-workflow-redesign` | **日期**：2026-04-24 | **规格**：`specs/010-finance-first-workflow-redesign/spec.md`

## 概述

本期不是修单点 bug，而是把发票整理助手从“规则引擎前台”收回到“财务可独立操作的整理助手”。实现顺序遵循“先冻结契约，再上重 UI”的原则：
1. 先用 Phase 0 去掉最刺眼的技术化入口和错误等待态，避免继续伤害当前用户。
2. 再用 Phase 1 冻结 typed config、稳定状态、人工确认领域契约和兼容矩阵，先把后续实现的事实源定下来。
3. 最后在 Phase 2/3/4 基于已冻结契约重做配置中心、批次结果、人工确认、预览和导出主流程，避免二次重构。

## 技术背景
**语言/版本**：TypeScript / React，Python 3.11，FastAPI，SQLite  
**主要依赖**：Ant Design、Vitest / Playwright、Pydantic、SQLAlchemy  
**测试**：前端运行时 UI 测试、Playwright 浏览器回归、后端 pytest、AI-SDLC close-check / dry-run  
**目标平台**：Windows 离线服务包 + 本地浏览器  
**当前约束**：
- 当前项目已有首次配置表单、结果页、人工确认、导出和预览链路，需在现有代码基础上重构，不另起炉灶。
- 历史配置版本与历史批次数据必须可读兼容，但本期不回写历史数据。
- 旧导出能力与部分兼容接口可短期保留，但 UI 主流程必须统一到“另存为”。
- `python -m ai_sdlc workitem init` 在当前环境缺失模板文件，正式工单文档改为手工按既有 `specs/*` 结构维护。

## 宪章检查
| 宪章门禁 | 计划响应 |
|----------|----------|
| 范围可控，避免一轮内重写全部系统 | 按 Phase 0-4 拆分，优先用户感知最强的 P0 路径，再收敛模型与兼容层。 |
| 先证据后结论 | 以用户实测问题、现有代码审阅、浏览器回归和两名对抗 agent 合议作为输入，不凭空重构。 |
| 文档与代码一致 | `spec.md`、`plan.md`、`tasks.md`、`task-execution-log.md` 持续同步，阶段完成后补测试和收口证据。 |
| 保持回退路径 | 每个阶段都限定影响范围和回退策略，避免一次性替换全部接口或数据结构。 |

## 项目结构

### 文档结构

```text
specs/010-finance-first-workflow-redesign/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 预期源码结构

```text
frontend/src/pages/SetupWizard.tsx
frontend/src/pages/Settings.tsx
frontend/src/pages/BatchWorkbench.tsx
frontend/src/pages/BatchResults.tsx
frontend/src/components/settings/*
frontend/src/components/results/*
backend/app/api/config.py
backend/app/api/invoices.py
backend/app/services/config_service.py
backend/app/services/export_service.py
backend/app/services/status_service.py
backend/app/services/batch_service.py
backend/app/db/models.py
```

## 阶段计划

### Phase 0：体验止血

**目标**：先移除最刺眼的技术化入口和错误心智。
**产物**：
- 配置中心不再展示 JSON 编辑器；
- 结果页、详情页默认收起内部诊断字段；
- 人工确认文案改成财务动作语言；
- 批次处理中状态稳定显示。
**验证方式**：
- 前端运行时 UI 测试；
- Playwright 浏览器回归；
- 针对处理中状态与人工确认即时刷新补回归。
**回退方式**：
- 保留旧 API 契约；
- 只允许回退展示层，不回退用户已确认的业务语义边界。

### Phase 1：契约冻结与兼容矩阵

**目标**：先冻结后续 UI 依赖的领域契约，避免 Phase 2/3 再次返工。
**产物**：
- `ConfigBundle` 的唯一事实源、统一版本号规则、旧三版本映射规则；
- `StableInvoiceStatus` 的枚举、状态转移表和 `archive_status` 语义；
- 持久化 `ReviewQueueItem` 的最小领域契约；
- 兼容矩阵，明确旧字段/API 在兼容期内的读写角色与退场条件。
**验证方式**：
- 文档对读；
- 配置/状态/复核接口 schema 测试；
- 与前端类型定义对齐校验。
**回退方式**：
- 当前阶段不触发大规模 UI 切换；
- 仅允许回退草案，不允许在契约未冻结时进入重 UI 开发。

### Phase 2：配置中心重做

**目标**：统一首次配置与后续配置，并完全建立在 Phase 1 契约上。
**产物**：
- 共享字段表单组件；
- 配置中心四区块；
- 发布确认页；
- 历史变更只读视图。
**验证方式**：
- 配置中心组件测试；
- Playwright 回归测试首次配置与后续修改共用组件；
- 必要的后端 schema/接口测试。
**回退方式**：
- 保留旧配置读取兼容层；
- 如需回退，只回退新 UI，不回退已冻结的 typed contract。

### Phase 3：批次结果、人工确认与可用预览闭环

**目标**：让财务处理路径清晰可用，且人工确认不依赖盲审。
**产物**：
- 结果页按财务动作分组；
- 独立“待人工确认”入口；
- 人工确认后摘要、列表、详情即时同步；
- 本批次重复单独分组；
- 稳定 PDF 预览与原始文件入口。
**验证方式**：
- 结果页与人工确认的 Playwright 场景回归；
- 后端复核接口集成测试；
- 重复判定范围测试；
- 预览回归测试。
**回退方式**：
- 保留旧数据字段兼容；
- 如新页面有问题，可临时退回旧入口，但不恢复“历史批次判重”或“盲审确认”语义。

### Phase 4：导出主流程与兼容收口

**目标**：统一主流程边界，退出长期双轨兼容。
**产物**：
- “另存为”成为唯一主流程导出入口；
- 旧 `/exports` 流程降级为兼容层；
- 旧 `display_status`、旧 JSON 配置入口、旧 HTML 预览兼容层退场。
**验证方式**：
- 浏览器回归测试另存为；
- 导出接口测试；
- 离线包验收。
**回退方式**：
- 兼容期保留旧接口；
- UI 不恢复自动落盘入口。

## 工作流计划

### 工作流 A：契约与治理先行
**范围**：`ConfigBundle`、稳定状态、人工确认领域对象、兼容矩阵  
**影响范围**：`config.py`、`config_service.py`、`models.py`、`status_service.py`、`invoices.py` 及对应前端类型  
**验证方式**：schema/接口测试 + 文档对读  
**回退方式**：保持草案状态，不推进重 UI

### 工作流 B：配置心智统一
**范围**：首次配置、配置中心、历史版本、发布确认  
**影响范围**：`SetupWizard.tsx`、`Settings.tsx`、`frontend/src/components/settings/*`、配置相关 API 与服务  
**验证方式**：UI 组件测试 + Playwright 场景测试 + 配置接口测试  
**回退方式**：保留旧配置读取兼容层

### 工作流 C：批次结果、复核与预览闭环
**范围**：批次处理、结果页、待人工确认队列、详情抽屉、预览资源  
**影响范围**：`BatchWorkbench.tsx`、`BatchResults.tsx`、`InvoiceDrawer.tsx`、`ReviewActions.tsx`、复核/预览服务  
**验证方式**：Playwright 回归 + pytest 集成测试  
**回退方式**：必要时短期回退入口布局，但不恢复错误语义

### 工作流 D：导出与兼容退场
**范围**：另存为主流程、旧 `/exports`、旧 HTML 预览、旧显示状态兼容层  
**影响范围**：`export_service.py`、`invoices.py`、结果页导出入口、兼容映射层  
**验证方式**：后端测试 + 离线包验收  
**回退方式**：短期保留兼容接口，但不恢复自动落盘入口

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 后续配置不再编辑 JSON | Playwright 配置流回归 | 组件测试 + 人工验收 |
| 配置中心建立在统一 typed contract 上 | schema/接口测试 | 前端类型检查 |
| 批次处理中不秒报失败 | Playwright 批量上传回归 | API 状态轮询测试 |
| 人工确认后即时刷新 | Playwright 复核回归 | 复核接口集成测试 |
| 本批次重复，不看历史 | pytest 集成测试 | 手工双批次验收 |
| 不自动落盘，只另存为 | 浏览器下载回归 | 导出接口测试 |
| PDF 预览可用 | Playwright 预览回归 | 接口资源检查 |

## 兼容矩阵

| 旧对象/接口 | 兼容期角色 | 新的 canonical contract | 退场条件 |
|-------------|------------|-------------------------|----------|
| 旧配置 JSON 编辑入口 | 只读或隐藏，不再主写 | `ConfigBundle` 表单 + 发布确认 | Phase 2 稳定并完成离线包验收 |
| `tax_profile` / `business_rules` / `naming_rules` 独立版本流 | 内部拆分存储或只读映射 | `ConfigBundle.bundle_version_no` | 历史版本视图完成迁移验证 |
| `display_status` 中文展示状态 | 兼容读取，不再主判断 | `StableInvoiceStatus` + 前端派生文案 | Phase 3 全量回归通过 |
| 旧 `/exports` 自动落盘主流程 | 兼容接口，不再 UI 主入口 | “另存为”下载主流程 | Phase 4 离线包验收通过 |
| 旧 HTML 预览响应 | 兼容回退，不再默认主预览 | 预览资源接口 + 前端渲染 | Phase 4 预览回归稳定 |
| 历史 batch snapshot 中旧配置结构 | 只读兼容 | 批次持有 `ConfigBundle` 快照或等价映射 | 历史批次读取回归通过 |

## 开放问题
| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 审核策略是继续保留档位模式，还是增加少量高级选项 | 待 Phase 1 细化 | 不阻塞 Phase 0 |
| 人工确认是否需要批量通过/批量驳回 | 待 Phase 2 细化 | 不阻塞 Phase 1 |
| 兼容期旧 `/exports` 保留多久 | 待 Phase 4 收口时决定 | 不阻塞前序阶段 |

## 实施顺序建议

1. 先完成 Phase 0 和 Phase 1，先把错误体验止血，并冻结后续实现必须遵守的契约。
2. 再推进 Phase 2 和 Phase 3，在已冻结契约上重做配置中心、批次结果、人工确认和可用预览。
3. 最后完成 Phase 4，退出长期双轨兼容。
