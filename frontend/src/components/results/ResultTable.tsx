import { Button, Space, Table, Tag, Typography } from "../../app/antd";
import type { ColumnsType } from "antd/es/table";

import type { InvoiceSummary } from "../../app/types";
import {
  getResultStatusColor,
  getResultStatusLabel,
  getReviewStatusColor,
  getReviewStatusLabel,
  isInvoiceFailed,
  isInvoiceProcessing,
} from "./resultPresentation";


interface ResultTableProps {
  invoices: InvoiceSummary[];
  onInspect: (invoiceId: string) => void;
  selectedRowKeys?: string[];
  onSelectionChange?: (invoiceIds: string[]) => void;
}

function renderBuyer(record: InvoiceSummary) {
  if (isInvoiceProcessing(record.processing_status)) {
    return (
      <Space direction="vertical" size={0}>
        <Typography.Text>处理中</Typography.Text>
        <Typography.Text type="secondary">等待识别</Typography.Text>
      </Space>
    );
  }

  if (isInvoiceFailed(record.processing_status)) {
    return (
      <Space direction="vertical" size={0}>
        <Typography.Text>需补充或重试</Typography.Text>
        <Typography.Text type="secondary">{record.failure_reason || "当前票据尚未完成识别"}</Typography.Text>
      </Space>
    );
  }

  return (
    <Space direction="vertical" size={0}>
      <Typography.Text>{record.buyer_name || "未识别"}</Typography.Text>
      <Typography.Text type="secondary">{record.buyer_tax_no || "税号缺失"}</Typography.Text>
    </Space>
  );
}

export function ResultTable({
  invoices,
  onInspect,
  selectedRowKeys = [],
  onSelectionChange,
}: ResultTableProps) {
  const columns: ColumnsType<InvoiceSummary> = [
    {
      title: "原文件名",
      dataIndex: "original_filename",
      key: "original_filename",
      ellipsis: true,
    },
    {
      title: "新文件名",
      dataIndex: "renamed_filename",
      key: "renamed_filename",
      ellipsis: true,
      render: (value: string | null, record) => {
        if (isInvoiceProcessing(record.processing_status)) {
          return "处理中";
        }
        if (isInvoiceFailed(record.processing_status)) {
          return "待补充后再生成";
        }
        return value || "未重命名";
      },
    },
    {
      title: "金额",
      dataIndex: "invoice_amount",
      key: "invoice_amount",
      width: 120,
      render: (value: string | null) => value || "--",
    },
    {
      title: "日期",
      dataIndex: "invoice_date",
      key: "invoice_date",
      width: 120,
      render: (value: string | null) => value || "--",
    },
    {
      title: "购方信息",
      key: "buyer",
      render: (_, record) => renderBuyer(record),
    },
    {
      title: "处理结论",
      key: "display_status",
      render: (_, record) => (
        <Tag color={getResultStatusColor(record.display_status)}>{getResultStatusLabel(record.display_status)}</Tag>
      ),
    },
    {
      title: "人工确认",
      key: "review_status",
      width: 140,
      render: (_, record) => (
        <Tag
          color={getReviewStatusColor({
            processingStatus: record.processing_status,
            systemDecision: record.system_decision,
            duplicateFlag: record.duplicate_flag,
            reviewStatus: record.review_status,
          })}
        >
          {getReviewStatusLabel({
            processingStatus: record.processing_status,
            systemDecision: record.system_decision,
            duplicateFlag: record.duplicate_flag,
            reviewStatus: record.review_status,
          })}
        </Tag>
      ),
    },
    {
      title: "问题数",
      dataIndex: "problem_count",
      key: "problem_count",
      width: 90,
    },
    {
      title: "操作",
      key: "actions",
      align: "right",
      width: 110,
      render: (_, record) => (
        <Button type="link" onClick={() => onInspect(record.id)}>
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      dataSource={invoices}
      rowSelection={
        onSelectionChange
          ? {
              selectedRowKeys,
              onChange: (keys) => onSelectionChange(keys.map((item) => String(item))),
              preserveSelectedRowKeys: true,
            }
          : undefined
      }
      pagination={{ pageSize: 8 }}
      scroll={{ x: 1080 }}
    />
  );
}
