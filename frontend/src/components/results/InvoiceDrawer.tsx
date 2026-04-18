import { Alert, App, Button, Descriptions, Drawer, List, Space, Table, Tabs, Tag, Typography } from "../../app/antd";
import { useCallback, useEffect, useState } from "react";

import { createInvoiceRetry, getErrorMessage, getInvoiceDetail, getInvoicePreviewUrl } from "../../app/api";
import type { ExtractedField, FieldCheck, InvoiceDetail } from "../../app/types";
import { AsyncBoundary } from "../common/AsyncBoundary";
import { ReviewActions } from "./ReviewActions";


interface InvoiceDrawerProps {
  invoiceId: string | null;
  open: boolean;
  onClose: () => void;
  onChanged: () => Promise<void> | void;
}

const extractedFieldColumns = [
  {
    title: "字段",
    dataIndex: "field_name",
    key: "field_name",
    width: 140,
  },
  {
    title: "提取值",
    dataIndex: "normalized_value",
    key: "normalized_value",
    render: (_: string | null, record: ExtractedField) => record.normalized_value || record.extracted_value || "--",
  },
  {
    title: "置信度",
    dataIndex: "confidence",
    key: "confidence",
    width: 100,
    render: (value: string | null) => value || "--",
  },
  {
    title: "来源片段",
    dataIndex: "source_fragment",
    key: "source_fragment",
    ellipsis: true,
  },
];

const fieldCheckColumns = [
  {
    title: "校验项",
    dataIndex: "field_name",
    key: "field_name",
    width: 160,
  },
  {
    title: "期望值",
    dataIndex: "expected_value",
    key: "expected_value",
  },
  {
    title: "实际值",
    dataIndex: "actual_value",
    key: "actual_value",
  },
  {
    title: "结果",
    dataIndex: "match_result",
    key: "match_result",
    width: 120,
  },
  {
    title: "原因",
    dataIndex: "reason",
    key: "reason",
    ellipsis: true,
  },
];

