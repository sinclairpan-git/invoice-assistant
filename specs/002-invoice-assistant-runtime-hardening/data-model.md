# 数据模型：发票整理助手二期：真实解析与运行时加固

## 1. 建模目标

二期的数据建模不是替换一期实体，而是在一期实体之上补足三类能力：

1. 真实解析运行时的 provider 诊断。
2. 异步批处理作业与单票尝试记录。
3. 服务重启后的恢复与重试幂等性。

## 2. 延续一期的核心实体

### 2.1 Batch

保留一期的批次主语义，继续作为用户看到的“批次”对象，已存在字段包括：

- `batch_no`
- `status`
- `total_files`
- `completed_files`
- `processing_files`
- `failed_files`
- `suggested_pass_count`
- `suggested_pass_total_amount`
- `snapshot_json`

二期建议新增的运行时字段：

- `active_job_id`：当前关联的 `ProcessingJob`。
- `last_recovered_at`：最近一次恢复时间。
- `last_stage_code`：最近一次可展示阶段代码。
- `last_stage_text`：最近一次可展示阶段文案。

### 2.2 InvoiceRecord

继续作为单张发票的主业务记录，保留一期的业务字段、系统判定、人工复核、疑似重复和失败原因。

二期建议新增字段：

- `processing_stage`：当前细粒度阶段，例如 `text_extraction`、`ocr_processing`、`classification`、`finalization`。
- `last_attempt_id`：当前生效的 `ProcessingAttempt`。
- `retry_count`：累计人工或系统重试次数。
- `last_error_stage`：最近一次失败发生在哪个阶段。
- `last_error_code`：最近一次失败的 provider / runtime 错误码。
- `last_error_message`：最近一次失败摘要。
- `retryable`：最近一次失败是否允许重试。

说明：
- `processing_status` 继续承担高层状态，例如 `queued`、`processing`、`completed`、`processing_failed`。
- `processing_stage` 用于补足前端阶段文案与恢复定位，不替代 `processing_status`。

### 2.3 DocumentEvidence / ExtractedField / FieldCheck

这三类实体继续承担统一证据与字段解释职责，不改变一期核心职责。

二期主要变化：

- `DocumentEvidence` 的 `provider_name`、`provider_version`、`provider_error_code` 必须真实反映当前 provider。
- 必要时补充 `provider_error_message`、`attempt_id` 或 `confidence_summary_json` 细化字段。
- `ExtractedField` 与 `FieldCheck` 建议增加 `attempt_id` 或逻辑上的“当前有效 attempt”绑定，以避免重试后重复累计旧结果。

## 3. 二期新增实体

### 3.1 ProcessingJob

批次级后台作业实体，建议字段如下：

- `id`
- `batch_id`
- `status`：`queued` / `running` / `recovering` / `completed` / `completed_with_failures` / `failed`
- `current_stage`
- `total_items`
- `completed_items`
- `failed_items`
- `created_at`
- `started_at`
- `completed_at`
- `last_heartbeat_at`
- `recovery_token`
- `summary_json`

职责：
- 作为批次后台执行的持久化入口。
- 为前端轮询提供批次级进度快照。
- 为服务启动恢复逻辑提供扫描对象。

### 3.2 ProcessingAttempt

单票级尝试实体，建议字段如下：

- `id`
- `job_id`
- `invoice_id`
- `attempt_no`
- `status`：`queued` / `running` / `succeeded` / `failed` / `retryable_failed`
- `stage`
- `parse_source`
- `provider_name`
- `provider_version`
- `error_code`
- `error_message`
- `retryable`
- `input_sha256`
- `started_at`
- `completed_at`
- `diagnostic_json`

职责：
- 记录某张票一次完整处理或重试的生命周期。
- 把 provider 诊断与业务主表解耦。
- 作为恢复、重试和幂等性的最小跟踪单元。

唯一性建议：
- `invoice_id + attempt_no` 唯一。
- 同一时刻仅允许一个 `running` 状态 attempt 绑定到某张票。

### 3.3 ProviderDiagnostic

可作为独立表，也可嵌入 `ProcessingAttempt.diagnostic_json`。建议至少包含：

- `provider_name`
- `provider_version`
- `stage`
- `error_code`
- `error_message`
- `confidence_summary`
- `fallback_trigger`

职责：
- 把“为什么走 OCR”“为什么失败”“为何进入待复核”从日志提升为结构化诊断。
- 为详情页、失败列表和运维排查提供统一来源。

## 4. 状态机建议

### 4.1 Job 状态机

`queued -> running -> completed`

异常分支：

- `queued -> running -> completed_with_failures`
- `running -> recovering -> running`
- `running -> failed`

说明：
- `completed_with_failures` 表示批次整体已收口，但存在失败子项。
- `recovering` 只代表服务正在回收失联作业，不代表业务失败。

### 4.2 Invoice 高层状态

- `queued`
- `processing`
- `completed`
- `processing_failed`
- `waiting_retry`

### 4.3 Invoice 细粒度阶段

- `queued`
- `text_extraction`
- `ocr_processing`
- `classification`
- `duplicate_check`
- `finalization`
- `completed`
- `failed`

说明：
- 细粒度阶段用于展示和恢复，不直接等同于最终业务结论。
- `review_required`、`suggested_reject`、`suggested_pass` 仍通过 `system_decision` 和 `display_status` 表达。

## 5. 幂等性与一致性约束

1. 单票的当前有效证据、字段和校验结果只能关联到当前有效 attempt。
2. 重试时，旧 attempt 的中间产物必须失效或隔离，不能继续参与金额统计、导出和详情展示。
3. 批次统计必须由当前有效 `InvoiceRecord` 状态汇总，而不是由 attempt 数量推导。
4. 恢复逻辑只能回收运行中且失联的 attempt，不能覆盖已完成 attempt 的最终状态。
5. 导出必须以当前有效 `InvoiceRecord` 为准，避免同票多次 attempt 造成重复导出。

## 6. 文件与目录约定

在沿用一期目录的基础上，二期建议新增或细化：

- `storage/originals/<batch_no>/`：原始文件。
- `storage/renamed/<batch_no>/`：重命名后的有效文件。
- `storage/intermediate/<batch_no>/<invoice_id>/attempt-<n>/`：解析中间产物、OCR 缓存或诊断文件。
- `storage/exports/<batch_no>/`：导出产物。

约束：
- 原始文件不可变。
- 中间产物按 attempt 隔离。
- 导出产物只指向当前有效结果。

## 7. 与一期兼容性要求

1. `Batch.suggested_pass_total_amount` 的业务语义不变。
2. `ReviewAction` 仍只做人工留痕，不覆盖 `system_decision`。
3. `DocumentEvidence` 仍是规则层与展示层的统一真源，新增 provider 能力只做加法。
4. 异步化和恢复不应改变前端页面已经依赖的主要字段语义，只允许补充更细粒度的阶段与失败信息。
