import { Button, Progress, Space, Table, Tag, Typography } from "../../app/antd";
import type { ColumnsType } from "antd/es/table";

import type { Batch } from "../../app/types";


interface BatchListProps {
  batches: Batch[];
  onOpenResults: (batchId: string) => void;
}

function renderStageTag(stageText: string | undefined) {
  if (!stageText) {
    return <Tag>未刷新</Tag>;
  }
  if (stageText.includes("完成")) {
    return <Tag color="green">{stageText}</Tag>;
  }
  if (stageText.includes("失败")) {
    return <Tag color="red">{stageText}</Tag>;
  }
  return <Tag color="gold">{stageText}</Tag>;
}

const columns: ColumnsType<Batch> = [
  {
    title: "批次",
    dataIndex: "batch_no",
    key: "batch_no",
    render: (value: string, record) => (
      <div>
        <Typography.Text strong>{value}</Typography.Text>
        <div className="table-subtext">{record.created_by}</div>
      </div>
    ),
  },
  {
    title: "阶段",
    key: "progress",
    render: (_, record) => (
      <div>
        {renderStageTag(record.progress?.stage_text)}
        <Progress
          percent={record.progress?.progress_percent ?? 0}
          size="small"
          showInfo={false}
          strokeColor="#118a62"
          trailColor="#dde5da"
        />
      </div>
    ),
  },
  {
    title: "文件统计",
    key: "totals",
    render: (_, record) => (
      <Space direction="vertical" size={0}>
        <Typography.Text>{`总数 ${record.total_files}`}</Typography.Text>
        <Typography.Text type="secondary">{`完成 ${record.completed_files} / 失败 ${record.failed_files}`}</Typography.Text>
      </Space>
    ),
  },
  {
    title: "建议通过",
    key: "suggested_pass",
    render: (_, record) => (
      <Space direction="vertical" size={0}>
        <Typography.Text>{`数量 ${record.suggested_pass_count}`}</Typography.Text>
        <Typography.Text type="secondary">{`金额 ${record.suggested_pass_total_amount}`}</Typography.Text>
      </Space>
    ),
  },
  {
    title: "操作",
    key: "actions",
    align: "right",
    render: () => null,
  },
];

export function BatchList({ batches, onOpenResults }: BatchListProps) {
  const resolvedColumns: ColumnsType<Batch> = columns.map((column) => {
    if (column.key !== "actions") {
      return column;
    }
    return {
      ...column,
      render: (_, record) => (
        <Button type="link" onClick={() => onOpenResults(record.id)}>
          查看结果
        </Button>
      ),
    };
  });

  return <Table rowKey="id" columns={resolvedColumns} dataSource={batches} pagination={{ pageSize: 6 }} />;
}
