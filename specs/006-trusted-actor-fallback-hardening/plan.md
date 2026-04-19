---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 实施计划：可信操作者 fallback 收口

**编号**：`006-trusted-actor-fallback-hardening` | **日期**：2026-04-19 | **规格**：specs/006-trusted-actor-fallback-hardening/spec.md

## 概述

本期只收口一个治理真值：当后端没有可信操作者上下文时，系统必须显式失败，而不是伪造一个带全角色的本机管理员继续执行写操作。实现上优先收紧依赖层与 API 入口，再用最小回归覆盖“缺配置失败”和“忽略前端伪造姓名”两条主路径，避免顺手扩展到登录体系、配置中心或导出字段增强。

## 技术背景

**语言/版本**：Python 3.12、TypeScript  
**主要依赖**：FastAPI、SQLAlchemy、Starlette TestClient、Pytest、React  
**存储**：本地 SQLite + 本地文件系统  
**测试**：后端 `pytest` API/服务测试，必要时复用前端既有错误展示路径  
**目标平台**：本地单机桌面/浏览器工作台  
**约束**：

- 本轮不引入完整登录体系、SSO、外部 IAM 或多用户配置模型。
- 本轮不恢复 `default_operator_name` 配置编辑，也不处理 Excel manifest 字段完整性。
- 本轮不改变现有角色集合与 denied audit 结构，只修正 trusted actor 缺失时的错误 fallback。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| 本地优先、治理证据真实 | 将 trusted actor 缺失视为本地配置错误，避免在伪造身份下继续写入业务或审计数据。 |
| 小步迭代、范围可控 | 只触达依赖层、受控 API 和定向测试，不顺手扩展登录体系、配置中心或导出契约。 |
| 先证据后结论 | 先补红灯测试，再写最小实现，最后用定向回归和 `run --dry-run` 验证。 |

## 项目结构

### 文档结构

```text
specs/006-trusted-actor-fallback-hardening/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 源码结构

```text
backend/
├── app/api/dependencies.py
├── app/api/actors.py
├── app/api/batches.py
├── app/api/config.py
└── app/api/invoices.py

backend/tests/
└── test_api_workflows.py
```

## 阶段计划

### Phase 0：研究与决策冻结

**目标**：把 006 的正式范围、非目标、验证口径和顺序执行边界写实，替换 `workitem init` 生成的占位文本。  
**产物**：spec.md / plan.md / tasks.md / task-execution-log.md  
**验证方式**：文档对账 + `python -m ai_sdlc run --dry-run`  
**回退方式**：仅文档变更，可通过单次 git 回滚撤销。

### Phase 1：trusted actor 缺失路径红绿收口

**目标**：让 trusted actor 缺失时的 `/api/me` 与受控写接口返回明确配置错误，并保证前端伪造姓名不再影响后端身份。  
**产物**：依赖层修复、API 入口收口、定向 API 测试  
**验证方式**：`python -m pytest backend/tests/test_api_workflows.py -q`  
**回退方式**：恢复现有 fallback 行为，但此方案只作为紧急回退，不保留为最终治理口径。

### Phase 2：验证与归档

**目标**：在不扩 scope 的前提下完成定向回归、dry-run 与执行归档。  
**产物**：更新后的任务状态、执行日志、必要的 close 前验证证据  
**验证方式**：定向 pytest + `python -m ai_sdlc run --dry-run`  
**回退方式**：回退本轮代码与归档修改，恢复到修复前分支状态。

## 工作流计划

### 工作流 A：trusted actor 依赖真值

**范围**：`get_trusted_actor()`、`resolve_actor()`、`/api/me`  
**影响范围**：后端可信身份读取、前端当前操作者只读展示、配置错误暴露路径  
**验证方式**：依赖行为测试 + `/api/me` API 测试  
**回退方式**：恢复当前 fallback 行为，但不保留为正式治理口径

### 工作流 B：受控写接口阻断与伪造姓名忽略

**范围**：批次创建、规则版本创建、人工复核、导出接口  
**影响范围**：业务写入前置校验、操作者显示名来源、现有角色拒绝审计  
**验证方式**：`backend/tests/test_api_workflows.py`  
**回退方式**：恢复旧的 fallback 分支，但保留新增测试方便后续重新收口

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| trusted actor 缺失时 `/api/me` 显式失败 | API 测试 | 前端既有错误展示路径走查 |
| trusted actor 缺失时受控写接口提前阻断 | API 测试 | DB 断言无业务写入 |
| 已配置 trusted actor 时忽略请求体伪造姓名 | API 测试 | 返回 payload / 落库记录对账 |
| 已配置 trusted actor 但缺角色时继续返回 `403` | 既有 API 测试回归 | denied audit 断言 |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| `/api/me` 缺失 trusted actor 时使用 `503` 还是 `500` 更符合既有错误约定 | 倾向 `503`，表示服务配置未就绪 | Phase 1 |
| 是否需要为“trusted actor 未配置”单独写审计日志 | 本期不做，避免无可信 actor 归属时伪造审计 | 不阻塞 |
| 是否一并移除请求模型中的 `created_by` / `changed_by` / `reviewed_by` 字段 | 本期优先忽略其值；接口 schema 清理可后续独立评估 | 不阻塞 |

## 实施顺序建议

1. 先冻结 006 文档与 backlog 真值，明确“只修 fallback，不扩登录体系”的边界。
2. 先写后端红灯测试，覆盖 trusted actor 缺失与请求体姓名伪造两条主路径。
3. 再写依赖层和 API 最小实现，保持现有 `403` 角色拒绝路径不回退。
4. 最后跑定向回归与 `python -m ai_sdlc run --dry-run`，并把本轮执行归档补齐。
