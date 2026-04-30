import { App, Button, Form, Input, Select, Space, Typography } from "../../app/antd";
import { useEffect, useState } from "react";

import { createReviewAction, getErrorMessage } from "../../app/api";
import { useOperatorSettings } from "../../app/operator-settings";
import type { InvoiceSummary } from "../../app/types";
import { getReviewStatusLabel, requiresManualReview } from "./resultPresentation";


interface ReviewActionsProps {
  invoiceId: string;
  processingStatus: string | null;
  systemDecision: string | null;
  duplicateFlag: boolean;
  reviewStatus: string | null;
  onSubmitted: (invoice: InvoiceSummary) => Promise<void> | void;
}

interface ReviewFormValues {
  reviewAction: string;
  reviewNote?: string;
}

const ACTION_OPTIONS = [
  { label: "确认通过", value: "approve" },
  { label: "确认驳回", value: "reject" },
  { label: "暂不处理", value: "keep_review_required" },
];

export function ReviewActions({
  invoiceId,
  processingStatus,
  systemDecision,
  duplicateFlag,
  reviewStatus,
  onSubmitted,
}: ReviewActionsProps) {
  const { message } = App.useApp();
  const { defaultOperatorName } = useOperatorSettings();
  const [form] = Form.useForm<ReviewFormValues>();
  const [submitting, setSubmitting] = useState(false);
  const reviewable = requiresManualReview({
    processingStatus,
    systemDecision,
    duplicateFlag,
    reviewStatus,
  });

  useEffect(() => {
    form.setFieldValue("reviewAction", "approve");
  }, [form]);

  if (!reviewable) {
    return (
      <Typography.Text type="secondary">
        {`当前票据${getReviewStatusLabel({
          processingStatus,
          systemDecision,
          duplicateFlag,
          reviewStatus,
        })}。`}
      </Typography.Text>
    );
  }

  const handleSubmit = async (values: ReviewFormValues) => {
    setSubmitting(true);
    try {
      const result = await createReviewAction({
        invoiceId,
        reviewAction: values.reviewAction,
        reviewNote: values.reviewNote,
      });
      message.success("人工确认已记录，结果会自动刷新。");
      form.setFieldValue("reviewNote", "");
      await onSubmitted(result.invoice);
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form form={form} layout="vertical" onFinish={handleSubmit}>
      <Typography.Text type="secondary">{`当前操作者：${defaultOperatorName}`}</Typography.Text>
      <Form.Item<ReviewFormValues> label="处理动作" name="reviewAction" rules={[{ required: true, message: "请选择处理动作" }]}>
        <Select options={ACTION_OPTIONS} />
      </Form.Item>
      <Form.Item<ReviewFormValues> label="备注" name="reviewNote">
        <Input.TextArea rows={4} placeholder="记录人工确认依据" />
      </Form.Item>
      <Typography.Text type="secondary">提交后会立即刷新当前票据和批次结果。</Typography.Text>
      <Space>
        <Button type="primary" htmlType="submit" loading={submitting}>
          提交确认
        </Button>
      </Space>
    </Form>
  );
}
