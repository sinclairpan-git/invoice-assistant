# 发票整理助手顶层缺口待办

## 目的

归档 2026-04-19 对顶层 PRD、设计文档、`specs/001-005` 与当前实现的对账结论，并作为本轮顺序执行的唯一 backlog。

## 对账基线

- 顶层 PRD：`发票整理助手_评审终版_重新生成.md`
- Phase 1 设计基线：`docs/superpowers/specs/2026-04-17-invoice-assistant-design.md`
- 当前 work items：`specs/001-invoice-assistant-mvp` 至 `specs/009-export-audit-surface-refresh`
- 当前实现：`backend/`、`frontend/`

## 总体结论

- `P1-P10` 已全部完成，顶层 backlog 当前无剩余待收口缺口。
- 经对抗 Agent 合议与本地复扫确认，当前仓库不存在新的主路径产品行为缺口；新增的 3 个后续缺口已经分别在 `006-009` 单独收口。
- 当前 `specs/001-009` 的 `python -m ai_sdlc workitem close-check --wi ... --json` 均返回 `ok: true`，`python -m ai_sdlc run --dry-run` 继续通过。
- 后续若再发现新的实现/治理缺口，只能继续在本文件追加新条目，而不是回写已完成条目的历史真相。

## 顺序执行清单

### P1 允许同一张发票聚合多份清单附件

- **状态**：已完成
- **来源规格**：
  - `specs/005-attachment-list-recognition/spec.md` 的边界情况要求支持“多页或多文件清单附件聚合证据”
  - `FR-006` 要求一张主发票可关联零到多份清单附件
- **现状**：
  - 当前 `backend/app/services/processing_service.py` 会把“多份附件命中同一发票”统一降级为 `ambiguous`，并清空 `matched_invoice_id`
  - 导致同票多附件无法被聚合消费，也无法进入详情/导出的附件链路
- **本轮目标**：
  1. 允许多份附件稳定关联同一发票
  2. 对可信附件聚合证据后再做重判
  3. 在详情和导出中保留全部关联附件
- **收口结果**：
  1. `ProcessingService` 已改为允许同票多附件共存，并聚合条目文本、页信息、字段候选与置信度
  2. 多附件命中同票时不再被统一降级成 `ambiguous`
  3. 详情接口可返回全部关联附件，回归测试已锁定

### P2 把附件缺失/未匹配/低置信度原因落到单票解释链

- **状态**：已完成
- **来源规格**：
  - `specs/005-attachment-list-recognition/spec.md` 要求详情明确区分“缺少附件”“附件无法匹配”“附件识别置信度不足”
- **现状**：
  - 批次级已有 `attachment_status_counts`
  - 单票详情与导出还主要依赖通用 `risk_flags`，缺少附件专属原因码
- **本轮目标**：
  1. 将附件缺失、未匹配、低置信度等状态映射到单票 `decision_reasons`
  2. 保持批次级统计不回退
  3. 让详情页与导出摘要对附件待复核原因可解释
- **收口结果**：
  1. 已新增附件专属风险标记：`attachment_missing`、`attachment_unmatched`、`attachment_low_confidence`、`attachment_parse_failed`
  2. 详情接口与导出摘要现在会把附件待复核原因写入单票解释链
  3. 批次级附件统计保持兼容，未引入批次级失败回退

### P3 修正文档真值缺口

- **状态**：已完成
- **包含项**：
  1. `specs/005-attachment-list-recognition/spec.md` 头部状态仍为“草稿”，需与任务完成状态对齐
  2. `specs/002-invoice-assistant-runtime-hardening/task-execution-log.md` 与 `execution-log.md` 仍保留已过期的“同步处理”剩余差距描述，需按当前实现修正或标注为历史记录
- **本轮目标**：
  1. 文档状态与代码事实保持一致
  2. 后续审计不再被过期结论误导
- **收口结果**：
  1. `005` 规格头部状态已从“草稿”更新为“已实现并完成回归验证”
  2. `002` 两份执行日志中的“同步处理剩余差距”已改为历史备注，并补充当前异步入队事实

### P4 收口 005 执行日志状态与归档真值

- **状态**：已完成
- **来源规格**：
  - `specs/005-attachment-list-recognition/tasks.md` 已显示 `T11-T51` 全部完成
  - `specs/005-attachment-list-recognition/spec.md` 已显示“已实现并完成回归验证（2026-04-19）”
