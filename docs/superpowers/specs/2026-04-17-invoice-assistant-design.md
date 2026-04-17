# 发票整理助手设计文档

> Source of truth for Phase 1. This document supersedes conflicting technical options that still appear in the source PRD at `/Users/sinclairpan/project/发票整理助手/发票整理助手_评审终版_重新生成.md`.

## 1. 产品定位

发票整理助手是一个面向企业内部报销初审场景的本机 Web 应用。它的职责是把批量 PDF 发票完成以下动作：

- 提取票面关键信息
- 执行购方信息严格校验
- 执行票面业务风险分类
- 检测疑似重复发票
- 自动重命名和分组整理
- 给出可解释的系统建议结果

它不是最终财务裁决系统，不直接代表最终可报销结论，也不承担真伪联网查验、正式入账或付款审批。

## 2. 第一期生效基线

以下内容是第一期唯一生效的设计基线：

- 部署形态：单机运行，本机浏览器访问本地服务
- 使用角色：单管理员，无登录流程
- 技术栈：
  - 前端：React + Vite + TypeScript + Ant Design
  - 后端：FastAPI + SQLAlchemy + Pydantic
  - 本地数据库：SQLite
  - 本地文件存储：本地目录
  - 后台任务：本地任务执行器，单写者模型
- 识别路线：文本提取优先，本地 OCR 兜底，接口层预留切换外部 API 的能力
- 页面结构：批次工作台、批次结果页、发票详情抽屉、配置中心
- 范围包含：主处理链路、配置中心、导出、最小人工复核、最小重复票检测、配置变更留痕

以下内容在第一期不生效，即使源 PRD 中仍有旧描述：

- Next.js
- shadcn/ui
- Redis / Celery / PostgreSQL
- 普通用户与管理员多角色体系
- 多人并发访问
- ERP / OA / 报销系统集成

## 3. 第一期开闭范围

### 3.1 必须完成

1. 批量上传 PDF 发票
2. 建立批次并展示处理进度
3. PDF 文本提取，失败后走 OCR 兜底
4. 输出统一的文档证据模型
5. 提取关键字段并记录置信信息
6. 购方字段严格校验
7. 票面业务风险分类
8. 历史库内疑似重复票检测
9. 自动重命名与结果分组
10. 结果页筛选、详情解释、导出 ZIP / Excel
11. 配置中心
12. 配置版本、批次规则快照、人工复核留痕
13. 系统建议通过金额汇总

### 3.2 明确不做

- 登录和权限体系
- 真伪联网查验、作废/红冲联网校验
- 图片文件直接上传
- 多公司主体
- 通用业务规则平台
- 多机部署和多人实时协作
- 与外部报销系统打通

## 4. 成功标准

第一期成功不以“自动判完所有票”为目标，而以以下结果为目标：

- 标准电子发票能稳定抽取关键字段
- 明确符合规则的票能被系统建议通过
- 明确不符合规则的票能被系统建议驳回
- 边界票、低置信票、混合票、疑似重复票被稳妥送去人工复核
- 每一张票的系统结论都能解释来源
- 管理员可以追溯某个批次使用的是哪一版规则和税务档案

## 5. 用户与主要流程

第一期只有一个用户角色：本机管理员。

管理员的主流程：

1. 在批次工作台上传一批 PDF
2. 查看批次进度和分组统计
3. 进入批次结果页筛选系统建议通过、系统建议驳回、待复核、疑似重复、处理失败
4. 打开详情抽屉查看字段提取结果、比对结果、业务风险依据、疑似重复依据
5. 对待复核或疑似重复票做最小人工复核并记录备注
6. 导出系统建议通过 ZIP、问题票 ZIP、Excel 台账

## 6. 页面结构

### 6.1 批次工作台

首页采用批次工作台，不采用纯上传页。

展示内容：

- 新建批次上传区
- 最近批次列表
- 每批次基础统计：
  - 总文件数
  - 已完成数
  - 处理中数
  - 失败数
  - 系统建议通过数量（不含疑似重复）
  - 系统建议通过金额（不含疑似重复）
- 当前活跃批次进度条和阶段文案

### 6.2 批次结果页

顶部汇总区展示两层金额：

