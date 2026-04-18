# Release Gate Evidence: 003-runtime-state-recovery

本文件记录 `003-runtime-state-recovery` 在 close-out 阶段的结构化发布证据。

```json
{
  "release_gate_evidence": {
    "overall_verdict": "WARN",
    "checks": [
      {
        "name": "recoverability",
        "verdict": "PASS",
        "evidence_source": "backend/tests/test_processing_recovery.py; specs/003-runtime-state-recovery/task-execution-log.md",
        "reason": "恢复回归继续通过，服务启动恢复后的批次仍能回到工作台可识别的活跃阶段。"
      },
      {
        "name": "portability",
        "verdict": "WARN",
        "evidence_source": "specs/003-runtime-state-recovery/task-execution-log.md",
        "reason": "当前仓库根环境未直接暴露 pytest 与 ruff 裸入口，close-out 需要使用 backend scoped fallback 命令，说明环境可移植性仍依赖本地约定。"
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