- **现状**：
  - `specs/005-attachment-list-recognition/task-execution-log.md` 头部状态仍为“执行中”
  - latest batch 仍停留在旧的 close-out 语气，未反映顶层 backlog 驱动补丁与本轮复扫结论
- **本轮目标**：
  1. 让 005 执行日志状态与当前代码/规格事实一致
  2. 把本轮顶层复扫与文档收口动作归档到 latest batch
  3. 继续以本文件作为顺序执行的唯一 backlog
- **收口结果**：
  1. 005 执行日志头部状态已更新为“已完成实现、回归验证与后续补丁归档”
  2. 已追加 next-round batch，记录 backlog 复扫与文档真值修正
  3. 复扫后仍未发现新的产品行为缺口

### P5 完成 `001-005` 的 AI-SDLC close-check 收口

- **状态**：已完成
- **来源规格**：
  - `python -m ai_sdlc workitem close-check --wi specs/<work-item> --json`
  - `src/ai_sdlc/rules/verification.md`
- **现状**：
  - `001-004` 的 `close-check` 在主工作区只阻塞于 git working tree 不干净
  - `005` 除 dirty tree 外，还因 latest batch 使用了不受支持的 `verification profile` 文案而被拒绝
- **本轮目标**：
  1. 把 `005` latest batch 的 `verification profile` 改成 AI-SDLC 可接受的值
  2. 补齐 `docs-only` 画像所需的约束验证命令证据
  3. 在 clean worktree 中确认 `001-005` 全部 `close-check` 通过
- **收口结果**：
  1. `005` latest batch 已改为 `docs-only`，并补录 `uv run ai-sdlc verify constraints`
  2. 在 clean worktree 中，`001-005` 的 `python -m ai_sdlc workitem close-check --wi ... --json` 全部返回 `ok: true`
  3. 当前主工作区继续保留 `.ai-sdlc/project/config/project-config.yaml` 这类运行态变更，不把它混入功能/归档提交

### P6 补齐远端 CI 门禁并与本地校验对齐

- **状态**：已完成
- **来源规格**：
  - `docs/pull-request-checklist.zh.md`
  - `docs/ai-sdlc-runtime-file-versioning.zh-CN.md`
  - 本地已存在 `uv run tracked-files`、`uv run ruff check`、`uv run pytest` 门禁包装
- **现状**：
  - 启动本轮收口前，仓库没有 `.github/workflows/ci.yml`
  - 启动本轮收口前，本地质量门禁已存在，但 PR / `main` 分支没有远端自动校验
- **本轮目标**：
  1. 为 PR 和 `main` 推送补齐 GitHub Actions workflow
  2. 远端同步执行 tracked-file policy、后端静态检查、后端测试
  3. 将前端测试与构建纳入同一条远端门禁
- **收口结果**：
  1. 已新增 `.github/workflows/ci.yml`，对 `pull_request` 和 `main` push 生效
  2. Python job 现在执行 `uv run tracked-files`、`uv run ruff check workspace_tools backend/tests backend/app`、`uv run pytest backend/tests -q`
  3. Frontend job 现在执行 `corepack pnpm --dir frontend test` 与 `corepack pnpm --dir frontend build`
  4. 已新增 `backend/tests/test_ci_workflow.py` 锁定 workflow 的关键门禁命令，避免后续漂移

### P7 收口 trusted actor fallback 真值

- **状态**：已完成（2026-04-19）
- **来源规格**：
  - `specs/004-controlled-review-export/spec.md` 要求未配置后端可信操作者上下文时，受控写操作不得回退到匿名或前端自由输入，而应返回明确配置错误
  - 对抗式评审合议结论：当前真实最高优先级缺口是 trusted actor fallback 失真；`default_operator_name` 不再单独立项，Excel 字段完整性和术语漂移后置
- **现状**：
  - `backend/app/api/dependencies.py` 在 `app.state.trusted_actor` 缺失时，会回退到带 `config_admin`、`reviewer`、`exporter` 全角色的伪造本机管理员
  - `backend/app/api/batches.py`、`backend/app/api/config.py`、`backend/app/api/invoices.py` 仍会把请求体里的 `created_by` / `changed_by` / `reviewed_by` 用作 fallback 显示名
  - 现有回归只覆盖“trusted actor 已配置时的角色控制”，尚未锁定“trusted actor 缺失时必须失败”的治理真值
