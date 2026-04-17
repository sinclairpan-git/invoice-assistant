# 数据模型：发票整理助手一期 MVP

## 1. 建模原则

1. 业务主记录、证据记录、规则版本和人工动作分层保存，避免一个对象承担过多职责。
2. 原始文件、重命名文件和导出文件分目录存储，数据库只保存路径与元数据。
3. 统计口径采用派生字段和可复算规则，不在多个位置手写重复逻辑。

## 2. 核心实体

### 2.1 Batch

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 批次主键 |
| `batch_no` | TEXT | 可读批次编号 |
| `created_at` | DATETIME | 创建时间 |
| `created_by` | TEXT | 本机操作者名 |
| `status` | TEXT | `queued / processing / completed / failed` |
| `total_files` | INTEGER | 总文件数 |
| `completed_files` | INTEGER | 已完成数 |
| `processing_files` | INTEGER | 处理中数 |
| `failed_files` | INTEGER | 失败数 |
| `suggested_pass_count` | INTEGER | 建议通过数量，排除疑似重复 |
| `suggested_pass_total_amount` | DECIMAL(18,2) | 建议通过总金额，排除疑似重复 |
| `tax_profile_version_id` | TEXT | 税务档案版本 |
| `business_rule_version_id` | TEXT | 风险规则版本 |
| `naming_rule_version_id` | TEXT | 命名模板版本 |
| `snapshot_json` | JSON / TEXT | 批次创建时固化的规则快照 |
| `export_manifest_path` | TEXT | 最近一次导出清单路径，可为空 |

### 2.2 InvoiceRecord

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 发票记录主键 |
| `batch_id` | TEXT | 所属批次 |
| `original_filename` | TEXT | 原文件名 |
| `renamed_filename` | TEXT | 新文件名，可为空 |
| `storage_path_original` | TEXT | 原始文件路径 |
| `storage_path_renamed` | TEXT | 重命名文件路径，可为空 |
| `file_sha256` | TEXT | 原始文件摘要，便于排查重复导入 |
| `invoice_code` | TEXT | 发票代码，可为空 |
| `invoice_number` | TEXT | 发票号码 |
| `seller_name` | TEXT | 销售方名称 |
| `buyer_name` | TEXT | 购方名称，可为空 |
| `buyer_tax_no` | TEXT | 购方税号，可为空 |
| `invoice_date` | DATE | 开票日期，可为空 |
| `invoice_amount` | DECIMAL(18,2) | 金额，可为空 |
| `parse_source` | TEXT | `text` / `ocr` |
| `processing_status` | TEXT | 处理状态 |
| `system_decision` | TEXT | 系统判定 |
| `review_status` | TEXT | 人工复核状态 |
| `artifact_status` | TEXT | 文件产物状态 |
| `duplicate_flag` | BOOLEAN | 是否疑似重复 |
| `duplicate_group_key` | TEXT | 疑似重复分组键，可为空 |
| `risk_flags` | JSON / TEXT | 风险标记列表 |
| `display_status` | TEXT | 页面派生展示状态 |
| `problem_count` | INTEGER | 问题数量 |
| `failure_reason` | TEXT | 处理失败原因，可为空 |

### 2.3 DocumentEvidence

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 证据记录主键 |
| `invoice_id` | TEXT | 关联发票 |
| `source_type` | TEXT | `text` / `ocr` |
| `raw_text` | TEXT | 原始文本 |
| `pages_json` | JSON / TEXT | 页级信息 |
| `text_blocks_json` | JSON / TEXT | 文本块 |
| `table_lines_json` | JSON / TEXT | 明细表格线索 |
| `field_candidates_json` | JSON / TEXT | 候选字段 |
| `confidence_summary_json` | JSON / TEXT | 置信度摘要 |
| `provider_name` | TEXT | 解析供应商 |
| `provider_version` | TEXT | 供应商版本 |
| `provider_error_code` | TEXT | 失败码，可为空 |

### 2.4 ExtractedField

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 主键 |
| `invoice_id` | TEXT | 关联发票 |
| `field_name` | TEXT | 字段名 |
| `extracted_value` | TEXT | 原始抽取值 |
| `normalized_value` | TEXT | 标准化值 |
| `confidence` | DECIMAL(5,4) | 置信度 |
| `page_no` | INTEGER | 页码 |
| `source_fragment` | TEXT | 证据片段 |
| `bbox_json` | JSON / TEXT | OCR 位置框，可为空 |

