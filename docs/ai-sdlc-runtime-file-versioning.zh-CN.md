# AI-SDLC 运行态文件版本控制审计

## 目的

归档 2026-04-19 对 `.ai-sdlc/` 目录的版本控制边界审计，并明确本仓库对运行态文件的纳管策略。

## 审计起点（执行前）

- 已跟踪文件：
  - `.ai-sdlc/memory/constitution.md`
  - `.ai-sdlc/profiles/tech-stack.yml`
  - `.ai-sdlc/profiles/decisions.yml`
  - `.ai-sdlc/project/config/project-config.yaml`
  - `.ai-sdlc/project/config/project-state.yaml`
- 已忽略目录：
  - `.ai-sdlc/local/`
  - `.ai-sdlc/state/`
  - `.ai-sdlc/work-items/`

## 执行后状态

- 继续受版本控制：
  - `.ai-sdlc/project/config/project-state.yaml`
- 停止跟踪并保留本地运行：
  - `.ai-sdlc/project/config/project-config.yaml`

## 事实

1. 当前工作区唯一相关脏改动来自 `.ai-sdlc/project/config/project-config.yaml`，差异仅为 `adapter_activated_at` 时间戳。
2. AI-SDLC 上游实现将 `project-config.yaml` 定义为“often gitignored”：
   - `src/ai_sdlc/models/project.py`
   - `src/ai_sdlc/core/config.py`
   - `src/ai_sdlc/stages/init.yaml`
3. AI-SDLC 上游实现说明：当 `project-config.yaml` 缺失时，加载逻辑返回默认配置；后续保存或 IDE 适配会重新生成该文件。
4. `project-state.yaml` 是 init 阶段显式输出物，也是 pipeline gate 读取对象；当前没有同等证据表明它应默认移出版本控制。
5. 仅新增 `.gitignore` 规则不足以解决问题，因为 `project-config.yaml` 已经被 Git 跟踪；若要消除这类运行态 diff，必须停止跟踪该文件。
6. `project-state.yaml` 当前只包含 6 个低频字段：`status`、`project_name`、`initialized_at`、`last_updated`、`next_work_item_seq`、`version`。
7. AI-SDLC 上游仅在少数“项目真值变化”路径写回 `project-state.yaml`：
   - `bootstrap` 初始化项目时写入初值
   - `work_intake` 创建 intake work item 时推进 `next_work_item_seq`
   - `workitem_scaffold` 直接初始化 formal work item 时推进 `next_work_item_seq`
8. `python -m ai_sdlc run --dry-run` 不会改写 `project-state.yaml`；本轮审计中工作区在 dry-run 后保持干净。
9. 仓库历史中，`project-state.yaml` 的提交只出现在基线初始化、work item 序号推进、运行态恢复收口等少量节点，并未表现出类似 `project-config.yaml` 的频繁时间戳噪音。

## 结论

### P1 立即执行：停止跟踪 `project-config.yaml`

- **状态**：本轮执行
- **原因**：
  - 文件内容以 IDE 适配状态、激活证据、时间戳等运行态元数据为主
  - 上游实现已明确按“通常应被 gitignore”设计
  - 继续跟踪只会让 `adapter activate` 一类常规动作不断制造无意义 diff

### P2 保持 `project-state.yaml` 继续受控

- **状态**：保留
- **原因**：
  - 该文件承载初始化状态、序列号等流水线真值
  - 现阶段缺少足够证据支持把它也降为纯运行态
  - 缺失该文件会破坏 AI-SDLC formal bootstrap / work item 初始化入口
  - 它的变更频率与“项目状态跃迁”相关，而不是与每次日常命令执行相关

### P3 不采用 `skip-worktree` 作为仓库方案

- **状态**：拒绝
- **原因**：
  - 这是本地掩盖手段，不是团队可见策略
  - 容易把真正需要审阅的配置改动一起藏掉

## 本轮落地动作

1. 在 `.gitignore` 中显式忽略 `.ai-sdlc/project/config/project-config.yaml`
2. 将 `project-config.yaml` 从 Git 跟踪集合移除，但保留本地文件供 AI-SDLC 继续读写
3. 执行 `python -m ai_sdlc run --dry-run`，确认仓库约定未被破坏

## 后续约束

1. 功能提交、文档提交、归档提交均不再混入 `project-config.yaml` 的运行态变更。
2. 若未来确实需要持久化非默认的稳定项目级配置，应新增专门的受控模板/默认文件，而不是重新把运行态文件纳回版本控制。
3. `project-state.yaml` 只应在以下场景进入提交：
   - 项目初始化或 bootstrap 修复
   - 新建 canonical work item 导致 `next_work_item_seq` 合法推进
   - 经确认的状态恢复/真值修复
4. 在没有新的上游证据前，不扩展到 `.ai-sdlc/project/config/project-state.yaml`。
