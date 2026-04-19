# 功能规格：可信操作者 fallback 收口

**功能编号**：`006-trusted-actor-fallback-hardening`
**创建日期**：2026-04-19
**状态**：已完成实现、验证与 dry-run 收口（2026-04-19）
**输入**：按对抗式评审结论，优先修复 004 受控治理链路中的 trusted actor fallback 缺口：未配置后端可信操作者上下文时，受控写操作不得回退到全角色本机管理员或前端自由输入；必须返回明确配置错误，并补齐回归测试锁定该真值。 参考：`docs/invoice-assistant-gap-backlog.zh-CN.md`、`specs/004-controlled-review-export/spec.md`、`docs/superpowers/specs/2026-04-17-invoice-assistant-design.md`

**范围**：

- 覆盖 `backend/app/api/dependencies.py` 中 trusted actor 解析与 fallback 行为收口。
- 覆盖 `/api/me`、批次创建、规则版本创建、人工复核、导出四类依赖 trusted actor 的接口真值。
- 覆盖“请求体伪造 `created_by` / `changed_by` / `reviewed_by` 不得影响后端可信身份”的行为锁定。
- 覆盖定向回归测试与本 work item 执行归档。
- 不覆盖完整登录体系、SSO、外部 IAM、多用户权限模型。
- 不覆盖 Excel manifest 字段补齐、`default_operator_name` 配置 UI 恢复、术语统一等后续条目。

## 用户场景与测试（必填）

### 用户故事 1 - trusted actor 缺失时阻断受控写操作（优先级：P0）

作为财务治理责任人，我希望当后端没有配置 trusted actor 上下文时，所有依赖可信身份的写操作都立即失败并返回明确配置错误，这样规则修改、人工复核和导出不会在伪造身份下继续执行。

**优先级说明**：004 的治理前提是“身份与角色来自后端可信上下文”。若未配置时仍能写入业务实体或审计记录，已收口的治理证据就不再可信。  
**独立测试**：后端 API 测试覆盖 trusted actor 缺失时的 `POST /api/config/{kind}/versions`、`POST /api/batches`、`POST /api/invoices/{id}/review-actions`、`POST /api/batches/{id}/exports` 配置错误路径。

**验收场景**：

1. **Given** 后端未配置 `trusted_actor`，**When** 用户调用规则版本创建接口，**Then** 接口返回明确配置错误，且不会创建新规则版本或写入冒名审计记录。
2. **Given** 后端未配置 `trusted_actor`，**When** 用户提交批次上传或人工复核，**Then** 接口在任何业务写入前即失败，且请求体中的操作者姓名不会被采纳。

---

### 用户故事 2 - 已配置 trusted actor 时请求体姓名不得影响后端记录（优先级：P0）

作为审计复核人，我希望一旦后端已经配置 trusted actor，前端传来的 `created_by` / `changed_by` / `reviewed_by` 只能被忽略，不能影响最终的业务记录和审计显示名。

**优先级说明**：即使 trusted actor 已配置，只要请求体还能回填显示名，治理链路仍然可以被前端伪造。  
**独立测试**：API 测试覆盖带伪造姓名的批次创建、规则版本创建与人工复核请求，并断言持久化结果继续使用后端 actor `display_name`。

**验收场景**：

1. **Given** 后端 trusted actor 显示名为“财务复核员”，**When** 前端提交 `changed_by=前端伪造姓名` 创建规则版本，**Then** 返回结果与落库记录中的 `changed_by` 仍为“财务复核员”。
2. **Given** 后端 trusted actor 显示名为“财务复核员”，**When** 前端提交 `created_by=前端伪造姓名` 创建批次，**Then** 批次记录中的 `created_by` 仍为“财务复核员”。

---

### 用户故事 3 - 前端可见 trusted actor 缺失的显式错误（优先级：P1）

作为本机管理员，我希望 `/api/me` 在 trusted actor 缺失时返回明确配置错误，而不是默默显示伪造的“本机管理员”，这样我能在进行复核、导出或规则修改前看到治理配置没有就绪。

**优先级说明**：这不是新增治理能力，而是让已存在的只读身份入口与真实后端状态保持一致。  
**独立测试**：API 测试覆盖 `/api/me` 缺失 trusted actor 时的错误返回；前端沿用既有错误展示路径，无需新增交互设计。

**验收场景**：

1. **Given** 后端未配置 `trusted_actor`，**When** 前端请求 `/api/me`，**Then** 接口返回明确配置错误，不再返回伪造身份与角色。
2. **Given** 后端已配置 `trusted_actor`，**When** 前端请求 `/api/me`，**Then** 接口继续返回后端 actor `actor_id`、`display_name` 与 `roles`。

### 边界情况

- trusted actor payload 存在但 `roles` 为空；此时允许只读查询，但受控写接口仍会因缺角色返回 `403`，而不是配置错误。
- trusted actor payload 缺字段或类型异常；系统应视为“未配置可信上下文”，而不是局部回退。
- `create_batch` 当前虽然没有单独的角色门槛，但其 `created_by` 仍属于可信身份链路的一部分，因此也必须受 trusted actor 配置约束。
- 本轮不要求为“缺失 trusted actor”额外写入 denied audit；因为没有可信 actor 可归属时，不应生成看似可信的拒绝审计。

## 需求（必填）

### 功能需求

- **FR-001**：系统必须把 `app.state.trusted_actor` 缺失或无效视为“trusted actor 未配置”，不得回退到伪造的本机管理员与全角色集合。
- **FR-002**：`/api/me` 必须在 trusted actor 未配置时返回明确配置错误，不得继续返回伪造身份。
- **FR-003**：批次创建、规则版本创建、人工复核和导出接口必须在 trusted actor 未配置时直接失败，并在任何业务写入前停止。
- **FR-004**：当 trusted actor 已配置时，后端必须完全忽略请求体中的 `created_by`、`changed_by`、`reviewed_by` fallback 值。
- **FR-005**：当 trusted actor 已配置时，批次、规则版本、人工复核和导出记录中的操作者显示名必须继续来自后端 actor `display_name`。
- **FR-006**：角色校验仍由后端执行；trusted actor 已配置但缺少相应角色时，继续保持现有 `403` 与 denied audit 行为。
- **FR-007**：系统必须补齐定向回归测试，覆盖 trusted actor 缺失时的配置错误路径，以及 trusted actor 已配置时忽略前端伪造姓名的行为。

### 关键实体（如涉及数据则必填）

- **TrustedActor**：后端可信操作者上下文，包含 `actor_id`、`display_name`、`roles`，本轮需要区分“已配置”与“未配置”状态。
- **Controlled Write Endpoint**：依赖 trusted actor 的写接口集合，包括批次创建、规则版本创建、人工复核和导出。
- **Trusted Actor Configuration Error**：当 trusted actor 缺失或无效时返回的显式错误结果，用于阻断治理链路并向前端暴露配置问题。

## 成功标准（必填）

### 可度量结果

- **SC-001**：在 trusted actor 未配置的测试场景下，`/api/me` 与四类受控写接口均返回明确配置错误，且不产生业务写入。
- **SC-002**：在 trusted actor 已配置的测试场景下，请求体伪造姓名不再影响批次、规则版本和人工复核记录中的操作者显示名。
- **SC-003**：在 trusted actor 已配置但缺角色的测试场景下，现有 `403` 与 denied audit 行为保持不回退。
- **SC-004**：本轮修复后，004 治理链路不再依赖“全角色本机管理员” fallback 才能通过现有回归。
