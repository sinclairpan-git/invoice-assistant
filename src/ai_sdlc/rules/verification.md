# AI-SDLC Verification Profiles

本项目遵循“先文档、再实现”的 AI-SDLC 约束，验证画像与命令面如下。

## Profiles

- `docs-only`
- `rules-only`
- `truth-only`
- `code-change`

## Required Commands

- 基线约束验证：`uv run ai-sdlc verify constraints`
- canonical truth 同步预演：`python -m ai_sdlc program truth sync --dry-run`
- 代码变更测试：`uv run pytest`
- 代码变更静态检查：`uv run ruff check`

## Notes

- 文档或规则变更阶段先完成文档收敛，再推进实现。
- `truth-only` 仅用于 canonical truth 同步，不替代代码或文档验证。
- `code-change` 需要同时保留测试、静态检查与约束验证证据。
