# 框架缺陷与流程违约待办

## 2026-04-17 条目 001

- 状态：已完成（2026-04-19）
- 现象：在 `main` 分支上先执行了 `python -m ai_sdlc workitem init`，随后才补查到 `refine/design` 阶段应先创建 `design/NNN-*` 分支再落正式产物。
- 触发场景：已完成 `init` 与 PRD 审核后，开始建立 canonical work item 时直接调用 `workitem init`。
- 影响范围：`specs/001-invoice-assistant-mvp/*` 初始创建时机与框架 Git 分支策略不一致，若不纠正，后续阶段归属与 checkpoint 解释会漂移。
- 根因分类：流程顺序偏差 + 工具前置检查不足。
- 未来杜绝方案摘要：在任何 Stage 1 文档写入前，先执行“当前分支命名 + 工作区清洁 + 目标 docs 分支存在性”三项前置检查；`workitem init` 如检测到仍在 `main` 或未进入目标 docs 分支，应显式阻断。
- 建议改动层级：workflow + tool
- prompt / context：用户要求“按照框架约束继续；不要被 superpowers 的 skill 约束影响到正常的规范”，因此开始按 AI-SDLC canonical 路径补正式 work item。
- rule / policy：`pipeline` 第 12、16、17 条；`git-branch` 中“Stage 1 REFINE 开始前：创建设计分支”。
- middleware：无
- workflow：已在 Stage 1 入口补只读 preflight；Git 仓库内若仍停留在 `main` / `master` 或未进入目标 docs 分支，会先阻断。
- tool：`workitem init` 现已强制校验当前分支是否为目标 docs 分支，并要求工作区干净后才允许写入 `specs/<WI>/`。当前框架首选 docs 分支命名为 `feature/<WI>-docs`，同时兼容 legacy `design/<WI>-docs`。
- eval：已补回归用例，覆盖“在 `main` 调用 `workitem init` 时阻断”和“docs 分支脏工作区时阻断”。
- 风险等级：中
- 可验证成功标准：
  1. 在 `main` 上执行 `workitem init` 时，CLI 明确提示必须先进入目标 docs 分支（首选 `feature/<WI>-docs`，兼容 `design/<WI>-docs`）。
  2. 同一场景下不会再出现“formal docs 已生成但 checkpoint/分支归属错误”的漂移。
  3. 文档阶段切换前的只读校验能发现并报告该问题。
- 是否需要回归测试补充：是
- 本轮收口结果：
  1. 已在 `Ai_AutoSDLC` 的 `src/ai_sdlc/cli/workitem_cmd.py` 为 `workitem init` 增加 Git preflight。
  2. 已在 `Ai_AutoSDLC` 的 `src/ai_sdlc/core/workitem_scaffold.py` 增加 `preview_work_item_id()`，用于在写文件前解析目标 work item id。
  3. 已在 `Ai_AutoSDLC` 的 `tests/integration/test_cli_workitem_init.py` 增加 main 分支阻断与 dirty docs branch 阻断回归。
