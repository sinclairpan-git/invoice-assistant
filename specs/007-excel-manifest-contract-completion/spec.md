# 功能规格：导出台账字段补齐

**功能编号**：`007-excel-manifest-contract-completion`
**创建日期**：2026-04-19
**状态**：已完成实现、验证与 dry-run 收口（2026-04-19）
**输入**：按顶层 backlog 继续执行 P8：补齐 excel_manifest 与设计基线/四期导出规格之间缺失的台账字段，优先覆盖疑似重复标记、购方税号、购方地址/电话/开户银行/银行账户、开票日期、销售方名称、发票明细摘要、处理时间，并用红绿测试锁定当前导出契约。 参考：`docs/invoice-assistant-gap-backlog.zh-CN.md`、`specs/004-controlled-review-export/spec.md`、`docs/superpowers/specs/2026-04-17-invoice-assistant-design.md`

**范围**：

- 覆盖 `backend/app/services/export_service.py` 中 `excel_manifest` 的列定义与行构建逻辑。
- 覆盖 `backend/tests/test_export_service.py` 对 manifest 字段契约的红绿测试。
- 覆盖必要的字段组装辅助逻辑，包括从 `InvoiceRecord`、`ExtractedField`、`DocumentEvidence`、`ProcessingAttempt` 派生 manifest 列值。
- 覆盖本 work item 的 formal docs、任务分解和执行归档。
- 不覆盖 OCR / 解析器新增字段抽取能力；仅消费当前已落库或已可派生的数据。
- 不覆盖前端术语统一、详情抽屉改版、导出新文件格式或外部对接。

## 用户场景与测试（必填）

### 用户故事 1 - 财务台账导出需要完整基础字段（优先级：P0）

作为导出责任人，我希望 Excel 台账至少包含购方税号、购方地址/电话/开户银行/银行账户、开票日期、销售方名称和处理时间，这样导出的台账能直接用于财务复核和归档，而不是再回到单票详情手工补字段。

**优先级说明**：这些字段属于设计基线中已定义的最小台账信息面；若导出缺失，`excel_manifest` 虽然可生成，但不能作为完整财务产物。

**独立测试**：后端导出服务测试验证生成的 sheet XML 中稳定包含新增列头和对应值。

**验收场景**：

1. **Given** 一张已完成处理的发票含有 `buyer_tax_no`、`invoice_date`、`seller_name` 与买方校验提取字段，**When** 用户导出 `excel_manifest`，**Then** 台账中能看到这些列头和值。
2. **Given** 一张发票已有处理完成时间，**When** 用户导出 `excel_manifest`，**Then** 台账中会写出稳定的“处理时间”列，而不是空白。

---

### 用户故事 2 - 问题票需要在台账中可解释（优先级：P0）

作为复核人员，我希望 manifest 对问题票能直接体现“疑似重复标记”和“发票明细摘要”，这样我不用打开 ZIP 或详情页才能理解为什么该票进入问题集合。

**优先级说明**：四期规格已经把解释面补到了单票详情；如果台账仍缺解释字段，导出和界面就会口径不一致。

**独立测试**：后端导出服务测试验证 manifest 中存在“疑似重复标记”“发票明细摘要”列，且值与当前发票事实一致。

**验收场景**：

1. **Given** 一张重复票 `duplicate_flag=true`，**When** 用户导出 `excel_manifest`，**Then** 台账中“疑似重复标记”为“是”。
2. **Given** 发票证据中已有 `line_text` / table lines，**When** 用户导出 `excel_manifest`，**Then** 台账中“发票明细摘要”会输出稳定的精简摘要。

---

### 边界情况

- 当某些扩展字段当前未被解析到时，manifest 应输出空字符串，而不是抛错或阻断导出。
- “处理时间”优先取最新成功处理 attempt 的 `completed_at`；若没有，则允许留空。
- “发票明细摘要”只消费当前已落库的证据文本，不新增新一轮 OCR/规则推断。
- 本轮不要求补齐设计基线中的所有未来字段，只处理当前代码库已有数据来源支持的缺口列。

## 需求（必填）

### 功能需求

- **FR-001**：`excel_manifest` 必须补齐以下列头：`疑似重复标记`、`购方税号`、`购方地址`、`购方电话`、`开户银行`、`银行账户`、`开票日期`、`销售方名称`、`发票明细摘要`、`处理时间`。
- **FR-002**：manifest 行数据必须优先复用当前已落库的 `InvoiceRecord` 字段，不新增数据库 schema。
- **FR-003**：`购方地址`、`购方电话`、`开户银行`、`银行账户` 必须从现有 `ExtractedField` / `FieldCheck` 可见信息中派生；缺失时输出空字符串。
- **FR-004**：`发票明细摘要` 必须从现有证据文本中提取精简摘要，优先使用 `DocumentEvidence.table_lines`，其次回退到 `text_blocks` / `raw_text` 中可用的首条业务行。
- **FR-005**：`处理时间` 必须使用当前发票最新处理 attempt 的完成时间，并以稳定字符串格式写入 manifest。
- **FR-006**：现有四期导出门槛、审计逻辑、附件列和合规解释列不得回退。
- **FR-007**：系统必须补齐导出服务测试，锁定新增列头和值，避免后续再次出现“设计有字段、manifest 无字段”的漂移。

### 关键实体（如涉及数据则必填）

- **ManifestRow**：`excel_manifest` 的单票行输出，需要把发票、解释、附件和新增补齐字段收敛为稳定列集合。
- **InvoiceRecord**：manifest 主数据来源，提供重复标记、税号、日期、金额、销方、购方等字段。
- **ExtractedField / DocumentEvidence / ProcessingAttempt**：manifest 的补充数据来源，用于派生买方扩展字段、明细摘要和处理时间。

## 成功标准（必填）

### 可度量结果

- **SC-001**：`backend/tests/test_export_service.py` 能稳定断言新增 10 个列头存在，且关键样例值正确。
- **SC-002**：`excel_manifest` 导出继续成功，且现有 `record_count`、`suggested_pass_count`、`suggested_pass_total_amount` 摘要契约不回退。
- **SC-003**：对重复票、缺字段票和普通通过票三类场景，manifest 都能输出可解释的稳定值或空值，不抛异常。
