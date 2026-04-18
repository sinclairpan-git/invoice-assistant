---
related_doc:
  - "发票整理助手_评审终版_重新生成.md"
  - "specs/001-invoice-assistant-mvp/spec.md"
  - "specs/003-runtime-state-recovery/spec.md"
---
# 实施计划：发票整理助手四期：受控复核与导出闭环

**编号**：`004-controlled-review-export` | **日期**：2026-04-18 | **规格**：`specs/004-controlled-review-export/spec.md`

## 概述

本计划用于把当前“结果页能用、导出能跑、复核能点”但缺少可信身份、角色约束和导出门槛的状态，收口成一条可上线的财务治理闭环。实现重点不是增加新业务，而是把现有规则与结果转成可信操作者、受控动作、结构化结论和可审计导出。

## 技术背景

- **语言 / 版本**：
  - 后端：Python 3.11+
  - 前端：TypeScript + React
- **主要依赖**：
  - 后端：FastAPI、SQLAlchemy、pytest
  - 前端：Vite、React、Vitest、Ant Design
- **存储**：SQLite + 本地文件系统
- **测试**：
  - 后端：`uv run --project backend --extra dev python -m pytest backend/tests/test_api_workflows.py backend/tests/test_export_service.py backend/tests/test_end_to_end_batch.py -q`
  - 前端：`npm test -- tests/app-shell.test.tsx tests/runtime-ui.test.tsx`（在 `frontend/` 目录执行）
  - 框架治理：`python -m ai_sdlc run --dry-run`
- **目标平台**：本地单机运行环境
- **关键约束**：
  - 不引入完整登录体系；可信身份由后端受控配置或请求上下文提供。
  - 先写红灯回归，再改生产代码。
  - 导出门槛与审计口径必须统一落在后端，不把前端禁用态当作真实约束。

## 宪章检查

| 宪章门禁 | 计划响应 |
|----------|----------|
| Persist decisions to the repository | 四期范围、门槛和任务全部落在 `specs/004-controlled-review-export/` |
| Prefer contract-level verification before closure | 以前后端回归测试锁定可信身份、权限、导出门槛和审计行为 |
| Keep docs and code traceable | 文档任务直接映射到 `backend/app/api/*.py`、`backend/app/services/export_service.py`、`frontend/src/app/**` 与对应测试文件 |

## 项目结构

### 文档结构

```text
specs/004-controlled-review-export/
├── spec.md
├── plan.md
├── tasks.md
└── task-execution-log.md
```

### 本次实现涉及的源码结构

```text
backend/
├── app/api/
│   ├── batches.py
│   ├── config.py
│   ├── invoices.py
│   ├── serializers.py
│   └── dependencies.py
├── app/db/models.py
└── app/services/
    ├── config_service.py
    └── export_service.py

frontend/
├── src/app/
│   ├── api.ts
│   ├── shell.tsx
│   ├── types.ts
│   └── operator-settings.tsx
├── src/components/
│   ├── batch/UploadPanel.tsx
│   ├── results/ReviewActions.tsx
│   └── settings/RuleVersionPanel.tsx
└── tests/
    ├── app-shell.test.tsx
    └── runtime-ui.test.tsx
```

## 阶段计划

### Phase 0：文档冻结与红灯测试设计

- **目标**：冻结四期治理边界、导出门槛和验证口径，并先写出当前会失败的回归测试。
- **产物**：`spec.md`、`plan.md`、`tasks.md`、红灯测试设计
- **验证方式**：文档自检 + 定向测试确认缺口
- **回退方式**：仅修改文档与测试，不变更生产逻辑

### Phase 1：可信身份与角色约束落地

- **目标**：建立后端可信操作者上下文，移除前端自由输入身份，并把规则修改、复核、导出挂到角色校验。
- **产物**：后端身份依赖、受控 API、前端当前操作者展示
- **验证方式**：API 测试 + 前端回归测试
- **回退方式**：改动限定在 API 入参与前端身份展示层，不回退现有批次/解析主流程

