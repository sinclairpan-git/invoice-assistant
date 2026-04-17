# 发票整理助手手工验收清单

## 1. 启动服务

1. 后端启动：
   `UV_CACHE_DIR=/Users/sinclairpan/project/发票整理助手/.uv-cache uv run --project backend uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000`
2. 前端启动：
   `COREPACK_HOME=/Users/sinclairpan/project/发票整理助手/frontend/.corepack corepack pnpm run dev -- --host 127.0.0.1 --port 5173`
3. 打开：
   `http://127.0.0.1:5173/`

## 2. 预置配置

在“配置中心”依次确认或新建以下生效版本：

- 税务档案：
  - `buyer_name = Shanghai Example Co`
  - `buyer_tax_no = 91310000X`
- 风险规则：
  - `minimum_confidence = 0.75`
  - `seller_whitelist = ["Acme Supplies Ltd", "Scan Services Co"]`
  - `review_keywords = ["DETAIL LIST ATTACHED"]`
- 命名模板：
  - `pattern = {date}_{amount}_{number}`

## 3. 上传样例

上传目录 `/Users/sinclairpan/project/发票整理助手/backend/tests/fixtures/invoices/` 下四张样例票：

1. `01-standard-electronic.pdf`
2. `02-scanned-ocr.pdf`
3. `03-review-required.pdf`
4. `04-duplicate.pdf`

## 4. 核心验收点

1. 工作台批次卡片显示：
   - 总文件数 `4`
   - 完成数 `4`
   - 失败数 `0`
   - 系统建议通过数 `2`
   - 合规票总金额 `384.50`
2. 结果页顶部同时显示：
   - 批次系统建议通过金额 `384.50`
   - 当前筛选系统建议通过金额
3. “系统建议通过”筛选下应看到两张票，重命名文件名分别为：
   - `20260417_128.50_STD-001.pdf`
   - `20260416_256.00_OCR-001.pdf`
4. “待复核”筛选下应看到 `03-review-required.pdf`，当前筛选系统建议通过金额应为 `0.00`
5. “疑似重复”筛选下应看到 `04-duplicate.pdf`，且不计入任何合规票金额汇总
6. 详情抽屉中应可查看：
   - 原始证据
   - 抽取字段
   - 购方校验记录
   - 风险标记
   - 疑似重复依据（仅重复票）
7. 对 `03-review-required.pdf` 发起人工复核“通过”后：
   - 留痕成功
   - `review_status` 更新为人工通过
   - `system_decision` 仍保持 `review_required`

## 5. 导出验收

依次执行三类导出并核对结果：

1. 系统建议通过 ZIP：
   - 文件数 `2`
   - 总金额 `384.50`
   - ZIP 内为两份重命名后的 PDF
2. 问题票 ZIP：
   - 文件数 `2`
   - 总金额 `216.50`
   - ZIP 内为 `03-review-required.pdf` 与 `04-duplicate.pdf`
3. Excel 台账：
   - 总记录数 `4`
   - 系统建议通过数 `2`
   - 系统建议通过总金额 `384.50`

## 6. 结论口径

- 合规票总金额只统计 `suggested_pass` 且排除疑似重复票。
- “批次总额”和“当前筛选总额”都必须展示。
- 人工复核只追加留痕，不改写系统判定。