### 2.5 FieldCheck

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 主键 |
| `invoice_id` | TEXT | 关联发票 |
| `field_name` | TEXT | 比对字段 |
| `expected_value` | TEXT | 期望值 |
| `actual_value` | TEXT | 实际值 |
| `match_result` | TEXT | `matched / mismatched / low_confidence / missing` |
| `reason` | TEXT | 说明 |

### 2.6 RuleVersion

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 主键 |
| `kind` | TEXT | `tax_profile / business_rules / naming_rules` |
| `version_no` | TEXT | 版本号 |
| `content_json` | JSON / TEXT | 配置内容 |
| `changed_by` | TEXT | 变更人 |
| `changed_at` | DATETIME | 变更时间 |
| `change_reason` | TEXT | 变更说明 |

### 2.7 ReviewAction

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 主键 |
| `invoice_id` | TEXT | 关联发票 |
| `review_action` | TEXT | `approve / reject / keep_review_required` |
| `review_note` | TEXT | 备注 |
| `reviewed_by` | TEXT | 操作者 |
| `reviewed_at` | DATETIME | 操作时间 |

### 2.8 ExportJob

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID / TEXT | 主键 |
| `batch_id` | TEXT | 关联批次 |
| `export_type` | TEXT | `suggested_pass_zip / issue_zip / excel_manifest` |
| `status` | TEXT | `queued / completed / failed` |
| `output_path` | TEXT | 导出产物路径 |
| `created_by` | TEXT | 导出人 |
| `created_at` | DATETIME | 导出时间 |
| `summary_json` | JSON / TEXT | 数量与金额摘要 |

## 3. 状态模型

### 3.1 `processing_status`

- `queued`
- `extracting`
- `classifying`
- `completed`
- `failed`

### 3.2 `system_decision`

- `suggested_pass`
- `suggested_reject`
- `review_required`
- `processing_failed`

### 3.3 `review_status`

- `not_reviewed`
- `manually_approved`
- `manually_rejected`

### 3.4 `artifact_status`

- `original_only`
- `renamed_ready`
- `exported`

### 3.5 `display_status`

由 `processing_status`、`system_decision` 和 `duplicate_flag` 派生：

1. 处理失败优先显示 `处理失败`
2. `duplicate_flag = true` 显示 `疑似重复`
3. `system_decision = review_required` 显示 `待复核`
4. `system_decision = suggested_reject` 显示 `系统建议驳回`
5. `system_decision = suggested_pass` 显示 `系统建议通过`

## 4. 关键索引与约束

1. `InvoiceRecord(batch_id, display_status)`：支撑结果页筛选。
2. `InvoiceRecord(invoice_number, invoice_code, invoice_date, invoice_amount, seller_name)`：支撑疑似重复检测。
3. `ExtractedField(invoice_id, field_name)`：支撑详情抽屉字段展示。
4. `FieldCheck(invoice_id, field_name)`：支撑购方校验逐项解释。
5. `RuleVersion(kind, version_no)`：保证配置中心版本可追溯。
6. `ReviewAction(invoice_id, reviewed_at)`：支撑人工复核历史查询。

## 5. 文件系统布局

```text
storage/
├── originals/<batch_no>/
├── renamed/<batch_no>/
├── exports/<batch_no>/
└── temp/
```

- `originals/` 只写入原始文件，不做覆盖修改。
- `renamed/` 保存重命名后的文件。
- `exports/` 保存 ZIP、Excel 与导出清单。
- 数据库仅保存相对路径与摘要，不保存二进制内容。

## 6. 与业务规则的关系

1. 购方档案、业务风险分类规则、命名模板统一以 `RuleVersion` 版本化。
2. `Batch.snapshot_json` 固化批次启动时使用的规则快照，避免后续配置修改影响历史解释。
3. 系统建议通过统计只基于 `InvoiceRecord.system_decision = suggested_pass` 且 `duplicate_flag = false`。

## 7. 结论

该数据模型已经覆盖第一期的批次处理、证据标准化、规则判定、人工复核、导出和审计留痕需求，可直接作为 execute 阶段的数据库与领域模型基线。