### Phase 2：单票结果解释面与导出门槛落地

- **目标**：补齐单票财务解释字段，定义并实现各导出类型门槛与审计落账。
- **产物**：序列化字段、导出服务门槛判断、审计 payload、导出台账字段
- **验证方式**：服务测试 + API / E2E 回归
- **回退方式**：回退到原有结果字段和导出服务逻辑，不影响上传、识别、重试能力

### Phase 3：验证、归档与收口

- **目标**：完成定向回归、执行日志归档和工作区收口说明。
- **产物**：通过的测试记录、`task-execution-log.md` 更新、`tasks.md` 勾选
- **验证方式**：定向回归 + `python -m ai_sdlc run --dry-run`
- **回退方式**：若验证失败，仅回退四期局部改动

## 工作流计划

### 工作流 A：可信操作者上下文与前端只读展示

- **范围**：当前操作者获取、API 依赖注入、前端展示与表单收口
- **影响范围**：上传、规则修改、复核、导出、应用顶部身份显示
- **验证方式**：`backend/tests/test_api_workflows.py` + `frontend/tests/app-shell.test.tsx`
- **回退方式**：恢复原有展示和入参，但不触碰批次结果和导出文件结构

### 工作流 B：规则修改 / 复核 / 导出角色控制与拒绝审计

- **范围**：`config.py`、`invoices.py`、`batches.py`、审计写入
- **影响范围**：敏感动作访问控制、错误响应、审计完整性
- **验证方式**：`backend/tests/test_api_workflows.py`
- **回退方式**：恢复原有写接口，但保留四期文档说明范围未完成

### 工作流 C：单票结果解释层与导出门槛

- **范围**：序列化层、导出服务、E2E 验证
- **影响范围**：结果页字段、详情抽屉字段、Excel 台账字段、导出成败判定
- **验证方式**：`backend/tests/test_export_service.py` + `backend/tests/test_end_to_end_batch.py`
- **回退方式**：恢复原有导出台账和结果字段，不影响原始文件导出能力

## 关键路径验证策略

| 关键路径 | 主验证方式 | 次验证方式 |
|----------|------------|------------|
| 前端不再自由输入操作者身份 | `frontend/tests/app-shell.test.tsx` | 手工检查设置页和上传/复核组件 |
| 受控接口按角色拒绝或放行 | `backend/tests/test_api_workflows.py` | API 代码走查 |
| 单票结果字段与导出台账统一 | `backend/tests/test_end_to_end_batch.py` | `serializers.py` / manifest 内容断言 |
| 导出门槛和审计落账正确 | `backend/tests/test_export_service.py` | `audit_logs` 数据断言 |

## 开放问题

| 问题 | 状态 | 阻塞阶段 |
|------|------|----------|
| 本地单机模式下可信操作者上下文使用环境配置还是固定测试夹具 | 实现时选后端受控配置方案，不阻塞 | Phase 1 |
| `suggested_pass_zip` 是否允许在存在待复核票据时部分导出 | 四期按“有待复核即拒绝”收口 | 已冻结 |
| 是否记录被拒绝动作的审计 | 四期明确要求记录 | 已冻结 |

## 执行授权边界

1. 四期只做可信身份、权限、结果解释和导出门槛，不顺带扩展登录系统。
2. 所有敏感动作的真实约束必须在后端完成，前端只做展示和交互引导。
3. 完成代码修改后必须同步更新 `tasks.md` 和执行归档，保持 work item 真值一致。

## 实施顺序建议

1. 先冻结四期文档和门槛口径。
2. 再补后端与前端红灯测试，锁定当前缺口。
3. 然后实现可信身份派生、角色校验和单票结果字段。
4. 最后实现导出门槛 / 审计，跑回归并更新执行归档。
