import { Button, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type { InvoiceSummary } from "../../app/types";


interface ResultTableProps {
  invoices: InvoiceSummary[];
  onInspect: (invoiceId: string) => void;
}

function statusColor(status: string) {
  if (status.includes("通过")) {
    return "green";
  }
  if (status.includes("驳回") || status.includes("失败")) {
    return "red";
  }
  if (status.includes("重复")) {
    return "volcano";
  }
  return "gold";
}

export function ResultTable({ invoices, onInspect }: ResultTableProps) {
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
      render: (value: string | null) => value || "未重命名",
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
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>{record.buyer_name || "未识别"}</Typography.Text>
          <Typography.Text type="secondary">{record.buyer_tax_no || "税号缺失"}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "风险标记",
      key: "risk_flags",
      render: (_, record) =>
        record.risk_flags.length > 0 ? (
          <Space wrap>
            {record.risk_flags.map((flag) => (
              <Tag key={flag}>{flag}</Tag>
            ))}
          </Space>
        ) : (
          "无"
        ),
    },
    {
      title: "系统结论",
      key: "display_status",
      render: (_, record) => <Tag color={statusColor(record.display_status)}>{record.display_status}</Tag>,
    },
    {
      title: "人工复核",
      dataIndex: "review_status",
      key: "review_status",
      width: 120,
      render: (value: string | null) => value || "--",
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

  return <Table rowKey="id" columns={columns} dataSource={invoices} pagination={{ pageSize: 8 }} scroll={{ x: 1200 }} />;
}