- **本轮目标**：
  1. 新建 `006-trusted-actor-fallback-hardening` work item，把修复范围从旧工单中切出并单独承接
  2. 收口 trusted actor 缺失时的依赖行为，禁止全角色 fallback 和前端姓名回填
  3. 以定向红绿测试锁定 `/api/me` 与受控写接口的配置错误真值
- **计划收口标准**：
  1. 未配置 trusted actor 时，`/api/me` 与受控写接口稳定返回明确配置错误
  2. 已配置 trusted actor 时，请求体伪造姓名不再影响后端记录的操作者身份
  3. 本条缺口完成后，再重新评估 Excel manifest 字段完整性与术语对齐
- **完成证据**：
  - `uv run pytest backend/tests -q`：`69 passed`
  - `uv run ruff check`：通过
  - `uv run ai-sdlc verify constraints`：`no BLOCKERs`
  - `python -m ai_sdlc recover --reconcile`
  - `python -m ai_sdlc run --dry-run`：`Stage close: PASS`

### P8 补齐 excel manifest 台账字段契约

- **状态**：已完成（2026-04-19）
- **来源规格**：
  - `docs/superpowers/specs/2026-04-17-invoice-assistant-design.md` 第 14 节要求 Excel 台账至少包含疑似重复标记、购方税号、购方地址/电话/开户银行/银行账户、开票日期、销售方名称、发票明细摘要、处理时间
  - `specs/004-controlled-review-export/spec.md` 要求导出台账与单票解释口径保持一致
- **现状**：
  - `backend/app/services/export_service.py` 旧版 manifest 只输出基础状态、合规解释、金额、发票号码、购方名称、风险标记和附件字段
  - 设计基线中已承诺的买方扩展字段、重复标记、销方、明细摘要与处理时间尚未进入导出台账
- **本轮目标**：
  1. 新建 `007-excel-manifest-contract-completion` work item，单独承接 manifest 契约补齐
  2. 以红灯测试锁定缺失列头和值
  3. 在不改 schema 的前提下，复用 `InvoiceRecord`、`ExtractedField`、`DocumentEvidence`、`ProcessingAttempt` 补齐缺列
- **完成证据**：
  - `uv run pytest backend/tests/test_export_service.py::test_excel_manifest_includes_required_contract_columns -q`：通过
  - `uv run pytest backend/tests/test_export_service.py backend/tests/test_end_to_end_batch.py::test_end_to_end_batch_upload_to_export_keeps_ui_export_and_db_consistent -q`：`6 passed`
  - `uv run ruff check backend/app/services/export_service.py backend/tests/test_export_service.py`：通过
  - `python -m ai_sdlc run --dry-run`：收口后通过

### P9 收口“业务风险分类”术语漂移

- **状态**：已完成（2026-04-19）
- **来源规格**：
  - `specs/001-invoice-assistant-mvp/spec.md` 已明确要求用户可见规则层命名必须使用“业务风险分类”
  - `docs/superpowers/specs/2026-04-17-invoice-assistant-design.md` 作为设计基线，已把“业务风险分类”定义为权威术语
  - 对抗 Agent 合议结论：只修复用户可见术语，不改内部/API 键 `business_compliance_status`
- **现状**：
  - `frontend/src/components/results/InvoiceDrawer.tsx` 详情标签仍显示“业务合规”
  - `backend/app/services/export_service.py` 的 `excel_manifest` 列头仍显示“业务合规”
  - `specs/002`、`specs/004` 当前正式规格仍保留旧 wording，和 `001` / 设计基线冲突
- **本轮目标**：
  1. 把详情标签与 Excel manifest 列头统一回“业务风险分类”
  2. 用前后端回归测试锁定术语，不让实现再次漂回旧文案
  3. 同步收口 `002/004` 正式规格与 008 work item 归档
- **完成证据**：
  - `uv run pytest backend/tests/test_export_service.py::test_export_service_blocks_pending_review_pass_export_and_success_manifest_includes_compliance_fields backend/tests/test_end_to_end_batch.py::test_end_to_end_batch_upload_to_export_keeps_ui_export_and_db_consistent -q`：通过
  - `corepack pnpm --dir frontend test`：通过
  - `corepack pnpm --dir frontend build`：通过
  - `uv run ai-sdlc verify constraints`：通过
  - `python -m ai_sdlc run --dry-run`：收口后通过

