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

## 2026-04-19 条目 002

- 状态：已完成（2026-04-19）
- 现象：框架实际 docs 分支策略已切到 `feature/<WI>-docs`，但 `refine.yaml`、`rules/git-branch.md`、`rules/pipeline.md`、`rules/scenario-routing.md` 仍以 `design/<WI>-docs` 作为主口径。
- 触发场景：完成条目 001 后继续复扫规则文档与阶段说明，发现 CLI / `BranchManager` / `decisions.yml` 与规范文本不一致。
- 影响范围：Stage 1 指引、分支切换说明、范围变更上升流程、checkpoint 示例都会给出过期分支名，导致用户和后续 agent 继续按旧规则操作。
- 根因分类：规则文档漂移 + 兼容迁移收尾不完整。
- 未来杜绝方案摘要：把 docs 分支命名真值固定为“首选 `feature/<WI>-docs`、兼容 `design/<WI>-docs`”，并用集成测试锁定 `stage show refine` 的对外展示口径。
- 建议改动层级：workflow + rule / policy + eval
- prompt / context：用户要求“继续”，上一轮已完成 `workitem init` preflight 修复；继续按框架 backlog 处理下一优先级时，发现规范文本仍落后于真实实现。
- rule / policy：`pipeline.md` 第 12 条；`git-branch.md`；`scenario-routing.md` 中 EXECUTE 上升流程；`refine.yaml` 的 create_docs_branch 检查项。
- middleware：无
- workflow：已将 Stage 1-4 的主 docs 分支口径统一为 `feature/<WI>-docs`，并明确 legacy `design/<WI>-docs` 仅作兼容说明，不再作为主指令。
- tool：`ai-sdlc stage show refine` 现在以 `feature/{id}-docs` 展示 Stage 1 docs branch 动作，不再把 `design/{id}-docs` 作为创建指令。
- eval：已补 `tests/integration/test_cli_stage.py` 回归，锁定 `stage show refine` 必须输出“创建 `feature/{id}-docs` 分支”。
- 风险等级：中
- 可验证成功标准：
  1. `stage show refine` 的输出主口径为 `feature/{id}-docs`。
  2. `git-branch.md`、`pipeline.md`、`scenario-routing.md` 与 `BranchManager` 当前行为一致。
  3. legacy `design/<WI>-docs` 仅以兼容说明出现，不再作为默认创建路径。
- 是否需要回归测试补充：是
- 本轮收口结果：
  1. 已在 `Ai_AutoSDLC` 的 `src/ai_sdlc/stages/refine.yaml` 更新 Stage 1 docs branch 指令。
  2. 已在 `Ai_AutoSDLC` 的 `src/ai_sdlc/rules/git-branch.md`、`pipeline.md`、`scenario-routing.md` 同步规则真值。
  3. 已在 `Ai_AutoSDLC` 的 `tests/integration/test_cli_stage.py` 增加 docs branch 命名回归。
