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

## 本轮验证证据

- `python -m ai_sdlc adapter activate`
- `python -m ai_sdlc run --dry-run`
- `uv run pytest backend/tests -q`

## 本轮验证结果

- 2026-04-19：`python -m ai_sdlc adapter activate` 已记录当前 adapter 人工确认（`acknowledged`）
- 2026-04-19：`python -m ai_sdlc run --dry-run` 通过，输出 `Stage close: PASS`
- 2026-04-19：`uv run pytest backend/tests -q` 通过，结果 `60 passed`

## 执行规则

1. 严格按 `P1 -> P2 -> P3 -> P4` 顺序执行。
2. 每个条目先补失败测试，再写最小实现，再跑对应回归。
3. 如某条目实现过程中发现新的范围扩张，只能在本文件追加，不直接隐式扩 scope。
