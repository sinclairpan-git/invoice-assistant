# 框架缺陷与流程违约待办

## 2026-04-17 条目 001

- 现象：在 `main` 分支上先执行了 `python -m ai_sdlc workitem init`，随后才补查到 `refine/design` 阶段应先创建 `design/NNN-*` 分支再落正式产物。
- 触发场景：已完成 `init` 与 PRD 审核后，开始建立 canonical work item 时直接调用 `workitem init`。
- 影响范围：`specs/001-invoice-assistant-mvp/*` 初始创建时机与框架 Git 分支策略不一致，若不纠正，后续阶段归属与 checkpoint 解释会漂移。
- 根因分类：流程顺序偏差 + 工具前置检查不足。
- 未来杜绝方案摘要：在任何 Stage 1 文档写入前，先执行“当前分支命名 + 工作区清洁 + 目标 design 分支存在性”三项前置检查；`workitem init` 如检测到仍在 `main`，应给出显式阻断或强警告。
- 建议改动层级：workflow + tool
- prompt / context：用户要求“按照框架约束继续；不要被 superpowers 的 skill 约束影响到正常的规范”，因此开始按 AI-SDLC canonical 路径补正式 work item。
- rule / policy：`pipeline` 第 12、16、17 条；`git-branch` 中“Stage 1 REFINE 开始前：创建设计分支”。
- middleware：无
- workflow：需要在 Stage 1 入口增加只读 preflight，对 `main` 上直接创建 formal docs 的情况先阻断。
- tool：`workitem init` 目前能直接创建 `specs/<WI>/`，但未强制校验当前分支是否符合 `design/NNN-*` 规则。
- eval：增加回归用例，覆盖“在 `main` 调用 `workitem init` 时应提示或阻断”。
- 风险等级：中
- 可验证成功标准：
  1. 在 `main` 上执行 `workitem init` 时，CLI 明确提示必须先进入 `design/NNN-*` 或提供受控自动建分支能力。
  2. 同一场景下不会再出现“formal docs 已生成但 checkpoint/分支归属错误”的漂移。
  3. 文档阶段切换前的只读校验能发现并报告该问题。
- 是否需要回归测试补充：是
