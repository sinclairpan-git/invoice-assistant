# 发票整理助手重设计文档

更新时间：2026-04-24

本文用于替代当前“首次配置友好、后续配置技术化”的混合设计，并作为下一轮产品和开发收敛的基准文档。

## 1. 复盘结论

当前产品的主问题不是单点 Bug，而是整体心智模型错误：

1. 首次配置是“财务表单”，后续配置却退化成“JSON 版本编辑器”。
2. 用户界面长期暴露内部实现概念，而不是财务动作语言。
3. 批次结果页和详情抽屉更像系统调试台，而不是财务处理工作台。
4. 人工复核只是状态补丁，不是完整的复核业务流。
5. 导出同时存在“落盘导出”和“另存为下载”两套主路径，产品语义冲突。

这会导致一个直接后果：非技术财务用户在关键路径上持续被迫理解系统内部结构，最终只能依赖技术人员代操作。

## 2. 本轮重设计目标

本轮不追求把产品做成通用规则平台，而是回到“发票整理助手”的单点目标：

1. 让财务用户能独立完成首次配置与后续调整。
2. 让批次处理页围绕“通过、待确认、失败恢复、另存为”组织。
3. 让人工复核成为可解释、可追踪、可批量处理的独立流程。
4. 让系统内部状态、规则实现、解析诊断退到二级信息，不再污染主界面。

## 3. 设计原则

1. 同一件事必须使用同一套交互模型。
说明：首次配置和后续调整都必须是字段表单，不能首次填表、后续改 JSON。

2. 默认只展示决策所需信息。
说明：主界面只展示结论、原因、影响、下一步；诊断细节折叠到“高级信息”。

3. 页面命名与状态命名必须使用财务语言。
说明：不能把 `display_status`、`risk_flags`、`provider_error` 直接暴露给用户。

4. 高频页面只服务一个主任务。
说明：批次结果页负责看结果和另存为；配置中心负责编辑配置；人工复核页负责确认。

5. 高风险操作必须可回看、可比较、可恢复。
说明：配置发布前要看变更摘要；人工复核后要立即反馈结果变更。

## 4. 当前反人类设计清单

### 4.1 配置中心

现状问题：

1. [Settings.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/pages/Settings.tsx) 把后续修改定义为“高级版本管理”。
2. [RuleVersionPanel.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/components/settings/RuleVersionPanel.tsx) 直接要求用户编辑 JSON 文本。
3. 首次配置页 [SetupWizard.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/pages/SetupWizard.tsx) 使用的是表单字段，两套模型完全割裂。

用户感受：

1. 财务用户会觉得“改一次配置像在改系统底层”。
2. 用户无法确定 JSON 字段和页面字段的对应关系。
3. 用户无法区分“改当前配置”和“发布新版本”之间的关系。

### 4.2 批次工作台与结果页

现状问题：

1. [UploadPanel.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/components/batch/UploadPanel.tsx) 只有一个上传口，把发票 PDF 与清单附件混在一起。
2. [BatchWorkbench.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/pages/BatchWorkbench.tsx) 和 [BatchResults.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/pages/BatchResults.tsx) 仍以系统状态和进度为主，不是以财务动作为主。
3. [ResultTable.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/components/results/ResultTable.tsx) 直接展示风险标记和内部结论风格，财务可读性不足。

用户感受：

1. 不知道上传前需要怎么分类文件。
2. 不知道批次完成后应该先处理哪类票。
3. 不知道哪些字段是“系统内部标签”，哪些才是财务结论。

### 4.3 发票详情与人工复核

现状问题：

1. [InvoiceDrawer.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/components/results/InvoiceDrawer.tsx) 首屏混入大量技术诊断信息。
2. [ReviewActions.tsx](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/frontend/src/components/results/ReviewActions.tsx) 只是动作表单，没有把“为什么拦截、建议看什么、确认后会怎样”讲清楚。
3. 复核入口埋在单票抽屉底部，不利于高频批量复核。

用户感受：

1. 用户在详情页里信息过载。
2. 复核时仍然要自己翻译系统内部证据。
3. 批量复核效率低。

### 4.4 后端模型与接口

现状问题：

1. [config.py](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/backend/app/api/config.py)、[config_service.py](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/backend/app/services/config_service.py) 使用通用 `dict[str, object]` 配置模型。
2. [models.py](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/backend/app/db/models.py) 中状态与版本对象过度碎片化。
3. [invoices.py](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/backend/app/api/invoices.py) 仍让预览接口直接返回 HTML 页面。
4. [export_service.py](D:/project/invoice-assistant-windows-dev-0.1.0-dev/workspace/backend/app/services/export_service.py) 同时保留落盘导出与内存下载双轨实现。

