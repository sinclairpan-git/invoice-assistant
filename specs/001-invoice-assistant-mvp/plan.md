---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 实施计划：发票整理助手一期 MVP

**编号**：`001-invoice-assistant-mvp` | **日期**：2026-04-17 | **规格**：`specs/001-invoice-assistant-mvp/spec.md`

## 概述

本计划用于把第一期 MVP 从需求冻结推进到可执行的工程分解。当前阶段的目标是完成 canonical 文档基线、研究结论、数据模型和任务分解，并在 verify 通过后等待用户明确 execute 授权。

## 技术背景

- **语言 / 版本**：
  - 后端：Python 3.11+
  - 前端：TypeScript + React
- **主要依赖**：
  - 后端：FastAPI、SQLAlchemy、Pydantic、SQLite 驱动、导出库、PDF 文本提取库
  - 前端：Vite、Ant Design、React Router、状态管理与数据请求基础库
- **存储**：SQLite + 本地文件目录
- **测试**：
  - 后端：`pytest`
  - 前端：组件测试 + 页面级手工验证
  - 框架治理：`python -m ai_sdlc gate ...` 与 `python -m ai_sdlc verify constraints`
- **目标平台**：macOS / Linux 本地开发环境，本机浏览器访问本地服务
- **关键约束**：
  - 单机、单管理员、无登录
  - 单写者后台模型
  - 文本提取优先，本地 OCR 兜底
  - 文档阶段不越过 execute 授权直接改产品代码

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Persist decisions to the repository | 以 `specs/001-invoice-assistant-mvp/` 为唯一正式真值，辅助设计仅作引用 |
| Prefer contract-level verification before closure | 在进入 execute 前先通过 refine / design / decompose / verify 相关 gate |
| Keep docs and code traceable | 所有实现任务都从 `spec.md`、`research.md`、`data-model.md` 和 `tasks.md` 反向追溯 |

## 项目结构

### 文档结构

```text
specs/001-invoice-assistant-mvp/
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
├── pyproject.toml
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
└── tests/

frontend/
├── package.json
├── src/
│   ├── app/
│   ├── pages/
│   ├── components/
│   ├── api/
│   └── types/
└── tests/
```

## 阶段计划

### Phase 0：文档冻结与框架对齐

- **目标**：完成 canonical 规格、研究结论、数据模型、任务分解和执行日志基线。
- **产物**：`spec.md`、`research.md`、`data-model.md`、`plan.md`、`tasks.md`、`task-execution-log.md`
- **验证方式**：
  - `python -m ai_sdlc gate refine`
  - `python -m ai_sdlc gate design`
  - `python -m ai_sdlc gate decompose`
  - `python -m ai_sdlc verify constraints`
- **回退方式**：只修改 `specs/001-invoice-assistant-mvp/` 与相关框架记录，不触碰产品代码

### Phase 1：后端基础设施与存储骨架

- **目标**：建立 FastAPI 服务、SQLite 数据模型、文件存储结构和配置版本化骨架。
- **产物**：后端应用骨架、数据库模型、迁移脚本、基础测试
- **验证方式**：`pytest`、数据库模型创建验证、基础 API smoke test
- **回退方式**：保持 schema 变更可逆，先在 feature 分支局部实现

### Phase 2：解析链路、规则判定与导出

- **目标**：建立证据模型、字段抽取、购方校验、业务风险分类、重复票检测、重命名和导出链路。
- **产物**：解析适配器、规则服务、导出服务、批次任务调度逻辑
- **验证方式**：规则单元测试、批次集成测试、导出结果抽查
- **回退方式**：解析适配器与规则层解耦，失败时可保留旧实现或切换到待复核

### Phase 3：前端工作台、结果页与配置中心

- **目标**：交付首页批次工作台、结果页、详情抽屉、配置中心和人工复核入口。
- **产物**：React 页面、路由、表格、筛选器、表单、操作抽屉
- **验证方式**：本地 dev server 手工走查、关键交互验证、构建检查
- **回退方式**：按页面模块拆分提交，问题局限在单页或单组件内

### Phase 4：端到端验证与交付收口

- **目标**：使用样例发票覆盖核心流程，确认统计口径、导出结果和留痕一致。
- **产物**：端到端验证记录、执行归档、收口说明
- **验证方式**：样例批次跑通、结果页核对、导出核对、`close-check`
- **回退方式**：保留样例数据与错误案例，按批次回滚到上一稳定实现

## 工作流计划

### 工作流 A：批次导入到结果判定

- **范围**：上传、建批、文本提取、OCR 兜底、证据标准化、字段抽取、规则判定
- **影响范围**：后端服务层、数据库模型、批次状态推进、结果页 API
- **验证方式**：样例批次处理测试 + 单张票规则测试
- **回退方式**：解析失败统一落到 `processing_failed` 或 `review_required`

### 工作流 B：配置中心与规则版本快照

- **范围**：税务档案、风险规则、命名模板、默认操作者名
- **影响范围**：配置 API、版本表、批次快照、审计日志
- **验证方式**：版本生成测试 + 历史批次不漂移验证
- **回退方式**：采用追加版本而不是就地覆盖

### 工作流 C：人工复核与导出

- **范围**：详情抽屉操作、ReviewAction、ZIP / Excel 导出
- **影响范围**：前端交互、导出服务、审计留痕、统计口径
- **验证方式**：复核动作测试 + 导出内容抽样对账
- **回退方式**：人工动作只追加记录，不改写系统判定

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 文档阶段完整性 | AI-SDLC refine / design / decompose gate | `verify constraints` |
| 批次处理链路 | 后端集成测试 | 手工上传样例票 |
| 规则判定正确性 | 规则单元测试 | 详情抽屉解释对账 |
| 统计口径一致性 | API / 导出结果对账 | 页面人工核对 |
| 配置版本快照 | 版本与批次快照测试 | 数据库抽查 |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 本地 OCR 具体供应商选型 | 待 execute 前确认 | execute |
| 样例发票数据集位置与脱敏方式 | 待准备 | execute |
| Excel 样式细节 | 不阻塞，先以字段完整性为准 | execute |

## 执行授权边界

1. 当前仅完成文档与计划冻结，不等于已获 execute 授权。
2. 在用户明确要求进入实现且 verify 无阻塞之前，不创建产品代码。
3. 进入 execute 时，需从 `design/001-invoice-assistant-mvp-docs` 切到对应 `feature/001-invoice-assistant-mvp-*` 分支。

## 实施顺序建议

1. 先冻结文档和 checkpoint 一致性。
2. 再按 `tasks.md` 逐批推进后端基础、规则链路和导出。
3. 然后交付前端工作台、结果页与配置中心。
4. 最后用样例批次完成端到端验证与收口。