- 批次系统建议通过金额：当前批次内 `system_decision = suggested_pass` 且 `duplicate_flag = false` 的总金额
- 当前筛选下系统建议通过金额：当前筛选结果内 `system_decision = suggested_pass` 且 `duplicate_flag = false` 的总金额

同时展示数量统计：

- 系统建议通过
- 系统建议驳回
- 待复核
- 疑似重复
- 处理失败

主表格字段：

- 原文件名
- 新文件名
- 金额
- 日期
- 购方校验结果
- 业务风险分类结果
- 疑似重复标记
- 系统结论
- 人工复核状态
- 问题数量
- 操作

筛选项：

- 全部
- 系统建议通过
- 系统建议驳回
- 待复核
- 疑似重复
- 处理失败

### 6.3 发票详情抽屉

详情抽屉分为四块：

- PDF 预览
- 识别字段与证据片段
- 购方字段逐项比对
- 业务风险分类依据、疑似重复依据、建议动作

对 `待复核` 或 `疑似重复` 的票，详情抽屉提供最小人工复核动作：

- 人工确认通过
- 人工确认驳回
- 保持待复核
- 备注

### 6.4 配置中心

配置中心包含：

- 公司税务档案
- 业务风险分类规则
- 命名规则模板
- 历史配置版本列表
- 变更日志

第一期不做多管理员权限，但必须记录本机操作者名。默认操作者由本机配置项维护，例如 `default_operator_name`。

## 7. 统一文档证据模型

为避免后续更换 OCR 或解析实现时重写半条链路，所有解析能力必须先产出统一的证据模型，再进入字段抽取与规则判断。

### 7.1 DocumentEvidence

建议结构：

- `document_id`
- `source_type`：`text` / `ocr`
- `pages`
- `raw_text`
- `text_blocks`
- `table_lines`
- `field_candidates`
- `confidence_summary`
- `provider_name`
- `provider_version`
- `provider_error_code`

### 7.2 FieldCandidate

- `field_name`
- `value`
- `confidence`
- `page_no`
- `source_fragment`
- `bbox`（若 OCR 提供）

规则层、命名层、导出层只消费统一证据模型，不直接依赖某个 OCR 供应商的原始响应。

## 8. 核心数据对象

### 8.1 Batch

- `id`
- `created_at`
- `created_by`
- `status`
- `total_files`
- `completed_files`
- `processing_files`
- `failed_files`
- `suggested_pass_count`
- `suggested_pass_total_amount`
- `rule_version_id`
- `tax_profile_version_id`
- `naming_rule_version_id`
- `export_manifest_path`

其中，`suggested_pass_count` 与 `suggested_pass_total_amount` 的统计口径均排除 `duplicate_flag = true` 的记录。

### 8.2 InvoiceRecord

- `id`
- `batch_id`
- `original_filename`
- `renamed_filename`
- `storage_path_original`
- `storage_path_renamed`
- `invoice_number`
- `seller_name`
- `invoice_date`
- `invoice_amount`
- `parse_source`
- `processing_status`
- `system_decision`
- `review_status`
- `artifact_status`
- `duplicate_flag`
- `duplicate_group_key`
- `risk_flags`
- `display_status`

### 8.3 ExtractedField

- `invoice_id`
- `field_name`
- `extracted_value`
- `normalized_value`
- `confidence`
- `source_fragment`

### 8.4 FieldCheck

- `invoice_id`
- `field_name`
- `expected_value`
- `actual_value`
- `match_result`
- `reason`

### 8.5 RuleVersion

- `id`
- `version_no`
- `kind`：`tax_profile` / `business_rules` / `naming_rules`
- `content_json`
- `changed_by`
- `changed_at`
- `change_reason`

### 8.6 ReviewAction

- `invoice_id`
- `review_action`
- `review_note`
- `reviewed_by`
- `reviewed_at`

## 9. 状态模型

底层不能只有一个“最终状态”。第一期采用四组状态：

### 9.1 处理状态 `processing_status`

- `queued`
- `extracting`
- `classifying`
- `completed`
- `failed`

### 9.2 系统判定 `system_decision`

- `suggested_pass`
- `suggested_reject`
- `review_required`
- `processing_failed`