技术后果：

1. 体验迭代每次都要穿透前后端多个模型。
2. 状态同步问题容易反复出现。
3. 未来一旦做批量复核、配置发布、只读历史对账，会越来越重。

## 5. 新的信息架构

重设计后保留 4 个一级导航：

1. 新建批次
2. 批次结果
3. 待人工确认
4. 配置中心

说明：

1. “批次工作台”改成更直接的“新建批次”，降低系统感。
2. “待人工确认”从批次结果中提升为独立入口。
3. “配置中心”不再默认承载 JSON 版本编辑，而是承载配置表单与历史变更。

## 6. 页面重设计

### 6.1 新建批次

目标：让用户清楚知道“上传什么、怎么分、上传后会发生什么”。

页面结构：

1. 发票文件上传区
说明：主发票 PDF。

2. 清单/附件上传区
说明：销货清单、附件明细等辅助文件。

3. 批次命名
说明：可选，支持自动生成。

4. 提交前提示
说明：清楚说明系统会先识别、再给出建议，不会自动另存。

5. 最近批次
说明：仅展示关键摘要，不抢主入口。

### 6.2 批次结果

目标：围绕财务动作，而不是系统状态机组织。

页面结构：

1. 顶部摘要
说明：本批次总数、建议通过数、待人工确认数、本批次重复数、失败数。

2. 主筛选分组
说明：建议通过、待人工确认、本批次重复、处理失败、全部。

3. 表格主列
说明：原文件名、建议新文件名、金额、日期、购方信息、处理结论、人工确认状态、操作。

4. 批量动作区
说明：另存为当前筛选结果、另存为勾选结果、导出台账。

5. 诊断信息入口
说明：风险标记、解析来源等收敛到“高级信息”二级入口。

### 6.3 待人工确认

目标：把人工复核从“单票抽屉动作”升级为“独立工作流”。

页面结构：

1. 待确认队列
说明：默认只显示需要人工处理的票。

2. 左侧列表 + 右侧详情
说明：列表负责切票，详情负责判断。

3. 决策按钮
说明：确认通过、确认驳回、暂不处理。

4. 决策依据区
说明：系统拦截原因、建议检查项、关键字段对比、PDF 预览。

5. 复核记录
说明：显示谁在什么时间做了什么结论。

### 6.4 配置中心

目标：后续调整必须和首次配置一样简单。

配置中心拆成 4 个区域：

1. 公司税务档案
字段：
企业名称、纳税人识别号、地址电话、开户行及账号

2. 审核策略
字段：
审核风格：严格 / 平衡 / 宽松

说明：
不再直接暴露 `minimumConfidence`。

3. 文件命名
字段：
命名组成项选择器，如 日期、购方名称、金额、发票号码

说明：
不再要求用户写 `{{date}}-{{buyer}}-{{amount}}` 这类模板。

4. 历史变更
说明：
只读展示版本、修改人、修改时间、摘要、变更前后差异。

## 7. 配置交互重做

### 7.1 首次配置与后续调整统一

要求：

1. 首次配置和后续调整共用同一套表单组件。
2. 后续调整允许“编辑当前值”。
3. 点击保存后不是直接写 JSON，而是进入“发布新版本确认”。

### 7.2 配置发布确认

发布前确认页展示：

1. 修改摘要
2. 修改原因
3. 修改前与修改后对比
4. 受影响范围提示
说明：例如“新上传批次将按新规则处理，历史批次不回写”。

### 7.3 不再向财务用户暴露以下内容

1. 原始 JSON
2. 内部字段别名
3. 配置对象结构
4. 低层规则键名

## 8. 领域模型重构建议

### 8.1 配置方案模型

新增统一配置方案对象：

1. `ConfigBundle`
字段：
`profile`、`review_policy`、`naming_policy`、`version_no`、`changed_by`、`changed_at`、`change_summary`、`change_reason`

说明：

1. 用户眼里只有“一套当前配置”。
2. 技术上可以内部继续拆分存储，但 API 和页面不再暴露三段式 JSON。

### 8.2 状态模型收敛

建议保留 3 层稳定状态码：

1. `processing_status`
枚举：
`queued`、`processing`、`completed`、`failed`

2. `review_status`
枚举：
`not_required`、`pending`、`approved`、`rejected`

3. `archive_status`
枚举：
`not_ready`、`ready`、`saved`

说明：

1. `display_status` 改成前端派生展示字段。
2. 接口不要再以中文文案做筛选主键。