### P10 收口结果页导出审计回显

- **状态**：已完成（2026-04-19）
- **来源规格**：
  - `specs/004-controlled-review-export/spec.md` 要求导出后留下可追溯审计证据
  - `docs/superpowers/specs/2026-04-17-invoice-assistant-design.md` 已将 `export_manifest_path` 纳入 `Batch` 核心对象
- **现状**：
  - 后端批次详情已经返回 `export_manifest_path` 与 `export_jobs`
  - 前端结果页导出成功后只弹一次 toast，没有刷新详情，也没有把持久化导出状态展示给用户
- **本轮目标**：
  1. 导出成功后刷新批次详情与批次列表
  2. 在结果页展示“最近导出”回显，消费现有的 `export_manifest_path` / `export_jobs`
  3. 通过前端测试锁定回显行为，并完成 009 work item 收口
- **完成证据**：
  - `corepack pnpm --dir frontend test`：通过
  - `corepack pnpm --dir frontend build`：通过
  - `uv run pytest backend/tests/test_end_to_end_batch.py::test_end_to_end_batch_upload_to_export_keeps_ui_export_and_db_consistent -q`：通过
  - `uv run ruff check backend/tests/test_end_to_end_batch.py`：通过
  - `uv run ai-sdlc verify constraints`：通过
  - `python -m ai_sdlc run --dry-run`：收口后通过

## 本轮验证证据

- `python -m ai_sdlc adapter activate`
- `uv run ai-sdlc verify constraints`
- `python -m ai_sdlc run --dry-run`
- `uv run tracked-files`
- `uv run ruff check workspace_tools backend/tests backend/app`
- `uv run pytest backend/tests -q`
- `corepack pnpm --dir frontend test`
- `corepack pnpm --dir frontend build`
- `python -m ai_sdlc workitem close-check --wi specs/001-invoice-assistant-mvp --json`
- `python -m ai_sdlc workitem close-check --wi specs/002-invoice-assistant-runtime-hardening --json`
- `python -m ai_sdlc workitem close-check --wi specs/003-runtime-state-recovery --json`
- `python -m ai_sdlc workitem close-check --wi specs/004-controlled-review-export --json`
- `python -m ai_sdlc workitem close-check --wi specs/005-attachment-list-recognition --json`
- `python -m ai_sdlc workitem close-check --wi specs/006-trusted-actor-fallback-hardening --json`
- `python -m ai_sdlc workitem close-check --wi specs/007-excel-manifest-contract-completion --json`
- `python -m ai_sdlc workitem close-check --wi specs/008-business-risk-terminology-alignment --json`
- `python -m ai_sdlc workitem close-check --wi specs/009-export-audit-surface-refresh --json`

## 本轮验证结果

- 2026-04-19：`python -m ai_sdlc adapter activate` 已记录当前 adapter 人工确认（`acknowledged`）
- 2026-04-19：`uv run ai_sdlc verify constraints` 通过，输出 `verify constraints: no BLOCKERs.`
- 2026-04-19：`python -m ai_sdlc run --dry-run` 通过，输出 `Stage close: PASS`
- 2026-04-19：`uv run tracked-files` 通过，输出 `Tracked file policy: OK`
- 2026-04-19：`uv run ruff check workspace_tools backend/tests backend/app` 通过，输出 `All checks passed!`
- 2026-04-19：`uv run pytest backend/tests -q` 通过，结果 `70 passed`
- 2026-04-19：`corepack pnpm --dir frontend test` 通过，结果 `8 passed`
- 2026-04-19：`corepack pnpm --dir frontend build` 通过
- 2026-04-19：在 clean worktree 中，`001-009` 的 `python -m ai_sdlc workitem close-check --wi ... --json` 均返回 `ok: true`

## 执行规则

1. 严格按 `P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8 -> P9 -> P10` 顺序执行。
2. 每个条目先补失败测试，再写最小实现，再跑对应回归。
3. 如某条目实现过程中发现新的范围扩张，只能在本文件追加，不直接隐式扩 scope。