### 9.3 人工复核状态 `review_status`

- `not_reviewed`
- `manually_approved`
- `manually_rejected`

### 9.4 文件产物状态 `artifact_status`

- `original_only`
- `renamed_ready`
- `exported`

### 9.5 风险标记 `risk_flags`

- `low_confidence`
- `mixed_items`
- `missing_amount_or_date`
- `suspected_duplicate`
- `missing_detail_lines`

### 9.6 页面显示状态 `display_status`

页面展示用派生值：

- `系统建议通过`
- `系统建议驳回`
- `待复核`
- `疑似重复`
- `处理失败`

派生规则：

- `processing_status = failed` 或 `system_decision = processing_failed` => `处理失败`
- `risk_flags` 包含 `suspected_duplicate` => `疑似重复`
- `system_decision = review_required` => `待复核`
- `system_decision = suggested_reject` => `系统建议驳回`
- `system_decision = suggested_pass` => `系统建议通过`

## 10. 处理流水线

### 10.1 接收与建批次

- 校验文件类型是否为 PDF
- 建立批次目录
- 保存原始文件
- 固化当前规则版本快照到批次

### 10.2 文本提取优先

- 优先做 PDF 文本提取
- 无法得到可用文本时再进入 OCR
- OCR 失败或无有效输出时标记为 `processing_failed`

### 10.3 证据标准化

- 把文本提取或 OCR 输出转换成统一 `DocumentEvidence`
- 记录来源、置信信息和原始证据片段

### 10.4 字段抽取

提取：

- 购方名称
- 购方税号
- 地址
- 电话
- 开户银行
- 银行账户
- 开票日期
- 金额
- 发票号码
- 销售方名称
- 发票明细

### 10.5 基础合规校验

规则：

- 某字段未出现：不参与判定
- 某字段出现且高置信：必须与标准档案严格一致
- 某字段出现但低置信：优先进入 `review_required`
- 任一已出现字段高置信不一致：`suggested_reject`

为降低误杀，税务档案支持维护历史合法值集合，例如旧开户地址、旧开户行名称。

### 10.6 业务风险分类

第一期不把这一层命名为“业务合规”，统一叫“业务风险分类”。

分类策略只做有限规则集：

- 服务类白名单：餐饮、住宿、打车、交通、会议服务、培训服务、技术服务、信息服务、咨询服务、软件服务、平台服务费、运维服务、维护服务、通信服务
- 实物类黑名单：办公用品、硬件设备、食品饮料、家具材料、耗材等
- 其余情形统一 `review_required`

以下场景直接 `review_required`：

- 明细只写“商品”
- 明细只写“服务费”
- 详见清单但无清单
- 混合票
- OCR 低置信
- 明细提取失败

### 10.7 疑似重复检测

重复票检测前移到第一期。

检测范围：

- 默认检查本机历史库内所有未删除发票记录
- 数据默认长期保留，管理员可手动清理归档目录和数据库记录

最小检测组合键：

- 发票号码
- 发票代码（若有）
- 金额
- 日期
- 销售方名称

若组合键命中历史记录：

- 设置 `duplicate_flag = true`
- 设置 `risk_flags += suspected_duplicate`
- 若当前 `system_decision = suggested_pass`，则降级为 `review_required`
- 页面显示状态变为 `疑似重复`
- 不进入系统建议通过数量与金额统计

### 10.8 重命名

默认命名模板改为可追溯优先：

- `YYYYMMDD_金额_发票号码.pdf`

其中：

- 金额优先取含税总额
- 日期格式为 `YYYYMMDD`
- 金额或日期或发票号码缺失时不自动重命名

兼容能力：

- 命名模板可在配置中心切换
- `金额_日期` 仅作为可选模板，不作为默认模板
- 重名时追加 `_2`、`_3`

### 10.9 导出与统计

导出内容：

- 系统建议通过 ZIP
- 问题票 ZIP
- Excel 台账

金额统计口径：

- 批次系统建议通过金额：只统计 `system_decision = suggested_pass` 且 `duplicate_flag = false`
- 当前筛选下系统建议通过金额：在当前筛选结果内使用同一口径动态汇总

