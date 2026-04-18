import { App, Button, Form, Input, Select, Space, Typography } from "../../app/antd";
import { useEffect, useState } from "react";

import { createReviewAction, getErrorMessage } from "../../app/api";
import { useOperatorSettings } from "../../app/operator-settings";


interface ReviewActionsProps {
  invoiceId: string;
  displayStatus: string;
  onSubmitted: () => Promise<void> | void;
}

interface ReviewFormValues {
  reviewAction: string;
  reviewNote?: string;
}

const ACTION_OPTIONS = [
  { label: "人工确认通过", value: "approve" },
  { label: "人工确认驳回", value: "reject" },
  { label: "保持待复核", value: "keep_review_required" },
];

export function ReviewActions({ invoiceId, displayStatus, onSubmitted }: ReviewActionsProps) {
  const { message } = App.useApp();
  const { defaultOperatorName } = useOperatorSettings();
  const [form] = Form.useForm<ReviewFormValues>();
  const [submitting, setSubmitting] = useState(false);
  const reviewable = displayStatus === "待复核" || displayStatus === "疑似重复";

  useEffect(() => {
    form.setFieldValue("reviewAction", "approve");
  }, [form]);

  if (!reviewable) {
    return <Typography.Text type="secondary">当前票据无需人工复核。</Typography.Text>;
  }

  const handleSubmit = async (values: ReviewFormValues) => {
    setSubmitting(true);
    try {
      await createReviewAction({
        invoiceId,
        reviewAction: values.reviewAction,
        reviewNote: values.reviewNote,
      });
      message.success("复核动作已记录");
      await onSubmitted();
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
        <Input.TextArea rows={4} placeholder="记录人工复核依据" />
      </Form.Item>
      <Space>
        <Button type="primary" htmlType="submit" loading={submitting}>
          提交复核
        </Button>
      </Space>
    </Form>
  );
}
