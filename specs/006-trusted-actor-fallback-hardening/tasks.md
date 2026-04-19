---
related_doc:
  - "docs/invoice-assistant-gap-backlog.zh-CN.md"
  - "specs/004-controlled-review-export/spec.md"
  - "docs/superpowers/specs/2026-04-17-invoice-assistant-design.md"
---
# 任务分解：可信操作者 fallback 收口

**编号**：`006-trusted-actor-fallback-hardening` | **日期**：2026-04-19
**来源**：plan.md + spec.md

---

## 分批策略

```text
Batch 1: 文档基线冻结
Batch 2: trusted actor 依赖与受控写接口
Batch 3: 定向验证与归档
```

---

## Batch 1：文档基线冻结

### Task 1.1 替换 006 占位 spec 为正式治理范围

- **任务编号**：T11
- **优先级**：P0
- **依赖**：无
- **文件**：spec.md, plan.md, tasks.md, task-execution-log.md
- **可并行**：否
- **验收标准**：
  1. `spec.md` 明确 trusted actor fallback 的覆盖范围、非目标、用户故事、功能需求与成功标准。
  2. 006 不再保留脚手架占位文本或与当前仓库无关的内容。
- **验证**：文档对账
- **状态**：已完成

### Task 1.2 固化实施计划与验证顺序

- **任务编号**：T12
- **优先级**：P0
- **依赖**：T11
- **文件**：plan.md
- **可并行**：否
- **验收标准**：
  1. `plan.md` 明确 trusted actor 依赖、受控写接口、测试与回退边界。
  2. 计划不把 Excel manifest、`default_operator_name` 或术语统一混入本期实现。
- **验证**：文档对账
- **状态**：已完成

### Task 1.3 建立真实执行日志基线

- **任务编号**：T13
- **优先级**：P1
- **依赖**：T11
- **文件**：task-execution-log.md
- **可并行**：是
- **验收标准**：
  1. 首批日志准确记录对抗评审结论、分支切换、`adapter activate` 与 `run --dry-run` 入口。
  2. 执行日志不再保留 direct-formal 脚手架占位描述。
- **验证**：文档对账
- **状态**：已完成

## Batch 2：trusted actor 依赖与受控写接口

### Task 2.1 红灯测试覆盖 trusted actor 缺失与请求体伪造姓名

- **任务编号**：T21
- **优先级**：P0
- **依赖**：T11
- **文件**：`backend/tests/test_api_workflows.py`
- **可并行**：否
- **验收标准**：
  1. 用例先暴露 trusted actor 缺失时 `/api/me` 与受控写接口仍然错误放行或返回伪造身份的问题。
  2. 用例先暴露已配置 trusted actor 时，请求体 `created_by` / `changed_by` / `reviewed_by` 仍能影响后端记录的问题。
- **验证**：`python -m pytest backend/tests/test_api_workflows.py -q`
- **状态**：已完成

### Task 2.2 实现 trusted actor 依赖真值收口

- **任务编号**：T22
- **优先级**：P0
- **依赖**：T21
- **文件**：`backend/app/api/dependencies.py`, `backend/app/api/actors.py`, `backend/app/api/batches.py`, `backend/app/api/config.py`, `backend/app/api/invoices.py`
- **可并行**：否
- **验收标准**：
  1. trusted actor 缺失或无效时，`/api/me` 与受控写接口返回明确配置错误，不再回退到全角色本机管理员。
  2. trusted actor 已配置时，后端忽略请求体伪造姓名，继续使用后端 actor `display_name`。
  3. 既有 `403` 角色拒绝与 denied audit 路径保持不回退。
- **验证**：`python -m pytest backend/tests/test_api_workflows.py -q`
- **状态**：已完成

## Batch 3：定向验证与归档

### Task 3.1 完成定向回归与 dry-run 收口

- **任务编号**：T31
- **优先级**：P1
- **依赖**：T22
- **文件**：测试与文档归档文件
- **可并行**：否
- **验收标准**：
  1. trusted actor 相关定向测试通过。
  2. `python -m ai_sdlc run --dry-run` 继续通过，且不因 006 的文档与代码改动引入新的 close-stage blocker。
- **验证**：`python -m pytest backend/tests/test_api_workflows.py -q`，`python -m ai_sdlc run --dry-run`
- **状态**：已完成