### 8.3 人工复核对象

建议新增明确的复核工作流语义：

1. 发票是否进入复核队列
2. 复核优先级
3. 复核决定
4. 复核备注
5. 复核时间

说明：
不要只把复核理解为改 `review_status`。

## 9. API 重构建议

### 9.1 配置接口

现状：
`/api/config/*` 过于通用。

建议：

1. `GET /api/settings/profile`
2. `PUT /api/settings/profile`
3. `GET /api/settings/review-policy`
4. `PUT /api/settings/review-policy`
5. `GET /api/settings/naming-policy`
6. `PUT /api/settings/naming-policy`
7. `POST /api/settings/publish`
8. `GET /api/settings/history`

### 9.2 结果接口

建议：

1. 列表接口返回稳定状态码字段。
2. 批次摘要接口返回可直接渲染的分组统计。
3. 复核提交接口返回“单票结果 + 批次增量摘要”。

### 9.3 预览接口

建议：

1. `GET /api/invoices/{id}/preview-meta`
返回：
`page_count`、`page_image_urls`、`pdf_url`

2. 前端自己组织 PDF 预览页面。

说明：
不再让后端直接返回 HTML 页面。

### 9.4 导出接口

建议：

1. 保留统一 `download` 能力。
2. 删除 UI 主流程中的落盘导出作业。
3. 旧 `/exports` 仅做兼容，不再作为主入口。

## 10. 开发拆分

### Phase 0：快速体验修正

目标：先去掉最刺眼的反人类体验。

范围：

1. 隐藏配置中心的 JSON 编辑入口。
2. 设置页改成“当前配置表单只读 + 编辑入口”。
3. 结果表和详情页默认隐藏内部诊断字段。
4. 人工复核区文案改成财务动作语言。

交付标准：

1. 财务用户在 UI 主路径上不再看到 JSON。
2. 不再看到 `not_reviewed` 这类内部词。

### Phase 1：配置中心重做

目标：统一首次配置与后续配置。

范围：

1. 抽出共享的税务档案表单、审核策略表单、命名规则表单。
2. 配置保存改成“编辑 + 发布确认”。
3. 历史版本改成只读列表，不可直接编辑配置内容。

交付标准：

1. 首次配置和后续调整使用同一套表单组件。
2. 配置变更前有确认页和差异摘要。

### Phase 2：批次结果与复核闭环重做

目标：让财务处理路径清晰。

范围：

1. 批次结果页按财务动作重新分组。
2. 新增待人工确认页面。
3. 复核后批次摘要与表格行即时同步。
4. 高级诊断折叠。

交付标准：

1. 用户能明确区分“建议通过、待确认、本批次重复、失败”。
2. 复核不再依赖手工刷新理解结果。

### Phase 3：后端模型收敛

目标：为后续迭代降复杂度。

范围：

1. 配置对象 typed 化。
2. 状态码收敛。
3. `display_status` 降级为兼容层。
4. 复核返回批次增量摘要。

交付标准：

1. 前端主流程不再依赖中文状态值作为逻辑判断。
2. 配置接口和状态接口具备明确 schema。

### Phase 4：导出与预览链路收口

目标：消灭双轨主流程。

范围：

1. 仅保留“另存为”主流程。
2. 预览改成资源接口 + 前端组件。
3. 旧导出作业只保留兼容期。

交付标准：

1. 用户主流程中不再出现“自动落盘导出”概念。
2. 预览前后端边界清晰。

## 11. 风险与兼容策略

1. 历史批次追溯风险
策略：继续保留历史 `snapshot_json` 只读适配。

2. 状态字段切换风险
策略：短期双写 `status_code` 与 `display_status`。

3. 配置迁移风险
策略：旧 JSON 映射到 typed schema，未知字段进入 `legacy_extensions`。

4. 导出习惯切换风险
策略：旧 `/exports` 接口保留一个版本周期，但 UI 下线入口。

## 12. 本轮明确要砍掉的低收益能力

1. 财务用户可直接编辑 JSON 配置
2. 把角色/可信上下文作为主信息长期展示
3. 把 Provider、解析来源、内部标记放在详情首屏
4. 把落盘导出作业继续作为产品主流程

## 13. 下一步执行建议

建议直接按以下顺序推进：

1. 先做 Phase 0 和 Phase 1
原因：这是用户感知最强、改动收益最高的部分。

2. 再做 Phase 2
原因：复核和批次结果是第二高频路径。

3. 最后做 Phase 3 和 Phase 4
原因：属于技术收口和长期维护收益。