## 11. 配置与审计

第一期虽然没有登录，但配置和人工动作必须可追溯。

### 11.1 配置版本化

每次修改以下内容都生成版本：

- 税务档案
- 业务风险规则
- 命名模板

批次创建时记录所用版本号，保证历史结果可复现。

### 11.2 变更日志

日志至少记录：

- 变更人
- 变更时间
- 变更对象
- 变更前摘要
- 变更后摘要
- 变更说明

### 11.3 人工复核留痕

对待复核或疑似重复票的人工操作必须记录：

- 操作人
- 操作时间
- 复核结果
- 备注

第一期人工复核不回写系统判定，只写 `review_status` 和 `ReviewAction`，避免把系统结论和人工结论混为一体。

## 12. 存储与执行模型

### 12.1 单写者模型

第一期明确采用单进程、单写者任务模型：

- 同一时刻只有一个后台写入器负责批次状态推进和数据库写入
- 可以并发做计算型解析，但最终状态写入必须串行提交

### 12.2 文件不可变原则

- 原始文件一经落盘不可修改
- 重命名文件写入独立目录
- 导出文件写入独立导出目录

### 12.3 可恢复性

批次状态机必须支持恢复：

- 应用重启后能扫描未完成批次
- 对 `extracting` / `classifying` 中断的记录重新排队
- 已完成结果不重复入库

## 13. API 与模块边界

### 13.1 前端

- 批次工作台
- 批次结果页
- 详情抽屉
- 配置中心

### 13.2 后端 API

- 上传批次
- 查询批次列表与详情
- 查询发票列表与筛选汇总
- 查询单票详情
- 提交人工复核动作
- 查询与修改配置
- 查询配置版本日志
- 触发导出

### 13.3 核心模块

- `pipeline.extractors`
- `pipeline.ocr`
- `pipeline.normalizers`
- `pipeline.field_extractors`
- `pipeline.basic_compliance`
- `pipeline.business_risk`
- `pipeline.duplicate_detector`
- `pipeline.naming`
- `pipeline.exports`

## 14. 导出设计

Excel 台账字段至少包含：

- 原文件名
- 新文件名
- 页面显示状态
- 系统判定
- 人工复核状态
- 疑似重复标记
- 购方校验结果
- 业务风险分类结果
- 不合规或待复核原因
- 购方名称
- 购方税号
- 地址
- 电话
- 开户银行
- 银行账户
- 开票日期
- 金额
- 发票号码
- 销售方名称
- 发票明细摘要
- 批次编号
- 处理时间

## 15. 测试与验收

### 15.1 单元测试

- 税务字段严格匹配
- 低置信进入待复核
- 白名单/黑名单/灰区业务风险分类
- 疑似重复检测与建议通过统计排除
- 命名规则
- 页面显示状态派生
- 金额汇总口径

### 15.2 集成测试

- 上传批次后完整走到结果页
- 生成批次系统建议通过金额和筛选金额，且疑似重复不计入建议通过统计
- 导出 ZIP 与 Excel
- 修改配置后创建新批次，旧批次结果保持可复现
- 人工复核动作可留痕

### 15.3 样例数据集

至少准备以下 PDF 样本：

1. 标准可通过电子发票
2. 购方字段不一致发票
3. 明确实物类发票
4. 灰区待复核发票
5. 低置信 OCR 发票
6. 疑似重复发票

## 16. 风险与延后事项

### 16.1 已接受风险

- 业务风险分类只覆盖有限规则集，高覆盖率不作为第一期目标
- 扫描件质量差时会显著增加待复核比例
- 单机模型不追求多人同时使用

### 16.2 延后事项

- 真伪联网查验
- 更细业务规则平台
- 多主体支持
- 图片上传
- 与外部系统对接

## 17. 需要用户 review 的重点

在进入 implementation plan 前，用户需重点确认以下内容：

1. 第一期开启重复票检测，并单独标记疑似重复
2. 页面和导出统一改口径为“系统建议通过/系统建议驳回”
3. 业务判断层改名为“业务风险分类”
4. 配置中心保留，但必须带版本快照和变更日志
5. 默认命名模板改为 `YYYYMMDD_金额_发票号码.pdf`
