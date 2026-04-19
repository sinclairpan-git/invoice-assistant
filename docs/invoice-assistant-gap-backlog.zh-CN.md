# 发票整理助手顶层缺口待办

## 目的

归档 2026-04-19 对顶层 PRD、设计文档、`specs/001-005` 与当前实现的对账结论，并作为本轮顺序执行的唯一 backlog。

## 对账基线

- 顶层 PRD：`发票整理助手_评审终版_重新生成.md`
- Phase 1 设计基线：`docs/superpowers/specs/2026-04-17-invoice-assistant-design.md`
- 当前 work items：`specs/001-invoice-assistant-mvp` 至 `specs/005-attachment-list-recognition`
- 当前实现：`backend/`、`frontend/`

## 总体结论

- `001-004` 未发现新的顶层主路径实现缺口。
- `005-attachment-list-recognition` 的 2 个行为缺口与 2 个文档真值缺口，已按本文件顺序完成收口。
- 下一轮复扫未发现新的产品行为缺口，仅发现 `005-attachment-list-recognition/task-execution-log.md` 的收口状态漂移，已在本轮修正。
- 继续按框架约束复扫后，新增发现 1 个 AI-SDLC 收口缺口：`005` latest batch 的 `verification profile` 不符合 `close-check` 要求；现已修正，并在 clean worktree 中确认 `001-005` 的 `workitem close-check` 全部通过。
- 在运行态文件版本控制守卫落地后，新增发现 1 个工程门禁缺口：仓库还缺少远端 CI workflow；现已补齐，并让 GitHub Actions 与本地 `tracked-files` / 后端 / 前端校验保持一致。
- 后续新增范围必须基于本文件继续追加，不再回到分散文档里重复建 backlog。

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
  - 仓库此前没有 `.github/workflows/ci.yml`
  - 本地质量门禁已存在，但 PR / `main` 分支没有远端自动校验
- **本轮目标**：
  1. 为 PR 和 `main` 推送补齐 GitHub Actions workflow
  2. 远端同步执行 tracked-file policy、后端静态检查、后端测试
  3. 将前端测试与构建纳入同一条远端门禁
- **收口结果**：
  1. 已新增 `.github/workflows/ci.yml`，对 `pull_request` 和 `main` push 生效
  2. Python job 现在执行 `uv run tracked-files`、`uv run ruff check workspace_tools backend/tests backend/app`、`uv run pytest backend/tests -q`
  3. Frontend job 现在执行 `corepack pnpm --dir frontend test` 与 `corepack pnpm --dir frontend build`
  4. 已新增 `backend/tests/test_ci_workflow.py` 锁定 workflow 的关键门禁命令，避免后续漂移

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

## 本轮验证结果

- 2026-04-19：`python -m ai_sdlc adapter activate` 已记录当前 adapter 人工确认（`acknowledged`）
- 2026-04-19：`uv run ai_sdlc verify constraints` 通过，输出 `verify constraints: no BLOCKERs.`
- 2026-04-19：`python -m ai_sdlc run --dry-run` 通过，输出 `Stage close: PASS`
- 2026-04-19：`uv run tracked-files` 通过，输出 `Tracked file policy: OK`
- 2026-04-19：`uv run ruff check workspace_tools backend/tests backend/app` 通过，输出 `All checks passed!`
- 2026-04-19：`uv run pytest backend/tests -q` 通过，结果 `67 passed`
- 2026-04-19：`corepack pnpm --dir frontend test` 通过，结果 `7 passed`
- 2026-04-19：`corepack pnpm --dir frontend build` 通过
- 2026-04-19：在 clean worktree 中，`001-005` 的 `python -m ai_sdlc workitem close-check --wi ... --json` 均返回 `ok: true`

## 执行规则

1. 严格按 `P1 -> P2 -> P3 -> P4 -> P5 -> P6` 顺序执行。
2. 每个条目先补失败测试，再写最小实现，再跑对应回归。
3. 如某条目实现过程中发现新的范围扩张，只能在本文件追加，不直接隐式扩 scope。