function renderStatusTag(status: string) {
  if (status.includes("通过")) {
    return <Tag color="green">{status}</Tag>;
  }
  if (status.includes("驳回") || status.includes("失败")) {
    return <Tag color="red">{status}</Tag>;
  }
  if (status.includes("重复")) {
    return <Tag color="volcano">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

export function InvoiceDrawer({ invoiceId, open, onClose, onChanged }: InvoiceDrawerProps) {
  const { message } = App.useApp();
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const loadInvoice = useCallback(async () => {
    if (!invoiceId) {
      setInvoice(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const detail = await getInvoiceDetail(invoiceId);
      setInvoice(detail);
    } catch (nextError) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoading(false);
    }
  }, [invoiceId]);

  useEffect(() => {
    if (open && invoiceId) {
      void loadInvoice();
    }
  }, [invoiceId, loadInvoice, open]);

  return (
    <Drawer width={960} open={open} onClose={onClose} title="发票详情" destroyOnClose>
      <AsyncBoundary loading={loading} error={error}>
        {invoice ? (
          <div className="drawer-body">
            <Space wrap className="status-row">
              {renderStatusTag(invoice.display_status)}
              <Tag>{invoice.review_status || "未复核"}</Tag>
              {invoice.duplicate_flag ? <Tag color="volcano">疑似重复</Tag> : null}
            </Space>
            <Descriptions bordered size="small" column={2} className="description-block">
              <Descriptions.Item label="原文件名">{invoice.original_filename}</Descriptions.Item>
              <Descriptions.Item label="新文件名">{invoice.renamed_filename || "未重命名"}</Descriptions.Item>
              <Descriptions.Item label="金额">{invoice.invoice_amount || "--"}</Descriptions.Item>
              <Descriptions.Item label="日期">{invoice.invoice_date || "--"}</Descriptions.Item>
              <Descriptions.Item label="购方名称">{invoice.buyer_name || "--"}</Descriptions.Item>
              <Descriptions.Item label="购方税号">{invoice.buyer_tax_no || "--"}</Descriptions.Item>
              <Descriptions.Item label="发票号码">{invoice.invoice_number || "--"}</Descriptions.Item>
              <Descriptions.Item label="问题数">{invoice.problem_count}</Descriptions.Item>
            </Descriptions>
            <Descriptions bordered size="small" column={2} className="description-block">
              <Descriptions.Item label="基础合规">{invoice.basic_compliance_status || "--"}</Descriptions.Item>
              <Descriptions.Item label="业务合规">{invoice.business_compliance_status || "--"}</Descriptions.Item>
              <Descriptions.Item label="最终结论">{invoice.final_decision || "--"}</Descriptions.Item>
              <Descriptions.Item label="建议动作">
                {invoice.suggested_actions.length > 0 ? invoice.suggested_actions.join("，") : "--"}
              </Descriptions.Item>
              <Descriptions.Item label="结论原因" span={2}>
                {invoice.decision_reasons.length > 0 ? invoice.decision_reasons.join("，") : "--"}
              </Descriptions.Item>
            </Descriptions>
            <Descriptions bordered size="small" column={2} className="description-block">
              <Descriptions.Item label="解析来源">{invoice.parse_source || "--"}</Descriptions.Item>
              <Descriptions.Item label="失败阶段">{invoice.last_error_stage || "--"}</Descriptions.Item>
              <Descriptions.Item label="错误码">{invoice.last_error_code || "--"}</Descriptions.Item>
              <Descriptions.Item label="可重试">{invoice.retryable ? "是" : "否"}</Descriptions.Item>
              <Descriptions.Item label="Provider">{invoice.provider_diagnostic.provider_name || "--"}</Descriptions.Item>
              <Descriptions.Item label="Provider 版本">{invoice.provider_diagnostic.provider_version || "--"}</Descriptions.Item>
              <Descriptions.Item label="Provider 错误">{invoice.provider_diagnostic.provider_error_code || "--"}</Descriptions.Item>
              <Descriptions.Item label="失败信息">{invoice.last_error_message || invoice.failure_reason || "--"}</Descriptions.Item>
            </Descriptions>
            {invoice.retryable ? (
              <Space>
                <Button
                  onClick={async () => {
                    setRetrying(true);
                    try {
                      await createInvoiceRetry({ invoiceId: invoice.id });
                      message.success("当前票已重新入队");
                      await loadInvoice();
                      await onChanged();
                    } catch (nextError) {
                      message.error(getErrorMessage(nextError));
                    } finally {
                      setRetrying(false);
                    }
                  }}
                  loading={retrying}
                >
                  重试当前票
                </Button>
              </Space>
            ) : null}
            <Tabs
              items={[
                {
                  key: "preview",
                  label: "PDF 预览",
                  children: (
                    <div className="preview-frame">
                      {invoice.preview_path ? (
                        <iframe src={getInvoicePreviewUrl(invoice.id)} title={invoice.original_filename} className="pdf-preview" />
                      ) : (
                        <Alert type="warning" showIcon message="当前记录没有可预览的文件路径" />
                      )}
                    </div>
                  ),
                },
                {
                  key: "evidence",
                  label: "字段与证据",
                  children: (
                    <Space direction="vertical" size="large" className="full-width">
                      <Table
                        rowKey="id"
                        columns={extractedFieldColumns}
                        dataSource={invoice.extracted_fields}
                        size="small"
                        pagination={false}
                      />
                      <List
                        header="证据片段"
                        bordered
                        dataSource={invoice.evidence_items}
                        renderItem={(item) => (
                          <List.Item>
                            <Space direction="vertical" size={4} className="full-width">
                              <Typography.Text strong>{`${item.provider_name || "parser"} / ${item.source_type}`}</Typography.Text>
                              <Typography.Paragraph className="evidence-text" ellipsis={{ rows: 4, expandable: true }}>
                                {item.raw_text || "无原始文本"}
                              </Typography.Paragraph>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Space>
                  ),
                },
                {
                  key: "rules",
                  label: "校验依据",
                  children: (
                    <Space direction="vertical" size="large" className="full-width">
                      <Table
                        rowKey="id"
                        columns={fieldCheckColumns}
                        dataSource={invoice.field_checks}
                        size="small"
                        pagination={false}
                      />
                      <Descriptions bordered size="small" column={1}>
                        <Descriptions.Item label="风险依据">
                          {invoice.risk_flags.length > 0 ? invoice.risk_flags.join("，") : "无风险标记"}
                        </Descriptions.Item>
                        <Descriptions.Item label="疑似重复依据">
                          {invoice.duplicate_group_key || "未命中重复组"}
                        </Descriptions.Item>
                        <Descriptions.Item label="失败原因">{invoice.failure_reason || "无"}</Descriptions.Item>
                      </Descriptions>
                    </Space>
                  ),
                },
                {
                  key: "review",
                  label: "人工复核",
                  children: (
                    <Space direction="vertical" size="large" className="full-width">
                      <ReviewActions
                        invoiceId={invoice.id}
                        displayStatus={invoice.display_status}
                        onSubmitted={async () => {
                          await loadInvoice();
                          await onChanged();
                        }}
                      />
                      <List
                        header="复核留痕"
                        bordered
                        dataSource={invoice.review_actions}
                        locale={{ emptyText: "暂无人工复核记录" }}
                        renderItem={(item) => (
                          <List.Item>
                            <Space direction="vertical" size={2}>
                              <Typography.Text strong>{item.review_action}</Typography.Text>
                              <Typography.Text type="secondary">{`${item.reviewed_by} · ${item.reviewed_at}`}</Typography.Text>
                              {item.review_note ? <Typography.Text>{item.review_note}</Typography.Text> : null}
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Space>
                  ),
                },
              ]}
            />
          </div>
        ) : null}
      </AsyncBoundary>
    </Drawer>
  );
}
