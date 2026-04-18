# Release Gate Evidence: 003-runtime-state-recovery

本文件记录 `003-runtime-state-recovery` 在 close-out 阶段的结构化发布证据。

```json
{
  "release_gate_evidence": {
    "overall_verdict": "PASS",
    "checks": [
      {
        "name": "recoverability",
        "verdict": "PASS",
        "evidence_source": "backend/tests/test_processing_recovery.py; specs/003-runtime-state-recovery/task-execution-log.md",
        "reason": "恢复回归继续通过，服务启动恢复后的批次仍能回到工作台可识别的活跃阶段。"
      },
      {
        "name": "portability",
        "verdict": "PASS",
        "evidence_source": "pyproject.toml; workspace_tools/cli.py; backend/tests/test_workspace_cli.py; specs/003-runtime-state-recovery/task-execution-log.md",
        "reason": "仓库根环境现在直接提供 `uv run pytest -q` 与 `uv run ruff check` 入口，通过 repo-level wrapper 统一委派到 backend dev 环境和 repo-local uvx ruff 工具目录，不再依赖本地 PATH 或手工 fallback。"
      },
      {
        "name": "multi_ide",
        "verdict": "PASS",
        "evidence_source": "specs/003-runtime-state-recovery/spec.md; specs/003-runtime-state-recovery/task-execution-log.md",
        "reason": "本次收口只补 formal artifact 与规格真值，不引入新的 IDE 绑定文件、宿主特化脚本或编辑器耦合逻辑。"
      },
      {
        "name": "stability",
        "verdict": "PASS",
        "evidence_source": "frontend/tests/runtime-ui.test.tsx; backend/tests/test_progress_reporting.py; backend/tests/test_processing_recovery.py",
        "reason": "前端运行时工作台回归和后端进度/恢复回归均通过，现有行为保持稳定。"
      }
    ]
  }
}
```
