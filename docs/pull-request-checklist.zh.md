# 发票整理助手 PR 收口清单

## Verification Profile

- 适用画像：`docs-only`、`rules-only`、`truth-only`、`code-change`
- 约束命令：`uv run ai-sdlc verify constraints`
- truth 同步预演：`python -m ai_sdlc program truth sync --dry-run`
- 代码变更验证：`uv run pytest`
- 代码变更静态检查：`uv run ruff check`

## 提交范围

- 变更只覆盖 `001-invoice-assistant-mvp` 的一期 MVP 范围
- `specs/001-invoice-assistant-mvp/` 与实际实现一致
- 未把 `docs/superpowers/*` 当作产品真源

## AI-SDLC 对齐

- 已执行 `python -m ai_sdlc run --dry-run`
- 当前 work item 仍为 `specs/001-invoice-assistant-mvp`
- `task-execution-log.md` 已追加本批命令、测试和结论
- `tasks.md` 完成状态与实际交付一致

## 自动化验证

- 后端端到端验证通过
- 后端全量测试通过
- 前端测试通过
- 前端构建通过
- `python -m ai_sdlc workitem close-check --wi specs/001-invoice-assistant-mvp` 无阻塞项

## 核心业务回归

- 上传到导出主链路可跑通
- 合规票总金额同时覆盖批次口径和当前筛选口径
- 疑似重复票不计入合规票金额
- 人工复核只留痕，不覆盖系统判定
- 导出统计与结果页统计一致

## 手工验收

- 已按 `frontend/tests/manual-checklist.md` 逐项核对
- 样例覆盖标准电子票、扫描票、待复核票、疑似重复票
- 结果页详情抽屉可查看证据、校验、风险和复核记录

## 已知边界

- 当前解析链路为本地确定性适配与测试样例驱动，真实 OCR/版式适配仍属于后续阶段能力扩展
- MVP 默认单机 SQLite + 本地文件存储，不覆盖多人协作和远程对象存储
- 重命名冲突已做后缀避让，但更复杂归档编排仍可在后续批次增强
